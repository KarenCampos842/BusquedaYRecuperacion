"""Pruebas sin Solr del corpus de prueba y de las métricas de comparación.

Ejecutar desde proyecto-final-solr/:  py -m unittest discover -s analisis_es -v
"""

import unittest

from comparar_analizadores import metricas, tabla_markdown
from corpus_prueba import TOTAL_DOCUMENTOS_ESPERADOS, cargar_corpus


class PruebasComparacion(unittest.TestCase):
    def test_corpus_tiene_60_documentos_validos(self):
        self.assertEqual(len(cargar_corpus()), TOTAL_DOCUMENTOS_ESPERADOS)

    def test_metricas(self):
        ids = ["a", "x", "b", "y", "z", "c"]
        self.assertEqual(metricas(ids, {"a", "b", "c", "d"}), {"p_at_5": 0.4, "recall_at_10": 0.75})

    def test_sin_juicios_no_hay_metricas(self):
        self.assertEqual(metricas(["a"], set()), {})

    def test_tabla_escapa_barras_verticales(self):
        variante = {"total": 1, "ganados_vs_ri": [], "perdidos_vs_ri": []}
        fila = {"id": "C1", "consulta": "a|b", "proposito": "x",
                "variantes": {v: variante for v in ("ri", "stop", "stem", "proyecto")}}
        self.assertIn(r"a\|b", tabla_markdown([fila]))


if __name__ == "__main__":
    unittest.main()
