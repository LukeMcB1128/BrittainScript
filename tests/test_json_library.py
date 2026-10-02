import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import main
import parser
import json_backend
from core.diagnostics import BSError


class JsonLibraryTests(unittest.TestCase):
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

    def test_native_library_roundtrip_and_unicode(self):
        self.assertEqual(self.run_bs('''add json
data = {"name": "café", "items": [1, true, null, {"score": 2}]}
text = json.stringify(data)
copy = json.parse(text)
push(copy == data)
push(copy["items"][3]["score"])
push(text)
'''), 'True\n2\n{"name":"café","items":[1,true,null,{"score":2}]}\n')

    def test_scalar_values_and_aliases(self):
        self.assertEqual(self.run_bs('''add json
push(json.loads("null") == null)
push(json.dumps(true))
push(json.parse("42"))
'''), 'True\ntrue\n42\n')

    def test_pretty_output_and_utf8_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.json'
            parser.names['json_path'] = str(path)
            self.assertEqual(self.run_bs('''add json
data = {"name": "café"}
push(json.save(json_path, data))
push(json.load(json_path) == data)
push(json.pretty(data, 2))
'''), 'True\nTrue\n{\n  "name": "café"\n}\n')
            self.assertIn('café'.encode('utf-8'), path.read_bytes())

    def test_invalid_json_is_catchable_and_preserves_subclass(self):
        self.assertEqual(self.run_bs('''add json
try:
    json.parse("{")
catch ValueError as problem:
    push(problem.type)
end
'''), 'JSONDecodeError\n')

    def test_non_json_values_and_invalid_arguments_fail(self):
        for value in [float('nan'), float('inf'), {1: 'a'}, b'bytes', (1, 2)]:
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    json_backend.stringify(value)
        for text in ['NaN', 'Infinity', '-Infinity', '1e999', '{"x": 1,}']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                json_backend.parse(text)
        for indent in [-1, 1.5, True, '2']:
            with self.subTest(indent=indent), self.assertRaises(ValueError):
                json_backend.stringify({}, indent)
        with self.assertRaises(TypeError):
            json_backend.parse(42)

    def test_cycles_fail_but_shared_values_are_allowed(self):
        value = []
        value.append(value)
        with self.assertRaises(ValueError):
            json_backend.stringify(value)
        shared = [1]
        self.assertEqual(json_backend.parse(json_backend.stringify([shared, shared])), [[1], [1]])

    def test_invalid_save_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.json'
            path.write_text('original')
            with self.assertRaises(TypeError):
                json_backend.save(path, {1: 'invalid key'})
            self.assertEqual(path.read_text(), 'original')

    def test_file_errors_and_wrong_arity_are_catchable(self):
        for expression, kind in [('json.load("missing_json_test_file")', 'FileNotFoundError'),
                                 ('json.parse()', 'TypeError'), ('json.pretty({}, 0 - 1)', 'ValueError')]:
            with self.subTest(expression=expression):
                with self.assertRaises(BSError) as raised:
                    self.run_bs('add json\ndiscard ' + expression)
                self.assertEqual(raised.exception.type, kind)
