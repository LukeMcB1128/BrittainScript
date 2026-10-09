# BrittainScript showcase

Run any example from the repository root with `bs examples/<name>.bs` or
`python3 run.py examples/<name>.bs`.

## Focus Board

A task board and focus timer built with the `ui` library: HTML and CSS in an
app window, with every part of the app written in BrittainScript. It shows bound
inputs, keyed lists, a timer, keyboard shortcuts, toasts, and a progress ring
drawn on a canvas.

```bash
bs examples/ui_demo.bs
```

Press Space outside a text field to start or pause the timer.

## Paint

Click-to-paint drawing on a `ui` canvas, with color swatches, a shape picker,
a size slider, undo and clear. It also shows a text field that updates the page
as you type.

```bash
bs examples/ui_paint.bs
```

## Orbit Focus Studio

A full desktop productivity app built with BrittainScript's `gui` and `io` libraries.
It includes a persistent task queue, focus timer, live canvas dashboard, saved
scratchpad, session statistics, keyboard shortcuts, and summary export.

```bash
bs examples/orbit_focus_studio.bs
```

Orbit stores its data in `orbit_tasks.txt`, `orbit_notes.txt`, and
`orbit_stats.txt` in the directory where it is launched. The **Export summary**
button creates `orbit_summary.txt`.

## GUI Demo

A desktop app built with the `gui` library (`libs/gui.bs`, backed by tkinter):
a click counter, a greeter with an entry field and popup dialogs, and a canvas
you can paint on by clicking.

```bash
bs examples/gui_demo.bs
```

Import the library in your own programs with `add gui`. See the `gui` section
of the [language reference](../Documentation/LANGUAGE_REFERENCE.md) for the
full widget list.

## More examples

| File | Shows |
| --- | --- |
| `dictionaries.bs` | Dictionaries and membership tests |
| `error_handling.bs` | `try`, `catch`, custom errors and Python errors |
| `string_interpolation.bs` | `if` and `f"..."` strings |
| `json_data.bs` | Parsing and writing JSON |
| `persistent_store.bs` | A visit counter saved with `store` |
| `http_client.bs` | Calling an API with `http` |
| `api_server.bs` | HTTP routes with `server` (needs the server extra) |
| `note_vault.bs` | A GUI and API in one process (needs the server extra and tkinter) |
| `torch_demo.bs` | PyTorch through the Python bridge (needs PyTorch) |
