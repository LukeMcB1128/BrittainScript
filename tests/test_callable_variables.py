import io
import contextlib
import textwrap
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
import main
import parser


def run(source):
    output = io.StringIO()
    lines = textwrap.dedent(source).strip("\n").split("\n")
    with contextlib.redirect_stdout(output):
        main.execute_lines([line + "\n" for line in lines])
    return output.getvalue().strip().split("\n") if output.getvalue().strip() else []


class CallableVariableTests(unittest.TestCase):
    def setUp(self):
        self.saved_functions = dict(main.functions)
        self.saved_names = dict(parser.names)

    def tearDown(self):
        main.functions.clear()
        main.functions.update(self.saved_functions)
        parser.names.clear()
        parser.names.update(self.saved_names)

    def test_a_python_function_in_a_variable_can_be_called(self):
        self.assertEqual(run('sqrt = pyimport("math").sqrt\npush(sqrt(9))'), ["3.0"])

    def test_arguments_are_passed_through(self):
        self.assertEqual(
            run('dumps = pyimport("json").dumps\npush(dumps([1, 2]))'), ["[1, 2]"]
        )

    def test_a_defined_function_takes_priority_over_a_variable(self):
        self.assertEqual(run("""
            func label(n):
                return "func " + n
            end
            label = pyimport("math").sqrt
            push(label("x"))
        """), ["func x"])

    def test_a_non_callable_variable_reports_an_error(self):
        self.assertEqual(run("value = 5\npush(value(1))"), ["Error: 'value' is not callable", "null"])

    def test_an_unknown_name_still_reports_undefined(self):
        self.assertEqual(run("push(nosuchthing(1))"), ["Undefined function: nosuchthing", "null"])

    def test_a_failing_call_reports_the_error(self):
        output = run('sqrt = pyimport("math").sqrt\npush(sqrt("text"))')
        self.assertTrue(output[0].startswith("Error calling 'sqrt'"), output)

    def test_builtins_are_unaffected(self):
        self.assertEqual(run("push(len([1, 2, 3]))"), ["3"])
        self.assertEqual(run("push(absolute(0 - 4))"), ["4"])

    def test_user_functions_are_unaffected(self):
        self.assertEqual(run("""
            func double(n):
                return n * 2
            end
            push(double(4))
        """), ["8"])


if __name__ == "__main__":
    unittest.main()
