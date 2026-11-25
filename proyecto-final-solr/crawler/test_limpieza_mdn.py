"""P02-07: regresiones locales contra ejemplos y el corpus de 60 documentos."""

from copy import deepcopy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import limpiar_corpus_mdn

from limpiar_corpus_mdn import (
    AVISO_COMPATIBILIDAD, CABECERAS, CSS_INTERFAZ, ENTRADA, MODIFICABLES,
    advertencias, ejecutar_limpieza, limpiar_texto, procesar_corpus,
    sha256, sha256_normalizado, ruta_reporte,
)
from mdn_corpus import huella, huella_normalizada


def bloque(cabecera=CABECERAS[0]):
    return cabecera + '\n\n' + CSS_INTERFAZ + '\n\n' + AVISO_COMPATIBILIDAD


class LimpiezaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = ENTRADA.read_bytes()
        cls.corpus = json.loads(cls.raw.decode('utf-8'))

    def documento(self, texto):
        doc = deepcopy(self.corpus[0])
        doc['contenido'] = texto
        doc['sha256_contenido'] = sha256(texto)
        doc['sha256_contenido_normalizado'] = sha256_normalizado(texto)
        return doc

    def test_elimina_solo_secuencia_exacta_y_registra_offsets(self):
        for cabecera in CABECERAS:
            texto = 'Antes, con áéíóú.\n\n' + bloque(cabecera) + '\n\nDespués, con ñ.'
            limpio, cambios = limpiar_texto(texto)
            self.assertEqual(limpio, 'Antes, con áéíóú.\n\nDespués, con ñ.')
            self.assertEqual(len(cambios), 1)
            for cambio in cambios:
                self.assertEqual(texto[cambio['inicio']:cambio['fin']], cambio['texto_eliminado'])
            self.assertNotIn(CSS_INTERFAZ, limpio)

    def test_limites_inicio_final_y_bloques_consecutivos(self):
        for texto, esperado in ((bloque() + '\n\nDespués', 'Después'),
                                ('Antes\n\n' + bloque(), 'Antes'),
                                ('Antes\n\n' + bloque() + '\n\n' + bloque() + '\n\nDespués',
                                 'Antes\n\nDespués')):
            with self.subTest(texto=texto[:20]):
                limpio, cambios = limpiar_texto(texto)
                self.assertEqual(limpio, esperado)
                self.assertEqual(sum(len(c['texto_eliminado']) for c in cambios), len(texto) - len(limpio))

    def test_css_legitimo_html_y_js_se_conservan_byte_a_byte(self):
        codigo = ('CSS\n\nspan.classy {\n  background-color: DodgerBlue;\n}\n\n'
                  '#myId#myId span { color: yellow; }\n.myClass.myClass span { color: orange; }\n\n'
                  '<style type="text/css">\n p { color: red; }\n</style>\n\n'
                  'function ejemplo() {\n  const s = "<style> no interpretar como HTML";\n  return s;\n}')
        self.assertEqual(limpiar_texto(codigo), (codigo, []))
        mezclado = codigo + '\n\n' + bloque() + '\n\nTexto final.'
        self.assertEqual(limpiar_texto(mezclado)[0], codigo + '\n\nTexto final.')

    def test_firma_sin_contexto_y_variantes_se_conservan_y_advierten(self):
        for texto in (CSS_INTERFAZ, bloque().replace('font:inherit', 'font: inherit'),
                      'Ejemplo legítimo\n\n' + CSS_INTERFAZ + '\n\n' + AVISO_COMPATIBILIDAD):
            with self.subTest(texto=texto[:25]):
                self.assertEqual(limpiar_texto(texto), (texto, []))
                self.assertTrue(advertencias(texto))
        self.assertTrue(advertencias('CSS Key Concepts: CSS syntax, at-rule, comments.'))

    def test_no_normaliza_espacios_prosa_ni_codigo(self):
        texto = 'Primera  oración.\n\n  segunda línea\n    código();  \n'
        self.assertEqual(limpiar_texto(texto)[0], texto)

    def test_corpus_real_preserva_esquema_orden_y_metadatos(self):
        self.assertEqual(ruta_reporte(ENTRADA), ENTRADA.relative_to(limpiar_corpus_mdn.PROYECTO).as_posix())
        antes = deepcopy(self.corpus)
        nuevos, reporte = procesar_corpus(self.corpus)
        self.assertEqual(self.corpus, antes)
        self.assertEqual(reporte['resumen']['modificados'], 34)
        self.assertEqual(reporte['resumen']['sin_cambios'], 26)
        self.assertEqual(reporte['resumen']['categorias'], {'JavaScript': 20, 'HTML': 20, 'CSS': 20})
        for original, nuevo in zip(self.corpus, nuevos):
            self.assertEqual(original.keys(), nuevo.keys())
            self.assertEqual({k: v for k, v in original.items() if k not in MODIFICABLES},
                             {k: v for k, v in nuevo.items() if k not in MODIFICABLES})
            self.assertEqual(nuevo['sha256_contenido'], huella(nuevo))
            self.assertEqual(nuevo['sha256_contenido_normalizado'], huella_normalizada(nuevo))
            if original['contenido'] == nuevo['contenido']:
                self.assertEqual(original, nuevo)
        for sufijo, ejemplo in (('Class_selectors', 'span.classy {\n  background-color: DodgerBlue;\n}'),
                                ('Specificity', '.myClass.myClass span { color: orange; }'),
                                ('style', '<style type="text/css">\n p { color: red; }\n</style>')):
            doc = next(d for d in nuevos if d['url'].endswith('/' + sufijo))
            self.assertIn(ejemplo, doc['contenido'])

    def test_idempotencia_del_corpus_real(self):
        primera, _ = procesar_corpus(self.corpus)
        segunda, reporte = procesar_corpus(primera)
        self.assertEqual(primera, segunda)
        self.assertEqual(reporte['resumen']['modificados'], 0)

    def test_rechaza_cantidad_hash_esquema_y_documentos_vacios(self):
        casos = [[], [{'contenido': 'Incompleto'}]]
        mal_hash = self.documento('Texto con hash alterado')
        mal_hash['sha256_contenido'] = '0' * 64
        casos.append([mal_hash])
        vacio = self.documento(bloque())
        casos.append([vacio])
        for docs in casos:
            with self.subTest(caso=str(docs)[:20]), self.assertRaises(ValueError):
                procesar_corpus(docs, esperados=1)

    def test_duplicados_despues_no_se_borran_silenciosamente(self):
        primero = self.documento('Texto legítimo.\n\n' + bloque())
        segundo = self.documento('Texto legítimo.')
        segundo['id'] += '/segundo'
        segundo['url'] += '/segundo'
        nuevos, reporte = procesar_corpus([primero, segundo], esperados=2)
        self.assertEqual(len(nuevos), 2)
        self.assertEqual(len(reporte['resumen']['duplicados_normalizados_despues']), 1)

    def test_salida_nueva_sin_sobrescribir_entrada_ni_reportes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            entrada = root / 'corpus.json'
            entrada.write_bytes(self.raw)
            reporte_original = root / 'reporte.json'
            reporte_original.write_bytes(b'{"evidencia":"intacta"}\n')
            salida = root / 'nueva'
            with patch.object(limpiar_corpus_mdn, 'PROYECTO', root.resolve()), contextlib.redirect_stdout(io.StringIO()):
                ejecutar_limpieza(entrada, salida)
                self.assertEqual(ruta_reporte(root.parent / 'externo.json'),
                                 (root.parent / 'externo.json').resolve().as_posix())
            reporte = json.loads((salida / 'reporte_limpieza.json').read_text('utf-8'))
            self.assertEqual(reporte['archivo_entrada'], 'corpus.json')
            self.assertEqual(reporte['archivo_salida'], 'nueva/corpus_limpio.json')
            for campo in ('archivo_entrada', 'archivo_salida'):
                self.assertNotIn(str(root), reporte[campo])
                self.assertNotIn('\\', reporte[campo])
                self.assertFalse(Path(reporte[campo]).is_absolute())
            self.assertEqual(reporte['sha256_archivo_entrada'], hashlib.sha256(self.raw).hexdigest())
            self.assertEqual(entrada.read_bytes(), self.raw)
            self.assertEqual(reporte_original.read_bytes(), b'{"evidencia":"intacta"}\n')
            resultado = (salida / 'corpus_limpio.json').read_bytes()
            with self.assertRaises(FileExistsError):
                ejecutar_limpieza(entrada, salida)
            self.assertEqual((salida / 'corpus_limpio.json').read_bytes(), resultado)

    def test_validacion_fallida_no_crea_salida(self):
        with tempfile.TemporaryDirectory() as tmp:
            entrada = Path(tmp) / 'corpus.json'
            entrada.write_text('[]', encoding='utf-8')
            salida = Path(tmp) / 'salida'
            with self.assertRaises(ValueError):
                ejecutar_limpieza(entrada, salida)
            self.assertFalse(salida.exists())


if __name__ == '__main__':
    unittest.main()
