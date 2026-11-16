"""Modos de búsqueda FULLTEXT y estructuras de los resultados.

En buscador2 este módulo calculaba idf, pesos tf-idf, coseno y el orden de los
resultados. Aquí esas funciones desaparecen: MATCH(...) AGAINST(...) devuelve la
relevancia y ORDER BY la usa para ordenar, todo dentro de MySQL.
"""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Modo:
    """Un modo de búsqueda de MySQL y cómo se presenta en la página."""

    clave: str
    nombre: str
    modificador: str
    descripcion: str


MODOS: dict[str, Modo] = {
    "natural": Modo(
        "natural",
        "Lenguaje natural",
        "IN NATURAL LANGUAGE MODE",
        "Cada palabra suma relevancia. Las palabras que están en todos los documentos no aportan.",
    ),
    "booleano": Modo(
        "booleano",
        "Booleano",
        "IN BOOLEAN MODE",
        'Operadores: +obligatoria  -excluida  palabra*  "frase exacta"  >más peso  <menos peso  ~resta  ( ).',
    ),
    "expansion": Modo(
        "expansion",
        "Expansión de consulta",
        "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION",
        "Busca dos veces: la segunda agrega palabras de los mejores resultados de la primera.",
    ),
}
MODO_POR_DEFECTO = "natural"


def obtener_modo(clave: str) -> Modo:
    """Devuelve el modo con esa clave o el modo por defecto."""
    return MODOS.get(clave, MODOS[MODO_POR_DEFECTO])


@dataclass(frozen=True)
class Resultado:
    """Un documento encontrado con su fragmento, su relevancia y sus datos."""

    nombre_archivo: str
    fragmento: str
    relevancia: float
    palabras: int = 0
    tokens: int = 0
    tamano: int = 0
    fecha: str = ""


@dataclass(frozen=True)
class Busqueda:
    """La respuesta completa a una consulta."""

    resultados: list[Resultado] = field(default_factory=list)
    modo: Modo = MODOS[MODO_POR_DEFECTO]
    palabras: tuple[str, ...] = ()
    prefijos: tuple[str, ...] = ()
    ignorados: tuple[str, ...] = ()
    total_documentos: int = 0
    sql: str = ""
    segundos: float = 0.0
    error: str = ""
