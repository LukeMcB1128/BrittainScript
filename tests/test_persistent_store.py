from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'core'))
import main
import parser
import store_backend
from core.diagnostics import BSError


class PersistentStoreTests(unittest.TestCase):
    def setUp(self):
        self.names, self.functions = dict(parser.names), dict(main.functions)
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'vault.json'

    def tearDown(self):
        parser.names.clear()
        parser.names.update(self.names)
        main.functions.clear()
        main.functions.update(self.functions)
        self.directory.cleanup()
        self.assertEqual(len(parser.scopes), 1)

    def test_create_persist_reopen_and_get_returns_separate_data(self):
        store = store_backend.Store(self.path, main)
        self.assertEqual(store.snapshot(), {})
        self.assertTrue(store.set('notes', [{'name': 'café'}]))
        returned = store.get('notes')
        returned.append('local only')
        reopened = store_backend.Store(self.path, main)
        self.assertEqual(reopened.get('notes'), [{'name': 'café'}])
        self.assertEqual(reopened.keys(), ['notes'])
        self.assertTrue(reopened.has('notes'))
        self.assertTrue(reopened.delete('notes'))
        self.assertFalse(reopened.delete('notes'))
        self.assertEqual(store.get('notes', []), [])

    def test_bs_transaction_updates_multiple_keys_and_extra_arguments(self):
        parser.names['store_path'] = str(self.path)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.execute_lines('''add store
vault = store.open(store_path)
func add_note(data, text):
    id = data.get("next_id", 1)
    notes = data.get("notes", [])
    notes.append({"id": id, "text": text})
    data["notes"] = notes
    data["next_id"] = id + 1
    return data
end
vault.transaction("add_note", ["café"])
push(vault.get("notes")[0]["text"])
push(vault.get("next_id"))
'''.splitlines())
        self.assertEqual(output.getvalue(), 'café\n2\n')

    def test_concurrent_handles_and_callbacks_do_not_lose_updates(self):
        main.execute_lines(['func increment(value):', '    return value + 1', 'end'])
        handles = [store_backend.Store(self.path, main) for _ in range(4)]
        def increment(handle):
            for _ in range(20):
                handle.update('count', 'increment', 0)
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(increment, handles))
        self.assertEqual(handles[0].get('count'), 80)

    def test_processes_share_file_lock_for_complete_updates(self):
        store_backend.Store(self.path, main).set('count', 0)
        source = '''import sys
sys.path.insert(0, sys.argv[1])
import main, parser
parser.names['path'] = sys.argv[2]
main.execute_lines(['add store', 'vault = store.open(path)',
                    'func increment(value):', '    return value + 1', 'end'])
for _ in range(20):
    main.execute_lines(['vault.update("count", "increment", 0)'])
'''
        processes = [subprocess.Popen([sys.executable, '-c', source, str(ROOT / 'core'), str(self.path)],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(2)]
        try:
            for process in processes:
                out, err = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, (out, err))
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                    process.communicate()
        self.assertEqual(store_backend.Store(self.path, main).get('count'), 40)

    def test_failed_callback_validation_and_replace_preserve_previous_data(self):
        store = store_backend.Store(self.path, main)
        store.set('value', [1])
        main.execute_lines(['func fail(value):', '    value.append(2)', '    raise "failed"', 'end'])
        original = self.path.read_bytes()
        with self.assertRaises(BSError):
            store.update('value', 'fail')
        self.assertEqual(self.path.read_bytes(), original)
        for value in [{1: 'bad key'}, float('nan')]:
            with self.subTest(value=value), self.assertRaises((TypeError, ValueError)):
                store.set('value', value)
        with patch('store_backend.os.replace', side_effect=OSError('replace failed')):
            with self.assertRaises(OSError):
                store.set('value', [2])
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])

    def test_corrupt_store_and_nested_store_calls_raise(self):
        for text in ['[]', '{']:
            self.path.write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError):
                store_backend.Store(self.path, main)
        self.path.unlink()
        parser.names['vault'] = store_backend.Store(self.path, main)
        main.execute_lines(['func nested(value):', '    return vault.get("count", 0)', 'end'])
        with self.assertRaises(BSError) as raised:
            parser.names['vault'].update('count', 'nested', 0)
        self.assertEqual(raised.exception.type, 'RuntimeError')
        self.assertEqual(parser.names['vault'].snapshot(), {})
