import contextlib
import io
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core'))
import main
import parser
import net_backend
from core.diagnostics import BSError


class BSTestCase(unittest.TestCase):
    def setUp(self):
        self.names = dict(parser.names)
        self.functions = dict(main.functions)

    def tearDown(self):
        parser.names.clear()
        parser.names.update(self.names)
        main.functions.clear()
        main.functions.update(self.functions)

    def run_bs(self, source):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.execute_lines(source.splitlines())
        return output.getvalue()


class NewBuiltinTests(BSTestCase):
    def test_chr_ord_and_invoke(self):
        self.assertEqual(self.run_bs('''func greet(name, mark):
    return "Hi " + name + mark
end
push(invoke("greet", ["Ada", chr(33)]))
push(ord("é"))
push(chr(233))
'''), 'Hi Ada!\n233\né\n')

    def test_invoke_reaches_user_functions_from_a_library(self):
        # ui.bs relies on this: a library calls the user's handler by name.
        self.assertEqual(self.run_bs('''add web
func handler(x):
    return x * 2
end
push(invoke("handler", [21]))
'''), '42\n')

    def test_invoke_prefers_user_functions_over_builtins(self):
        # A ui handler named "clear" used to run the terminal-clearing built-in.
        self.assertEqual(self.run_bs('''func clear(x):
    return "mine " + x
end
push(invoke("clear", ["ok"]))
push(invoke("len", ["abc"]))
'''), 'mine ok\n3\n')

    def test_bad_arguments_raise(self):
        for source in ('ord("ab")', 'chr("a")', 'invoke("f", 1)', 'invoke("missing_function_xyz", [])'):
            with self.subTest(source=source), self.assertRaises(BSError):
                self.run_bs(source)


class ParseCacheTests(BSTestCase):
    def test_cached_lines_evaluate_fresh_values(self):
        # Reused trees must still build new lists and dictionaries every run.
        self.assertEqual(self.run_bs('''func make(n):
    return [n, {"n": n}]
end
a = make(1)
a.add("extra")
a[1]["n"] = 99
b = make(2)
push(b)
for i in space(3):
    push(f"${i}:${i * i}")
end
'''), "[2, {'n': 2}]\n0:0\n1:1\n2:4\n")

    def test_syntax_errors_still_report_every_time(self):
        for _ in range(2):
            with self.assertRaises(BSError):
                self.run_bs('x = (1 +')


class NetPrimitiveTests(unittest.TestCase):
    def test_wait_skips_idle_connections_and_round_trips_bytes(self):
        server = net_backend.listen('127.0.0.1', 0)
        port = net_backend.port(server)
        idle = socket.create_connection(('127.0.0.1', port))
        active = socket.create_connection(('127.0.0.1', port))
        try:
            self.assertIsNone(net_backend.wait(server, 0.1))
            active.sendall('héllo'.encode('utf-8'))
            conn = net_backend.wait(server, 2)
            self.assertIsNotNone(conn)
            raw = net_backend.recv(conn, 100)
            self.assertEqual(len(raw), 6)
            self.assertEqual(net_backend.decode(raw), 'héllo')
            net_backend.send(conn, net_backend.encode('✓ ok'))
            net_backend.close(conn)
            self.assertEqual(active.recv(100).decode('utf-8'), '✓ ok')
        finally:
            idle.close()
            active.close()
            net_backend.close(server)

    def test_validation(self):
        with self.assertRaises(ValueError):
            net_backend.listen('127.0.0.1', 70000)
        with self.assertRaises(ValueError):
            net_backend.recv(123456, 10)
        with self.assertRaises(UnicodeEncodeError):
            server = net_backend.listen('127.0.0.1', 0)
            try:
                net_backend.send(server, '✓')
            finally:
                net_backend.close(server)
        with self.assertRaises(ValueError):
            net_backend.open_app('file:///etc/passwd')


class WebLibraryTests(BSTestCase):
    def request_in_background(self, port, *args):
        result = {}

        def run():
            try:
                with urlopen(Request(f'http://127.0.0.1:{port}' + args[0], *args[1:]), timeout=5) as response:
                    result['status'] = response.status
                    result['type'] = response.headers['Content-Type']
                    result['body'] = response.read().decode('utf-8')
            except HTTPError as error:
                result['status'] = error.code
                result['body'] = error.read().decode('utf-8')
        thread = threading.Thread(target=run)
        thread.start()
        return thread, result

    def test_request_parsing_and_json_reply(self):
        self.run_bs('add web\nserver = web.listen("127.0.0.1", 0)\nport = web.port(server)')
        thread, result = self.request_in_background(
            parser.names['port'], '/notes/caf%C3%A9?tag=a+b&x=%26', 'ünï'.encode('utf-8'),
            {'Content-Type': 'text/plain', 'X-Test': 'yes'})
        self.run_bs('''request = web.next(server, 5)
web.json(request, {"method": request["method"], "path": request["path"], "query": request["query"], "body": request["body"], "header": web.header(request, "X-Test")})
web.close(server)
''')
        thread.join(5)
        self.assertEqual(result['status'], 200)
        self.assertEqual(result['type'], 'application/json')
        self.assertEqual(json.loads(result['body']), {
            'method': 'POST', 'path': '/notes/café', 'query': {'tag': 'a b', 'x': '&'},
            'body': 'ünï', 'header': 'yes'})

    def test_serve_reports_handler_errors_as_500(self):
        self.run_bs('add web\nserver = web.listen("127.0.0.1", 0)\nport = web.port(server)')
        thread, result = self.request_in_background(parser.names['port'], '/boom')
        output = self.run_bs('''func handle(request):
    web.stop(server)
    raise error("broken", "Boom")
end
web.serve(server, "handle")
web.close(server)
''')
        thread.join(5)
        self.assertEqual(result['status'], 500)
        self.assertIn('Boom: broken', output)


class UiRenderingTests(BSTestCase):
    def setUp(self):
        super().setUp()
        self.run_bs('add ui')

    def bs_value(self, expression):
        self.run_bs('test_value = ' + expression)
        return parser.names['test_value']

    def test_html_escapes_text_and_attributes(self):
        html = self.bs_value('ui._uiHtml(ui._uiNorm(ui.el("div", {"title": "a\\"<b>", "hidden": true, "open": false}, ["x < y & z", ui.el("br", null, null), 5])))')
        self.assertEqual(html, '<div title="a&quot;&lt;b&gt;" hidden>x &lt; y &amp; z<br>5</div>')

    def test_normalize_merges_text_and_flattens_lists(self):
        tree = self.bs_value('ui._uiNorm(ui.row(["a", "", null, ["b", 1], ui.text("c"), "d"]))')
        self.assertEqual(tree['kids'][0], 'ab1')
        self.assertEqual(tree['kids'][1]['tag'], 'span')
        self.assertEqual(tree['kids'][2], 'd')

    def test_diff_produces_minimal_patches(self):
        self.run_bs('''old = ui._uiNorm(ui.col([ui.h1("Title"), ui.p("one"), ui.p("two"), ui.button("Go", "go")]))
new = ui._uiNorm(ui.col([ui.h2("Title"), ui.danger(ui.p("one")), ui.p("TWO"), ui.button("Go", "stop"), ui.p("added")]))
patches = []
ui._uiDiff(old, new, [0], patches)
shrunk = []
ui._uiDiff(new, ui._uiNorm(ui.col([ui.h2("Title")])), [0], shrunk)''')
        patches = parser.names['patches']
        self.assertEqual([patch['op'] for patch in patches], ['replace', 'attrs', 'text', 'attrs', 'append'])
        self.assertEqual(patches[0]['path'], [0, 0])
        self.assertEqual(patches[1]['set'], {'class': 'bs-p danger'})
        self.assertEqual(patches[2], {'op': 'text', 'path': [0, 2, 0], 'text': 'TWO'})
        self.assertEqual(patches[3]['set'], {'data-bs-click': 'stop'})
        self.assertEqual(patches[4]['html'], '<p class="bs-p">added</p>')
        self.assertEqual(parser.names['shrunk'], [{'op': 'trim', 'path': [0], 'count': 1}])

    def test_keys_replace_items_that_changed_identity(self):
        self.run_bs('''old = ui._uiNorm(ui.list([ui.key(ui.text("a"), 1), ui.key(ui.text("b"), 2)]))
new = ui._uiNorm(ui.list([ui.key(ui.text("b"), 2)]))
patches = []
ui._uiDiff(old, new, [0], patches)''')
        self.assertEqual([patch['op'] for patch in parser.names['patches']], ['replace', 'trim'])


class UiCanvasTests(BSTestCase):
    def setUp(self):
        super().setUp()
        self.run_bs('add ui')

    def bs_value(self, expression):
        self.run_bs('test_value = ' + expression)
        return parser.names['test_value']

    def test_canvas_renders_svg_shapes(self):
        html = self.bs_value('ui._uiHtml(ui._uiNorm(ui.onPoint(ui.canvas(200, 100, [ui.rounded(ui.rect(0, 0, 200, 100, "var(--surface)"), 8), ui.stroke(ui.circle(50, 50, 10, "red"), "blue", 3), ui.polyline([[0, 0], [10.256, 5]], "green"), ui.move(ui.drawText(100, 50, "a < b", "black"), 5, 0)]), "paint")))')
        self.assertTrue(html.startswith('<svg class="bs-canvas" viewBox="0 0 200 100" width="200" height="100" xmlns="http://www.w3.org/2000/svg" data-bs-point="paint">'))
        self.assertIn('<rect x="0" y="0" width="200" height="100" style="fill: var(--surface)" rx="8" ry="8"></rect>', html)
        self.assertIn('<circle cx="50" cy="50" r="10" style="fill: red; stroke: blue; stroke-width: 3"></circle>', html)
        self.assertIn('points="0,0 10.26,5"', html)
        self.assertIn('transform="translate(5 0)">a &lt; b</text>', html)

    def test_arc_paths(self):
        self.assertEqual(self.bs_value('ui.arc(80, 80, 66, 0, 90, "red")["attrs"]["d"]'), 'M 80 14 A 66 66 0 0 1 146 80')
        self.assertEqual(self.bs_value('ui.arc(80, 80, 66, 135, 360, "red")["attrs"]["d"]'), 'M 126.67 126.67 A 66 66 0 1 1 80 14')
        self.assertEqual(self.bs_value('ui.arc(80, 80, 66, 90, 90, "red")["attrs"]["d"]'), '')

    def test_canvas_point_handler_receives_coordinates(self):
        self.run_bs('''state = {"dots": []}
func view(s):
    return ui.onPoint(ui.canvas(100, 100, s["dots"]), "paint")
end
func paint(s, event):
    s["dots"].add(ui.circle(event["x"], event["y"], 4, "red"))
end
_ui["state"] = state
_ui["view"] = "view"
page = ui._uiDocument()
reply = ui._uiEvent("{\\"handler\\": \\"paint\\", \\"x\\": 12.5, \\"y\\": 40, \\"values\\": {}, \\"version\\": 1}")''')
        reply = json.loads(parser.names['reply'])
        self.assertEqual(reply['patches'], [{'op': 'append', 'path': [0], 'html': '<circle cx="12.5" cy="40" r="4" style="fill: red"></circle>'}])


class UiEventTests(BSTestCase):
    APP = '''add ui
state = {"draft": "", "items": [], "count": 0}
func view(s):
    return ui.page([ui.h1(f"${s["count"]} items"), ui.input("draft", "New"), ui.button("Add", "add"), ui.button("Fail", "fail"), ui.list(s["items"])])
end
func add(s, event):
    s["items"].add(s["draft"])
    s["count"] += 1
    s["draft"] = ""
    ui.toast("Added")
end
func fail(s, event):
    raise error("handler broke", "Broken")
end
func replace_state(s, event):
    return {"draft": "", "items": [], "count": 7}
end
_ui["state"] = state
_ui["view"] = "view"
page = ui._uiDocument()
'''

    def event(self, payload):
        self.output = self.run_bs('reply = ui._uiEvent(event_body)'.replace('event_body', json.dumps(json.dumps(payload))))
        return json.loads(parser.names['reply'])

    def test_document_contains_tree_theme_and_client(self):
        self.run_bs(self.APP)
        page = parser.names['page']
        self.assertIn('<div id="bs-root"><main class="bs-page"><h1>0 items</h1>', page)
        self.assertIn('data-bs-bind="draft"', page)
        self.assertIn('.bs-card{', page)
        self.assertIn('window.BS={"token":', page)

    def test_handler_updates_state_and_clears_the_bound_input(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.run_bs(self.APP)
        reply = self.event({'handler': 'add', 'values': {'draft': 'milk'}, 'version': 1})
        ops = {patch['op']: patch for patch in reply['patches']}
        self.assertEqual(reply['version'], 2)
        self.assertEqual(ops['text']['text'], '1 items')
        # The browser showed "milk"; the handler cleared it, so the value must be patched.
        self.assertEqual(ops['attrs']['set'], {'data-bs-value': ''})
        self.assertIn('<li>milk</li>', ops['append']['html'])
        self.assertEqual(ops['toast']['text'], 'Added')
        self.assertEqual(parser.names['state']['items'], ['milk'])

    def test_typed_text_is_not_patched_back(self):
        self.run_bs(self.APP)
        reply = self.event({'handler': '', 'values': {'draft': 'half typed'}, 'version': 1})
        self.assertEqual(reply['patches'], [])
        self.assertEqual(parser.names['state']['draft'], 'half typed')

    def test_errors_unknown_handlers_and_stale_versions(self):
        self.run_bs(self.APP)
        failed = self.event({'handler': 'fail', 'values': {}, 'version': 1})
        self.assertIn('Broken: handler broke', self.output)
        unknown = self.event({'handler': 'replace_state', 'values': {}, 'version': 2})
        stale = self.event({'handler': '', 'values': {}, 'version': 1})
        self.assertEqual(failed['patches'], [{'op': 'toast', 'text': 'Broken: handler broke', 'kind': 'error'}])
        # replace_state exists but is not on screen, so the window cannot call it.
        self.assertEqual(unknown['patches'][0]['kind'], 'error')
        self.assertEqual(parser.names['_ui']['state']['count'], 0)
        self.assertEqual(stale['patches'][0]['op'], 'replace')
        self.assertEqual(stale['patches'][0]['path'], [0])


class UiAppProcessTests(unittest.TestCase):
    def test_app_serves_events_and_exits_when_the_window_closes(self):
        script = '''add ui
func view(s):
    return ui.page([ui.h1(f"Count ${s["n"]}"), ui.button("Add", "bump")])
end
func bump(s, event):
    s["n"] += 1
end
final = ui.app("Test App", {"n": 0}, "view")
push(f"final ${final["n"]}")
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'app.bs'
            path.write_text(script)
            env = dict(os.environ, BS_UI_BROWSER='none', PYTHONUNBUFFERED='1')
            process = subprocess.Popen([sys.executable, str(ROOT / 'run.py'), str(path)], env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            try:
                line = process.stdout.readline()
                url = re.search(r'http://127\.0\.0\.1:\d+/', line).group(0)
                with urlopen(url, timeout=5) as response:
                    page = response.read().decode('utf-8')
                token = re.search(r'"token":"([0-9a-f]+)"', page).group(1)
                self.assertIn('<h1>Count 0</h1>', page)
                body = json.dumps({'handler': 'bump', 'values': {}, 'version': 1}).encode()
                with urlopen(Request(url + 'bs/event', body, {'X-BS-Token': token}), timeout=5) as response:
                    reply = json.loads(response.read())
                self.assertEqual(reply['patches'], [{'op': 'text', 'path': [0, 0, 0], 'text': 'Count 1'}])
                with self.assertRaises(HTTPError) as forbidden:
                    urlopen(Request(url + 'bs/event', body), timeout=5)
                self.assertEqual(forbidden.exception.code, 403)
                with self.assertRaises(HTTPError) as rebound:
                    urlopen(Request(url, headers={'Host': 'evil.example:80'}), timeout=5)
                self.assertEqual(rebound.exception.code, 403)
                urlopen(Request(url + 'bs/bye?t=' + token, b''), timeout=5).close()
                output, _ = process.communicate(timeout=10)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        self.assertEqual(process.returncode, 0)
        self.assertIn('final 1', output)


if __name__ == '__main__':
    unittest.main()
