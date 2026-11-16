"""Evalúa las aplicaciones originales por HTTP y conserva evidencia verificable.

Ejecutar con un MySQL ya disponible. EVAL_DB_* configura la conexión.
Cada ejecución crea dos bases nuevas y cierra sus servidores HTTP al terminar.
"""
import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from fractions import Fraction
import hashlib
from html.parser import HTMLParser
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.parse import parse_qs, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen

from metricas import evaluar_ranking

RAIZ = Path(__file__).resolve().parent
REPO = RAIZ.parent
SISTEMAS = {
    "buscador2": ("buscador2", "INDEXADOR"),
    "empresarial": ("Busqueda empresarial", "EMPRESARIAL"),
}


def guardar_json(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ResultadosHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nombres = []

    def handle_starttag(self, etiqueta, atributos):
        datos = dict(atributos)
        if etiqueta == "a" and "resultado-titulo" in datos.get("class", "").split():
            self.nombres.append(unquote(datos["href"].removeprefix("/archivos/")))


def worker(sistema, accion):
    carpeta, _ = SISTEMAS[sistema]
    sys.path.insert(0, str(REPO / carpeta))
    from base_datos.inicializador import inicializar_base_datos
    from base_datos.conexion import abrir_conexion
    from config import ajustes
    if accion == "servidor":
        from web.servidor import crear_servidor
        inicializar_base_datos()
        if sistema == "buscador2":
            ajustes.CARPETA_ALMACEN.mkdir(parents=True, exist_ok=True)
        servidor = crear_servidor(ajustes.HOST, ajustes.PUERTO)
        try:
            servidor.serve_forever()
        finally:
            servidor.server_close()
        return
    from busqueda import motor_busqueda
    protocolo = json.loads((RAIZ / "protocolo.json").read_text(encoding="utf-8"))
    conexion = abrir_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            cursor.execute("SELECT nombre_archivo FROM documentos ORDER BY nombre_archivo")
            nombres = [fila[0] for fila in cursor.fetchall()]
            cursor.execute("SHOW CREATE TABLE documentos")
            esquema = cursor.fetchone()[1]
            cursor.execute("SHOW VARIABLES LIKE 'innodb_ft_%'")
            variables = dict(cursor.fetchall())
            stopwords = []
            if sistema == "empresarial":
                cursor.execute("SELECT value FROM stopwords_es ORDER BY value")
                stopwords = [fila[0] for fila in cursor.fetchall()]
    finally:
        conexion.close()
    resultados = {}
    for consulta in protocolo["consultas"]:
        busqueda = (motor_busqueda.buscar(consulta["consulta"]) if sistema == "buscador2"
                    else motor_busqueda.buscar(consulta["consulta"], "natural"))
        if getattr(busqueda, "error", ""):
            raise RuntimeError(busqueda.error)
        resultados[consulta["id"]] = asdict(busqueda)
    salida = {
        "mysql": version, "base": ajustes.DB_NOMBRE, "documentos": nombres,
        "esquema_documentos": esquema, "variables_fulltext": variables,
        "stopwords_mysql": stopwords,
        "stopwords_sha256": hashlib.sha256(ajustes.RUTA_STOPWORDS.read_bytes()).hexdigest(),
        "consultas": resultados,
    }
    sys.stdout.buffer.write(json.dumps(salida, ensure_ascii=False).encode("utf-8"))


def solicitar(url, datos=None, tipo=None):
    peticion = Request(url, data=datos)
    if tipo:
        peticion.add_header("Content-Type", tipo)
    with urlopen(peticion, timeout=60) as respuesta:
        return respuesta.read(), respuesta.url


def multipart(archivos):
    frontera = "----EvaluacionBusquedaColeccion2026"
    partes = []
    for archivo in archivos:
        partes.append((
            f"--{frontera}\r\n"
            f'Content-Disposition: form-data; name="archivos[]"; filename="{archivo.name}"\r\n'
            "Content-Type: text/plain; charset=utf-8\r\n\r\n"
        ).encode("utf-8") + archivo.read_bytes() + b"\r\n")
    partes.append(f"--{frontera}--\r\n".encode("ascii"))
    return b"".join(partes), f"multipart/form-data; boundary={frontera}"


def esperar_servidor(proceso, url):
    limite = time.monotonic() + 45
    while time.monotonic() < limite:
        if proceso.poll() is not None:
            raise RuntimeError("El servidor terminó antes de estar disponible. Revisar su log.")
        try:
            solicitar(url)
            return
        except OSError:
            time.sleep(0.2)
    raise TimeoutError(f"El servidor no respondió en {url}")


def validar_metricas(metricas, relevantes, universo):
    # Comprobación independiente mediante conjuntos y aritmética racional.
    recuperados = {p["nombre"] for p in metricas["puntos"]}
    etiquetas = set(relevantes)
    assert metricas["TP"] == len(recuperados & etiquetas)
    assert metricas["FP"] == len(recuperados - etiquetas)
    assert metricas["FN"] == len(etiquetas - recuperados)
    assert metricas["TN"] == len(set(universo) - (recuperados | etiquetas))
    assert sum(metricas[c] for c in ("TP", "FP", "FN", "TN")) == len(universo)
    assert metricas["TP"] + metricas["FN"] == len(etiquetas)
    posiciones = [p["posicion"] for p in metricas["puntos"] if p["relevante"]]
    ap = sum((Fraction(i, posicion) for i, posicion in enumerate(posiciones, 1)), Fraction()) / len(etiquetas)
    assert abs(float(ap) - metricas["AP"]) < 1e-12
    for clave in ("precision", "recall", "accuracy", "AP"):
        assert 0 <= metricas[clave] <= 1


def ejecutar(puerto_base):
    protocolo_bytes = (RAIZ / "protocolo.json").read_bytes()
    protocolo = json.loads(protocolo_bytes)
    archivos = sorted((RAIZ / "coleccion").glob("*.txt"))
    universo = {d["nombre"] for d in protocolo["documentos"]}
    assert len(universo) == 30 and {a.name for a in archivos} == universo
    for documento in protocolo["documentos"]:
        assert hashlib.sha256((RAIZ / "coleccion" / documento["nombre"]).read_bytes()).hexdigest() == documento["sha256"]
    instante = datetime.now(timezone(timedelta(hours=-6)))
    identificador = instante.strftime("%Y%m%d_%H%M%S_%f")
    evidencia = RAIZ / "resultados" / identificador
    evidencia.mkdir(parents=True)
    salida = {
        "fecha": instante.isoformat(), "ejecucion": identificador,
        "protocolo_sha256": hashlib.sha256(protocolo_bytes).hexdigest(),
        "protocolo": protocolo, "python": sys.version, "sistemas": {},
        "dependencias": {p: importlib.metadata.version(p) for p in
                         ("PyMySQL", "reportlab", "matplotlib", "pypdf", "PyMuPDF")},
        "fuentes_sha256": {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                            for carpeta, _ in SISTEMAS.values()
                            for p in (REPO / carpeta).rglob("*.py")
                            if ".venv" not in p.parts and "__pycache__" not in p.parts},
    }
    try:
        salida["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        salida["git_commit"] = "no disponible"
    for indice, (sistema, (_, prefijo)) in enumerate(SISTEMAS.items()):
        entorno = os.environ.copy()
        for clave, defecto in (("HOST", "127.0.0.1"), ("PUERTO", "3306"),
                               ("USUARIO", "root"), ("CONTRASENA", "")):
            entorno[f"{prefijo}_DB_{clave}"] = os.environ.get(f"EVAL_DB_{clave}", defecto)
        base = f"eval_{sistema}_{identificador}"
        entorno[f"{prefijo}_DB_NOMBRE"] = base
        entorno[f"{prefijo}_HOST"] = "127.0.0.1"
        entorno[f"{prefijo}_PUERTO"] = str(puerto_base + indice)
        entorno[f"{prefijo}_CARPETA_ALMACEN"] = str(REPO / "tmp" / base / "almacen")
        entorno["PYTHONIOENCODING"] = "utf-8"
        url = f"http://127.0.0.1:{puerto_base + indice}"
        print(f"Evaluando {sistema} con base {base}.", flush=True)
        with (evidencia / f"{sistema}.log").open("wb") as log:
            proceso = subprocess.Popen(
                [sys.executable, __file__, "--worker", "servidor", "--sistema", sistema],
                cwd=REPO, env=entorno, stdout=log, stderr=log,
            )
            try:
                esperar_servidor(proceso, url)
                datos, tipo = multipart(archivos)
                inicio, destino = solicitar(url + "/subir", datos, tipo)
                conteo = parse_qs(urlsplit(destino).query)
                assert conteo.get("subidos") == ["30"] and conteo.get("rechazados") == ["0"], conteo
                (evidencia / f"{sistema}_inicio.html").write_bytes(inicio)
                html_rankings = {}
                for consulta in protocolo["consultas"]:
                    parametros = {"q": consulta["consulta"]}
                    if sistema == "empresarial":
                        parametros["modo"] = "natural"
                    html, _ = solicitar(url + "/buscar?" + urlencode(parametros))
                    (evidencia / f"{sistema}_{consulta['id']}.html").write_bytes(html)
                    parser = ResultadosHTML()
                    parser.feed(html.decode("utf-8"))
                    html_rankings[consulta["id"]] = parser.nombres
                for archivo in archivos:
                    descarga, _ = solicitar(url + "/archivos/" + archivo.name)
                    assert descarga == archivo.read_bytes(), archivo.name
                vacio, _ = solicitar(url + "/buscar?" + urlencode({"q": "zzterminoinexistentezz"}))
                parser = ResultadosHTML()
                parser.feed(vacio.decode("utf-8"))
                assert not parser.nombres
                captura = json.loads(subprocess.check_output(
                    [sys.executable, __file__, "--worker", "capturar", "--sistema", sistema],
                    cwd=REPO, env=entorno,
                ))
                assert set(captura["documentos"]) == universo
                # Repetir una carga verifica la sustitución por nombre sin duplicados.
                repetido, tipo = multipart(archivos[:1])
                _, destino = solicitar(url + "/subir", repetido, tipo)
                assert parse_qs(urlsplit(destino).query).get("reemplazados") == ["1"]
                segunda = json.loads(subprocess.check_output(
                    [sys.executable, __file__, "--worker", "capturar", "--sistema", sistema],
                    cwd=REPO, env=entorno,
                ))
                assert segunda["documentos"] == captura["documentos"]
                resumen = {}
                for consulta in protocolo["consultas"]:
                    clave = consulta["id"]
                    resultados = captura["consultas"][clave]["resultados"]
                    nombres = [r["nombre_archivo"] for r in resultados]
                    assert nombres == html_rankings[clave]
                    assert nombres == [r["nombre_archivo"] for r in segunda["consultas"][clave]["resultados"]]
                    assert [r["relevancia"] for r in resultados] == [r["relevancia"] for r in segunda["consultas"][clave]["resultados"]]
                    metricas = evaluar_ranking(nombres, consulta["relevantes"], universo)
                    validar_metricas(metricas, consulta["relevantes"], universo)
                    resumen[clave] = metricas
                captura["metricas"] = resumen
                captura["MAP"] = sum(m["AP"] for m in resumen.values()) / len(resumen)
                captura["curva_media"] = [
                    sum(m["interpolada"][i] for m in resumen.values()) / len(resumen)
                    for i in range(11)
                ]
                captura["comprobaciones"] = {
                    "subida_formulario": 30, "descargas_identicas": 30,
                    "documentos_en_base": 30, "orden_http_igual_motor": True,
                    "consulta_sin_coincidencias": True, "recarga_sin_duplicados": True,
                    "ranking_y_puntajes_estables_tras_recarga": True,
                    "metricas_validadas_con_fracciones": True,
                }
                salida["sistemas"][sistema] = captura
                guardar_json(evidencia / f"{sistema}.json", captura)
                print(f"{sistema}: MAP={captura['MAP']:.6f}", flush=True)
            finally:
                proceso.terminate()
                proceso.wait(timeout=15)
    assert hashlib.sha256((RAIZ / "protocolo.json").read_bytes()).hexdigest() == salida["protocolo_sha256"]
    guardar_json(evidencia / "resultados.json", salida)
    guardar_json(RAIZ / "resultados" / "ultima_ejecucion.json", salida)
    print(f"Evidencia guardada en {evidencia}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puerto-base", type=int, default=8100)
    parser.add_argument("--worker", choices=("servidor", "capturar"))
    parser.add_argument("--sistema", choices=tuple(SISTEMAS))
    argumentos = parser.parse_args()
    if argumentos.worker:
        if not argumentos.sistema:
            parser.error("--worker requiere --sistema")
        worker(argumentos.sistema, argumentos.worker)
    else:
        ejecutar(argumentos.puerto_base)
