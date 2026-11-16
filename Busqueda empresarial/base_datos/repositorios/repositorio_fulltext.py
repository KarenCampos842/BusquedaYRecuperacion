"""Búsqueda con MATCH ... AGAINST y lectura de la configuración FULLTEXT del servidor."""
from dataclasses import dataclass

from pymysql.connections import Connection


@dataclass(frozen=True)
class ConfiguracionFulltext:
    """Variables del servidor que deciden qué palabras entran al índice."""

    version: str
    longitud_minima: int
    longitud_maxima: int
    stopwords_activas: bool


def obtener_configuracion(conexion: Connection) -> ConfiguracionFulltext:
    """Lee la versión del servidor y las variables innodb_ft_*."""
    with conexion.cursor() as cursor:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        cursor.execute("SHOW VARIABLES LIKE 'innodb_ft_%'")
        variables = {nombre: valor for nombre, valor in cursor.fetchall()}
    return ConfiguracionFulltext(
        version=version,
        longitud_minima=int(variables.get("innodb_ft_min_token_size", 3)),
        longitud_maxima=int(variables.get("innodb_ft_max_token_size", 84)),
        stopwords_activas=str(variables.get("innodb_ft_enable_stopword", "ON")).upper() in ("ON", "1"),
    )


def buscar(conexion: Connection, consulta: str, modificador: str) -> tuple[list[tuple], str]:
    """Ejecuta la búsqueda FULLTEXT y devuelve las filas y la sentencia enviada.

    La relevancia y el orden los calcula MySQL. El modificador viene de una lista
    cerrada (busqueda.ranking.MODOS), nunca del usuario, porque no puede ir como
    parámetro. El texto de búsqueda sí va como parámetro (%s).
    """
    sql = (
        "SELECT nombre_archivo, contenido, palabras, tokens, tamano, fecha_indexado, "
        f"MATCH(contenido) AGAINST (%s {modificador}) AS relevancia "
        "FROM documentos "
        f"WHERE MATCH(contenido) AGAINST (%s {modificador}) "
        "ORDER BY relevancia DESC, nombre_archivo"
    )
    parametros = (consulta, consulta)
    with conexion.cursor() as cursor:
        enviada = cursor.mogrify(sql, parametros)
        cursor.execute(sql, parametros)
        return list(cursor.fetchall()), enviada
