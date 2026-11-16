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


def es_util(token: str, stopwords: frozenset[str]) -> bool:
    """Indica si un token se indexa: longitud válida y no es palabra vacía."""
    return LONGITUD_MINIMA <= len(token) <= LONGITUD_MAXIMA and token not in stopwords


def filtrar(tokens: list[str], stopwords: frozenset[str]) -> list[str]:
    """Descarta palabras vacías, tokens de un carácter y tokens demasiado largos."""
    return [token for token in tokens if es_util(token, stopwords)]


def obtener_frecuencias(texto: str, stopwords: frozenset[str]) -> dict[str, int]:
    """Devuelve la frecuencia de cada término útil del texto."""
    tokens = filtrar(tokenizar(normalizar(texto)), stopwords)
    return dict(Counter(tokens))


def obtener_posiciones(tokens: list[str], stopwords: frozenset[str]) -> dict[str, list[int]]:
    """Devuelve las posiciones de cada término útil.

    La posición es el lugar del token en el texto (empezando en 1), contando
    también las palabras vacías, de modo que corresponde a la palabra real.
    """
    posiciones: dict[str, list[int]] = {}
    for numero, token in enumerate(tokens, start=1):
        if es_util(token, stopwords):
            posiciones.setdefault(token, []).append(numero)
    return posiciones


def contar_indexables(tokens: list[str], stopwords: frozenset[str], minimo: int, maximo: int) -> int:
    """Cuenta los tokens que MySQL indexaría con la longitud y palabras vacías dadas.

    Es una aproximación: el parser de MySQL corta las palabras con sus propias reglas.
    """
    return sum(1 for token in tokens if minimo <= len(token) <= maximo and token not in stopwords)


PATRON_PREFIJO = re.compile(r"([a-z0-9ñ]+)\*")
PATRON_EXCLUIDA = re.compile(r"(?<![a-z0-9ñ])-([a-z0-9ñ]+)")


def analizar_consulta(consulta: str, booleano: bool) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Devuelve las palabras y los prefijos (palabra*) de una consulta para resaltarlos.

    En modo booleano se omiten las palabras excluidas con '-'.
    """
    normalizada = normalizar(consulta)
    prefijos = tuple(dict.fromkeys(PATRON_PREFIJO.findall(normalizada))) if booleano else ()
    excluidas = set(PATRON_EXCLUIDA.findall(normalizada)) if booleano else set()
    palabras = tuple(
        token for token in dict.fromkeys(tokenizar(normalizada))
        if token not in excluidas and token not in prefijos
    )
    return palabras, prefijos


def coincide(token: str, palabras: frozenset[str], prefijos: tuple[str, ...]) -> bool:
    """Indica si un token normalizado es una palabra buscada o empieza con un prefijo buscado."""
    return token in palabras or any(token.startswith(prefijo) for prefijo in prefijos)


def primera_aparicion(texto_normalizado: str, palabras: frozenset[str], prefijos: tuple[str, ...]) -> int | None:
    """Devuelve la posición de la primera palabra del texto que coincide con la consulta."""
    for coincidencia in PATRON_PALABRA.finditer(texto_normalizado):
        if coincide(coincidencia.group(), palabras, prefijos):
            return coincidencia.start()
    return None


def extraer_fragmento(texto_original: str, inicio: int | None, longitud: int, contexto: int) -> str:
    """Devuelve un fragmento del original alrededor de la posición dada, cortado en palabras completas."""
    if inicio is None:
        inicio = 0
    desde = max(0, inicio - contexto)
    if desde > 0:
        espacio = texto_original.find(" ", desde, inicio)
        desde = espacio + 1 if espacio != -1 else desde
    hasta = min(len(texto_original), desde + longitud)
    if hasta < len(texto_original):
        espacio = texto_original.rfind(" ", inicio, hasta)
        hasta = espacio if espacio > inicio else hasta
    fragmento = " ".join(texto_original[desde:hasta].split())
    prefijo = "… " if desde > 0 else ""
    sufijo = " …" if hasta < len(texto_original) else ""
    return prefijo + fragmento + sufijo