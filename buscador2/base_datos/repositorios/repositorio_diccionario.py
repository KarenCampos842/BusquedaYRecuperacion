"""Consultas SQL de la tabla diccionario."""
from pymysql.connections import Connection


def sumar_terminos(conexion: Connection, frecuencias: dict[str, int]) -> None:
    """Suma un documento y las frecuencias de cada término al diccionario."""
    if not frecuencias:
        return
    with conexion.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO diccionario (termino, num_documentos, total_frecuencias) "
            "VALUES (%s, 1, %s) "
            "ON DUPLICATE KEY UPDATE "
            "num_documentos = num_documentos + 1, "
            "total_frecuencias = total_frecuencias + VALUES(total_frecuencias)",
            list(frecuencias.items()),
        )


def restar_terminos(conexion: Connection, frecuencias: dict[str, int]) -> None:
    """Resta un documento y las frecuencias de cada término del diccionario."""
    if not frecuencias:
        return
    with conexion.cursor() as cursor:
        cursor.executemany(
            "UPDATE diccionario SET num_documentos = num_documentos - 1, "
            "total_frecuencias = total_frecuencias - %s WHERE termino = %s",
            [(frecuencia, termino) for termino, frecuencia in frecuencias.items()],
        )


def eliminar_sin_documentos(conexion: Connection) -> None:
    """Borra los términos que ya no aparecen en ningún documento."""
    with conexion.cursor() as cursor:
        cursor.execute("DELETE FROM diccionario WHERE num_documentos <= 0")


def obtener_df(conexion: Connection, terminos: list[str]) -> dict[str, int]:
    """Devuelve el número de documentos de cada término existente."""
    if not terminos:
        return {}
    marcadores = ", ".join(["%s"] * len(terminos))
    with conexion.cursor() as cursor:
        cursor.execute(
            f"SELECT termino, num_documentos FROM diccionario WHERE termino IN ({marcadores})",
            terminos,
        )
        return {termino: df for termino, df in cursor.fetchall()}


def contar_terminos(conexion: Connection) -> int:
    """Cuenta los términos del diccionario."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM diccionario")
        return cursor.fetchone()[0]
