import sys
import lexer as lexer_module
import parser as parser_module

def execute_line(line):
    result = parser_module.parser.parse(line, lexer=lexer_module.lexer.clone())
    if result is not None:
        print(result)

def execute_lines(lines):
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith('#'):
            i += 1
            continue

        first_word = line.split()[0]
        if first_word == 'cond':
            condition = parser_module.parser.parse(line, lexer=lexer_module.lexer.clone())
            i += 1
            body = []
            depth = 1
            while i < len(lines):
                inner = lines[i].strip()
                if inner.split()[0] == 'cond' if inner else False:
                    depth += 1
                elif inner == 'end':
                    depth -= 1
                    if depth == 0:
                        break
                body.append(lines[i])
                i += 1
            i += 1  # skip 'end'
            if condition:
                execute_lines(body)
        else:
            execute_line(line)
            i += 1

def run_file(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    execute_lines(lines)

def run_repl():
    print("BrittainScript — type 'exit' to quit")
    while True:
        try:
            text = input('bs> ')
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.strip() in ('exit', 'quit'):
            break
        if not text.strip():
            continue

        first_word = text.strip().split()[0]
        if first_word == 'cond':
            condition = parser_module.parser.parse(text.strip(), lexer=lexer_module.lexer.clone())
            body = []
            while True:
                try:
                    line = input('...> ')
                except (EOFError, KeyboardInterrupt):
                    break
                if line.strip() == 'end':
                    break
                body.append(line)
            if condition:
                execute_lines(body)
        else:
            execute_line(text)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        run_repl()
