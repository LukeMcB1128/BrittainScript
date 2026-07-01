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
