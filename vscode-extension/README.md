# BrittainScript for VS Code

Language support for [BrittainScript](https://github.com/LukeMcB1128/BrittainScript) `.bs` files.

## Features

- **Syntax highlighting** for keywords, built-in functions, strings, `f"..."` interpolation, numbers and comments.
- **Hover documentation.** Hover over a built-in such as `len`, a library function such as `ui.button` or `math.max`, a method such as `.get`, a keyword, or a library name after `add` to see what it does and how to call it. Your own functions show their signature and the `#` comment above their `func` line.
- **Completions** for library functions after `ui.`, `math.` and the other libraries, for string, list and dictionary methods, for built-ins and keywords, and for library names after `add`.
- **Run button** in the editor title bar, which runs the current file with `bs` in a terminal.

Document your own functions with a comment directly above them, and the hover shows it:

```brittainscript
# add a task to the board and clear the input
func addTask(s, event):
    s["tasks"].add(s["draft"])
    s["draft"] = ""
end
```

## Requirements

Install BrittainScript itself so the run button can find the `bs` command:

```bash
pip3 install --upgrade brittainscript
```

## Learn the language

The [language reference](https://github.com/LukeMcB1128/BrittainScript/blob/main/Documentation/LANGUAGE_REFERENCE.md) covers the syntax, built-in functions and every bundled library, including `ui` for HTML desktop apps.

```brittainscript
add ui

state = {"count": 0}

func view(s):
    return ui.page([ui.h1(f"Clicked ${s["count"]} times"), ui.primary(ui.button("Click me", "clicked"))])
end

func clicked(s, event):
    s["count"] += 1
end

ui.app("Counter", state, "view")
```
