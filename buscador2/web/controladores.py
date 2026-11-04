"""Controladores: uno por ruta (GET /, /buscar, /archivos/<nombre>, /estaticos/<ruta> y POST /subir)."""
import mimetypes
from http.server import BaseHTTPRequestHandler
from urllib.parse import SplitResult, parse_qs, unquote, urlencode

from base_datos.conexion import abrir_conexion
from base_datos.repositorios import repositorio_diccionario, repositorio_documentos
from busqueda import motor_busqueda
from config import ajustes
from indexacion import almacen_archivos, indexador_incremental
from web import respuestas, vistas
from web.lector_multipart import leer_archivos

PREFIJO_ARCHIVOS = "/archivos/"
PREFIJO_ESTATICOS = "/estaticos/"
LONGITUD_MAXIMA_CONSULTA = 500
TIPOS_MIME = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}


def _numero(parametros: dict[str, list[str]], clave: str) -> int:
    """Lee un entero no negativo de la cadena de consulta."""
    valor = parametros.get(clave, ["0"])[0]
    return int(valor) if valor.isdigit() else 0


def _armar_mensaje(parametros: dict[str, list[str]]) -> tuple[str, str] | None:
    """Arma el mensaje de resultado de una subida, si lo hay."""
    nuevos = _numero(parametros, "subidos")
    reemplazados = _numero(parametros, "reemplazados")
    rechazados = _numero(parametros, "rechazados")
    if not (nuevos or reemplazados or rechazados):
        return None
    partes = []
    if nuevos:
        partes.append(f"{nuevos} archivo(s) nuevo(s) indexado(s)")
    if reemplazados:
        partes.append(f"{reemplazados} reemplazado(s)")
    if rechazados:
        partes.append(f"{rechazados} rechazado(s)")
    tipo = "success" if nuevos or reemplazados else "danger"
    return tipo, ", ".join(partes) + "."


def atender_inicio(manejador: BaseHTTPRequestHandler, url: SplitResult) -> None:
    """Responde la página de inicio con los totales del índice."""
    conexion = abrir_conexion()
    try:
        total_documentos = repositorio_documentos.contar(conexion)
        total_terminos = repositorio_diccionario.contar_terminos(conexion)
    finally:
        conexion.close()
    mensaje = _armar_mensaje(parse_qs(url.query))
    respuestas.enviar_html(manejador, vistas.construir_inicio(total_documentos, total_terminos, mensaje))


def atender_busqueda(manejador: BaseHTTPRequestHandler, url: SplitResult) -> None:
    """Busca la consulta q y responde la página de resultados."""
    consulta = parse_qs(url.query).get("q", [""])[0].strip()[:LONGITUD_MAXIMA_CONSULTA]
    if not consulta:
        respuestas.redirigir(manejador, "/")
        return
    busqueda = motor_busqueda.buscar(consulta)
    respuestas.enviar_html(manejador, vistas.construir_resultados(consulta, busqueda))


def _indexar_todos(manejador: BaseHTTPRequestHandler, archivos: list[tuple[str, bytes]]) -> dict[str, int]:
    """Indexa cada archivo válido y cuenta nuevos, reemplazados y rechazados."""
    conteo = {"subidos": 0, "reemplazados": 0, "rechazados": 0}
    for nombre, datos in archivos:
        if not almacen_archivos.nombre_seguro(nombre):
            conteo["rechazados"] += 1
            continue
        try:
            reemplazo = indexador_incremental.indexar_archivo(nombre, datos)
        except Exception as error:
            manejador.log_error("No se pudo indexar %r: %r", nombre, error)
            conteo["rechazados"] += 1
            continue
        conteo["reemplazados" if reemplazo else "subidos"] += 1
    return conteo


def atender_subida(manejador: BaseHTTPRequestHandler, url: SplitResult) -> None:
    """Recibe los archivos, los indexa uno por uno y redirige al inicio."""
    longitud = manejador.headers.get("Content-Length", "")
    if not longitud.isdigit():
        respuestas.enviar_error(manejador, 411, "Falta la longitud del contenido.")
        return
    if int(longitud) > ajustes.TAMANO_MAXIMO_SUBIDA:
        respuestas.enviar_error(manejador, 413, "La subida supera el tamaño máximo permitido.")
        return
    cuerpo = manejador.rfile.read(int(longitud))
    conteo = _indexar_todos(manejador, leer_archivos(manejador.headers, cuerpo))
    respuestas.redirigir(manejador, "/?" + urlencode(conteo))


def atender_descarga(manejador: BaseHTTPRequestHandler, url: SplitResult) -> None:
    """Envía como descarga un archivo indexado."""
    nombre = unquote(url.path[len(PREFIJO_ARCHIVOS):])
    if almacen_archivos.nombre_seguro(nombre) != nombre:
        respuestas.enviar_error(manejador, 404, "Archivo no encontrado.")
        return
    conexion = abrir_conexion()
    try:
        indexado = repositorio_documentos.existe_nombre(conexion, nombre)
    finally:
        conexion.close()
    if not indexado or not almacen_archivos.existe(nombre):
        respuestas.enviar_error(manejador, 404, "Archivo no encontrado.")
        return
    respuestas.enviar_descarga(manejador, nombre, almacen_archivos.leer_bytes(nombre))


def atender_estaticos(manejador: BaseHTTPRequestHandler, url: SplitResult) -> None:
    """Envía un archivo estático sin salir de la carpeta de estáticos."""
    base = ajustes.CARPETA_ESTATICOS.resolve()
    ruta = (base / unquote(url.path[len(PREFIJO_ESTATICOS):])).resolve()
    if base not in ruta.parents or not ruta.is_file():
        respuestas.enviar_error(manejador, 404, "Archivo no encontrado.")
        return
    tipo = TIPOS_MIME.get(ruta.suffix.lower()) or mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
    respuestas.enviar_archivo(manejador, ruta, tipo)
