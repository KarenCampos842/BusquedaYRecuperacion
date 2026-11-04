"""Consultas SQL de la tabla posicion."""
from itertools import islice
from typing import Iterator

from pymysql.connections import Connection

TAMANO_LOTE = 5000


def _filas(
    id_documento: int,
    posiciones: dict[str, list[int]],
    ids_posting: dict[str, int],
    ids_token: dict[str, int],
) -> Iterator[tuple[int, int, int, int]]:
    """Genera una fila por cada aparición de cada término."""
    for termino, lista in posiciones.items():
        for posicion in lista:
            yield ids_posting[termino], ids_token[termino], id_documento, posicion


def insertar_varios(
    conexion: Connection,
    id_documento: int,
    posiciones: dict[str, list[int]],
    ids_posting: dict[str, int],
    ids_token: dict[str, int],
) -> None:
    """Inserta las posiciones de un documento por lotes."""
    filas = _filas(id_documento, posiciones, ids_posting, ids_token)
    with conexion.cursor() as cursor:
        while True:
            lote = list(islice(filas, TAMANO_LOTE))
            if not lote:
                break
            cursor.executemany(
                "INSERT INTO posicion (id_posting, id_token, id_documento, posicion) "
                "VALUES (%s, %s, %s, %s)",
                lote,
            )