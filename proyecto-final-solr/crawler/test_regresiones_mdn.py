"""Regresiones sin red: codificación, patrones robots y evidencia inmutable."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mdn_corpus
import mdn_piloto
from mdn_piloto import (
    PilotoError, URL, USER_AGENT, crear_ejecucion, descargar_articulo, extraer,
    guardar_nuevo, interpretar_robots,
)
from test_mdn_corpus import TEXTO, pagina
from test_mdn_piloto import ClienteFalso


class CodificacionTests(unittest.TestCase):
    def test_utf8_sin_charset_no_depende_de_autodeteccion(self):
        # Reproducir exactamente el caso sin HTTP charset ni meta charset.
        html = pagina('El árbol, la programación y el pingüino: áéíóúñ. ' + TEXTO)
        html = html.replace(b'<meta charset="utf-8">', b'')
        with patch('bs4.dammit.UnicodeDammit', side_effect=AssertionError('No autodetectar')):
            doc = extraer(URL, html)
        self.assertEqual(doc['titulo_original'], 'Introducción')
        self.assertIn('árbol, la programación y el pingüino: áéíóúñ.', doc['contenido'])

    def test_charset_http_explicito_y_utf8_producen_el_mismo_texto(self):
        utf8 = pagina('El árbol y la programación de la página. ' + TEXTO)
        latin1 = utf8.decode('utf-8').encode('iso-8859-1')
        a = extraer(URL, utf8)
        b = extraer(URL, latin1, 'iso-8859-1')
        self.assertEqual(a['contenido'], b['contenido'])
        self.assertEqual(a['titulo_original'], b['titulo_original'])

    def test_error_de_bytes_o_charset_desconocido_rechaza(self):
        for html, charset in ((b'\xff', None), (b'html', 'charset-inexistente')):
            with self.subTest(charset=charset), self.assertRaises(PilotoError):
                extraer(URL, html, charset)

    def test_bom_utf8_no_altera_el_contenido(self):
        html = pagina(TEXTO)
        self.assertEqual(extraer(URL, html)['contenido'], extraer(URL, b'\xef\xbb\xbf' + html)['contenido'])


class RobotsPatronesTests(unittest.TestCase):
    def test_regla_mdn_files_impide_la_solicitud(self):
        robots = interpretar_robots('User-agent: *\nDisallow: /*/files/\n')
        cliente = ClienteFalso()
        prohibida = URL + '/files/ejemplo'
        self.assertFalse(robots.can_fetch(USER_AGENT, prohibida))
        self.assertTrue(robots.can_fetch(USER_AGENT, URL))
        with self.assertRaisesRegex(PilotoError, 'robots.txt'):
            descargar_articulo(cliente, robots, prohibida)
        self.assertEqual(cliente.llamadas, [])

    def test_redireccion_a_files_no_se_solicita(self):
        cliente = ClienteFalso(URL + '/files/ejemplo')
        robots = interpretar_robots('User-agent: *\nDisallow: /*/files/\n')
        with self.assertRaisesRegex(PilotoError, 'robots.txt'):
            descargar_articulo(cliente, robots, URL)
        self.assertEqual(cliente.llamadas, [URL])

    def test_ancla_final_y_allow_mas_especifico(self):
        robots = interpretar_robots('User-agent: *\nDisallow: /*/files/\n'
                                   'Allow: /es/docs/Web/CSS/files/publico$\n')
        base = 'https://developer.mozilla.org/es/docs/Web/CSS/files/'
        self.assertTrue(robots.can_fetch(USER_AGENT, base + 'publico'))
        self.assertFalse(robots.can_fetch(USER_AGENT, base + 'publico/privado'))
        self.assertFalse(robots.can_fetch(USER_AGENT, base + 'privado'))

    def test_grupos_especificos_repetidos_y_desempate_allow(self):
        robots = interpretar_robots('User-agent: *\nDisallow: /\n'
                                   'User-agent: MDNPilotoAcademico\nDisallow: /*/files/\n'
                                   'User-agent: MDNPilotoAcademico\nAllow: /*/files/publico$\n'
                                   'Disallow: /*/files/publico$\n')
        self.assertTrue(robots.can_fetch(USER_AGENT, URL))
        self.assertFalse(robots.can_fetch('OtroBot/1.0', URL))
        self.assertTrue(robots.can_fetch(USER_AGENT, URL + '/files/publico'))
        self.assertFalse(robots.can_fetch(USER_AGENT, URL + '/files/privado'))

    def test_escapes_y_frecuencia(self):
        robots = interpretar_robots('User-agent: *\nDisallow: /*/files/\n'
                                   'Crawl-delay: 5\nRequest-rate: 1/10\n')
        self.assertFalse(robots.can_fetch(USER_AGENT, URL + '/%66iles/ejemplo'))
        self.assertEqual(robots.crawl_delay(USER_AGENT), 5)
        self.assertEqual(robots.request_rate(USER_AGENT).seconds, 10)
        with self.assertRaises(PilotoError):
            interpretar_robots('User-agent: *\nDisallow: /%GG/files/\n')


class PersistenciaTests(unittest.TestCase):
    def test_escritura_exclusiva_y_colision_no_sobrescriben(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'evidencia.json'
            guardar_nuevo(path, {'contenido': 'Primera versión'})
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                guardar_nuevo(path, {'contenido': 'Cambios'})
            self.assertEqual(path.read_bytes(), original)
            primera = crear_ejecucion(tmp, 'corpus')
            with patch.object(mdn_piloto, 'datetime') as fecha, patch.object(mdn_piloto, 'uuid4') as uuid:
                # Forzar exactamente el nombre ya reservado.
                marca, identificador = primera.name.removeprefix('corpus_').split('_')
                fecha.now.return_value.strftime.return_value = marca
                uuid.return_value.hex = identificador
                with self.assertRaises(FileExistsError):
                    crear_ejecucion(tmp, 'corpus')

    def test_main_fallido_y_exitoso_crean_resultados_separados(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp)
            evidencias = ('corpus_piloto.json', 'corpus_piloto_reporte.json',
                          'corpus_piloto_v2.json', 'corpus_piloto_v2_ajustes.json',
                          'piloto_1.json', 'piloto_1_reporte.json')
            for nombre in evidencias:
                (raiz / nombre).write_bytes(b'{"evidencia":"intacta"}\n')
            antes = {p.name: p.read_bytes() for p in raiz.glob('*.json')}
            resultados = [([], {'resultado': 'detenido', 'conteo_por_categoria': {}}),
                          ([{'ejemplo': 'local'}] * 12,
                           {'resultado': 'completo', 'conteo_por_categoria': {}})]
            with patch.object(mdn_corpus, 'DATA', raiz), \
                    patch.object(mdn_corpus, 'ejecutar', side_effect=resultados), \
                    patch('sys.argv', ['mdn_corpus.py']), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(mdn_corpus.main(), 1)
                self.assertEqual(mdn_corpus.main(), 0)
            carpetas = list((raiz / 'ejecuciones').iterdir())
            self.assertEqual(len(carpetas), 2)
            estados = {json.loads((p / 'reporte.json').read_text('utf-8'))['resultado']: p
                       for p in carpetas}
            self.assertEqual(json.loads((estados['detenido'] / 'corpus.json').read_text('utf-8')), [])
            self.assertEqual(len(json.loads((estados['completo'] / 'corpus.json').read_text('utf-8'))), 12)
            self.assertEqual(antes, {p.name: p.read_bytes() for p in raiz.glob('*.json')})


if __name__ == '__main__':
    unittest.main()
