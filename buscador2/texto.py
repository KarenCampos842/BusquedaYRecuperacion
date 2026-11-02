"""Preprocesamiento de texto: normalizar, tokenizar, quitar palabras vacías y contar."""
import re
import unicodedata
from collections import Counter
from pathlib import Path

PATRON_PALABRA = re.compile(r"[a-z0-9ñ]+")
LONGITUD_MINIMA = 2
LONGITUD_MAXIMA = 100


def _normalizar_caracter(caracter: str) -> str:
    """Normaliza un solo carácter devolviendo siempre un carácter."""
    minuscula = caracter.lower()[:1]
    if minuscula == "ñ":
        return minuscula
    base = "".join(c for c in unicodedata.normalize("NFD", minuscula) if not unicodedata.combining(c))
    return base[:1] if base else minuscula


def normalizar(texto: str) -> str:
    """Devuelve el texto en minúsculas y sin acentos, con la misma longitud."""
    return "".join(_normalizar_caracter(c) for c in texto)


def tokenizar(texto_normalizado: str) -> list[str]:
    """Devuelve las palabras de un texto ya normalizado."""
    return PATRON_PALABRA.findall(texto_normalizado)


def cargar_stopwords(ruta: Path) -> frozenset[str]:
    """Lee las palabras vacías de un archivo con una por línea."""
    lineas = Path(ruta).read_text(encoding="utf-8").splitlines()
    return frozenset(linea.strip() for linea in lineas if linea.strip())


def filtrar(tokens: list[str], stopwords: frozenset[str]) -> list[str]:
    """Descarta palabras vacías, tokens de un carácter y tokens demasiado largos."""
    return [
        token
        for token in tokens
        if LONGITUD_MINIMA <= len(token) <= LONGITUD_MAXIMA and token not in stopwords
    ]


def obtener_frecuencias(texto: str, stopwords: frozenset[str]) -> dict[str, int]:
    """Devuelve la frecuencia de cada término útil del texto."""
    tokens = filtrar(tokenizar(normalizar(texto)), stopwords)
    return dict(Counter(tokens))


def extraer_fragmento(texto_original: str, texto_normalizado: str, termino: str, longitud: int) -> str:
    """Devuelve hasta longitud caracteres del original desde la primera aparición del término."""
    patron = rf"(?<![a-z0-9ñ]){re.escape(termino)}(?![a-z0-9ñ])"
    coincidencia = re.search(patron, texto_normalizado)
    inicio = coincidencia.start() if coincidencia else 0
    fragmento = texto_original[inicio:inicio + longitud]
    return re.sub(r"[\r\n\t]", " ", fragmento).rstrip()
