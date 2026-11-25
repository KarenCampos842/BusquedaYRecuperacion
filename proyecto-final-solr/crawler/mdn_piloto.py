"""Prueba de un artículo de MDN; ejecutar desde cualquier directorio."""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urldefrag, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser
from uuid import uuid4

from bs4 import BeautifulSoup, Comment, NavigableString


URL = "https://developer.mozilla.org/es/docs/Web/JavaScript/Guide/Introduction"
ROBOTS_URL = "https://developer.mozilla.org/robots.txt"
USER_AGENT = "MDNPilotoAcademico/2.0 (proyecto universitario; piloto limitado)"
TIMEOUT = 20
PAUSA = 3.0
MAX_BYTES = 5_000_000
EXTENSIONES_RECURSOS = {
    ".txt", ".json", ".xml", ".csv", ".tsv", ".md", ".pdf", ".zip", ".gz",
    ".tar", ".7z", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".avif", ".mp3", ".mp4", ".ogg", ".webm", ".wav", ".woff", ".woff2",
    ".ttf", ".otf", ".css", ".js", ".mjs", ".map", ".wasm", ".webmanifest",
}
DATA = Path(__file__).resolve().parents[1] / "data" / "mdn"


class PilotoError(Exception):
    pass


class RastreoDetenido(PilotoError):
    """Bloqueo o restricción que impide continuar con otras páginas."""


def normalizar_url(url, base=None):
    url = urljoin(base, url) if base else url
    parts = urlsplit(url)
    # Validar antes de resolver segmentos: no ocultar rutas ambiguas codificadas.
    limpia = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path,
                        parts.query, ""))
    validar_url(limpia)
    path = unquote(parts.path)
    if "%" in path or "//" in path or any(ord(c) < 32 for c in path):
        raise PilotoError(f"Ruta ambigua: {url}")
    if Path(path.rstrip("/")).suffix.casefold() in EXTENSIONES_RECURSOS:
        raise PilotoError(f"Recurso ajeno a artículos HTML: {url}")
    path = quote(path.rstrip("/"), safe="/!$&'()*+,-.:;=@_~")
    return urlunsplit(("https", "developer.mozilla.org", path, "", ""))


def filtrar_enlaces(enlaces, origen):
    """Candidatos HTML únicos; el MIME real se comprueba al descargar."""
    propia = normalizar_url(origen)
    resultado, vistos = [], {propia}
    for enlace in enlaces:
        try:
            destino = normalizar_url(enlace, origen)
        except (PilotoError, ValueError):
            continue
        if destino not in vistos:
            vistos.add(destino)
            resultado.append(destino)
    return resultado


def clasificar_documento(url):
    """Heurística por ruta: raíces y portadas de secciones son índices."""
    url = normalizar_url(url)
    categoria = validar_url(url)
    ruta = unquote(urlsplit(url).path)
    if ruta == f"/es/docs/Web/{categoria}" or ruta.rsplit("/", 1)[-1] in {
        "Guide", "Guides", "Reference", "Tutorials",
    }:
        return "indice"
    return "articulo_explicativo"


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


def octetos_robots(texto):
    """Unificar escapes no reservados; conservar %2F distinto de /."""
    no_reservados = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
    if re.search(r"%(?![0-9a-fA-F]{2})", texto):
        raise PilotoError("Escape porcentual ambiguo en política o URL")

    def escape(match):
        caracter = chr(int(match[1], 16))
        return caracter if caracter in no_reservados else "%" + match[1].upper()

    texto = re.sub(r"%([0-9a-fA-F]{2})", escape, texto)
    return quote(texto, safe="/?:@!$&'()*+,;=-._~%")


class RobotsConPatrones(RobotFileParser):
    """robotparser para frecuencias; reglas de acceso con *, $ y precedencia."""

    def parse(self, lines):
        lines = list(lines)
        self.grupos = []
        agentes, reglas, con_directivas = [], [], False
        for linea in lines:
            linea = linea.split("#", 1)[0].strip()
            if not linea:
                continue
            clave, _, valor = linea.partition(":")
            clave, valor = clave.strip().lower(), valor.strip()
            if clave == "user-agent":
                if con_directivas:
                    self.grupos.append((agentes, reglas))
                    agentes, reglas, con_directivas = [], [], False
                if not valor or ("*" in valor and valor != "*"):
                    raise PilotoError("User-agent de robots.txt no interpretable")
                agentes.append(valor.lower())
            elif clave in {"allow", "disallow"}:
                if not agentes:
                    raise PilotoError("Regla de robots.txt sin User-agent")
                con_directivas = True
                if not valor:
                    continue
                if not valor.startswith("/"):
                    raise PilotoError("Ruta de robots.txt no interpretable")
                patron = octetos_robots(valor)
                final = patron.endswith("$")
                cuerpo = patron[:-1] if final else patron
                regex = "^" + ".*".join(re.escape(p) for p in cuerpo.split("*"))
                if final:
                    regex += "$"
                reglas.append((re.compile(regex), len(cuerpo.replace("*", "").encode("utf-8")),
                               clave == "allow"))
            elif agentes:
                con_directivas = True
        if agentes:
            self.grupos.append((agentes, reglas))
        super().parse(lines)

    def can_fetch(self, useragent, url):
        if not self.last_checked or not getattr(self, "grupos", None):
            return False
        agente = useragent.split("/", 1)[0].lower()
        candidatos = []
        for agentes, reglas in self.grupos:
            coincidencias = [len(a) for a in agentes if a != "*" and a in agente]
            prioridad = max(coincidencias) if coincidencias else (0 if "*" in agentes else -1)
            if prioridad >= 0:
                candidatos.append((prioridad, reglas))
        if not candidatos:
            return True
        prioridad = max(p for p, _ in candidatos)
        partes = urlsplit(url)
        ruta = octetos_robots((partes.path or "/") + ("?" + partes.query if partes.query else ""))
        coincidencias = [(longitud, permite) for p, reglas in candidatos if p == prioridad
                         for patron, longitud, permite in reglas if patron.search(ruta)]
        # La regla más específica gana; en empate se prefiere Allow.
        return max(coincidencias)[1] if coincidencias else True


def interpretar_robots(texto):
    # RobotFileParser es permisivo con documentos arbitrarios: rechazar HTML
    # y respuestas sin grupos antes de consultar can_fetch.
    if "<" in texto or not any(
        line.split("#", 1)[0].strip().lower().startswith("user-agent:")
        and line.split(":", 1)[1].split("#", 1)[0].strip()
        for line in texto.splitlines()
    ):
        raise PilotoError("robots.txt no contiene una política interpretable con seguridad")
    for linea in texto.splitlines():
        linea = linea.split("#", 1)[0].strip()
        if not linea:
            continue
        clave, separador, valor = linea.partition(":")
        clave, valor = clave.strip().lower(), valor.strip()
        if not separador or not re.fullmatch(r"[a-z-]+", clave):
            raise PilotoError("robots.txt tiene sintaxis ambigua; permisos no comprobados")
        if clave == "crawl-delay" and not valor.isdigit():
            raise PilotoError("crawl-delay no interpretable por urllib.robotparser")
        if clave == "request-rate" and not re.fullmatch(r"[1-9]\d*/[1-9]\d*", valor):
            raise PilotoError("request-rate no interpretable por urllib.robotparser")
    parser = RobotsConPatrones(ROBOTS_URL)
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
                exc.close()
                return None, exc.headers
            exc.close()
            if exc.code in (401, 403, 429, 503) or evento["retry_after"]:
                raise RastreoDetenido(f"HTTP {exc.code}; Retry-After={evento['retry_after']}; sin reintentos") from exc
            raise PilotoError(f"HTTP {exc.code} en {url}; Retry-After={evento['retry_after']}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            evento["error"] = str(exc)
            raise PilotoError(f"Error de red en {url}: {exc}") from exc
        finally:
            self.ultima = time.monotonic()


def descargar_articulo(cliente, robots, url, solicitadas=None):
    visitadas = set()
    for _ in range(6):
        url = normalizar_url(url)
        if url in visitadas:
            raise PilotoError("Bucle de redirecciones")
        visitadas.add(url)
        if not robots.can_fetch(USER_AGENT, url):
            cliente.reporte["rechazadas"].append({"url": url, "motivo": "robots.txt"})
            raise PilotoError(f"robots.txt no permite descargar {url}")
        if solicitadas is not None:
            if url in solicitadas:
                raise PilotoError(f"URL ya solicitada: {url}")
            solicitadas.add(url)
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


def texto_limpio(articulo):
    """Separar bloques, unir texto inline como en HTML y preservar <pre>."""
    bloques = {"p", "div", "section", "h1", "h2", "h3", "h4", "h5", "h6",
               "li", "ul", "ol", "dl", "dt", "dd", "tr", "blockquote", "figure"}
    ejemplos = []

    def render(node):
        if isinstance(node, Comment):
            return ""
        if isinstance(node, NavigableString):
            return re.sub(r"\s+", " ", str(node))
        if node.name == "pre":
            ejemplos.append(node.get_text().strip("\n"))
            return f"\n\n\x00PRE{len(ejemplos) - 1}\x00\n\n"
        if node.name == "br":
            return "\n\n"
        contenido = "".join(render(child) for child in node.children)
        if node.name in {"td", "th"}:
            return contenido + " | "
        return f"\n\n{contenido}\n\n" if node.name in bloques else contenido

    texto = render(articulo)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r" *\n *", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    for i, ejemplo in enumerate(ejemplos):
        texto = texto.replace(f"\x00PRE{i}\x00", ejemplo)
    return texto


def extraer(url, body, charset=None):
    # MDN se trata como UTF-8 si HTTP no declara charset. No usar detección
    # estadística (puede variar según las dependencias instaladas).
    try:
        html = body.decode(charset or "utf-8-sig", errors="strict")
    except (LookupError, UnicodeError) as exc:
        raise PilotoError(f"HTML no decodificable con {charset or 'UTF-8'}: {exc}") from exc
    soup = BeautifulSoup(html, "html.parser")
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
    if articulo.get("lang", idioma).lower().split("-")[0] != "es":
        raise PilotoError("El contenido principal declara otro idioma")
    # Descubrir antes de eliminar la navegación del contenido exportado.
    enlaces = filtrar_enlaces(
        [enlace["href"] for enlace in articulo.select("a[href]")
         if not enlace.has_attr("download")
         and enlace.get("type", "text/html").split(";", 1)[0].strip().lower()
         in {"text/html", "application/xhtml+xml"}], url)
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
    titulo_documento = soup.title.get_text(" ", strip=True) if soup.title else ""
    og = soup.select_one('meta[property="og:title"]')
    descriptivo = (og.get("content", "").strip() if og else "") or titulo_documento or titulo
    descriptivo = re.sub(r"\s*[|—-]\s*MDN(?: Web Docs)?\s*$", "", descriptivo).strip()
    contenido = texto_limpio(articulo)
    if not titulo or len(contenido) < 100:
        raise PilotoError("Artículo vacío o insuficiente")
    palabras = set(re.findall(r"[a-záéíóúñ]+", contenido.casefold()))
    if len(palabras & {"el", "la", "los", "las", "de", "del", "para", "que", "una", "un", "en", "es", "por", "con"}) < 3:
        raise PilotoError("Contenido sin evidencia textual suficiente de español")
    return {
        "id": url, "url": url, "titulo": titulo, "contenido": contenido,
        "titulo_original": titulo, "titulo_descriptivo": descriptivo,
        "titulo_documento": titulo_documento, "enlaces_salientes": enlaces,
        "idioma": idioma, "categoria": validar_url(url), "fuente": "MDN Web Docs",
        "tipo_fuente": "web", "profundidad": 0,
        "tipo_documento": clasificar_documento(url),
        "fecha_rastreo": datetime.now(timezone.utc).isoformat(),
        "atribucion": f"MDN Web Docs — {titulo} — {url}",
    }


def guardar(path, objeto):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(objeto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def crear_ejecucion(directorio, prefijo):
    """Reservar una carpeta nueva; jamás reutilizar rutas de evidencia."""
    directorio = Path(directorio)
    directorio.mkdir(parents=True, exist_ok=True)
    nombre = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    ruta = directorio / f"{prefijo}_{nombre}_{uuid4().hex}"
    ruta.mkdir(exist_ok=False)
    return ruta


def guardar_nuevo(path, objeto):
    """Escritura exclusiva: un archivo existente siempre produce error."""
    with Path(path).open("x", encoding="utf-8", newline="\n") as archivo:
        archivo.write(json.dumps(objeto, ensure_ascii=False, indent=2) + "\n")


def main():
    ejecucion = crear_ejecucion(DATA / "ejecuciones", "pagina")
    reporte = {"url_solicitada": URL, "user_agent": USER_AGENT,
               "fecha": datetime.now(timezone.utc).isoformat(),
               "solicitudes": [], "aceptadas": [], "rechazadas": []}
    salida = ejecucion / "documento.json"
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
        guardar_nuevo(salida, documento)
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
        print(f"DETENIDO: {exc}\nNo se generó un nuevo documento.")
        codigo = 1
    guardar_nuevo(ejecucion / "reporte.json", reporte)
    print(f"Reporte: {ejecucion / 'reporte.json'}")
    return codigo


if __name__ == "__main__":
    raise SystemExit(main())
