# Parser C-
# Luis Daniel Filorio Luna A01028418

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lexer'))

from lexer import *
import lexer as _lexer
from enum import Enum

TokenType = _lexer.TokenType   # exposición explícita para el analizador estático


class TipoNodo(Enum):
    # Declaraciones
    PROGRAMA       = 0
    VAR_DECL       = 1
    FUN_DECL       = 2
    PARAM_LIST     = 3   # wrapper: lista de parámetros
    PARAMS_VOID    = 4   # params vacíos (void)
    PARAM          = 5
    # Sentencias
    COMPOUND_STMT  = 6
    LOCAL_DECLS    = 7   # wrapper: declaraciones locales
    STMT_LIST      = 8   # wrapper: lista de sentencias
    EXPR_STMT      = 9
    SELECTION_STMT = 10
    ITERATION_STMT = 11
    RETURN_STMT    = 12
    # Expresiones
    ASSIGN_EXP     = 13
    OP_EXP         = 14
    CONST_EXP      = 15
    ID_EXP         = 16
    CALL_EXP       = 17
    ARG_LIST       = 18  # wrapper: lista de argumentos
    ARGS_EMPTY     = 19  # args vacíos


class NodoArbol:
    def __init__(self):
        self.hijoIzq  = None   # primer hijo
        self.hijoDer  = None   # segundo hijo
        self.hijoTer  = None   # tercer hijo (else en if-else)
        self.hermano  = None   # siguiente nodo en una secuencia
        self.exp      = None   # TipoNodo
        self.op       = None   # operador
        self.value    = 0      # valor numérico
        self.nombre   = ''     # nombre de identificador
        self.tipo     = None   # tipo de dato (TokenType.INT / TokenType.VOID)
        self.esArr    = False  # ¿es arreglo?
        self.tamano   = 0      # tamaño del arreglo


def nuevoNodo(tipo):
    t = NodoArbol()
    if t is None:
        print('Se terminó la memoria')
    else:
        t.exp = tipo
    return t


# Variables globales 

programa    = ''
posicion    = 0
progLong    = 0
token       = None
tokenString = ''
_linea_tok  = 1
_col_tok    = 0
hayError    = False
endentacion = 0


def globales(prog, pos, long):
    global programa, posicion, progLong
    programa = prog
    posicion = pos
    progLong = long
    _lexer.globales(prog, pos, long)


# Manejo de tokens 

def avanzar():
    global token, tokenString, _linea_tok, _col_tok
    # Loop para saltar tokens ERROR del lexer (el lexer ya imprimió el mensaje)
    while True:
        pos_pre = _lexer.posicion
        prog    = _lexer.programa
        while pos_pre < len(prog) and prog[pos_pre] in ' \t\n':
            pos_pre += 1
        texto_pre  = prog[:pos_pre]
        _linea_tok = texto_pre.count('\n') + 1
        _col_tok   = pos_pre - texto_pre.rfind('\n') - 1
        token, tokenString = getToken(False)
        if token != TokenType.ERROR:
            break


def errorSintaxis(mensaje):
    global hayError
    hayError   = True
    prog_lines = _lexer.programa.split('\n')
    linea_str  = prog_lines[_linea_tok - 1] if _linea_tok <= len(prog_lines) else ''
    linea_str  = linea_str.rstrip('$')
    print(f'Línea {_linea_tok}: Error de sintaxis: {mensaje}:')
    print(linea_str)
    print(' ' * max(0, _col_tok) + '^')


def match(esperado):
    if token == esperado:
        avanzar()
    else:
        errorSintaxis(f"se esperaba '{esperado.value}' pero se encontró '{tokenString}'")


_RELOPS = {
    TokenType.LESS_EQUAL, TokenType.LESS,
    TokenType.GREAT, TokenType.GREAT_EQUAL,
    TokenType.EQUAL, TokenType.NOT_EQUAL,
}
_STMT_FIRST = {
    TokenType.OPEN_PAR, TokenType.NUM, TokenType.ID,
    TokenType.OPEN_BR, TokenType.IF, TokenType.WHILE,
    TokenType.RETURN, TokenType.SEMI_COLON,
}
_SYNC_DECL = {TokenType.INT, TokenType.VOID, TokenType.ENDFILE}


def _panic(sync_tokens):
    while token not in sync_tokens and token != TokenType.ENDFILE:
        avanzar()


# Construir cadena de hermanos

def lista_hermanos(lista):
    """Recibe una lista de NodoArbol y los enlaza como hermanos; devuelve el primero."""
    if not lista:
        return None
    nodos = [n for n in lista if n is not None]
    for i in range(len(nodos) - 1):
        nodos[i].hermano = nodos[i + 1]
    return nodos[0] if nodos else None


# Gramática 

def program():
    t = nuevoNodo(TipoNodo.PROGRAMA)
    t.hijoIzq = declaration_list()
    return t


def declaration_list():
    decls = []
    while token in (TokenType.INT, TokenType.VOID):
        d = declaration()
        if d is not None:
            decls.append(d)
    return lista_hermanos(decls)


def declaration():
    tipo = type_specifier()
    if token != TokenType.ID:
        errorSintaxis(f"se esperaba un identificador pero se encontró '{tokenString}'")
        _panic(_SYNC_DECL | {TokenType.SEMI_COLON})
        return None
    nombre = tokenString
    match(TokenType.ID)

    if token == TokenType.SEMI_COLON:
        return _finish_var_decl(tipo, nombre, False, 0)
    elif token == TokenType.OPEN_COR:
        match(TokenType.OPEN_COR)
        if token != TokenType.NUM:
            errorSintaxis(f"se esperaba tamaño de arreglo pero se encontró '{tokenString}'")
            _panic({TokenType.SEMI_COLON, TokenType.CLOSE_BR})
            return None
        tam = int(tokenString)
        match(TokenType.NUM)
        match(TokenType.CLOSE_COR)
        return _finish_var_decl(tipo, nombre, True, tam)
    elif token == TokenType.OPEN_PAR:
        return _finish_fun_decl(tipo, nombre)
    else:
        errorSintaxis(f"token inesperado '{tokenString}' en declaración")
        _panic(_SYNC_DECL)
        return None


def _finish_var_decl(tipo, nombre, es_arr, tamano):
    match(TokenType.SEMI_COLON)
    t = nuevoNodo(TipoNodo.VAR_DECL)
    t.tipo   = tipo
    t.nombre = nombre
    t.esArr  = es_arr
    t.tamano = tamano
    return t


def _finish_fun_decl(tipo, nombre):
    match(TokenType.OPEN_PAR)
    ps     = params()           # nodo PARAM_LIST o PARAMS_VOID
    match(TokenType.CLOSE_PAR)
    cuerpo = compound_stmt()
    t = nuevoNodo(TipoNodo.FUN_DECL)
    t.tipo    = tipo
    t.nombre  = nombre
    t.hijoIzq = ps              # nodo de parámetros
    t.hijoDer = cuerpo
    return t


def type_specifier():
    if token == TokenType.INT:
        match(TokenType.INT)
        return TokenType.INT
    elif token == TokenType.VOID:
        match(TokenType.VOID)
        return TokenType.VOID
    else:
        errorSintaxis(f"se esperaba 'int' o 'void' pero se encontró '{tokenString}'")
        _panic({TokenType.ID, TokenType.SEMI_COLON, TokenType.CLOSE_PAR})
        return None


def params():
    if token == TokenType.VOID:
        match(TokenType.VOID)
        if token == TokenType.CLOSE_PAR:
            return nuevoNodo(TipoNodo.PARAMS_VOID)
        # void es el tipo del primer parámetro
        p = nuevoNodo(TipoNodo.PARAM)
        p.tipo = TokenType.VOID
        if token != TokenType.ID:
            errorSintaxis(f"se esperaba identificador en parámetro pero se encontró '{tokenString}'")
            _panic({TokenType.COMMA, TokenType.CLOSE_PAR})
            return nuevoNodo(TipoNodo.PARAM_LIST)
        p.nombre = tokenString
        match(TokenType.ID)
        if token == TokenType.OPEN_COR:
            match(TokenType.OPEN_COR)
            match(TokenType.CLOSE_COR)
            p.esArr = True
        lista = [p]
        while token == TokenType.COMMA:
            match(TokenType.COMMA)
            lista.append(param())
        t = nuevoNodo(TipoNodo.PARAM_LIST)
        t.hijoIzq = lista_hermanos(lista)
        return t
    elif token == TokenType.INT:
        return param_list()
    elif token == TokenType.CLOSE_PAR:
        return nuevoNodo(TipoNodo.PARAMS_VOID)
    else:
        errorSintaxis(f"se esperaba parámetros pero se encontró '{tokenString}'")
        _panic({TokenType.CLOSE_PAR})
        return nuevoNodo(TipoNodo.PARAMS_VOID)


def param_list():
    lista = [param()]
    while token == TokenType.COMMA:
        match(TokenType.COMMA)
        lista.append(param())
    t = nuevoNodo(TipoNodo.PARAM_LIST)
    t.hijoIzq = lista_hermanos(lista)
    return t


def param():
    tipo = type_specifier()
    if token != TokenType.ID:
        errorSintaxis(f"se esperaba identificador en parámetro pero se encontró '{tokenString}'")
        _panic({TokenType.COMMA, TokenType.CLOSE_PAR})
        return nuevoNodo(TipoNodo.PARAM)
    t = nuevoNodo(TipoNodo.PARAM)
    t.tipo   = tipo
    t.nombre = tokenString
    match(TokenType.ID)
    if token == TokenType.OPEN_COR:
        match(TokenType.OPEN_COR)
        match(TokenType.CLOSE_COR)
        t.esArr = True
    return t


def compound_stmt():
    if token != TokenType.OPEN_BR:
        errorSintaxis(f"se esperaba '{{' pero se encontró '{tokenString}'")
        _panic({TokenType.CLOSE_BR, TokenType.ENDFILE})
        return nuevoNodo(TipoNodo.COMPOUND_STMT)
    match(TokenType.OPEN_BR)
    t = nuevoNodo(TipoNodo.COMPOUND_STMT)
    ld = nuevoNodo(TipoNodo.LOCAL_DECLS)
    ld.hijoIzq = local_declarations()
    sl = nuevoNodo(TipoNodo.STMT_LIST)
    sl.hijoIzq = statement_list()
    t.hijoIzq = ld
    t.hijoDer = sl
    if token != TokenType.CLOSE_BR:
        _panic({TokenType.CLOSE_BR, TokenType.ENDFILE})
    match(TokenType.CLOSE_BR)
    return t


def local_declarations():
    decls = []
    while token in (TokenType.INT, TokenType.VOID):
        tipo = type_specifier()
        if token != TokenType.ID:
            errorSintaxis(f"se esperaba identificador en declaración local pero se encontró '{tokenString}'")
            _panic({TokenType.SEMI_COLON, TokenType.CLOSE_BR})
            continue
        nombre = tokenString
        match(TokenType.ID)
        if token == TokenType.OPEN_COR:
            match(TokenType.OPEN_COR)
            if token != TokenType.NUM:
                errorSintaxis(f"se esperaba tamaño de arreglo pero se encontró '{tokenString}'")
                _panic({TokenType.SEMI_COLON})
                continue
            tam = int(tokenString)
            match(TokenType.NUM)
            match(TokenType.CLOSE_COR)
            decls.append(_finish_var_decl(tipo, nombre, True, tam))
        else:
            decls.append(_finish_var_decl(tipo, nombre, False, 0))
    return lista_hermanos(decls)


def statement_list():
    stmts = []
    while token in _STMT_FIRST:
        s = statement()
        if s is not None:
            stmts.append(s)
    return lista_hermanos(stmts)


def statement():
    if token == TokenType.OPEN_BR:
        return compound_stmt()
    elif token == TokenType.IF:
        return selection_stmt()
    elif token == TokenType.WHILE:
        return iteration_stmt()
    elif token == TokenType.RETURN:
        return return_stmt()
    else:
        return expression_stmt()


def expression_stmt():
    t = nuevoNodo(TipoNodo.EXPR_STMT)
    if token == TokenType.SEMI_COLON:
        match(TokenType.SEMI_COLON)
    else:
        t.hijoIzq = expression()
        # Pánico: si no encontramos ';', buscar uno para sincronizar
        if token != TokenType.SEMI_COLON:
            _panic({TokenType.SEMI_COLON, TokenType.CLOSE_BR, TokenType.ENDFILE})
        match(TokenType.SEMI_COLON)
    return t


def selection_stmt():
    t = nuevoNodo(TipoNodo.SELECTION_STMT)
    match(TokenType.IF)
    match(TokenType.OPEN_PAR)
    t.hijoIzq = expression()    # condición
    match(TokenType.CLOSE_PAR)
    t.hijoDer = statement()     # rama then
    if token == TokenType.ELSE:
        match(TokenType.ELSE)
        t.hijoTer = statement() # rama else
    return t


def iteration_stmt():
    t = nuevoNodo(TipoNodo.ITERATION_STMT)
    match(TokenType.WHILE)
    match(TokenType.OPEN_PAR)
    t.hijoIzq = expression()    # condición
    match(TokenType.CLOSE_PAR)
    t.hijoDer = statement()     # cuerpo
    return t


def return_stmt():
    t = nuevoNodo(TipoNodo.RETURN_STMT)
    match(TokenType.RETURN)
    if token != TokenType.SEMI_COLON:
        t.hijoIzq = expression()
    match(TokenType.SEMI_COLON)
    return t


# expression → var = expression | simple-expression
# Al ver un ID se consume primero; después se decide si es asignación o no.
def expression():
    if token == TokenType.ID:
        nombre = tokenString
        avanzar()              # consumir ID

        if token == TokenType.OPEN_PAR:
            left = _finish_call(nombre)
        elif token == TokenType.OPEN_COR:
            left = _finish_var_subscript(nombre)
            if token == TokenType.ASSIGN:
                match(TokenType.ASSIGN)
                p = nuevoNodo(TipoNodo.ASSIGN_EXP)
                p.hijoIzq = left
                p.hijoDer = expression()
                return p
        else:
            left = nuevoNodo(TipoNodo.ID_EXP)
            left.nombre = nombre
            if token == TokenType.ASSIGN:
                match(TokenType.ASSIGN)
                p = nuevoNodo(TipoNodo.ASSIGN_EXP)
                p.hijoIzq = left
                p.hijoDer = expression()
                return p

        return _simple_expr_desde_factor(left)
    else:
        return simple_expression()


def _finish_call(nombre):
    match(TokenType.OPEN_PAR)
    t = nuevoNodo(TipoNodo.CALL_EXP)
    t.nombre  = nombre
    t.hijoIzq = args()          # cadena de argumentos (hermanos)
    match(TokenType.CLOSE_PAR)
    return t


def _finish_var_subscript(nombre):
    match(TokenType.OPEN_COR)
    t = nuevoNodo(TipoNodo.ID_EXP)
    t.nombre  = nombre
    t.esArr   = True
    t.hijoIzq = expression()    # índice
    match(TokenType.CLOSE_COR)
    return t


def simple_expression():
    left = additive_expression()
    return _simple_cont(left)


def _simple_expr_desde_factor(f):
    left = _additive_desde_factor(f)
    return _simple_cont(left)


def _simple_cont(left):
    if token in _RELOPS:
        t = nuevoNodo(TipoNodo.OP_EXP)
        t.op      = tokenString
        t.hijoIzq = left
        avanzar()
        t.hijoDer = additive_expression()
        return t
    return left


def additive_expression():
    left = term()
    return _additive_rest(left)


def _additive_desde_factor(f):
    left = _term_rest(f)
    return _additive_rest(left)


def _additive_rest(left):
    while token in (TokenType.SUM, TokenType.SUB):
        t = nuevoNodo(TipoNodo.OP_EXP)
        t.op      = tokenString
        t.hijoIzq = left
        avanzar()
        t.hijoDer = term()
        left = t
    return left


def term():
    left = factor()
    return _term_rest(left)


def _term_rest(left):
    while token in (TokenType.MULT, TokenType.DIV):
        t = nuevoNodo(TipoNodo.OP_EXP)
        t.op      = tokenString
        t.hijoIzq = left
        avanzar()
        t.hijoDer = factor()
        left = t
    return left


def factor():
    if token == TokenType.OPEN_PAR:
        match(TokenType.OPEN_PAR)
        t = expression()
        match(TokenType.CLOSE_PAR)
        return t
    elif token == TokenType.NUM:
        t = nuevoNodo(TipoNodo.CONST_EXP)
        t.value = int(tokenString)
        match(TokenType.NUM)
        return t
    elif token == TokenType.ID:
        nombre = tokenString
        avanzar()
        if token == TokenType.OPEN_PAR:
            return _finish_call(nombre)
        elif token == TokenType.OPEN_COR:
            return _finish_var_subscript(nombre)
        else:
            t = nuevoNodo(TipoNodo.ID_EXP)
            t.nombre = nombre
            return t
    else:
        errorSintaxis(f"token inesperado '{tokenString}' en expresión")
        _panic({TokenType.SEMI_COLON, TokenType.CLOSE_PAR, TokenType.CLOSE_BR, TokenType.COMMA})
        return nuevoNodo(TipoNodo.CONST_EXP)


def args():
    if token == TokenType.CLOSE_PAR:
        return nuevoNodo(TipoNodo.ARGS_EMPTY)
    lista = [expression()]
    while token == TokenType.COMMA:
        match(TokenType.COMMA)
        lista.append(expression())
    t = nuevoNodo(TipoNodo.ARG_LIST)
    t.hijoIzq = lista_hermanos(lista)
    return t


# Imprimir el AST

def imprimeEspacios():
    print(' ' * endentacion, end='')


def imprimirAST(arbol):
    global endentacion
    endentacion += 2
    if arbol is not None:
        imprimeEspacios()
        t = arbol.exp
        ts = '<int>' if arbol.tipo == TokenType.INT else '<void>'
        if t == TipoNodo.PROGRAMA:
            print('Declaration: Program')
        elif t == TipoNodo.VAR_DECL:
            print(f'Declaration: Var Declaration [{arbol.nombre}] {ts}')
        elif t == TipoNodo.FUN_DECL:
            print(f'Declaration: Function Declaration [{arbol.nombre}] {ts}')
        elif t == TipoNodo.PARAM_LIST:
            print('Declaration: Param List')
        elif t == TipoNodo.PARAMS_VOID:
            print('Declaration: Params [void]')
        elif t == TipoNodo.PARAM:
            nombre_arr = f'{arbol.nombre}[]' if arbol.esArr else arbol.nombre
            print(f'Declaration: Parameter [{nombre_arr}] {ts}')
        elif t == TipoNodo.COMPOUND_STMT:
            print('Statement: Compound')
        elif t == TipoNodo.LOCAL_DECLS:
            print('Declaration: Local Declarations')
        elif t == TipoNodo.STMT_LIST:
            print('Statement: Statement List')
        elif t == TipoNodo.EXPR_STMT:
            print('Statement: Expression Stmt')
        elif t == TipoNodo.SELECTION_STMT:
            print('Statement: If')
        elif t == TipoNodo.ITERATION_STMT:
            print('Statement: While')
        elif t == TipoNodo.RETURN_STMT:
            print('Statement: Return')
        elif t == TipoNodo.ASSIGN_EXP:
            print('Expression: Assign')
        elif t == TipoNodo.OP_EXP:
            print(f'Expression: Operation [{arbol.op}]')
        elif t == TipoNodo.CONST_EXP:
            print(f'Expression: Constant [{arbol.value}]')
        elif t == TipoNodo.ID_EXP:
            print(f'Expression: Variable [{arbol.nombre}]')
        elif t == TipoNodo.CALL_EXP:
            print(f'Expression: Call [{arbol.nombre}]')
        elif t == TipoNodo.ARG_LIST:
            print('Expression: Arg List')
        elif t == TipoNodo.ARGS_EMPTY:
            print('Expression: Args [empty]')
        else:
            print(f'Nodo desconocido: {t}')
        imprimirAST(arbol.hijoIzq)
        imprimirAST(arbol.hijoDer)
        imprimirAST(arbol.hijoTer)
    endentacion -= 2
    if arbol is not None and arbol.hermano is not None:
        imprimirAST(arbol.hermano)

def parser(imprime=True):
    global token, tokenString, endentacion, hayError
    hayError    = False
    endentacion = -2    # el nodo raíz imprime sin sangría
    avanzar()
    ast = program()
    if token != TokenType.ENDFILE:
        errorSintaxis(f"se esperaba fin de archivo pero se encontró '{tokenString}'")
    if imprime:
        if hayError:
            print('\n--- AST (con errores) ---')
        imprimirAST(ast)
    return ast


if __name__ == '__main__':
    archivo = input('Archivo C-: ').strip()
    with open(archivo, 'r') as f:
        prog = f.read()
    prog += '$'
    globales(prog, 0, len(prog) - 1)
    parser(imprime=True)
