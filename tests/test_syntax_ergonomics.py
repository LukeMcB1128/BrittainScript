import contextlib
import io
from pathlib import Path
import sys
import textwrap
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import main
import parser
from core.diagnostics import BSError, SourceLine


class SyntaxErgonomicsTests(unittest.TestCase):
    def setUp(self):
        self.names, self.functions = dict(parser.names), dict(main.functions)

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

    def test_if_alias_with_nested_cond_elif_else_and_parentheses(self):
        self.assertEqual(self.run_bs('''
            if (true):
                cond false:
                    push("wrong")
                elif true:
                    if true:
                        push("nested")
                    end
                else:
                    push("wrong")
                end
            else:
                push("wrong")
            end
            if false:
                push("wrong")
            elif true:
                push("elif")
            end
        '''), 'nested\nelif\n')

    def test_repl_collects_if_blocks(self):
        output = io.StringIO()
        with patch('builtins.input', side_effect=['if true:', 'push("yes")', 'end', 'exit']), contextlib.redirect_stdout(output):
            main.run_repl()
        self.assertIn('yes\n', output.getvalue())

    def test_interpolation_uses_bs_expressions_and_tostr_values(self):
        self.assertEqual(self.run_bs('''
            data = {"name": "café", "id": 7}
            push(f"Added ${data["name"]} ${data["id"] + 1}.")
            push(f"${true}, ${false}, ${null}")
            push("Literal ${data}")
            push(f"${{\"a\": [1, 2]}[\"a\"][1]}")
        '''), 'Added café 8.\nTrue, False, null\nLiteral ${data}\n2\n')

    def test_escapes_hashes_equals_unicode_and_nested_templates(self):
        source = r'''
            data = {"#=": "日本語"}
            push(f"value=${data["#="]} # kept") # removed
            push(f"literal \${unknown} and tab\t✓")
            push(f"${f"inner ${2}"}")
        '''
        self.assertEqual(self.run_bs(source), 'value=日本語 # kept\nliteral ${unknown} and tab\t✓\ninner 2\n')

    def test_expression_effects_run_in_order_and_short_circuit_skips_them(self):
        effects = []
        parser.names['effect'] = lambda value: effects.append(value) or value
        self.assertEqual(self.run_bs('''push(f"${effect(1)} ${effect(2)}")
discard true or f"${effect(3)}"
'''), '1 2\n')
        self.assertEqual(effects, [1, 2])

    def test_invalid_interpolation_and_keywords_fail_before_any_effect(self):
        effects = []
        original_value = parser.names.get('value', parser.UNBOUND)
        parser.names['effect'] = lambda: effects.append('ran')
        for source in ['push(effect(), f"${}")', 'push(f"${effect()} ${1 + }")',
                       'push(f"${effect()} ${effect(method=1)}")',
                       'push(f"${value = 1}")', 'push(f"${[1)}")', 'push(f"unclosed)']:
            with self.subTest(source=source), self.assertRaises(BSError):
                main.execute_lines([source])
        self.assertEqual(effects, [])
        self.assertIs(parser.names.get('value', parser.UNBOUND), original_value)

    def test_interpolation_error_has_outer_file_and_field_column(self):
        source = SourceLine('push(f"value ${1 / 0}")', 'interpolation.bs', 12)
        with self.assertRaises(BSError) as raised:
            main.execute_lines([source])
        self.assertEqual(raised.exception.file, 'interpolation.bs')
        self.assertEqual(raised.exception.line, 12)
        self.assertEqual(raised.exception.type, 'ZeroDivisionError')
        self.assertEqual(raised.exception.column, str(source).index('/') + 1)

    def test_low_level_parser_diagnostics_do_not_run_invalid_template_calls(self):
        effects = []
        original_value = parser.names.get('value', parser.UNBOUND)
        parser.names['effect'] = lambda *args: effects.append('ran')
        import lexer
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            for source in ['effect(f"${value = 1}")', 'effect(f"${effect(method=1)}")']:
                self.assertIsNone(parser.parser.parse(source, lexer=lexer.lexer.clone()))
        self.assertEqual(effects, [])
        self.assertIs(parser.names.get('value', parser.UNBOUND), original_value)
        self.assertIn('Assignments are not allowed', output.getvalue())
        self.assertIn('Keyword arguments', output.getvalue())
