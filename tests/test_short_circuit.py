import contextlib
import io
from pathlib import Path
import sys
import textwrap
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import main
import parser
from core.diagnostics import BSError
from py2bs import translate


class ShortCircuitTests(unittest.TestCase):
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
            main.execute_lines(textwrap.dedent(source).strip().splitlines())
        return output.getvalue()

    def test_skipped_names_indexes_calls_and_errors(self):
        self.assertEqual(self.run_bs('''
            push(false and missing_name)
            push(true or [][9])
            push(false and missing_function())
            push(true or 1 / 0)
            push(false and {[]: 1})
            push(true or pyimport("missing_module"))
        '''), 'False\nTrue\nFalse\nTrue\nFalse\nTrue\n')

    def test_required_operands_run_once_and_in_order(self):
        self.assertEqual(self.run_bs('''
            func mark(value):
                push(value)
                return value
            end
            push(mark(true) and mark(false) and mark(true))
            push(mark(false) or mark(true) or mark(false))
        '''), 'True\nFalse\nFalse\nFalse\nTrue\nTrue\n')

    def test_precedence_groups_and_boolean_result(self):
        self.assertEqual(self.run_bs('''
            push(true or false and missing_name)
            push(not (false and missing_name))
            push(0 or "present")
            push("present" and 3)
            push((false or true) and true)
        '''), 'True\nTrue\nTrue\nTrue\nTrue\n')

    def test_safe_null_and_key_guards(self):
        self.assertEqual(self.run_bs('''
            data = null
            push(data != null and data["field"] == 1)
            data = {}
            push(data.has("field") and data["field"] == 1)
        '''), 'False\nFalse\n')

    def test_required_right_operand_still_raises(self):
        for source in ('discard true and 1 / 0', 'discard false or 1 / 0'):
            with self.subTest(source=source):
                with self.assertRaises(BSError) as raised:
                    self.run_bs(source)
                self.assertEqual(raised.exception.type, 'ZeroDivisionError')

    def test_entire_expression_is_parsed_before_any_effect(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(BSError):
            main.execute_lines(['discard push("unreachable") + )'])
        self.assertEqual(output.getvalue(), '')
        with self.assertRaises(BSError):
            self.run_bs('discard true or (1 + )')

    def test_dictionary_entries_evaluate_in_order_and_stop_at_invalid_key(self):
        self.assertEqual(self.run_bs('''
            func key():
                push("key")
                return "a"
            end
            func value():
                push("value")
                return 1
            end
            data = {key(): value()}
            try:
                data = {[]: 1, "later": value()}
            catch TypeError:
                push("invalid key")
            end
        '''), 'key\nvalue\ninvalid key\n')

    def test_translation_of_guards_matches_python(self):
        result = translate('''xs = []
print(len(xs) > 0 and xs[0] > 1)
print(True or 1 / 0 > 0)
''')
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.bs_stdout, 'False\nTrue\n')
