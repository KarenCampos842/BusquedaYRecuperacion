"""Consultas SQL de la tabla posting."""
from pymysql.connections import Connection


def insertar_varios(
    conexion: Connection,
    id_documento: int,
    nombre_archivo: str,
    frecuencias: dict[str, int],
    fragmentos: dict[str, str],
) -> None:
    """Inserta los renglones de posting de un documento."""
    if not frecuencias:
        return
    filas = [
        (termino, id_documento, frecuencia, nombre_archivo, fragmentos[termino])
        for termino, frecuencia in frecuencias.items()
    ]
    with conexion.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO posting (termino, id_documento, frecuencia, nombre_archivo, fragmento) "
            "VALUES (%s, %s, %s, %s, %s)",
            filas,
        )


def obtener_por_terminos(conexion: Connection, terminos: list[str]) -> list[tuple[str, int, int, str, str]]:
    """Devuelve los postings de los términos dados."""
    if not terminos:
        return []
    marcadores = ", ".join(["%s"] * len(terminos))
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT termino, id_documento, frecuencia, nombre_archivo, fragmento "
            f"FROM posting WHERE termino IN ({marcadores})",
            terminos,
        )
        return list(cursor.fetchall())


def obtener_por_documento(conexion: Connection, id_documento: int) -> dict[str, int]:
    """Devuelve las frecuencias por término de un documento."""
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT termino, frecuencia FROM posting WHERE id_documento = %s",
            (id_documento,),
        )
        return {termino: frecuencia for termino, frecuencia in cursor.fetchall()}


def obtener_pesos_de_documentos(
    conexion: Connection, ids_documentos: list[int]
) -> list[tuple[int, str, int, int]]:
    """Devuelve id, término, tf y df de todos los términos de los documentos."""
    if not ids_documentos:
        return []
    marcadores = ", ".join(["%s"] * len(ids_documentos))
    with conexion.cursor() as cursor:
        cursor.execute(
            "SELECT p.id_documento, p.termino, p.frecuencia, d.num_documentos "
            "FROM posting p JOIN diccionario d ON d.termino = p.termino "
            f"WHERE p.id_documento IN ({marcadores})",
            ids_documentos,
        )
        return list(cursor.fetchall())


def eliminar_por_documento(conexion: Connection, id_documento: int) -> None:
    """Borra los renglones de posting de un documento."""
    with conexion.cursor() as cursor:
        cursor.execute("DELETE FROM posting WHERE id_documento = %s", (id_documento,))
