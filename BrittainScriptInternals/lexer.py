import ply.lex as lex
import math

tokens = (
    'NUMBER',
    'PLUS',
    'MINUS',
    'DIVIDE',
    'MULTIPLY',
    'POWER',
    'LPAREN',
    'RPAREN',
    'STRING',
    # keywords — resolved from ID
    'SQUAREROOT',
    'SINE',
    'COSINE',
    'TANGENT',
    'PI',
    'PRINT',
    # variables
    'NAME',
    'EQ',
    # booleans and logic comparsions
    'AND',
    'OR',
    'NOT',
    'EQUALTO',
    'NOTEQUALTO',
    'GREATERTHAN',
    'LESSTHAN',
    'GREATERTHANEQUALTO',
    'LESSTHANEQUALTO',
    'TRUE',
    'FALSE'
)

reserved = {
    'sqrroot': 'SQUAREROOT',
    'sin':     'SINE',
    'cos':     'COSINE',
    'tan':     'TANGENT',
    'pi':      'PI',
    'push':    'PRINT',
    'and':     'AND',
    'or':      'OR',
    'not':     'NOT',
    'true':    'TRUE',
    'false':   'FALSE',
}

t_PLUS     = r'\+'
t_MINUS    = r'\-'
t_DIVIDE   = r'\/'
t_MULTIPLY = r'\*'
t_POWER    = r'\^'
t_LPAREN   = r'\('
t_RPAREN   = r'\)'
t_EQ       = r'='

def t_EQUALTO(t):
    r'=='
    return t

def t_NOTEQUALTO(t):
    r'!='
    return t

def t_GREATERTHANEQUALTO(t):
    r'>='
    return t

def t_LESSTHANEQUALTO(t):
    r'<='
    return t

def t_GREATERTHAN(t):
    r'>'
    return t

def t_LESSTHAN(t):
    r'<'
    return t

def t_NUMBER(t):
    r'\d+(\.\d+)?'
    t.value = float(t.value) if '.' in t.value else int(t.value)
    return t

def t_NAME(t):
    r'[a-zA-Z_][a-zA-Z0-9_]*'
    t.type = reserved.get(t.value, 'NAME')
    return t

def t_STRING(t):
    r'"[^"]*"'
    t.value = t.value[1:-1]
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

t_ignore = ' \t'

def t_error(t):
    print("Illegal character: '%s'" % t.value[0])
    t.lexer.skip(1)

lexer = lex.lex()
