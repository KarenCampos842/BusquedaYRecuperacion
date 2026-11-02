"""Orquesta una búsqueda sobre el índice."""
from functools import lru_cache

from base_datos.conexion import abrir_conexion
from base_datos.repositorios import (
    repositorio_diccionario,
    repositorio_documentos,
    repositorio_posting,
)
from busqueda import ranking
from busqueda.ranking import Resultado
from config import ajustes
import texto


@lru_cache(maxsize=1)
def _stopwords() -> frozenset[str]:
    """Carga una sola vez las palabras vacías."""
    return texto.cargar_stopwords(ajustes.RUTA_STOPWORDS)


def _vectores_de_documentos(
    filas: list[tuple[int, str, int, int]], total_documentos: int
) -> dict[int, dict[str, float]]:
    """Construye el vector de pesos tf-idf de cada documento."""
    vectores: dict[int, dict[str, float]] = {}
    for id_documento, termino, frecuencia, df in filas:
        peso = ranking.peso(frecuencia, ranking.idf(total_documentos, df))
        vectores.setdefault(id_documento, {})[termino] = peso
    return vectores


def _mejores_fragmentos(
    postings: list[tuple[str, int, int, str, str]],
    vectores: dict[int, dict[str, float]],
) -> dict[int, tuple[str, str]]:
    """Elige por documento el nombre y el fragmento del término de mayor peso."""
    mejores: dict[int, tuple[float, str, str, str]] = {}
    for termino, id_documento, _, nombre, fragmento in sorted(postings):
        peso = vectores[id_documento][termino]
        actual = mejores.get(id_documento)
        if actual is None or peso > actual[0] + 1e-12:
            mejores[id_documento] = (peso, termino, nombre, fragmento)
    return {id_doc: (datos[2], datos[3]) for id_doc, datos in mejores.items()}


def buscar(consulta: str) -> list[Resultado]:
    """Busca la consulta y devuelve los resultados ordenados."""
    frecuencias_consulta = texto.obtener_frecuencias(consulta, _stopwords())
    if not frecuencias_consulta:
        return []
    conexion = abrir_conexion()
    try:
        total_documentos = repositorio_documentos.contar(conexion)
        if total_documentos == 0:
            return []
        dfs = repositorio_diccionario.obtener_df(conexion, list(frecuencias_consulta))
        if not dfs:
            return []
        postings = repositorio_posting.obtener_por_terminos(conexion, list(dfs))
        candidatos = sorted({fila[1] for fila in postings})
        filas = repositorio_posting.obtener_pesos_de_documentos(conexion, candidatos)
    finally:
        conexion.close()
    vectores = _vectores_de_documentos(filas, total_documentos)
    vector_consulta = {
        termino: ranking.peso(
            frecuencias_consulta[termino], ranking.idf(total_documentos, df)
        )
        for termino, df in dfs.items()
    }
    fragmentos = _mejores_fragmentos(postings, vectores)
    resultados = [
        Resultado(
            nombre_archivo=fragmentos[id_documento][0],
            fragmento=fragmentos[id_documento][1],
            relevancia=sum(vectores[id_documento].get(termino, 0.0) for termino in dfs),
            coseno=ranking.coseno(vector_consulta, vectores[id_documento]),
        )
        for id_documento in candidatos
    ]
    return ranking.ordenar(resultados)
