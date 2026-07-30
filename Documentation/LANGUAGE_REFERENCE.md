# BrittainScript language reference

This guide covers BrittainScript 0.4.0 as implemented in this repository.
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

The REPL exits on `exit` or `quit`. When entering a `cond`, `while`, `for`, or `func` block, it prompts for subsequent lines with `...>`; finish with `end`.

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

Native literals are numbers, double-quoted strings, lists, `true`, `false`, and `null`. `null` is the empty value and is falsy.

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
| `+`, `-`, `*`, `/` | arithmetic |
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

Precedence, highest first: indexing and member access; power; `*`, `/`, `%`, `@`; `+`, `-`; comparisons; `not`; `and`; `or`. Parentheses override it. Division/modulo by zero report an error and result in `null`.

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

The mutating list methods return `null`. Invalid indexing, an empty `pop`, and a missing `remove` print an error. Other Python methods work as a fallback, including `"a,b".split(",")`, `text.replace(...)`, `items.sort()`, and `items.index(value)`.

### Logic and comparisons

Use `==`, `!=`, `<`, `<=`, `>`, `>=`, `not`, `and`, and `or`. Logical operators produce boolean values.

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

## Built-in functions

| Function | Description |
| --- | --- |
| `push(value)` | Print a value; returns `null`. |
| `input([prompt])` | Read one input line. |
| `len(value)` | Length of a compatible value. |
| `tonum(value)` | Convert to integer or decimal; invalid input gives `null`. |
| `tostr(value)` | Convert a value to text; `null` becomes `"null"`. |
| `space(...)` | Construct an integer list. |
| `absolute(x)`, `round(x)`, `floor(x)`, `ceiling(x)` | Numeric helpers. |
| `type(value)` | Underlying Python type object. |
| `clear()` | Clear the terminal. |
| `readfile`, `readlines`, `createfile`, `writefile`, `appendfile`, `fileexists`, `deletefile` | Low-level file operations. |

File writes return `true` or `false`; failed reads return `null`. File paths use the current working directory.

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

Functions: `now()`, `parse(text, pattern)`, `format(date, pattern)`, `year(date)`, `month(date)`, `day(date)`, `hour(date)`, `minute(date)`, `second(date)`, `weekday(date)` (Monday is `0`), `isLeapYear(year)`, and `daysInMonth(year, month)`. Format patterns are Python `strftime`/`strptime` patterns. Invalid input returns `null` after an error message.

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

There are no dictionary literals or keyword arguments in BrittainScript; use APIs with positional arguments or create a Python helper. A failed import or method call reports an error and yields `null`.

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
result.rejected_features  # e.g. ['dict literals']
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
| `x += 1` | `x = (x + 1)` | no augmented assignment in the grammar |
| `-x` | `(0 - x)` | no unary minus |
| `a // b` | `floor((a / b))` | no `//`; exact for integers |
| `range(n)` | `space(n)` | different name |
| a function's local `total` | `f_total` | see below |

### Why locals get renamed

Assigning to a name inside a BrittainScript function walks outward and updates
a matching outer variable, where Python would create a local. Without renaming,
this Python prints 6, 100, 7 but the direct translation would print 6, 6, 3:

```python
total = 100
def accumulate(items):
    total = 0
    for value in items:
        total = total + value
    return total
```

So every function-local name that collides with a module-level name is renamed.

### What is rejected, and why it is rejected rather than approximated

Classes, imports, `try`/`except`, `with`, `lambda`, comprehensions, generators,
decorators, dicts, sets, tuples, `*args`, `global`, chained comparisons and
`in` have no BrittainScript equivalent. Four rejections are subtler, and each
would otherwise produce a program that runs and gives a different answer:

- **`and`/`or` returning a value.** `name or "default"` yields the string in
  Python and `true` in BrittainScript, so `and`/`or` are only accepted when
  both sides are already booleans.
- **`and`/`or` as a guard.** BrittainScript evaluates both sides, so
  `i < len(xs) and xs[i] > 0` does not protect the index.
- **`**`.** `2 ** 3` is `8` in Python and `8.0` in BrittainScript.
- **`list.pop()`.** Returns the removed item in Python, `null` here.

One known divergence is left to verification rather than rejected: Python
prints `None` where BrittainScript prints `null`, so a program that prints a
null value translates cleanly but fails the output comparison.

## Examples and tests

- [`examples/gui_demo.bs`](../examples/gui_demo.bs): GUI widgets, callbacks, dialogs, and canvas drawing.
- [`examples/orbit_focus_studio.bs`](../examples/orbit_focus_studio.bs): larger persistent GUI app.
- [`examples/torch_demo.bs`](../examples/torch_demo.bs): PyTorch autograd via the bridge (requires PyTorch).

The Python programs under [`tests/py_corpus/`](../tests/py_corpus) are the
round-trip suite: each must translate, run, and print exactly what the Python
prints.

Run the automated tests from the repository root:

```bash
python3 -m unittest discover -s tests
```

Implementation overview: `core/lexer.py` tokenizes source, `core/parser.py` parses/evaluates expressions, `core/main.py` executes files and blocks, and `core/gui_backend.py` adapts Tkinter.
