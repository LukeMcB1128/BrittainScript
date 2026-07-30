import datetime as py_datetime
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
import parser
import main


class DatetimeBuiltinTests(unittest.TestCase):
    def test_now_returns_a_datetime(self):
        value = parser.call_function("datetime", ["now"])
        self.assertIsInstance(value, py_datetime.datetime)

    def test_parse_format_roundtrip_and_parts(self):
        parsed = parser.call_function("datetime", ["parse", "2024-02-29 13:05:07", "%Y-%m-%d %H:%M:%S"])
        self.assertEqual(parser.call_function("datetime", ["year", parsed]), 2024)
        self.assertEqual(parser.call_function("datetime", ["month", parsed]), 2)
        self.assertEqual(parser.call_function("datetime", ["day", parsed]), 29)
        self.assertEqual(parser.call_function("datetime", ["hour", parsed]), 13)
        self.assertEqual(parser.call_function("datetime", ["minute", parsed]), 5)
        self.assertEqual(parser.call_function("datetime", ["second", parsed]), 7)
        self.assertEqual(parser.call_function("datetime", ["weekday", parsed]), 3)
        self.assertEqual(parser.call_function("datetime", ["format", parsed, "%Y-%m-%d"]), "2024-02-29")

    def test_calendar_helpers(self):
        self.assertTrue(parser.call_function("datetime", ["isLeapYear", 2024]))
        self.assertFalse(parser.call_function("datetime", ["isLeapYear", 2023]))
        self.assertEqual(parser.call_function("datetime", ["daysInMonth", 2024, 2]), 29)
        self.assertEqual(parser.call_function("datetime", ["daysInMonth", 2023, 2]), 28)

    def test_bad_input_returns_none_instead_of_raising(self):
        self.assertIsNone(parser.call_function("datetime", ["parse", "junk", "%Y-%m-%d"]))
        self.assertIsNone(parser.call_function("datetime", ["daysInMonth", 2024, 13]))
        self.assertIsNone(parser.call_function("datetime", ["year", "not a date"]))
        self.assertIsNone(parser.call_function("datetime", ["isLeapYear", "not a year"]))

    def test_unknown_command_and_wrong_arity(self):
        self.assertIsNone(parser.call_function("datetime", []))
        self.assertIsNone(parser.call_function("datetime", ["frobnicate"]))
        self.assertIsNone(parser.call_function("datetime", ["year"]))
        self.assertIsNone(parser.call_function("datetime", ["now", "extra"]))

    def test_datetime_module_imports_with_expected_functions(self):
        module = main.import_module("datetime")
        self.assertIsNotNone(module)
        for name in ("now", "format", "parse", "year", "month", "day", "hour",
                     "minute", "second", "weekday", "isLeapYear", "daysInMonth"):
            self.assertIn(name, module["funcs"])


if __name__ == "__main__":
    unittest.main()
