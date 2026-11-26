"""Pruebas sin Solr de las definiciones de tipos.

Ejecutar desde proyecto-final-solr/:  py -m unittest discover -s analisis_es -v
"""

import unittest

from configuracion import TIPO_CONTROL
from configurar_analizadores import agregar_o_reemplazar
from definiciones_tipos import (
    DEFINIDORES_TIPOS,
    definir_text_es_proyecto,
    definir_text_es_stem,
    definir_text_es_stop,
    leer_text_es_ri_del_kit,
)


def clases(analizador: dict) -> list[str]:
    return [filtro["class"].removeprefix("solr.") for filtro in analizador["filters"]]


class PruebasTipoControl(unittest.TestCase):
    def test_lee_text_es_ri_del_kit(self):
        tipo = leer_text_es_ri_del_kit()
        self.assertEqual(tipo["name"], TIPO_CONTROL)
        self.assertEqual(clases(tipo["indexAnalyzer"]), ["LowerCaseFilterFactory", "ASCIIFoldingFilterFactory"])

    def test_no_se_define_ni_reemplaza_el_control(self):
        self.assertNotIn(TIPO_CONTROL, DEFINIDORES_TIPOS)
        with self.assertRaises(ValueError):
            agregar_o_reemplazar("core_inexistente", "field-type", {"name": TIPO_CONTROL})


class PruebasTiposAlternativos(unittest.TestCase):
    def test_stop_es_control_mas_palabras_vacias(self):
        control = clases(leer_text_es_ri_del_kit()["indexAnalyzer"])
        self.assertEqual(clases(definir_text_es_stop()["indexAnalyzer"]), control + ["ManagedStopFilterFactory"])

    def test_stem_termina_en_stemming_ligero(self):
        self.assertEqual(clases(definir_text_es_stem()["indexAnalyzer"])[-1], "SpanishLightStemFilterFactory")

    def test_proyecto_orden_de_indice(self):
        self.assertEqual(clases(definir_text_es_proyecto()["indexAnalyzer"]), [
            "LowerCaseFilterFactory", "ASCIIFoldingFilterFactory", "ManagedStopFilterFactory",
            "KeywordMarkerFilterFactory", "SpanishLightStemFilterFactory",
        ])

    def test_proyecto_sinonimos_solo_en_consulta(self):
        tipo = definir_text_es_proyecto()
        self.assertNotIn("ManagedSynonymGraphFilterFactory", clases(tipo["indexAnalyzer"]))
        consulta = clases(tipo["queryAnalyzer"])
        self.assertLess(consulta.index("ManagedSynonymGraphFilterFactory"), consulta.index("SpanishLightStemFilterFactory"))

    def test_protegidos_antes_del_stemming(self):
        consulta = clases(definir_text_es_proyecto()["queryAnalyzer"])
        self.assertLess(consulta.index("KeywordMarkerFilterFactory"), consulta.index("SpanishLightStemFilterFactory"))


if __name__ == "__main__":
    unittest.main()
