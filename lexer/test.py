from globalTypes import *
from lexer import *
from pathlib import Path

sample_path = Path(__file__).resolve().parent / 'sample.c-'
f = open(sample_path, 'r')
programa = f.read()
progLong = len(programa)
programa = programa + '$'
posicion = 0

globales(programa, posicion, progLong)

token, tokenString = getToken(True)
while (token != TokenType.ENDFILE):
    token, tokenString = getToken(True)
