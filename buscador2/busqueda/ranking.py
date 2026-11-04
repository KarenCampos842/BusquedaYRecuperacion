"""Pesos tf-idf, similitud coseno y orden de los resultados."""
import math
from dataclasses import dataclass, field
from functools import cmp_to_key

TOLERANCIA = 1e-9


@dataclass(frozen=True)
class DetalleTermino:
    """El cálculo tf-idf de un término de la consulta en un documento."""

    termino: str
    tf: int
    df: int
    idf: float
    peso: float


@dataclass(frozen=True)
class Resultado:
    """Un documento encontrado con su fragmento, sus puntajes y sus datos."""

    nombre_archivo: str
    fragmento: str
    relevancia: float
    coseno: float
    palabras: int = 0
    tokens: int = 0
    tamano: int = 0
    fecha: str = ""
    detalle: tuple[DetalleTermino, ...] = ()


@dataclass(frozen=True)
class Busqueda:
    """La respuesta completa a una consulta."""

    resultados: list[Resultado] = field(default_factory=list)
    terminos: tuple[str, ...] = ()
    ignorados: tuple[str, ...] = ()
    total_documentos: int = 0


def idf(total_documentos: int, df: int) -> float:
    """Calcula el idf de un término."""
    if total_documentos <= 0 or df <= 0:
        return 0.0
    return math.log10(total_documentos / df)


def peso(tf: int, idf_termino: float) -> float:
    """Calcula el peso tf-idf de un término."""
    return tf * idf_termino


def producto_punto(a: dict[str, float], b: dict[str, float]) -> float:
    """Calcula el producto punto de dos vectores dispersos."""
    if len(b) < len(a):
        a, b = b, a
    return sum(valor * b[termino] for termino, valor in a.items() if termino in b)


def norma(vector: dict[str, float]) -> float:
    """Calcula la norma euclidiana de un vector."""
    return math.sqrt(sum(valor * valor for valor in vector.values()))


def coseno(a: dict[str, float], b: dict[str, float]) -> float:
    """Calcula el coseno entre dos vectores, o 0 si alguna norma es 0."""
    denominador = norma(a) * norma(b)
    if denominador == 0:
        return 0.0
    return producto_punto(a, b) / denominador


def _comparar(a: Resultado, b: Resultado) -> int:
    """Compara por relevancia, luego coseno y luego nombre."""
    if abs(a.relevancia - b.relevancia) >= TOLERANCIA:
        return -1 if a.relevancia > b.relevancia else 1
    if abs(a.coseno - b.coseno) >= TOLERANCIA:
        return -1 if a.coseno > b.coseno else 1
    return (a.nombre_archivo > b.nombre_archivo) - (a.nombre_archivo < b.nombre_archivo)


def ordenar(resultados: list[Resultado]) -> list[Resultado]:
    """Ordena por relevancia descendente con desempate por coseno y nombre."""
    return sorted(resultados, key=cmp_to_key(_comparar))