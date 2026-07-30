import io
import contextlib
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
import main
import parser


def reader(typed):
    # stands in for the '...>' prompt; raises EOFError once the input runs out
    remaining = list(typed)

    def read_line():
        if not remaining:
            raise EOFError
        return remaining.pop(0)

    return read_line


def collect(first_line, typed):
    return main.read_block_lines(first_line, reader(typed))


def run_block(first_line, typed):
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        main.execute_lines(collect(first_line, typed))
    return output.getvalue().strip().split("\n") if output.getvalue().strip() else []


class ScriptTestCase(unittest.TestCase):
    def setUp(self):
        self.saved_functions = dict(main.functions)
        self.saved_names = dict(parser.names)

    def tearDown(self):
        main.functions.clear()
        main.functions.update(self.saved_functions)
        parser.names.clear()
        parser.names.update(self.saved_names)


class BlockIndentationTests(unittest.TestCase):
    def test_body_is_indented_under_its_block(self):
        self.assertEqual(
            collect("cond x > 10:", ['push("big")', "end"]),
            ["cond x > 10:", '    push("big")', "end"],
        )

    def test_nested_blocks_are_indented_by_depth(self):
        self.assertEqual(
            collect("cond a:", ["while b:", "push(1)", "end", "push(2)", "end"]),
            [
                "cond a:",
                "    while b:",
                "        push(1)",
                "    end",
                "    push(2)",
                "end",
            ],
        )

    def test_branch_keywords_line_up_with_their_block(self):
        self.assertEqual(
            collect("cond a:", ['push("a")', "elif b:", 'push("b")', "else:", 'push("c")', "end"]),
            [
                "cond a:",
                '    push("a")',
                "elif b:",
                '    push("b")',
                "else:",
                '    push("c")',
                "end",
            ],
        )

    def test_an_inner_end_does_not_close_the_outer_block(self):
        lines = collect("cond a:", ["cond b:", "push(1)", "end", "push(2)", "end"])
        self.assertEqual(lines[-1], "end")
        self.assertEqual(lines.count("end"), 1)
        self.assertIn("    end", lines)

    def test_typed_indentation_is_normalised(self):
        self.assertEqual(
            collect("cond a:", ["        push(1)", "end"]),
            ["cond a:", "    push(1)", "end"],
        )

    def test_end_of_input_closes_open_blocks(self):
        self.assertEqual(
            collect("cond a:", ['push("partial")']),
            ["cond a:", '    push("partial")', "end"],
        )

    def test_end_of_input_closes_every_open_block(self):
        self.assertEqual(
            collect("cond a:", ["while b:", "push(1)"]),
            ["cond a:", "    while b:", "        push(1)", "    end", "end"],
        )


class BlockExecutionTests(ScriptTestCase):
    def test_a_false_condition_runs_nothing(self):
        parser.set_name("x", 7)
        self.assertEqual(run_block("cond x > 10:", ['push("big")', "end"]), [])

    def test_a_true_condition_runs_the_body(self):
        parser.set_name("x", 20)
        self.assertEqual(run_block("cond x > 10:", ['push("big")', "end"]), ["big"])

    def test_elif_chain_picks_the_matching_branch(self):
        parser.set_name("x", 7)
        typed = ['push("big")', "elif x > 5:", 'push("middle")', "else:", 'push("small")', "end"]
        self.assertEqual(run_block("cond x > 10:", typed), ["middle"])

    def test_else_branch_runs_when_nothing_matches(self):
        parser.set_name("x", 1)
        typed = ['push("big")', "elif x > 5:", 'push("middle")', "else:", 'push("small")', "end"]
        self.assertEqual(run_block("cond x > 10:", typed), ["small"])

    def test_nested_cond_keeps_its_own_else(self):
        parser.set_name("b", 2)
        typed = [
            "cond b == 1:",
            'push("b1")',
            "else:",
            'push("b2")',
            "end",
            'push("after inner")',
            "else:",
            'push("outer else")',
            "end",
        ]
        self.assertEqual(run_block("cond true:", typed), ["b2", "after inner"])

    def test_a_false_outer_block_skips_the_nested_body(self):
        typed = ["cond true:", 'push("inner")', "end", 'push("outer")', "end"]
        self.assertEqual(run_block("cond false:", typed), [])

    def test_a_loop_nested_in_a_block_runs(self):
        typed = ["c = 0", "while c < 3:", "c = c + 1", "push(c)", "end", 'push("loop done")', "end"]
        self.assertEqual(run_block("cond true:", typed), ["1", "2", "3", "loop done"])

    def test_a_function_with_branches_can_be_defined_and_called(self):
        typed = [
            "cond n < 0:",
            'return "negative"',
            "elif n == 0:",
            'return "zero"',
            "else:",
            'return "positive"',
            "end",
            "end",
        ]
        self.assertEqual(run_block("func classify(n):", typed), [])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.execute_lines(["push(classify(0))", "push(classify(4))"])
        self.assertEqual(output.getvalue().split(), ["zero", "positive"])

    def test_break_inside_a_nested_cond_stops_the_loop(self):
        parser.set_name("i", 0)
        typed = ["i = i + 1", "cond i == 3:", "break", "end", "push(i)", "end"]
        self.assertEqual(run_block("while true:", typed), ["1", "2"])


if __name__ == "__main__":
    unittest.main()
