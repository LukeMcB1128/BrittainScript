import sys
import lexer as lexer_module
import parser as parser_module

def run_file(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        result = parser_module.parser.parse(line, lexer=lexer_module.lexer.clone())
        if result is not None:
            print(result)

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
        result = parser_module.parser.parse(text, lexer=lexer_module.lexer.clone())
        if result is not None:
            print(result)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        run_repl()
