"""Pruebas sin Solr de aplicar_en_ri.py.

Ejecutar desde proyecto-final-solr/:  py -m unittest discover -s analisis_es -v
"""

import unittest
from unittest import mock

import aplicar_en_ri
import configurar_analizadores
from configuracion import CORE_PRODUCCION, TIPO_CONTROL
from definiciones_tipos import TIPO_PROYECTO
from verificar_linea_base import ESTADO_AUSENTE, ESTADO_DISTINTO, ESTADO_IDENTICO

COMANDOS_DE_TIPO = {"add-field-type", "replace-field-type"}


def ejecutar_aplicar(estados: list[str], enviados: list | None = None) -> list[dict]:
    """Ejecuta aplicar() con Solr simulado y devuelve los comandos enviados a la Schema API."""
    enviados = [] if enviados is None else enviados

    def enviar_falso(core, ruta, cuerpo, **_):
        if ruta == "schema":
            enviados.append(cuerpo)
        return {}

    with mock.patch.object(aplicar_en_ri, "estado_tipo_en_produccion", side_effect=estados), \
         mock.patch.object(configurar_analizadores, "enviar", side_effect=enviar_falso), \
         mock.patch.object(configurar_analizadores, "preparar_core"), \
         mock.patch.object(configurar_analizadores, "sincronizar_recursos"), \
         mock.patch("builtins.print"):
        aplicar_en_ri.aplicar()
    return enviados


def nombres_de_tipos(comandos: list[dict]) -> list[str]:
    return [definicion["name"] for comando in comandos for definicion in comando.values()]


class PruebasAplicar(unittest.TestCase):
    def test_si_falta_text_es_ri_lo_crea_del_kit_antes_que_text_es_proyecto(self):
        comandos = ejecutar_aplicar([ESTADO_AUSENTE, ESTADO_IDENTICO, ESTADO_IDENTICO])
        self.assertEqual(nombres_de_tipos(comandos), [TIPO_CONTROL, TIPO_PROYECTO])
        self.assertEqual(comandos[0], {"add-field-type": configurar_analizadores.leer_text_es_ri_del_kit()})

    def test_si_text_es_ri_existe_no_lo_toca(self):
        comandos = ejecutar_aplicar([ESTADO_IDENTICO, ESTADO_IDENTICO])
        self.assertEqual(nombres_de_tipos(comandos), [TIPO_PROYECTO])

    def test_si_text_es_ri_es_distinto_se_detiene_sin_enviar_nada(self):
        enviados = []
        with self.assertRaises(SystemExit):
            ejecutar_aplicar([ESTADO_DISTINTO], enviados)
        self.assertEqual(enviados, [])

    def test_solo_envia_tipos_de_campo_nunca_campos(self):
        comandos = ejecutar_aplicar([ESTADO_AUSENTE, ESTADO_IDENTICO, ESTADO_IDENTICO])
        self.assertTrue(all(set(comando) <= COMANDOS_DE_TIPO for comando in comandos))

    def test_alerta_si_el_control_cambia_al_final(self):
        with self.assertRaises(SystemExit):
            ejecutar_aplicar([ESTADO_IDENTICO, ESTADO_DISTINTO])


class PruebasModoDePrueba(unittest.TestCase):
    def test_describe_creacion_del_control_cuando_falta(self):
        cambios = aplicar_en_ri.describir_cambios(ESTADO_AUSENTE)
        self.assertIn("se crea", cambios[TIPO_CONTROL])
        self.assertEqual(cambios["definicion_" + TIPO_CONTROL]["name"], TIPO_CONTROL)

    def test_no_incluye_definicion_del_control_cuando_existe(self):
        cambios = aplicar_en_ri.describir_cambios(ESTADO_IDENTICO)
        self.assertIn("sin cambios", cambios[TIPO_CONTROL])
        self.assertNotIn("definicion_" + TIPO_CONTROL, cambios)

    def _main(self, argumentos, estado=ESTADO_AUSENTE, respuesta=CORE_PRODUCCION):
        with mock.patch.object(aplicar_en_ri, "exigir_solr"), \
             mock.patch.object(aplicar_en_ri, "estado_tipo_en_produccion", return_value=estado), \
             mock.patch.object(aplicar_en_ri, "estado_actual", return_value={}), \
             mock.patch.object(aplicar_en_ri, "aplicar") as aplicar, \
             mock.patch("builtins.print"):
            aplicar_en_ri.main(argumentos, leer_respuesta=lambda _: respuesta)
        return aplicar

    def test_sin_bandera_no_aplica(self):
        self.assertFalse(self._main([]).called)

    def test_con_bandera_y_sin_confirmacion_no_aplica(self):
        self.assertFalse(self._main(["--aplicar"], respuesta="no").called)

    def test_con_bandera_y_confirmacion_aplica(self):
        self.assertTrue(self._main(["--aplicar"]).called)

    def test_control_distinto_bloquea_aunque_se_confirme(self):
        self.assertFalse(self._main(["--aplicar"], estado=ESTADO_DISTINTO).called)


class PruebasConfirmacion(unittest.TestCase):
    def test_acepta_solo_el_nombre_exacto_del_core(self):
        self.assertTrue(aplicar_en_ri.confirmado(lambda _: " ri "))
        for respuesta in ("", "si", "RI", "ri_analisis_es"):
            self.assertFalse(aplicar_en_ri.confirmado(lambda _, r=respuesta: r))


if __name__ == "__main__":
    unittest.main()
