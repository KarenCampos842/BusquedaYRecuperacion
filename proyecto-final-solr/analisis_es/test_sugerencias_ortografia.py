"""Pruebas sin Solr de Suggester y SpellCheck (P05).

Ejecutar desde proyecto-final-solr/:  py -m unittest discover -s analisis_es -v
"""

import re
import unittest
from unittest import mock

import configurar_analizadores
import configurar_sugerencias_ortografia as configuracion_p05
from configuracion import CORE_PRODUCCION
from definiciones_sugerencias import (
    CAMPO_CONTENIDO,
    CAMPO_ORTOGRAFIA,
    CAMPO_SUGERENCIA,
    CAMPO_TITULO,
    CAMPO_VOCABULARIO,
    CAMPOS_AUXILIARES,
    COMPONENTE_SUGGESTER,
    CONFIGURACION_SOLRCONFIG,
    COPIAS,
    DICCIONARIOS_AUTOCOMPLETADO,
    HANDLER_SUGGESTER,
    NOMBRES_DEL_CONFIGSET_QUE_NO_SE_TOCAN,
    PATRON_TOKEN_VALIDO,
    definir_text_ortografia_es,
    definir_text_sugerencia_es,
    definir_text_vocabulario_es,
)

# \p{L} (Java) equivale a [^\W\d_] en el módulo re de Python.
TOKEN_VALIDO = re.compile(PATRON_TOKEN_VALIDO.replace(r"\p{L}", r"[^\W\d_]"))


def clases(tipo: dict) -> list[str]:
    return [f["class"].removeprefix("solr.") for f in tipo["indexAnalyzer"]["filters"]]


class PruebasDefiniciones(unittest.TestCase):
    def test_nombres_nuevos_no_chocan_con_el_configset(self):
        nombres = {definicion["name"] for _, definicion in CONFIGURACION_SOLRCONFIG}
        self.assertFalse(nombres & NOMBRES_DEL_CONFIGSET_QUE_NO_SE_TOCAN)

    def test_ortografia_sin_stemming_ni_plegado(self):
        filtros = clases(definir_text_ortografia_es())
        self.assertNotIn("SpanishLightStemFilterFactory", filtros)
        self.assertNotIn("ASCIIFoldingFilterFactory", filtros)

    def test_sugerencia_sin_stemming_ni_palabras_vacias(self):
        filtros = clases(definir_text_sugerencia_es())
        self.assertEqual(filtros, ["LowerCaseFilterFactory", "ASCIIFoldingFilterFactory"])

    def test_copias_desde_titulo_y_contenido(self):
        self.assertEqual({(c["source"], c["dest"]) for c in COPIAS}, {
            (CAMPO_TITULO, CAMPO_SUGERENCIA),
            (CAMPO_CONTENIDO, CAMPO_ORTOGRAFIA),
            (CAMPO_CONTENIDO, CAMPO_VOCABULARIO),
        })

    def test_vocabulario_sin_stemming_ni_plegado(self):
        filtros = clases(definir_text_vocabulario_es())
        self.assertNotIn("SpanishLightStemFilterFactory", filtros)
        self.assertNotIn("ASCIIFoldingFilterFactory", filtros)
        self.assertIn("ManagedStopFilterFactory", filtros)

    def test_vocabulario_descarta_restos_de_codigo(self):
        for valido in ("promesa", "función", "promise.all"):
            self.assertTrue(TOKEN_VALIDO.fullmatch(valido), valido)
        for invalido in ("javascript:void", "h1", "123", ".prototype", "a_b"):
            self.assertFalse(TOKEN_VALIDO.fullmatch(invalido), invalido)

    def test_suggester_con_diccionarios_de_terminos_y_titulos(self):
        nombres = [s["name"] for s in COMPONENTE_SUGGESTER["suggester"]]
        self.assertEqual(sorted(nombres), sorted(DICCIONARIOS_AUTOCOMPLETADO))
        self.assertEqual(HANDLER_SUGGESTER["defaults"]["suggest.dictionary"], DICCIONARIOS_AUTOCOMPLETADO)

    def test_titulo_sugerencia_almacenado_para_el_diccionario(self):
        campo = next(c for c in CAMPOS_AUXILIARES if c["name"] == CAMPO_SUGERENCIA)
        self.assertTrue(campo["stored"])


def simular_solr(copias_existentes=()):
    """Devuelve (obtener, enviar, enviados) simulados."""
    enviados = []

    def obtener(core, ruta, parametros=None):
        if ruta == "schema/copyfields":
            return {"copyFields": [{"source": s, "dest": d} for s, d in copias_existentes]}
        return {}

    def enviar(core, ruta, cuerpo, **_):
        enviados.append((ruta, cuerpo))
        return {}

    return obtener, enviar, enviados


class PruebasConfigurar(unittest.TestCase):
    def _configurar(self, copias_existentes=()):
        obtener, enviar, enviados = simular_solr(copias_existentes)
        with mock.patch.object(configuracion_p05, "obtener", side_effect=obtener), \
             mock.patch.object(configuracion_p05, "enviar", side_effect=enviar), \
             mock.patch.object(configurar_analizadores, "enviar", side_effect=enviar), \
             mock.patch.object(configuracion_p05, "campo_existe", return_value=True), \
             mock.patch("builtins.print"):
            configuracion_p05.configurar("core_de_prueba")
        return enviados

    def test_nunca_crea_ni_modifica_titulo_ni_contenido(self):
        for ruta, cuerpo in self._configurar():
            for comando, definicion in cuerpo.items():
                if comando in ("add-field", "replace-field"):
                    self.assertNotIn(definicion["name"], (CAMPO_TITULO, CAMPO_CONTENIDO))

    def test_no_duplica_copias_existentes(self):
        existentes = [(c["source"], c["dest"]) for c in COPIAS]
        enviados = self._configurar(existentes)
        self.assertFalse([c for _, c in enviados if "add-copy-field" in c])

    def test_falla_si_faltan_titulo_o_contenido(self):
        with mock.patch.object(configuracion_p05, "campo_existe", return_value=False):
            with self.assertRaises(SystemExit):
                configuracion_p05.exigir_campos_origen("core_de_prueba")


class PruebasConfirmacionEnRi(unittest.TestCase):
    def _main(self, argumentos, respuesta=CORE_PRODUCCION):
        with mock.patch.object(configuracion_p05, "exigir_solr"), \
             mock.patch.object(configuracion_p05, "configurar") as configurar, \
             mock.patch("builtins.print"):
            configuracion_p05.main(argumentos, leer_respuesta=lambda _: respuesta)
        return configurar

    def test_ri_sin_bandera_no_aplica(self):
        self.assertFalse(self._main(["--core", "ri"]).called)

    def test_ri_con_bandera_sin_confirmacion_no_aplica(self):
        self.assertFalse(self._main(["--core", "ri", "--aplicar"], respuesta="no").called)

    def test_ri_con_bandera_y_confirmacion_aplica(self):
        self.assertTrue(self._main(["--core", "ri", "--aplicar"]).called)

    def test_core_de_prueba_aplica_sin_confirmacion(self):
        self.assertTrue(self._main([]).called)


if __name__ == "__main__":
    unittest.main()
