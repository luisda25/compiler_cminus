# Analizador léxico C- 
# Luis Daniel Filorio Luna A01028418
from globalTypes import *
import re

# Variables globalTypes
programa = ''
posicion = 0
progLong = 0

# Tabla de palabras reservadas
keywords = {
    'if': TokenType.IF,
    'else': TokenType.ELSE,
    'int': TokenType.INT,
    'return': TokenType.RETURN,
    'void': TokenType.VOID,
    'while': TokenType.WHILE
}

# Tabla de estados del DFA
from pathlib import Path
_tabla_path = Path(__file__).resolve().parent / 'tabla.txt'
with open(_tabla_path, 'r') as f:
    tabla = [[int(x) for x in line.split(',')] for line in f if line.strip()]

# Estados de aceptación y tokens
estados_aceptacion = {
    10: TokenType.NUM,
    11: TokenType.ID,
    12: TokenType.MULT,
    13: TokenType.COMMENT,
    14: TokenType.DIV,
    15: TokenType.LESS_EQUAL,
    16: TokenType.LESS,
    17: TokenType.GREAT_EQUAL,
    18: TokenType.GREAT,
    19: TokenType.EQUAL,
    20: TokenType.ASSIGN,
    21: TokenType.NOT_EQUAL,
    22: TokenType.SUM,
    23: TokenType.OPEN_PAR,
    24: TokenType.SUB,
    25: TokenType.SEMI_COLON,
    26: TokenType.CLOSE_PAR,
    27: TokenType.COMMA,
    28: TokenType.OPEN_COR,
    29: TokenType.CLOSE_COR,
    30: TokenType.OPEN_BR,
    31: TokenType.CLOSE_BR,
    32: TokenType.ERROR
}

estados_retroceso = {10, 11, 14, 16, 18, 20}

def globales(prog, pos, long):
    global programa
    global posicion
    global progLong
    programa = prog
    posicion = pos
    progLong = long


def getCategoria(c):
    if c.isdigit():
        return 0  # digit
    elif c.isalpha():
        return 1  # letter
    elif c in ' \t\n':
        return 2  # blank
    elif c == '+':
        return 3  # sum
    elif c == '-':
        return 4  # sub
    elif c == '/':
        return 5  # division
    elif c == '*':
        return 6  # times
    elif c == '<':
        return 7  # less
    elif c == '>':
        return 8  # greater
    elif c == '=':
        return 9  # assign
    elif c == '!':
        return 10 # exclamation
    elif c == '(':
        return 11 # open parenthesis
    elif c == '[':
        return 12 # open cor
    elif c == '{':
        return 13 # open bracket
    elif c == ')':
        return 14 # close parenthesis
    elif c == ']':
        return 15 # close cor
    elif c == '}':
        return 16 # close br
    elif c == ',':
        return 17 # comma
    elif c == ';':
        return 18 # semi-colon
    else:
        return 19  # NOT

# Funcion para detectar el tipo de token para el manejo de errores
def _inferir_token(lexema, estado):
    if estado == 0 or not lexema:
        return f"caracter no reconocido '{lexema}'"
    c = lexema[0]
    if c.isdigit():
        return "NUM"
    if c.isalpha():
        return "ID"
    if c == '!':
        return "NOT_EQUAL"
    if c == '<':
        return "LESS_EQUAL"
    if c == '>':
        return "GREAT_EQUAL"
    if c == '=':
        return "EQUAL"
    if c == '/':
        return "COMMENT"
    return f"'{c}'"

def getToken(imprime=True):
    global posicion
    estado = 0
    lexema = ''

    while True:
        # Obtener caracter actual
        c = programa[posicion]

        # EOF
        if c == '$':
            if imprime:
                print(f'{str(TokenType.ENDFILE):<22} = $')
            return TokenType.ENDFILE, ''

        categoria = getCategoria(c)

        # Consultar tabla de estados
        estado_siguiente = tabla[estado][categoria]

        # Checa el tipo de estado
        if estado_siguiente >= 10:
            if estado_siguiente in estados_retroceso:
                pass
            else:
                lexema += c
                posicion += 1

            # Obtiene el token
            token = estados_aceptacion[estado_siguiente]

            # Ignorar comentarios
            if token == TokenType.COMMENT:
                estado = 0
                lexema = ''
                continue

            # Checar si es un keyword
            if token == TokenType.ID:
                token = keywords.get(lexema, TokenType.ID)

            # Error handler 
            if token == TokenType.ERROR:
                if estado == 0:
                    lexema = c
                    pos_error = posicion - 1
                else:
                    lexema = lexema.strip()
                    pos_error = posicion - len(lexema)

                nombre_token = _inferir_token(lexema, estado)
                linea = programa[:pos_error].count('\n') + 1
                linea_contenido = programa.split('\n')[linea - 1]
                pos_en_linea = pos_error - programa[:pos_error].rfind('\n') - 1
                print(f'Linea {linea}: Error en la formacion del token {nombre_token}:')
                print(linea_contenido)
                print(' ' * pos_en_linea + '^')
                token = TokenType.ERROR

            if imprime and token != TokenType.ENDFILE:
                print(f'{str(token):<22} = {lexema}')

            return token, lexema
        
        else:
            if not (estado == 0 and categoria == 2):
                lexema += c 
            posicion += 1
            estado = estado_siguiente
