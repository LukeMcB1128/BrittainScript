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


class StringLiteralTests(unittest.TestCase):
    def test_escape_sequences_are_decoded(self):
        self.assertEqual(evaluate(r'"tab\there"'), "tab\there")
        self.assertEqual(evaluate(r'"nl\nhere"'), "nl\nhere")
        self.assertEqual(evaluate(r'"quote\"inside"'), 'quote"inside')
        self.assertEqual(evaluate(r'"back\\slash"'), "back\\slash")

    def test_accented_characters_survive(self):
        self.assertEqual(evaluate('"café"'), "café")
        self.assertEqual(evaluate('"naïve résumé"'), "naïve résumé")

    def test_characters_beyond_latin1_survive(self):
        self.assertEqual(evaluate('"日本語"'), "日本語")
        self.assertEqual(evaluate('"✓ done"'), "✓ done")
        self.assertEqual(evaluate('"emoji 🎉 here"'), "emoji 🎉 here")

    def test_length_counts_characters_not_bytes(self):
        self.assertEqual(evaluate('len("café")'), 4)
        self.assertEqual(evaluate('len("日本語")'), 3)

    def test_methods_work_on_non_ascii(self):
        self.assertEqual(evaluate('"café".upper()'), "CAFÉ")

    def test_escapes_and_non_ascii_together(self):
        self.assertEqual(evaluate(r'"café\tnaïve"'), "café\tnaïve")

    def test_empty_string(self):
        self.assertEqual(evaluate('""'), "")

    def test_printing_matches_python(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            evaluate('push("café ✓ 日本語")')
        self.assertEqual(output.getvalue(), "café ✓ 日本語\n")


if __name__ == "__main__":
    unittest.main()
