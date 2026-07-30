import sys
from core import main

if __name__ == '__main__':
    if len(sys.argv) > 1:
        main.run_file(sys.argv[1])
    else:
        main.run_repl()