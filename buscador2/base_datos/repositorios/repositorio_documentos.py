"""Consultas SQL de la tabla documentos."""
from pymysql.connections import Connection


def buscar_id_por_nombre(conexion: Connection, nombre: str) -> int | None:
    """Devuelve el id de un documento por su nombre o None."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT id_documento FROM documentos WHERE nombre_archivo = %s", (nombre,))
        fila = cursor.fetchone()
    return fila[0] if fila else None


def insertar(
    conexion: Connection, nombre: str, url: str, palabras: int, tokens: int, tamano: int
) -> int:
    """Inserta un documento con sus datos y devuelve su id."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "INSERT INTO documentos (nombre_archivo, url, palabras, tokens, tamano) "
            "VALUES (%s, %s, %s, %s, %s)",
            (nombre, url, palabras, tokens, tamano),
        )
        return cursor.lastrowid


def actualizar_datos(
    conexion: Connection, id_documento: int, url: str, palabras: int, tokens: int, tamano: int
) -> None:
    """Actualiza la fecha de indexado y los datos de un documento reemplazado."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE documentos SET fecha_indexado = CURRENT_TIMESTAMP, url = %s, "
            "palabras = %s, tokens = %s, tamano = %s WHERE id_documento = %s",
            (url, palabras, tokens, tamano, id_documento),
        )


def contar(conexion: Connection) -> int:
    """Cuenta los documentos indexados."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM documentos")
        return cursor.fetchone()[0]


def listar_nombres(conexion: Connection) -> list[str]:
    """Lista los nombres de los documentos indexados."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT nombre_archivo FROM documentos ORDER BY nombre_archivo")
        return [fila[0] for fila in cursor.fetchall()]


def existe_nombre(conexion: Connection, nombre: str) -> bool:
    """Indica si ya existe un documento con ese nombre."""
    return buscar_id_por_nombre(conexion, nombre) is not None

def obtener_metadatos(conexion: Connection, ids_documentos: list[int]) -> dict[int, tuple]:
    """Devuelve (palabras, tokens, tamano, fecha_indexado) de cada documento."""
    if not ids_documentos:
        return {}
    marcadores = ", ".join(["%s"] * len(ids_documentos))
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT id_documento, palabras, tokens, tamano, fecha_indexado "
            f"FROM documentos WHERE id_documento IN ({marcadores})",
            ids_documentos,
        )
        return {fila[0]: fila[1:] for fila in cursor.fetchall()}
    