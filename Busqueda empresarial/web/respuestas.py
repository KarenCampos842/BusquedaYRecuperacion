"""Escribe respuestas HTTP."""
import html
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import quote


def _enviar(manejador: BaseHTTPRequestHandler, estado: int, tipo: str, cuerpo: bytes, extras: dict[str, str] | None = None) -> None:
    """Envía una respuesta con encabezados y cuerpo."""
    manejador.send_response(estado)
    manejador.send_header("Content-Type", tipo)
    manejador.send_header("Content-Length", str(len(cuerpo)))
    for nombre, valor in (extras or {}).items():
        manejador.send_header(nombre, valor)
    manejador.end_headers()
    if manejador.command != "HEAD":
        manejador.wfile.write(cuerpo)


def enviar_html(manejador: BaseHTTPRequestHandler, contenido: str, estado: int = 200) -> None:
    """Envía una página HTML."""
    _enviar(manejador, estado, "text/html; charset=utf-8", contenido.encode("utf-8"))


def enviar_archivo(manejador: BaseHTTPRequestHandler, ruta: Path, tipo_mime: str) -> None:
    """Envía un archivo estático con su tipo MIME."""
    _enviar(manejador, 200, tipo_mime, ruta.read_bytes())


def enviar_descarga(manejador: BaseHTTPRequestHandler, nombre: str, datos: bytes) -> None:
    """Envía un archivo como descarga."""
    respaldo = nombre.encode("ascii", "replace").decode("ascii").replace("?", "_").replace('"', "_")
    disposicion = f"attachment; filename=\"{respaldo}\"; filename*=UTF-8''{quote(nombre)}"
    _enviar(manejador, 200, "text/plain; charset=utf-8", datos, {"Content-Disposition": disposicion})


def redirigir(manejador: BaseHTTPRequestHandler, destino: str) -> None:
    """Redirige con 303 See Other."""
    _enviar(manejador, 303, "text/plain; charset=utf-8", b"", {"Location": destino})


def enviar_error(manejador: BaseHTTPRequestHandler, estado: int, mensaje: str) -> None:
    """Envía una página de error simple."""
    pagina = (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        f"<title>Error {estado}</title></head><body>"
        f"<h1>Error {estado}</h1><p>{html.escape(mensaje)}</p>"
        '<p><a href="/">Volver al inicio</a></p></body></html>'
    )
    _enviar(manejador, estado, "text/html; charset=utf-8", pagina.encode("utf-8"), {"Connection": "close"})
