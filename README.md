# BrittainScript

BrittainScript is a compact scripting language built in Python. It supports expressions, functions, control flow, lists, bundled libraries, Tkinter GUI programs, and direct use of installed Python packages.

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

## License

[MIT](LICENSE)
