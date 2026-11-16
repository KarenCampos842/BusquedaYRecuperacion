"""Configuración de la aplicación leída de variables de entorno.

Usa el prefijo EMPRESARIAL_ y valores por defecto distintos a los de buscador2
(base de datos y puerto) para que ambos buscadores puedan correr a la vez.
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _entero(nombre: str, defecto: int) -> int:
    """Lee un entero de una variable de entorno con prefijo EMPRESARIAL_."""
    return int(os.environ.get(f"EMPRESARIAL_{nombre}", defecto))


def _texto(nombre: str, defecto: str) -> str:
    """Lee un texto de una variable de entorno con prefijo EMPRESARIAL_."""
    return os.environ.get(f"EMPRESARIAL_{nombre}", defecto)


HOST = _texto("HOST", "localhost")
PUERTO = _entero("PUERTO", 8001)
DB_HOST = _texto("DB_HOST", "localhost")
DB_PUERTO = _entero("DB_PUERTO", 3306)
DB_USUARIO = _texto("DB_USUARIO", "root")
DB_CONTRASENA = _texto("DB_CONTRASENA", "")
DB_NOMBRE = _texto("DB_NOMBRE", "busqueda_empresarial")
CARPETA_PLANTILLAS = RAIZ / "plantillas"
CARPETA_ESTATICOS = RAIZ / "estaticos"
RUTA_ESQUEMA = RAIZ / "base_datos" / "esquema.sql"
RUTA_ESQUEMA_STOPWORDS = RAIZ / "base_datos" / "esquema_stopwords.sql"
RUTA_STOPWORDS = RAIZ / "recursos" / "stopwords_es.txt"
TABLA_STOPWORDS = "stopwords_es"
TAMANO_MAXIMO_SUBIDA = _entero("TAMANO_MAXIMO_SUBIDA", 5 * 1024 * 1024)
LONGITUD_FRAGMENTO = 180
CONTEXTO_FRAGMENTO = 40
