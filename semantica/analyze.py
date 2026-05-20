import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in [_HERE,
           os.path.join(_HERE, 'parser'),
           os.path.join(_HERE, 'parser', 'lexer'),
           os.path.dirname(_HERE)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from parser import TipoNodo                              # noqa: E402
from globalTypes import TokenType  # noqa: E402  lexer/ is in sys.path (added above)
from symtab import SymTab                                 # noqa: E402

# =============================================================================
# Estado del módulo
# =============================================================================

symtab       = SymTab()
_errors      = False
_current_fun = None   # nodo FUN_DECL del que estamos analizando el cuerpo


def _error(lineno, msg):
    global _errors
    print(f"Error semántico, línea {lineno}: {msg}")
    _errors = True


# =============================================================================
# Funciones predefinidas: input / output
# =============================================================================

def _insert_predefined():
    symtab.insert('input', {
        'kind': 'fun', 'name': 'input',
        'return_type': TokenType.INT,
        'params': [],
        'lineno': 0,
    })
    symtab.insert('output', {
        'kind': 'fun', 'name': 'output',
        'return_type': TokenType.VOID,
        'params': [(TokenType.INT, False)],
        'lineno': 0,
    })


# =============================================================================
# Utilidades
# =============================================================================

def _collect_params(params_node):
    """Devuelve [(tipo, es_arreglo), ...] a partir de PARAM_LIST o PARAMS_VOID."""
    if params_node is None or params_node.exp == TipoNodo.PARAMS_VOID:
        return []
    result = []
    p = params_node.hijoIzq
    while p is not None:
        result.append((p.tipo, p.esArr))
        p = p.hermano
    return result


def _get_args(args_node):
    """Devuelve lista de nodos argumento a partir de ARG_LIST o ARGS_EMPTY."""
    if args_node is None or args_node.exp == TipoNodo.ARGS_EMPTY:
        return []
    result = []
    a = args_node.hijoIzq
    while a is not None:
        result.append(a)
        a = a.hermano
    return result


def _is_array_ref(node):
    """True si el nodo es un ID_EXP que referencia un arreglo sin subíndice."""
    if node is None or node.exp != TipoNodo.ID_EXP:
        return False
    if node.esArr:          # tiene subíndice → acceso a elemento, no arreglo
        return False
    entry = getattr(node, '_entry', None)
    return entry is not None and entry.get('is_array', False)


# =============================================================================
# PRIMER PASE: construcción de la tabla de símbolos
# =============================================================================

def _insert(t, fun_body=False):
    """Recorrido del AST para insertar declaraciones y verificar referencias."""
    if t is None:
        return

    kind = t.exp

    # ------------------------------------------------------------------
    if kind == TipoNodo.PROGRAMA:
        _insert(t.hijoIzq)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.VAR_DECL:
        if t.tipo == TokenType.VOID:
            _error(t.lineno, f"la variable '{t.nombre}' no puede ser de tipo void")
        else:
            entry = {
                'kind': 'var', 'name': t.nombre,
                'type': t.tipo, 'is_array': t.esArr, 'size': t.tamano,
                'lineno': t.lineno, 'memloc': symtab.next_loc(),
            }
            if not symtab.insert(t.nombre, entry):
                _error(t.lineno, f"'{t.nombre}' ya fue declarado en este ámbito")
        _insert(t.hermano)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.FUN_DECL:
        params = _collect_params(t.hijoIzq)
        entry = {
            'kind': 'fun', 'name': t.nombre,
            'return_type': t.tipo, 'params': params,
            'lineno': t.lineno,
        }
        if not symtab.insert(t.nombre, entry):
            _error(t.lineno, f"la función '{t.nombre}' ya fue declarada")
        symtab.enter_scope()
        _insert(t.hijoIzq)                      # PARAM_LIST / PARAMS_VOID
        _insert(t.hijoDer, fun_body=True)        # COMPOUND_STMT del cuerpo
        symtab.exit_scope()
        _insert(t.hermano)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.PARAM_LIST:
        _insert(t.hijoIzq)      # primer PARAM (cadena de hermanos)

    elif kind == TipoNodo.PARAMS_VOID:
        pass

    elif kind == TipoNodo.PARAM:
        if t.tipo == TokenType.VOID:
            _error(t.lineno, f"el parámetro '{t.nombre}' no puede ser de tipo void")
        else:
            entry = {
                'kind': 'var', 'name': t.nombre,
                'type': t.tipo, 'is_array': t.esArr, 'size': 0,
                'lineno': t.lineno, 'memloc': symtab.next_loc(),
            }
            if not symtab.insert(t.nombre, entry):
                _error(t.lineno, f"parámetro duplicado '{t.nombre}'")
        _insert(t.hermano)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.COMPOUND_STMT:
        if not fun_body:
            symtab.enter_scope()
        _insert(t.hijoIzq)   # LOCAL_DECLS
        _insert(t.hijoDer)   # STMT_LIST
        if not fun_body:
            symtab.exit_scope()
        _insert(t.hermano)

    elif kind == TipoNodo.LOCAL_DECLS:
        _insert(t.hijoIzq)   # primer VAR_DECL (cadena de hermanos)

    elif kind == TipoNodo.STMT_LIST:
        _insert(t.hijoIzq)   # primera sentencia (cadena de hermanos)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.EXPR_STMT:
        _insert(t.hijoIzq)
        _insert(t.hermano)

    elif kind == TipoNodo.SELECTION_STMT:
        _insert(t.hijoIzq)   # condición
        _insert(t.hijoDer)   # rama then
        _insert(t.hijoTer)   # rama else (puede ser None)
        _insert(t.hermano)

    elif kind == TipoNodo.ITERATION_STMT:
        _insert(t.hijoIzq)   # condición
        _insert(t.hijoDer)   # cuerpo
        _insert(t.hermano)

    elif kind == TipoNodo.RETURN_STMT:
        _insert(t.hijoIzq)   # expresión (puede ser None)
        _insert(t.hermano)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.ASSIGN_EXP:
        _insert(t.hijoIzq)   # var
        _insert(t.hijoDer)   # expresión derecha
        _insert(t.hermano)

    elif kind == TipoNodo.OP_EXP:
        _insert(t.hijoIzq)
        _insert(t.hijoDer)
        _insert(t.hermano)

    elif kind == TipoNodo.CONST_EXP:
        _insert(t.hermano)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.ID_EXP:
        entry = symtab.lookup(t.nombre)
        if entry is None:
            _error(t.lineno, f"variable '{t.nombre}' no declarada")
        elif entry['kind'] == 'fun':
            _error(t.lineno, f"'{t.nombre}' es una función, no una variable")
        t._entry = entry   # anotar para el pase de tipos
        if t.esArr:
            _insert(t.hijoIzq)   # expresión subíndice
        _insert(t.hermano)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.CALL_EXP:
        entry = symtab.lookup(t.nombre)
        if entry is None:
            _error(t.lineno, f"función '{t.nombre}' no declarada")
        elif entry['kind'] != 'fun':
            _error(t.lineno, f"'{t.nombre}' es una variable, no una función")
        t._entry = entry
        _insert(t.hijoIzq)   # ARG_LIST / ARGS_EMPTY
        _insert(t.hermano)

    elif kind == TipoNodo.ARG_LIST:
        _insert(t.hijoIzq)   # primer argumento (cadena de hermanos)

    elif kind == TipoNodo.ARGS_EMPTY:
        pass


# =============================================================================
# SEGUNDO PASE: verificación de tipos
# =============================================================================

def _check(t, fun_body=False):
    """Recorrido postorden para inferencia y verificación de tipos."""
    if t is None:
        return

    kind = t.exp

    # ------------------------------------------------------------------
    if kind == TipoNodo.PROGRAMA:
        _check(t.hijoIzq)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.VAR_DECL:
        _check(t.hermano)

    elif kind == TipoNodo.FUN_DECL:
        global _current_fun
        prev         = _current_fun
        _current_fun = t
        _check(t.hijoDer, fun_body=True)   # cuerpo
        _current_fun = prev
        _check(t.hermano)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.COMPOUND_STMT:
        _check(t.hijoIzq)   # LOCAL_DECLS
        _check(t.hijoDer)   # STMT_LIST
        _check(t.hermano)

    elif kind == TipoNodo.LOCAL_DECLS:
        _check(t.hijoIzq)

    elif kind == TipoNodo.STMT_LIST:
        _check(t.hijoIzq)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.EXPR_STMT:
        _check(t.hijoIzq)
        _check(t.hermano)

    elif kind == TipoNodo.SELECTION_STMT:
        _check(t.hijoIzq)
        cond_type = getattr(t.hijoIzq, 'tipo', TokenType.INT)
        if cond_type == TokenType.VOID:
            _error(t.lineno, "la condición del if no puede ser de tipo void")
        _check(t.hijoDer)
        _check(t.hijoTer)
        _check(t.hermano)

    elif kind == TipoNodo.ITERATION_STMT:
        _check(t.hijoIzq)
        cond_type = getattr(t.hijoIzq, 'tipo', TokenType.INT)
        if cond_type == TokenType.VOID:
            _error(t.lineno, "la condición del while no puede ser de tipo void")
        _check(t.hijoDer)
        _check(t.hermano)

    elif kind == TipoNodo.RETURN_STMT:
        _check(t.hijoIzq)
        if _current_fun is not None:
            has_val = t.hijoIzq is not None
            if _current_fun.tipo == TokenType.VOID and has_val:
                _error(t.lineno,
                       f"la función void '{_current_fun.nombre}' no debe retornar un valor")
            elif _current_fun.tipo == TokenType.INT and not has_val:
                _error(t.lineno,
                       f"la función int '{_current_fun.nombre}' debe retornar un valor entero")
            elif has_val:
                ret_type = getattr(t.hijoIzq, 'tipo', TokenType.INT)
                if ret_type == TokenType.VOID:
                    _error(t.lineno,
                           f"la función '{_current_fun.nombre}' retorna una expresión void")
        _check(t.hermano)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.ASSIGN_EXP:
        _check(t.hijoIzq)   # var
        _check(t.hijoDer)   # expresión
        expr_type = getattr(t.hijoDer, 'tipo', TokenType.INT)
        if expr_type == TokenType.VOID:
            _error(t.lineno, "no se puede asignar un valor de tipo void")
        t.tipo = TokenType.INT
        _check(t.hermano)

    elif kind == TipoNodo.OP_EXP:
        _check(t.hijoIzq)
        _check(t.hijoDer)
        lt = getattr(t.hijoIzq, 'tipo', TokenType.INT)
        rt = getattr(t.hijoDer, 'tipo', TokenType.INT)
        if lt != TokenType.INT:
            _error(t.lineno, f"operando izquierdo de '{t.op}' no es entero")
        if rt != TokenType.INT:
            _error(t.lineno, f"operando derecho de '{t.op}' no es entero")
        t.tipo = TokenType.INT   # relops también devuelven entero (0 ó 1)
        _check(t.hermano)

    # ------------------------------------------------------------------
    elif kind == TipoNodo.CONST_EXP:
        t.tipo = TokenType.INT
        _check(t.hermano)

    elif kind == TipoNodo.ID_EXP:
        entry = getattr(t, '_entry', None)
        t.tipo = entry['type'] if entry else TokenType.INT
        if t.esArr:
            _check(t.hijoIzq)
            idx_type = getattr(t.hijoIzq, 'tipo', TokenType.INT)
            if idx_type != TokenType.INT:
                _error(t.lineno, "el índice de arreglo debe ser entero")
        _check(t.hermano)

    elif kind == TipoNodo.CALL_EXP:
        _check(t.hijoIzq)   # argumentos (postorden: tipos ya establecidos)
        entry = getattr(t, '_entry', None)
        if entry is not None:
            t.tipo = entry['return_type']
            args   = _get_args(t.hijoIzq)
            params = entry['params']
            if len(args) != len(params):
                _error(t.lineno,
                       f"'{t.nombre}': se esperaban {len(params)} argumento(s), "
                       f"se encontraron {len(args)}")
            else:
                for i, (arg, (p_type, p_arr)) in enumerate(zip(args, params)):
                    arg_arr = _is_array_ref(arg)
                    if p_arr and not arg_arr:
                        _error(t.lineno,
                               f"'{t.nombre}': argumento {i+1} debe ser un arreglo")
                    elif not p_arr and arg_arr:
                        _error(t.lineno,
                               f"'{t.nombre}': argumento {i+1} no debe ser un arreglo")
                    elif not p_arr:
                        atype = getattr(arg, 'tipo', TokenType.INT)
                        if atype == TokenType.VOID:
                            _error(t.lineno,
                                   f"'{t.nombre}': argumento {i+1} es de tipo void")
        else:
            t.tipo = TokenType.VOID
        _check(t.hermano)

    elif kind == TipoNodo.ARG_LIST:
        _check(t.hijoIzq)

    elif kind == TipoNodo.ARGS_EMPTY:
        pass


# =============================================================================
# Verificación: última declaración global debe ser main
# =============================================================================

def _check_main(tree):
    if tree is None or tree.hijoIzq is None:
        _error(0, "el programa no tiene declaraciones")
        return
    node = tree.hijoIzq
    last = node
    while node is not None:
        last = node
        node = node.hermano
    if last.exp != TipoNodo.FUN_DECL or last.nombre != 'main':
        _error(last.lineno,
               "la última declaración global debe ser la función 'main'")


# =============================================================================
# API pública  (misma interfaz que el SemanticaTiny)
# =============================================================================

def buildSymtab(tree, verbose=True):
    """Primera pasada: construcción de la tabla de símbolos."""
    global _errors
    _errors = False
    symtab.__init__()        # reinicia la tabla en cada llamada
    _insert_predefined()
    _insert(tree)
    _check_main(tree)
    if verbose:
        print()
        print("Tabla de símbolos:")
        symtab.print_table()
    return _errors


def typeCheck(tree):
    """Segunda pasada: verificación de tipos."""
    _check(tree)
    return _errors
