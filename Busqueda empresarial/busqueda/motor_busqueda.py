"""Orquesta una búsqueda FULLTEXT sobre la tabla documentos.

La relevancia y el ranking los calcula MySQL con MATCH(...) AGAINST(...).
Python solo prepara los avisos, recorta el fragmento y mide el tiempo.
"""
import time
from functools import lru_cache

import pymysql

from base_datos.conexion import abrir_conexion
from base_datos.repositorios import repositorio_documentos, repositorio_fulltext
from base_datos.repositorios.repositorio_fulltext import ConfiguracionFulltext
from busqueda.ranking import Busqueda, Resultado, obtener_modo
from config import ajustes
import texto


@lru_cache(maxsize=1)
def _stopwords() -> frozenset[str]:
    """Carga una sola vez las palabras vacías."""
    return texto.cargar_stopwords(ajustes.RUTA_STOPWORDS)


def _ignoradas(palabras: tuple[str, ...], configuracion: ConfiguracionFulltext) -> dict[str, str]:
    """Devuelve las palabras de la consulta que MySQL no busca y el motivo."""
    ignoradas: dict[str, str] = {}
    for palabra in palabras:
        if len(palabra) < configuracion.longitud_minima:
            ignoradas[palabra] = f"menos de {configuracion.longitud_minima} caracteres"
        elif len(palabra) > configuracion.longitud_maxima:
            ignoradas[palabra] = f"más de {configuracion.longitud_maxima} caracteres"
        elif configuracion.stopwords_activas and palabra in _stopwords():
            ignoradas[palabra] = "palabra vacía"
    return ignoradas


def _fragmento(contenido: str, palabras: frozenset[str], prefijos: tuple[str, ...]) -> str:
    """Recorta el texto alrededor de la primera palabra que coincide con la consulta.

    MySQL no tiene una función para extraer fragmentos, así que se hace en Python.
    """
    inicio = texto.primera_aparicion(texto.normalizar(contenido), palabras, prefijos)
    return texto.extraer_fragmento(
        contenido, inicio, ajustes.LONGITUD_FRAGMENTO, ajustes.CONTEXTO_FRAGMENTO
    )


def buscar(consulta: str, clave_modo: str) -> Busqueda:
    """Busca la consulta en el modo indicado y devuelve los resultados ordenados por MySQL."""
    modo = obtener_modo(clave_modo)
    palabras, prefijos = texto.analizar_consulta(consulta, modo.clave == "booleano")
    conexion = abrir_conexion()
    try:
        total_documentos = repositorio_documentos.contar(conexion)
        configuracion = repositorio_fulltext.obtener_configuracion(conexion)
        ignoradas = _ignoradas(palabras, configuracion)
        avisos = tuple(f"{palabra} ({motivo})" for palabra, motivo in ignoradas.items())
        buscadas = tuple(palabra for palabra in palabras if palabra not in ignoradas)
        inicio = time.perf_counter()
        try:
            filas, sql = repositorio_fulltext.buscar(conexion, consulta, modo.modificador)
        except pymysql.MySQLError as error:
            mensaje = error.args[1] if len(error.args) > 1 else str(error)
            return Busqueda(
                modo=modo,
                palabras=buscadas,
                prefijos=prefijos,
                ignorados=avisos,
                total_documentos=total_documentos,
                error=f"MySQL no pudo interpretar la consulta: {mensaje}",
            )
        segundos = time.perf_counter() - inicio
    finally:
        conexion.close()
    conjunto = frozenset(buscadas)
    resultados = [
        Resultado(
            nombre_archivo=nombre,
            fragmento=_fragmento(contenido, conjunto, prefijos),
            relevancia=float(relevancia),
            palabras=palabras_doc,
            tokens=tokens,
            tamano=tamano,
            fecha=str(fecha)[:16],
        )
        for nombre, contenido, palabras_doc, tokens, tamano, fecha, relevancia in filas
    ]
    return Busqueda(
        resultados=resultados,
        modo=modo,
        palabras=buscadas,
        prefijos=prefijos,
        ignorados=avisos,
        total_documentos=total_documentos,
        sql=sql,
        segundos=segundos,
    )
