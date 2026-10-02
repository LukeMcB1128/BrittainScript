# BrittainScript language reference

This guide covers the current source code in this repository.
BrittainScript is a small scripting language implemented in Python, with direct access to installed Python packages when needed.

## Install and run

Requirements: Python 3.9+ and PLY 3.11+.

Install the local project to get the `bs` command:

```bash
python3 -m pip install -e .
```

Run a `.bs` program or start the REPL:

```bash
bs path/to/program.bs
bs
```

From a checkout, the equivalent commands are:

```bash
python3 run.py path/to/program.bs
python3 run.py
```

The REPL exits on `exit` or `quit`. When entering a `cond`, `while`, `for`, `func`, or `try` block, it prompts for subsequent lines with `...>`; finish with `end`.

## First program

```bs
name = input("What is your name? ")
cond name.trim() == "":
    push("Hello, stranger!")
else:
    push("Hello, " + name.trim() + "!")
end
```

## Source and values

Programs run top to bottom. Blank lines are ignored. `#` starts a comment except inside a double-quoted string.

```bs
# A comment
message = "A # inside a string is not a comment" # this is one
push(message)
```

Variables are dynamically typed. Names start with a letter or underscore, followed by letters, digits, or underscores. Assignments and a bare `null` are quiet; other bare top-level expressions print their result. Prefer `push(...)` for intentional output.

```bs
title = "BrittainScript"
count = 3
count = count + 1
items = ["tea", "coffee"]
items[1] = "water"
```

### Types

Numbers can use exponent notation, such as `1e-7` and `2E3`.

Native literals are numbers, double-quoted strings, lists, dictionaries, `true`, `false`, and `null`. `null` is the empty value and is falsy.

```bs
push(null == null) # True
push(not null)     # True
push(tostr(null))  # null
```

`push(null)` renders `null`; a function with no explicit return also returns `null`.

## Expressions

### Arithmetic

| Syntax | Meaning |
| --- | --- |
| `+`, `-`, `*`, `/`, `//` | arithmetic; `//` is floor division |
| `%` | remainder |
| `^` | power |
| `@` | matrix multiplication for Python-backed values |
| `()` | grouping |
| `sqrroot(x)` | square root |
| `sin(x)`, `cos(x)`, `tan(x)` | trigonometry, with degree input |
| `pi` | mathematical pi |

```bs
push(10 - 3 * 2)  # 4
push((2 + 3) * 4) # 20
push(2 ^ 3)       # 8.0
push(sin(90))     # 1.0
```

Precedence, highest first: indexing and member access; power; `*`, `/`, `//`, `%`, `@`; `+`, `-`; comparisons; `not`; `and`; `or`. Parentheses override it. Division or modulo by zero raises `ZeroDivisionError`.

### Strings, lists, indexes, and slices

Strings use double quotes and support typical escapes (`\n`, `\t`, `\"`, `\\`). Both strings and lists support zero-based indexing and slicing.

```bs
text = "  hello  "
push(text[1:4])
push(text.trim().upper())

scores = [10, 20, 30]
scores.add(40)
scores[0] = 15
push(scores[:2])
```

| Built-in method | Description |
| --- | --- |
| `text.upper()`, `text.lower()`, `text.trim()` | transform text |
| `text.contains(value)`, `text.locate(value)` | test/find text (`locate` returns `-1` when absent) |
| `items.add(value)` | append to a list |
| `items.remove(value)` | remove first matching item |
| `items.pop()` | remove last item |
| `items.has(value)` | test whether a list contains an item |

The mutating list methods return `null`. Invalid indexing, an empty `pop`, and a missing `remove` raise errors. Other Python methods work as a fallback, including `"a,b".split(",")`, `text.replace(...)`, `items.sort()`, and `items.index(value)`.

### Dictionaries

Use `{key: value}` for a dictionary. `{}` creates an empty dictionary.

```bs
record = {"name": "Luke", "score": 10, "child": {"active": true}}
record["score"] += 1
push(record.get("score"))
push("name" in record)
```

Keys must be hashable. Strings, numbers, booleans, and `null` can be keys.
Values can contain dictionaries and lists. A trailing comma is allowed.
Duplicate keys use the last value. Iteration visits keys in insertion order.
Assignments modify the dictionary; aliases see the same changes.

`get(key)` returns `null` for a missing key. `get(key, fallback)` supplies a fallback.
`has(key)` tests key presence, including keys whose values are `null`.
`remove(key)` deletes a key and returns `null`. Missing indexed keys and missing
keys passed to `remove` raise `KeyError`. Unhashable keys raise `TypeError`.

`keys()`, `values()`, and `items()` return Python iterable views. Use
`list(record.keys())` for a list snapshot. `copy()`, `update(other)`, and
`setdefault(key, value)` also work. `dict()` creates an empty dictionary;
`dict(other)` copies a mapping or an iterable of key/value pairs.

`in` and `not in` test dictionary keys. They also work with lists, strings,
and Python containers. Dictionaries and library namespaces are distinct values.

### Logic and comparisons

Use `==`, `!=`, `<`, `<=`, `>`, `>=`, `not`, `and`, and `or`. Logical operators produce boolean values. They evaluate from left to right.
`and` skips its right operand when the left operand is false.
`or` skips its right operand when the left operand is true.

```bs
data = null
push(data != null and data["field"] == 1) # False; the index is skipped
push(true or 1 / 0)                     # True; division is skipped
```

Expressions are parsed in full before execution. A skipped operand must still
have valid syntax. Reads, calls, and errors in skipped operands do not occur.

```bs
ready = true
push(5 >= 3 and ready) # True
```

## Blocks and functions

Blocks normally close with `end`. Use indentation for readability. A source-file block can also close on dedent, but `end` is clearer and is required for an unambiguous REPL session. A final colon is conventional but optional.

### Conditions

```bs
score = 83
cond score >= 90:
    push("A")
elif score >= 80:
    push("B")
else:
    push("F")
end
```

`elif` and `else` are optional; only the first matching branch runs. `else` takes no condition and must be last. Parentheses around a condition are optional.

### Loops

```bs
n = 0
while n < 3:
    n = n + 1
    push(n)
end

for i in space(1, 10, 2):
    push(i)
end
```

`space(stop)`, `space(start, stop)`, and `space(start, stop, step)` return lists like Python `range`. A `for` loop accepts any iterable, including lists, strings, and Python objects. `break` exits the nearest loop; `continue` starts its next iteration. Both are errors outside a loop.

### Functions and scope

```bs
func classify(value):
    cond value > 0:
        return "positive"
    elif value < 0:
        return "negative"
    end
    return "zero"
end

push(classify(-4))
```

Arguments are positional only. Functions may be recursive. Parameters start in a local scope. Assigning a name already found in an outer scope updates that name; an otherwise-new assignment is local to the function. `return` without a value, or reaching the end, returns `null`. `return` outside a function is an error.

## Error handling

An error stops the current operation. Failed expressions do not supply a replacement value.
Use `try` and `catch` to recover from an error:

```bs
try:
    count = tonum("invalid")
catch ValueError as problem:
    push(problem.type)
    push(problem.message)
finally:
    push("Cleanup complete")
end
```

The first matching `catch` runs. These forms are supported:

| Form | Action |
| --- | --- |
| `catch ValueError:` | Catch one error type. |
| `catch ValueError as problem:` | Catch that type and bind an error value. |
| `catch as problem:` | Catch any error and bind its value. |
| `catch:` | Catch any error. |

Python error types keep their names and parent types. For example, `catch OSError`
also catches `FileNotFoundError`. `Error` and `Exception` catch all BS errors.
A handler that catches all errors must be last. Errors raised in a handler pass
to an outer `try`. They do not pass to another handler in the same block.

A catch variable is cleared when its handler finishes, including on return or error.
Copy it to another variable if you need it later. If that name had an earlier value,
the earlier binding is also removed. Other variables follow the normal scope rules.

`finally` runs after success or failure. It also runs on `return`, `break`, and
`continue`. A return or error in `finally` replaces any pending return or error.
An optional `else` after the catch handlers runs only when the try body succeeds.
Errors from `else` pass to an outer handler. A try block needs at least one catch
handler or a finally block.

### Raise an error

```bs
func require_positive(value):
    cond value <= 0:
        raise error("Value must be positive", "ValidationError")
    end
    return value
end

try:
    require_positive(0)
catch ValidationError as problem:
    push(problem.message)
end
```

`error(message)` creates a `RuntimeError` value. An optional second string gives
its type. A custom type must be a valid name. It can also be caught as `RuntimeError`,
`Exception`, or `Error`. `raise "message"` raises a `RuntimeError` directly.
`raise` without an expression raises the active error again and keeps its original
location and call stack. It is an error when no error is active.
Python exception objects from the bridge can also be raised.

### Error fields and command status

| Field | Value |
| --- | --- |
| `problem.type` | Error type name. |
| `problem.message` | Error message. |
| `problem.file` | Source file, or `<input>` or `<repl>`. |
| `problem.line`, `problem.column` | Source location, starting at 1. |
| `problem.stack` | List of BS function call frames, from outer to inner. |

Each frame has `function`, `file`, `line`, and `column` fields. Frames identify
the call sites. The error location identifies the failed operation. A bare raise
preserves this information.

Uncaught errors go to stderr with their type, source location, and BS call stack.
The `bs` command and `run.py` return status `1`. Successful runs return `0`.
Caught errors do not print a diagnostic or cause a failure status. The REPL prints
an uncaught error and then accepts another command.

An uncaught GUI callback error stops the event loop and passes out of `gui.run()`.
A catch handler around that call can recover from it. Catch an error inside the
callback if the event loop must continue.

This changes the earlier behavior: failed operations no longer print an error
and continue with `null`, `false`, or `0`. Use a catch handler for a fallback value.
For Python embedding, `main.execute_lines()` raises `core.diagnostics.BSError`.
`main.run_file()` prints uncaught errors and returns the status code.
The low-level PLY parser retains its earlier diagnostic interface when called
directly outside an execution context.

## Built-in functions

| Function | Description |
| --- | --- |
| `push(value)` | Print a value; returns `null`. |
| `input([prompt])` | Read one input line. |
| `len(value)` | Length of a compatible value. |
| `tonum(value)` | Convert to integer or decimal; invalid input raises `ValueError`. |
| `error(message, type)` | Create an error value; the type string is optional. |
| `tostr(value)` | Convert a value to text; `null` becomes `"null"`. |
| `space(...)` | Construct an integer list. |
| `absolute(x)`, `round(x)`, `floor(x)`, `ceiling(x)` | Numeric helpers. |
| `type(value)` | Underlying Python type object. |
| `clear()` | Clear the terminal. |
| `readfile`, `readlines`, `createfile`, `writefile`, `appendfile`, `fileexists`, `deletefile` | Low-level file operations. |

File writes return `true` on success. Failed reads and writes raise errors. File paths use the current working directory.

## Bundled libraries

Load a bundled module with `add name`, then call its functions. Modules live in `libs/` next to the interpreter, not beside the source file.

```bs
add math
push(math.clamp(120, 0, 100))
```

### `math`

`max(a, b)`, `min(a, b)`, `abs(x)`, `clamp(x, low, high)`, `factorial(n)`, and `pow(base, exp)`.

### `convert`

`inchesToCentimeters`, `centimetersToInches`, `celToFahrenheit`, `fahrenheitToCel`, `celToKelvin`, `calToJoule`, `jouleToCal`, `atmToPa`, `kgToLbs`, `lbsToKg`, `ozToGrams`, and `gramsToOz`.

### `io`

`io.create(path)`, `io.read(path)`, `io.readLines(path)`, `io.write(path, content)`, `io.append(path, content)`, `io.exists(path)`, and `io.delete(path)` are readable aliases for the low-level file API.

### `datetime`

```bs
add datetime
now = datetime.now()
push(datetime.format(now, "%Y-%m-%d %H:%M"))
```

Functions: `now()`, `parse(text, pattern)`, `format(date, pattern)`, `year(date)`, `month(date)`, `day(date)`, `hour(date)`, `minute(date)`, `second(date)`, `weekday(date)` (Monday is `0`), `isLeapYear(year)`, and `daysInMonth(year, month)`. Format patterns are Python `strftime`/`strptime` patterns. Invalid input raises an error.

### `terminal`

Text-interface helpers: `repeat(text, count)`, `padRight(text, width)`, `wholeDivide(value, divisor)`, `meter(value, maximum, width)`, `rule(width)`, and `panel(text, width)`.

### `gui`

`gui` wraps Tkinter and needs a graphical desktop with Tkinter installed. Widgets are numeric handles. Create the window and widgets, lay them out, then call `gui.run()`.

```bs
add gui

func greet():
    gui.setText(message, "Hello, " + gui.getText(name) + "!")
end

win = gui.window("Greeter", 320, 160)
name = gui.entry(win)
button = gui.button(win, "Greet", "greet")
message = gui.label(win, "")
gui.pack(name)
gui.pack(button)
gui.pack(message)
gui.run()
```

| Group | Functions |
| --- | --- |
| Windows | `window`, `title`, `close`, `run` |
| Widgets | `frame`, `label`, `button`, `entry`, `textbox`, `checkbox`, `slider`, `canvas` |
| Layout | `pack`, `place`, `grid` |
| State | `getText`, `setText`, `setColor`, `setFont`, `isChecked`, `getValue`, `setValue` |
| Canvas | `line`, `rect`, `oval`, `circle`, `text`, `move`, `erase`, `clearCanvas` |
| Events | `onKey`, `onClick`, `after` |
| Dialogs | `alert`, `confirm`, `prompt` |

Callbacks are function names as strings. Button and timer callbacks receive no arguments; `onKey` gets a key name and `onClick` gets `x, y`. See [`examples/gui_demo.bs`](../examples/gui_demo.bs).

## Python interoperability

Use `pyimport("module")` for any Python package installed in the same environment. Imported modules and returned values support attributes, positional method calls, indexing, slicing, iteration, arithmetic, and `@` matrix multiplication.

```bs
json = pyimport("json")
data = json.loads("{\"answer\": 42}")
push(data["answer"])

np = pyimport("numpy")
a = np.array([[1, 2], [3, 4]])
push(a.shape)
push(a @ a)
```

Dictionary literals can hold data from Python libraries. Keyword arguments are not supported; use positional arguments or a Python helper. A failed import or method call raises a catchable error. Python exception types and their parent types are preserved.

The bridge is not sandboxed. A script can import `os`, `subprocess`, networking libraries, or any installed package with the same privileges as its Python process. Do not run untrusted `.bs` files.

## Translating Python (`py2bs`)

`py2bs` turns a subset of Python into BrittainScript and, by default, *proves*
each translation by running both programs and comparing their output.

```bash
bs-from-python program.py --out program.bs
```

Point it at a directory to get a rejection-frequency report instead:

```bash
bs-from-python somedir/
```

From Python:

```python
from py2bs import translate

result = translate(source, verify=True)
result.ok                 # translated and both programs printed the same thing
result.brittainscript     # the emitted source
result.rejected_features  # e.g. ['dictionary unpacking']
result.python_stdout      # what each side actually printed
result.bs_stdout
result.error
```

### What translates

`def`, `if`/`elif`/`else`, `while`, `for`, `break`, `continue`, `return`,
`print`, `len`, `str`, `abs`, `round`, `range` (as a for-loop iterable), list
literals, indexing and slicing, f-strings without format specifiers, and the
list/string methods that behave identically in both languages.

These are rewritten on the way through:

| Python | emitted | why |
|---|---|---|
| `x += 1` | `x += 1` | preserves in-place mutation and evaluates the target once |
| `-x` | `(0 - x)` | no unary minus |
| `a // b` | `(a // b)` | uses native floor division without a float conversion |
| `range(n)` | `space(n)` | different name |
| a function's local `total` | `local total` | keeps the variable in the current call |

### Local variables and unused results

Each translated function starts with a `local` statement. This statement lists
its parameters and local variables. Each call has separate local storage,
including recursive calls. Reads use the current function scope and the module
scope. They do not use a caller's local variables.

A `local` statement with no names still selects this scope behavior. Native
functions without a `local` statement keep the scope behavior described above.

Python discards unused expression results. The translator emits `discard
expression` for these statements. The expression runs, but its result does not
print. Explicit `print(...)` calls still produce output.

Validation checks module paths without importing parent packages. Verification
runs both programs. Interpreter errors use stderr during verification and cause
a non-zero exit status. Program output remains on stdout, including messages
that start with `Error:` or `Syntax error`.

### What is rejected, and why it is rejected rather than approximated

Standard Python `try`/`except`/`else`/`finally` blocks and `raise` are supported.
An exception handler can name one built-in exception type or catch all errors.
Bound exception values support `str(e)` and `e.args`. Built-in exception constructors
use the Python bridge. Handler variables are cleared after the handler runs.

Exception groups, tuple handler types, exception chaining (`raise ... from ...`),
and rebinding built-in exception type names are rejected. A catch-all handler must be last.

Classes, `with`, `lambda`, comprehensions, generators,
decorators, dictionary unpacking, sets, tuples, `*args`, `global`, and chained comparisons
have no BrittainScript equivalent. Three rejections are subtler, and each
would otherwise produce a program that runs and gives a different answer:

- **`and`/`or` returning a value.** `name or "default"` yields the string in
  Python and `true` in BrittainScript, so `and`/`or` are only accepted when
  both sides are already booleans.
- **`**`.** `2 ** 3` is `8` in Python and `8.0` in BrittainScript.
- **`list.pop()`.** Returns the removed item in Python, `null` here.

One known divergence is left to verification rather than rejected: Python
prints `None` where BrittainScript prints `null`, so a program that prints a
null value translates cleanly but fails the output comparison.

## Examples and tests

- [`examples/gui_demo.bs`](../examples/gui_demo.bs): GUI widgets, callbacks, dialogs, and canvas drawing.
- [`examples/error_handling.bs`](../examples/error_handling.bs): conversion errors, custom errors, and Python errors.
- [`examples/orbit_focus_studio.bs`](../examples/orbit_focus_studio.bs): larger persistent GUI app.
- [`examples/torch_demo.bs`](../examples/torch_demo.bs): PyTorch autograd via the bridge (requires PyTorch).

The Python programs under [`tests/py_corpus/`](../tests/py_corpus) are the
round-trip suite: each must translate, run, and print exactly what the Python
prints.

Run the automated tests from the repository root:

```bash
python3 -m unittest discover -s tests
```

Implementation overview: `core/lexer.py` tokenizes source, `core/parser.py` parses expressions, `core/expressions.py` evaluates expression trees, `core/main.py` executes files and blocks, and `core/gui_backend.py` adapts Tkinter.
