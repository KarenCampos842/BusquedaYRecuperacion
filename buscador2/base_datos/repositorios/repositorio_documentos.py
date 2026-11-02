"""Consultas SQL de la tabla documentos."""
from pymysql.connections import Connection


def buscar_id_por_nombre(conexion: Connection, nombre: str) -> int | None:
    """Devuelve el id de un documento por su nombre o None."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT id_documento FROM documentos WHERE nombre_archivo = %s", (nombre,))
        fila = cursor.fetchone()
    return fila[0] if fila else None


def insertar(conexion: Connection, nombre: str) -> int:
    """Inserta un documento y devuelve su id."""
    with conexion.cursor() as cursor:
        cursor.execute("INSERT INTO documentos (nombre_archivo) VALUES (%s)", (nombre,))
        return cursor.lastrowid


def actualizar_fecha(conexion: Connection, id_documento: int) -> None:
    """Actualiza la fecha de indexado de un documento."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "UPDATE documentos SET fecha_indexado = CURRENT_TIMESTAMP WHERE id_documento = %s",
            (id_documento,),
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
