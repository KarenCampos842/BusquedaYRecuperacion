"""Guarda, lee y localiza los archivos subidos en la carpeta del servidor."""
import re
from pathlib import Path

from config import ajustes

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


def ruta_de(nombre: str) -> Path:
    """Devuelve la ruta en disco de un archivo del almacén."""
    return Path(ajustes.CARPETA_ALMACEN) / nombre


def guardar(nombre: str, datos: bytes) -> Path:
    """Escribe los bytes en el almacén y devuelve la ruta."""
    ruta = ruta_de(nombre)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_bytes(datos)
    return ruta


def leer_bytes(nombre: str) -> bytes:
    """Lee los bytes de un archivo del almacén."""
    return ruta_de(nombre).read_bytes()


def existe(nombre: str) -> bool:
    """Indica si el archivo existe en el almacén."""
    return ruta_de(nombre).is_file()
