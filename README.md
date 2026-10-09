# BrittainScript

BrittainScript is a compact scripting language built in Python. It supports expressions, functions, control flow, lists, dictionaries, error handling, JSON, HTTP servers, bundled libraries, Tkinter GUI programs, and direct use of installed Python packages.

## Quick start

```bash
python3 -m pip install -e .
bs examples/gui_demo.bs
```

Or run a checkout without installing it:

```bash
python3 run.py examples/gui_demo.bs
```

```bs
func greet(name):
    return "Hello, " + name + "!"
end

push(greet("BrittainScript"))
```

Read the complete [language guide](Documentation/LANGUAGE_REFERENCE.md) for syntax, built-ins, libraries, Python interop, GUI use, examples, and safety notes.

To run the HTTP server example, install the server dependencies:

```bash
python3 -m pip install -e '.[server]'
bs examples/api_server.bs
```

Then open `http://127.0.0.1:8000/health`. BS functions handle requests directly.
Werkzeug processes routes, and Waitress serves HTTP requests.

For a complete GUI and API app in one process:

```bash
bs examples/note_vault.bs
```

Note Vault uses a native list widget, a background server, the HTTP client, JSON,
and a persistent store. It saves notes in `note_vault.json` in the current directory.
Read [unreleased changes](RELEASE_NOTES.md) for script output and callback behavior.

## License

[MIT](LICENSE)
