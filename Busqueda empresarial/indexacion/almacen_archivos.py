"""Valida los nombres de los archivos subidos.

A diferencia de buscador2, el archivo ya no se guarda en una carpeta del servidor:
su texto completo vive en la columna documentos.contenido.
"""
import re
from pathlib import Path

CARACTERES_NO_PERMITIDOS = re.compile(r"[^\w. -]")
LONGITUD_MAXIMA_NOMBRE = 255


def nombre_seguro(nombre: str) -> str:
    """Devuelve un nombre de archivo .txt sin rutas ni símbolos, o vacío si no es válido."""
    base = Path(nombre.replace("\\", "/")).name.strip()
    base = CARACTERES_NO_PERMITIDOS.sub("_", base)
    if not base.lower().endswith(".txt") or not base[:-4].strip(" ._"):
        return ""
    if len(base) > LONGITUD_MAXIMA_NOMBRE:
        return ""
    return base
