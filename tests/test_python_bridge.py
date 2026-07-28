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


def call_capturing(function, *args):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        result = function(*args)
    return result, output.getvalue()


class PyimportTests(unittest.TestCase):
    def test_pyimport_returns_the_python_module(self):
        import math as python_math
        self.assertIs(parser.call_function("pyimport", ["math"]), python_math)

    def test_pyimport_works_from_a_script_expression(self):
        import json as python_json
        self.assertIs(evaluate('pyimport("json")'), python_json)

    def test_pyimport_reports_a_missing_module(self):
        result, output = call_capturing(parser.call_function, "pyimport", ["no_such_module_xyz"])
        self.assertIsNone(result)
        self.assertIn("cannot import 'no_such_module_xyz'", output)

    def test_pyimport_rejects_bad_arguments(self):
        for args in ([], [1], ["math", "json"]):
            result, output = call_capturing(parser.call_function, "pyimport", args)
            self.assertIsNone(result)
            self.assertIn("pyimport() expects one string argument", output)


class MethodFallbackTests(unittest.TestCase):
    def test_fallback_calls_a_python_method(self):
        self.assertEqual(parser.call_method("a,b,c", "split", [","]), ["a", "b", "c"])
        self.assertEqual(parser.call_method("hello", "count", ["l"]), 2)
        self.assertEqual(parser.call_method([3, 1, 2], "index", [2]), 2)

    def test_fallback_returns_a_non_callable_attribute(self):
        import decimal
        value = decimal.Decimal("1.5")
        self.assertEqual(parser.call_method(value, "real", []), value)

    def test_fallback_works_from_a_script_expression(self):
        self.assertEqual(evaluate('"a b".split(" ")'), ["a", "b"])

    def test_whitelisted_methods_still_win_over_the_fallback(self):
        # 'add' on a list appends in BrittainScript; Python lists have no add()
        values = [1, 2]
        self.assertIsNone(parser.call_method(values, "add", [3]))
        self.assertEqual(values, [1, 2, 3])
        # 'contains' and 'locate' are BrittainScript names, not Python ones
        self.assertIs(parser.call_method("hello", "contains", ["ell"]), True)
        self.assertEqual(parser.call_method("hello", "locate", ["l"]), 2)
        self.assertEqual(parser.call_method("  hi  ", "trim", []), "hi")
        self.assertEqual(parser.call_method("hi", "upper", []), "HI")

    def test_missing_method_reports_an_error(self):
        result, output = call_capturing(parser.call_method, "hello", "notamethod", [])
        self.assertIsNone(result)
        self.assertIn("no method 'notamethod' on str", output)

    def test_failing_python_call_reports_an_error(self):
        result, output = call_capturing(parser.call_method, "hello", "split", [1, 2, 3])
        self.assertIsNone(result)
        self.assertIn("Error calling 'split'", output)

    def test_module_methods_still_route_to_the_module_caller(self):
        module = {"__bs_module__": True, "name": "demo", "funcs": {}}
        calls = []
        previous = parser.module_caller
        parser.set_module_caller(lambda receiver, name, args: calls.append((name, args)))
        try:
            parser.call_method(module, "greet", ["world"])
        finally:
            parser.set_module_caller(previous)
        self.assertEqual(calls, [("greet", ["world"])])


class AttributeAccessTests(unittest.TestCase):
    def test_attribute_access_reads_a_python_attribute(self):
        self.assertEqual(evaluate('pyimport("math").pi'), 3.141592653589793)

    def test_attribute_access_on_a_value(self):
        parser.set_name("value", complex(3, 4))
        self.assertEqual(evaluate("value.imag"), 4.0)

    def test_method_call_syntax_is_unaffected_by_the_attribute_rule(self):
        self.assertEqual(evaluate('"hi".upper()'), "HI")
        self.assertEqual(evaluate('pyimport("math").floor(3.7)'), 3)

    def test_missing_attribute_reports_an_error(self):
        result, output = evaluate_capturing('"hello".notanattribute')
        self.assertIsNone(result)
        self.assertIn("no attribute 'notanattribute' on str", output)

    def test_module_members_must_be_called(self):
        parser.set_name("demo", {"__bs_module__": True, "name": "demo", "funcs": {}})
        result, output = evaluate_capturing("demo.greet")
        self.assertIsNone(result)
        self.assertIn("'demo' members must be called", output)


class MatrixMultiplyTests(unittest.TestCase):
    def test_matmul_uses_the_python_operator(self):
        class Recorder:
            def __matmul__(self, other):
                return ("matmul", other)

        parser.set_name("left", Recorder())
        parser.set_name("right", 7)
        self.assertEqual(evaluate("left @ right"), ("matmul", 7))

    def test_matmul_on_unsupported_types_reports_an_error(self):
        result, output = evaluate_capturing("2 @ 3")
        self.assertIsNone(result)
        self.assertIn("cannot matrix-multiply", output)

    def test_matmul_binds_like_multiplication(self):
        class Recorder:
            def __init__(self, tag):
                self.tag = tag

            def __matmul__(self, other):
                return Recorder(f"({self.tag}@{other.tag})")

            def __add__(self, other):
                return Recorder(f"({self.tag}+{other.tag})")

        parser.set_name("a", Recorder("a"))
        parser.set_name("b", Recorder("b"))
        parser.set_name("c", Recorder("c"))
        self.assertEqual(evaluate("a + b @ c").tag, "(a+(b@c))")
        self.assertEqual(evaluate("a @ b @ c").tag, "((a@b)@c)")


class NumpyBridgeTests(unittest.TestCase):
    def setUp(self):
        try:
            import numpy
        except ImportError:
            self.skipTest("numpy is not installed")

    def test_numpy_flows_through_the_bridge(self):
        source = 'pyimport("numpy").array([[1, 2], [3, 4]])'
        matrix = evaluate(source)
        parser.set_name("matrix", matrix)
        self.assertEqual(evaluate("matrix.shape"), (2, 2))
        self.assertEqual(evaluate("matrix.sum()"), 10)
        self.assertEqual(evaluate("matrix @ matrix").tolist(), [[7, 10], [15, 22]])
        self.assertEqual(evaluate("matrix * 2").tolist(), [[2, 4], [6, 8]])
        self.assertEqual(evaluate("matrix[0][1]"), 2)


class TorchBridgeTests(unittest.TestCase):
    def setUp(self):
        try:
            import torch
        except ImportError:
            self.skipTest("torch is not installed")

    def test_autograd_works_through_the_bridge(self):
        torch_module = evaluate('pyimport("torch")')
        parser.set_name("torch", torch_module)
        parser.set_name("weight", torch_module.ones(2, 2, requires_grad=True))
        self.assertEqual(evaluate("weight.shape")[0], 2)
        loss = evaluate("(weight * 3).sum()")
        parser.set_name("loss", loss)
        evaluate("loss.backward()")
        self.assertEqual(evaluate("weight.grad").tolist(), [[3.0, 3.0], [3.0, 3.0]])


if __name__ == "__main__":
    unittest.main()
