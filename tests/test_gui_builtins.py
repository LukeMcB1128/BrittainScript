import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core"))
import parser
import gui_backend
import main


class GuiBuiltinDispatchTests(unittest.TestCase):
    def test_gui_builtins_are_registered(self):
        for name in ("guiwindow", "guibutton", "guicanvas", "guirun",
                     "guidrawline", "guisettext", "guialert"):
            self.assertTrue(gui_backend.is_gui_builtin(name))

    def test_non_gui_names_are_not_registered(self):
        self.assertFalse(gui_backend.is_gui_builtin("window"))
        self.assertFalse(gui_backend.is_gui_builtin("push"))

    def test_wrong_arity_is_rejected_without_touching_tk(self):
        self.assertIsNone(gui_backend.call_builtin("guiwindow", []))
        self.assertIsNone(gui_backend.call_builtin("guipack", [1, 2]))

    def test_unknown_widget_id_is_handled(self):
        self.assertIsNone(gui_backend.call_builtin("guipack", [99999]))
        self.assertIsNone(gui_backend.call_builtin("guisettext", [99999, "hi"]))

    def test_run_without_window_is_handled(self):
        self.assertIsNone(gui_backend.call_builtin("guirun", []))


class GuiModuleTests(unittest.TestCase):
    def test_gui_module_imports_with_expected_functions(self):
        module = main.import_module("gui")
        self.assertIsNotNone(module)
        for name in ("window", "label", "button", "entry", "canvas", "pack",
                     "setText", "getText", "circle", "onClick", "after", "run"):
            self.assertIn(name, module["funcs"])


if __name__ == "__main__":
    unittest.main()
