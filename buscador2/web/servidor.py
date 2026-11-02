"""Servidor HTTP: recibe las peticiones y las delega en su controlador."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Callable
from urllib.parse import SplitResult, urlsplit

from web import controladores, respuestas

Controlador = Callable[[BaseHTTPRequestHandler, SplitResult], None]


def resolver(metodo: str, ruta: str) -> Controlador | None:
    """Devuelve el controlador de un método y ruta, o None si no existe."""
    if metodo == "GET":
        if ruta == "/":
            return controladores.atender_inicio
        if ruta == "/buscar":
            return controladores.atender_busqueda
        if ruta.startswith(controladores.PREFIJO_ARCHIVOS):
            return controladores.atender_descarga
        if ruta.startswith(controladores.PREFIJO_ESTATICOS):
            return controladores.atender_estaticos
    if metodo == "POST" and ruta == "/subir":
        return controladores.atender_subida
    return None


class ManejadorHttp(BaseHTTPRequestHandler):
    """Manejador que delega cada petición en su controlador."""

    def _atender(self, metodo: str) -> None:
        """Busca el controlador de la petición y lo ejecuta."""
        url = urlsplit(self.path)
        controlador = resolver(metodo, url.path)
        if controlador is None:
            respuestas.enviar_error(self, 404, "Página no encontrada.")
            return
        try:
            controlador(self, url)
        except Exception as error:
            self.log_error("Error no controlado: %r", error)
            respuestas.enviar_error(self, 500, "Ocurrió un error en el servidor.")

    def do_GET(self) -> None:
        """Atiende las peticiones GET."""
        self._atender("GET")

    def do_POST(self) -> None:
        """Atiende las peticiones POST."""
        self._atender("POST")


def crear_servidor(host: str, puerto: int) -> HTTPServer:
    """Crea un servidor de un solo hilo en el host y puerto dados."""
    return HTTPServer((host, puerto), ManejadorHttp)
