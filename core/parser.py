import ply.yacc as yacc
import lexer as lexer_module
from lexer import tokens
import math
import os
import re
import gui_backend
import calendar
import datetime
try:
    from core.diagnostics import report, BSError, expression_offset
except ModuleNotFoundError:
    from diagnostics import report, BSError, expression_offset

# variable storage
names = {}
scopes = [names]
function_caller = None
module_caller = None
UNBOUND = object()
NAME_TARGET = object()


class FunctionScope(dict):
    lexical = False

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'EQUALTO', 'NOTEQUALTO'),
    ('left', 'LESSTHAN', 'GREATERTHAN', 'LESSTHANEQUALTO', 'GREATERTHANEQUALTO'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'MULTIPLY', 'DIVIDE', 'FLOORDIVIDE', 'MODULO', 'AT'),
    ('right', 'POWER'),
    ('left', 'LBRACKET'),
    ('left', 'DOT'),
)

def push_scope(scope=None):
    scopes.append(FunctionScope({} if scope is None else scope))

def pop_scope():
    if len(scopes) > 1:
        scopes.pop()

def get_name(name):
    for scope in visible_scopes():
        if name in scope:
            if scope[name] is UNBOUND:
                raise UnboundLocalError(f"local variable '{name}' has no value")
            return scope[name]
    raise KeyError(name)

def set_name(name, value):
    for scope in visible_scopes():
        if name in scope:
            scope[name] = value
            return
    scopes[-1][name] = value


def unset_name(name):
    for scope in visible_scopes():
        if name in scope:
            if getattr(scope, 'lexical', False):
                scope[name] = UNBOUND
            else:
                del scope[name]
            return


def visible_scopes():
    if getattr(scopes[-1], 'lexical', False):
        return (scopes[-1], scopes[0])
    return reversed(scopes)


def declare_locals(local_names):
    if len(scopes) == 1:
        report('Error: local used outside a function')
        return
    scopes[-1].lexical = True
    for name in local_names:
        scopes[-1].setdefault(name, UNBOUND)

def assign_target(target, value):
    try:
        container, key = resolve_target(target)
        store_target(container, key, value)
    except (KeyError, TypeError, IndexError, ValueError) as error:
        report(f'Error: invalid assignment target: {error}', cause=error)

def resolve_target(target):
    """Evaluate a target once, including nested indexes and slice bounds."""
    import re
    target = target.strip()
    if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', target):
        return NAME_TARGET, target
    scanner = lexer_module.lexer.clone()
    scanner.input(target)
    depth = 0
    opening = None
    for token in scanner:
        if token.type == 'LBRACKET':
            if depth == 0:
                opening = token.lexpos
            depth += 1
        elif token.type == 'RBRACKET':
            depth -= 1
            if depth == 0 and token.lexpos == len(target) - 1:
                container = parser.parse(target[:opening], lexer=lexer_module.lexer.clone())
                return container, parse_target_index(target[opening + 1:-1])
    raise ValueError('expected a name or an indexed value')


def parse_target_index(text):
    scanner = lexer_module.lexer.clone()
    scanner.input(text)
    depth = 0
    cuts = []
    for token in scanner:
        if token.type in ('LPAREN', 'LBRACKET'):
            depth += 1
        elif token.type in ('RPAREN', 'RBRACKET'):
            depth -= 1
        elif token.type == 'COLON' and depth == 0:
            cuts.append(token.lexpos)
    if not cuts:
        return parser.parse(text, lexer=lexer_module.lexer.clone())
    if len(cuts) > 2:
        raise ValueError('too many slice bounds')
    bounds = [-1] + cuts + [len(text)]
    values = []
    for left, right in zip(bounds, bounds[1:]):
        part = text[left + 1:right].strip()
        values.append(parser.parse(part, lexer=lexer_module.lexer.clone()) if part else None)
    return slice(*values)


def store_target(container, key, value):
    if container is NAME_TARGET:
        set_name(key, value)
    else:
        container[key] = value

def set_function_caller(caller):
    global function_caller
    function_caller = caller

def set_module_caller(caller):
    global module_caller
    module_caller = caller

def p_expression_number(p):
    'expression : NUMBER'
    p[0] = p[1]

def p_expression_group(p):
    'expression : LPAREN expression RPAREN'
    p[0] = p[2]

def p_expression_plus(p):
    'expression : expression PLUS expression'
    try:
        p[0] = p[1] + p[3]
    except TypeError as error:
        report(f"Error: cannot add {type(p[1]).__name__} and {type(p[3]).__name__}", cause=error, offset=p.lexpos(2))
        p[0] = None

def p_expression_minus(p):
    'expression : expression MINUS expression'
    p[0] = p[1] - p[3]

def p_expression_divide(p):
    'expression : expression DIVIDE expression'
    if p[3] == 0:
        report("Error: division by zero", offset=p.lexpos(2))
        p[0] = None
        return
    p[0] = p[1] / p[3]


def p_expression_floordivide(p):
    'expression : expression FLOORDIVIDE expression'
    if p[3] == 0:
        report('Error: division by zero', offset=p.lexpos(2))
        p[0] = None
        return
    p[0] = p[1] // p[3]

def p_expression_times(p):
    'expression : expression MULTIPLY expression'
    try:
        p[0] = p[1] * p[3]
    except TypeError as error:
        report(f"Error: cannot multiply {type(p[1]).__name__} and {type(p[3]).__name__}", cause=error, offset=p.lexpos(2))
        p[0] = None

def p_expression_matmul(p):
    'expression : expression AT expression'
    try:
        p[0] = p[1] @ p[3]
    except TypeError as exc:
        report(f"Error: cannot matrix-multiply: {exc}", cause=exc, offset=p.lexpos(2))
        p[0] = None

def p_expression_modulo(p):
    'expression : expression MODULO expression'
    if p[3] == 0:
        report("Error: modulo by zero", offset=p.lexpos(2))
        p[0] = None
        return
    p[0] = p[1] % p[3]

def p_expression_power(p):
    'expression : expression POWER expression'
    p[0] = math.pow(p[1], p[3])

def p_expression_squareroot(p):
    'expression : SQUAREROOT LPAREN expression RPAREN'
    p[0] = math.sqrt(p[3])

def p_expression_sine(p):
    'expression : SINE LPAREN expression RPAREN'
    p[0] = math.sin(math.radians(p[3]))

def p_expression_cosine(p):
    'expression : COSINE LPAREN expression RPAREN'
    p[0] = math.cos(math.radians(p[3]))

def p_expression_tangent(p):
    'expression : TANGENT LPAREN expression RPAREN'
    p[0] = math.tan(math.radians(p[3]))

def p_expression_pi(p):
    'expression : PI'
    p[0] = math.pi

def display(value):
    # 'null' is Python's None underneath -- show it with the BrittainScript name
    if value is None:
        return 'null'
    return value

def p_expression_print(p):
    'expression : PRINT LPAREN expression RPAREN'
    print(display(p[3]))
    p[0] = None

def p_expression_string(p):
    'expression : STRING'
    p[0] = p[1]

def p_statement_assign(p):
    'expression : NAME EQ expression'
    set_name(p[1], p[3])
    p[0] = None

def p_expression_name(p):
    'expression : NAME'
    try:
        p[0] = get_name(p[1])
    except KeyError:
        report(f'Undefined variable: {p[1]}', offset=p.lexpos(1))
        p[0] = 0

def p_expression_list(p):
    'expression : LBRACKET optional_arguments RBRACKET'
    p[0] = p[2]

def p_expression_index(p):
    'expression : expression LBRACKET expression RBRACKET'
    try:
        p[0] = p[1][p[3]]
    except (TypeError, IndexError, KeyError) as error:
        report("Error: invalid index", cause=error, offset=p.lexpos(2))
        p[0] = None

def p_expression_slice(p):
    'expression : expression LBRACKET optional_expression COLON optional_expression RBRACKET'
    try:
        p[0] = p[1][p[3]:p[5]]
    except (TypeError, ValueError) as error:
        report("Error: invalid slice", cause=error, offset=p.lexpos(2))
        p[0] = None

def p_optional_expression_empty(p):
    'optional_expression :'
    p[0] = None

def p_optional_expression_value(p):
    'optional_expression : expression'
    p[0] = p[1]

def p_optional_arguments_empty(p):
    'optional_arguments :'
    p[0] = []

def p_optional_arguments_value(p):
    'optional_arguments : arguments'
    p[0] = p[1]

def p_arguments_single(p):
    'arguments : expression'
    p[0] = [p[1]]

def p_arguments_many(p):
    'arguments : arguments COMMA expression'
    p[0] = p[1] + [p[3]]

def p_expression_function_call(p):
    'expression : NAME LPAREN optional_arguments RPAREN'
    with expression_offset(p.lexpos(1)):
        p[0] = call_function(p[1], p[3])

def p_expression_range_call(p):
    'expression : RANGE LPAREN optional_arguments RPAREN'
    p[0] = call_function('range', p[3])

def p_expression_method_call(p):
    'expression : expression DOT NAME LPAREN optional_arguments RPAREN'
    with expression_offset(p.lexpos(3)):
        p[0] = call_method(p[1], p[3], p[5])

def p_expression_attribute(p):
    'expression : expression DOT NAME'
    receiver, attr = p[1], p[3]
    if isinstance(receiver, dict) and receiver.get('__bs_module__'):
        report(f"Error: '{receiver['name']}' members must be called")
        p[0] = None
        return
    try:
        p[0] = getattr(receiver, attr)
    except AttributeError:
        report(f"Error: no attribute '{attr}' on {type(receiver).__name__}")
        p[0] = None

def call_function(name, args):
    try:
        return _call_function(name, args)
    except BSError:
        raise
    except Exception as error:
        report(f"Error calling '{name}': {error}", cause=error)


def _call_function(name, args):
    if name == 'error':
        if len(args) not in (1, 2) or not all(isinstance(arg, str) for arg in args):
            report('Error: error() expects a message and an optional type string', kind='TypeError')
            return None
        if len(args) == 2 and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', args[1]):
            report('Error: error type must be a name', kind='ValueError')
            return None
        return BSError(args[0], args[1] if len(args) == 2 else 'RuntimeError')
    if name == 'pyimport':
        if len(args) != 1 or not isinstance(args[0], str):
            report("Error: pyimport() expects one string argument")
            return None
        import importlib
        try:
            return importlib.import_module(args[0])
        except ImportError as exc:
            report(f"Error: cannot import '{args[0]}': {exc}", cause=exc)
            return None
    if name == 'len':
        if len(args) != 1:
            report("Error: len() expects 1 argument")
            return None
        return len(args[0])
    if name == 'tonum':
        if len(args) != 1:
            report("Error: tonum() expects 1 argument")
            return None
        try:
            value = float(args[0]) if '.' in str(args[0]) else int(args[0])
            return value
        except ValueError as error:
            report("Error: tonum() could not convert value", cause=error)
            return None
    if name == 'tostr':
        if len(args) != 1:
            report("Error: tostr() expects 1 argument")
            return None
        return str(display(args[0]))
    if name == 'input':
        if len(args) > 1:
            report("Error: input() expects 0 or 1 arguments")
            return None
        return input(args[0] if args else '')
    if name == 'range':
        if len(args) not in (1, 2, 3):
            report("Error: range() expects 1 to 3 arguments")
            return []
        return list(range(*args))
    if name == 'clear':
        os.system('cls' if os.name == 'nt' else 'clear')
        return None
    if name == 'absolute':
        if len(args) != 1:
            report("Error: absolute() expects 1 argument")
            return None
        return abs(args[0])
    if name == 'round':
        if len(args) != 1:
            report("Error: round() expects 1 argument")
            return None
        return round(args[0])
    if name == 'floor':
        if len(args) != 1:
            report("Error: floor() expects 1 argument")
            return None
        return math.floor(args[0])
    if name == 'ceiling':
        if len(args) != 1:
            report("Error: ceiling() expects 1 argument")
            return None
        return math.ceil(args[0])
    if name == 'type':
        if len(args) != 1:
            report("Error: type() expects 1 argument")
            return None
        return type(args[0])
    if name == 'readfile':
        if len(args) != 1:
            report("Error: readfile() expects 1 argument")
            return None
        try:
            with open(args[0], 'r') as f:
                return f.read()
        except OSError as error:
            report(f"Error: could not read file '{args[0]}': {error}", cause=error)
            return None
    if name == 'readlines':
        if len(args) != 1:
            report("Error: readlines() expects 1 argument")
            return None
        try:
            with open(args[0], 'r') as f:
                return [line.rstrip('\n') for line in f.readlines()]
        except OSError as error:
            report(f"Error: could not read file '{args[0]}': {error}", cause=error)
            return None
    if name == 'createfile':
        if len(args) != 1:
            report("Error: createfile() expects 1 argument")
            return None
        try:
            with open(args[0], 'x'):
                pass
            return True
        except FileExistsError as error:
            report(f"Error: file '{args[0]}' already exists", cause=error)
            return False
        except OSError as error:
            report(f"Error: could not create file '{args[0]}': {error}", cause=error)
            return False
    if name == 'writefile':
        if len(args) != 2:
            report("Error: writefile() expects 2 arguments")
            return None
        try:
            with open(args[0], 'w') as f:
                f.write(str(args[1]))
            return True
        except OSError as error:
            report(f"Error: could not write file '{args[0]}': {error}", cause=error)
            return False
    if name == 'appendfile':
        if len(args) != 2:
            report("Error: appendfile() expects 2 arguments")
            return None
        try:
            with open(args[0], 'a') as f:
                f.write(str(args[1]))
            return True
        except OSError as error:
            report(f"Error: could not append to file '{args[0]}': {error}", cause=error)
            return False
    if name == 'fileexists':
        if len(args) != 1:
            report("Error: fileexists() expects 1 argument")
            return None
        return os.path.exists(args[0])
    if name == 'deletefile':
        if len(args) != 1:
            report("Error: deletefile() expects 1 argument")
            return None
        try:
            os.remove(args[0])
            return True
        except OSError as error:
            report(f"Error: could not delete file '{args[0]}': {error}", cause=error)
            return False
    if name == "datetime":
        return call_datetime(args)
    if gui_backend.is_gui_builtin(name):
        return gui_backend.call_builtin(name, args)
    if function_caller:
        return function_caller(name, args)
    report(f"Undefined function: {name}")
    return None

gui_backend.set_callback_invoker(lambda name, args: call_function(name, args))

# command -> (argument count after the command, handler)
DATETIME_COMMANDS = {
    'now':         (0, lambda a: datetime.datetime.now()),
    'format':      (2, lambda a: a[0].strftime(a[1])),
    'parse':       (2, lambda a: datetime.datetime.strptime(a[0], a[1])),
    'year':        (1, lambda a: a[0].year),
    'month':       (1, lambda a: a[0].month),
    'day':         (1, lambda a: a[0].day),
    'hour':        (1, lambda a: a[0].hour),
    'minute':      (1, lambda a: a[0].minute),
    'second':      (1, lambda a: a[0].second),
    'weekday':     (1, lambda a: a[0].weekday()),
    'isLeapYear':  (1, lambda a: calendar.isleap(a[0])),
    'daysInMonth': (2, lambda a: calendar.monthrange(a[0], a[1])[1]),
}

def call_datetime(args):
    if not args:
        report("Error: datetime() expects a command argument")
        return None
    command = args[0]
    entry = DATETIME_COMMANDS.get(command)
    if entry is None:
        report(f"Error: unknown datetime command '{command}'")
        return None
    arity, handler = entry
    rest = args[1:]
    if len(rest) != arity:
        report(f"Error: datetime {command}() expects {arity} argument{'s' if arity != 1 else ''}")
        return None
    try:
        return handler(rest)
    except (AttributeError, TypeError, ValueError) as error:
        report(f"Error: datetime {command}() failed: {error}", cause=error)
        return None

def call_method(receiver, name, args):
    try:
        return _call_method(receiver, name, args)
    except BSError:
        raise
    except Exception as error:
        report(f"Error calling '{name}': {error}", cause=error)


def _call_method(receiver, name, args):
    if isinstance(receiver, dict) and receiver.get('__bs_module__'):
        if module_caller:
            return module_caller(receiver, name, args)
        report(f"Error: no module caller set")
        return None
    if name == 'upper' and isinstance(receiver, str) and not args:
        return receiver.upper()
    if name == 'lower' and isinstance(receiver, str) and not args:
        return receiver.lower()
    if name == 'trim' and isinstance(receiver, str) and not args:
        return receiver.strip()
    if name == 'add' and isinstance(receiver, list) and len(args) == 1:
        receiver.append(args[0])
        return None
    if name == 'contains' and isinstance(receiver, str):
        if len(args) != 1:
            report('Error: contains() expects 1 argument', kind='TypeError')
            return None
        if args[0] in receiver:
            return True
        else:
            return False
    if name == 'locate' and isinstance(receiver, str) and len(args) == 1:
        return receiver.find(args[0])
    if name == 'remove' and isinstance(receiver, list) and len(args) == 1:
        try:
            receiver.remove(args[0])
        except ValueError as error:
            report("Error: list does not contain value", cause=error)
        return None
    if name == 'pop' and isinstance(receiver, list) and len(args) == 0:
        if not receiver:
            report("Error: cannot pop from an empty list")
            return None
        receiver.pop()
        return None
    if name == 'has' and isinstance(receiver, list) and len(args) == 1:
        if args[0] in receiver:
            return True
        else:
            return False
    try:
        attribute = getattr(receiver, name)
    except AttributeError:
        report(f"Error: no method '{name}' on {type(receiver).__name__}")
        return None
    if callable(attribute):
        try:
            return attribute(*args)
        except BSError:
            raise
        except Exception as exc:
            report(f"Error calling '{name}': {exc}", cause=exc)
            return None
    return attribute

def p_expression_and(p):
    'expression : expression AND expression'
    p[0] = bool(p[1]) and bool(p[3])

def p_expression_or(p):
    'expression : expression OR expression'
    p[0] = bool(p[1]) or bool(p[3])

def p_expression_not(p):
    'expression : NOT expression'
    p[0] = not bool(p[2])

def p_expression_equalto(p):
    'expression : expression EQUALTO expression'
    p[0] = p[1] == p[3]

def p_expression_notequalto(p):
    'expression : expression NOTEQUALTO expression'
    p[0] = p[1] != p[3]

def p_expression_greaterthan(p):
    'expression : expression GREATERTHAN expression'
    p[0] = p[1] > p[3]

def p_expression_lessthan(p):
    'expression : expression LESSTHAN expression'
    p[0] = p[1] < p[3]

def p_expression_greaterthanequalto(p):
    'expression : expression GREATERTHANEQUALTO expression'
    p[0] = p[1] >= p[3]

def p_expression_lessthanequalto(p):
    'expression : expression LESSTHANEQUALTO expression'
    p[0] = p[1] <= p[3]

def p_expression_true(p):
    'expression : TRUE'
    p[0] = True

def p_expression_false(p):
    'expression : FALSE'
    p[0] = False

def p_expression_null(p):
    'expression : NULL'
    p[0] = None

def p_expression_cond(p):
    'expression : COND LPAREN expression RPAREN'
    p[0] = bool(p[3])

def p_error(p):
    if p:
        report("Syntax error at '%s'" % p.value, offset=p.lexpos)
    else:
        report("Syntax error at end of input")

parser = yacc.yacc()

if __name__ == '__main__':
    while True:
        try:
            text = input('bs> ')
        except (EOFError, KeyboardInterrupt):
            break
        if not text.strip():
            continue
        result = parser.parse(text, lexer=lexer_module.lexer.clone())
        if result is not None:
            print(result)
