import ply.yacc as yacc
import lexer as lexer_module
from lexer import tokens
import math

# variable storage
names = {}

precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    ('right', 'NOT'),
    ('left', 'EQUALTO', 'NOTEQUALTO'),
    ('left', 'LESSTHAN', 'GREATERTHAN', 'LESSTHANEQUALTO', 'GREATERTHANEQUALTO'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'MULTIPLY', 'DIVIDE'),
    ('right', 'POWER'),
)

def p_expression_number(p):
    'expression : NUMBER'
    p[0] = p[1]

def p_expression_group(p):
    'expression : LPAREN expression RPAREN'
    p[0] = p[2]

def p_expression_plus(p):
    'expression : expression PLUS expression'
    p[0] = p[1] + p[3]

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

def p_expression_print_string(p):
    'expression : PRINT LPAREN STRING RPAREN'
    print(p[3])
    p[0] = None

def p_statement_assign(p):
    'expression : NAME EQ expression'
    names[p[1]] = p[3]

def p_expression_name(p):
    'expression : NAME'
    try:
        p[0] = names[p[1]]
    except KeyError:
        print(f'Undefined variable: {p[1]}')
        p[0] = 0

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
