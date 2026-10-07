import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import re
import operator
import math
from contextvars import ContextVar
try:
    import core.diagnostics as diagnostics
    import core.runtime as runtime
except ModuleNotFoundError:
    import diagnostics
    import runtime
report = diagnostics.report
import lexer as lexer_module
import parser as parser_module

functions = {}
function_environments = [None]
_echo = ContextVar('brittainscript_echo', default=False)


def current_functions():
    active = runtime.state.get()
    return active.functions if active is not None else functions


def current_environments():
    active = runtime.state.get()
    return active.environments if active is not None else function_environments

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
        if char in '([{':
            depth += 1
            continue
        if char in ')]}':
            depth -= 1
            continue
        if char == '=' and depth == 0:
            previous_char = line[index - 1] if index > 0 else ''
            next_char = line[index + 1] if index + 1 < len(line) else ''
            if previous_char in ('=', '!', '<', '>') or next_char == '=':
                continue
            if previous_char in AUGMENTED_OPERATORS:
                continue
            return line[:index].strip(), line[index + 1:].strip()
    return None

# 'x += 1' and friends -- the operator sits immediately before the '='
AUGMENTED_OPERATORS = ('+', '-', '*', '/', '%', '^')
INPLACE_OPERATORS = {
    '+': operator.iadd, '-': operator.isub, '*': operator.imul,
    '/': operator.itruediv, '//': operator.ifloordiv, '%': operator.imod,
    '^': math.pow,
}

def split_augmented_assignment(line):
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
        if char in '([{':
            depth += 1
            continue
        if char in ')]}':
            depth -= 1
            continue
        if char == '=' and depth == 0:
            previous_char = line[index - 1] if index > 0 else ''
            next_char = line[index + 1] if index + 1 < len(line) else ''
            if next_char == '=' or previous_char not in AUGMENTED_OPERATORS:
                return None
            operator_start = index - 1
            if previous_char == '/' and line[index - 2:index] == '//':
                operator_start -= 1
            target = line[:operator_start].strip()
            if not target:
                return None
            return target, line[operator_start:index], line[index + 1:].strip()
    return None

def parse_expression(text):
    with diagnostics.expression_location(text):
        try:
            return parser_module.parser.parse(text, lexer=lexer_module.lexer.clone())
        except (BreakSignal, ContinueSignal, ReturnSignal, diagnostics.BSError):
            raise
        except Exception as error:
            raise diagnostics.from_python(error) from error

def execute_line(line):
    augmented = split_augmented_assignment(line)
    if augmented:
        target, operation, expression = augmented
        try:
            container, key = parser_module.resolve_target(target)
            current = (parser_module.get_name(key) if container is parser_module.NAME_TARGET
                       else container[key])
            value = INPLACE_OPERATORS[operation](current, parse_expression(expression))
            parser_module.store_target(container, key, value)
        except (KeyError, TypeError, IndexError, ValueError, ZeroDivisionError) as error:
            report(f'Error: augmented assignment failed: {error}', cause=error)
        return
    assignment = split_assignment(line)
    if assignment:
        target, expression = assignment
        parser_module.assign_target(target, parse_expression(expression))
        return
    result = parse_expression(line)
    if result is not None and _echo.get():
        print(parser_module.display(result))

def block_keyword(line):
    for keyword in ('cond', 'while', 'for', 'func', 'try'):
        if line in (keyword, keyword + ':') or line.startswith(keyword + ' ') or line.startswith(keyword + '('):
            return keyword
    return None

def is_block_start(line):
    return block_keyword(line) is not None

def branch_keyword(line):
    for keyword in ('elif', 'else', 'catch', 'finally'):
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
            header = lines[i].with_text(line) if isinstance(lines[i], diagnostics.SourceLine) else line
            branches.append((header, []))
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
    report("Syntax error: missing end")
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
        source = header if header is not None else line
        with diagnostics.source_location(source):
            if header is None:
                condition_text = parse_colon_expression(line, 'cond')
            elif branch_keyword(header) == 'else':
                execute_lines(body)
                return
            else:
                condition_text = parse_colon_expression(header, 'elif')
            if not condition_text:
                report("Syntax error: expected a condition")
            if parse_expression(condition_text):
                execute_lines(body)
                return

def validate_branches(branches):
    seen_else = False
    for header, body in branches:
        if header is None:
            continue
        with diagnostics.source_location(header):
            keyword = branch_keyword(header)
            if keyword not in ('elif', 'else'):
                report(f"Syntax error: unexpected {keyword}")
            if seen_else:
                report(f"Syntax error: {keyword} after else")
                return False
            if keyword == 'else':
                if parse_colon_expression(header, 'else'):
                    report("Syntax error: else does not take a condition")
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
        report("Syntax error: expected for name in expression:")
        return
    name, iterable_text = match.groups()
    iterable = parse_expression(iterable_text)
    if iterable is None:
        return
    try:
        iterator = iter(iterable)
    except TypeError as error:
        report("Error: for loop target is not iterable", cause=error)
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
        report("Syntax error: expected func name(arg1, arg2):")
        return
    name, raw_params = match.groups()
    params = [param.strip() for param in raw_params.split(',') if param.strip()]
    invalid = [param for param in params if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', param)]
    if invalid:
        report("Syntax error: invalid function parameter")
        return
    environment = current_environments()[-1]
    registry = current_functions() if environment is None else environment
    registry[name] = (params, body)

def call_variable(name, args):
    # a name can hold something callable -- a Python function pulled in through
    # pyimport, for instance. Functions defined with 'func' still win.
    try:
        value = parser_module.get_name(name)
    except KeyError:
        report(f"Undefined function: {name}")
        return None
    if not callable(value):
        report(f"Error: '{name}' is not callable")
        return None
    try:
        return value(*args)
    except diagnostics.BSError:
        raise
    except Exception as error:
        report(f"Error calling '{name}': {error}", cause=error)
        return None

def call_user_function(name, args):
    environment = current_environments()[-1]
    if environment is not None and name in environment:
        return call_definition(name, environment[name], args, environment)
    registry = current_functions()
    if name not in registry:
        return call_variable(name, args)
    return call_definition(name, registry[name], args)


def call_definition(name, definition, args, environment=None):
    params, body = definition
    if len(args) != len(params):
        report(f"Error: {name}() expects {len(params)} arguments")
        return None

    parser_module.push_scope(dict(zip(params, args)))
    current_environments().append(environment)
    try:
        with diagnostics.call_frame(name):
            execute_lines(body)
    except ReturnSignal as signal:
        return signal.value
    except (BreakSignal, ContinueSignal) as signal:
        raise signal.error
    finally:
        current_environments().pop()
        parser_module.pop_scope()
    return None

def call_module_function(module, func_name, args):
    funcs = module['funcs']
    if func_name not in funcs:
        report(f"Error: '{module['name']}' has no function '{func_name}'", kind='AttributeError')
        return None
    if callable(funcs[func_name]):
        with diagnostics.call_frame(module['name'] + '.' + func_name):
            try:
                return funcs[func_name](*args)
            except diagnostics.BSError:
                raise
            except Exception as error:
                raise diagnostics.from_python(error) from error
    return call_definition(func_name, funcs[func_name], args, funcs)


def call_callback_function(name, args):
    # GUI events call user functions even while a library runs its event loop.
    current_environments().append(None)
    try:
        return parser_module.call_function(name, args)
    finally:
        current_environments().pop()

def import_module(lib_name):
    if lib_name == 'server':
        import server_backend
        return server_backend.create_module(sys.modules[__name__])
    libs_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'libs'))
    lib_path = os.path.join(libs_dir, lib_name + '.bs')
    if not os.path.exists(lib_path):
        report(f"Error: library '{lib_name}' not found", kind='ImportError')
        return None
    with open(lib_path, 'r') as f:
        lines = [diagnostics.SourceLine(text, lib_path, index)
                 for index, text in enumerate(f, 1)]
    module_funcs = {}
    current_environments().append(module_funcs)
    try:
        try:
            execute_lines(lines)
        except (BreakSignal, ContinueSignal, ReturnSignal):
            pass
    finally:
        current_environments().pop()
    return parser_module.BSModule({'__bs_module__': True, 'name': lib_name, 'funcs': module_funcs})

parser_module.set_function_caller(call_user_function)
parser_module.set_module_caller(call_module_function)
parser_module.gui_backend.set_callback_invoker(call_callback_function)

def catch_spec(header):
    match = re.fullmatch(r'catch(?:\s+([A-Za-z_][A-Za-z0-9_]*))?(?:\s+as\s+([A-Za-z_][A-Za-z0-9_]*))?\s*:?', header)
    if not match:
        report('Syntax error: expected catch Type as name, catch as name, or catch')
    kind, name = match.groups()
    statement_names = ('try', 'catch', 'finally', 'raise', 'end', 'local', 'discard',
                       'func', 'for', 'while', 'in', 'elif', 'else', 'return',
                       'break', 'continue', 'add')
    if name in lexer_module.reserved or name in statement_names:
        report('Syntax error: invalid catch variable')
    return kind or 'Error', name


def execute_try(line, branches):
    if line not in ('try', 'try:'):
        report('Syntax error: try does not take an expression')
    handlers = []
    final_body = None
    else_body = None
    catch_all = False
    for header, body in branches[1:]:
        with diagnostics.source_location(header):
            keyword = branch_keyword(header)
            if final_body is not None:
                report('Syntax error: finally must be last')
            if keyword == 'catch':
                if else_body is not None:
                    report('Syntax error: catch after else')
                if catch_all:
                    report('Syntax error: catch-all handler must be last')
                kind, name = catch_spec(header)
                catch_all = kind in ('Error', 'Exception')
                handlers.append((kind, name, body))
            elif keyword == 'finally':
                if parse_colon_expression(header, 'finally'):
                    report('Syntax error: finally does not take an expression')
                final_body = body
            elif keyword == 'else':
                if not handlers or else_body is not None or parse_colon_expression(header, 'else'):
                    report('Syntax error: expected one else after catch')
                else_body = body
            else:
                report(f'Syntax error: unexpected {keyword} in try')
    if not handlers and final_body is None:
        report('Syntax error: try requires catch or finally')

    try:
        try:
            execute_lines(branches[0][1])
        except diagnostics.BSError as error:
            for kind, name, body in handlers:
                if error.matches(kind):
                    if name:
                        parser_module.set_name(name, error)
                    try:
                        with diagnostics.handling(error):
                            execute_lines(body)
                    finally:
                        if name:
                            parser_module.unset_name(name)
                    break
            else:
                raise
        else:
            if else_body is not None:
                execute_lines(else_body)
    finally:
        if final_body is not None:
            # A pending error is also available to bare raise in finally.
            pending = sys.exc_info()[1]
            active = pending if isinstance(pending, diagnostics.BSError) else diagnostics.current_error()
            with diagnostics.handling(active):
                execute_lines(final_body)


def execute_lines(lines, echo=False):
    lines = [line if isinstance(line, diagnostics.SourceLine)
             else diagnostics.SourceLine(line, line=index)
             for index, line in enumerate(lines, 1)]
    token = _echo.set(echo)
    try:
        with diagnostics.execution():
            return _execute_lines(lines)
    finally:
        _echo.reset(token)


def _execute_lines(lines):
    i = 0
    while i < len(lines):
        line = strip_inline_comment(lines[i])
        if not line:
            i += 1
            continue
        with diagnostics.source_location(lines[i].with_text(line)):
            try:
                i = execute_statement(lines, i, lines[i].with_text(line))
            except (BreakSignal, ContinueSignal, ReturnSignal) as signal:
                if not hasattr(signal, 'error'):
                    keyword = {BreakSignal: 'break', ContinueSignal: 'continue', ReturnSignal: 'return'}[type(signal)]
                    signal.error = diagnostics.BSError(f'{keyword} used outside a loop or function')
                    signal.error.raised = True
                raise
            except diagnostics.BSError:
                raise
            except Exception as error:
                raise diagnostics.from_python(error) from error


def execute_statement(lines, i, line):
    first_word = block_keyword(line) or branch_keyword(line) or line.split()[0]
    if first_word == 'cond':
        branches, i = collect_block(lines, i + 1, indentation(lines[i]), collect_branches=True)
        execute_cond(line, branches)
    elif first_word in ('elif', 'else', 'catch', 'finally'):
        report(f"Syntax error: unexpected {first_word}")
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
    elif first_word == 'try':
        branches, i = collect_block(lines, i + 1, indentation(lines[i]), collect_branches=True)
        execute_try(line, branches)
    elif first_word == 'raise':
        expression = line[len('raise'):].strip()
        if expression:
            value = parse_expression(expression)
            if isinstance(value, type) and issubclass(value, Exception):
                value = value()
            if isinstance(value, str):
                value = diagnostics.BSError(value)
            elif isinstance(value, Exception) and not isinstance(value, diagnostics.BSError):
                value = diagnostics.from_python(value)
            if not isinstance(value, diagnostics.BSError):
                report('Error: raise expects an error value or a string', kind='TypeError')
            raise value.mark_raised()
        error = diagnostics.current_error()
        if error is None:
            report('Error: raise used without an active error')
        raise error
    elif first_word == 'break':
        raise BreakSignal()
    elif first_word == 'continue':
        raise ContinueSignal()
    elif first_word == 'return':
        return_text = line[len('return'):].strip()
        raise ReturnSignal(parse_expression(return_text) if return_text else None)
    elif first_word == 'local':
        local_names = [name.strip() for name in line[len('local'):].split(',') if name.strip()]
        if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) for name in local_names):
            report('Syntax error: invalid local name')
        else:
            parser_module.declare_locals(local_names)
        i += 1
    elif first_word == 'discard':
        parse_expression(line[len('discard'):].strip())
        i += 1
    elif first_word == 'add':
        parts = line.split(None, 1)
        if len(parts) < 2:
            report("Syntax error: expected import name")
        else:
            lib_name = parts[1].strip()
            module = import_module(lib_name)
            if module:
                parser_module.set_name(lib_name, module)
        i += 1
    elif first_word == 'end':
        report("Syntax error: unexpected end")
        i += 1
    else:
        execute_line(line)
        i += 1
    return i


def run_file(file_path):
    source = diagnostics.SourceLine('', os.path.abspath(file_path), 1)
    try:
        with diagnostics.source_location(source), diagnostics.execution():
            with open(file_path, 'r') as f:
                lines = [diagnostics.SourceLine(text, source.file, index)
                         for index, text in enumerate(f, 1)]
            execute_lines(lines)
    except diagnostics.BSError as error:
        diagnostics.emit(error)
        return 1
    except (BreakSignal, ContinueSignal, ReturnSignal) as signal:
        diagnostics.emit(signal.error)
        return 1
    except Exception as error:
        with diagnostics.source_location(source):
            diagnostics.emit(diagnostics.from_python(error))
        return 1
    return 0

def read_block_lines(first_line, read_line):
    # Typed-in blocks arrive with no indentation, but the block collector reads
    # structure from indentation, so re-indent by nesting depth as we go. That
    # also lets an inner 'end' close only its own block instead of everything.
    lines = [first_line.strip()]
    depth = 1
    while depth > 0:
        try:
            line = read_line()
        except (EOFError, KeyboardInterrupt):
            break
        content = strip_inline_comment(line).strip()
        if content == 'end':
            depth -= 1
            lines.append('    ' * depth + 'end')
            continue
        if branch_keyword(content):
            # elif/else line up with the block they belong to
            lines.append('    ' * (depth - 1) + line.strip())
            continue
        lines.append('    ' * depth + line.strip())
        if is_block_start(content):
            depth += 1
    while depth > 0:
        depth -= 1
        lines.append('    ' * depth + 'end')
    return lines

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

        first_word = block_keyword(stripped_text) or stripped_text.split()[0]
        try:
            if first_word in ('cond', 'while', 'for', 'func', 'try'):
                lines = read_block_lines(text, lambda: input('...> '))
            else:
                lines = [text]
            execute_lines([diagnostics.SourceLine(line, '<repl>', index)
                           for index, line in enumerate(lines, 1)], echo=len(lines) == 1)
        except diagnostics.BSError as error:
            diagnostics.emit(error)
        except (BreakSignal, ContinueSignal, ReturnSignal) as signal:
            diagnostics.emit(signal.error)

def cli_entry():
    if len(sys.argv) > 1:
        sys.exit(run_file(sys.argv[1]))
    else:
        run_repl()

if __name__ == '__main__':
    cli_entry()
