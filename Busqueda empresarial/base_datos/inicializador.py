"""Crea la base de datos, la tabla de palabras vacías y la tabla con el índice FULLTEXT."""
from pathlib import Path

from pymysql.connections import Connection

from base_datos.conexion import abrir_conexion, abrir_conexion_servidor
from base_datos.repositorios import repositorio_stopwords
from config import ajustes
import texto


def _ejecutar_archivo(conexion: Connection, ruta: Path) -> None:
    """Ejecuta un archivo .sql sentencia por sentencia."""
    sentencias = ruta.read_text(encoding="utf-8").split(";")
    with conexion.cursor() as cursor:
        for sentencia in sentencias:
            if _sin_comentarios(sentencia):
                cursor.execute(sentencia)


def _sin_comentarios(sentencia: str) -> str:
    """Devuelve la sentencia sin las líneas de comentario."""
    lineas = [linea for linea in sentencia.splitlines() if not linea.strip().startswith("--")]
    return "\n".join(lineas).strip()


def usar_stopwords_propias(conexion: Connection) -> None:
    """Indica a InnoDB que use la tabla de palabras vacías en español en esta conexión.

    Debe llamarse antes de crear o reconstruir el índice FULLTEXT: la lista de
    palabras vacías se toma en el momento de construir el índice.
    """
    with conexion.cursor() as cursor:
        cursor.execute(
            "SET SESSION innodb_ft_user_stopword_table = %s",
            (f"{ajustes.DB_NOMBRE}/{ajustes.TABLA_STOPWORDS}",),
        )


def inicializar_base_datos() -> None:
    """Crea la base configurada, carga las palabras vacías y crea las tablas."""
    servidor = abrir_conexion_servidor()
    try:
        with servidor.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{ajustes.DB_NOMBRE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
    finally:
        servidor.close()
    conexion = abrir_conexion()
    try:
        _ejecutar_archivo(conexion, ajustes.RUTA_ESQUEMA_STOPWORDS)
        repositorio_stopwords.reemplazar(conexion, texto.cargar_stopwords(ajustes.RUTA_STOPWORDS))
        conexion.commit()
        usar_stopwords_propias(conexion)
        _ejecutar_archivo(conexion, ajustes.RUTA_ESQUEMA)
        conexion.commit()
    finally:
        conexion.close()
