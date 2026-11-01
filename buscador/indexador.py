"""Indización: de los archivos .txt al índice invertido en la base de datos."""
import time
from collections import defaultdict
from datetime import datetime

import config
import db
import texto

LOTE = 5000  # filas por inserción


def leer_archivo(ruta):
    """Lee un .txt probando UTF-8 y, si falla, la codificación de Windows."""
    datos = ruta.read_bytes()
    for codificacion in ("utf-8-sig", "cp1252"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return datos.decode("latin-1")


def _insertar_por_lotes(con, sql, filas):
    for i in range(0, len(filas), LOTE):
        con.muchos(sql, filas[i:i + LOTE])


def indexar(con):
    """Reconstruye todo el índice. Devuelve un resumen con las cifras."""
    inicio = time.perf_counter()
    db.recrear_esquema(con)

    carpeta = config.CARPETA_DOCUMENTOS
    carpeta.mkdir(exist_ok=True)
    archivos = sorted(carpeta.rglob("*.txt"))

    vocabulario = {}   # token -> [id_token, documentos]
    documentos, postings, posiciones = [], [], []
    id_posting = 0
    id_posicion = 0

    for id_doc, ruta in enumerate(archivos, start=1):
        contenido = leer_archivo(ruta)
        palabras, tokens = texto.analizar(contenido)

        # Agrupar las posiciones de cada token dentro de este documento.
        por_token = defaultdict(list)
        for pos, token in tokens:
            por_token[token].append(pos)

        info = ruta.stat()
        documentos.append((
            id_doc,
            ruta.relative_to(carpeta).as_posix(),
            datetime.fromtimestamp(info.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            ruta.resolve().as_uri(),
            palabras,
            len(tokens),
            info.st_size,
        ))

        for token, lista in por_token.items():
            if token not in vocabulario:
                vocabulario[token] = [len(vocabulario) + 1, 0]
            vocabulario[token][1] += 1            # un documento más contiene este término
            id_token = vocabulario[token][0]

            id_posting += 1
            postings.append((id_posting, id_token, id_doc, len(lista)))
            for pos in lista:
                id_posicion += 1
                posiciones.append((id_posicion, id_posting, id_token, id_doc, pos))

    # El orden respeta las llaves foráneas.
    _insertar_por_lotes(con,
        "INSERT INTO Documento (id_documento, archivo, fecha, url, palabras, tokens, tamano) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", documentos)
    _insertar_por_lotes(con,
        "INSERT INTO Vocabulario (id_token, token, documentos) VALUES (?, ?, ?)",
        [(i, t, df) for t, (i, df) in vocabulario.items()])
    _insertar_por_lotes(con,
        "INSERT INTO Posting (id_posting, id_token, id_documento, frecuencia) VALUES (?, ?, ?, ?)",
        postings)
    _insertar_por_lotes(con,
        "INSERT INTO Posicion (id_posicion, id_posting, id_token, id_documento, posicion) "
        "VALUES (?, ?, ?, ?, ?)", posiciones)
    con.confirmar()

    return {
        "documentos": len(documentos),
        "terminos": len(vocabulario),
        "postings": len(postings),
        "posiciones": len(posiciones),
        "segundos": time.perf_counter() - inicio,
    }
