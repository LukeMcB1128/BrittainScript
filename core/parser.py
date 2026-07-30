import ply.yacc as yacc
import lexer as lexer_module
from lexer import tokens
import math
import os
import gui_backend
import calendar
import datetime

# variable storage
names = {}
scopes = [names]
function_caller = None
module_caller = None

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'EQUALTO', 'NOTEQUALTO'),
    ('left', 'LESSTHAN', 'GREATERTHAN', 'LESSTHANEQUALTO', 'GREATERTHANEQUALTO'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'MULTIPLY', 'DIVIDE', 'MODULO', 'AT'),
    ('right', 'POWER'),
    ('left', 'LBRACKET'),
    ('left', 'DOT'),
)

def push_scope(scope=None):
    scopes.append({} if scope is None else scope)

def pop_scope():
    if len(scopes) > 1:
        scopes.pop()

def get_name(name):
    for scope in reversed(scopes):
        if name in scope:
            return scope[name]
    raise KeyError(name)

def set_name(name, value):
    for scope in reversed(scopes):
        if name in scope:
            scope[name] = value
            return
    scopes[-1][name] = value

def assign_target(target, value):
    target = target.strip()
    indexed = re_match_index(target)
    if indexed:
        name, index_text = indexed
        try:
            container = get_name(name)
            index = parser.parse(index_text, lexer=lexer_module.lexer.clone())
            container[index] = value
        except KeyError:
            print(f'Undefined variable: {name}')
        except (TypeError, IndexError):
            print("Error: invalid assignment target")
        return
    set_name(target, value)

def re_match_index(target):
    import re
    match = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*)\s*\[(.+)\]', target)
    if not match:
        return None
    return match.group(1), match.group(2)

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
    except TypeError:
        print(f"Error: cannot add {type(p[1]).__name__} and {type(p[3]).__name__}")
        p[0] = None

def p_expression_minus(p):
    'expression : expression MINUS expression'
    p[0] = p[1] - p[3]

def p_expression_divide(p):
    'expression : expression DIVIDE expression'
    if p[3] == 0:
        print("Error: division by zero")
        p[0] = None
        return
    p[0] = p[1] / p[3]

def p_expression_times(p):
    'expression : expression MULTIPLY expression'
    try:
        p[0] = p[1] * p[3]
    except TypeError:
        print(f"Error: cannot multiply {type(p[1]).__name__} and {type(p[3]).__name__}")
        p[0] = None

def p_expression_matmul(p):
    'expression : expression AT expression'
    try:
        p[0] = p[1] @ p[3]
    except TypeError as exc:
        print(f"Error: cannot matrix-multiply: {exc}")
        p[0] = None

def p_expression_modulo(p):
    'expression : expression MODULO expression'
    if p[3] == 0:
        print("Error: modulo by zero")
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
        print(f'Undefined variable: {p[1]}')
        p[0] = 0

def p_expression_list(p):
    'expression : LBRACKET optional_arguments RBRACKET'
    p[0] = p[2]

def p_expression_index(p):
    'expression : expression LBRACKET expression RBRACKET'
    try:
        p[0] = p[1][p[3]]
    except (TypeError, IndexError, KeyError):
        print("Error: invalid index")
        p[0] = None

def p_expression_slice(p):
    'expression : expression LBRACKET optional_expression COLON optional_expression RBRACKET'
    try:
        p[0] = p[1][p[3]:p[5]]
    except TypeError:
        print("Error: invalid slice")
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
    p[0] = call_function(p[1], p[3])

def p_expression_range_call(p):
    'expression : RANGE LPAREN optional_arguments RPAREN'
    p[0] = call_function('range', p[3])

def p_expression_method_call(p):
    'expression : expression DOT NAME LPAREN optional_arguments RPAREN'
    p[0] = call_method(p[1], p[3], p[5])

def p_expression_attribute(p):
    'expression : expression DOT NAME'
    receiver, attr = p[1], p[3]
    if isinstance(receiver, dict) and receiver.get('__bs_module__'):
        print(f"Error: '{receiver['name']}' members must be called")
        p[0] = None
        return
    try:
        p[0] = getattr(receiver, attr)
    except AttributeError:
        print(f"Error: no attribute '{attr}' on {type(receiver).__name__}")
        p[0] = None

def call_function(name, args):
    if name == 'pyimport':
        if len(args) != 1 or not isinstance(args[0], str):
            print("Error: pyimport() expects one string argument")
            return None
        import importlib
        try:
            return importlib.import_module(args[0])
        except ImportError as exc:
            print(f"Error: cannot import '{args[0]}': {exc}")
            return None
    if name == 'len':
        if len(args) != 1:
            print("Error: len() expects 1 argument")
            return None
        return len(args[0])
    if name == 'tonum':
        if len(args) != 1:
            print("Error: tonum() expects 1 argument")
            return None
        try:
            value = float(args[0]) if '.' in str(args[0]) else int(args[0])
            return value
        except ValueError:
            print("Error: tonum() could not convert value")
            return None
    if name == 'tostr':
        if len(args) != 1:
            print("Error: tostr() expects 1 argument")
            return None
        return str(display(args[0]))
    if name == 'input':
        if len(args) > 1:
            print("Error: input() expects 0 or 1 arguments")
            return None
        return input(args[0] if args else '')
    if name == 'range':
        if len(args) not in (1, 2, 3):
            print("Error: range() expects 1 to 3 arguments")
            return []
        return list(range(*args))
    if name == 'clear':
        os.system('cls' if os.name == 'nt' else 'clear')
        return None
    if name == 'absolute':
        if len(args) != 1:
            print("Error: absolute() expects 1 argument")
            return None
        return abs(args[0])
    if name == 'round':
        if len(args) != 1:
            print("Error: round() expects 1 argument")
            return None
        return round(args[0])
    if name == 'floor':
        if len(args) != 1:
            print("Error: floor() expects 1 argument")
            return None
        return math.floor(args[0])
    if name == 'ceiling':
        if len(args) != 1:
            print("Error: ceiling() expects 1 argument")
            return None
        return math.ceil(args[0])
    if name == 'type':
        if len(args) != 1:
            print("Error: type() expects 1 argument")
            return None
        return type(args[0])
    if name == 'readfile':
        if len(args) != 1:
            print("Error: readfile() expects 1 argument")
            return None
        try:
            with open(args[0], 'r') as f:
                return f.read()
        except OSError as error:
            print(f"Error: could not read file '{args[0]}': {error}")
            return None
    if name == 'readlines':
        if len(args) != 1:
            print("Error: readlines() expects 1 argument")
            return None
        try:
            with open(args[0], 'r') as f:
                return [line.rstrip('\n') for line in f.readlines()]
        except OSError as error:
            print(f"Error: could not read file '{args[0]}': {error}")
            return None
    if name == 'createfile':
        if len(args) != 1:
            print("Error: createfile() expects 1 argument")
            return None
        try:
            with open(args[0], 'x'):
                pass
            return True
        except FileExistsError:
            print(f"Error: file '{args[0]}' already exists")
            return False
        except OSError as error:
            print(f"Error: could not create file '{args[0]}': {error}")
            return False
    if name == 'writefile':
        if len(args) != 2:
            print("Error: writefile() expects 2 arguments")
            return None
        try:
            with open(args[0], 'w') as f:
                f.write(str(args[1]))
            return True
        except OSError as error:
            print(f"Error: could not write file '{args[0]}': {error}")
            return False
    if name == 'appendfile':
        if len(args) != 2:
            print("Error: appendfile() expects 2 arguments")
            return None
        try:
            with open(args[0], 'a') as f:
                f.write(str(args[1]))
            return True
        except OSError as error:
            print(f"Error: could not append to file '{args[0]}': {error}")
            return False
    if name == 'fileexists':
        if len(args) != 1:
            print("Error: fileexists() expects 1 argument")
            return None
        return os.path.exists(args[0])
    if name == 'deletefile':
        if len(args) != 1:
            print("Error: deletefile() expects 1 argument")
            return None
        try:
            os.remove(args[0])
            return True
        except OSError as error:
            print(f"Error: could not delete file '{args[0]}': {error}")
            return False
    if name == "datetime":
        return call_datetime(args)
    if gui_backend.is_gui_builtin(name):
        return gui_backend.call_builtin(name, args)
    if function_caller:
        return function_caller(name, args)
    print(f"Undefined function: {name}")
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
        print("Error: datetime() expects a command argument")
        return None
    command = args[0]
    entry = DATETIME_COMMANDS.get(command)
    if entry is None:
        print(f"Error: unknown datetime command '{command}'")
        return None
    arity, handler = entry
    rest = args[1:]
    if len(rest) != arity:
        print(f"Error: datetime {command}() expects {arity} argument{'s' if arity != 1 else ''}")
        return None
    try:
        return handler(rest)
    except (AttributeError, TypeError, ValueError) as error:
        print(f"Error: datetime {command}() failed: {error}")
        return None

def call_method(receiver, name, args):
    if isinstance(receiver, dict) and receiver.get('__bs_module__'):
        if module_caller:
            return module_caller(receiver, name, args)
        print(f"Error: no module caller set")
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
        if args[0] in receiver:
            return True
        else:
            return False
    if name == 'locate' and isinstance(receiver, str) and len(args) == 1:
        return receiver.find(args[0])
    if name == 'remove' and isinstance(receiver, list) and len(args) == 1:
        try:
            receiver.remove(args[0])
        except ValueError:
            print("Error: list does not contain value")
        return None
    if name == 'pop' and isinstance(receiver, list) and len(args) == 0:
        if not receiver:
            print("Error: cannot pop from an empty list")
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
        print(f"Error: no method '{name}' on {type(receiver).__name__}")
        return None
    if callable(attribute):
        try:
            return attribute(*args)
        except Exception as exc:
            print(f"Error calling '{name}': {exc}")
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
        print("Syntax error at '%s'" % p.value)
    else:
        print("Syntax error at end of input")

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
