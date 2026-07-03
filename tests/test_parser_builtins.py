import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
import parser


class NumericBuiltinTests(unittest.TestCase):
    def test_numeric_builtins_receive_the_value_not_argument_list(self):
        self.assertEqual(parser.call_function("floor", [3.9]), 3)
        self.assertEqual(parser.call_function("ceiling", [3.1]), 4)
        self.assertEqual(parser.call_function("round", [3.7]), 4)
        self.assertEqual(parser.call_function("absolute", [-8]), 8)
        self.assertIs(parser.call_function("type", [42]), int)

    def test_numeric_builtins_reject_wrong_arity(self):
        self.assertIsNone(parser.call_function("floor", []))
        self.assertIsNone(parser.call_function("floor", [1, 2]))


class ListMethodTests(unittest.TestCase):
    def test_pop_mutates_list(self):
        values = [1, 2, 3]
        parser.call_method(values, "pop", [])
        self.assertEqual(values, [1, 2])

    def test_remove_mutates_list(self):
        values = [1, 2, 3]
        parser.call_method(values, "remove", [2])
        self.assertEqual(values, [1, 3])

    def test_empty_pop_and_missing_remove_do_not_crash(self):
        self.assertIsNone(parser.call_method([], "pop", []))
        self.assertIsNone(parser.call_method([1], "remove", [2]))


if __name__ == "__main__":
    unittest.main()
