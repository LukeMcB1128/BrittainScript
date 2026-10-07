import contextlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import main
import parser
from core.diagnostics import BSError, from_python


class AppCorrectnessTests(unittest.TestCase):
    def setUp(self):
        self.names = dict(parser.names)
        self.functions = dict(main.functions)

    def tearDown(self):
        parser.names.clear()
        parser.names.update(self.names)
        main.functions.clear()
        main.functions.update(self.functions)

    def test_keyword_error_precedes_all_argument_and_receiver_effects(self):
        effects = []
        parser.names['effect'] = lambda: effects.append('ran')
        for source in ['effect(method=effect())', 'effect().call(effect(), method="DELETE")',
                       'discard true or effect(method="DELETE")',
                       'push([effect(method="DELETE")])']:
            with self.subTest(source=source), self.assertRaises(BSError) as raised:
                main.execute_lines([source])
            self.assertEqual(raised.exception.type, 'TypeError')
            self.assertIn('Keyword arguments', raised.exception.message)
        self.assertEqual(effects, [])
        self.assertNotIn('method', parser.names)

    def test_keyword_error_can_be_caught_and_positional_calls_work(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.execute_lines('''urllib = pyimport("urllib.request")
try:
    request = urllib.Request("http://example.invalid", method="DELETE")
catch TypeError:
    push("caught")
end
request = urllib.Request("http://example.invalid", null, {}, null, false, "DELETE")
push(request.get_method())
'''.splitlines())
        self.assertEqual(output.getvalue(), 'caught\nDELETE\n')

    def test_exception_fields_and_original_args_survive(self):
        from urllib.error import HTTPError
        original = HTTPError('http://example.invalid', 405, 'wrong method', {}, None)
        error = from_python(original)
        self.assertEqual(error.code, 405)
        self.assertIs(error.headers, original.headers)
        self.assertEqual(error.args, original.args)
        self.assertIs(error.cause, original)
        missing = from_python(FileNotFoundError(2, 'missing', 'file.json'))
        self.assertEqual(missing.errno, 2)
        self.assertEqual(missing.filename, 'file.json')
        with self.assertRaises(AttributeError):
            getattr(missing, 'unknown_attribute')
        output = io.StringIO()
        parser.names['original'] = original
        with contextlib.redirect_stdout(output):
            main.execute_lines('''try:
    raise original
catch HTTPError as problem:
    push(problem.code)
    push(problem.type)
end
'''.splitlines())
        self.assertEqual(output.getvalue(), '405\nHTTPError\n')

    def test_scripts_and_function_bodies_are_quiet_but_effects_run(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.execute_lines('''items = []
func action():
    items.append(1)
    true
    return true
end
action()
42
push(len(items))
'''.splitlines())
        self.assertEqual(output.getvalue(), '1\n')

    def test_repl_echoes_results_but_function_bodies_stay_quiet(self):
        main.execute_lines(['func value():', '    true', '    return 7', 'end'])
        output = io.StringIO()
        with patch('builtins.input', side_effect=['value()', 'discard value()', 'exit']), contextlib.redirect_stdout(output):
            main.run_repl()
        self.assertEqual(output.getvalue().splitlines(), ["BrittainScript — type 'exit' to quit", '7'])
