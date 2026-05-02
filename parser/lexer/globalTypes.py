from enum import Enum 

class TokenType(Enum):
    # Tipos de datos
    NUM = 'NUM'
    ID = 'ID'

    # Palabras reservadas
    IF = 'IF'
    ELSE = 'ELSE'
    INT = 'INT'
    RETURN = 'RETURN'
    VOID = 'VOID'
    WHILE = 'WHILE'

    # Operadores relacionales
    LESS = '<'
    LESS_EQUAL = '<='
    GREAT = '>'
    GREAT_EQUAL = '>='
    EQUAL = '=='
    ASSIGN = '='
    NOT_EQUAL = '!='

    # Operadores aritméticos
    SUM = '+'
    SUB = '-'
    MULT = '*'
    DIV = '/'

    # Símbolos de agrupación
    OPEN_PAR = '('
    CLOSE_PAR = ')'
    OPEN_COR = '['
    CLOSE_COR = ']'
    OPEN_BR = '{'
    CLOSE_BR = '}'
     
    # Puntuación
    SEMI_COLON = ';'
    COMMA = ','

    # Especiales
    COMMENT = 'COMMENT'
    ENDFILE = '$'
    ERROR = 'ERROR'
