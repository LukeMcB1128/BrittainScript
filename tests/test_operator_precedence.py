import io
import contextlib
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
import lexer as lexer_module
import parser


def evaluate(source):
    return parser.parser.parse(source, lexer=lexer_module.lexer.clone())


def evaluate_capturing(source):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = evaluate(source)
    return result, output.getvalue()


class ModuloPrecedenceTests(unittest.TestCase):
    def test_modulo_binds_tighter_than_comparison(self):
        self.assertIs(evaluate("7 % 3 == 1"), True)
        self.assertIs(evaluate("7 % 3 != 1"), False)
        self.assertIs(evaluate("10 % 4 > 1"), True)

    def test_modulo_binds_tighter_than_addition(self):
        self.assertEqual(evaluate("10 % 4 + 1"), 3)
        self.assertEqual(evaluate("1 + 10 % 4"), 3)

    def test_modulo_is_left_associative_with_the_other_products(self):
        self.assertEqual(evaluate("10 % 4 * 2"), 4)
        self.assertEqual(evaluate("2 * 10 % 4"), 0)

    def test_modulo_by_zero_reports_an_error(self):
        result, output = evaluate_capturing("10 % 0")
        self.assertIsNone(result)
        self.assertIn("modulo by zero", output)


class ArithmeticPrecedenceTests(unittest.TestCase):
    def test_products_bind_tighter_than_sums(self):
        self.assertEqual(evaluate("2 + 3 * 4"), 14)
        self.assertEqual(evaluate("2 * 3 + 4"), 10)
        self.assertEqual(evaluate("8 / 4 + 1"), 3.0)

    def test_grouping_overrides_precedence(self):
        self.assertEqual(evaluate("(2 + 3) * 4"), 20)

    def test_division_by_zero_reports_an_error(self):
        result, output = evaluate_capturing("10 / 0")
        self.assertIsNone(result)
        self.assertIn("division by zero", output)


if __name__ == "__main__":
    unittest.main()
