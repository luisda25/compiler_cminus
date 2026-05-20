import sys, os
_HERE = os.path.dirname(os.path.abspath(__file__))
for _p in [_HERE,
           os.path.join(_HERE, 'parser'),
           os.path.join(_HERE, 'parser', 'lexer'),
           os.path.dirname(_HERE)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

import parser as _pmod                               # noqa: E402
from analyze import buildSymtab, typeCheck           # noqa: E402

# ---------------------------------------------------------------------------

fileName = sys.argv[1] if len(sys.argv) >= 2 else input('Archivo C-: ').strip()

with open(fileName, 'r') as f:
    programa = f.read()

progLong = len(programa)
programa = programa + '$'

_pmod.globales(programa, 0, progLong)

print("=== Análisis Sintáctico ===")
ast = _pmod.parser(imprime=False)

if _pmod.hayError:
    print("Se encontraron errores sintácticos; se omite el análisis semántico.")
    sys.exit(1)

print("Sintaxis correcta.")
print()
print("=== Análisis Semántico ===")
print()
print("Construyendo tabla de símbolos...")
errores = buildSymtab(ast, verbose=True)

print()
print("Verificando tipos...")
typeCheck(ast)

print()
if errores:
    print("Análisis semántico finalizado con errores.")
else:
    print("Análisis semántico finalizado sin errores.")
