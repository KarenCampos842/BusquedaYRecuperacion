"""Lectura y normalización de los recursos lingüísticos (stopwords, protegidas, sinónimos)."""

import re
import unicodedata
from pathlib import Path

from configuracion import RUTA_PROTEGIDAS, RUTA_SINONIMOS, RUTA_STOPWORDS

MARCA_COMENTARIO = "#"
SEPARADOR_SINONIMOS = ","
OPERADOR_REEMPLAZO = "=>"


def leer_lineas_utiles(ruta: Path) -> list[str]:
    """Devuelve las líneas no vacías que no son comentarios, sin espacios extremos."""
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    return [
        linea.strip()
        for linea in lineas
        if linea.strip() and not linea.strip().startswith(MARCA_COMENTARIO)
    ]


def normalizar_termino(termino: str) -> str:
    """Minúsculas y sin acentos, igual que LowerCase + ASCIIFolding de Solr."""
    descompuesto = unicodedata.normalize("NFKD", termino.strip().lower())
    sin_acentos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    return " ".join(sin_acentos.split())


def leer_stopwords(ruta: Path = RUTA_STOPWORDS) -> list[str]:
    """Palabras vacías en su forma original y sin acentos.

    Se incluyen ambas formas porque text_es_stop conserva el token original
    (preserveOriginal=true, como text_es_ri) y text_es_proyecto lo pliega.
    """
    palabras = set()
    for palabra in leer_lineas_utiles(ruta):
        palabras.add(palabra.lower())
        palabras.add(normalizar_termino(palabra))
    return sorted(palabras)


def leer_terminos_protegidos(ruta: Path = RUTA_PROTEGIDAS) -> list[str]:
    return sorted({normalizar_termino(termino) for termino in leer_lineas_utiles(ruta)})


def patron_terminos_protegidos(terminos: list[str]) -> str:
    """Expresión regular exacta para KeywordMarkerFilterFactory (atributo pattern)."""
    if not terminos:
        raise ValueError("La lista de términos protegidos está vacía.")
    alternativas = "|".join(re.escape(termino) for termino in terminos)
    return f"^(?:{alternativas})$"


def leer_grupos_sinonimos(ruta: Path = RUTA_SINONIMOS) -> list[list[str]]:
    """Grupos de equivalentes normalizados, uno por línea."""
    grupos = []
    for numero, linea in enumerate(leer_lineas_utiles(ruta), start=1):
        if OPERADOR_REEMPLAZO in linea:
            raise ValueError(f"Línea {numero}: solo se admiten equivalencias con comas.")
        grupo = [normalizar_termino(t) for t in linea.split(SEPARADOR_SINONIMOS) if t.strip()]
        if len(grupo) < 2:
            raise ValueError(f"Línea {numero}: un grupo necesita al menos dos términos.")
        grupos.append(grupo)
    return grupos
