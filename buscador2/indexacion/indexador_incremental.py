"""Agrega un solo documento al índice invertido."""
from functools import lru_cache

from pymysql.connections import Connection

from base_datos.conexion import abrir_conexion
from base_datos.repositorios import (
    repositorio_diccionario,
    repositorio_documentos,
    repositorio_posting,
)
from config import ajustes
from indexacion import almacen_archivos
import texto


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


def _construir_fragmentos(contenido: str, terminos: list[str]) -> dict[str, str]:
    """Obtiene el fragmento de cada término dentro del texto."""
    normalizado = texto.normalizar(contenido)
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
    almacen_archivos.guardar(nombre_limpio, datos)
    contenido = decodificar(datos)
    frecuencias = texto.obtener_frecuencias(contenido, _stopwords())
    fragmentos = _construir_fragmentos(contenido, list(frecuencias))
    conexion = abrir_conexion()
    try:
        id_documento = repositorio_documentos.buscar_id_por_nombre(conexion, nombre_limpio)
        reemplazo = id_documento is not None
        if reemplazo:
            quitar_documento(conexion, id_documento)
            repositorio_documentos.actualizar_fecha(conexion, id_documento)
        else:
            id_documento = repositorio_documentos.insertar(conexion, nombre_limpio)
        repositorio_diccionario.sumar_terminos(conexion, frecuencias)
        repositorio_posting.insertar_varios(conexion, id_documento, nombre_limpio, frecuencias, fragmentos)
        conexion.commit()
        return reemplazo
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()
