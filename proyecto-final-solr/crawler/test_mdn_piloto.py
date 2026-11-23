"""Pruebas locales de límites de acceso y extracción; no usan Internet."""

import unittest
from email.message import Message

from mdn_piloto import (
    URL, PilotoError, SinRedirecciones, descargar_articulo, extraer,
    interpretar_robots, validar_url,
)


class ClienteFalso:
    def __init__(self, destino=None):
        self.llamadas = []
        self.reporte = {"rechazadas": []}
        self.destino = destino

    def obtener(self, url):
        self.llamadas.append(url)
        headers = Message()
        headers["Location"] = self.destino
        return None, headers


class PilotoTests(unittest.TestCase):
    def test_rechaza_rutas_fuera_del_alcance(self):
        for url in (
            URL.replace("https:", "http:"), URL.replace("/es/", "/en-US/"),
            URL.replace("developer.mozilla.org", "developer.mozilla.org.ejemplo.com"),
            "https://developer.mozilla.org/es/docs/Web/CSS/../API",
        ):
            with self.subTest(url=url), self.assertRaises(PilotoError):
                validar_url(url)

    def test_robots_invalido_detiene(self):
        for texto in ("", "<html>Error</html>", "Disallow: /"):
            with self.subTest(texto=texto), self.assertRaises(PilotoError):
                interpretar_robots(texto)

    def test_robots_denegado_no_descarga(self):
        cliente = ClienteFalso()
        robots = interpretar_robots("User-agent: *\nDisallow: /es/\n")
        with self.assertRaises(PilotoError):
            descargar_articulo(cliente, robots, URL)
        self.assertEqual(cliente.llamadas, [])

    def test_redireccion_externa_no_se_solicita(self):
        cliente = ClienteFalso("https://example.com/articulo")
        robots = interpretar_robots("User-agent: *\nAllow: /\n")
        with self.assertRaises(PilotoError):
            descargar_articulo(cliente, robots, URL)
        self.assertEqual(cliente.llamadas, [URL])
        self.assertIsNone(SinRedirecciones().redirect_request(None, None, 302, "", {}, URL))

    def test_redireccion_interna_revalida_robots(self):
        destino = "https://developer.mozilla.org/es/docs/Web/CSS/bloqueado"
        cliente = ClienteFalso(destino)
        robots = interpretar_robots("User-agent: *\nDisallow: /es/docs/Web/CSS/\n")
        with self.assertRaises(PilotoError):
            descargar_articulo(cliente, robots, URL)
        self.assertEqual(cliente.llamadas, [URL])

    def test_extrae_articulo_sin_navegacion(self):
        html = ('<html lang="es"><nav>MENU EXTERIOR</nav><main><h1>Introducción</h1>'
                '<article class="main-page-content"><nav>MENU INTERIOR</nav>'
                '<script>NO INCLUIR</script><p>' + 'Texto del artículo. ' * 15
                + '</p><pre>const ejemplo = 1;</pre></article></main></html>')
        doc = extraer(URL, html.encode("utf-8"))
        self.assertEqual(doc["titulo"], "Introducción")
        self.assertNotIn("MENU", doc["contenido"])
        self.assertNotIn("NO INCLUIR", doc["contenido"])
        self.assertIn("const ejemplo = 1;", doc["contenido"])
        for cuerpo in ('<html lang="en"><article></article></html>', '<html lang="es"></html>'):
            with self.assertRaises(PilotoError):
                extraer(URL, cuerpo.encode())

    def test_diseno_actual_excluye_aviso_y_tabla_lateral(self):
        html = ('<html lang="es"><main id="content">'
                '<div class="reference-layout__header">AVISO<h1>Introducción</h1></div>'
                '<aside>TABLA LATERAL</aside><div class="reference-layout__body">'
                '<a>Anterior</a><p>' + 'Contenido principal. ' * 15
                + '</p><a>Siguiente</a></div></main></html>')
        doc = extraer(URL, html.encode("utf-8"))
        self.assertEqual(doc["titulo"], "Introducción")
        for texto in ("AVISO", "TABLA LATERAL", "Anterior", "Siguiente"):
            self.assertNotIn(texto, doc["contenido"])


if __name__ == "__main__":
    unittest.main()
