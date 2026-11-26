"""Pruebas sin Solr de aplicar_en_ri.py (modo de prueba y confirmación).

Ejecutar desde proyecto-final-solr/:  py -m unittest discover -s analisis_es -v
"""

import unittest
from unittest import mock

import aplicar_en_ri
from configuracion import TIPO_CONTROL
from definiciones_tipos import TIPO_PROYECTO


class PruebasConfirmacion(unittest.TestCase):
    def test_acepta_solo_el_nombre_exacto_del_core(self):
        self.assertTrue(aplicar_en_ri.confirmado(lambda _: " ri "))
        for respuesta in ("", "si", "RI", "ri_analisis_es"):
            self.assertFalse(aplicar_en_ri.confirmado(lambda _, r=respuesta: r))


class PruebasModoDePrueba(unittest.TestCase):
    def test_describe_solo_text_es_proyecto(self):
        cambios = aplicar_en_ri.describir_cambios()
        self.assertEqual(cambios["tipo"]["name"], TIPO_PROYECTO)
        self.assertIn(TIPO_CONTROL, cambios["no_se_modifica"])

    def _ejecutar(self, argumentos, respuesta="ri"):
        with mock.patch.object(aplicar_en_ri, "exigir_solr"), \
             mock.patch.object(aplicar_en_ri, "estado_actual", return_value={}), \
             mock.patch.object(aplicar_en_ri, "aplicar") as aplicar, \
             mock.patch("builtins.print"):
            aplicar_en_ri.main(argumentos, leer_respuesta=lambda _: respuesta)
        return aplicar

    def test_sin_bandera_no_aplica(self):
        self.assertFalse(self._ejecutar([]).called)

    def test_con_bandera_y_sin_confirmacion_no_aplica(self):
        self.assertFalse(self._ejecutar(["--aplicar"], respuesta="no").called)

    def test_con_bandera_y_confirmacion_aplica(self):
        self.assertTrue(self._ejecutar(["--aplicar"]).called)


if __name__ == "__main__":
    unittest.main()
