import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import main
import parser
import http_backend
from core.diagnostics import BSError


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self):
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/echo')
            self.end_headers()
            return
        status = 404 if self.path == '/missing' else 200
        body = self.rfile.read(int(self.headers.get('Content-Length', 0))).decode('utf-8')
        value = {'method': self.command, 'body': body, 'content_type': self.headers.get('Content-Type'),
                 'test_header': self.headers.get('X-Test')}
        encoded = b'{' if self.path == '/invalid-json' else json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(encoded)))
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(encoded)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = respond


class HttpClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(5)

    def test_methods_json_utf8_headers_and_error_status(self):
        for method in http_backend.METHODS:
            with self.subTest(method=method):
                response = http_backend.request(method, self.url + '/echo', {'name': 'café'}, {'X-Test': 'yes'})
                self.assertEqual(response['status'], 200)
                if method == 'HEAD':
                    self.assertEqual(response['body'], '')
                    continue
                self.assertEqual(response['json']['method'], method)
                self.assertEqual(json.loads(response['json']['body']), {'name': 'café'})
                self.assertEqual(response['json']['test_header'], 'yes')
                self.assertEqual(response['json']['content_type'], 'application/json')
        response = http_backend.request('GET', self.url + '/missing')
        self.assertEqual(response['status'], 404)
        self.assertEqual(response['json']['method'], 'GET')

    def test_redirect_invalid_json_and_text_body(self):
        response = http_backend.request('GET', self.url + '/redirect')
        self.assertTrue(response['url'].endswith('/echo'))
        self.assertEqual(response['status'], 200)
        malformed = http_backend.request('GET', self.url + '/invalid-json')
        self.assertIsNone(malformed['json'])
        self.assertIsNotNone(malformed['json_error'])
        self.assertEqual(malformed['body'], '{')
        text = http_backend.request('POST', self.url + '/echo', 'hello')
        self.assertEqual(text['json']['body'], 'hello')
        self.assertEqual(text['json']['content_type'], 'text/plain; charset=utf-8')

    def test_bs_library_and_delete_status(self):
        names, functions = dict(parser.names), dict(main.functions)
        parser.names['base_url'] = self.url
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                main.execute_lines('''add http
created = http.post(base_url + "/echo", {"note": "café"})
push(created["status"])
push(created["json"]["method"])
deleted = http.delete(base_url + "/missing")
push(deleted["status"])
push(deleted["json"]["method"])
'''.splitlines())
            self.assertEqual(output.getvalue(), '200\nPOST\n404\nDELETE\n')
        finally:
            parser.names.clear()
            parser.names.update(names)
            main.functions.clear()
            main.functions.update(functions)

    def test_transport_failure_timeout_and_response_limit(self):
        with patch('http_backend.urlopen', side_effect=URLError('not connected')):
            with self.assertRaises(URLError):
                http_backend.request('GET', self.url)
        with patch('http_backend.urlopen', side_effect=TimeoutError('timeout')):
            with self.assertRaises(TimeoutError):
                http_backend.request('GET', self.url)
        with patch.object(http_backend, 'MAX_RESPONSE_SIZE', 2):
            with self.assertRaises(ValueError):
                http_backend.request('GET', self.url + '/echo')

    def test_invalid_input_rejected_before_open(self):
        cases = [('GET', 'file:///tmp/data'), ('TRACE', self.url),
                 ('GET', self.url, None, {'X-Test': 'a\nb'}),
                 ('GET', self.url, None, {'Content-Length': '9'}),
                 ('GET', self.url, None, {}, 0), ('GET', self.url, None, {}, True),
                 ('GET', self.url, None, {}, float('inf'))]
        with patch('http_backend.urlopen') as opened:
            for args in cases:
                with self.subTest(args=args), self.assertRaises((TypeError, ValueError)):
                    http_backend.request(*args)
            opened.assert_not_called()
