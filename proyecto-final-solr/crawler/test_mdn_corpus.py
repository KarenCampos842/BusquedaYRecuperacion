import unittest
import hashlib
import json
from email.message import Message

from mdn_corpus import SEMILLAS, Unicos, ejecutar, huella, huella_normalizada
from mdn_piloto import (PilotoError, URL, extraer, normalizar_url, interpretar_robots,
                        clasificar_documento, filtrar_enlaces)
from actualizar_corpus_piloto import actualizar


def pagina(texto, enlaces="", idioma="es"):
    return (f'<html lang="{idioma}"><head><meta charset="utf-8"><title>Introducción a JavaScript | MDN</title>'
            '<meta property="og:title" content="Introducción a JavaScript | MDN"></head>'
            '<main><h1>Introducción</h1><article class="main-page-content">'
            f'<p>{texto}</p>{enlaces}</article></main></html>').encode('utf-8')


TEXTO = 'El lenguaje es para la web y permite crear aplicaciones. ' * 5


class CorpusTests(unittest.TestCase):
    def test_hash_del_contenido_almacenado_y_deduplicacion_separados(self):
        doc = {'url': URL, 'contenido': '  ÁRBOL\n\nUn ejemplo.\n  código();  '}
        self.assertTrue(Unicos().aceptar(doc))
        almacenado = json.loads(json.dumps(doc, ensure_ascii=False))
        self.assertEqual(almacenado['sha256_contenido'],
                         hashlib.sha256(almacenado['contenido'].encode('utf-8')).hexdigest())
        self.assertEqual(doc['sha256_contenido_normalizado'],
                         hashlib.sha256('árbol un ejemplo. código();'.encode('utf-8')).hexdigest())
        self.assertNotEqual(huella(doc), huella_normalizada(doc))

    def test_filtra_recursos_y_autorreferencias(self):
        recursos = ['contributors.txt', 'CONTRIBUTORS.TXT/', '%63ontributors%2Etxt',
                    'datos.json', 'manual.pdf', 'imagen.svg', 'archivo.zip', 'ejemplo.js']
        enlaces = [URL + '/' + recurso for recurso in recursos]
        enlaces += [URL, URL + '/', '#seccion', URL + '#titulo', '']
        destino = SEMILLAS[2] + '/Reference/Properties/color'
        self.assertEqual(filtrar_enlaces(enlaces + [destino, destino + '#x'], URL), [destino])
        for recurso in recursos:
            with self.subTest(recurso=recurso), self.assertRaises(PilotoError):
                normalizar_url(URL + '/' + recurso)
        # Los puntos también aparecen en nombres de artículos, no son todos recursos.
        self.assertEqual(normalizar_url(SEMILLAS[0] + '/Reference/Global_Objects/Object.assign'),
                         SEMILLAS[0] + '/Reference/Global_Objects/Object.assign')

    def test_extractor_excluye_enlaces_descargables_y_propios(self):
        enlaces = (f'<a href="{URL}#x">Esta página</a><a href="contributors.txt">Autoría</a>'
                   '<a href="adjunto" download>Descarga</a>'
                   '<a href="datos" type="application/json">Datos</a>'
                   f'<a href="{SEMILLAS[2]}">CSS</a>')
        self.assertEqual(extraer(URL, pagina(TEXTO, enlaces))['enlaces_salientes'], [SEMILLAS[2]])

    def test_clasificacion_independiente_de_categoria(self):
        for raiz in SEMILLAS:
            for url in (raiz, raiz + '/', raiz + '/Guide', raiz + '/Reference'):
                self.assertEqual(clasificar_documento(url), 'indice')
        self.assertEqual(clasificar_documento(URL), 'articulo_explicativo')
        doc = extraer(URL, pagina(TEXTO))
        self.assertEqual(doc['tipo_documento'], 'articulo_explicativo')
        self.assertEqual(doc['categoria'], 'JavaScript')

    def test_actualizacion_local_no_muta_el_original(self):
        original = {'url': URL, 'contenido': TEXTO, 'categoria': 'JavaScript',
                    'fecha_rastreo': '2026-11-23', 'sha256_contenido': 'huella antigua',
                    'enlaces_salientes': [URL + '/contributors.txt', URL + '#x', SEMILLAS[2]]}
        copia = json.loads(json.dumps(original))
        nuevo = actualizar([original])[0]
        self.assertEqual(original, copia)
        for campo in ('contenido', 'categoria', 'fecha_rastreo'):
            self.assertEqual(nuevo[campo], original[campo])
        self.assertEqual(nuevo['sha256_contenido'], huella(nuevo))
        self.assertEqual(nuevo['enlaces_salientes'], [SEMILLAS[2]])

    def test_normalizacion_y_filtros(self):
        self.assertEqual(normalizar_url(URL + '/#ejemplo'), URL)
        self.assertEqual(normalizar_url('/es/docs/Web/CSS/%63olor#x', URL),
                         'https://developer.mozilla.org/es/docs/Web/CSS/color')
        for url in ('https://example.com/es/docs/Web/CSS',
                    'http://developer.mozilla.org/es/docs/Web/CSS',
                    'https://developer.mozilla.org/en-US/docs/Web/CSS',
                    'https://developer.mozilla.org/es/docs/Web/CSSx',
                    'https://developer.mozilla.org/es/docs/Web/CSS/%2e%2e/API',
                    'https://developer.mozilla.org/es/docs/Web/CSS/%252e%252e/API',
                    URL + '?raw=1', 'javascript:alert(1)'):
            with self.subTest(url=url), self.assertRaises(PilotoError):
                normalizar_url(url)

    def test_inline_parrafos_codigo_y_titulos(self):
        html = pagina('<!--lit-part NO EXPORTAR-->La <a href="/es/docs/Web/CSS">web</a> usa '
                      '<strong>JavaScript</strong> para crear aplicaciones. ' + TEXTO,
                      '<p>Una segunda oración con <code>Array</code>.</p>'
                      '<pre>if (x) {\n  hola();\n}</pre>')
        doc = extraer(URL, html)
        self.assertIn('La web usa JavaScript para crear aplicaciones.', doc['contenido'])
        self.assertIn('\n\nUna segunda oración con Array.', doc['contenido'])
        self.assertIn('if (x) {\n  hola();\n}', doc['contenido'])
        self.assertEqual(doc['titulo_original'], 'Introducción')
        self.assertEqual(doc['titulo_descriptivo'], 'Introducción a JavaScript')
        self.assertNotIn('lit-part', doc['contenido'])

    def test_robots_ambiguo_y_frecuencia_ininterpretable(self):
        for regla in ('Disallow /', 'Crawl-delay: 0.5', 'Request-rate: 0/0'):
            with self.subTest(regla=regla), self.assertRaises(PilotoError):
                interpretar_robots('User-agent: *\n' + regla)

    def test_no_html_no_se_extrae(self):
        from mdn_piloto import descargar_articulo

        class ClienteNoHTML:
            reporte = {'rechazadas': []}

            def obtener(self, url):
                headers = Message()
                headers['Content-Type'] = 'application/pdf'
                return b'%PDF', headers

        with self.assertRaisesRegex(PilotoError, 'no es HTML'):
            descargar_articulo(ClienteNoHTML(), interpretar_robots('User-agent: *\nAllow: /'), URL)

    def test_rechaza_ingles_con_html_es(self):
        with self.assertRaises(PilotoError):
            extraer(URL, pagina('This is the main article with examples for the browser. ' * 10))

    def test_deduplicacion_url_y_contenido(self):
        unicos = Unicos()
        self.assertTrue(unicos.aceptar({'url': URL, 'contenido': TEXTO}))
        self.assertFalse(unicos.aceptar({'url': URL + '#x', 'contenido': 'otro'}))
        self.assertFalse(unicos.aceptar({'url': SEMILLAS[1], 'contenido': TEXTO.upper()}))

    def test_fallo_robots_no_solicita_articulos(self):
        clientes = []

        class ClienteFallido:
            def __init__(self, reporte):
                self.llamadas = []
                clientes.append(self)

            def obtener(self, url):
                self.llamadas.append(url)
                raise PilotoError('robots inaccesible')

        docs, reporte = ejecutar(cliente_factory=ClienteFallido, corpus_previo=None)
        self.assertEqual(docs, [])
        self.assertEqual(reporte['resultado'], 'detenido')
        self.assertEqual(len(clientes[0].llamadas), 1)

    def test_descubre_por_enlaces_cuotas_y_sin_descargas_duplicadas(self):
        clientes = []

        class ClienteLocal:
            def __init__(self, reporte):
                self.reporte = reporte
                self.llamadas = []
                clientes.append(self)

            def obtener(self, url):
                self.llamadas.append(url)
                self.reporte['solicitudes'].append({'url': url, 'codigo_http': 200})
                headers = Message()
                if url.endswith('/robots.txt'):
                    headers['Content-Type'] = 'text/plain'
                    return b'User-agent: *\nAllow: /\n', headers
                headers['Content-Type'] = 'text/html; charset=utf-8'
                enlaces = ''.join(f'<a href="{url}/articulo{i}#x">Artículo</a>' for i in range(3))
                enlaces += f'<a href="{url}/contributors.txt">Autoría</a><a href="{url}#x">Aquí</a>'
                return pagina(TEXTO + url, enlaces), headers

        docs, reporte = ejecutar(cliente_factory=ClienteLocal, corpus_previo=None,
                                cuotas={'JavaScript': 4, 'HTML': 4, 'CSS': 4}, max_indices_por_categoria=4)
        self.assertEqual(len(docs), 12)
        self.assertEqual(reporte['conteo_por_categoria'], {'JavaScript': 4, 'HTML': 4, 'CSS': 4})
        self.assertTrue(all(d['descubierta_desde'] for d in docs if d['profundidad'] > 0))
        self.assertEqual(len(clientes[0].llamadas), len(set(clientes[0].llamadas)))
        self.assertFalse(any('contributors.txt' in x['url'] for x in reporte['descubiertas']))
        self.assertFalse(any('contributors.txt' in url for url in clientes[0].llamadas))


if __name__ == '__main__':
    unittest.main()
