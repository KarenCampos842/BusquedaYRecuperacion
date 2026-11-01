"""Acceso a la base de datos y esquema.

Tablas (según el diagrama de la clase):

    Vocabulario(id_token, token, documentos)
    Posting(id_posting, id_token, id_documento, frecuencia)
    Posicion(id_posicion, id_posting, id_token, id_documento, posicion)
    Documento(id_documento, archivo, fecha, url, palabras, tokens, tamano)

Relaciones: Vocabulario 1─* Posting, Documento 1─* Posting, Posting 1─* Posicion.
"""
import config


class Conexion:
    """Envoltura mínima para que el resto del código no dependa del motor."""

    def __init__(self):
        if config.MOTOR == "mysql":
            try:
                import mysql.connector
            except ImportError:
                raise SystemExit(
                    "Falta el conector de MySQL. Instálalo con:\n"
                    "    pip install mysql-connector-python\n"
                    "o cambia MOTOR a \"sqlite\" en config.py."
                )
            self._con = mysql.connector.connect(**config.MYSQL, charset="utf8mb4")
            self._ph = "%s"
        else:
            import sqlite3
            self._con = sqlite3.connect(config.SQLITE_ARCHIVO)
            self._con.execute("PRAGMA foreign_keys = ON")
            self._ph = "?"
        self._cur = self._con.cursor()

    # Escribimos las consultas con "?" y aquí las adaptamos al motor.
    def _sql(self, sql):
        return sql.replace("?", self._ph)

    def ejecutar(self, sql, params=()):
        self._cur.execute(self._sql(sql), params)

    def muchos(self, sql, filas):
        self._cur.executemany(self._sql(sql), filas)

    def consultar(self, sql, params=()):
        self._cur.execute(self._sql(sql), params)
        return self._cur.fetchall()

    def confirmar(self):
        self._con.commit()

    def cerrar(self):
        try:
            self._cur.close()
        finally:
            self._con.close()

    def __enter__(self):
        return self

    def __exit__(self, tipo, valor, traza):
        self.cerrar()


def crear_base_si_falta():
    """En MySQL crea la base de datos vacía si todavía no existe."""
    if config.MOTOR != "mysql":
        return
    import mysql.connector
    cfg = dict(config.MYSQL)
    nombre = cfg.pop("database")
    con = mysql.connector.connect(**cfg)
    cur = con.cursor()
    cur.execute(
        f"CREATE DATABASE IF NOT EXISTS `{nombre}` "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    con.close()


def recrear_esquema(con):
    """Borra y vuelve a crear las cuatro tablas."""
    mysql = config.MOTOR == "mysql"
    pk = "INT AUTO_INCREMENT PRIMARY KEY" if mysql else "INTEGER PRIMARY KEY"
    # En MySQL el token se compara en binario: así "año" y "ano" son términos distintos.
    binario = "CHARACTER SET utf8mb4 COLLATE utf8mb4_bin" if mysql else ""
    cierre = " ENGINE=InnoDB DEFAULT CHARSET=utf8mb4" if mysql else ""

    for tabla in ("Posicion", "Posting", "Vocabulario", "Documento"):
        con.ejecutar(f"DROP TABLE IF EXISTS {tabla}")

    con.ejecutar(f"""
        CREATE TABLE Documento (
            id_documento {pk},
            archivo      VARCHAR(255) NOT NULL,
            fecha        DATETIME,
            url          VARCHAR(500),
            palabras     INT NOT NULL DEFAULT 0,
            tokens       INT NOT NULL DEFAULT 0,
            tamano       INT NOT NULL DEFAULT 0
        ){cierre}""")

    con.ejecutar(f"""
        CREATE TABLE Vocabulario (
            id_token   {pk},
            token      VARCHAR(100) {binario} NOT NULL UNIQUE,
            documentos INT NOT NULL DEFAULT 0
        ){cierre}""")

    con.ejecutar(f"""
        CREATE TABLE Posting (
            id_posting   {pk},
            id_token     INT NOT NULL,
            id_documento INT NOT NULL,
            frecuencia   INT NOT NULL,
            FOREIGN KEY (id_token)     REFERENCES Vocabulario (id_token),
            FOREIGN KEY (id_documento) REFERENCES Documento (id_documento)
        ){cierre}""")

    con.ejecutar(f"""
        CREATE TABLE Posicion (
            id_posicion  {pk},
            id_posting   INT NOT NULL,
            id_token     INT NOT NULL,
            id_documento INT NOT NULL,
            posicion     INT NOT NULL,
            FOREIGN KEY (id_posting)   REFERENCES Posting (id_posting),
            FOREIGN KEY (id_token)     REFERENCES Vocabulario (id_token),
            FOREIGN KEY (id_documento) REFERENCES Documento (id_documento)
        ){cierre}""")

    con.ejecutar("CREATE INDEX ix_posting_token ON Posting (id_token)")
    con.ejecutar("CREATE INDEX ix_posting_documento ON Posting (id_documento)")
    con.ejecutar("CREATE INDEX ix_posicion_posting ON Posicion (id_posting)")
    con.confirmar()


def esquema_existe(con):
    try:
        con.consultar("SELECT COUNT(*) FROM Documento")
        return True
    except Exception:
        return False
