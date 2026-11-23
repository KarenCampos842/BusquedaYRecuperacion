"""Prueba de un artículo de MDN; ejecutar desde cualquier directorio."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urldefrag, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup


URL = "https://developer.mozilla.org/es/docs/Web/JavaScript/Guide/Introduction"
ROBOTS_URL = "https://developer.mozilla.org/robots.txt"
USER_AGENT = "MDNPilotoAcademico/1.0 (proyecto universitario; una pagina)"
TIMEOUT = 20
PAUSA = 3.0
MAX_BYTES = 5_000_000
DATA = Path(__file__).resolve().parents[1] / "data" / "mdn"


class PilotoError(Exception):
    pass


class SinRedirecciones(HTTPRedirectHandler):
    """Impide que urllib descargue destinos sin validarlos primero."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validar_url(url):
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.netloc != "developer.mozilla.org"
            or parts.query or parts.fragment):
        raise PilotoError(f"URL fuera del alcance: {url}")
    path = unquote(parts.path)
    if "\\" in path or any(p in {".", ".."} for p in path.split("/")):
        raise PilotoError(f"Ruta ambigua: {url}")
    for categoria in ("JavaScript", "HTML", "CSS"):
        root = f"/es/docs/Web/{categoria}"
        if path == root or path.startswith(root + "/"):
            return categoria
    raise PilotoError(f"Ruta fuera del alcance: {url}")


def interpretar_robots(texto):
    # RobotFileParser es permisivo con documentos arbitrarios: rechazar HTML
    # y respuestas sin grupos antes de consultar can_fetch.
    if "<" in texto or not any(
        line.split("#", 1)[0].strip().lower().startswith("user-agent:")
        and line.split(":", 1)[1].split("#", 1)[0].strip()
        for line in texto.splitlines()
    ):
        raise PilotoError("robots.txt no contiene una política interpretable con seguridad")
    parser = RobotFileParser(ROBOTS_URL)
    parser.parse(texto.splitlines())
    return parser


class Cliente:
    def __init__(self, reporte):
        self.opener = build_opener(SinRedirecciones())
        self.reporte = reporte
        self.ultima = None
        self.intervalo = PAUSA

    def obtener(self, url):
        if self.ultima is not None:
            time.sleep(max(0, self.intervalo - (time.monotonic() - self.ultima)))
        evento = {"url": url}
        self.reporte["solicitudes"].append(evento)
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"})
        try:
            with self.opener.open(request, timeout=TIMEOUT) as response:
                evento["codigo_http"] = response.status
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    raise PilotoError("Respuesta demasiado grande")
                if response.status != 200:
                    raise PilotoError(f"HTTP inesperado: {response.status}")
                return body, response.headers
        except HTTPError as exc:
            evento["codigo_http"] = exc.code
            evento["retry_after"] = exc.headers.get("Retry-After")
            if exc.code in (301, 302, 303, 307, 308):
                destino = exc.headers.get("Location")
                evento["redireccion"] = destino
                return None, exc.headers
            raise PilotoError(f"HTTP {exc.code} en {url}; Retry-After={evento['retry_after']}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            evento["error"] = str(exc)
            raise PilotoError(f"Error de red en {url}: {exc}") from exc
        finally:
            self.ultima = time.monotonic()


def descargar_articulo(cliente, robots, url):
    visitadas = set()
    for _ in range(6):
        validar_url(url)
        if url in visitadas:
            raise PilotoError("Bucle de redirecciones")
        visitadas.add(url)
        if not robots.can_fetch(USER_AGENT, url):
            cliente.reporte["rechazadas"].append({"url": url, "motivo": "robots.txt"})
            raise PilotoError(f"robots.txt no permite descargar {url}")
        body, headers = cliente.obtener(url)
        if body is None:
            destino = headers.get("Location")
            if not destino:
                raise PilotoError("Redirección sin Location")
            url = urldefrag(urljoin(url, destino))[0]
            # El siguiente paso valida alcance y robots ANTES de solicitarlo.
            continue
        if headers.get_content_type() not in {"text/html", "application/xhtml+xml"}:
            raise PilotoError("El artículo no es HTML")
        return url, body, headers.get_content_charset()
    raise PilotoError("Demasiadas redirecciones")


def extraer(url, body, charset=None):
    soup = BeautifulSoup(body, "html.parser", from_encoding=charset)
    idioma = str(soup.html.get("lang", "")).lower() if soup.html else ""
    if idioma != "es" and not idioma.startswith("es-"):
        raise PilotoError(f"Idioma inesperado: {idioma!r}")
    # Estructura confirmada con el HTML real: el cuerpo está separado del
    # encabezado (aviso de traducción) y de la tabla lateral de contenidos.
    articulo = (soup.select_one("article.main-page-content")
                or soup.select_one("main#content .reference-layout__body"))
    if articulo is None:
        estructura = [(tag.name, tag.get("id"), tag.get("class"))
                      for tag in soup.select("main, article, h1")]
        raise PilotoError(f"No se encontró el contenedor principal; estructura real: {estructura}")
    for elemento in articulo.select(
        "script, style, noscript, nav, aside, footer, button, [role=navigation], [role=menu], "
        ".visually-hidden, .reference-layout__toc, .left-sidebar, .right-sidebar, "
        ".prev-next, .prevnext, .article-footer"
    ):
        elemento.decompose()
    for enlace in articulo.select("a"):
        if enlace.get_text(" ", strip=True).casefold() in {"anterior", "siguiente"}:
            enlace.decompose()
    heading = articulo.find("h1") or soup.select_one("main h1")
    if heading is None:
        raise PilotoError("No se encontró el título del artículo")
    titulo = heading.get_text(" ", strip=True)
    contenido = articulo.get_text("\n", strip=True)
    if not titulo or len(contenido) < 100:
        raise PilotoError("Artículo vacío o insuficiente")
    return {
        "id": url, "url": url, "titulo": titulo, "contenido": contenido,
        "idioma": idioma, "categoria": validar_url(url), "fuente": "MDN Web Docs",
        "tipo_fuente": "web", "profundidad": 0,
        "fecha_rastreo": datetime.now(timezone.utc).isoformat(),
        "atribucion": f"MDN Web Docs — {titulo} — {url}",
    }


def guardar(path, objeto):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(objeto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    reporte = {"url_solicitada": URL, "user_agent": USER_AGENT,
               "fecha": datetime.now(timezone.utc).isoformat(),
               "solicitudes": [], "aceptadas": [], "rechazadas": []}
    salida = DATA / "piloto_1.json"
    try:
        validar_url(URL)
        cliente = Cliente(reporte)
        body, headers = cliente.obtener(ROBOTS_URL)
        if body is None:
            raise PilotoError("robots.txt redirige; permisos no comprobados")
        if headers.get_content_type() != "text/plain":
            raise PilotoError("robots.txt no es text/plain; permisos no comprobados")
        robots = interpretar_robots(body.decode("utf-8-sig", errors="strict"))
        reporte["robots_permite_url"] = robots.can_fetch(USER_AGENT, URL)
        delay = robots.crawl_delay(USER_AGENT)
        rate = robots.request_rate(USER_AGENT)
        cliente.intervalo = max(PAUSA, delay or 0, rate.seconds / rate.requests if rate else 0)
        reporte["intervalo_segundos"] = cliente.intervalo
        url, html, charset = descargar_articulo(cliente, robots, URL)
        documento = extraer(url, html, charset)
        guardar(salida, documento)
        reporte["aceptadas"].append(url)
        reporte["resultado"] = "correcto"
        reporte["caracteres_contenido"] = len(documento["contenido"])
        print(f"OK: {url}\nTítulo: {documento['titulo']}\nIdioma: {documento['idioma']}"
              f"\nCategoría: {documento['categoria']}\nCaracteres: {len(documento['contenido'])}"
              f"\nArchivo: {salida}\nVista previa:\n{documento['contenido'][:600]}")
        codigo = 0
    except (PilotoError, UnicodeError, OSError, ValueError) as exc:
        reporte["resultado"] = "detenido"
        reporte["motivo"] = str(exc)
        print(f"DETENIDO: {exc}\nNo se generó un nuevo piloto_1.json.")
        codigo = 1
    guardar(DATA / "piloto_1_reporte.json", reporte)
    print(f"Reporte: {DATA / 'piloto_1_reporte.json'}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
