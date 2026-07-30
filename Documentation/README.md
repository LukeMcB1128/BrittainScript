# BrittainScript

A custom scripting language built in Python using PLY (Python Lex-Yacc), created as a genius hour project.

## Requirements

Python 3 and PLY must be installed:

```
pip install ply
```

---

## Running BrittainScript

All commands below are run from the `BrittainScriptInternals/` directory.

### Run a .bs file

Pass the path to any `.bs` file as an argument:

```
python3 main.py path/to/yourfile.bs
```

For example, to run the included test file:

```
python3 main.py ../TestFiles/test.bs
```

Each non-blank line in the file is parsed and executed top to bottom. Lines starting with `#` are treated as comments and skipped.

### Interactive REPL

Run without any arguments to get a live prompt where you can type expressions one at a time:

```
python3 main.py
```

```
BrittainScript — type 'exit' to quit
bs> 3 + 4
7
bs> push("hello")
hello
bs> exit
```

---

## Language Syntax

### Basic Math

```
3 + 4
10 - 3 * 2
8 / 2
```

### Power and Square Root

```
4^2          => 16
sqrroot(16)  => 4.0
```

### Pi

```
5 * pi       => 15.707...
```

### Trigonometry (input in degrees)

```
sin(90)      => 1.0
cos(0)       => 1.0
tan(45)      => 1.0
```

### Print (`push`)

```
push(3 + 4)        => prints 7
push("hello")      => prints hello
```

`push()` only prints. It does not return the printed value.

### Variables

```
name = "BrittainScript"
count = 3
```

### Comments

```
# Full-line comment
push("hello") # Inline comment
```

### Conditionals

```
cond (count > 1)
    push("count is greater than one")
end
```

Use `elif` for further conditions and `else` for the fallback. The first branch
whose condition is true runs, and the rest are skipped.

```
cond score >= 90:
    push("A")
elif score >= 80:
    push("B")
elif score >= 70:
    push("C")
else:
    push("F")
end
```

Both are optional: a `cond` on its own still works, `elif` can appear without an
`else`, and `else` can appear without any `elif`. An `else` must come last and
takes no condition.

### Null

`null` is the empty value. It is what a function returns when it returns
nothing, and what a built-in gives back when it fails.

```
x = null
push(x)                      => null
push(x == null)              => True
push(not null)               => True

cond x == null:
    push("nothing here")
end
```

`null` is falsy, so it can be tested directly:

```
value = datetime.parse(text, "%Y-%m-%d")
cond value:
    push(datetime.year(value))
else:
    push("could not read that date")
end
```

`push()` and `tostr()` render it as `null`. A bare `null` on its own line prints
nothing, the same way an assignment does.

### Loops

```
x = 0
while x < 3:
    x = x + 1
    push(x)
end

for i in space(1, 4):
    push(i)
end
```

Use `break` to exit a loop and `continue` to skip to the next iteration.

### Functions

```
func double(x):
    return x * 2
end

push(double(5))
```

Functions return values with `return`.

### Input

```
name = input("Enter your name: ")
push(name)
```

### Strings

```
push("hello" + " world")
push(len("hello"))

name = " BrittainScript "
push(name[1])
push(name[1:5])
push(name.trim().upper())

push(tonum("42") + 8)
push(tostr(42) + "!")
```

### Lists

```
nums = [1, 2, 3, 4]
push(nums[0])
nums.add(5)
push(len(nums))
```

### Grouping

```
(2 + 3) * 4   => 20
```

---

## Python Interop

BrittainScript can call into any Python library installed in the same Python
environment — `numpy`, `requests`, `torch`, anything. There is nothing to
install beyond the library itself; the interpreter's only dependency is `ply`.

### `pyimport(name)`

Imports a Python module and hands it back as an ordinary BrittainScript value.

```
np = pyimport("numpy")
json = pyimport("json")
```

If the module cannot be imported, `pyimport` prints an error and returns
nothing:

```
missing = pyimport("not_a_real_module")
=> Error: cannot import 'not_a_real_module': No module named 'not_a_real_module'
```

### Calling Python methods

Method-call syntax falls through to Python whenever the name is not one of
BrittainScript's own methods (`upper`, `lower`, `trim`, `contains`, `locate`,
`add`, `remove`, `pop`, `has`). Those built-ins always win, so existing scripts
are unaffected.

```
np = pyimport("numpy")
matrix = np.array([[1, 2], [3, 4]])

push(matrix.sum())            => 10
push(matrix.transpose())
push("a,b,c".split(","))      => ['a', 'b', 'c']
push("hello".replace("l", "L"))
```

Note that arguments are positional only — BrittainScript has no keyword
argument syntax. Where a Python API needs a keyword, look for a method form of
it (`tensor.requires_grad_()` rather than `requires_grad=true`).

### Attribute access

A dotted name with no call reads the attribute directly.

```
np = pyimport("numpy")
matrix = np.array([[1, 2], [3, 4]])

push(matrix.shape)            => (2, 2)
push(matrix.T)
push(pyimport("math").pi)     => 3.141592653589793
```

Reserved words such as `pi`, `sin`, `cos` and `tan` are treated as ordinary
names when they follow a `.`, so `math.pi` and `np.sin(x)` both work.

### The `@` operator

`@` is matrix multiplication, passed straight through to Python's `__matmul__`.

```
np = pyimport("numpy")
a = np.array([[1, 2], [3, 4]])
push(a @ a)                   => [[ 7 10]
                                  [15 22]]
```

It binds at the same level as `*`, so `x @ w + b` multiplies before it adds.

### Why this works everywhere else too

BrittainScript values are native Python objects, so once a Python object is in
a variable, the rest of the language already applies to it — arithmetic,
indexing, slicing, comparison and `for` loops all use Python's own behaviour:

```
np = pyimport("numpy")
values = np.array([10, 20, 30, 40])

push(values * 2)
push(values[1])
push(values[1:3])
for value in values:
    push(value)
end
```

### A worked example

`examples/torch_demo.bs` trains a small linear model with PyTorch, including a
hand-written SGD loop driven by autograd. Run it with:

```
python3 run.py examples/torch_demo.bs
```

It prints a message and stops if `torch` is not installed.

### A note on scope

`pyimport` gives a script the whole Python environment — including `os`,
`subprocess` and `shutil`. That is the expected trade-off for a scripting
language FFI and is the same power a Python script has, but it does mean a
`.bs` file can do anything the Python interpreter running it can do. Treat
untrusted BrittainScript the way you would treat untrusted Python.

---

## Test Files

There are two standalone test suites in `TestFiles/`. These are self-contained and independent from the main interpreter — they were used to prototype the lexer and parser separately.

### Math test (`TestFiles/TestMath/`)

Tests a basic arithmetic lexer and parser (addition, subtraction, multiplication, division). Run from inside the `TestMath` folder:

```
cd TestFiles/TestMath
python3 testcalc.py
```

You'll see a `Test:` prompt. Type a math expression and it prints the tokens it found, then the parsed result:

```
Test: 3 + 4
LexToken(NUMBER,3,1,0)
LexToken(PLUS,'+',1,2)
LexToken(NUMBER,4,1,4)
Yacc parsed:  7
```

### Text test (`TestFiles/TestText/`)

Tests a minimal text lexer and parser. Run from inside the `TestText` folder:

```
cd TestFiles/TestText
python3 testtext.py
```

You'll see an `Enter some text:` prompt. Type anything and it prints the token and the parsed result:

```
Enter some text: hello world
LexToken(TEXT,'hello world',1,0)
Parsed: hello world
```

---

## Project Structure

```
BrittainScript/
├── BrittainScriptInternals/
│   ├── main.py       — entry point (REPL + file runner)
│   ├── lexer.py      — tokenizer
│   └── parser.py     — grammar and evaluator
├── TestFiles/
│   ├── TestMath/     — standalone arithmetic test
│   └── TestText/     — standalone text test
└── Documentation/
    └── mathdocs.txt  — language reference for math features
```
