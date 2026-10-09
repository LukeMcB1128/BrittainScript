import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import main
import parser


class LocalModuleTests(unittest.TestCase):
    def setUp(self):
        self.names = dict(parser.names)
        self.functions = dict(main.functions)
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        parser.names.clear()
        parser.names.update(self.names)
        main.functions.clear()
        main.functions.update(self.functions)
        self.directory.cleanup()

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def run_file(self, relative):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = main.run_file(str(self.root / relative))
        return status, out.getvalue(), err.getvalue()

    def test_local_files_and_subfolders(self):
        self.write('helpers.bs', 'func double(x):\n    return x * 2\nend\n')
        self.write('utils/strings.bs', 'add case\nfunc shout(text):\n    return case.up(text) + "!"\nend\n')
        # a module's own add looks beside that module, so utils/strings.bs finds utils/case.bs
        self.write('utils/case.bs', 'func up(text):\n    return text.upper()\nend\n')
        self.write('app/main.bs', 'add helpers\n')
        self.write('main.bs', 'add helpers\nadd utils.strings\nadd math\npush(helpers.double(21))\npush(strings.shout("hi"))\npush(math.max(3, 9))\n')
        self.assertEqual(self.run_file('main.bs'), (0, '42\nHI!\n9\n', ''))

    def test_each_file_loads_once(self):
        self.write('counter.bs', 'counterLoads = 0\ncounterLoads += 1\nfunc loads():\n    return counterLoads\nend\n')
        self.write('other.bs', 'add counter\n')
        self.write('main.bs', 'add counter\nadd other\nadd counter\npush(counter.loads())\n')
        self.assertEqual(self.run_file('main.bs')[1], '1\n')

    def test_local_file_shadows_bundled_library_with_warning(self):
        self.write('math.bs', 'func max(a, b):\n    return "mine"\nend\n')
        self.write('main.bs', 'add math\npush(math.max(1, 2))\n')
        status, output, errors = self.run_file('main.bs')
        self.assertEqual(output, 'mine\n')
        self.assertIn('not the bundled math library', errors)

    def test_bundled_libraries_adding_each_other_do_not_warn(self):
        # ui.bs adds web and net from libs/; those are not local overrides
        self.write('main.bs', 'add ui\npush(ui.badge("x")["tag"])\n')
        self.assertEqual(self.run_file('main.bs'), (0, 'span\n', ''))

    def test_circular_add_is_an_error(self):
        self.write('a.bs', 'add b\n')
        self.write('b.bs', 'add a\n')
        self.write('main.bs', 'add a\n')
        status, _, errors = self.run_file('main.bs')
        self.assertEqual(status, 1)
        self.assertIn('circular add: a.bs -> b.bs -> a.bs', errors)

    def test_missing_and_invalid_names(self):
        self.write('missing.bs', 'add nothere\n')
        self.assertIn("library 'nothere' not found beside this file", self.run_file('missing.bs')[2])
        self.write('invalid.bs', 'add ../secret\n')
        self.assertIn("invalid library name '../secret'", self.run_file('invalid.bs')[2])


if __name__ == '__main__':
    unittest.main()
