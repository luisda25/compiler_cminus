# semantica.py  –  Analizador Semántico para C-
# Luis Daniel Filorio Luna  A01028418
#
# API pública:
#   tabla(tree, imprime=True)    → construye tabla(s) de símbolos
#   semantica(tree, imprime=True)→ tabla + verificación de tipos
#
# NOTA sobre imports:
#   TipoNodo y TokenType se obtienen del módulo parser YA CARGADO en
#   sys.modules en tiempo de ejecución (dentro de tabla/semantica), no en
#   tiempo de importación. Esto evita conflictos circulares con el lexer.

import sys
import os

# Asegurar que el directorio actual y lexer/ estén en sys.path
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in [_HERE, os.path.join(_HERE, 'lexer')]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ─────────────────────────────────────────────────────────────────────────
# TipoNodo y TokenType se inicializan perezosamente (lazy) en _reset(),
# que es la primera función que llaman tabla() y semantica().
# ─────────────────────────────────────────────────────────────────────────
TipoNodo  = None
TokenType = None


def _init_types():
    """Obtiene TipoNodo y TokenType del módulo parser ya cargado."""
    global TipoNodo, TokenType
    for mod_name in ('parser', 'Parser'):
        mod = sys.modules.get(mod_name)
        if mod:
            TipoNodo  = getattr(mod, 'TipoNodo',  TipoNodo)
            TokenType = getattr(mod, 'TokenType', TokenType)
    if TipoNodo is None or TokenType is None:
        raise ImportError(
            "No se encontró TipoNodo/TokenType. "
            "Asegúrate de importar Parser antes de llamar a semantica()."
        )


# ─────────────────────────────────────────────────────────────────────────
# Estado del módulo  (se reinicia en cada llamada a tabla())
# ─────────────────────────────────────────────────────────────────────────
_errores     = False
_current_fun = None   # nodo FUN_DECL activo (para verificar returns)

# Tabla de ámbitos:
#   _all_scopes  – lista de {'name': str, 'entries': dict} en orden de apertura
#   _scope_stack – lista de índices en _all_scopes que están activos
_all_scopes  = []
_scope_stack = []
_loc         = 0      # contador de ubicaciones de memoria


def _reset():
    global _errores, _current_fun, _all_scopes, _scope_stack, _loc
    _init_types()     # garantiza TipoNodo y TokenType
    _errores     = False
    _current_fun = None
    _all_scopes  = []
    _scope_stack = []
    _loc         = 0


# ─────────────────────────────────────────────────────────────────────────
# Obtener línea fuente  (para mensajes de error)
# ─────────────────────────────────────────────────────────────────────────
def _get_line(lineno):
    """Devuelve el texto de la línea indicada del programa fuente."""
    prog = None
    for mod_name in ('parser', 'Parser'):
        mod = sys.modules.get(mod_name)
        if mod:
            prog = getattr(mod, 'programa', None)
            if prog:
                break
    if not prog:
        return ''
    lines = prog.split('\n')
    if 0 < lineno <= len(lines):
        return lines[lineno - 1].rstrip('$').rstrip()
    return ''


# ─────────────────────────────────────────────────────────────────────────
# Reporte de errores
# ─────────────────────────────────────────────────────────────────────────
def _error(msg, lineno, col=0):
    """Imprime un error semántico con la línea fuente y marcador ^."""
    global _errores
    _errores = True
    print(f"Línea {lineno}: Error {msg}:")
    src = _get_line(lineno)
    if src:
        print(src)
        print(' ' * col + '^')


# ─────────────────────────────────────────────────────────────────────────
# Tabla de símbolos con ámbitos
# ─────────────────────────────────────────────────────────────────────────
def _enter_scope(name):
    idx = len(_all_scopes)
    _all_scopes.append({'name': name, 'entries': {}})
    _scope_stack.append(idx)


def _exit_scope():
    if _scope_stack:
        _scope_stack.pop()


def _st_insert(name, entry):
    """Inserta en el ámbito actual. Devuelve False si ya existe."""
    if not _scope_stack:
        return False
    current = _all_scopes[_scope_stack[-1]]['entries']
    if name in current:
        return False
    current[name] = entry
    return True


def _st_lookup(name):
    """Busca de adentro hacia afuera. Devuelve la entrada o None."""
    for idx in reversed(_scope_stack):
        e = _all_scopes[idx]['entries'].get(name)
        if e is not None:
            return e
    return None


def _next_loc():
    global _loc
    loc  = _loc
    _loc += 1
    return loc


# ─────────────────────────────────────────────────────────────────────────
# Funciones predefinidas de C-
# ─────────────────────────────────────────────────────────────────────────
def _insert_predefined():
    _st_insert('input', {
        'kind': 'fun', 'name': 'input',
        'return_type': TokenType.INT, 'params': [], 'lineno': 0,
    })
    _st_insert('output', {
        'kind': 'fun', 'name': 'output',
        'return_type': TokenType.VOID,
        'params': [(TokenType.INT, False)], 'lineno': 0,
    })


# ─────────────────────────────────────────────────────────────────────────
# Funciones auxiliares
# ─────────────────────────────────────────────────────────────────────────
def _collect_params(params_node):
    """Extrae lista de (tipo, es_arreglo) de PARAM_LIST o PARAMS_VOID."""
    if params_node is None or params_node.exp == TipoNodo.PARAMS_VOID:
        return []
    result = []
    p = params_node.hijoIzq
    while p is not None:
        result.append((p.tipo, p.esArr))
        p = p.hermano
    return result


def _get_args(args_node):
    """Devuelve lista de nodos argumento de ARG_LIST / ARGS_EMPTY."""
    if args_node is None or args_node.exp == TipoNodo.ARGS_EMPTY:
        return []
    result = []
    a = args_node.hijoIzq
    while a is not None:
        result.append(a)
        a = a.hermano
    return result


def _is_array_ref(node):
    """True si el nodo pasa un arreglo completo (ID sin subíndice, tipo is_array)."""
    if node is None or node.exp != TipoNodo.ID_EXP:
        return False
    if node.esArr:        # tiene subíndice → devuelve un elemento, no el arreglo
        return False
    entry = getattr(node, '_entry', None)
    return entry is not None and entry.get('is_array', False)


# ─────────────────────────────────────────────────────────────────────────
# Impresión de tablas de símbolos
# ─────────────────────────────────────────────────────────────────────────
def _print_scope(scope):
    """Imprime la tabla de símbolos de un ámbito."""
    print(f"=== Tabla de Símbolos: {scope['name']} ===")
    print(f"{'Nombre':<16} {'Clase':<6} {'Tipo':<16} {'Línea'}")
    print('-' * 48)
    for sym, entry in scope['entries'].items():
        if entry['kind'] == 'var':
            t_str = 'int[]' if entry['is_array'] else 'int'
            print(f"{sym:<16} {'var':<6} {t_str:<16} {entry['lineno']}")
        else:
            rt    = 'int' if entry['return_type'] == TokenType.INT else 'void'
            ps    = entry['params']
            p_str = ', '.join(('int[]' if arr else 'int') for _, arr in ps) if ps else 'void'
            sig   = f"{rt}({p_str})"
            print(f"{sym:<16} {'fun':<6} {sig:<16} {entry['lineno']}")
    print()


def _print_all_tables():
    for scope in _all_scopes:
        if scope['entries']:
            _print_scope(scope)


# ═════════════════════════════════════════════════════════════════════════════
# PRIMER PASE  –  construcción de la tabla de símbolos
# ═════════════════════════════════════════════════════════════════════════════
def _pass1(t, fun_body=False, fun_name='Global'):
    """
    Recorre el AST en preorden para:
      • Insertar declaraciones en la tabla de símbolos (una por ámbito/bloque).
      • Verificar que toda referencia esté declarada y sea del tipo correcto.
      • Anotar ID_EXP y CALL_EXP con ._entry para el segundo pase.
    """
    if t is None:
        return

    kind = t.exp

    # ── Nodos de declaración ──────────────────────────────────────────────
    if kind == TipoNodo.PROGRAMA:
        _pass1(t.hijoIzq, fun_name='Global')

    elif kind == TipoNodo.VAR_DECL:
        if t.tipo == TokenType.VOID:
            _error("de tipo: una variable no puede ser de tipo void", t.lineno)
        else:
            entry = {
                'kind': 'var', 'name': t.nombre,
                'type': t.tipo, 'is_array': t.esArr,
                'size': t.tamano, 'lineno': t.lineno, 'memloc': _next_loc(),
            }
            if not _st_insert(t.nombre, entry):
                _error(f"de declaración: '{t.nombre}' ya fue declarado en este ámbito",
                       t.lineno)
        _pass1(t.hermano, fun_body=fun_body, fun_name=fun_name)

    elif kind == TipoNodo.FUN_DECL:
        params = _collect_params(t.hijoIzq)
        entry  = {
            'kind': 'fun', 'name': t.nombre,
            'return_type': t.tipo, 'params': params, 'lineno': t.lineno,
        }
        if not _st_insert(t.nombre, entry):
            _error(f"de declaración: la función '{t.nombre}' ya fue declarada", t.lineno)
        # Parámetros y cuerpo directo comparten el mismo ámbito
        _enter_scope(f"Función: {t.nombre}")
        _pass1(t.hijoIzq, fun_name=t.nombre)                    # PARAM_LIST / PARAMS_VOID
        _pass1(t.hijoDer, fun_body=True, fun_name=t.nombre)     # COMPOUND_STMT del cuerpo
        _exit_scope()
        _pass1(t.hermano, fun_name=fun_name)

    elif kind == TipoNodo.PARAM_LIST:
        _pass1(t.hijoIzq, fun_name=fun_name)

    elif kind == TipoNodo.PARAMS_VOID:
        pass

    elif kind == TipoNodo.PARAM:
        if t.tipo == TokenType.VOID:
            _error(f"de tipo: el parámetro '{t.nombre}' no puede ser void", t.lineno)
        else:
            entry = {
                'kind': 'var', 'name': t.nombre,
                'type': t.tipo, 'is_array': t.esArr,
                'size': 0, 'lineno': t.lineno, 'memloc': _next_loc(),
            }
            if not _st_insert(t.nombre, entry):
                _error(f"de declaración: parámetro duplicado '{t.nombre}'", t.lineno)
        _pass1(t.hermano, fun_name=fun_name)

    # ── Sentencias ────────────────────────────────────────────────────────
    elif kind == TipoNodo.COMPOUND_STMT:
        if not fun_body:
            _enter_scope(f"Bloque en {fun_name}")   # bloque anidado → ámbito propio
        _pass1(t.hijoIzq, fun_name=fun_name)        # LOCAL_DECLS
        _pass1(t.hijoDer, fun_name=fun_name)        # STMT_LIST
        if not fun_body:
            _exit_scope()
        _pass1(t.hermano, fun_body=fun_body, fun_name=fun_name)

    elif kind == TipoNodo.LOCAL_DECLS:
        _pass1(t.hijoIzq, fun_name=fun_name)

    elif kind == TipoNodo.STMT_LIST:
        _pass1(t.hijoIzq, fun_name=fun_name)

    elif kind == TipoNodo.EXPR_STMT:
        _pass1(t.hijoIzq, fun_name=fun_name)
        _pass1(t.hermano, fun_name=fun_name)

    elif kind == TipoNodo.SELECTION_STMT:
        _pass1(t.hijoIzq, fun_name=fun_name)        # condición
        _pass1(t.hijoDer, fun_name=fun_name)        # rama then
        _pass1(t.hijoTer, fun_name=fun_name)        # rama else (puede ser None)
        _pass1(t.hermano, fun_name=fun_name)

    elif kind == TipoNodo.ITERATION_STMT:
        _pass1(t.hijoIzq, fun_name=fun_name)
        _pass1(t.hijoDer, fun_name=fun_name)
        _pass1(t.hermano, fun_name=fun_name)

    elif kind == TipoNodo.RETURN_STMT:
        _pass1(t.hijoIzq, fun_name=fun_name)
        _pass1(t.hermano, fun_name=fun_name)

    # ── Expresiones ───────────────────────────────────────────────────────
    elif kind == TipoNodo.ASSIGN_EXP:
        _pass1(t.hijoIzq, fun_name=fun_name)
        _pass1(t.hijoDer, fun_name=fun_name)
        _pass1(t.hermano, fun_name=fun_name)

    elif kind == TipoNodo.OP_EXP:
        _pass1(t.hijoIzq, fun_name=fun_name)
        _pass1(t.hijoDer, fun_name=fun_name)
        _pass1(t.hermano, fun_name=fun_name)

    elif kind == TipoNodo.CONST_EXP:
        _pass1(t.hermano, fun_name=fun_name)

    elif kind == TipoNodo.ID_EXP:
        entry = _st_lookup(t.nombre)
        if entry is None:
            _error(f"de declaración: variable '{t.nombre}' no declarada", t.lineno)
        elif entry['kind'] == 'fun':
            _error(f"de declaración: '{t.nombre}' es una función, no una variable",
                   t.lineno)
        t._entry = entry          # anotación para el segundo pase
        if t.esArr:
            _pass1(t.hijoIzq, fun_name=fun_name)   # expresión subíndice
        _pass1(t.hermano, fun_name=fun_name)

    elif kind == TipoNodo.CALL_EXP:
        entry = _st_lookup(t.nombre)
        if entry is None:
            _error(f"de declaración: función '{t.nombre}' no declarada", t.lineno)
        elif entry['kind'] != 'fun':
            _error(f"de declaración: '{t.nombre}' es una variable, no una función",
                   t.lineno)
        t._entry = entry
        _pass1(t.hijoIzq, fun_name=fun_name)        # ARG_LIST / ARGS_EMPTY
        _pass1(t.hermano, fun_name=fun_name)

    elif kind == TipoNodo.ARG_LIST:
        _pass1(t.hijoIzq, fun_name=fun_name)

    elif kind == TipoNodo.ARGS_EMPTY:
        pass


# ─────────────────────────────────────────────────────────────────────────
# Verificar que la última declaración global sea main
# ─────────────────────────────────────────────────────────────────────────
def _check_main(tree):
    if tree is None or tree.hijoIzq is None:
        _error("de programa: el programa no tiene declaraciones", 0)
        return
    node = tree.hijoIzq
    last = node
    while node is not None:
        last  = node
        node  = node.hermano
    if last.exp != TipoNodo.FUN_DECL or last.nombre != 'main':
        _error("de declaración: la última declaración global debe ser la función 'main'",
               last.lineno)


# ═════════════════════════════════════════════════════════════════════════════
# SEGUNDO PASE  –  verificación de tipos
# ═════════════════════════════════════════════════════════════════════════════
def _pass2(t):
    """
    Recorre el AST en postorden (hijos antes que padre) para:
      • Inferir el tipo de cada expresión (TokenType.INT / TokenType.VOID).
      • Verificar compatibilidad de tipos en operaciones, asignaciones,
        llamadas y sentencias return.
    Usa las anotaciones ._entry del primer pase; no accede a la tabla de
    símbolos directamente.
    """
    if t is None:
        return

    kind = t.exp

    # ── Declaraciones ─────────────────────────────────────────────────────
    if kind == TipoNodo.PROGRAMA:
        _pass2(t.hijoIzq)

    elif kind == TipoNodo.VAR_DECL:
        _pass2(t.hermano)

    elif kind == TipoNodo.FUN_DECL:
        global _current_fun
        prev         = _current_fun
        _current_fun = t               # para verificar sentencias return
        _pass2(t.hijoDer)              # cuerpo compuesto
        _current_fun = prev
        _pass2(t.hermano)

    # ── Sentencias ────────────────────────────────────────────────────────
    elif kind == TipoNodo.COMPOUND_STMT:
        _pass2(t.hijoIzq)
        _pass2(t.hijoDer)
        _pass2(t.hermano)

    elif kind == TipoNodo.LOCAL_DECLS:
        _pass2(t.hijoIzq)

    elif kind == TipoNodo.STMT_LIST:
        _pass2(t.hijoIzq)

    elif kind == TipoNodo.EXPR_STMT:
        _pass2(t.hijoIzq)
        _pass2(t.hermano)

    elif kind == TipoNodo.SELECTION_STMT:
        _pass2(t.hijoIzq)                                  # condición (postorden)
        if getattr(t.hijoIzq, 'tipo', None) == TokenType.VOID:
            _error("en el tipo de la expresión: condición del if es void", t.lineno)
        _pass2(t.hijoDer)
        _pass2(t.hijoTer)
        _pass2(t.hermano)

    elif kind == TipoNodo.ITERATION_STMT:
        _pass2(t.hijoIzq)
        if getattr(t.hijoIzq, 'tipo', None) == TokenType.VOID:
            _error("en el tipo de la expresión: condición del while es void", t.lineno)
        _pass2(t.hijoDer)
        _pass2(t.hermano)

    elif kind == TipoNodo.RETURN_STMT:
        _pass2(t.hijoIzq)
        if _current_fun is not None:
            has_val  = t.hijoIzq is not None
            fun_name = _current_fun.nombre
            fun_tipo = _current_fun.tipo
            if fun_tipo == TokenType.VOID and has_val:
                _error(f"de tipo: función void '{fun_name}' no debe retornar un valor",
                       t.lineno)
            elif fun_tipo == TokenType.INT and not has_val:
                _error(f"de tipo: función int '{fun_name}' debe retornar un valor",
                       t.lineno)
            elif has_val:
                if getattr(t.hijoIzq, 'tipo', None) == TokenType.VOID:
                    _error(f"en el tipo de la expresión: '{fun_name}' retorna void",
                           t.lineno)
        _pass2(t.hermano)

    # ── Expresiones ───────────────────────────────────────────────────────
    elif kind == TipoNodo.ASSIGN_EXP:
        _pass2(t.hijoIzq)
        _pass2(t.hijoDer)
        if getattr(t.hijoDer, 'tipo', None) == TokenType.VOID:
            _error("de tipo: no se puede asignar un valor void", t.lineno)
        t.tipo = TokenType.INT         # la asignación produce el valor asignado
        _pass2(t.hermano)

    elif kind == TipoNodo.OP_EXP:
        _pass2(t.hijoIzq)
        _pass2(t.hijoDer)
        lt = getattr(t.hijoIzq, 'tipo', TokenType.INT)
        rt = getattr(t.hijoDer, 'tipo', TokenType.INT)
        if lt != TokenType.INT:
            _error(f"en el tipo de la expresión: operando izquierdo de '{t.op}' no es entero",
                   t.lineno)
        if rt != TokenType.INT:
            _error(f"en el tipo de la expresión: operando derecho de '{t.op}' no es entero",
                   t.lineno)
        t.tipo = TokenType.INT         # operadores aritméticos y relacionales → entero
        _pass2(t.hermano)

    elif kind == TipoNodo.CONST_EXP:
        t.tipo = TokenType.INT
        _pass2(t.hermano)

    elif kind == TipoNodo.ID_EXP:
        entry  = getattr(t, '_entry', None)
        t.tipo = entry['type'] if entry else TokenType.INT
        if t.esArr:
            _pass2(t.hijoIzq)
            if getattr(t.hijoIzq, 'tipo', None) != TokenType.INT:
                _error("en el tipo de la expresión: índice de arreglo debe ser entero",
                       t.lineno)
        _pass2(t.hermano)

    elif kind == TipoNodo.CALL_EXP:
        _pass2(t.hijoIzq)              # argumentos primero (postorden)
        entry = getattr(t, '_entry', None)
        if entry is not None:
            t.tipo = entry['return_type']
            args   = _get_args(t.hijoIzq)
            params = entry['params']
            if len(args) != len(params):
                _error(f"en el tipo de la expresión: '{t.nombre}' espera "
                       f"{len(params)} argumento(s), se encontraron {len(args)}",
                       t.lineno)
            else:
                for i, (arg, (p_type, p_arr)) in enumerate(zip(args, params)):
                    arg_arr = _is_array_ref(arg)
                    if p_arr and not arg_arr:
                        _error(f"en el tipo de la expresión: '{t.nombre}' "
                               f"argumento {i+1} debe ser un arreglo", t.lineno)
                    elif not p_arr and arg_arr:
                        _error(f"en el tipo de la expresión: '{t.nombre}' "
                               f"argumento {i+1} no debe ser un arreglo", t.lineno)
                    elif not p_arr:
                        if getattr(arg, 'tipo', TokenType.INT) == TokenType.VOID:
                            _error(f"en el tipo de la expresión: '{t.nombre}' "
                                   f"argumento {i+1} es de tipo void", t.lineno)
        else:
            t.tipo = TokenType.VOID    # función desconocida (error ya reportado)
        _pass2(t.hermano)

    elif kind == TipoNodo.ARG_LIST:
        _pass2(t.hijoIzq)

    elif kind == TipoNodo.ARGS_EMPTY:
        pass


# ═════════════════════════════════════════════════════════════════════════════
# API PÚBLICA
# ═════════════════════════════════════════════════════════════════════════════

def tabla(tree, imprime=True):
    """
    Construye la(s) tabla(s) de símbolos del programa (una por ámbito/bloque).

    Parámetros:
        tree    – raíz del AST generado por parser()
        imprime – si True, imprime las tablas en pantalla

    Retorna:
        Lista de ámbitos [{name, entries}] para uso de semantica()
    """
    _reset()

    _enter_scope('Global')
    _insert_predefined()
    _pass1(tree)
    _exit_scope()

    _check_main(tree)

    if imprime:
        print()
        _print_all_tables()

    return list(_all_scopes)


def semantica(tree, imprime=True):
    """
    Análisis semántico completo de C-:
      1. Llama a tabla() para construir (e imprimir si imprime=True) la(s)
         tabla(s) de símbolos.
      2. Recorre el AST verificando tipos con reglas de inferencia.

    Parámetros:
        tree    – raíz del AST generado por parser()
        imprime – se pasa a tabla()
    """
    tabla(tree, imprime)

    print("Verificando tipos...")
    _pass2(tree)

    if _errores:
        print("\nAnálisis semántico finalizado con errores.")
    else:
        print("\nAnálisis semántico finalizado sin errores.")
