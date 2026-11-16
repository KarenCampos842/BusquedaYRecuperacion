"""Consultas SQL de la tabla de palabras vacías que usa el índice FULLTEXT."""
from pymysql.connections import Connection

from config import ajustes


def reemplazar(conexion: Connection, palabras: frozenset[str]) -> None:
    """Vacía la tabla y la llena con las palabras dadas."""
    tabla = ajustes.TABLA_STOPWORDS
    with conexion.cursor() as cursor:
        cursor.execute(f"DELETE FROM `{tabla}`")
        if palabras:
            cursor.executemany(
                f"INSERT INTO `{tabla}` (value) VALUES (%s)",
                [(palabra,) for palabra in sorted(palabras)],
            )


def contar(conexion: Connection) -> int:
    """Cuenta las palabras vacías cargadas."""
    with conexion.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) FROM `{ajustes.TABLA_STOPWORDS}`")
        return cursor.fetchone()[0]
