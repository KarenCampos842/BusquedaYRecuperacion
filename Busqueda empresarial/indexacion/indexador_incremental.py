"""Guarda el texto completo de un documento; MySQL lo agrega al índice FULLTEXT.

Comparado con buscador2, aquí no se construye el índice invertido a mano: no hay
diccionario, posting ni posiciones. Solo se calculan datos descriptivos (palabras,
tokens indexables, tamaño) para mostrarlos en los resultados.
"""
from functools import lru_cache
from urllib.parse import quote

from base_datos.conexion import abrir_conexion
from base_datos.repositorios import repositorio_documentos, repositorio_fulltext
from config import ajustes
from indexacion import almacen_archivos
import texto

PREFIJO_URL = "/archivos/"


@lru_cache(maxsize=1)
def _stopwords() -> frozenset[str]:
    """Carga una sola vez las palabras vacías."""
    return texto.cargar_stopwords(ajustes.RUTA_STOPWORDS)


def decodificar(datos: bytes) -> str:
    """Decodifica como utf-8 y, si falla, como cp1252."""
    try:
        return datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        return datos.decode("cp1252", errors="replace")


def indexar_archivo(nombre: str, datos: bytes) -> bool:
    """Guarda el texto de un archivo en la base y devuelve True si reemplazó uno existente."""
    nombre_limpio = almacen_archivos.nombre_seguro(nombre)
    if not nombre_limpio:
        raise ValueError(f"Nombre de archivo no válido: {nombre!r}")
    contenido = decodificar(datos)
    tokens = texto.tokenizar(texto.normalizar(contenido))
    url = PREFIJO_URL + quote(nombre_limpio)
    tamano = len(datos)
    conexion = abrir_conexion()
    try:
        configuracion = repositorio_fulltext.obtener_configuracion(conexion)
        indexables = texto.contar_indexables(
            tokens,
            _stopwords() if configuracion.stopwords_activas else frozenset(),
            configuracion.longitud_minima,
            configuracion.longitud_maxima,
        )
        id_documento = repositorio_documentos.buscar_id_por_nombre(conexion, nombre_limpio)
        reemplazo = id_documento is not None
        if reemplazo:
            repositorio_documentos.actualizar(
                conexion, id_documento, url, len(tokens), indexables, tamano, contenido
            )
        else:
            repositorio_documentos.insertar(
                conexion, nombre_limpio, url, len(tokens), indexables, tamano, contenido
            )
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()
    return reemplazo
