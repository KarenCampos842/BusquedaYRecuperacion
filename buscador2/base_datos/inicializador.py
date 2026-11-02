"""Crea la base de datos y las tablas si no existen."""
from config import ajustes
from base_datos.conexion import abrir_conexion, abrir_conexion_servidor


def inicializar_base_datos() -> None:
    """Crea la base configurada y ejecuta el esquema sentencia por sentencia."""
    servidor = abrir_conexion_servidor()
    try:
        with servidor.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{ajustes.DB_NOMBRE}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_bin"
            )
    finally:
        servidor.close()
    sentencias = ajustes.RUTA_ESQUEMA.read_text(encoding="utf-8").split(";")
    conexion = abrir_conexion()
    try:
        with conexion.cursor() as cursor:
            for sentencia in sentencias:
                if sentencia.strip():
                    cursor.execute(sentencia)
        conexion.commit()
    finally:
        conexion.close()
