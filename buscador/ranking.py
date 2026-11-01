"""Ranking con TF-IDF y similitud coseno.

    TF(t, d)     = frecuencia del término t en el documento d      (tabla Posting)
    IDF(t)       = log10(N / df(t))                                (N = documentos, df = Vocabulario.documentos)
    peso(t, d)   = TF(t, d) * IDF(t)
    sim(q, d)    = (q · d) / (||q|| * ||d||)                       (similitud coseno)
"""
import math
from collections import Counter, defaultdict

import config
import texto

_normas = None   # caché: id_documento -> ||d||


def invalidar_cache():
    global _normas
    _normas = None


def idf(n_docs, df):
    if df <= 0 or n_docs <= 0:
        return 0.0
    valor = math.log10(n_docs / df)
    return valor + 1 if config.IDF_SUAVIZADO else valor


def _normas_documentos(con, n_docs):
    """Longitud (norma) del vector TF-IDF de cada documento. Se calcula una vez."""
    global _normas
    if _normas is None:
        acumulado = defaultdict(float)
        filas = con.consultar(
            "SELECT p.id_documento, p.frecuencia, v.documentos "
            "FROM Posting p JOIN Vocabulario v ON v.id_token = p.id_token")
        for id_doc, frecuencia, df in filas:
            peso = frecuencia * idf(n_docs, df)
            acumulado[id_doc] += peso * peso
        _normas = {d: math.sqrt(s) for d, s in acumulado.items()}
    return _normas


def estadisticas(con):
    return {
        "documentos": con.consultar("SELECT COUNT(*) FROM Documento")[0][0],
        "terminos": con.consultar("SELECT COUNT(*) FROM Vocabulario")[0][0],
    }


def buscar(con, consulta):
    n_docs = con.consultar("SELECT COUNT(*) FROM Documento")[0][0]
    tf_consulta = Counter(texto.terminos_de_consulta(consulta))

    salida = {
        "consulta": consulta, "N": n_docs, "terminos": list(tf_consulta),
        "ignorados": [], "total": 0, "resultados": [],
    }
    if not tf_consulta or n_docs == 0:
        return salida

    # 1) Términos de la consulta que existen en el vocabulario.
    marcas = ",".join("?" * len(tf_consulta))
    filas = con.consultar(
        f"SELECT id_token, token, documentos FROM Vocabulario WHERE token IN ({marcas})",
        list(tf_consulta))

    info = {}
    for id_token, token, df in filas:
        valor_idf = idf(n_docs, df)
        info[id_token] = {
            "token": token, "df": df, "idf": valor_idf,
            "peso_q": tf_consulta[token] * valor_idf,
        }
    encontrados = {t["token"] for t in info.values()}
    salida["ignorados"] = [t for t in tf_consulta if t not in encontrados]

    norma_q = math.sqrt(sum(t["peso_q"] ** 2 for t in info.values()))
    if norma_q == 0:
        return salida

    # 2) Solo se leen los postings de esos términos (esa es la ventaja del índice invertido).
    marcas = ",".join("?" * len(info))
    postings = con.consultar(
        f"SELECT id_documento, id_token, frecuencia FROM Posting WHERE id_token IN ({marcas})",
        list(info))

    producto = defaultdict(float)
    detalle = defaultdict(list)
    for id_doc, id_token, frecuencia in postings:
        t = info[id_token]
        peso_d = frecuencia * t["idf"]
        producto[id_doc] += peso_d * t["peso_q"]
        detalle[id_doc].append({
            "token": t["token"], "tf": frecuencia, "df": t["df"],
            "idf": t["idf"], "peso": peso_d,
        })

    # 3) Similitud coseno y orden descendente.
    normas = _normas_documentos(con, n_docs)
    puntajes = []
    for id_doc, punto in producto.items():
        norma_d = normas.get(id_doc, 0.0)
        if punto > 0 and norma_d > 0:
            puntajes.append((min(1.0, punto / (norma_d * norma_q)), id_doc))
    puntajes.sort(key=lambda x: (-x[0], x[1]))

    salida["total"] = len(puntajes)
    mejores = puntajes[:config.RESULTADOS_MAX]
    if not mejores:
        return salida

    # 4) Datos del documento para mostrarlos.
    marcas = ",".join("?" * len(mejores))
    meta = {
        fila[0]: fila for fila in con.consultar(
            "SELECT id_documento, archivo, fecha, palabras, tokens, tamano "
            f"FROM Documento WHERE id_documento IN ({marcas})",
            [d for _, d in mejores])
    }
    for score, id_doc in mejores:
        _, archivo, fecha, palabras, tokens, tamano = meta[id_doc]
        salida["resultados"].append({
            "id": id_doc, "archivo": archivo, "fecha": str(fecha)[:10],
            "palabras": palabras, "tokens": tokens, "tamano": tamano,
            "score": score,
            "detalle": sorted(detalle[id_doc], key=lambda x: -x["peso"]),
        })
    return salida
