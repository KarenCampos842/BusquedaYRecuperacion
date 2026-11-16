"""Consultas SQL de la tabla documentos."""
from pymysql.connections import Connection


def buscar_id_por_nombre(conexion: Connection, nombre: str) -> int | None:
    """Devuelve el id de un documento por su nombre o None."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT id_documento FROM documentos WHERE nombre_archivo = %s", (nombre,))
        fila = cursor.fetchone()
    return fila[0] if fila else None


def insertar(
    conexion: Connection,
    nombre: str,
    url: str,
    palabras: int,
    tokens: int,
    tamano: int,
    contenido: str,
) -> int:
    """Inserta un documento con su texto completo y devuelve su id.

    MySQL agrega el texto al índice FULLTEXT al confirmar la transacción.
    """
    with conexion.cursor() as cursor:
        cursor.execute(
            "INSERT INTO documentos (nombre_archivo, url, palabras, tokens, tamano, contenido) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (nombre, url, palabras, tokens, tamano, contenido),
        )
        return cursor.lastrowid


def actualizar(
    conexion: Connection,
    id_documento: int,
    url: str,
    palabras: int,
    tokens: int,
    tamano: int,
    contenido: str,
) -> None:
    """Reemplaza el texto y los datos de un documento; MySQL actualiza el índice solo."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE documentos SET fecha_indexado = CURRENT_TIMESTAMP, url = %s, "
            "palabras = %s, tokens = %s, tamano = %s, contenido = %s WHERE id_documento = %s",
            (url, palabras, tokens, tamano, contenido, id_documento),
        )


def contar(conexion: Connection) -> int:
    """Cuenta los documentos indexados."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM documentos")
        return cursor.fetchone()[0]


def sumar_palabras(conexion: Connection) -> int:
    """Suma las palabras de todos los documentos."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT COALESCE(SUM(palabras), 0) FROM documentos")
        return int(cursor.fetchone()[0])


def existe_nombre(conexion: Connection, nombre: str) -> bool:
    """Indica si ya existe un documento con ese nombre."""
    return buscar_id_por_nombre(conexion, nombre) is not None


def obtener_contenido(conexion: Connection, nombre: str) -> str | None:
    """Devuelve el texto guardado de un documento, o None si no existe."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT contenido FROM documentos WHERE nombre_archivo = %s", (nombre,))
        fila = cursor.fetchone()
    return fila[0] if fila else None
