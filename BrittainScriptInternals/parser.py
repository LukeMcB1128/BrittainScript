import ply.yacc as yacc
import lexer as lexer_module
from lexer import tokens
import math

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
    p[0] = p[3]

def p_expression_string(p):
    'expression : STRING'
    p[0] = p[1]

def p_expression_print_string(p):
    'expression : PRINT LPAREN STRING RPAREN'
    print(p[3])
    p[0] = p[3]

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
