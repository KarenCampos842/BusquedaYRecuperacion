"""Pruebas sin Solr de Suggester y SpellCheck (P05).

Ejecutar desde proyecto-final-solr/:  py -m unittest discover -s analisis_es -v
"""

import re
import unittest
from unittest import mock

import configurar_analizadores
import configurar_sugerencias_ortografia as configuracion_p05
from configuracion import CORE_PRODUCCION
from solr_cliente import ErrorSolr
from definiciones_sugerencias import (
    CAMPO_CONTENIDO,
    CAMPO_ORTOGRAFIA,
    CAMPO_SUGERENCIA,
    CAMPO_TITULO,
    CAMPO_VOCABULARIO,
    TIPO_VOCABULARIO,
    CAMPOS_AUXILIARES,
    COMPONENTE_SUGGESTER,
    CONFIGURACION_SOLRCONFIG,
    COPIAS,
    DEFINIDORES_TIPOS_SUGERENCIAS,
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


class EsquemaSimulado:
    """Solr en memoria: responde las lecturas del esquema y registra cada escritura."""

    def __init__(self, tipos=None, campos=None, copias=None):
        self.tipos = {t["name"]: t for t in (tipos or [])}
        self.campos = {CAMPO_TITULO: {"name": CAMPO_TITULO}, CAMPO_CONTENIDO: {"name": CAMPO_CONTENIDO}}
        self.campos.update({c["name"]: c for c in (campos or [])})
        self.copias = list(copias or [])
        self.escrituras = []

    @classmethod
    def completo(cls):
        return cls([d() for d in DEFINIDORES_TIPOS_SUGERENCIAS.values()],
                   [dict(c) for c in CAMPOS_AUXILIARES], [dict(c) for c in COPIAS])

    def obtener(self, core, ruta, parametros=None):
        if ruta == "schema/copyfields":
            return {"copyFields": list(self.copias)}
        coleccion, _, nombre = ruta.rpartition("/")
        almacen, clave = {"schema/fieldtypes": (self.tipos, "fieldType"),
                          "schema/fields": (self.campos, "field")}[coleccion]
        if nombre not in almacen:
            raise ErrorSolr(404, "no existe")
        return {clave: almacen[nombre]}

    def enviar(self, core, ruta, cuerpo, **_):
        self.escrituras.append((ruta, cuerpo))
        for comando, definicion in cuerpo.items():
            if comando in ("add-field-type", "replace-field-type"):
                self.tipos[definicion["name"]] = definicion
            elif comando in ("add-field", "replace-field"):
                self.campos[definicion["name"]] = definicion
            elif comando == "add-copy-field":
                self.copias.append(definicion)
            elif comando == "delete-copy-field":
                par = (definicion["source"], definicion["dest"])
                self.copias = [c for c in self.copias if (c["source"], c["dest"]) != par]
        return {}

    def comandos_de_esquema(self):
        return [comando for ruta, cuerpo in self.escrituras if ruta == "schema" for comando in cuerpo]


def ejecutar_configurar(esquema, core="core_de_prueba", reemplazar=False):
    with mock.patch.object(configuracion_p05, "obtener", side_effect=esquema.obtener), \
         mock.patch.object(configuracion_p05, "enviar", side_effect=esquema.enviar), \
         mock.patch("builtins.print"):
        configuracion_p05.configurar(core, reemplazar=reemplazar)


class PruebasConfigurar(unittest.TestCase):
    def assertSeDetieneSinEnviar(self, esquema, reemplazar=False):
        with self.assertRaises(SystemExit):
            ejecutar_configurar(esquema, reemplazar=reemplazar)
        self.assertEqual(esquema.escrituras, [])

    def test_no_existe_crea_todo_sin_reemplazar(self):
        esquema = EsquemaSimulado()
        ejecutar_configurar(esquema)
        comandos = esquema.comandos_de_esquema()
        self.assertEqual(comandos.count("add-field-type"), len(DEFINIDORES_TIPOS_SUGERENCIAS))
        self.assertEqual(comandos.count("add-field"), len(CAMPOS_AUXILIARES))
        self.assertEqual(comandos.count("add-copy-field"), len(COPIAS))
        self.assertFalse([c for c in comandos if c.startswith(("replace-", "delete-"))])

    def test_existe_y_es_compatible_no_envia_comandos_de_esquema(self):
        esquema = EsquemaSimulado.completo()
        ejecutar_configurar(esquema)
        self.assertEqual(esquema.comandos_de_esquema(), [])
        self.assertTrue(all(ruta == "config" for ruta, _ in esquema.escrituras))

    def test_booleanos_omitidos_o_como_texto_son_compatibles(self):
        esquema = EsquemaSimulado.completo()
        for nombre in (CAMPO_SUGERENCIA, CAMPO_ORTOGRAFIA, CAMPO_VOCABULARIO):
            campo = esquema.campos[nombre]
            for propiedad in ("required", "multiValued", "docValues"):
                campo.pop(propiedad)
            campo["indexed"] = "true"
        ejecutar_configurar(esquema)
        self.assertEqual(esquema.comandos_de_esquema(), [])

    def test_tipo_incompatible_se_detiene_sin_enviar(self):
        esquema = EsquemaSimulado.completo()
        analizador = esquema.tipos[TIPO_VOCABULARIO]["indexAnalyzer"]
        analizador["filters"] = analizador["filters"][:1]
        self.assertSeDetieneSinEnviar(esquema)

    def test_campo_incompatible_se_detiene_sin_enviar(self):
        esquema = EsquemaSimulado.completo()
        esquema.campos[CAMPO_ORTOGRAFIA]["stored"] = True
        self.assertSeDetieneSinEnviar(esquema)

    def test_campo_con_default_se_detiene_sin_enviar(self):
        esquema = EsquemaSimulado.completo()
        esquema.campos[CAMPO_SUGERENCIA]["default"] = "x"
        self.assertSeDetieneSinEnviar(esquema)

    def test_copia_con_max_chars_distinto_se_detiene_sin_enviar(self):
        for valor in (100, "0", 0.0, None):
            with self.subTest(maxChars=valor):
                esquema = EsquemaSimulado.completo()
                esquema.copias[2] = {**esquema.copias[2], "maxChars": valor}
                self.assertSeDetieneSinEnviar(esquema)

    def test_copia_con_max_chars_cero_entero_es_compatible(self):
        esquema = EsquemaSimulado.completo()
        esquema.copias[0] = {**esquema.copias[0], "maxChars": 0}
        ejecutar_configurar(esquema)
        self.assertEqual(esquema.comandos_de_esquema(), [])

    def test_copia_no_autorizada_o_duplicada_se_detiene_incluso_con_reemplazar(self):
        for extra in ({"source": "*", "dest": CAMPO_VOCABULARIO}, dict(COPIAS[0])):
            with self.subTest(regla=extra):
                esquema = EsquemaSimulado.completo()
                esquema.copias.append(extra)
                self.assertSeDetieneSinEnviar(esquema, reemplazar=True)

    def test_segunda_ejecucion_sin_duplicados(self):
        esquema = EsquemaSimulado()
        ejecutar_configurar(esquema)
        escrituras_primera = len(esquema.comandos_de_esquema())
        ejecutar_configurar(esquema)
        self.assertEqual(len(esquema.comandos_de_esquema()), escrituras_primera)
        self.assertEqual(sorted((c["source"], c["dest"]) for c in esquema.copias),
                         sorted((c["source"], c["dest"]) for c in COPIAS))

    def test_reemplazar_corrige_max_chars_en_core_de_prueba(self):
        esquema = EsquemaSimulado.completo()
        esquema.copias[2] = {**esquema.copias[2], "maxChars": 100}
        ejecutar_configurar(esquema, reemplazar=True)
        self.assertEqual(esquema.comandos_de_esquema(), ["delete-copy-field", "add-copy-field"])
        self.assertTrue(all("maxChars" not in c for c in esquema.copias))
        self.assertEqual(len(esquema.copias), len(COPIAS))

    def test_reemplazar_en_ri_se_rechaza_antes_de_leer_o_escribir(self):
        esquema = EsquemaSimulado.completo()
        with self.assertRaises(ValueError):
            ejecutar_configurar(esquema, core=CORE_PRODUCCION, reemplazar=True)
        self.assertEqual(esquema.escrituras, [])

    def test_nunca_crea_ni_modifica_titulo_ni_contenido(self):
        esquema = EsquemaSimulado()
        ejecutar_configurar(esquema)
        for _, cuerpo in esquema.escrituras:
            for comando, definicion in cuerpo.items():
                if comando in ("add-field", "replace-field"):
                    self.assertNotIn(definicion["name"], (CAMPO_TITULO, CAMPO_CONTENIDO))

    def test_falla_si_faltan_titulo_o_contenido(self):
        with mock.patch.object(configuracion_p05, "campo_existe", return_value=False):
            with self.assertRaises(SystemExit):
                configuracion_p05.exigir_campos_origen("core_de_prueba")


class PruebasConfirmacionEnRi(unittest.TestCase):
    def _main(self, argumentos, respuesta=CORE_PRODUCCION):
        with mock.patch.object(configuracion_p05, "exigir_solr"), \
             mock.patch.object(configuracion_p05, "exigir_campos_origen"), \
             mock.patch.object(configuracion_p05, "describir_cambios", return_value={}), \
             mock.patch.object(configuracion_p05, "configurar") as configurar, \
             mock.patch("builtins.print"):
            configuracion_p05.main(argumentos, leer_respuesta=lambda _: respuesta)
        return configurar

    def test_reemplazar_con_core_ri_lo_rechaza_argparse(self):
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            configuracion_p05.leer_argumentos(["--core", "ri", "--reemplazar"])
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            self._main(["--core", "ri", "--aplicar", "--reemplazar"])

    def test_reemplazar_en_core_de_prueba_se_pasa_a_configurar(self):
        configurar = self._main(["--reemplazar"])
        configurar.assert_called_once_with(configuracion_p05.CORE_SUGERENCIAS, reemplazar=True)

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
