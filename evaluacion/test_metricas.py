"""Casos independientes para las decisiones de evaluación de la actividad."""
import unittest

from metricas import evaluar_ranking


class MetricasTest(unittest.TestCase):
    def test_relevante_ausente_cuenta_en_denominador(self):
        resultado = evaluar_ranking(["x", "a", "b"], {"a", "b", "c"}, set("abcxyz"))
        self.assertEqual([resultado[k] for k in ("TP", "FP", "FN", "TN")], [2, 1, 1, 2])
        self.assertAlmostEqual(resultado["AP"], 7 / 18)
        self.assertAlmostEqual(resultado["accuracy"], 4 / 6)
        self.assertEqual(resultado["interpolada"][-1], 0)

    def test_sin_resultados(self):
        resultado = evaluar_ranking([], {"a"}, {"a", "b"})
        self.assertEqual(resultado["precision"], 0)
        self.assertEqual(resultado["recall"], 0)
        self.assertEqual(resultado["AP"], 0)
        self.assertEqual(resultado["interpolada"], [0] * 11)
        self.assertEqual(resultado["accuracy"], 0.5)

    def test_orden_cambia_ap_y_conserva_contingencia(self):
        primero = evaluar_ranking(["a", "x"], {"a"}, {"a", "x"})
        segundo = evaluar_ranking(["x", "a"], {"a"}, {"a", "x"})
        self.assertEqual(primero["AP"], 1)
        self.assertEqual(segundo["AP"], 0.5)
        for clave in ("TP", "FP", "FN", "TN", "precision", "recall", "accuracy"):
            self.assertEqual(primero[clave], segundo[clave])

    def test_rechaza_resultados_invalidos(self):
        for ranking in (["a", "a"], ["desconocido"]):
            with self.assertRaises(ValueError):
                evaluar_ranking(ranking, {"a"}, {"a", "b"})


if __name__ == "__main__":
    unittest.main()
