import contextlib
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
from pathlib import Path
import sys
import threading
import time
import unittest
from urllib.request import urlopen
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import main
import parser
import server_backend
from core import runtime
from core.diagnostics import BSError
from core.values import BSModule

HAS_SERVER = all(importlib.util.find_spec(name) for name in ('werkzeug', 'waitress'))


class RuntimeStateTests(unittest.TestCase):
    def test_clone_retains_aliases_cycles_and_module_type(self):
        shared = [1]
        original = {'a': shared, 'b': shared, 'module': BSModule({'funcs': {}})}
        original['self'] = original
        copied = runtime.clone(original)
        self.assertIs(copied['a'], copied['b'])
        self.assertIs(copied['self'], copied)
        self.assertIsInstance(copied['module'], BSModule)
        copied['a'].append(2)
        self.assertEqual(original['a'], [1])


@unittest.skipUnless(HAS_SERVER, 'Install the server extra to test HTTP support')
class ServerSupportTests(unittest.TestCase):
    def setUp(self):
        from werkzeug.test import Client
        from werkzeug.wrappers import Response
        self.Client, self.Response = Client, Response
        self.names = dict(parser.names)
        self.functions = dict(main.functions)
        self.servers = []
        self.threads = []

    def tearDown(self):
        for server in self.servers:
            server.stop()
        for thread in self.threads:
            thread.join(10)
            self.assertFalse(thread.is_alive(), 'Server did not stop')
        parser.names.clear()
        parser.names.update(self.names)
        main.functions.clear()
        main.functions.update(self.functions)
        self.assertIsNone(runtime.state.get())
        self.assertEqual(len(parser.scopes), 1)
        self.assertEqual(main.function_environments, [None])

    def configure(self, source):
        main.execute_lines(('add server\n' + source).splitlines())
        server = parser.names['server']['funcs']['app']()
        self.servers.append(server)
        return server, self.Client(server, self.Response)

    def test_native_routes_request_fields_and_json_response(self):
        server, client = self.configure('''func echo(request):
    return server.response(request, 201, {"X-Test": "yes"})
end
server.post("/users/<int:user_id>", "echo")
''')
        response = client.post('/users/42?q=one&q=two', json={'name': 'café'}, headers={'X-Request': 'test'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers['X-Test'], 'yes')
        self.assertEqual(response.mimetype, 'application/json')
        data = response.json
        self.assertEqual(data['params'], {'user_id': 42})
        self.assertEqual(data['query'], {'q': 'one'})
        self.assertEqual(data['query_all'], {'q': ['one', 'two']})
        self.assertEqual(data['headers']['x-request'], 'test')
        self.assertEqual(data['json'], {'name': 'café'})
        self.assertEqual(data['method'], 'POST')
        self.assertEqual(data['path'], '/users/42')

    def test_json_errors_and_body_limit_do_not_break_later_requests(self):
        _, client = self.configure('''func echo(request):
    return request["json"]
end
server.post("/echo", "echo")
''')
        for body in ['{', 'NaN', '1e999', b'\xff', '']:
            with self.subTest(body=body):
                self.assertEqual(client.post('/echo', data=body, content_type='application/json').status_code, 400)
        response = client.post('/echo', data='x' * (server_backend.MAX_BODY_SIZE + 1))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(client.post('/echo', json=[1, True, None]).json, [1, True, None])
        self.assertEqual(client.post('/echo', data='{"a":2}', content_type='application/test+json').json, {'a': 2})
        self.assertEqual(client.post('/echo', data='text').json, None)

    def test_routing_errors_head_options_and_redirect(self):
        _, client = self.configure('''func health(request):
    return {"ok": true}
end
server.get("/health", "health")
server.get("/folder/", "health")
''')
        self.assertEqual(client.get('/missing').status_code, 404)
        self.assertEqual(client.get('/health').json, {'ok': True})
        self.assertEqual(client.head('/health').data, b'')
        wrong_method = client.post('/health')
        self.assertEqual(wrong_method.status_code, 405)
        self.assertIn('GET', wrong_method.headers['Allow'])
        options = client.options('/health')
        self.assertEqual(options.status_code, 204)
        self.assertIn('OPTIONS', options.headers['Allow'])
        redirect = client.get('/folder')
        self.assertEqual(redirect.status_code, 308)
        self.assertTrue(redirect.headers['Location'].endswith('/folder/'))

    def test_response_types_caught_errors_and_no_content(self):
        _, client = self.configure('''func text(request):
    return "café"
end
func caught(request):
    try:
        value = 1 / 0
    catch ZeroDivisionError:
        return server.response({"error": "invalid operation"}, 422)
    end
end
func empty(request):
    return server.response(null, 204)
end
server.get("/text", "text")
server.get("/caught", "caught")
server.delete("/empty", "empty")
''')
        response = client.get('/text')
        self.assertEqual(response.get_data(as_text=True), 'café')
        self.assertEqual(response.mimetype, 'text/plain')
        self.assertEqual(client.get('/caught').status_code, 422)
        self.assertEqual(client.delete('/empty').data, b'')

    def test_handler_failure_is_logged_and_other_requests_continue(self):
        _, client = self.configure('''func fail(request):
    return 1 / 0
end
func health(request):
    return {"ok": true}
end
server.get("/fail", "fail")
server.get("/health", "health")
''')
        log = io.StringIO()
        with contextlib.redirect_stderr(log):
            response = client.get('/fail')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json, {'error': 'Internal server error'})
        self.assertIn('ZeroDivisionError', log.getvalue())
        self.assertIn('fail at', log.getvalue())
        self.assertEqual(client.get('/health').json, {'ok': True})

    def test_concurrent_requests_have_separate_variables_and_library_calls(self):
        barrier = threading.Barrier(4)
        parser.names['wait_for_peers'] = lambda: barrier.wait(timeout=5)
        server, _ = self.configure('''add json
shared = {"items": []}
func isolated(request):
    value = request["params"]["value"]
    shared["items"].append(value)
    wait_for_peers()
    return json.parse(json.stringify({"value": value, "items": shared["items"]}))
end
server.get("/isolated/<int:value>", "isolated")
''')
        def get(value):
            return self.Client(server, self.Response).get(f'/isolated/{value}').json
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(get, range(4)))
        self.assertEqual(results, [{'value': value, 'items': [value]} for value in range(4)])
        self.assertEqual(parser.names['shared'], {'items': []})

    def test_startup_snapshot_is_fixed_and_servers_are_independent(self):
        server, client = self.configure('''value = {"count": 1}
func count(request):
    value["count"] += 1
    return value
end
server.get("/count", "count")
''')
        parser.names['value']['count'] = 20
        self.assertEqual(client.get('/count').json, {'count': 2})
        self.assertEqual(client.get('/count').json, {'count': 2})
        other, other_client = self.configure('''func other(request):
    return "other"
end
server.get("/other", "other")
''')
        self.assertIsNot(server, other)
        self.assertEqual(other_client.get('/count').status_code, 404)
        self.assertEqual(other_client.get('/other').get_data(as_text=True), 'other')

    def test_bad_routes_and_late_registration_are_catchable(self):
        source = '''add server
func handler(request):
    return true
end
func wrong(a, b):
    return false
end
'''
        main.execute_lines(source.splitlines())
        for expression in ['server.get("/a", "missing")', 'server.get("/a", "wrong")',
                           'server.get("a", "handler")', 'server.route("TRACE", "/a", "handler")']:
            with self.subTest(expression=expression), self.assertRaises(BSError):
                main.execute_lines([expression])
        main.execute_lines(['server.get("/a", "handler")'])
        with self.assertRaises(BSError):
            main.execute_lines(['server.get("/a", "handler")'])
        main.execute_lines(['app = server.app()'])
        with self.assertRaises(BSError) as raised:
            main.execute_lines(['server.get("/b", "handler")'])
        self.assertEqual(raised.exception.type, 'RuntimeError')

    def test_invalid_response_headers_and_status_are_catchable(self):
        main.execute_lines(['add server'])
        for expression in ['server.response({}, true)', 'server.response({}, 199)',
                           'server.response({}, 200, {"X-Test": "a\\nb"})',
                           'server.response({}, 200, {"Content-Length": "0"})',
                           'server.response({}, 200, {"bad name": "value"})',
                           'server.response({}, 200, {"X-Test": 1})']:
            with self.subTest(expression=expression), self.assertRaises(BSError):
                main.execute_lines([expression])

    def start(self, server):
        errors = []
        def run():
            try:
                server.run('127.0.0.1', 0)
            except Exception as error:
                errors.append(error)
        thread = threading.Thread(target=run, daemon=True)
        self.threads.append(thread)
        thread.start()
        deadline = time.monotonic() + 5
        while server.port() is None and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertEqual(errors, [])
        self.assertIsNotNone(server.port())
        return f'http://127.0.0.1:{server.port()}', thread

    def test_real_http_server_and_shutdown_route_flush_response(self):
        server, _ = self.configure('''func health(request):
    return {"ok": true}
end
func shutdown(request):
    server.stop()
    return "stopped"
end
server.get("/health", "health")
server.post("/shutdown", "shutdown")
''')
        url, thread = self.start(server)
        with urlopen(url + '/health', timeout=5) as response:
            self.assertEqual(response.read(), b'{"ok":true}')
        with urlopen(url + '/shutdown', data=b'', timeout=5) as response:
            self.assertEqual(response.read(), b'stopped')
        thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertIsNone(server.port())
        self.assertFalse(server.stop())

    def test_external_stop_restart_and_invalid_bind(self):
        server, _ = self.configure('''func health(request):
    return "ok"
end
server.get("/health", "health")
''')
        for _ in range(2):
            url, thread = self.start(server)
            with urlopen(url + '/health', timeout=5) as response:
                self.assertEqual(response.read(), b'ok')
            self.assertTrue(server.stop())
            thread.join(10)
            self.assertFalse(thread.is_alive())
        for host, port in [('localhost', 80), ('127.0.0.1', True), ('127.0.0.1', 65536)]:
            with self.subTest(host=host, port=port), self.assertRaises(ValueError):
                server.run(host, port)
        with patch('waitress.server.create_server', side_effect=OSError('bind failed')):
            with self.assertRaises(OSError):
                server.run('127.0.0.1', 0)
        self.assertFalse(server.running)
        self.assertIsNone(server.port())

    def test_missing_optional_backend_has_install_hint(self):
        import builtins
        original_import = builtins.__import__
        def without_backend(name, *args, **kwargs):
            if name.startswith('werkzeug'):
                raise ImportError('not installed')
            return original_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=without_backend):
            with self.assertRaises(BSError) as raised:
                main.execute_lines(['add server'])
        self.assertEqual(raised.exception.type, 'ImportError')
        self.assertIn('brittainscript[server]', raised.exception.message)
