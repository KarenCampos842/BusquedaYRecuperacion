"""Configuración del buscador. Edita aquí lo que necesites."""
from pathlib import Path

BASE = Path(__file__).resolve().parent

# ── Base de datos ────────────────────────────────────────────────────────────
# "mysql"  -> usa el MySQL/MariaDB de XAMPP (requiere: pip install mysql-connector-python)
# "sqlite" -> usa solo la biblioteca estándar de Python (sin instalar nada)
MOTOR = "mysql"

# Valores por defecto de XAMPP: usuario root, sin contraseña.
MYSQL = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "",
    "database": "buscador_ri",   # se crea sola si no existe
}

SQLITE_ARCHIVO = BASE / "buscador.db"

# ── Corpus ───────────────────────────────────────────────────────────────────
CARPETA_DOCUMENTOS = BASE / "documentos"   # aquí van los archivos .txt

# ── Ranking ──────────────────────────────────────────────────────────────────
RESULTADOS_MAX = 20        # cuántos documentos se muestran
# False: IDF(t) = log10(N / df)        (fórmula vista en clase)
# True : IDF(t) = log10(N / df) + 1    (evita peso 0 si un término está en todos los documentos)
IDF_SUAVIZADO = False

# ── Servidor web local ───────────────────────────────────────────────────────
PUERTO = 8000
