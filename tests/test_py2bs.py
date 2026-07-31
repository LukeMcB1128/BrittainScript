import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from py2bs import UnsupportedFeature, translate
from py2bs.emitter import emit
from py2bs.frontend import parse_and_validate
from py2bs.lowering import lower
from py2bs.report import run_corpus

CORPUS = REPO_ROOT / 'tests' / 'py_corpus'
REJECTS = REPO_ROOT / 'tests' / 'py_rejects'


def to_bs(source):
    return emit(lower(parse_and_validate(source)))


def rejection(source):
    try:
        parse_and_validate(source)
    except UnsupportedFeature as error:
        return error
    try:
        emit(lower(parse_and_validate(source)))
    except UnsupportedFeature as error:
        return error
    raise AssertionError('expected a rejection')


class EmissionTests(unittest.TestCase):
    def test_print_becomes_push(self):
        self.assertEqual(to_bs('print(1)'), 'push(1)\n')

    def test_a_string_literal_is_not_rewritten(self):
        # the reason for using ast rather than regular expressions: 'print'
        # inside a string must survive untouched
        self.assertEqual(to_bs('print("the print function")'), 'push("the print function")\n')

    def test_function_definition(self):
        self.assertEqual(
            to_bs('def add(a, b):\n    return a + b\n'),
            'func add(a, b):\n    return (a + b)\nend\n',
        )

    def test_if_elif_else(self):
        source = 'if a:\n    print(1)\nelif b:\n    print(2)\nelse:\n    print(3)\n'
        self.assertEqual(
            to_bs(source),
            'cond a:\n    push(1)\nelif b:\n    push(2)\nelse:\n    push(3)\nend\n',
        )

    def test_while_with_break_and_continue(self):
        source = 'while a:\n    break\n    continue\n'
        self.assertEqual(to_bs(source), 'while a:\n    break\n    continue\nend\n')

    def test_for_over_range_becomes_space(self):
        self.assertEqual(
            to_bs('for i in range(3):\n    print(i)\n'),
            'for i in space(3):\n    push(i)\nend\n',
        )

    def test_for_over_a_list(self):
        self.assertEqual(
            to_bs('for i in [1, 2]:\n    print(i)\n'),
            'for i in [1, 2]:\n    push(i)\nend\n',
        )

    def test_constants(self):
        self.assertEqual(to_bs('print(None)'), 'push(null)\n')
        self.assertEqual(to_bs('print(True)'), 'push(true)\n')
        self.assertEqual(to_bs('print(False)'), 'push(false)\n')

    def test_string_escaping(self):
        self.assertEqual(to_bs(r'print("a\"b")'), 'push("a\\"b")\n')
        self.assertEqual(to_bs(r'print("a\\b")'), 'push("a\\\\b")\n')
        self.assertEqual(to_bs(r'print("a\nb")'), 'push("a\\nb")\n')

    def test_indexing_and_slicing(self):
        self.assertEqual(to_bs('print(a[1])'), 'push(a[1])\n')
        self.assertEqual(to_bs('print(a[1:2])'), 'push(a[1:2])\n')
        self.assertEqual(to_bs('print(a[:2])'), 'push(a[:2])\n')
        self.assertEqual(to_bs('print(a[1:])'), 'push(a[1:])\n')

    def test_builtin_renaming(self):
        self.assertEqual(to_bs('print(str(1))'), 'push(tostr(1))\n')
        self.assertEqual(to_bs('print(abs(a))'), 'push(absolute(a))\n')
        self.assertEqual(to_bs('print(len(a))'), 'push(len(a))\n')

    def test_print_with_several_arguments(self):
        self.assertEqual(to_bs('print(a, b)'), 'push(tostr(a) + " " + tostr(b))\n')

    def test_print_with_no_arguments(self):
        self.assertEqual(to_bs('print()'), 'push("")\n')

    def test_fstring_becomes_concatenation(self):
        self.assertEqual(to_bs('print(f"n={n}")'), 'push(("n=" + tostr(n)))\n')

    def test_method_calls_pass_through(self):
        self.assertEqual(to_bs('xs.append(1)'), 'xs.append(1)\n')
        self.assertEqual(to_bs('print(s.upper())'), 'push(s.upper())\n')

    def test_binary_operations_are_parenthesised(self):
        self.assertEqual(to_bs('print(a + b * c)'), 'push((a + (b * c)))\n')


class LoweringTests(unittest.TestCase):
    def test_augmented_assignment_is_expanded(self):
        self.assertEqual(to_bs('x += 1'), 'x = (x + 1)\n')
        self.assertEqual(to_bs('x -= 1'), 'x = (x - 1)\n')
        self.assertEqual(to_bs('x *= 2'), 'x = (x * 2)\n')

    def test_augmented_assignment_on_an_index(self):
        self.assertEqual(to_bs('xs[0] += 1'), 'xs[0] = (xs[0] + 1)\n')

    def test_unary_minus_becomes_a_subtraction(self):
        self.assertEqual(to_bs('print(-5)'), 'push((0 - 5))\n')
        self.assertEqual(to_bs('print(-x)'), 'push((0 - x))\n')

    def test_floor_division_becomes_floor(self):
        self.assertEqual(to_bs('print(a // b)'), 'push(floor((a / b)))\n')

    def test_function_locals_are_renamed_away_from_globals(self):
        source = 'total = 1\ndef f():\n    total = 2\n    return total\n'
        emitted = to_bs(source)
        self.assertIn('f_total = 2', emitted)
        self.assertIn('return f_total', emitted)

    def test_locals_that_do_not_collide_keep_their_names(self):
        source = 'def f():\n    scratch = 2\n    return scratch\n'
        self.assertIn('scratch = 2', to_bs(source))

    def test_a_global_only_read_is_not_renamed(self):
        source = 'limit = 5\ndef f():\n    return limit\n'
        self.assertIn('return limit', to_bs(source))


class RejectionTests(unittest.TestCase):
    def assertRejects(self, source, feature):
        self.assertEqual(rejection(source).feature, feature)

    def test_rejected_statements(self):
        self.assertRejects('import math', 'imports')
        self.assertRejects('from math import pi', 'imports')
        self.assertRejects('class A:\n    pass\n', 'classes')
        self.assertRejects('try:\n    pass\nexcept:\n    pass\n', 'try/except')
        self.assertRejects('with open("f") as h:\n    pass\n', 'with')
        self.assertRejects('raise ValueError()', 'raise')
        self.assertRejects('assert True', 'assert')
        self.assertRejects('del x', 'del')
        self.assertRejects('x: int = 1', 'annotated assignment')

    def test_rejected_expressions(self):
        self.assertRejects('x = {"a": 1}', 'dict literals')
        self.assertRejects('x = {1, 2}', 'set literals')
        self.assertRejects('x = (1, 2)', 'tuples')
        self.assertRejects('x = [i for i in y]', 'comprehensions')
        self.assertRejects('f = lambda a: a', 'lambda')
        self.assertRejects('x = 1 if y else 2', 'conditional expression')
        self.assertRejects('print(2 ** 3)', 'power operator')
        self.assertRejects('print(1 & 2)', 'bitwise operators')
        self.assertRejects('print(a in b)', 'in operator')
        self.assertRejects('print(a is b)', 'is operator')
        self.assertRejects('print(1 < a < 3)', 'chained comparison')

    def test_rejected_function_shapes(self):
        self.assertRejects('def f(*args):\n    pass\n', 'star arguments')
        self.assertRejects('def f(a=1):\n    pass\n', 'default arguments')
        self.assertRejects('@d\ndef f():\n    pass\n', 'decorators')
        self.assertRejects('def f():\n    def g():\n        pass\n', 'nested functions')
        self.assertRejects('def f():\n    yield 1\n', 'generators')
        self.assertRejects('def f():\n    global x\n', 'global/nonlocal')

    def test_rejected_assignment_shapes(self):
        self.assertRejects('a = b = 1', 'multiple assignment')
        self.assertRejects('a, b = 1, 2', 'tuple unpacking')
        self.assertRejects('for a, b in xs:\n    pass\n', 'tuple unpacking')

    def test_short_circuit_guard_is_rejected(self):
        # BrittainScript evaluates both sides, so this guard would not guard
        self.assertRejects('if i < len(xs) and xs[i] > 0:\n    pass\n', 'short-circuit and/or')

    def test_non_boolean_and_or_is_rejected(self):
        # Python returns an operand here; BrittainScript returns a bool
        self.assertRejects('x = name or "default"', 'non-boolean and/or')
        self.assertRejects('x = 1 and 2', 'non-boolean and/or')

    def test_safe_boolean_operators_are_accepted(self):
        self.assertEqual(to_bs('print(a > 1 and b < 2)'), 'push(((a > 1) and (b < 2)))\n')
        self.assertEqual(to_bs('print(not a == 1)'), 'push((not (a == 1)))\n')

    def test_pop_is_rejected_for_returning_a_different_value(self):
        self.assertRejects('x = xs.pop()', 'pop() method')

    def test_unknown_calls_are_rejected(self):
        self.assertRejects('print(sorted(xs))', 'unsupported call')
        self.assertRejects('print(sum(xs))', 'unsupported call')
        self.assertRejects('x = input()', 'I/O or dynamic execution')
        self.assertRejects('x = open("f")', 'I/O or dynamic execution')

    def test_range_outside_a_for_loop_is_rejected(self):
        self.assertRejects('x = range(3)', 'range() outside a for loop')

    def test_bare_attribute_access_is_rejected(self):
        self.assertRejects('print(a.b)', 'attribute access')

    def test_format_specifiers_are_rejected(self):
        self.assertRejects('print(f"{x:.2f}")', 'format specifiers')

    def test_non_ascii_string_is_rejected(self):
        self.assertRejects('print("caf\u00e9")', 'non-ascii string literal')

    def test_invalid_python_is_reported(self):
        self.assertEqual(rejection('def f(:\n').feature, 'invalid python')

    def test_a_rejection_names_the_line(self):
        self.assertEqual(rejection('x = 1\ny = {"a": 1}\n').line, 2)


class TranslateApiTests(unittest.TestCase):
    def test_result_fields_on_success(self):
        result = translate('print(1 + 1)')
        self.assertTrue(result.ok)
        self.assertEqual(result.brittainscript, 'push((1 + 1))\n')
        self.assertEqual(result.rejected_features, [])
        self.assertEqual(result.python_stdout, '2\n')
        self.assertEqual(result.bs_stdout, '2\n')
        self.assertIsNone(result.error)

    def test_result_fields_on_rejection(self):
        result = translate('import os')
        self.assertFalse(result.ok)
        self.assertIsNone(result.brittainscript)
        self.assertEqual(result.rejected_features, ['imports'])
        self.assertIn('imports', result.error)

    def test_verification_can_be_skipped(self):
        result = translate('print(1)', verify=False)
        self.assertTrue(result.ok)
        self.assertIsNone(result.python_stdout)

    def test_a_mismatch_is_reported(self):
        # printing None is a real divergence: Python says None, BrittainScript
        # says null, and verification is what catches it
        result = translate('print(None)')
        self.assertFalse(result.ok)
        self.assertEqual(result.error, 'stdout mismatch')
        self.assertEqual(result.python_stdout, 'None\n')
        self.assertEqual(result.bs_stdout, 'null\n')

    def test_an_infinite_loop_times_out_instead_of_hanging(self):
        result = translate('while True:\n    x = 1\n', timeout=2)
        self.assertFalse(result.ok)
        self.assertIn('timed out', result.error)


class RoundTripTests(unittest.TestCase):
    def test_every_corpus_program_matches_python(self):
        paths = sorted(CORPUS.glob('*.py'))
        self.assertGreaterEqual(len(paths), 8)
        for path in paths:
            with self.subTest(program=path.name):
                result = translate(path.read_text())
                self.assertTrue(result.ok, f'{path.name}: {result.error}')
                self.assertEqual(result.python_stdout, result.bs_stdout)


class ReportTests(unittest.TestCase):
    def test_corpus_report_counts_rejections(self):
        report = run_corpus(REJECTS, verify=False)
        self.assertEqual(report.translated, 0)
        self.assertEqual(report.rejected, len(list(REJECTS.glob('*.py'))))
        features = dict(report.feature_counts)
        self.assertIn('dict literals', features)
        self.assertIn('try/except', features)
        self.assertIn('imports', features)

    def test_report_percentages_sum_to_one_hundred(self):
        report = run_corpus(REJECTS, verify=False)
        total = sum(share for _, _, share in report.rejection_table())
        self.assertAlmostEqual(total, 100.0, places=6)

    def test_report_formats_a_table(self):
        text = run_corpus(REJECTS, verify=False).format()
        self.assertIn('rejected features, by share of rejections:', text)
        self.assertIn('%', text)

    def test_an_unreadable_file_does_not_abort_the_run(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            good = pathlib.Path(directory) / 'good.py'
            good.write_text('print(1)\n')
            binary = pathlib.Path(directory) / 'binary.py'
            binary.write_bytes(b'x = "\xe9"\n')
            report = run_corpus(directory, verify=False)
            self.assertEqual(report.translated, 1)
            self.assertEqual(report.feature_counts['unreadable file'], 1)

    def test_source_with_a_null_byte_is_rejected_not_raised(self):
        # reported as a rejection rather than escaping as an exception; the
        # ValueError/RecursionError branch covers Python versions that do not
        # raise SyntaxError here
        self.assertEqual(rejection('x = 1\x00\n').feature, 'invalid python')

    def test_corpus_report_counts_successes(self):
        report = run_corpus(CORPUS, verify=True)
        self.assertEqual(report.rejected, 0)
        self.assertEqual(report.verified, report.translated)


if __name__ == '__main__':
    unittest.main()
