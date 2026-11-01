"""Preprocesamiento: tokenización → normalización → eliminación de stopwords."""
import re
import unicodedata

# Una "palabra" es una secuencia de letras o dígitos.
PATRON = re.compile(r"[^\W_]+", re.UNICODE)

_STOPWORDS_TEXTO = """
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun aunque cada casi como con contra
cual cuales cuando cuyo de del desde donde dos e el ella ellas ello ellos en entre era eran es esa esas
ese eso esos esta estaba estaban estan estar estas este esto estos fue fueron ha habia han hasta hay
la las le les lo los mas me mediante mi mis mucho muchos muy ni no nos nosotros nuestra nuestro o os otra
otras otro otros para pero poco por porque pueden puede que quien quienes se sea sean segun ser si sido
sin sobre solo son su sus tambien tan tanto te tiene tienen todo todos tras tu tus un una unas uno unos
usa usan vez y ya yo
"""


def normalizar(palabra):
    """Minúsculas y sin acentos. La ñ se conserva (año ≠ ano)."""
    p = palabra.lower().replace("ñ", "\x00")
    p = "".join(c for c in unicodedata.normalize("NFD", p) if unicodedata.category(c) != "Mn")
    return p.replace("\x00", "ñ")


STOPWORDS = {normalizar(w) for w in _STOPWORDS_TEXTO.split()}


def analizar(texto):
    """Devuelve (total_de_palabras, [(posicion, token), ...]).

    - La posición es el lugar de la palabra en el documento (empieza en 1) y
      cuenta también las stopwords, así se puede reconstruir el orden original.
    - Solo se devuelven los tokens que quedan después de quitar stopwords.
    """
    palabras = 0
    tokens = []
    for m in PATRON.finditer(texto):
        palabras += 1
        t = normalizar(m.group())
        if len(t) < 2 or len(t) > 60 or t in STOPWORDS:
            continue
        tokens.append((palabras, t))
    return palabras, tokens


def terminos_de_consulta(consulta):
    """Aplica a la consulta exactamente el mismo proceso que a los documentos."""
    return [t for _, t in analizar(consulta)[1]]
