try:
    from core.diagnostics import report, BSError, emit, from_python, handling
except ModuleNotFoundError:
    from diagnostics import report, BSError, emit, from_python, handling

import threading

# gui_backend.py -- tkinter bridge for the BrittainScript gui library
#
# Widgets are handed to BrittainScript code as integer ids so scripts only
# ever hold plain numbers. Callbacks are BrittainScript function names passed
# as strings; when tkinter fires an event we call back into the interpreter
# through the invoker set by parser.py.
#
# tkinter is imported lazily so environments without a display can still run
# non-GUI scripts.

tk = None
messagebox = None
simpledialog = None

callback_invoker = None

widgets = {}
next_id = 1
root_window = None
callback_error_frames = []
error_callback = None
stop_on_error = False
handling_callback_error = False
gui_thread_id = None


def set_callback_invoker(invoker):
    global callback_invoker
    callback_invoker = invoker


def _load_tk():
    global tk, messagebox, simpledialog
    if tk is not None:
        return True
    try:
        import tkinter as tk_module
        from tkinter import messagebox as messagebox_module
        from tkinter import simpledialog as simpledialog_module
    except ImportError:
        report("GUI error: tkinter is not available on this system")
        return False
    tk = tk_module
    messagebox = messagebox_module
    simpledialog = simpledialog_module
    return True


def _register(widget):
    global next_id
    widget_id = next_id
    next_id += 1
    widgets[widget_id] = widget
    return widget_id


def _lookup(widget_id, kinds=None):
    widget = widgets.get(widget_id)
    if widget is None:
        report(f"GUI error: no widget with id {widget_id}")
        return None
    if kinds and not isinstance(widget, kinds):
        report(f"GUI error: widget {widget_id} does not support this operation")
        return None
    return widget


def _run_callback(name, args):
    if callback_error_frames and callback_error_frames[-1]:
        return
    if callback_invoker is None:
        report("GUI error: no callback invoker set")
        return
    try:
        callback_invoker(name, list(args))
    except Exception as cause:
        error = from_python(cause)
        global handling_callback_error
        if error_callback is not None and not handling_callback_error:
            handling_callback_error = True
            try:
                with handling(error):
                    callback_invoker(error_callback, [error])
            except Exception as handler_error:
                emit(error)
                emit(from_python(handler_error))
            finally:
                handling_callback_error = False
            return
        if stop_on_error and not handling_callback_error:
            if not callback_error_frames:
                raise error
            callback_error_frames[-1].append(error)
            root_window.quit()
        else:
            emit(error)


def gui_onerror(args):
    global error_callback
    name = args[0]
    if name is not None and (not isinstance(name, str) or not name):
        raise TypeError('GUI error handler must be a function name or null')
    error_callback = name
    return None


def gui_stoponerror(args):
    global stop_on_error
    if type(args[0]) is not bool:
        raise TypeError('GUI stop-on-error setting must be a boolean')
    stop_on_error = args[0]
    return None


def gui_window(args):
    if not _load_tk():
        return None
    global root_window, gui_thread_id
    title, width, height = args
    if root_window is None or not _window_alive(root_window):
        window = tk.Tk()
        root_window = window
        gui_thread_id = threading.get_ident()
    else:
        window = tk.Toplevel(root_window)
    window.title(str(title))
    window.geometry(f"{int(width)}x{int(height)}")
    return _register(window)


def _window_alive(window):
    try:
        return bool(window.winfo_exists())
    except Exception:
        return False


def gui_title(args):
    window = _lookup(args[0])
    if window is not None:
        window.title(str(args[1]))
    return None


def gui_close(args):
    window = _lookup(args[0])
    if window is not None:
        window.destroy()
    return None


def gui_run(args):
    if root_window is None or not _window_alive(root_window):
        report("GUI error: create a window before calling run()")
        return None
    errors = []
    callback_error_frames.append(errors)
    try:
        root_window.mainloop()
        if errors:
            raise errors[0]
    finally:
        callback_error_frames.pop()
    return None


def gui_frame(args):
    parent = _lookup(args[0])
    if parent is None:
        return None
    return _register(tk.Frame(parent))


def gui_label(args):
    parent = _lookup(args[0])
    if parent is None:
        return None
    return _register(tk.Label(parent, text=str(args[1])))


def gui_button(args):
    parent = _lookup(args[0])
    if parent is None:
        return None
    callback_name = str(args[2])
    button = tk.Button(parent, text=str(args[1]),
                       command=lambda: _run_callback(callback_name, []))
    return _register(button)


def gui_entry(args):
    parent = _lookup(args[0])
    if parent is None:
        return None
    return _register(tk.Entry(parent))


def gui_textbox(args):
    parent = _lookup(args[0])
    if parent is None:
        return None
    return _register(tk.Text(parent, width=int(args[1]), height=int(args[2])))


def _list_items(items):
    if not isinstance(items, list):
        raise TypeError('GUI list items must be a list')
    return [str(item) for item in items]


def gui_list(args):
    parent = _lookup(args[0])
    if parent is None:
        return None
    items = _list_items(args[1])
    callback = args[2]
    if callback is not None and (not isinstance(callback, str) or not callback):
        raise TypeError('List selection callback must be a function name or null')
    widget = tk.Listbox(parent, exportselection=False, selectmode='browse')
    if items:
        widget.insert('end', *items)
    if callback is not None:
        def selected(event):
            indexes = widget.curselection()
            if indexes:
                _run_callback(callback, [int(indexes[0])])
        widget.bind('<<ListboxSelect>>', selected)
    return _register(widget)


def gui_setitems(args):
    widget = _lookup(args[0], (tk.Listbox,))
    if widget is not None:
        items = _list_items(args[1])
        widget.delete(0, 'end')
        if items:
            widget.insert('end', *items)
    return None


def gui_getitems(args):
    widget = _lookup(args[0], (tk.Listbox,))
    return list(widget.get(0, 'end')) if widget is not None else None


def gui_selectedindex(args):
    widget = _lookup(args[0], (tk.Listbox,))
    if widget is not None:
        indexes = widget.curselection()
        return int(indexes[0]) if indexes else None
    return None


def gui_select(args):
    widget = _lookup(args[0], (tk.Listbox,))
    if widget is not None:
        index = args[1]
        if index is not None and (type(index) is not int or not 0 <= index < widget.size()):
            raise IndexError('GUI list index is out of range')
        widget.selection_clear(0, 'end')
        if index is not None:
            widget.selection_set(index)
            widget.see(index)
    return None


def gui_listsize(args):
    widget = _lookup(args[0], (tk.Listbox,))
    if widget is not None:
        width, height = args[1:]
        if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
            raise ValueError('GUI list width and height must be positive integers')
        widget.configure(width=width, height=height)
    return None


def gui_checkbox(args):
    parent = _lookup(args[0])
    if parent is None:
        return None
    variable = tk.BooleanVar(parent, value=False)
    checkbox = tk.Checkbutton(parent, text=str(args[1]), variable=variable)
    checkbox.bs_variable = variable
    return _register(checkbox)


def gui_slider(args):
    parent = _lookup(args[0])
    if parent is None:
        return None
    slider = tk.Scale(parent, from_=args[1], to=args[2], orient='horizontal')
    return _register(slider)


def gui_canvas(args):
    parent = _lookup(args[0])
    if parent is None:
        return None
    canvas = tk.Canvas(parent, width=int(args[1]), height=int(args[2]),
                       background='white', highlightthickness=0)
    return _register(canvas)


def gui_pack(args):
    widget = _lookup(args[0])
    if widget is not None:
        widget.pack(padx=4, pady=4)
    return None


def gui_place(args):
    widget = _lookup(args[0])
    if widget is not None:
        widget.place(x=int(args[1]), y=int(args[2]))
    return None


def gui_grid(args):
    widget = _lookup(args[0])
    if widget is not None:
        widget.grid(row=int(args[1]), column=int(args[2]), padx=4, pady=4)
    return None


def gui_gettext(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    if isinstance(widget, tk.Entry):
        return widget.get()
    if isinstance(widget, tk.Text):
        return widget.get('1.0', 'end-1c')
    try:
        return widget.cget('text')
    except Exception:
        report(f"GUI error: widget {args[0]} has no text")
        return None


def gui_settext(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    text = str(args[1])
    if isinstance(widget, tk.Entry):
        widget.delete(0, 'end')
        widget.insert(0, text)
    elif isinstance(widget, tk.Text):
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
    else:
        try:
            widget.config(text=text)
        except Exception:
            report(f"GUI error: widget {args[0]} has no text")
    return None


def gui_setcolor(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    try:
        widget.config(background=str(args[1]), foreground=str(args[2]))
    except Exception:
        try:
            widget.config(background=str(args[1]))
        except Exception as error:
            report(f"GUI error: could not set color: {error}")
    return None


def gui_setfont(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    try:
        widget.config(font=(str(args[1]), int(args[2])))
    except Exception as error:
        report(f"GUI error: could not set font: {error}")
    return None


def gui_ischecked(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    variable = getattr(widget, 'bs_variable', None)
    if variable is None:
        report(f"GUI error: widget {args[0]} is not a checkbox")
        return None
    return bool(variable.get())


def gui_getvalue(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    try:
        return widget.get()
    except Exception:
        report(f"GUI error: widget {args[0]} has no value")
        return None


def gui_setvalue(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    try:
        widget.set(args[1])
    except Exception:
        report(f"GUI error: widget {args[0]} has no value")
    return None


def _canvas(args):
    return _lookup(args[0], (tk.Canvas,)) if _load_tk() else None


def gui_drawline(args):
    canvas = _canvas(args)
    if canvas is None:
        return None
    return canvas.create_line(args[1], args[2], args[3], args[4],
                              fill=str(args[5]), width=2)


def gui_drawrect(args):
    canvas = _canvas(args)
    if canvas is None:
        return None
    return canvas.create_rectangle(args[1], args[2], args[3], args[4],
                                   fill=str(args[5]), outline=str(args[5]))


def gui_drawoval(args):
    canvas = _canvas(args)
    if canvas is None:
        return None
    return canvas.create_oval(args[1], args[2], args[3], args[4],
                              fill=str(args[5]), outline=str(args[5]))


def gui_drawtext(args):
    canvas = _canvas(args)
    if canvas is None:
        return None
    return canvas.create_text(args[1], args[2], text=str(args[3]),
                              fill=str(args[4]))


def gui_move(args):
    canvas = _canvas(args)
    if canvas is not None:
        canvas.move(args[1], args[2], args[3])
    return None


def gui_erase(args):
    canvas = _canvas(args)
    if canvas is not None:
        canvas.delete(args[1])
    return None


def gui_clearcanvas(args):
    canvas = _canvas(args)
    if canvas is not None:
        canvas.delete('all')
    return None


def gui_onkey(args):
    window = _lookup(args[0])
    if window is None:
        return None
    callback_name = str(args[1])
    window.bind('<Key>',
                lambda event: _run_callback(callback_name, [event.keysym]))
    return None


def gui_onclick(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    callback_name = str(args[1])
    widget.bind('<Button-1>',
                lambda event: _run_callback(callback_name, [event.x, event.y]))
    return None


def gui_after(args):
    if root_window is None or not _window_alive(root_window):
        report("GUI error: create a window before calling after()")
        return None
    callback_name = str(args[1])
    root_window.after(int(args[0]), lambda: _run_callback(callback_name, []))
    return None


def gui_alert(args):
    if not _load_tk():
        return None
    messagebox.showinfo(str(args[0]), str(args[1]))
    return None


def gui_confirm(args):
    if not _load_tk():
        return None
    return bool(messagebox.askyesno(str(args[0]), str(args[1])))


def gui_prompt(args):
    if not _load_tk():
        return None
    answer = simpledialog.askstring(str(args[0]), str(args[1]))
    return answer if answer is not None else ""


BUILTINS = {
    'guiwindow':      (gui_window, 3),
    'guititle':       (gui_title, 2),
    'guiclose':       (gui_close, 1),
    'guirun':         (gui_run, 0),
    'guiframe':       (gui_frame, 1),
    'guilabel':       (gui_label, 2),
    'guibutton':      (gui_button, 3),
    'guientry':       (gui_entry, 1),
    'guitextbox':     (gui_textbox, 3),
    'guilist':        (gui_list, 3),
    'guisetitems':    (gui_setitems, 2),
    'guigetitems':    (gui_getitems, 1),
    'guiselectedindex': (gui_selectedindex, 1),
    'guiselect':      (gui_select, 2),
    'guilistsize':    (gui_listsize, 3),
    'guionerror':     (gui_onerror, 1),
    'guistoponerror': (gui_stoponerror, 1),
    'guicheckbox':    (gui_checkbox, 2),
    'guislider':      (gui_slider, 3),
    'guicanvas':      (gui_canvas, 3),
    'guipack':        (gui_pack, 1),
    'guiplace':       (gui_place, 3),
    'guigrid':        (gui_grid, 3),
    'guigettext':     (gui_gettext, 1),
    'guisettext':     (gui_settext, 2),
    'guisetcolor':    (gui_setcolor, 3),
    'guisetfont':     (gui_setfont, 3),
    'guiischecked':   (gui_ischecked, 1),
    'guigetvalue':    (gui_getvalue, 1),
    'guisetvalue':    (gui_setvalue, 2),
    'guidrawline':    (gui_drawline, 6),
    'guidrawrect':    (gui_drawrect, 6),
    'guidrawoval':    (gui_drawoval, 6),
    'guidrawtext':    (gui_drawtext, 5),
    'guimove':        (gui_move, 4),
    'guierase':       (gui_erase, 2),
    'guiclearcanvas': (gui_clearcanvas, 1),
    'guionkey':       (gui_onkey, 2),
    'guionclick':     (gui_onclick, 2),
    'guiafter':       (gui_after, 2),
    'guialert':       (gui_alert, 2),
    'guiconfirm':     (gui_confirm, 2),
    'guiprompt':      (gui_prompt, 2),
}


def is_gui_builtin(name):
    return name in BUILTINS


def call_builtin(name, args):
    if gui_thread_id is not None and gui_thread_id != threading.get_ident():
        report('GUI operations must run on the thread that created the window', kind='RuntimeError')
        return None
    handler, arity = BUILTINS[name]
    if len(args) != arity:
        report(f"Error: {name}() expects {arity} argument{'s' if arity != 1 else ''}")
        return None
    try:
        return handler(args)
    except BSError:
        raise
    except Exception as error:
        report(f"GUI error: {error}", cause=error)
        return None
