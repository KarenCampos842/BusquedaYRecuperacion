"""Agrega un solo documento al índice invertido."""
from functools import lru_cache
from urllib.parse import quote

from pymysql.connections import Connection

from base_datos.conexion import abrir_conexion
from base_datos.repositorios import (
    repositorio_diccionario,
    repositorio_documentos,
    repositorio_posicion,
    repositorio_posting,
)
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


def _construir_fragmentos(contenido: str, normalizado: str, terminos: list[str]) -> dict[str, str]:
    """Obtiene el fragmento de cada término dentro del texto."""
    return {
        termino: texto.extraer_fragmento(contenido, normalizado, termino, ajustes.LONGITUD_FRAGMENTO)
        for termino in terminos
    }


def quitar_documento(conexion: Connection, id_documento: int) -> None:
    """Resta el aporte de un documento al diccionario y borra su posting."""
    frecuencias = repositorio_posting.obtener_por_documento(conexion, id_documento)
    repositorio_diccionario.restar_terminos(conexion, frecuencias)
    repositorio_posting.eliminar_por_documento(conexion, id_documento)
    repositorio_diccionario.eliminar_sin_documentos(conexion)


def indexar_archivo(nombre: str, datos: bytes) -> bool:
    """Indexa un archivo y devuelve True si reemplazó uno existente."""
    nombre_limpio = almacen_archivos.nombre_seguro(nombre)
    if not nombre_limpio:
        raise ValueError(f"Nombre de archivo no válido: {nombre!r}")
    contenido = decodificar(datos)
    normalizado = texto.normalizar(contenido)
    tokens = texto.tokenizar(normalizado)
    posiciones = texto.obtener_posiciones(tokens, _stopwords())
    frecuencias = {termino: len(lista) for termino, lista in posiciones.items()}
    fragmentos = _construir_fragmentos(contenido, normalizado, list(frecuencias))
    url = PREFIJO_URL + quote(nombre_limpio)
    palabras = len(tokens)
    total_tokens = sum(frecuencias.values())
    tamano = len(datos)
    conexion = abrir_conexion()
    try:
        id_documento = repositorio_documentos.buscar_id_por_nombre(conexion, nombre_limpio)
        reemplazo = id_documento is not None
        if reemplazo:
            quitar_documento(conexion, id_documento)
            repositorio_documentos.actualizar_datos(
                conexion, id_documento, url, palabras, total_tokens, tamano
            )
        else:
            id_documento = repositorio_documentos.insertar(
                conexion, nombre_limpio, url, palabras, total_tokens, tamano
            )
        repositorio_diccionario.sumar_terminos(conexion, frecuencias)
        ids_token = repositorio_diccionario.obtener_ids(conexion, list(frecuencias))
        repositorio_posting.insertar_varios(
            conexion, id_documento, nombre_limpio, frecuencias, fragmentos, ids_token
        )
        ids_posting = repositorio_posting.obtener_ids_por_documento(conexion, id_documento)
        repositorio_posicion.insertar_varios(conexion, id_documento, posiciones, ids_posting, ids_token)
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()
    almacen_archivos.guardar(nombre_limpio, datos)
    return reemplazo