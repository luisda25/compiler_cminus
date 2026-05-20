import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, 'parser', 'lexer'))
sys.path.insert(0, os.path.dirname(_HERE))

from globalTypes import TokenType  # lexer/ is in sys.path (added above)


class SymTab:
    """Tabla de símbolos con manejo de ámbitos para C-."""

    def __init__(self):
        self._scopes   = [{}]   # pila de ámbitos; [0] = global
        self._registry = []     # (nombre, profundidad, entrada) para impresión
        self._loc      = 0      # contador de ubicaciones de memoria

    # ------------------------------------------------------------------
    # Gestión de ámbitos

    def enter_scope(self):
        self._scopes.append({})

    def exit_scope(self):
        if len(self._scopes) > 1:
            self._scopes.pop()

    def depth(self):
        return len(self._scopes) - 1

    # ------------------------------------------------------------------
    # Inserción y búsqueda

    def insert(self, name, entry):
        """Inserta en el ámbito actual. Devuelve False si ya existe en ese ámbito."""
        scope = self._scopes[-1]
        if name in scope:
            return False
        scope[name] = entry
        self._registry.append((name, self.depth(), entry))
        return True

    def lookup(self, name):
        """Busca de adentro hacia afuera. Devuelve la entrada o None."""
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def lookup_current(self, name):
        """Busca solo en el ámbito actual."""
        return self._scopes[-1].get(name)

    def next_loc(self):
        loc = self._loc
        self._loc += 1
        return loc

    # ------------------------------------------------------------------
    # Impresión

    def print_table(self):
        print(f"{'Nombre':<16} {'Clase':<5} {'Tipo':<10} {'Ámbito':<8} {'Línea'}")
        print('-' * 56)
        for name, depth, entry in self._registry:
            scope_str = 'global' if depth == 0 else f'local{depth}'
            if entry['kind'] == 'var':
                t_str = 'int[]' if entry['is_array'] else 'int'
                print(f"{name:<16} {'var':<5} {t_str:<10} {scope_str:<8} {entry['lineno']}")
            else:
                rt = 'int' if entry['return_type'] == TokenType.INT else 'void'
                params = entry['params']
                p_str = ', '.join(
                    ('int[]' if p_arr else 'int') for _, p_arr in params
                ) if params else 'void'
                sig = f"{rt}({p_str})"
                print(f"{name:<16} {'fun':<5} {sig:<10} {scope_str:<8} {entry['lineno']}")
