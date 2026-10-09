import contextlib
import io
from pathlib import Path
import sys
import textwrap
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import main
import parser
from core.diagnostics import BSError
from py2bs import translate


class DictionaryTests(unittest.TestCase):
    def setUp(self):
        self.saved_names = dict(parser.names)
        self.saved_functions = dict(main.functions)

    def tearDown(self):
        parser.names.clear()
        parser.names.update(self.saved_names)
        main.functions.clear()
        main.functions.update(self.saved_functions)

    def run_bs(self, source):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.execute_lines(textwrap.dedent(source).strip().splitlines())
        return output.getvalue()

    def test_nested_data_key_reads_writes_and_aliases(self):
        self.assertEqual(self.run_bs('''
            data = {"name": "Luke", "child": {"scores": [1, 2]},}
            alias = data
            data["child"]["scores"][0] += 4
            data["name"] = "BS"
            push(alias["child"]["scores"][0])
            push(alias["name"])
            push(len({}))
        '''), '5\nBS\n0\n')

    def test_methods_membership_and_null_values(self):
        self.assertEqual(self.run_bs('''
            data = {"empty": null, "score": 10}
            push(data.has("empty"))
            push(data.get("missing", 99))
            push(data.get("empty") == null)
            push("score" in data)
            push("missing" not in data)
            push(not "score" in data)
            push(list(data.keys()))
            push(list(data.values())[1])
            data.remove("score")
            push(len(data))
        '''), "True\n99\nTrue\nTrue\nTrue\nFalse\n['empty', 'score']\n10\n1\n")

    def test_ordinary_data_does_not_impersonate_a_library(self):
        self.assertEqual(self.run_bs('''
            data = {"__bs_module__": true, "name": "math", "funcs": {}}
            push(data.get("name"))
            push(data.has("funcs"))
            add math
            push(math.max(2, 4))
        '''), 'math\nTrue\n4\n')

    def test_order_and_duplicate_keys(self):
        self.assertEqual(self.run_bs('''
            data = {"a": 1, "b": 2, "a": 3}
            for key in data:
                push(key + tostr(data[key]))
            end
        '''), 'a3\nb2\n')

    def test_invalid_keys_and_methods_raise_typed_errors(self):
        for source, kind in [
            ('discard {}["missing"]', 'KeyError'), ('discard {[1]: 2}', 'TypeError'),
            ('data = {}\ndata[[1]] = 2', 'TypeError'), ('discard {}.has()', 'TypeError'),
            ('discard {}.remove("missing")', 'KeyError'), ('discard "a" in 3', 'TypeError'),
        ]:
            with self.subTest(source=source):
                with self.assertRaises(BSError) as raised:
                    self.run_bs(source)
                self.assertEqual(raised.exception.type, kind)

    def test_constructor_and_dictionary_in_index_expression(self):
        self.assertEqual(self.run_bs('''
            data = dict()
            data[{"key": "a"}["key"]] = 8
            push(data["a"])
            push(2 in [1, 2])
            push("b" in "abc")
        '''), '8\nTrue\nTrue\n')

    def test_translation_matches_python(self):
        result = translate('''data = {"a": 1, "b": {"c": 2}}
data["a"] += data["b"]["c"]
print(data.get("a"))
print("a" in data)
print("missing" not in data)
print(list(data.keys()))
print(dict())
''')
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.bs_stdout, "3\nTrue\nTrue\n['a', 'b']\n{}\n")
