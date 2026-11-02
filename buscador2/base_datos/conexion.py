"""Abre conexiones a MySQL."""
import pymysql
from pymysql.connections import Connection

from config import ajustes


def abrir_conexion(nombre_base: str | None = None) -> Connection:
    """Abre una conexión a la base indicada o a la configurada."""
    return pymysql.connect(
        host=ajustes.DB_HOST,
        port=ajustes.DB_PUERTO,
        user=ajustes.DB_USUARIO,
        password=ajustes.DB_CONTRASENA,
        database=nombre_base or ajustes.DB_NOMBRE,
        charset="utf8mb4",
        autocommit=False,
    )


def abrir_conexion_servidor() -> Connection:
    """Abre una conexión al servidor sin elegir base de datos."""
    return pymysql.connect(
        host=ajustes.DB_HOST,
        port=ajustes.DB_PUERTO,
        user=ajustes.DB_USUARIO,
        password=ajustes.DB_CONTRASENA,
        charset="utf8mb4",
        autocommit=True,
    )
