"""Checks for the defects found in the repository review."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import main
import parser

from py2bs import translate
from py2bs.frontend import module_is_available, survey_features
from py2bs.verify import compare, run_brittainscript


class TranslationRegressionTests(unittest.TestCase):
    def assertMatches(self, source, expected):
        result = translate(textwrap.dedent(source).strip() + '\n')
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.python_stdout, expected)
        self.assertEqual(result.bs_stdout, expected)

    def test_called_function_does_not_change_caller_locals(self):
        self.assertMatches('''
            def inner():
                x = 2
            def outer():
                x = 1
                inner()
                return x
            print(outer())
        ''', '1\n')

    def test_recursive_calls_have_independent_locals(self):
        self.assertMatches('''
            def total(n):
                acc = n
                if n > 0:
                    result = total(n - 1)
                    return acc + result
                return acc
            print(total(3))
        ''', '6\n')

    def test_global_reads_do_not_use_caller_locals(self):
        self.assertMatches('''
            x = 10
            def inner():
                return x
            def outer():
                x = 1
                return inner()
            print(outer())
            print(x)
        ''', '10\n10\n')

    def test_conditional_module_bindings_do_not_change_function_locals(self):
        self.assertMatches('''
            if True:
                x = 10
            def f():
                x = 2
                return x
            print(f())
            print(x)
        ''', '2\n10\n')

    def test_local_import_does_not_replace_module_import(self):
        self.assertMatches('''
            import math as module
            def f():
                import json as module
                return module.dumps([1])
            print(f())
            print(module.sqrt(9))
        ''', '[1]\n3.0\n')

    def test_augmented_target_is_evaluated_once_before_rhs(self):
        self.assertMatches('''
            xs = [10]
            def index():
                print("index")
                return 0
            def value():
                print("value")
                return 1
            xs[index()] += value()
            print(xs)
        ''', 'index\nvalue\n[11]\n')

    def test_augmented_assignment_preserves_list_aliases(self):
        self.assertMatches('''
            a = [1]
            b = a
            a += [2]
            print(b)
            xs = [[1]]
            alias = xs[0]
            xs[0] += [2]
            print(alias)
        ''', '[1, 2]\n[1, 2]\n')

    def test_unused_results_are_discarded_but_effects_run(self):
        self.assertMatches('''
            def f():
                print("called")
                return 7
            f()
            1 + 2
            "docstring"
            print("done")
        ''', 'called\ndone\n')

    def test_exponent_literals_round_trip(self):
        self.assertMatches('print(1e-7)\nprint(1e20)\nprint(-2e-7)',
                           '1e-07\n1e+20\n-2e-07\n')

    def test_floor_division_preserves_integer_precision_and_float_type(self):
        large_integer = str(10 ** 400)
        self.assertMatches('print(9007199254740993 // 1)\n'
                           f'print({large_integer} // 1)',
                           '9007199254740993\n' + large_integer + '\n')
        self.assertMatches('''
            print(-7 // 3)
            print(7 // -3)
            print(3.5 // 2)
            n = 9007199254740993
            n //= 1
            print(n)
        ''', '-3\n-3\n1.0\n9007199254740993\n')

    def test_slice_and_nested_index_assignments(self):
        self.assertMatches('''
            xs = [1, 2, 3]
            xs[1:2] = [9]
            xs[:1] = [8]
            xs[2:] = [7]
            print(xs)
            rows = [[1, 2], [3, 4]]
            rows[0][1] = 9
            rows[1][:] = [5]
            print(rows)
        ''', '[8, 9, 7]\n[[1, 9], [5]]\n')

    def test_slice_target_bounds_run_once(self):
        self.assertMatches('''
            xs = [1, 2, 3]
            def bound():
                print("bound")
                return 1
            xs[bound():2] += [9]
            print(xs)
        ''', 'bound\n[1, 2, 9, 3]\n')

    def test_diagnostic_prefixes_in_user_output_are_valid(self):
        self.assertMatches('''
            print("Error: user message")
            print("Syntax error example")
            print("Undefined value example")
            print("Illegal character example")
            print("GUI error example")
        ''', 'Error: user message\nSyntax error example\nUndefined value example\n'
            'Illegal character example\nGUI error example\n')

    def test_real_errors_fail_even_when_stdout_matches(self):
        result = run_brittainscript('push(1)\nx = unknown_name\n')
        self.assertFalse(result.ok)
        self.assertEqual(result.stdout, '1\n')
        self.assertIn('Undefined variable', result.error)
        matched, _, _, error = compare('print(1)\n', 'push(1)\nx = unknown_name\n')
        self.assertFalse(matched)
        self.assertIn('brittainscript failed', error)

    def test_lexer_errors_use_the_diagnostic_channel(self):
        result = run_brittainscript('push(1$)\n')
        self.assertFalse(result.ok)
        self.assertIn('Illegal character', result.error)
        self.assertNotIn('Illegal character', result.stdout)


class ImportValidationRegressionTests(unittest.TestCase):
    def test_dotted_lookup_does_not_execute_parent_packages(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / 'review_regression_package'
            package.mkdir()
            (package / '__init__.py').write_text('raise RuntimeError("package executed")\n')
            (package / 'child.py').write_text('value = 1\n')
            source = 'import review_regression_package.child as child\n'
            with mock.patch.object(sys, 'path', [directory] + sys.path):
                self.assertTrue(translate(source, verify=False).ok)
                self.assertEqual(survey_features(source), set())
                self.assertFalse(module_is_available('review_regression_package.missing'))
            self.assertNotIn('review_regression_package', sys.modules)

    def test_namespace_and_builtin_modules_are_available(self):
        self.assertTrue(module_is_available('math'))
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / 'review_namespace_package'
            package.mkdir()
            (package / 'child.py').write_text('value = 1\n')
            with mock.patch.object(sys, 'path', [directory] + sys.path):
                self.assertTrue(module_is_available('review_namespace_package.child'))
                self.assertFalse(module_is_available('math.child'))
                nested = package / 'nested'
                nested.mkdir()
                (nested / 'child.py').write_text('value = 2\n')
                self.assertTrue(module_is_available('review_namespace_package.nested.child'))

    def test_new_statement_keywords_cannot_be_assignment_targets(self):
        for source in ('local = 1', 'discard = 1', 'local += 1', 'discard += 1'):
            with self.subTest(source=source):
                result = translate(source, verify=False)
                self.assertIn('name collides with a keyword', result.rejected_features)


class ModuleRegressionTests(unittest.TestCase):
    def setUp(self):
        self.functions = dict(main.functions)
        self.names = dict(parser.names)
        main.functions.clear()
        parser.names.clear()

    def tearDown(self):
        main.functions.clear()
        main.functions.update(self.functions)
        parser.names.clear()
        parser.names.update(self.names)
        self.assertEqual(len(parser.scopes), 1)
        self.assertEqual(main.function_environments, [None])

    def run_source(self, source):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.execute_lines(textwrap.dedent(source).strip().splitlines())
        return output.getvalue()

    def test_import_preserves_user_functions_and_module_members(self):
        self.assertEqual(self.run_source('''
            func max(a, b):
                return 99
            end
            add math
            push(math.max(1, 2))
            push(max(1, 2))
            push(math.min(1, 2))
            push(max(1, 2))
        '''), '2\n99\n1\n99\n')

    def test_nested_module_calls_restore_outer_helpers(self):
        inner = parser.BSModule({'__bs_module__': True, 'name': 'inner',
                 'funcs': {'helper': ([], ['return 3'])}})
        outer = parser.BSModule({'__bs_module__': True, 'name': 'outer', 'funcs': {
            'run': ([], ['return inner.helper() + helper()']),
            'helper': ([], ['return 7']),
        }})
        parser.set_name('inner', inner)
        original = ([], ['return 99'])
        main.functions['helper'] = original
        self.assertEqual(main.call_module_function(outer, 'run', []), 10)
        self.assertEqual(main.functions, {'helper': original})

    def test_gui_callback_uses_user_function_during_a_module_call(self):
        original = ([], ['return 99'])
        main.functions['helper'] = original
        module = {'name': 'events', 'funcs': {
            'run': ([], ['return helper()']),
            'helper': ([], ['return 1']),
        }}
        observed = []
        original_execute = main.execute_lines
        def event_loop(_):
            observed.append(main.functions['helper'])
            with mock.patch.object(main, 'execute_lines', original_execute):
                observed.append(parser.gui_backend.callback_invoker('helper', []))
        with mock.patch.object(main, 'execute_lines', side_effect=event_loop):
            main.call_module_function(module, 'run', [])
        self.assertEqual(observed, [original, 99])

    def test_module_bindings_are_restored_after_an_exception(self):
        original = ([], ['return 99'])
        main.functions['helper'] = original
        module = {'name': 'broken', 'funcs': {'helper': ([], ['return 1'])}}
        with mock.patch.object(main, 'execute_lines', side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):
                main.call_module_function(module, 'helper', [])
            self.assertEqual(main.functions, {'helper': original})
            with self.assertRaises(RuntimeError):
                main.import_module('math')
            self.assertEqual(main.functions, {'helper': original})

    def test_library_abs_handles_negative_values(self):
        self.assertEqual(self.run_source('''
            add math
            push(math.abs(0 - 5))
            push(math.abs(0))
            push(math.abs(5))
        '''), '5\n0\n5\n')


if __name__ == '__main__':
    unittest.main()
