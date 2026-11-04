"""Orquesta una búsqueda sobre el índice."""
from functools import lru_cache

from base_datos.conexion import abrir_conexion
from base_datos.repositorios import (
    repositorio_diccionario,
    repositorio_documentos,
    repositorio_posting,
)
from busqueda import ranking
from busqueda.ranking import Busqueda, DetalleTermino, Resultado
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


def _detalles_por_documento(
    postings: list[tuple[str, int, int, str, str]],
    dfs: dict[str, int],
    total_documentos: int,
) -> dict[int, tuple[DetalleTermino, ...]]:
    """Arma el cálculo tf-idf de los términos de la consulta en cada documento."""
    detalles: dict[int, list[DetalleTermino]] = {}
    for termino, id_documento, frecuencia, _, _ in postings:
        df = dfs[termino]
        valor_idf = ranking.idf(total_documentos, df)
        detalles.setdefault(id_documento, []).append(
            DetalleTermino(termino, frecuencia, df, valor_idf, ranking.peso(frecuencia, valor_idf))
        )
    return {
        id_documento: tuple(sorted(lista, key=lambda d: (-d.peso, d.termino)))
        for id_documento, lista in detalles.items()
    }


def buscar(consulta: str) -> Busqueda:
    """Busca la consulta y devuelve los resultados ordenados y los avisos."""
    frecuencias_consulta = texto.obtener_frecuencias(consulta, _stopwords())
    terminos = tuple(frecuencias_consulta)
    if not terminos:
        return Busqueda()
    conexion = abrir_conexion()
    try:
        total_documentos = repositorio_documentos.contar(conexion)
        if total_documentos == 0:
            return Busqueda(terminos=terminos, ignorados=terminos)
        dfs = repositorio_diccionario.obtener_df(conexion, list(terminos))
        ignorados = tuple(termino for termino in terminos if termino not in dfs)
        if not dfs:
            return Busqueda(terminos=terminos, ignorados=ignorados, total_documentos=total_documentos)
        postings = repositorio_posting.obtener_por_terminos(conexion, list(dfs))
        candidatos = sorted({fila[1] for fila in postings})
        filas = repositorio_posting.obtener_pesos_de_documentos(conexion, candidatos)
        metadatos = repositorio_documentos.obtener_metadatos(conexion, candidatos)
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
    detalles = _detalles_por_documento(postings, dfs, total_documentos)
    resultados = []
    for id_documento in candidatos:
        palabras, total_tokens, tamano, fecha = metadatos[id_documento]
        resultados.append(
            Resultado(
                nombre_archivo=fragmentos[id_documento][0],
                fragmento=fragmentos[id_documento][1],
                relevancia=sum(vectores[id_documento].get(termino, 0.0) for termino in dfs),
                coseno=ranking.coseno(vector_consulta, vectores[id_documento]),
                palabras=palabras,
                tokens=total_tokens,
                tamano=tamano,
                fecha=str(fecha)[:16],
                detalle=detalles[id_documento],
            )
        )
    return Busqueda(
        resultados=ranking.ordenar(resultados),
        terminos=terminos,
        ignorados=ignorados,
        total_documentos=total_documentos,
    )