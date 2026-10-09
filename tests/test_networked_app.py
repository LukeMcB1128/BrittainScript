from concurrent.futures import ThreadPoolExecutor
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core'))
import main
import parser
import http_backend
import store_backend
from core.diagnostics import SourceLine

HAS_SERVER = all(importlib.util.find_spec(name) for name in ('werkzeug', 'waitress'))


@unittest.skipUnless(HAS_SERVER, 'Install the server extra to test the complete API')
class NetworkedAppTests(unittest.TestCase):
    def test_note_vault_concurrent_requests_statuses_persistence_and_restart(self):
        names, functions = dict(parser.names), dict(main.functions)
        parser.names.clear()
        main.functions.clear()
        server = None
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'notes.json'
            parser.names['test_store_path'] = str(path)
            source = (ROOT / 'examples/note_vault.bs').read_text().split('port = server.serve_background', 1)[0]
            source = source.replace('store.open("note_vault.json")', 'store.open(test_store_path)')
            try:
                main.execute_lines([SourceLine(line, 'note_vault.bs', index)
                                    for index, line in enumerate(source.splitlines(), 1)])
                server = parser.names['server']['funcs']['app']()
                port = server.serve_background('127.0.0.1', 0)
                url = f'http://127.0.0.1:{port}'
                def create(index):
                    return http_backend.request('POST', url + '/notes', {'text': f'café {index} ${{literal}}'})
                with ThreadPoolExecutor(max_workers=4) as executor:
                    responses = list(executor.map(create, range(8)))
                self.assertEqual([response['status'] for response in responses], [201] * 8)
                notes = http_backend.request('GET', url + '/notes')['json']
                self.assertEqual(sorted(note['id'] for note in notes), list(range(1, 9)))
                self.assertEqual(len({note['text'] for note in notes}), 8)
                self.assertEqual(parser.names['current_notes'], [])
                for payload in [{}, {'text': ''}, {'text': True}, [1]]:
                    with self.subTest(payload=payload):
                        self.assertEqual(http_backend.request('POST', url + '/notes', payload)['status'], 400)
                self.assertEqual(http_backend.request('DELETE', url + '/notes/999')['status'], 404)
                self.assertEqual(http_backend.request('DELETE', url + '/notes/1')['status'], 204)
                server.stop()
                self.assertTrue(server.wait(10))
                self.assertEqual(len(store_backend.Store(path, main).get('notes')), 7)
                port = server.serve_background('127.0.0.1', 0)
                self.assertEqual(len(http_backend.request('GET', f'http://127.0.0.1:{port}/notes')['json']), 7)
            finally:
                if server is not None:
                    server.stop()
                    server.wait(10)
                parser.names.clear()
                parser.names.update(names)
                main.functions.clear()
                main.functions.update(functions)
