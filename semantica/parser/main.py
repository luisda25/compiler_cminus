from pathlib import Path
from parser import *

f = open(Path(__file__).resolve().parent / 'lexer' / 'sample.c-', 'r')
programa = f.read() # lee todo el archivo a compilar
progLong = len(programa) # longitud original del programa
programa = programa + '$' # agregar un caracter $ que represente EOF
posicion = 0 # posición del caracter actual del string

# función para pasar los valores iniciales de las variables globales
globales(programa, posicion, progLong)
AST = parser(True)