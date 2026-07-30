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


class ScriptTestCase(unittest.TestCase):
    # scripts here define functions and variables globally, so put both back the
    # way they were or later tests inherit them
    def setUp(self):
        self.saved_functions = dict(main.functions)
        self.saved_names = dict(parser.names)

    def tearDown(self):
        main.functions.clear()
        main.functions.update(self.saved_functions)
        parser.names.clear()
        parser.names.update(self.saved_names)


class ElseTests(ScriptTestCase):
    def test_else_runs_when_the_condition_is_false(self):
        self.assertEqual(run("""
            x = 1
            cond x == 2:
                push("then")
            else:
                push("otherwise")
            end
        """), ["otherwise"])

    def test_else_is_skipped_when_the_condition_is_true(self):
        self.assertEqual(run("""
            x = 2
            cond x == 2:
                push("then")
            else:
                push("otherwise")
            end
        """), ["then"])

    def test_code_after_the_block_still_runs(self):
        self.assertEqual(run("""
            cond false:
                push("a")
            else:
                push("b")
            end
            push("after")
        """), ["b", "after"])


class ElifTests(ScriptTestCase):
    def test_first_matching_branch_wins(self):
        source = """
            cond n < 0:
                push("negative")
            elif n == 0:
                push("zero")
            elif n < 10:
                push("small")
            else:
                push("large")
            end
        """
        expected = {-4: "negative", 0: "zero", 3: "small", 99: "large"}
        for value, label in expected.items():
            parser.set_name("n", value)
            self.assertEqual(run(source), [label])

    def test_only_one_branch_runs_when_several_match(self):
        self.assertEqual(run("""
            x = 5
            cond x > 1:
                push("first")
            elif x > 2:
                push("second")
            end
        """), ["first"])

    def test_elif_without_else_can_match_nothing(self):
        self.assertEqual(run("""
            x = 0
            cond x == 1:
                push("one")
            elif x == 2:
                push("two")
            end
            push("after")
        """), ["after"])

    def test_parenthesised_conditions_work(self):
        self.assertEqual(run("""
            x = 2
            cond (x == 1):
                push("one")
            elif (x == 2):
                push("two")
            end
        """), ["two"])


class NestingTests(ScriptTestCase):
    def test_inner_else_binds_to_the_inner_cond(self):
        self.assertEqual(run("""
            a = 1
            b = 2
            cond a == 1:
                cond b == 1:
                    push("a1 b1")
                else:
                    push("a1 b2")
                end
                push("after inner")
            else:
                push("a2")
            end
        """), ["a1 b2", "after inner"])

    def test_branches_work_inside_a_loop(self):
        self.assertEqual(run("""
            for n in space(4):
                cond (n % 2) == 0:
                    push(tostr(n) + " even")
                else:
                    push(tostr(n) + " odd")
                end
            end
        """), ["0 even", "1 odd", "2 even", "3 odd"])

    def test_branches_work_inside_a_function_with_return(self):
        self.assertEqual(run("""
            func label(n):
                cond n < 0:
                    return "negative"
                elif n == 0:
                    return "zero"
                else:
                    return "positive"
                end
            end
            push(label(0))
            push(label(7))
        """), ["zero", "positive"])

    def test_dedent_terminated_blocks_still_work(self):
        self.assertEqual(run("""
            x = 7
            cond x > 10:
                push("big")
            elif x > 5:
                push("middle")
            else:
                push("small")
            push("after")
        """), ["middle", "after"])


class BranchErrorTests(ScriptTestCase):
    def test_elif_after_else_is_rejected(self):
        self.assertIn("elif after else", "\n".join(run("""
            cond false:
                push("a")
            else:
                push("b")
            elif true:
                push("c")
            end
        """)))

    def test_else_with_a_condition_is_rejected(self):
        self.assertIn("else does not take a condition", "\n".join(run("""
            cond false:
                push("a")
            else true:
                push("b")
            end
        """)))

    def test_elif_without_a_condition_is_rejected(self):
        self.assertIn("expected a condition", "\n".join(run("""
            cond false:
                push("a")
            elif:
                push("b")
            end
        """)))

    def test_stray_else_is_reported(self):
        self.assertIn("unexpected else", "\n".join(run("""
            push("before")
            else:
                push("stray")
        """)))


class NullTests(ScriptTestCase):
    def test_null_is_a_value(self):
        self.assertEqual(run("push(null)"), ["null"])
        self.assertEqual(run("x = null\npush(x)"), ["null"])

    def test_null_compares_equal_to_itself(self):
        self.assertEqual(run("""
            x = null
            push(x == null)
            push(x != null)
            push(1 == null)
        """), ["True", "False", "False"])

    def test_null_is_falsy(self):
        self.assertEqual(run("""
            cond null:
                push("truthy")
            else:
                push("falsy")
            end
            push(not null)
        """), ["falsy", "True"])

    def test_tostr_renders_null(self):
        self.assertEqual(run('push(tostr(null))'), ["null"])
        self.assertEqual(run('push("value: " + tostr(null))'), ["value: null"])

    def test_null_lives_in_lists(self):
        self.assertEqual(run("""
            items = [1, null, 3]
            push(len(items))
            push(items[1] == null)
        """), ["3", "True"])

    def test_a_function_can_return_null(self):
        self.assertEqual(run("""
            func nothing():
                return null
            end
            push(nothing() == null)
        """), ["True"])

    def test_a_bare_null_prints_nothing(self):
        # null is the interpreter's "no value", so a bare null at the top level
        # stays quiet the way an assignment does
        self.assertEqual(run("null"), [])


if __name__ == "__main__":
    unittest.main()
