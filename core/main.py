import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import re
import lexer as lexer_module
import parser as parser_module

functions = {}

class BreakSignal(Exception):
    pass

class ContinueSignal(Exception):
    pass

class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value

def strip_inline_comment(line):
    in_string = False
    escaped = False
    result = []
    for char in line:
        if escaped:
            result.append(char)
            escaped = False
            continue
        if char == '\\' and in_string:
            result.append(char)
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            result.append(char)
            continue
        if char == '#' and not in_string:
            break
        result.append(char)
    return ''.join(result).strip()

def indentation(line):
    return len(line) - len(line.lstrip(' \t'))

def split_assignment(line):
    in_string = False
    escaped = False
    depth = 0
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == '\\' and in_string:
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char in '([':
            depth += 1
            continue
        if char in ')]':
            depth -= 1
            continue
        if char == '=' and depth == 0:
            previous_char = line[index - 1] if index > 0 else ''
            next_char = line[index + 1] if index + 1 < len(line) else ''
            if previous_char in ('=', '!', '<', '>') or next_char == '=':
                continue
            return line[:index].strip(), line[index + 1:].strip()
    return None

def parse_expression(text):
    return parser_module.parser.parse(text, lexer=lexer_module.lexer.clone())

def execute_line(line):
    assignment = split_assignment(line)
    if assignment:
        target, expression = assignment
        parser_module.assign_target(target, parse_expression(expression))
        return
    result = parse_expression(line)
    if result is not None:
        print(result)

def block_keyword(line):
    for keyword in ('cond', 'while', 'for', 'func'):
        if line == keyword or line.startswith(keyword + ' ') or line.startswith(keyword + '('):
            return keyword
    return None

def is_block_start(line):
    return block_keyword(line) is not None

def branch_keyword(line):
    for keyword in ('elif', 'else'):
        if line == keyword or line == keyword + ':':
            return keyword
        if line.startswith(keyword + ' ') or line.startswith(keyword + '('):
            return keyword
    return None

def collect_block(lines, start_index, parent_indent=0, collect_branches=False):
    # branches is [(header, body)]; the first header is None because the opening
    # 'cond' line is the header for it. Blocks close on 'end' or on a dedent, so
    # both styles have to keep working.
    branches = [(None, [])]
    i = start_index
    block_indents = [parent_indent]
    while i < len(lines):
        line = strip_inline_comment(lines[i])
        if not line:
            branches[-1][1].append(lines[i])
            i += 1
            continue

        current_indent = indentation(lines[i])
        # an 'elif'/'else' sitting at the indent of an inner block belongs to
        # that block, so it must not pop it the way an ordinary dedent would
        continues_branch = branch_keyword(line) is not None
        while len(block_indents) > 1 and line != 'end':
            if continues_branch:
                if current_indent >= block_indents[-1]:
                    break
            elif current_indent > block_indents[-1]:
                break
            block_indents.pop()

        is_branch = collect_branches and continues_branch and len(block_indents) == 1
        if len(block_indents) == 1 and current_indent <= parent_indent and line != 'end' and not is_branch:
            return finish_block(branches, collect_branches), i

        if is_branch:
            branches.append((line, []))
            i += 1
            continue

        if is_block_start(line):
            block_indents.append(current_indent)
        elif line == 'end':
            if len(block_indents) == 1:
                return finish_block(branches, collect_branches), i + 1
            block_indents.pop()
        branches[-1][1].append(lines[i])
        i += 1
    print("Syntax error: missing end")
    return finish_block(branches, collect_branches), i

def finish_block(branches, collect_branches):
    if collect_branches:
        return branches
    return branches[0][1]

def parse_colon_expression(line, keyword):
    expression = line[len(keyword):].strip()
    if expression.endswith(':'):
        expression = expression[:-1].strip()
    if expression.startswith('(') and expression.endswith(')'):
        expression = expression[1:-1].strip()
    return expression

def execute_cond(line, branches):
    if not validate_branches(branches):
        return
    for header, body in branches:
        if header is None:
            condition_text = parse_colon_expression(line, 'cond')
        elif branch_keyword(header) == 'else':
            execute_lines(body)
            return
        else:
            condition_text = parse_colon_expression(header, 'elif')
        if not condition_text:
            print("Syntax error: expected a condition")
            return
        if parse_expression(condition_text):
            execute_lines(body)
            return

def validate_branches(branches):
    seen_else = False
    for header, body in branches:
        if header is None:
            continue
        keyword = branch_keyword(header)
        if seen_else:
            print(f"Syntax error: {keyword} after else")
            return False
        if keyword == 'else':
            if parse_colon_expression(header, 'else'):
                print("Syntax error: else does not take a condition")
                return False
            seen_else = True
    return True

def execute_while(line, body):
    condition_text = parse_colon_expression(line, 'while')
    while parse_expression(condition_text):
        try:
            execute_lines(body)
        except ContinueSignal:
            continue
        except BreakSignal:
            break

def execute_for(line, body):
    match = re.fullmatch(r'for\s+([A-Za-z_][A-Za-z0-9_]*)\s+in\s+(.+?):?', line)
    if not match:
        print("Syntax error: expected for name in expression:")
        return
    name, iterable_text = match.groups()
    iterable = parse_expression(iterable_text)
    if iterable is None:
        return
    try:
        iterator = iter(iterable)
    except TypeError:
        print("Error: for loop target is not iterable")
        return

    for value in iterator:
        parser_module.set_name(name, value)
        try:
            execute_lines(body)
        except ContinueSignal:
            continue
        except BreakSignal:
            break

def execute_func_definition(line, body):
    match = re.fullmatch(r'func\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*:?', line)
    if not match:
        print("Syntax error: expected func name(arg1, arg2):")
        return
    name, raw_params = match.groups()
    params = [param.strip() for param in raw_params.split(',') if param.strip()]
    invalid = [param for param in params if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', param)]
    if invalid:
        print("Syntax error: invalid function parameter")
        return
    functions[name] = (params, body)

def call_user_function(name, args):
    if name not in functions:
        print(f"Undefined function: {name}")
        return None
    params, body = functions[name]
    if len(args) != len(params):
        print(f"Error: {name}() expects {len(params)} arguments")
        return None

    parser_module.push_scope(dict(zip(params, args)))
    try:
        execute_lines(body)
    except ReturnSignal as signal:
        return signal.value
    except BreakSignal:
        print("Error: break used outside a loop")
        return None
    except ContinueSignal:
        print("Error: continue used outside a loop")
        return None
    finally:
        parser_module.pop_scope()
    return None

def call_module_function(module, func_name, args):
    funcs = module['funcs']
    if func_name not in funcs:
        print(f"Error: '{module['name']}' has no function '{func_name}'")
        return None
    params, body = funcs[func_name]
    if len(args) != len(params):
        print(f"Error: {func_name}() expects {len(params)} arguments")
        return None
    # Register module functions globally so they can call each other recursively
    for name, defn in funcs.items():
        functions[name] = defn
    parser_module.push_scope(dict(zip(params, args)))
    try:
        execute_lines(body)
    except ReturnSignal as s:
        return s.value
    except BreakSignal:
        print("Error: break used outside a loop")
        return None
    except ContinueSignal:
        print("Error: continue used outside a loop")
        return None
    finally:
        parser_module.pop_scope()
        for name in funcs:
            functions.pop(name, None)
    return None

def import_module(lib_name):
    libs_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'libs'))
    lib_path = os.path.join(libs_dir, lib_name + '.bs')
    if not os.path.exists(lib_path):
        print(f"Error: library '{lib_name}' not found")
        return None
    before = set(functions.keys())
    with open(lib_path, 'r') as f:
        lines = f.readlines()
    try:
        execute_lines(lines)
    except (BreakSignal, ContinueSignal, ReturnSignal):
        pass
    new_names = set(functions.keys()) - before
    module_funcs = {name: functions.pop(name) for name in new_names}
    return {'__bs_module__': True, 'name': lib_name, 'funcs': module_funcs}

parser_module.set_function_caller(call_user_function)
parser_module.set_module_caller(call_module_function)

def execute_lines(lines):
    i = 0
    while i < len(lines):
        line = strip_inline_comment(lines[i])
        if not line:
            i += 1
            continue

        first_word = block_keyword(line) or branch_keyword(line) or line.split()[0]
        if first_word == 'cond':
            branches, i = collect_block(lines, i + 1, indentation(lines[i]), collect_branches=True)
            execute_cond(line, branches)
        elif first_word in ('elif', 'else'):
            print(f"Syntax error: unexpected {first_word}")
            i += 1
        elif first_word == 'while':
            body, i = collect_block(lines, i + 1, indentation(lines[i]))
            execute_while(line, body)
        elif first_word == 'for':
            body, i = collect_block(lines, i + 1, indentation(lines[i]))
            execute_for(line, body)
        elif first_word == 'func':
            body, i = collect_block(lines, i + 1, indentation(lines[i]))
            execute_func_definition(line, body)
        elif first_word == 'break':
            raise BreakSignal()
        elif first_word == 'continue':
            raise ContinueSignal()
        elif first_word == 'return':
            return_text = line[len('return'):].strip()
            raise ReturnSignal(parse_expression(return_text) if return_text else None)
        elif first_word == 'add':
            parts = line.split(None, 1)
            if len(parts) < 2:
                print("Syntax error: expected import name")
            else:
                lib_name = parts[1].strip()
                module = import_module(lib_name)
                if module:
                    parser_module.set_name(lib_name, module)
            i += 1
        elif first_word == 'end':
            print("Syntax error: unexpected end")
            i += 1
        else:
            execute_line(line)
            i += 1

def run_file(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    try:
        execute_lines(lines)
    except BreakSignal:
        print("Error: break used outside a loop")
    except ContinueSignal:
        print("Error: continue used outside a loop")
    except ReturnSignal:
        print("Error: return used outside a function")

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
        stripped_text = strip_inline_comment(text)
        if not stripped_text:
            continue

        first_word = stripped_text.split()[0]
        if first_word in ('cond', 'while', 'for', 'func'):
            body = []
            while True:
                try:
                    line = input('...> ')
                except (EOFError, KeyboardInterrupt):
                    break
                if line.strip() == 'end':
                    break
                body.append(line)
            try:
                execute_lines([text] + body + ['end'])
            except BreakSignal:
                print("Error: break used outside a loop")
            except ContinueSignal:
                print("Error: continue used outside a loop")
            except ReturnSignal:
                print("Error: return used outside a function")
        else:
            try:
                execute_lines([stripped_text])
            except BreakSignal:
                print("Error: break used outside a loop")
            except ContinueSignal:
                print("Error: continue used outside a loop")
            except ReturnSignal:
                print("Error: return used outside a function")

def cli_entry():
    if len(sys.argv) > 1:
        run_file(sys.argv[1])
    else:
        run_repl()

if __name__ == '__main__':
    cli_entry()
