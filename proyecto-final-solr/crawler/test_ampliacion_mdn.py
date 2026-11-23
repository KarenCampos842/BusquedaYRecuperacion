"""Ampliación controlada usando únicamente respuestas locales."""

import contextlib
import io
import json
import tempfile
import unittest
from email.message import Message
from pathlib import Path
from unittest.mock import patch

import mdn_corpus
from mdn_corpus import (CATEGORIAS, CORPUS_VALIDADO, SEMILLAS, cargar_validados,
                        ejecutar, huella, huella_normalizada)
from mdn_piloto import PilotoError, clasificar_documento
from test_mdn_corpus import TEXTO, pagina


def validado(url, enlaces=()):
    doc = {'id': url, 'url': url, 'titulo': 'Documento validado', 'contenido': TEXTO + url,
           'categoria': url.split('/')[6], 'idioma': 'es', 'fuente': 'MDN Web Docs',
           'tipo_fuente': 'web', 'tipo_documento': clasificar_documento(url),
           'profundidad': 1, 'fecha_rastreo': '2026-11-23T22:00:00+00:00',
           'descubierta_desde': SEMILLAS[0], 'atribucion': 'Atribución original',
           'enlaces_salientes': list(enlaces)}
    doc['sha256_contenido'] = huella(doc)
    doc['sha256_contenido_normalizado'] = huella_normalizada(doc)
    return doc


class AmpliacionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'validados.json'
        self.llamadas = []
        self.html = {}
        self.politica = b'User-agent: *\nAllow: /\n'

    def guardar(self, docs):
        self.path.write_text(json.dumps(docs, ensure_ascii=False), encoding='utf-8')
        return self.path

    def cliente(self, reporte):
        exterior = self

        class ClienteLocal:
            def obtener(self, url):
                exterior.llamadas.append(url)
                headers = Message()
                if url.endswith('/robots.txt'):
                    headers['Content-Type'] = 'text/plain'
                    body = exterior.politica
                else:
                    headers['Content-Type'] = 'text/html; charset=utf-8'
                    body = exterior.html.get(url, pagina(TEXTO + url))
                reporte['solicitudes'].append({'url': url, 'codigo_http': 200})
                return body, headers

        return ClienteLocal()

    def ejecutar(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return ejecutar(cliente_factory=self.cliente, corpus_previo=self.path, **kwargs)

    def test_cuotas_desiguales_con_reutilizacion_y_sin_redescargas(self):
        previos = [validado(raiz, [raiz + '/nuevo', raiz + '/nuevo#x']) for raiz in SEMILLAS]
        self.guardar(previos)
        antes = self.path.read_bytes()
        cuotas = dict(zip(CATEGORIAS, (3, 2, 1)))
        self.html[SEMILLAS[0] + '/nuevo'] = pagina(TEXTO + 'JavaScript nuevo',
                                               f'<a href="{SEMILLAS[0]}/otro">Otro</a>')
        docs, reporte = self.ejecutar(cuotas=cuotas, max_indices_por_categoria=1)
        self.assertEqual(reporte['conteo_por_categoria'], cuotas)
        self.assertEqual(reporte['resultado'], 'completo')
        self.assertEqual(reporte['total_reutilizados'], 3)
        self.assertEqual(reporte['total_nuevos'], 3)
        for previo in previos:
            self.assertIn(previo, docs)
            self.assertNotIn(previo['url'], self.llamadas)
        self.assertEqual(self.path.read_bytes(), antes)
        self.assertEqual(len(self.llamadas), len(set(self.llamadas)))

    def test_prioridad_articulos_y_limite_indices_cero(self):
        raiz = SEMILLAS[0]
        self.guardar([validado(raiz, [raiz + '/Guide', raiz + '/explicacion'])])
        self.html[raiz + '/explicacion'] = pagina(TEXTO + 'Explicación real de JavaScript.')
        docs, reporte = self.ejecutar(cuotas={'JavaScript': 1, 'HTML': 0, 'CSS': 0},
                                     max_indices_por_categoria=0)
        self.assertEqual([d['url'] for d in docs], [raiz + '/explicacion'])
        self.assertNotIn(raiz + '/Guide', self.llamadas)
        self.assertEqual(reporte['indices_por_categoria']['JavaScript'], 0)
        self.assertEqual(len(reporte['solo_descubrimiento']), 1)

    def test_indice_descubre_pero_no_ocupa_plaza_de_articulo(self):
        self.guardar([])
        raiz = SEMILLAS[0]
        self.html[raiz] = pagina(TEXTO, f'<a href="{raiz}/explicacion">Artículo</a>')
        docs, reporte = self.ejecutar(cuotas={'JavaScript': 1, 'HTML': 0, 'CSS': 0},
                                     max_indices_por_categoria=1)
        self.assertEqual([d['url'] for d in docs], [raiz + '/explicacion'])
        self.assertEqual(len(reporte['indices_no_incorporados']), 1)

    def test_relleno_indices_respeta_cupo_y_resultado_parcial(self):
        self.guardar([])
        raiz = SEMILLAS[0]
        self.html[raiz] = pagina(TEXTO, f'<a href="{raiz}/Guide">Guía</a>')
        docs, reporte = self.ejecutar(cuotas={'JavaScript': 3, 'HTML': 0, 'CSS': 0},
                                     max_indices_por_categoria=1)
        self.assertEqual(len(docs), 1)
        self.assertEqual(reporte['resultado'], 'parcial')
        self.assertEqual(reporte['faltantes_por_categoria']['JavaScript'], 2)

    def test_limite_exacto_incluye_robots(self):
        self.guardar([])
        docs, reporte = self.ejecutar(max_solicitudes=1)
        self.assertEqual(len(self.llamadas), 1)
        self.assertTrue(self.llamadas[0].endswith('/robots.txt'))
        self.assertEqual(docs, [])
        self.assertEqual(reporte['resultado'], 'parcial')

    def test_limite_global_tambien_corta_redirecciones(self):
        self.guardar([])
        factory = self.cliente

        def con_redireccion(reporte):
            cliente = factory(reporte)
            obtener = cliente.obtener

            def respuesta(url):
                if url.endswith('/robots.txt'):
                    return obtener(url)
                self.llamadas.append(url)
                headers = Message()
                headers['Location'] = SEMILLAS[0] + '/destino'
                reporte['solicitudes'].append({'url': url, 'codigo_http': 302})
                return None, headers

            cliente.obtener = respuesta
            return cliente

        with contextlib.redirect_stdout(io.StringIO()):
            docs, reporte = ejecutar(cliente_factory=con_redireccion, corpus_previo=self.path,
                                     cuotas={'JavaScript': 1, 'HTML': 0, 'CSS': 0}, max_solicitudes=2)
        self.assertEqual(len(self.llamadas), 2)
        self.assertNotIn(SEMILLAS[0] + '/destino', self.llamadas)
        self.assertEqual(docs, [])
        self.assertEqual(reporte['resultado'], 'parcial')

    def test_profundidad_cero_no_descubre_descendientes(self):
        self.guardar([validado(SEMILLAS[0], [SEMILLAS[0] + '/hijo'])])
        docs, reporte = self.ejecutar(cuotas={'JavaScript': 2, 'HTML': 0, 'CSS': 0},
                                     max_profundidad=0)
        self.assertNotIn(SEMILLAS[0] + '/hijo', self.llamadas)
        self.assertEqual(reporte['descubiertas'], [])
        self.assertEqual(len(docs), 1)

    def test_duplicado_contenido_validado_se_rechaza(self):
        raiz = SEMILLAS[0]
        previo = validado(raiz + '/explicacion', [raiz + '/alias'])
        self.guardar([previo])
        self.html[raiz + '/alias'] = pagina(previo['contenido'])
        docs, reporte = self.ejecutar(cuotas={'JavaScript': 2, 'HTML': 0, 'CSS': 0},
                                     max_indices_por_categoria=0)
        self.assertEqual(docs, [previo])
        self.assertTrue(any('duplicado' in d['motivo'].lower() for d in reporte['rechazadas']))

    def test_corpus_alterado_detiene_antes_de_red(self):
        previo = validado(SEMILLAS[0])
        previo['contenido'] += ' Alteración'
        self.guardar([previo])
        docs, reporte = self.ejecutar()
        self.assertEqual(docs, [])
        self.assertEqual(reporte['resultado'], 'detenido')
        self.assertEqual(self.llamadas, [])

    def test_robots_denegado_no_borra_reutilizados(self):
        previo = validado(SEMILLAS[0], [SEMILLAS[0] + '/nuevo'])
        self.guardar([previo])
        self.politica = b'User-agent: *\nDisallow: /\n'
        docs, reporte = self.ejecutar()
        self.assertEqual(docs, [previo])
        self.assertEqual(len(self.llamadas), 1)
        self.assertGreater(len(reporte['rechazadas']), 0)

    def test_corpus_v2_real_se_reutiliza_identico_sin_red(self):
        previos, procedencia = cargar_validados(CORPUS_VALIDADO)
        with contextlib.redirect_stdout(io.StringIO()):
            docs, reporte = ejecutar(cliente_factory=self.cliente, corpus_previo=CORPUS_VALIDADO,
                                     cuotas={cat: 4 for cat in CATEGORIAS})
        self.assertEqual(len(docs), 12)
        self.assertTrue(all(d in docs for d in previos))
        self.assertEqual(reporte['total_reutilizados'], 12)
        self.assertEqual(reporte['total_nuevos'], 0)
        self.assertFalse(reporte['robots_verificado'])
        self.assertEqual(self.llamadas, [])
        self.assertEqual(reporte['corpus_origen']['sha256_archivo'], procedencia['sha256_archivo'])

    def test_objetivo_60_con_12_reutilizados_y_48_respuestas_locales(self):
        previos, _ = cargar_validados(CORPUS_VALIDADO)
        for previo in previos:
            # Crear un archivo temporal de validados con enlaces de prueba;
            # nunca editar el V2 real ni su texto o fecha de rastreo.
            raiz = f"https://developer.mozilla.org/es/docs/Web/{previo['categoria']}"
            previo['enlaces_salientes'] = [raiz + f'/nuevo{i}' for i in range(16)]
        self.guardar(previos)
        docs, reporte = self.ejecutar()
        self.assertEqual(reporte['conteo_por_categoria'], {cat: 20 for cat in CATEGORIAS})
        self.assertEqual(reporte['total_documentos'], 60)
        self.assertEqual(reporte['total_reutilizados'], 12)
        self.assertEqual(reporte['total_nuevos'], 48)
        self.assertEqual(len(self.llamadas), 49)  # 48 páginas simuladas + robots
        self.assertEqual(len({d['url'] for d in docs}), 60)
        self.assertEqual(len({d['sha256_contenido_normalizado'] for d in docs}), 60)
        self.assertTrue(all(d in docs for d in previos))

    def test_configuracion_invalida(self):
        for config in ({'cuotas': {cat: 0 for cat in CATEGORIAS}}, {'pausa': 0},
                       {'max_indices_por_categoria': -1}, {'max_solicitudes': 0}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                self.ejecutar(**config)


if __name__ == '__main__':
    unittest.main()
