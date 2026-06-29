import ply.yacc as yacc
import lexer as lexer_module
from lexer import tokens
import math

# variable storage
names = {}
scopes = [names]
function_caller = None

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'EQUALTO', 'NOTEQUALTO'),
    ('left', 'LESSTHAN', 'GREATERTHAN', 'LESSTHANEQUALTO', 'GREATERTHANEQUALTO'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'MULTIPLY', 'DIVIDE'),
    ('right', 'POWER'),
    ('left', 'LBRACKET'),
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
    p[0] = p[1] * p[3]

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

def p_expression_print(p):
    'expression : PRINT LPAREN expression RPAREN'
    print(p[3])
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

def call_function(name, args):
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
        return str(args[0])
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
    if function_caller:
        return function_caller(name, args)
    print(f"Undefined function: {name}")
    return None

def call_method(receiver, name, args):
    if name == 'upper' and isinstance(receiver, str) and not args:
        return receiver.upper()
    if name == 'lower' and isinstance(receiver, str) and not args:
        return receiver.lower()
    if name == 'trim' and isinstance(receiver, str) and not args:
        return receiver.strip()
    if name == 'add' and isinstance(receiver, list) and len(args) == 1:
        receiver.append(args[0])
        return None
    print(f"Error: unsupported method {name}()")
    return None

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
