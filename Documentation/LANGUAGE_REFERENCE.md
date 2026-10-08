# BrittainScript language reference

This guide covers the current `dev` source code, including changes that are not yet on PyPI. The package version is `0.6.2`. An installed PyPI release can have fewer features. The short examples can use variables created in an earlier example in the same section.
BrittainScript runs through a Python interpreter. It can use Python packages installed in the same environment.

Function tables show all public built-ins and bundled library functions. In a signature, `parameter=default` means that the argument is optional. Pass arguments by position. The `=` in a signature does not mean that a call accepts keyword arguments.

- [Install and run](#install-and-run)
- [Source and values](#source-and-values)
- [Expressions and assignment](#expressions)
- [Blocks, functions, and scope](#blocks-and-functions)
- [Error handling](#error-handling)
- [Built-in functions](#built-in-functions)
- [Bundled libraries: math, convert, io, datetime, terminal, gui](#bundled-libraries)
- [JSON](#json-library), [persistent stores](#persistent-store-library), [HTTP client](#http-client-library), and [HTTP server](#http-server-library)
- [HTML apps (`ui`)](#html-app-library-ui), [web server (`web`)](#web-server-library-web), and [sockets (`net`)](#socket-library-net)
- [Direct backend functions](#direct-backend-functions)
- [Python interoperability](#python-interoperability)
- [Python translation](#translating-python-py2bs)
- [Current language limits](#current-language-limits)
- [Examples and tests](#examples-and-tests)

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
python3 core/main.py path/to/program.bs
python3 -m core.main path/to/program.bs
```

Relative file paths use the current working directory. Extra script arguments are available through `pyimport("sys").argv`. The interpreter uses the first command argument as the script path; it has no separate option parser.

The REPL exits on `exit` or `quit`. When entering a `cond`, `if`, `while`, `for`, `func`, or `try` block, it prompts for subsequent lines with `...>`; finish with `end`.

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

Variables are dynamically typed. Names use ASCII letters, digits, and underscores. The first character must be a letter or underscore. Names and library functions are case-sensitive. Use `true`, `false`, and `null` in lower case. Do not use language keywords as variable or function names. Scripts do not print bare expression results. Use `push(...)` for output. The REPL prints the result of a single expression; function bodies and blocks remain quiet.

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

`push(null)` renders `null`; a function with no explicit return also returns `null`. Printed booleans are `True` and `False`.

`type(value)` returns a Python type object, such as `int`, `float`, `str`, `list`, or `dict`. Integers have Python integer precision. Decimal and exponent literals use floating-point numbers. Python packages can supply other object types.

False values include `false`, `null`, zero, and empty strings, lists, and dictionaries. Other values use Python truth testing.

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

Precedence, highest first:

| Level | Operators |
| --- | --- |
| 1 | Member access and calls, then indexing and slicing |
| 2 | `^` |
| 3 | `*`, `/`, `//`, `%`, `@` |
| 4 | `+`, `-` |
| 5 | `<`, `<=`, `>`, `>=` |
| 6 | `==`, `!=`, `in`, `not in` |
| 7 | `not` |
| 8 | `and` |
| 9 | `or` |

Power groups from the right: `2 ^ 3 ^ 2` means `2 ^ (3 ^ 2)`. Other binary operators at the same level group from the left. Parentheses override precedence. Use `a < b and b < c` for a range test; chained comparisons do not use Python's range-test rules.

There is no unary minus. Write `0 - 4` or `0 - value`. Power uses floating-point `math.pow`; for example, `2 ^ 3` returns `8.0`. Division or modulo by zero raises `ZeroDivisionError`.

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
| `items.pop()` | Remove the last item; return `null`. |
| `items.has(value)` | test whether a list contains an item |

The native list methods `add`, `remove`, and zero-argument `pop` return `null`. `has` and `contains` return a boolean. `locate` returns a zero-based index, or `0 - 1` when absent. Invalid indexing, an empty `pop`, and a missing `remove` raise errors. Other Python methods work through the bridge. The interpreter does not restrict them to a fixed list. Arguments must still be positional. Common methods are listed below.

| Python method | Result or action |
| --- | --- |
| `text.split(separator)` | Split into a list of strings. With no argument, split on whitespace. |
| `text.replace(old, new, count)` | Replace text. Omit `count` to replace all matches. |
| `text.strip(chars)` | Remove characters from both ends. With no argument, remove whitespace. |
| `text.find(value, start, stop)` | Return the first match index, or `0 - 1`. Start and stop are optional. |
| `text.count(value)` | Count matches. |
| `text.startswith(prefix)` | Boolean prefix test. |
| `text.endswith(suffix)` | Boolean suffix test. |
| `separator.join(items)` | Join a sequence of strings. |
| `items.append(value)` | Append one item; return `null`. |
| `items.extend(values)` | Append the items of an iterable; return `null`. |
| `items.insert(index, value)` | Insert an item; return `null`. |
| `items.index(value)` | Return the first match index; raise `ValueError` if absent. |
| `items.count(value)` | Count matching items. |
| `items.reverse()` | Reverse the list in place; return `null`. |
| `items.sort()` | Sort the list in place; return `null`. |
| `items.copy()` | Return a shallow list copy. |
| `items.clear()` | Remove all items; return `null`. |
| `items.pop(index)` | Remove and return the indexed item through the Python method. |

The zero-argument native `items.pop()` returns `null`. Supplying an index uses Python's method and returns the removed item. Dictionary `record.pop(key, fallback)` uses Python's dictionary method; the fallback is optional.

An index can be negative: `items[0 - 1]` is the last item. A slice excludes its upper bound. Omitted bounds use the start or end of the value. Slice reads return a new string or list. Strings cannot be changed by indexed assignment. Lists can be changed by index or slice. A slice has no step argument.

`list()` creates an empty list. `list(iterable)` copies its items. List assignment shares the same object; use `items.copy()` or `list(items)` for a shallow copy. A shallow copy still shares nested values.

### Assignment

Use `name = value`, `items[index] = value`, or `items[start:stop] = values`. Nested targets such as `record["notes"][0]` also work.

The supported update operators are `+=`, `-=`, `*=`, `/=`, `//=`, `%=`, and `^=`. They work on names and indexed or sliced targets. The target is evaluated once. List `+=` changes the existing list, so aliases see the added items.

```bs
items = [10, 20, 30]
alias = items
items += [40]
items[1:3] = [25]
items[0] //= 3
push(alias) # [3, 25, 40]
```

Attribute assignment, unpacking, and chained assignment are not supported. Use a Python helper when an imported object needs attribute assignment.

### String interpolation

Use `f"..."` or `F"..."` with `${expression}` to insert values into text:

```bs
note = {"id": 7, "text": "café"}
push(f"Added note ${note["id"]}: ${note["text"]}.")
push(f"Next ID: ${note["id"] + 1}")
```

Fields accept BS expressions, including indexes, calls, and dictionaries.
They are converted as with `tostr`; `null` becomes `"null"`.
Fields run from left to right. Short-circuit logic can skip the whole string.
All field syntax is checked before any expression in the containing statement runs.
Assignments and format specifiers are not supported inside fields.

Ordinary strings keep `${...}` as literal text. Inside an interpolated string,
use `\${...}` for literal text. Normal string escapes and Unicode still work.
The `f` or `F` prefix is required. Existing JSON, templates, and ordinary strings keep their text.

### Dictionaries

Use `{key: value}` for a dictionary. `{}` creates an empty dictionary.

```bs
record = {"name": "Luke", "score": 10, "child": {"active": true}}
record["score"] += 1
record["email"] = "luke@example.com" # Add a key, or replace its value.
record.update({"level": 2, "active": true}) # Add several keys.
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

| Method | Result |
| --- | --- |
| `record.get(key, fallback=null)` | Value, or the fallback if the key is absent. |
| `record.has(key)` | Boolean key-presence test. |
| `record.remove(key)` | Delete the key; return `null`. A missing key raises `KeyError`. |
| `record.keys()` | Iterable view of keys. |
| `record.values()` | Iterable view of values. |
| `record.items()` | Iterable view of key/value pairs. |
| `record.copy()` | Shallow dictionary copy. |
| `record.update(other)` | Add or replace keys from a mapping or key/value pairs; return `null`. |
| `record.setdefault(key, value=null)` | Existing value, or insert and return the supplied value. |

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
ready = cond([1])       # Boolean conversion inside an expression.
push(5 >= 3 and ready) # True
```

## Blocks and functions

Close blocks with `end` and use indentation to show their structure. In a source file, a later line at the block header's indentation can also close the block. End of file does not replace the final `end`. Use explicit `end` in the REPL. A final colon on a block header is optional.

### Conditions

`if` is an alias for `cond`. Both use the same `elif`, `else`, and `end` syntax.

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

`space(stop)`, `space(start, stop)`, and `space(start, stop, step)` return integer lists. `range(...)` is an alias. The stop value is excluded. Arguments must be integers; the step cannot be zero. Use `space(3, 0, 0 - 1)` to count down. A `for` loop accepts any iterable, including lists, strings, and Python objects. `break` exits the nearest loop; `continue` starts its next iteration. Both are errors outside a loop.

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

push(classify(0 - 4))
```

Arguments are positional only. Functions may be recursive. Parameters start in a local scope. Assigning a name already found in an outer scope updates that name; an otherwise-new assignment is local to the function. `return` without a value, or reaching the end, returns `null`. `return` outside a function is an error.

### Explicit local scope

Use `local` at the start of a function to select explicit local scope. List each local name, separated by commas. Reads then use the current call and the module scope. They do not read a caller's local variables. Each call, including a recursive call, has separate local storage.

```bs
total = 100
func sum_values(values):
    local values, total, item
    total = 0
    for item in values:
        total += item
    end
    return total
end
push(sum_values([2, 3])) # 5
push(total)             # 100
```

A bare `local` selects the same scope rules without declaring names. A declared name with no assigned value raises `UnboundLocalError` when read. An undeclared name that already exists at module level can still be updated. `local` takes effect when its statement runs. It is an error outside a function.

BS function definitions are called by name. They are not first-class function values. Server, GUI, and store callbacks use function names as strings. A Python callable can be stored in a variable and called by that name.

### Discard a result

`discard expression` evaluates an expression and suppresses its result. This is useful in the REPL. Script expressions are already quiet. `discard push("Hello")` still prints `Hello`, because `push` itself prints.

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
| `problem.args` | The original Python exception arguments. |
| `problem.cause` | The original Python exception, or `null` for a BS error. |
| `problem.types` | Tuple of type names used for catch matching. |

Each frame has `function`, `file`, `line`, and `column` fields. Frames identify
the call sites. The error location identifies the failed operation. A bare raise
preserves this information.

`problem.matches("OSError")` tests a type name, including parent types. `problem.format()` returns the diagnostic text with its location and BS call stack.

Caught Python errors also expose their original attributes. For example,
`problem.code` reads an HTTP status, and `problem.errno` reads a system error
number. BS fields take precedence. Use `problem.cause` to access the original
Python exception directly.

Uncaught errors go to stderr with their type, source location, and BS call stack.
The `bs` command and `run.py` return status `1`. Successful runs return `0`.
Caught errors do not print a diagnostic or cause a failure status. The REPL prints
an uncaught error and then accepts another command.

An uncaught GUI callback error is reported to stderr, and the event loop continues.
Register `gui.onError("handler")` to pass the error to a BS handler instead.
Use `gui.stopOnError(true)` to stop on an unhandled callback error and pass it
out of `gui.run()`. A registered error handler handles the error and keeps the loop running.

This changes the earlier behavior: failed operations no longer print an error
and continue with `null`, `false`, or `0`. Use a catch handler for a fallback value.
For Python embedding, `main.execute_lines()` raises `core.diagnostics.BSError`.
`main.run_file()` prints uncaught errors and returns the status code.
The low-level PLY parser retains its earlier diagnostic interface when called
directly outside an execution context.

## Built-in functions

These functions do not need `add`.

| Function | Result or action |
| --- | --- |
| `push(value)` | Print one value and a newline; return `null`. |
| `input(prompt="")` | Read one input line and return a string without its final newline. |
| `len(value)` | Length of a compatible value. |
| `tonum(value)` | Convert to an integer, or a float if its text contains a decimal point. Invalid input raises an error. |
| `tostr(value)` | Convert to text; `null` becomes `"null"`. |
| `chr(code)` | One-character string for an integer Unicode code point. |
| `ord(text)` | Integer code point of a one-character string. |
| `invoke(name, args)` | Call the BS function named by the string `name` with the list `args`; return its result. Libraries use it to call handlers passed by name. |
| `error(message, type="RuntimeError")` | Create an error value. Both arguments must be strings. |
| `list(iterable)` | Create a list; omit the argument for an empty list. |
| `dict(source)` | Copy a mapping or key/value pairs; omit the argument for an empty dictionary. |
| `space(stop)` | Integer list from zero to the excluded stop. |
| `space(start, stop, step=1)` | Integer list with an excluded stop and a nonzero step. |
| `range(stop)` | Alias for `space(stop)`. |
| `range(start, stop, step=1)` | Alias for the corresponding `space` call. |
| `absolute(value)` | Absolute value. |
| `round(value)` | Nearest integer; exact halves round to the even integer. No precision argument. |
| `floor(value)` | Greatest integer less than or equal to the value. |
| `ceiling(value)` | Smallest integer greater than or equal to the value. |
| `sqrroot(value)` | Floating-point square root. |
| `sin(degrees)` | Sine, with input in degrees. |
| `cos(degrees)` | Cosine, with input in degrees. |
| `tan(degrees)` | Tangent, with input in degrees. |
| `type(value)` | Underlying Python type object. |
| `cond(value)` | Boolean truth test inside an expression. A statement that starts with `cond` opens a block. |
| `if(value)` | Alias for `cond(value)` inside an expression. A statement that starts with `if` opens a block. |
| `pyimport(name)` | Import an installed Python module by its string name. |
| `clear()` | Clear the terminal; return `null`. |
| `datetime(command, ...)` | Date/time operation; see the `datetime` library and direct backend functions. |

`tonum("2.5")` returns `2.5`; `tonum("2")` returns `2`. For scientific notation as text, use a decimal point, such as `tonum("2.0e3")`. A source literal such as `2e3` already works without conversion. `tonum` has no numeric-base argument.

### File functions

| Function | Result or action |
| --- | --- |
| `createfile(path)` | Create an empty file; return `true`. An existing path raises `FileExistsError`. |
| `readfile(path)` | Read the whole file as text. |
| `readlines(path)` | Return a list of lines with final newline characters removed. |
| `writefile(path, content)` | Replace the file contents with Python `str(content)`; return `true`. |
| `appendfile(path, content)` | Append Python `str(content)`; return `true`. Create the file if absent. |
| `fileexists(path)` | Return whether the path exists, including a directory. |
| `deletefile(path)` | Delete a file; return `true`. |

These operations use the platform's default text encoding. They do not add newlines. Paths use the current working directory. Parent directories must exist. Failed operations raise errors. Use `json` or `store` for structured UTF-8 data.

## Bundled libraries

Load a bundled module with `add name`, then call its functions. BS modules live in `libs/` next to the interpreter, not beside the source file. The native `server`, `http`, `store`, and `net` modules use Python backends. `web` and `ui` are written in BrittainScript.

```bs
add math
push(math.clamp(120, 0, 100))
```

To make a BS library, put `name.bs` in the interpreter's `libs/` directory and define its public functions with `func`. `add name` runs that file and makes those functions available as `name.function(...)`. Library variables follow the normal scope rules; the namespace exposes functions, not a separate data object. A later `add name` loads a new namespace. Keep one `server` namespace for a running server.

### `math`

| Function | Result |
| --- | --- |
| `math.max(a, b)` | Greater value. |
| `math.min(a, b)` | Smaller value. |
| `math.abs(value)` | Absolute value. |
| `math.clamp(value, low, high)` | Limit a value to the inclusive bounds; use `low <= high`. |
| `math.factorial(n)` | Factorial; use a non-negative integer. |
| `math.pow(base, exp)` | Repeated multiplication; use a non-negative integer exponent. |

`math.pow` is a BS loop. Use the `^` operator for floating-point powers, including negative or fractional exponents.

### `convert`

Each function takes one numeric argument and returns the converted value.

| Function | Conversion |
| --- | --- |
| `convert.inchesToCentimeters(value)` | Inches to centimeters. |
| `convert.centimetersToInches(value)` | Centimeters to inches. |
| `convert.celToFahrenheit(value)` | Celsius to Fahrenheit. |
| `convert.fahrenheitToCel(value)` | Fahrenheit to Celsius. |
| `convert.celToKelvin(value)` | Celsius to kelvin. |
| `convert.calToJoule(value)` | Calories to joules, using 4.184 joules per calorie. |
| `convert.jouleToCal(value)` | Joules to calories. |
| `convert.atmToPa(value)` | Atmospheres to pascals, using 101325 pascals per atmosphere. |
| `convert.kgToLbs(value)` | Kilograms to pounds. |
| `convert.lbsToKg(value)` | Pounds to kilograms. |
| `convert.ozToGrams(value)` | Ounces to grams, using 28.35 grams per ounce. |
| `convert.gramsToOz(value)` | Grams to ounces. |

### `io`

These wrappers use the [file functions](#file-functions), including their encoding and error rules.

| Function | Result or action |
| --- | --- |
| `io.create(path)` | Create an empty file; return `true`. Fail if it exists. |
| `io.read(path)` | Return the whole file as text. |
| `io.readLines(path)` | Return lines without final newline characters. |
| `io.write(path, content)` | Replace file contents; return `true`. |
| `io.append(path, content)` | Append content; return `true`. |
| `io.exists(path)` | Boolean path-presence test. |
| `io.delete(path)` | Delete a file; return `true`. |

### `datetime`

```bs
add datetime
now = datetime.now()
push(datetime.format(now, "%Y-%m-%d %H:%M"))
```

| Function | Result |
| --- | --- |
| `datetime.now()` | Current local Python datetime object, without timezone information. |
| `datetime.format(date, pattern)` | Formatted string. |
| `datetime.parse(text, pattern)` | Python datetime object parsed from text. |
| `datetime.year(date)` | Year number. |
| `datetime.month(date)` | Month, from 1 to 12. |
| `datetime.day(date)` | Day of the month, starting at 1. |
| `datetime.hour(date)` | Hour, from 0 to 23. |
| `datetime.minute(date)` | Minute, from 0 to 59. |
| `datetime.second(date)` | Second, from 0 to 59. |
| `datetime.weekday(date)` | Day of the week, from Monday `0` to Sunday `6`. |
| `datetime.isLeapYear(yearNum)` | Boolean leap-year test. |
| `datetime.daysInMonth(yearNum, monthNum)` | Number of days in the given month. |

Patterns use Python `strftime` and `strptime` rules. Common fields are `%Y` (year), `%m` (month), `%d` (day), `%H` (hour), `%M` (minute), and `%S` (second). Invalid input raises an error. Returned datetime objects also support Python attributes and positional method calls.

### `terminal`

These functions return strings, except `wholeDivide`, which returns an integer. They do not print. Use integer counts and widths. For `wholeDivide`, use a non-negative value and a positive divisor. For `meter`, use a non-negative value, a positive maximum, and a non-negative width. A zero or negative divisor can prevent the loop from finishing.

| Function | Result |
| --- | --- |
| `terminal.repeat(text, count)` | Repeat text `count` times. |
| `terminal.padRight(text, width)` | Add spaces until the text has at least `width` characters. Does not trim longer text. |
| `terminal.wholeDivide(value, divisor)` | Integer quotient calculated by repeated subtraction. |
| `terminal.meter(value, maximum, width)` | A bracketed progress bar with `width` positions, using `#` and `.`. |
| `terminal.rule(width)` | A line with `width` dashes between `+` characters. |
| `terminal.panel(text, width)` | Text padded or trimmed to `width`, between vertical bars. |

```bs
add terminal
push(terminal.meter(3, 5, 10)) # [######....]
```

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

| Function | Result or action |
| --- | --- |
| `gui.window(title, width, height)` | Create a window; return its handle. Width and height are pixels. |
| `gui.title(win, text)` | Change the window title. |
| `gui.close(win)` | Destroy the window. |
| `gui.run()` | Run the event loop until it stops. |
| `gui.frame(win)` | Create a container; return its handle. |
| `gui.label(win, text)` | Create a text label; return its handle. |
| `gui.button(win, text, callback)` | Create a button; return its handle. Callback receives no arguments. |
| `gui.entry(win)` | Create a single-line input; return its handle. |
| `gui.textbox(win, width, height)` | Create a multiline input; return its handle. Width is characters; height is rows. |
| `gui.list(win, items, callback)` | Create a single-selection list; return its handle. Callback receives the selected index. |
| `gui.setItems(widget, items)` | Replace list labels and clear selection. |
| `gui.getItems(widget)` | Return list labels as a list of strings. |
| `gui.selectedIndex(widget)` | Return the zero-based selected index, or `null`. |
| `gui.select(widget, index)` | Select an index without calling its callback. `null` clears selection. |
| `gui.setListSize(widget, width, height)` | Set list width in characters and height in rows; both must be positive integers. |
| `gui.onError(callback)` | Register a callback with one error parameter. `null` restores default reporting. |
| `gui.stopOnError(enabled)` | Set whether an unhandled callback error stops the loop. Default is `false`. |
| `gui.checkbox(win, text)` | Create an unchecked checkbox; return its handle. |
| `gui.slider(win, low, high)` | Create a horizontal slider between the given bounds; return its handle. |
| `gui.canvas(win, width, height)` | Create a drawing canvas; return its handle. Width and height are pixels. |
| `gui.pack(widget)` | Place a widget with the pack layout. |
| `gui.place(widget, x, y)` | Place a widget at pixel coordinates within its parent. |
| `gui.grid(widget, row, col)` | Place a widget at the given row and column, starting at zero. |
| `gui.getText(widget)` | Read an entry, textbox, or widget text such as a label. |
| `gui.setText(widget, text)` | Replace an entry, textbox, or widget text. |
| `gui.setColor(widget, background, foreground)` | Set background and foreground colors. Widgets without foreground support use background only. |
| `gui.setFont(widget, fontname, size)` | Set a widget font by name and size. |
| `gui.isChecked(widget)` | Read a checkbox as a boolean. |
| `gui.getValue(widget)` | Read a slider value; also works for an entry that supplies `get()`. |
| `gui.setValue(widget, value)` | Set a slider value. A checkbox does not use this function. |
| `gui.line(cnv, x1, y1, x2, y2, color)` | Draw a line between two pixel coordinates; return its canvas item ID. |
| `gui.rect(cnv, x1, y1, x2, y2, color)` | Draw a filled rectangle bounded by two corners; return its item ID. |
| `gui.oval(cnv, x1, y1, x2, y2, color)` | Draw a filled oval inside the given bounds; return its item ID. |
| `gui.circle(cnv, x, y, radius, color)` | Draw a filled circle with the given center and radius; return its item ID. |
| `gui.text(cnv, x, y, message, color)` | Draw centered text at pixel coordinates; return its item ID. |
| `gui.move(cnv, shape, dx, dy)` | Move a canvas item by the given offsets. |
| `gui.erase(cnv, shape)` | Delete one canvas item. |
| `gui.clearCanvas(cnv)` | Delete all canvas items. |
| `gui.onKey(win, callback)` | Bind a key event. Callback receives a Tk key name, such as `Return`. |
| `gui.onClick(widget, callback)` | Bind a left-button click. Callback receives pixel coordinates `x, y`. |
| `gui.after(milliseconds, callback)` | Schedule one callback after the given delay. Callback receives no arguments. |
| `gui.alert(title, message)` | Show an information dialog. |
| `gui.confirm(title, message)` | Show a yes/no dialog; return a boolean. |
| `gui.prompt(title, message)` | Show a text-input dialog; return a string, or an empty string on cancel. |

Widget constructors return numeric handles. Canvas drawing functions return numeric item IDs; an item ID is used with its canvas handle. Other GUI operations return `null`, except the reads and dialogs described above.

Callbacks are BS function names as strings. Define them before an event can run. Pass `null` to `gui.list` if it needs no selection callback. Create the window before its widgets or a timer. A frame or window can be a widget's parent. Do not mix `pack` and `grid` for children of the same parent.

Colors use Tk names such as `"red"` or hex values such as `"#336699"`. Font support depends on the system. `gui.after` schedules a single call; a repeating timer must schedule its next call itself. Dialogs block until the user closes them.

### GUI lists and callback errors

`gui.list(parent, items, callback)` creates a native list widget. `items` is a
list of labels. `callback` is a function name or `null`. Selection callbacks
receive the selected index, starting at zero:

```bs
func selected(index):
    push(index)
end
notes = gui.list(win, ["First note", "Second note"], "selected")
gui.pack(notes)
```

Use `gui.setItems(widget, items)` to replace the labels and clear selection.
`gui.getItems(widget)` returns the displayed strings.
`gui.selectedIndex(widget)` returns the selected index, or `null`.
`gui.select(widget, index)` selects an item without calling the callback;
`gui.select(widget, null)` clears selection.
`gui.setListSize(widget, width, height)` sets width in characters and height in rows.
Existing layout, color, and font functions also work with list widgets.

By default, callback errors print a diagnostic and leave the window running.
`gui.onError("handler")` registers a function with one error parameter.
Use `gui.onError(null)` to restore default reporting. A failed error handler
reports both errors and does not call itself again. `gui.stopOnError(true)`
restores the earlier behavior for unhandled errors; `false` is the default.
All widget operations must run on the thread that created the window.

## JSON library

Use `add json` for JSON data and files.

```bs
add json
record = json.parse("{\"name\":\"Luke\",\"active\":true}")
record["score"] = 11
push(json.stringify(record))
push(json.pretty(record, 2))
json.save("record.json", record)
record = json.load("record.json")
```

| Function | Action |
| --- | --- |
| `json.parse(text)` | Parse JSON into BS values. |
| `json.stringify(value)` | Encode compact JSON. |
| `json.pretty(value, indent)` | Encode JSON with the given indentation. |
| `json.load(path)` | Read and parse a UTF-8 file. |
| `json.save(path, value)` | Write a UTF-8 file; return `true`. |
| `json.loads(text)` | Alias for `json.parse(text)`. |
| `json.dumps(value)` | Alias for `json.stringify(value)`. |

JSON objects become dictionaries; arrays become lists. JSON booleans and `null`
become BS booleans and `null`. Object keys must be strings when encoding.
Numbers must be finite. Cycles, unsupported values, and invalid UTF-8 strings raise errors.
Shared list and dictionary values are allowed when they do not form a cycle.

Invalid JSON raises `JSONDecodeError`, which can be caught as `ValueError`.
Non-finite numbers raise `ValueError`. File errors keep their Python types.
The `indent` argument must be a non-negative integer. `json.loads(text)` and `json.dumps(value)` each accept one argument; they do not accept the options of Python's JSON module.

Saving validates and encodes the data before opening the destination file.
Invalid data therefore leaves an existing file unchanged. A successful save replaces its contents. This write is not atomic; use `store` when replacement must be atomic.

## Persistent store library

Use `add store` for a file-backed JSON dictionary:

```bs
add store
vault = store.open("vault.json")
if not vault.has("notes"):
    vault.set("notes", [])
end
push(vault.get("notes"))
```

`store.open(path)` returns a store object. The path must be a string. It creates an empty JSON object if the file does not exist.
An existing file must contain a valid JSON object. Its parent directory must exist.
Keys are strings, and saved values must be valid JSON values.

| Method | Action |
| --- | --- |
| `vault.get(key, default=null)` | Read a value; default is `null`. |
| `vault.set(key, value)` | Save a value; return `true`. |
| `vault.has(key)` | Test whether a key exists. |
| `vault.delete(key)` | Delete a key; return whether it existed. |
| `vault.keys()` | Return the keys as a list. |
| `vault.snapshot()` | Read the whole dictionary. |
| `vault.update(key, callback, default=null, args=null)` | Read, transform, and save one value under the lock; return the saved value. |
| `vault.transaction(callback, args=null)` | Transform and save the whole dictionary under the lock; return the saved dictionary. |

Reads return separate values. Changing a returned list does not save it.
Use `set` to save a replacement. Each operation reads the current file while holding the lock, so separate handles see saved changes. Use `update` or `transaction` when a complete
read-modify-write operation must hold the lock:

```bs
func increment(value):
    return value + 1
end
count = vault.update("visits", "increment", 0)
```

Callbacks are BS function names and must exist before the operation runs. The first parameter receives the old value,
or the whole dictionary for `transaction`. Optional `args` is a list of extra
arguments. A transaction callback must return a dictionary with string keys and JSON values. An update callback
returns the new value. Callback variables are separate from the caller; pass
request data through `args`. Callbacks must not call store methods, including
methods on another store. This prevents nested lock errors and stale writes.

Stores use UTF-8 JSON files. Every operation takes a thread lock and an OS file lock. All handles use a stable
`path.lock` file, which must remain in place. The data file is replaced atomically
after validation and writing a complete temporary file in the same directory.
A callback, validation, or replacement failure leaves the previous data intact.
These guarantees require a local filesystem with file locking and atomic replace.
Create a store before starting a server. Store objects remain shared across
requests while ordinary BS dictionaries remain separate.

## HTTP client library

Use `add http` to send HTTP requests. No extra dependencies are needed.

```bs
add http
response = http.get("http://127.0.0.1:8000/health")
push(response["status"])
push(response["json"])
response = http.post("http://127.0.0.1:8000/echo", {"message": "Hello"})
```

| Function | Request |
| --- | --- |
| `http.get(url, headers=null, timeout=10)` | GET. |
| `http.delete(url, headers=null, timeout=10)` | DELETE. |
| `http.head(url, headers=null, timeout=10)` | HEAD, without a response body. |
| `http.options(url, headers=null, timeout=10)` | OPTIONS. |
| `http.post(url, body=null, headers=null, timeout=10)` | POST. |
| `http.put(url, body=null, headers=null, timeout=10)` | PUT. |
| `http.patch(url, body=null, headers=null, timeout=10)` | PATCH. |
| `http.request(method, url, body=null, headers=null, timeout=10)` | One of the seven methods above, supplied as a string. |

Timeout is a positive, finite number of seconds. Each function returns the response dictionary described below.

Dictionaries, lists, numbers, and booleans are sent as JSON. Strings are sent
as UTF-8 text. Python bytes are sent as binary data. A `null` body means no body.
To send JSON `null`, supply the string `"null"` and a JSON content-type header.
Custom headers must have string names and values. URLs must use HTTP or HTTPS.
TLS certificates are checked, and standard redirects are followed. Header values cannot contain newlines. The client sets `Content-Length` and `Transfer-Encoding`; do not supply them. JSON bodies get a JSON content type unless you supply another type.

| Response key | Value |
| --- | --- |
| `"status"` | Integer HTTP status. |
| `"headers"` | Dictionary with lowercase header names. |
| `"body"` | Response text. |
| `"bytes"` | Raw Python bytes. |
| `"json"` | Parsed JSON, or `null`. |
| `"json_error"` | JSON error message, or `null`. |
| `"url"` | Final URL after redirects. |

Use dictionary indexing, for example `response["status"]`. JSON content types are parsed
automatically. Invalid JSON leaves `json` as `null` and sets `json_error` to the
parse error message. Valid JSON or a non-JSON response sets `json_error` to `null`.
Body text uses the declared charset, or UTF-8; invalid text bytes are replaced.
Use `bytes` when the exact response data is needed.

HTTP statuses such as 404 and 500 return normal response dictionaries.
Connection errors, timeouts, and responses larger than 8 MiB raise catchable
errors. These calls block until the response arrives or an error occurs.

## HTTP server library

Install the optional dependencies from a checkout:

```bash
python3 -m pip install -e '.[server]'
```

For a published version that includes this feature, use
`python3 -m pip install 'brittainscript[server]'`.
Then use `add server` and register BS functions as request handlers:

```bs
add server
func health(request):
    return {"status": "ok"}
end
func echo(request):
    return server.response(request["json"], 201)
end
discard server.get("/health", "health")
discard server.post("/echo", "echo")
discard server.run("127.0.0.1", 8000)
```

Handlers must exist before registration and take one parameter. Supply the
function name as a string. Werkzeug processes routes. Waitress serves HTTP with
four worker threads. The interpreter executes BS handlers directly.

| Function | Action |
| --- | --- |
| `server.get(path, handler)` | Register GET and HEAD requests. |
| `server.post(path, handler)` | Register POST requests. |
| `server.put(path, handler)` | Register PUT requests. |
| `server.patch(path, handler)` | Register PATCH requests. |
| `server.delete(path, handler)` | Register DELETE requests. |
| `server.head(path, handler)` | Register HEAD requests. |
| `server.options(path, handler)` | Register OPTIONS requests. |
| `server.route(method, path, handler)` | Register an HTTP method from the list above. |
| `server.response(body, status=200, headers=null)` | Create a response value with status and headers. `null` means no extra headers. |
| `server.run(host="127.0.0.1", port=8000)` | Serve until stopped; return `true` after shutdown. |
| `server.serve_background(host="127.0.0.1", port=8000)` | Start a background server; return its integer bound port. |
| `server.stop()` | Request shutdown; return `true` if the server is running. |
| `server.wait(timeout=null)` | Wait for background shutdown; return `true` when stopped or `false` on timeout. `null` has no time limit. |
| `server.is_running()` | Return whether the server is running. |
| `server.error()` | Return the last background error, or `null`. |
| `server.port()` | Return the bound port, or `null` if the server is stopped. |
| `server.app()` | Return a WSGI application for an external host or tests. |

Use a numeric IPv4 or IPv6 address for `host`. Port must be an integer from 0 to 65535. Port `0` selects an available port. Route registration returns `true`. Paths must start with `/`.
Register each method and path only once. GET includes HEAD, so a separate HEAD
handler cannot use the same path. OPTIONS is automatic unless you register it.
Routes can have parameters such as `/users/<int:user_id>` or `/files/<path:name>`.

Each handler gets a dictionary with these fields:

| Field | Value |
| --- | --- |
| `method`, `path` | The HTTP method and URL path. |
| `params` | Route parameters; an `int` parameter is a number. |
| `query` | Query strings; the first value is used for each key. |
| `query_all` | All query values as lists. |
| `headers` | Request headers with lowercase names. |
| `body` | The request body as UTF-8 text. |
| `json` | Parsed JSON for `application/json` or `application/*+json`; otherwise `null`. |

Return a dictionary, list, number, boolean, or `null` for a JSON response.
Return a string for a text response. Python byte values produce binary responses.
Use `server.response(body, status, headers)` to set a status or headers, for example
`server.response({"error": "missing"}, 404, {"X-Result": "missing"})`.
Status must be an integer from 200 to 599. Header names and values must be strings. Names must be HTTP tokens; values cannot contain newlines. The backend sets `Content-Length`, `Transfer-Encoding`, and `Connection`; do not supply them. HEAD responses have no body, and HTTP 204 responses have no body.

Invalid UTF-8 or JSON returns HTTP 400. Bodies larger than 1 MiB return HTTP 413.
Missing routes return 404; an incorrect method returns 405 with an `Allow` header. Automatic OPTIONS returns 204 with `Allow`. Route redirects keep their redirect status and `Location` header. An uncaught handler
error returns a generic 500 response and prints the BS error to stderr. Other
requests can continue. Catch errors in the handler to return a specific response.

The first call to `server.app()`, `server.run()`, or `server.serve_background()` fixes the routes, functions,
and startup variables. Define all functions and variables before this call.
Each request gets a separate copy of BS dictionaries and lists. Changes made in
one request do not change the startup data or another request. Use `store` or a database for shared persistent application data. Opaque Python objects, such as connections and
locks, remain shared; their thread safety depends on the Python package.

`server.run()` blocks. Ctrl+C or `server.stop()` starts shutdown. The backend
allows active responses up to five seconds to finish. An external WSGI host
controls its own server lifecycle. `server.stop()` controls servers started with `run` or `serve_background`.

`server.serve_background()` binds the socket before returning. Startup failures
raise in the calling BS function. The server uses a daemon thread, so it does not
keep a finished script alive. Stop it and wait in `finally` when a GUI closes:

```bs
port = server.serve_background("127.0.0.1", 0)
try:
    gui.run()
finally:
    server.stop()
    server.wait(10)
end
```

Define handlers and application variables before starting the server. GUI widget
operations must stay on the GUI thread. Call the API through `http` from GUI
callbacks. An unexpected background server error is printed to stderr and kept
by `server.error()`; `server.wait()` raises it after the thread stops.
A wait timeout must be a non-negative, finite number of seconds. A timeout does not stop the server. Call `stop` to request shutdown, then `wait` to wait for it. Call `wait` outside request handlers and store transaction callbacks.

## HTML app library (`ui`)

`add ui` builds desktop apps with HTML and CSS. The library is written in
BrittainScript: it serves the page through [`web`](#web-server-library-web),
renders elements, diffs them and handles events. No extra packages are needed.

```bs
add ui

state = {"count": 0, "name": ""}

func view(s):
    return ui.page([ui.h1(f"Clicked ${s["count"]} times"), ui.input("name", "Your name"), ui.p("Hello " + s["name"]), ui.primary(ui.button("Click me", "clicked"))])
end

func clicked(s, event):
    s["count"] += 1
end

ui.app("Counter", state, "view")
```

`ui.app(title, state, view)` starts a local server on `127.0.0.1` and opens the
page. With Chrome, Edge, Chromium or Brave installed, the page opens in an app
window without tabs or an address bar. Otherwise it opens in the default
browser. The call blocks until the window closes, `ui.quit()` runs, or Ctrl+C,
and then returns the final state.

How a frame is drawn:

1. `view(state)` returns a tree of elements. Elements are dictionaries made by the functions below.
2. A click or other event calls the named handler with `(state, event)`. A handler changes `state` in place, or returns a new state dictionary.
3. `ui` calls `view(state)` again, compares the new tree with the previous one, and sends only the changed text, attributes and elements to the window.

Handlers are function names as strings, like other BS callbacks. Only handlers
that appear on screen, or that are registered with `ui.every` and `ui.onKey`,
can be called. `event` is a dictionary:

| Key | Value |
| --- | --- |
| `"handler"` | The handler name. |
| `"arg"` | The value set with `ui.arg(element, value)`, or `null`. |
| `"key"` | The key name for `ui.onKey` handlers, such as `"Escape"`; otherwise `null`. |
| `"values"` | The current values of all bound inputs. |

An error in a handler or in `view` prints the BS diagnostic in the terminal and
shows an error toast in the window. The app keeps running.

### Bound inputs

Input functions take a state key. The field shows `state[key]`, and every
event first copies the field's current value into `state[key]`. A handler can
read the typed text from state, or set the key to change the field, for example
`s["draft"] = ""` to clear it. Text that the user is still typing is never
overwritten by unrelated updates, such as a timer.

Checkboxes, sliders and select menus redraw the page when they change, so
`view` can depend on them directly. Use `ui.live(field)` to redraw a text field
as the user types.

### Elements

| Function | Element |
| --- | --- |
| `ui.page(kids)` | Centered page column. Use it as the root. |
| `ui.row(kids)` | Horizontal, wrapping row with spacing. |
| `ui.col(kids)` | Vertical column with spacing. |
| `ui.grid(kids)` | Responsive grid of equal columns. |
| `ui.card(kids)` | Raised panel. |
| `ui.spacer()` | Fills the free space in a row. |
| `ui.divider()` | Horizontal rule. |
| `ui.h1(text)`, `ui.h2(text)`, `ui.h3(text)` | Headings. |
| `ui.p(text)` | Paragraph. |
| `ui.muted(text)` | Small secondary text. |
| `ui.text(text)` | Inline text. |
| `ui.code(text)` | Inline code. |
| `ui.badge(text)` | Small rounded label. |
| `ui.link(label, url)` | Link that opens in the browser. |
| `ui.button(label, handler)` | Button that calls `handler`. |
| `ui.input(key, placeholder)` | One-line text field bound to `state[key]`. |
| `ui.password(key, placeholder)` | Password field bound to `state[key]`. |
| `ui.textarea(key, rows)` | Multi-line text field bound to `state[key]`. |
| `ui.checkbox(key, label)` | Checkbox bound to a boolean `state[key]`. |
| `ui.slider(key, low, high)` | Range slider bound to a number `state[key]`. |
| `ui.select(key, options)` | Drop-down menu bound to `state[key]`; `options` is a list. |
| `ui.progress(value, maximum)` | Progress bar. |
| `ui.stat(label, value)` | Large number with a caption. |
| `ui.list(items)` | List; each item can be text or an element. |
| `ui.table(headers, rows)` | Table; `rows` is a list of lists. |
| `ui.empty(message)` | Placeholder for an empty area. |
| `ui.el(tag, attrs, kids)` | Any HTML element. `attrs` is a dictionary or `null`. |

`kids` is a list of elements, strings or numbers. A single value also works.
Nested lists are flattened and `null` is skipped, so a view can build a list of
items in a loop and pass it as one child. Text is always escaped.

### Modifiers

Each modifier changes the element and returns it, so modifiers can be nested:
`ui.small(ui.danger(ui.button("Delete", "remove")))`.

| Function | Effect |
| --- | --- |
| `ui.primary(el)`, `ui.danger(el)`, `ui.ghost(el)`, `ui.small(el)` | Button styles. |
| `ui.cls(el, names)` | Add CSS classes. |
| `ui.style(el, rules)` | Add inline CSS, such as `"color: red"`. |
| `ui.attr(el, name, value)` | Set an HTML attribute. `true` adds a bare attribute; `false` or `null` removes it. |
| `ui.disabled(el, flag)` | Disable a control when `flag` is `true`. |
| `ui.arg(el, value)` | Pass a JSON value to the handler as `event["arg"]`. |
| `ui.key(el, value)` | Give a list item a stable identity. |
| `ui.onClick(el, handler)` | Call a handler on click. |
| `ui.onChange(el, handler)` | Call a handler when a control changes. |
| `ui.onEnter(el, handler)` | Call a handler when Enter is pressed in a text field. |
| `ui.live(el)` | Redraw while the user types in this field. |

### App settings and commands

Call these before `ui.app`:

| Function | Effect |
| --- | --- |
| `ui.size(width, height)` | Initial app window size in pixels. |
| `ui.accent(color)` | Accent color, such as `"#0a84ff"`. |
| `ui.css(text)` | Add CSS rules after the built-in theme. |
| `ui.every(milliseconds, handler)` | Call a handler repeatedly while the window is open. |
| `ui.onKey(handler, keys)` | Call a handler for keys such as `["Escape", " ", "ArrowUp"]`. Keys typed into a text field are ignored, except Escape. |

Call these inside handlers:

| Function | Effect |
| --- | --- |
| `ui.toast(message)` | Show a short message. |
| `ui.notify(message, kind)` | Show a message; `kind` is `"info"`, `"success"` or `"error"`. |
| `ui.setTitle(text)` | Change the window title. |
| `ui.focus(key)` | Move keyboard focus to the field bound to `key`. |
| `ui.quit()` | Close the window and return from `ui.app`. |

The theme follows the system light or dark mode. The built-in classes start
with `bs-`, for example `.bs-card` and `.bs-btn`, and the colors are CSS
variables such as `--accent`, `--bg`, `--surface` and `--muted`.

Set the environment variable `BS_UI_BROWSER=tab` to open a normal browser tab,
or `BS_UI_BROWSER=none` to open nothing and print the URL only. Browsers slow
down timers in hidden windows, so a timer app should not rely on exact tick
counts while minimized.

The server accepts only `127.0.0.1` and `localhost` host names. Each window gets
a random token, and events without it are refused. Only handlers on screen can
be called. The library keeps its own state in global variables whose names
start with `_ui`; do not reuse those names.

## Web server library (`web`)

`add web` is an HTTP/1.1 server written in BrittainScript on top of `net`.
It needs no extra packages. It handles one request at a time, and each reply
closes its connection. Use the [`server`](#http-server-library) library for
multithreaded APIs.

```bs
add web

func handle(request):
    if request["path"] == "/":
        web.html(request, "<h1>Hello from BrittainScript</h1>")
    else:
        web.notFound(request)
    end
end

server = web.listen("127.0.0.1", 8080)
web.serve(server, "handle")
```

| Function | Result or action |
| --- | --- |
| `web.listen(host, port)` | Open a listening socket and return its handle. Port `0` picks a free port. |
| `web.port(server)` | Return the bound port. |
| `web.next(server, timeout)` | Wait up to `timeout` seconds and return the next request, or `null`. |
| `web.serve(server, handler)` | Call `handler(request)` for each request until `web.stop(server)`. |
| `web.stop(server)` | Make `web.serve` return after the current request. |
| `web.close(server)` | Close the listening socket. |
| `web.reply(request, status, contentType, body, headers)` | Send a response. `headers` is a dictionary or `null`. |
| `web.html(request, body)`, `web.text(request, body)` | Send HTML or plain text with status 200. |
| `web.json(request, value)` | Send a value as JSON with status 200. |
| `web.redirect(request, location)` | Send a 302 redirect. |
| `web.notFound(request)` | Send a 404 response. |
| `web.header(request, name)` | Read a request header by name, or `null`. |
| `web.parseQuery(text)` | Decode a query string into a dictionary. |
| `web.urlDecode(text)` | Decode `%XX` escapes as UTF-8. |

A request is a dictionary with `"method"`, `"path"` (decoded), `"target"` (the
raw path and query), `"query"` (a dictionary of the first value for each key),
`"headers"` (lowercase names), `"body"` (UTF-8 text) and `"done"` (`true` after
a reply). Each request gets exactly one reply. `web.serve` replies `500` when the
handler raises an error, and `204` when the handler sends nothing.
Malformed requests get a `400` reply. Headers are limited to 64 KiB and bodies to 1 MiB.
Chunked request bodies are not supported.

## Socket library (`net`)

`add net` holds the primitives that `web` and `ui` are built on. They use only
the Python standard library. Sockets are integer handles.

Network data uses *raw strings*: each character is one byte, so `len(raw)` is
the byte count. Use `net.encode(text)` before sending text and `net.decode(raw)`
after receiving it.

| Function | Result or action |
| --- | --- |
| `net.listen(host, port)` | Listen for TCP connections and return a server handle. |
| `net.port(handle)` | Return the bound port. |
| `net.wait(server, timeout)` | Return a connection handle that has data to read, or `null` after `timeout` seconds. Connections that stay idle are kept waiting and closed after 30 seconds. |
| `net.recv(conn, size)` | Read up to `size` bytes as a raw string; `""` means the peer closed. Waits up to 5 seconds. |
| `net.send(conn, raw)` | Send a raw string; return the byte count. |
| `net.close(handle)` | Close a socket; return whether it was open. |
| `net.encode(text)` | UTF-8 encode text into a raw string. |
| `net.decode(raw)` | Decode a raw string as UTF-8; invalid bytes are replaced. |
| `net.clock()` | Monotonic time in seconds, for measuring intervals. |
| `net.sleep(seconds)` | Pause. |
| `net.token()` | Random 32-character hexadecimal token. |
| `net.openApp(url, width, height)` | Open a URL in a browser app window; return `true`, or `false` when it fell back to a normal tab. |

## Direct backend functions

The bundled BS libraries call the functions below. You can also call them without `add`. Their arguments, results, and errors follow the corresponding library function. Use the library names for clearer application code.

### JSON backend

| Function | Library equivalent |
| --- | --- |
| `jsonparse(text)` | `json.parse(text)` |
| `jsonstringify(value, indent=null)` | `json.stringify(value)` when indent is `null`; otherwise `json.pretty(value, indent)`. |
| `jsonload(path)` | `json.load(path)` |
| `jsonsave(path, value)` | `json.save(path, value)` |

### Date/time backend

`datetime("command", ...)` accepts the following commands. It works without `add datetime`, and it also works after the library is loaded.

| Direct call | Library equivalent |
| --- | --- |
| `datetime("now")` | `datetime.now()` |
| `datetime("format", date, pattern)` | `datetime.format(date, pattern)` |
| `datetime("parse", text, pattern)` | `datetime.parse(text, pattern)` |
| `datetime("year", date)` | `datetime.year(date)` |
| `datetime("month", date)` | `datetime.month(date)` |
| `datetime("day", date)` | `datetime.day(date)` |
| `datetime("hour", date)` | `datetime.hour(date)` |
| `datetime("minute", date)` | `datetime.minute(date)` |
| `datetime("second", date)` | `datetime.second(date)` |
| `datetime("weekday", date)` | `datetime.weekday(date)` |
| `datetime("isLeapYear", yearNum)` | `datetime.isLeapYear(yearNum)` |
| `datetime("daysInMonth", yearNum, monthNum)` | `datetime.daysInMonth(yearNum, monthNum)` |

### GUI backend

| Direct call | Library equivalent |
| --- | --- |
| `guiwindow(title, width, height)` | `gui.window(title, width, height)` |
| `guititle(win, text)` | `gui.title(win, text)` |
| `guiclose(win)` | `gui.close(win)` |
| `guirun()` | `gui.run()` |
| `guiframe(win)` | `gui.frame(win)` |
| `guilabel(win, text)` | `gui.label(win, text)` |
| `guibutton(win, text, callback)` | `gui.button(win, text, callback)` |
| `guientry(win)` | `gui.entry(win)` |
| `guitextbox(win, width, height)` | `gui.textbox(win, width, height)` |
| `guilist(win, items, callback)` | `gui.list(win, items, callback)` |
| `guisetitems(widget, items)` | `gui.setItems(widget, items)` |
| `guigetitems(widget)` | `gui.getItems(widget)` |
| `guiselectedindex(widget)` | `gui.selectedIndex(widget)` |
| `guiselect(widget, index)` | `gui.select(widget, index)` |
| `guilistsize(widget, width, height)` | `gui.setListSize(widget, width, height)` |
| `guionerror(callback)` | `gui.onError(callback)` |
| `guistoponerror(enabled)` | `gui.stopOnError(enabled)` |
| `guicheckbox(win, text)` | `gui.checkbox(win, text)` |
| `guislider(win, low, high)` | `gui.slider(win, low, high)` |
| `guicanvas(win, width, height)` | `gui.canvas(win, width, height)` |
| `guipack(widget)` | `gui.pack(widget)` |
| `guiplace(widget, x, y)` | `gui.place(widget, x, y)` |
| `guigrid(widget, row, col)` | `gui.grid(widget, row, col)` |
| `guigettext(widget)` | `gui.getText(widget)` |
| `guisettext(widget, text)` | `gui.setText(widget, text)` |
| `guisetcolor(widget, background, foreground)` | `gui.setColor(widget, background, foreground)` |
| `guisetfont(widget, fontname, size)` | `gui.setFont(widget, fontname, size)` |
| `guiischecked(widget)` | `gui.isChecked(widget)` |
| `guigetvalue(widget)` | `gui.getValue(widget)` |
| `guisetvalue(widget, value)` | `gui.setValue(widget, value)` |
| `guidrawline(cnv, x1, y1, x2, y2, color)` | `gui.line(cnv, x1, y1, x2, y2, color)` |
| `guidrawrect(cnv, x1, y1, x2, y2, color)` | `gui.rect(cnv, x1, y1, x2, y2, color)` |
| `guidrawoval(cnv, x1, y1, x2, y2, color)` | `gui.oval(cnv, x1, y1, x2, y2, color)` |
| `guidrawtext(cnv, x, y, message, color)` | `gui.text(cnv, x, y, message, color)` |
| `guimove(cnv, shape, dx, dy)` | `gui.move(cnv, shape, dx, dy)` |
| `guierase(cnv, shape)` | `gui.erase(cnv, shape)` |
| `guiclearcanvas(cnv)` | `gui.clearCanvas(cnv)` |
| `guionkey(win, callback)` | `gui.onKey(win, callback)` |
| `guionclick(widget, callback)` | `gui.onClick(widget, callback)` |
| `guiafter(milliseconds, callback)` | `gui.after(milliseconds, callback)` |
| `guialert(title, message)` | `gui.alert(title, message)` |
| `guiconfirm(title, message)` | `gui.confirm(title, message)` |
| `guiprompt(title, message)` | `gui.prompt(title, message)` |

`gui.circle` is a BS wrapper around `guidrawoval`; there is no separate circle backend function. File backend functions are listed in [File functions](#file-functions). `http`, `store`, and `server` expose their public API through `add`, without separate global backend function names.

## Python interoperability

Use `pyimport("module")` for any Python package installed in the same environment. Imported modules and returned values support attributes, positional method calls, indexing, slicing, iteration, arithmetic, and `@` matrix multiplication.

Keyword arguments are not supported. Syntax such as `method="DELETE"` inside
a call raises `TypeError` before any argument runs. Use positional arguments.

```bs
json = pyimport("json")
data = json.loads("{\"answer\": 42}")
push(data["answer"])

np = pyimport("numpy")
a = np.array([[1, 2], [3, 4]])
push(a.shape)
push(a @ a)
```

To call a Python callable returned by another call, assign it to a name first:

```bs
builtins = pyimport("builtins")
make_tuple = builtins.tuple
pair = make_tuple(["name", "Luke"])
push(pair[0])
```

Use positional arguments or a Python helper for an API that requires keywords. Dictionary keys use indexing, such as `record["name"]`; attribute access does not read dictionary keys. Native BS library functions must be called through their namespace, such as `json.parse(...)`; they cannot be read as Python function values.

Dictionary literals can hold data from Python libraries. A failed import or method call raises a catchable error. Python exception types and their parent types are preserved.

The bridge is not sandboxed. A script can import `os`, `subprocess`, networking libraries, or any installed package with the same privileges as its Python process. Do not run untrusted `.bs` files.

## Translating Python (`py2bs`)

`py2bs` translates a subset of Python into BrittainScript. By default, it runs both programs and compares stdout. Both must also finish successfully. This check verifies the supplied run; it does not prove that every possible input has the same result.

```bash
bs-from-python program.py --out program.bs
python3 -m py2bs.cli program.py --out program.bs
```

| Option | Action |
| --- | --- |
| `--out path` | Write the translated source to this file instead of stdout. |
| `--no-verify` | Translate without running either program. |
| `--timeout seconds` | Integer time limit per program; default is 10 seconds. |

File translation returns status `0` on success, `1` on rejection or verification failure, and `2` if the input cannot be read. A directory report returns status `0`, including when some files cannot translate.

Use a directory path to get a report of translation results and rejected features:

```bash
bs-from-python somedir/
```

From Python:

```python
from py2bs import translate

source = "def double(value):\n    return value * 2\nprint(double(3))\n"
result = translate(source, verify=True, timeout=10)
result.ok                 # True when translation and the requested check succeed
result.brittainscript     # the emitted source
result.rejected_features  # e.g. ['dictionary unpacking']
result.python_stdout      # what each side actually printed
result.bs_stdout
result.error
```

With `verify=False`, `result.ok` means that translation succeeded. The two stdout fields remain `None`, because neither program runs.

### What translates

`def`, `if`/`elif`/`else`, `while`, `for`, `break`, `continue`, `return`,
`print`, `len`, `str`, `abs`, `round`, `dict`, `list`, and `range` (only as a for-loop iterable). Supported values include numbers, strings, booleans, `None`, lists, and dictionaries. Indexing, slices without a step, membership tests, arithmetic, and f-strings without conversions or format specifiers also translate.

The supported native method names are `append`, `upper`, `lower`, `strip`, `find`, `replace`, `split`, `count`, `join`, `startswith`, `endswith`, `index`, `insert`, `extend`, `reverse`, `sort`, `remove`, `get`, `keys`, `values`, `items`, `copy`, `update`, and `setdefault`.

Resolvable imports, aliases, and absolute `from module import name` forms can use the Python bridge. An `import` without an alias must name a top-level module. Relative imports and star imports are rejected. Imported objects can use attribute reads and positional calls. The translator rejects imports from its list of modules that affect files, processes, networks, or other external state. This restriction also applies with `--no-verify`; native `pyimport` has no such restriction.

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

### Error translation and rejected features

Standard Python `try`/`except`/`else`/`finally` blocks and `raise` are supported.
An exception handler can name one built-in exception type or catch all errors.
Bound exception values support `str(e)` and `e.args`. Built-in exception constructors
use the Python bridge. Handler variables are cleared after the handler runs.

Exception groups, tuple handler types, exception chaining (`raise ... from ...`),
and rebinding built-in exception type names are rejected. A catch-all handler must be last.

Classes, `with`, `lambda`, comprehensions, generators,
decorators, dictionary unpacking, sets, tuple literals, `*args`, `**kwargs`, `global`, and chained comparisons are rejected by this translator. Other rejected forms include nested functions, default arguments, keyword-only or positional-only parameters, loop `else`, conditional expressions, `assert`, `del`, annotated assignment, `nonlocal`, async functions, bitwise operators, `is`, multiple assignment, and unpacking targets. Slice steps, computed calls, keyword arguments, f-string conversions, and f-string format specifiers are also rejected. This list describes the translator; imported Python objects can provide some of these capabilities to native BS code. Three rejected forms can produce different results in the two languages:

- **`and`/`or` returning a value.** `name or "default"` yields the string in
  Python and `true` in BrittainScript, so `and`/`or` are only accepted when
  both sides are already booleans.
- **`**`.** `2 ** 3` is `8` in Python and `8.0` in BrittainScript.
- **`list.pop()`.** Returns the removed item in Python, `null` here.

Verification checks one known difference: Python prints `None` where BrittainScript prints `null`. A program that prints a null value can translate, then fail the output comparison.

## Current language limits

Write one statement per line. Expressions, calls, strings, lists, and dictionaries must fit on one source line. Use double-quoted strings; single-quoted, triple-quoted, raw, and byte literals are not supported. Negative numbers use subtraction from zero. Use decimal literals with digits before and after the decimal point, such as `0.5`.

Function parameters have no defaults, type annotations, keyword-only parameters, or argument unpacking. Calls accept positional arguments only. Function calls must supply the exact number of parameters in a BS definition. Native syntax does not include classes, lambdas, closures, comprehensions, generators, or async/await. It has no set or tuple literals, bitwise operators, ternary expressions, `with`, Python `import`, or `pass`. An empty block needs only its header and `end`. Use `add` for bundled libraries and `pyimport` for Python packages. Python packages can provide tuples, bytes, sets, classes, SQL connections, and other objects.

Slices have no step. Multiple assignment, unpacking, attribute assignment, and loop `else` are not supported. Dictionaries allow a trailing comma; lists and call arguments do not. Use a separate comparison joined by `and` for each bound in a range test.

There is no bundled SQL library. A Python driver can be imported with `pyimport`, subject to its positional-call interface. GUI calls must run on the window's thread. HTTP client calls block, so a long call from a GUI callback delays the window until it finishes.

## Examples and tests

- [`examples/error_handling.bs`](../examples/error_handling.bs): conversion errors, custom errors, and Python errors.
- [`examples/dictionaries.bs`](../examples/dictionaries.bs): dictionaries and membership tests.
- [`examples/json_data.bs`](../examples/json_data.bs): JSON parsing, output, and errors.
- [`examples/api_server.bs`](../examples/api_server.bs): HTTP routes and JSON responses; requires the server extra.
- [`examples/http_client.bs`](../examples/http_client.bs): calls the API server through the HTTP client.
- [`examples/persistent_store.bs`](../examples/persistent_store.bs): a visit counter saved in `vault.json`.
- [`examples/string_interpolation.bs`](../examples/string_interpolation.bs): `if` and interpolated strings.
- [`examples/note_vault.bs`](../examples/note_vault.bs): a GUI and API in one process with persistent notes; requires the server extra and Tkinter.
- [`examples/ui_demo.bs`](../examples/ui_demo.bs): a task board and focus timer built with the `ui` library.
- [`examples/torch_demo.bs`](../examples/torch_demo.bs): PyTorch autograd via the bridge (requires PyTorch).

The Python programs under [`tests/py_corpus/`](../tests/py_corpus) are the
round-trip suite: each must translate, run, and print exactly what the Python
prints.

Run the automated tests from the repository root:

```bash
python3 -m unittest discover -s tests
```

Install `.[server]` to include the server tests. HTTP tests use local loopback sockets.
Store tests check concurrent threads and processes. GUI unit tests use test widgets;
the native list widget has also been checked with Tkinter.

Implementation files:

| File | Purpose |
| --- | --- |
| `core/lexer.py` | Read source tokens. |
| `core/parser.py` | Parse expressions and dispatch built-in calls. |
| `core/expressions.py` | Evaluate expression trees, including short-circuit logic. |
| `core/strings.py` | Read string escapes and interpolation fields. |
| `core/main.py` | Execute files, blocks, functions, and the REPL. |
| `core/diagnostics.py` | Keep error types, source locations, and call frames. |
| `core/runtime.py` | Separate request and callback state. |
| `core/json_backend.py` | Validate, read, and write JSON values. |
| `core/store_backend.py` | Lock and replace persistent store files. |
| `core/http_backend.py` | Send HTTP requests. |
| `core/server_backend.py` | Route and serve HTTP requests. |
| `core/gui_backend.py` | Connect GUI functions to Tkinter. |
| `core/net_backend.py` | Socket primitives for `web` and `ui`. |
| `libs/web.bs`, `libs/ui.bs` | HTTP server and HTML app framework, written in BrittainScript. |
| `py2bs/` | Validate, translate, and check Python programs. |
