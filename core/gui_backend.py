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
        print("GUI error: tkinter is not available on this system")
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
        print(f"GUI error: no widget with id {widget_id}")
        return None
    if kinds and not isinstance(widget, kinds):
        print(f"GUI error: widget {widget_id} does not support this operation")
        return None
    return widget


def _run_callback(name, args):
    if callback_invoker is None:
        print("GUI error: no callback invoker set")
        return
    callback_invoker(name, list(args))


def gui_window(args):
    if not _load_tk():
        return None
    global root_window
    title, width, height = args
    if root_window is None or not _window_alive(root_window):
        window = tk.Tk()
        root_window = window
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
        print("GUI error: create a window before calling run()")
        return None
    root_window.mainloop()
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
        print(f"GUI error: widget {args[0]} has no text")
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
            print(f"GUI error: widget {args[0]} has no text")
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
            print(f"GUI error: could not set color: {error}")
    return None


def gui_setfont(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    try:
        widget.config(font=(str(args[1]), int(args[2])))
    except Exception as error:
        print(f"GUI error: could not set font: {error}")
    return None


def gui_ischecked(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    variable = getattr(widget, 'bs_variable', None)
    if variable is None:
        print(f"GUI error: widget {args[0]} is not a checkbox")
        return None
    return bool(variable.get())


def gui_getvalue(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    try:
        return widget.get()
    except Exception:
        print(f"GUI error: widget {args[0]} has no value")
        return None


def gui_setvalue(args):
    widget = _lookup(args[0])
    if widget is None:
        return None
    try:
        widget.set(args[1])
    except Exception:
        print(f"GUI error: widget {args[0]} has no value")
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
        print("GUI error: create a window before calling after()")
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
    handler, arity = BUILTINS[name]
    if len(args) != arity:
        print(f"Error: {name}() expects {arity} argument{'s' if arity != 1 else ''}")
        return None
    try:
        return handler(args)
    except Exception as error:
        print(f"GUI error: {error}")
        return None
