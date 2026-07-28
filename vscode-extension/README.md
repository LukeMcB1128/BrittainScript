# BrittainScript

## Installation

1. Install the BrittainScript extension from the VS Code Marketplace
2. Use pip(or pip3) to install brittainscript
3. Open any `.bs` file to get syntax highlighting and language support
4. Use the integrated terminal to run your scripts

Use:

```bash
pip3 install brittainscript
# or
pip install brittainscript
```

## Running BrittainScript

### Run a Script File

Open a `.bs` file, press the run button, and press **Ctrl+Shift+B** (or Cmd+Shift+B on Mac) to run:

```brittainscript
// example.bs
push("Hello, BrittainScript!")
```

Or use the terminal:

```bash
python3 main.py path/to/yourfile.bs
```

### Interactive REPL

Open the integrated terminal and run:

```bash
python3 main.py
```

Then type expressions one at a time:

```
bs> 3 + 4
7
bs> push("hello")
hello
bs> exit
```

---

## Language Syntax

### Variables

```brittainscript
name = "BrittainScript"
count = 42
```

### Math Operations

```brittainscript
result = 3 + 4           # 7
result = 10 - 3          # 7
result = 3 * 2           # 6
result = 8 / 2           # 4
result = 10 % 3          # 1
result = 2 ^ 3           # 8
result = sqrroot(16)     # 4.0
```

### Trigonometry (degrees)

```brittainscript
result = sin(90)         # 1.0
result = cos(0)          # 1.0
result = tan(45)         # 1.0
result = pi              # 3.14159...
```

### Strings

```brittainscript
text = "hello" + " world"
length = len(text)
char = text[0]           # "h"
slice = text[0:5]        # "hello"

upper = text.upper()     # "HELLO WORLD"
lower = text.lower()     # "hello world"
trimmed = "  text  ".trim()  # "text"

has_substring = text.contains("world")    # true
index = text.locate("world")              # 6
```

### Type Conversion

```brittainscript
num = tonum("42")        # 42
str = tostr(42)          # "42"
t = type(42)             # <class 'int'>
```

### Lists

```brittainscript
nums = [1, 2, 3, 4]
first = nums[0]          # 1
length = len(nums)       # 4

nums.add(5)              # [1, 2, 3, 4, 5]
nums.remove(3)           # [1, 2, 4, 5]
nums.pop()               # [1, 2, 4]
has_element = nums.has(2)  # true

slice = nums[0:2]        # [1, 2]
```

### Boolean Logic

```brittainscript
result = true and false       # false
result = true or false        # true
result = not true             # false
```

### Comparisons

```brittainscript
result = 5 == 5          # true
result = 5 != 3          # true
result = 5 > 3           # true
result = 3 < 5           # true
result = 5 >= 5          # true
result = 3 <= 5          # true
```

### Conditionals

```brittainscript
cond (count > 1):
    push("count is greater than one")
end
```

### Loops

```brittainscript
# While loop
x = 0
while x < 3:
    x = x + 1
    push(x)
end

# For loop with range
for i in space(1, 4):
    push(i)
end

# Range with step
for i in space(0, 10, 2):
    push(i)  # 0, 2, 4, 6, 8
end

# Break and continue
while true:
    x = x + 1
    cond (x == 5):
        break
    end
    cond (x == 2):
        continue
    end
    push(x)
end
```

### Functions

```brittainscript
func double(x):
    return x * 2
end

func greet(name):
    push("Hello, " + name)
    return "Greeted"
end

result = double(5)       # 10
msg = greet("Luke")      # prints "Hello, Luke"
```

### Input/Output

```brittainscript
push("Hello, World!")
name = input("Enter your name: ")
push(name)
```

### Comments

```brittainscript
# This is a full-line comment
push(5)  # This is an inline comment
```

### Grouping

```brittainscript
result = (2 + 3) * 4    # 20
```

---

## Modules

### Math Module

```brittainscript
add math

a = math.max(10, 50)     # 50
b = math.min(10, 50)     # 10
c = math.abs(-5)         # 5
d = math.clamp(15, 0, 10)  # 10
e = math.factorial(5)    # 120
f = math.pow(2, 8)       # 256
```

### Convert Module

```brittainscript
add convert

fahrenheit = convert.celToFahrenheit(0)       # 32
celsius = convert.fahrenheitToCel(32)         # 0.0
```

### IO Module

```brittainscript
add io

io.write("notes.txt", "hello")            # overwrites the file, returns true
io.append("notes.txt", " world")          # appends to the file, returns true
text = io.read("notes.txt")               # "hello world"
lines = io.readLines("notes.txt")         # each line as a list entry, no "\n"
exists = io.exists("notes.txt")           # true
io.delete("notes.txt")                    # deletes the file, returns true

io.print("Hello!")                        # same as push()
name = io.read_input("Name: ")            # same as input()
```

### Datetime Module

Work with dates and times. `now()` and `parse()` return a date value you pass to the other functions.

```brittainscript
add datetime

t = datetime.now()
push(datetime.format(t, "%Y-%m-%d %H:%M:%S"))   # "2026-07-06 14:30:00"

push(datetime.year(t))                # 2026
push(datetime.month(t))               # 1-12
push(datetime.day(t))                 # 1-31
push(datetime.hour(t))                # 0-23
push(datetime.minute(t))              # 0-59
push(datetime.second(t))              # 0-59
push(datetime.weekday(t))             # 0 = Monday ... 6 = Sunday

birthday = datetime.parse("2024-02-29", "%Y-%m-%d")
push(datetime.year(birthday))         # 2024

push(datetime.isLeapYear(2024))       # true
push(datetime.daysInMonth(2024, 2))   # 29
```

Format patterns use the standard codes: `%Y` year, `%m` month, `%d` day, `%H` hour (24h), `%M` minute, `%S` second. Invalid input (a bad format, month 13, etc.) prints an error and returns nothing instead of stopping the program.

### GUI Module

Build desktop windows, widgets, and canvas graphics (backed by tkinter). Widgets are plain number ids, and callbacks are function names passed as strings.

```brittainscript
add gui

count = 0

win = gui.window("My App", 400, 300)     # returns a window id

label = gui.label(win, "Clicks: 0")
gui.pack(label)

func on_click():
    count = count + 1
    gui.setText(label, "Clicks: " + tostr(count))
end

button = gui.button(win, "Click me", "on_click")
gui.pack(button)

gui.run()                                # starts the event loop (blocks)
```

**Windows & app**

| Function | Description |
|----------|-------------|
| `gui.window(title, width, height)` | create a window, returns its id |
| `gui.title(win, text)` | change a window's title |
| `gui.close(win)` | close a window |
| `gui.run()` | start the event loop (call last) |

**Widgets** (all return a widget id)

| Function | Description |
|----------|-------------|
| `gui.label(win, text)` | text label |
| `gui.button(win, text, callback)` | button; `callback` is a function name string |
| `gui.entry(win)` | single-line text input |
| `gui.textbox(win, width, height)` | multi-line text input (chars × lines) |
| `gui.checkbox(win, text)` | checkbox |
| `gui.slider(win, low, high)` | horizontal slider |
| `gui.canvas(win, width, height)` | drawing canvas (pixels) |
| `gui.frame(win)` | container for grouping widgets |

**Layout** — every widget needs one of these to appear

| Function | Description |
|----------|-------------|
| `gui.pack(widget)` | stack top-to-bottom |
| `gui.place(widget, x, y)` | exact pixel position |
| `gui.grid(widget, row, col)` | row/column grid |

**Widget state**

| Function | Description |
|----------|-------------|
| `gui.getText(widget)` / `gui.setText(widget, text)` | read/write label, entry, textbox, or button text |
| `gui.setColor(widget, background, foreground)` | color names (`"red"`) or hex (`"#ff0000"`) |
| `gui.setFont(widget, name, size)` | e.g. `gui.setFont(label, "Helvetica", 20)` |
| `gui.isChecked(checkbox)` | `true`/`false` |
| `gui.getValue(slider)` / `gui.setValue(slider, value)` | read/write slider position |

**Canvas drawing** — shapes return an id for `move`/`erase`

| Function | Description |
|----------|-------------|
| `gui.line(cnv, x1, y1, x2, y2, color)` | line segment |
| `gui.rect(cnv, x1, y1, x2, y2, color)` | filled rectangle |
| `gui.oval(cnv, x1, y1, x2, y2, color)` | filled oval in a bounding box |
| `gui.circle(cnv, x, y, radius, color)` | filled circle around a center point |
| `gui.text(cnv, x, y, message, color)` | draw text |
| `gui.move(cnv, shape, dx, dy)` | shift a shape |
| `gui.erase(cnv, shape)` | remove one shape |
| `gui.clearCanvas(cnv)` | remove everything |

**Events, timers, dialogs**

| Function | Description |
|----------|-------------|
| `gui.onClick(widget, callback)` | callback receives `(x, y)` |
| `gui.onKey(win, callback)` | callback receives `(key)`, e.g. `"a"`, `"Left"`, `"space"` |
| `gui.after(ms, callback)` | run a zero-arg function once after a delay; re-schedule inside the callback for animation |
| `gui.alert(title, message)` | info popup |
| `gui.confirm(title, message)` | yes/no popup, returns `true`/`false` |
| `gui.prompt(title, message)` | text input popup, returns the string |

See `examples/gui_demo.bs` for a full program with a click counter, greeter, and paintable canvas.

### Importing Multiple Modules

```brittainscript
add math
add convert

value = math.max(10, 20)
temp = convert.celToFahrenheit(value)
push(temp)
```

---

## Python Interop

BrittainScript can call into any Python library installed in the same Python
environment — `numpy`, `requests`, `torch`, anything. Nothing to install beyond
the library itself; the interpreter's only dependency is `ply`.

### `pyimport(name)`

```brittainscript
np = pyimport("numpy")
json = pyimport("json")

missing = pyimport("not_a_real_module")
# Error: cannot import 'not_a_real_module': No module named 'not_a_real_module'
```

### Calling Python methods

Method calls fall through to Python whenever the name is not one of
BrittainScript's own methods (`upper`, `lower`, `trim`, `contains`, `locate`,
`add`, `remove`, `pop`, `has`). Those built-ins always take priority, so
existing scripts behave exactly as before.

```brittainscript
np = pyimport("numpy")
matrix = np.array([[1, 2], [3, 4]])

push(matrix.sum())                  # 10
push("a,b,c".split(","))            # ['a', 'b', 'c']
push("hello".replace("l", "L"))     # heLLo
```

Arguments are positional only — there is no keyword argument syntax. Where a
Python API needs a keyword, look for a method form of it
(`tensor.requires_grad_()` rather than `requires_grad=true`).

### Attribute access

A dotted name with no call reads the attribute directly.

```brittainscript
np = pyimport("numpy")
matrix = np.array([[1, 2], [3, 4]])

push(matrix.shape)                  # (2, 2)
push(matrix.T)
push(pyimport("math").pi)           # 3.141592653589793
```

Reserved words like `pi`, `sin`, `cos` and `tan` count as ordinary names after
a `.`, so `math.pi` and `np.sin(x)` both work.

### The `@` operator

`@` is matrix multiplication, passed straight through to Python. It binds at
the same level as `*`, so `x @ w + b` multiplies before it adds.

```brittainscript
np = pyimport("numpy")
a = np.array([[1, 2], [3, 4]])
push(a @ a)                         # [[ 7 10]
                                    #  [15 22]]
```

### Everything else already works

BrittainScript values are native Python objects, so arithmetic, indexing,
slicing, comparison and `for` loops all apply to imported objects directly:

```brittainscript
np = pyimport("numpy")
values = np.array([10, 20, 30, 40])

push(values * 2)                    # [20 40 60 80]
push(values[1:3])                   # [20 30]
for value in values:
    push(value)
end
```

`examples/torch_demo.bs` in the repository trains a small linear model with
PyTorch, autograd and a hand-written SGD loop.

**A note on scope:** `pyimport` gives a script the whole Python environment,
including `os` and `subprocess`. That is the expected trade-off for a scripting
language FFI — it is the same power a Python script has — but it does mean a
`.bs` file can do anything the Python interpreter running it can do. Treat
untrusted BrittainScript the way you would treat untrusted Python.

---

## Built-in Functions

| Function | Example | Returns |
|----------|---------|---------|
| `len()` | `len("hello")` | `5` |
| `tonum()` | `tonum("42")` | `42` |
| `tostr()` | `tostr(42)` | `"42"` |
| `input()` | `input("Prompt: ")` | user input |
| `space()` | `space(1, 5)` | `[1, 2, 3, 4]` |
| `push()` | `push("text")` | prints to console |
| `type()` | `type(42)` | `<class 'int'>` |
| `round()` | `round(3.7)` | `4` |
| `floor()` | `floor(3.7)` | `3` |
| `ceiling()` | `ceiling(3.2)` | `4` |
| `absolute()` | `absolute(-5)` | `5` |
| `sqrroot()` | `sqrroot(16)` | `4.0` |
| `sin()` | `sin(90)` | `1.0` |
| `cos()` | `cos(0)` | `1.0` |
| `tan()` | `tan(45)` | `1.0` |
| `clear()` | `clear()` | clears terminal |
| `readfile()` | `readfile("a.txt")` | file contents as a string |
| `readlines()` | `readlines("a.txt")` | file contents as a list of lines |
| `writefile()` | `writefile("a.txt", "hi")` | overwrites file, returns `true`/`false` |
| `appendfile()` | `appendfile("a.txt", "hi")` | appends to file, returns `true`/`false` |
| `fileexists()` | `fileexists("a.txt")` | `true`/`false` |
| `deletefile()` | `deletefile("a.txt")` | deletes file, returns `true`/`false` |
| `pyimport()` | `pyimport("numpy")` | the imported Python module |

---

## Operator Precedence

From highest to lowest:

1. `[]` — Brackets (indexing/slicing)
2. `^` — Power
3. `*`, `/`, `@` — Multiply, Divide, Matrix multiply
4. `+`, `-` — Plus, Minus
5. `<`, `>`, `<=`, `>=`, `==`, `!=` — Comparisons
6. `not` — Logical NOT
7. `and` — Logical AND
8. `or` — Logical OR

---

## Tips & Tricks

- **Escape sequences**: Use `\n` for newline, `\t` for tab, `\\` for backslash
- **Negative indexing**: `list[-1]` gets the last element
- **Open slices**: `list[:3]` and `list[2:]` work as expected
- **Mixed-type lists**: `[1, "hello", true, 3.14]` is valid
- **Recursion**: Functions can call themselves
- **Variable scope**: Function parameters are local; outer variables are global

---

## Troubleshooting

### Syntax Error: missing end

Make sure all `cond`, `while`, `for`, and `func` blocks end with `end`:

```brittainscript
# Wrong
cond (x > 5):
    push("yes")

# Correct
cond (x > 5):
    push("yes")
end
```

### Undefined function error

Check that the function is defined before calling it:

```brittainscript
result = double(5)  # Error: not defined yet

func double(x):
    return x * 2
end

result = double(5)  # OK
```

### Module not found

Make sure to import the module with `add`:

```brittainscript
add math
result = math.max(1, 2)  # OK
```

---

## Example Programs

### Factorial Calculator

```brittainscript
add math

n = input("Enter a number: ")
num = tonum(n)
result = math.factorial(num)
push("Factorial: " + tostr(result))
```

### Temperature Converter

```brittainscript
add convert

celsius = input("Enter temperature in Celsius: ")
c = tonum(celsius)
f = convert.celToFahrenheit(c)
push(tostr(c) + "°C = " + tostr(f) + "°F")
```

### List Operations

```brittainscript
nums = [5, 2, 8, 1, 9]
push("Original: " + tostr(nums))

nums.add(3)
push("After add: " + tostr(nums))

max_val = 0
for i in nums:
    cond (i > max_val):
        max_val = i
    end
end
push("Max: " + tostr(max_val))
```

---

## Resources

- **Official Repository**: [GitHub BrittainScript](https://github.com/LukeMcB1128/BrittainScript)
- **Issue Tracker**: Report bugs and request features
- **Documentation**: See README.md in the repository

---