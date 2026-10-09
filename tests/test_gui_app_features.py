import contextlib
import io
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'core'))
import main
import parser
import gui_backend as gui
from core.diagnostics import BSError


class Listbox:
    def __init__(self, *args, **kwargs):
        self.items, self.selection, self.events = [], (), {}

    def insert(self, index, *items):
        self.items.extend(items)

    def delete(self, *args):
        self.items.clear()
        self.selection = ()

    def bind(self, name, callback):
        self.events[name] = callback

    def curselection(self):
        return self.selection

    def get(self, first, last):
        return tuple(self.items)

    def selection_clear(self, *args):
        self.selection = ()

    def selection_set(self, index):
        self.selection = (index,)

    def size(self):
        return len(self.items)

    def see(self, index):
        self.seen = index

    def configure(self, **kwargs):
        self.config = kwargs


class GuiAppFeatureTests(unittest.TestCase):
    def setUp(self):
        self.names = dict(parser.names)
        self.functions = dict(main.functions)
        self.widgets = dict(gui.widgets)
        self.identifier = gui.next_id

    def tearDown(self):
        parser.names.clear()
        parser.names.update(self.names)
        main.functions.clear()
        main.functions.update(self.functions)
        gui.widgets.clear()
        gui.widgets.update(self.widgets)
        gui.next_id = self.identifier
        self.assertEqual(gui.callback_error_frames, [])

    def test_default_callback_error_is_logged_and_next_callback_runs(self):
        window = Mock()
        def events():
            gui._run_callback('fail', [])
            gui._run_callback('success', [])
        window.mainloop.side_effect = events
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(gui, 'root_window', window), patch.object(gui, 'error_callback', None), \
             patch.object(gui, 'stop_on_error', False), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            main.execute_lines('''func fail():
    raise "failed action"
end
func success():
    push("next callback")
end
guirun()
'''.splitlines())
        self.assertEqual(output.getvalue(), 'next callback\n')
        self.assertIn('failed action', errors.getvalue())
        window.quit.assert_not_called()

    def test_error_handler_gets_bs_error_and_handler_failures_do_not_recurse(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.object(gui, 'error_callback', None), contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            main.execute_lines('''add gui
func on_error(problem):
    push(problem.message)
end
func fail():
    raise "failed action"
end
gui.onError("on_error")
'''.splitlines())
            gui._run_callback('fail', [])
            main.execute_lines(['func on_error(problem):', '    raise "handler failed"', 'end'])
            gui._run_callback('fail', [])
            main.execute_lines(['gui.onError(null)'])
            self.assertIsNone(gui.error_callback)
        self.assertEqual(output.getvalue(), 'failed action\n')
        self.assertIn('handler failed', errors.getvalue())
        self.assertFalse(gui.handling_callback_error)

    def test_list_selection_uses_widget_index_and_data_updates_clear_selection(self):
        tk = Mock()
        tk.Listbox = Listbox
        parent = gui._register(object())
        calls = []
        with patch.object(gui, 'tk', tk), patch.object(gui, 'callback_invoker', lambda name, args: calls.append((name, args))):
            identifier = gui.call_builtin('guilist', [parent, ['one', 'two'], 'selected'])
            widget = gui.widgets[identifier]
            gui.call_builtin('guiselect', [identifier, 1])
            widget.events['<<ListboxSelect>>'](Mock())
            self.assertEqual(calls, [('selected', [1])])
            self.assertEqual(gui.call_builtin('guiselectedindex', [identifier]), 1)
            self.assertEqual(gui.call_builtin('guigetitems', [identifier]), ['one', 'two'])
            gui.call_builtin('guilistsize', [identifier, 40, 10])
            self.assertEqual(widget.config, {'width': 40, 'height': 10})
            gui.call_builtin('guisetitems', [identifier, ['new']])
            self.assertIsNone(gui.call_builtin('guiselectedindex', [identifier]))
            widget.events['<<ListboxSelect>>'](Mock())
            self.assertEqual(len(calls), 1)
            with self.assertRaises(BSError):
                main.execute_lines([f'guiselect({identifier}, 2)'])

    def test_widget_operations_reject_other_threads(self):
        with patch.object(gui, 'gui_thread_id', threading.get_ident() + 1):
            with self.assertRaises(BSError) as raised:
                main.execute_lines(['guirun()'])
        self.assertEqual(raised.exception.type, 'RuntimeError')
        self.assertIn('thread', raised.exception.message)

    def test_gui_module_has_all_new_functions(self):
        module = main.import_module('gui')
        for name in ['list', 'setItems', 'getItems', 'selectedIndex', 'select', 'setListSize', 'onError', 'stopOnError']:
            self.assertIn(name, module['funcs'])
