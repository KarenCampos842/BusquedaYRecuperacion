"""Pruebas sin Solr de validar_espanol_final.py (P03-10, P08-03, P08-04).

Ejecutar desde proyecto-final-solr/:  py -m unittest discover -s analisis_es -v
"""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import validar_espanol_final as validacion
from configuracion import CORE_PRODUCCION, CORE_PRUEBA
from corpus_prueba import cargar_corpus
from definiciones_tipos import TIPO_PROYECTO

CORES_NO_PREPARABLES = (CORE_PRODUCCION, CORE_PRUEBA, "core_inventado")
CORES_SIN_EVIDENCIA_FINAL = (validacion.CORE_VALIDACION, CORE_PRUEBA, "core_inventado")
INSTANTE = datetime(2026, 11, 27, 19, 30, 0, tzinfo=timezone.utc)


def documentos(*ids):
    return [{"id": i, "titulo": f"Título {i}"} for i in ids]


class PruebasArgumentos(unittest.TestCase):
    def rechaza(self, argumentos):
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            validacion.leer_argumentos(argumentos)

    def test_preparar_solo_con_core_de_validacion(self):
        for core in CORES_NO_PREPARABLES:
            with self.subTest(core=core):
                self.rechaza(["--core", core, "--preparar-core-de-prueba"])
        self.assertTrue(validacion.leer_argumentos(["--preparar-core-de-prueba"]).preparar_core_de_prueba)

    def test_evidencia_final_solo_con_ri(self):
        for core in CORES_SIN_EVIDENCIA_FINAL:
            with self.subTest(core=core):
                self.rechaza(["--core", core, "--evidencia-final"])
        self.assertTrue(validacion.leer_argumentos(["--core", "ri", "--evidencia-final"]).evidencia_final)

    def test_preparar_core_rechaza_otros_cores_sin_escribir(self):
        for core in CORES_NO_PREPARABLES:
            with self.subTest(core=core), \
                 mock.patch.object(validacion, "configurar_tipos") as configurar, \
                 mock.patch.object(validacion, "reindexar_core_de_prueba") as reindexar, \
                 self.assertRaises(ValueError):
                validacion.preparar_core_de_prueba(core)
            configurar.assert_not_called()
            reindexar.assert_not_called()


class PruebasEvidenciaFinal(unittest.TestCase):
    def ejecutar_main(self, argumentos, respuesta):
        with mock.patch.object(validacion, "exigir_solr") as exigir_solr, \
             mock.patch.object(validacion, "exigir_carpeta_nueva"), \
             mock.patch.object(validacion, "exigir_core_listo", return_value=60) as core_listo, \
             mock.patch.object(validacion, "construir_encabezado", return_value={}) as encabezado, \
             mock.patch.object(validacion, "leer_casos", return_value=[]), \
             mock.patch.object(validacion, "guardar", return_value=("j", "t")), \
             mock.patch.object(validacion, "tabla_markdown", return_value=""), \
             mock.patch("builtins.print"):
            validacion.main(argumentos, leer_respuesta=lambda _: respuesta)
        return exigir_solr, encabezado, core_listo

    def test_sin_confirmacion_no_conecta_ni_genera(self):
        with mock.patch.object(validacion, "exigir_solr") as exigir_solr, \
             mock.patch("builtins.print"), self.assertRaises(SystemExit):
            validacion.main(["--core", "ri", "--evidencia-final"], leer_respuesta=lambda _: "ri")
        exigir_solr.assert_not_called()

    def test_con_confirmacion_marca_evidencia_final_y_exige_corpus(self):
        _, encabezado, core_listo = self.ejecutar_main(["--core", "ri", "--evidencia-final"],
                                                       respuesta=validacion.CONFIRMACION_EVIDENCIA_FINAL)
        self.assertEqual(encabezado.call_args.args[:3], ("ri", 60, True))
        core_listo.assert_called_once_with("ri", exigir_corpus=True)

    def test_prueba_local_no_exige_corpus_y_es_la_etiqueta_por_defecto(self):
        for argumentos in (["--core", "ri"], []):
            with self.subTest(argumentos=argumentos):
                _, encabezado, core_listo = self.ejecutar_main(argumentos, respuesta="")
                self.assertFalse(encabezado.call_args.args[2])
                self.assertFalse(core_listo.call_args.kwargs["exigir_corpus"])
        with mock.patch.object(validacion, "huella_sinonimos", return_value="x"):
            self.assertEqual(validacion.construir_encabezado("ri", 60, False, INSTANTE)["etiqueta"],
                             validacion.ETIQUETA_PRUEBA_LOCAL)

    def test_carpetas_separadas(self):
        self.assertEqual(validacion.directorio_salida(False, "ri", INSTANTE), validacion.DIRECTORIO_PRUEBA_LOCAL)
        self.assertEqual(validacion.directorio_salida(True, "ri", INSTANTE).name, "2026-11-27T193000Z_ri")


class IndiceSimulado:
    """Solr en memoria para exigir_core_listo: campos, conteo y consulta {!terms f=id}."""

    def __init__(self, documentos, tipo_campos=TIPO_PROYECTO):
        self.documentos = {d["id"]: d for d in documentos}
        self.tipo_campos = tipo_campos

    def obtener(self, _core, ruta, parametros=None):
        if ruta.startswith("schema/fields/"):
            return {"field": {"type": self.tipo_campos}}
        consulta = parametros["q"]
        if consulta == "*:*":
            return {"response": {"numFound": len(self.documentos), "docs": []}}
        ids = consulta.removeprefix("{!terms f=id}").split(",")
        return {"response": {"docs": [self.documentos[i] for i in ids if i in self.documentos]}}


def indice_mdn(*, quitar=0, extras=(), cambiar=None):
    """Índice con los 60 MDN aprobados; `cambiar` = {posición: {campo: valor}}."""
    documentos = [{"id": d["id"], "categoria": d["categoria"], "tipo_fuente": d["tipo_fuente"]}
                  for d in cargar_corpus()]
    for posicion, valores in (cambiar or {}).items():
        documentos[posicion] = {**documentos[posicion], **valores}
    return documentos[quitar:] + list(extras)


PDF_EXTRA = [{"id": f"pdf-{n}", "categoria": "General", "tipo_fuente": "pdf"} for n in (1, 2)]


class PruebasCorpusAprobado(unittest.TestCase):
    def core_listo(self, documentos, exigir_corpus=True, tipo_campos=TIPO_PROYECTO):
        indice = IndiceSimulado(documentos, tipo_campos)
        with mock.patch.object(validacion, "core_existe", return_value=True), \
             mock.patch.object(validacion, "obtener", side_effect=indice.obtener):
            return validacion.exigir_core_listo("ri", exigir_corpus=exigir_corpus)

    def rechaza(self, documentos, *fragmentos, **opciones):
        with self.assertRaises(SystemExit) as contexto:
            self.core_listo(documentos, **opciones)
        for fragmento in fragmentos:
            self.assertIn(fragmento, str(contexto.exception))

    def test_a_los_60_mdn_correctos_se_aceptan(self):
        self.assertEqual(self.core_listo(indice_mdn()), 60)

    def test_b_60_mdn_mas_dos_pdf_se_aceptan(self):
        self.assertEqual(self.core_listo(indice_mdn(extras=PDF_EXTRA)), 62)

    def test_c_falta_un_id_aprobado_aunque_haya_otros_documentos(self):
        faltante = cargar_corpus()[0]["id"]
        self.rechaza(indice_mdn(quitar=1, extras=PDF_EXTRA), f"falta en el índice: {faltante}",
                     "conteo por categoría")

    def test_c_59_mdn_se_rechaza(self):
        self.rechaza(indice_mdn(quitar=1), "falta en el índice")

    def test_d_categorias_que_no_coinciden_se_rechazan(self):
        aprobados = cargar_corpus()
        css = next(i for i, d in enumerate(aprobados) if d["categoria"] == "CSS")
        self.rechaza(indice_mdn(cambiar={css: {"categoria": "JavaScript"}}),
                     "categoría incorrecta", "'JavaScript': 21", "'CSS': 19")

    def test_d_tipo_fuente_distinto_de_web_se_rechaza(self):
        self.rechaza(indice_mdn(cambiar={0: {"tipo_fuente": "pdf"}}), "tipo_fuente incorrecto")

    def test_e_indice_vacio_y_tipo_incorrecto_siguen_rechazandose(self):
        for exigir_corpus in (True, False):
            with self.subTest(exigir_corpus=exigir_corpus):
                self.rechaza([], "no tiene documentos", exigir_corpus=exigir_corpus)
                self.rechaza(indice_mdn(), "no usan", exigir_corpus=exigir_corpus, tipo_campos="text_es_ri")

    def test_prueba_local_no_consulta_los_ids_aprobados(self):
        self.assertEqual(self.core_listo(indice_mdn(quitar=10), exigir_corpus=False), 50)

    def test_rechazo_en_main_no_escribe_nada(self):
        with tempfile.TemporaryDirectory() as temporal:
            indice = IndiceSimulado(indice_mdn(quitar=1))
            with mock.patch.object(validacion, "DIRECTORIO_EVIDENCIA_FINAL", Path(temporal)), \
                 mock.patch.object(validacion, "exigir_solr"), \
                 mock.patch.object(validacion, "core_existe", return_value=True), \
                 mock.patch.object(validacion, "obtener", side_effect=indice.obtener), \
                 mock.patch("builtins.print"), self.assertRaises(SystemExit):
                validacion.main(["--core", "ri", "--evidencia-final"],
                                leer_respuesta=lambda _: validacion.CONFIRMACION_EVIDENCIA_FINAL)
            self.assertEqual(list(Path(temporal).iterdir()), [])


class PruebasCarpetasDeEvidencia(unittest.TestCase):
    ENCABEZADO = {"etiqueta": validacion.ETIQUETA_EVIDENCIA_FINAL, "core": "ri", "documentos": 62,
                  "huella_sinonimos": "h", "consulta": "q"}

    def guardar(self, directorio, instante, evidencia_final=True):
        encabezado = {**self.ENCABEZADO, "fecha_utc": instante.strftime(validacion.FORMATO_FECHA)}
        with mock.patch.object(validacion, "DIRECTORIO_EVIDENCIA_FINAL", directorio):
            return validacion.guardar(encabezado, [], evidencia_final, instante)

    def test_segunda_ejecucion_en_otro_instante_no_sobrescribe(self):
        with tempfile.TemporaryDirectory() as temporal:
            directorio = Path(temporal)
            primera, _ = self.guardar(directorio, INSTANTE)
            contenido_primera = primera.read_text(encoding="utf-8")
            segunda, _ = self.guardar(directorio, INSTANTE + timedelta(minutes=5))
            self.assertNotEqual(primera.parent, segunda.parent)
            self.assertEqual(primera.read_text(encoding="utf-8"), contenido_primera)
            lineas = (directorio / validacion.NOMBRE_INDICE_EVIDENCIAS).read_text(encoding="utf-8").splitlines()
            filas = [linea for linea in lineas if linea.startswith("| 2026")]
            self.assertEqual(len(filas), 2)
            self.assertIn("2026-11-27T193000Z_ri", filas[0])
            self.assertIn("2026-11-27T193500Z_ri", filas[1])
            self.assertIn("| 62 |", filas[1])

    def test_carpeta_existente_se_rechaza_sin_modificar_nada(self):
        with tempfile.TemporaryDirectory() as temporal:
            directorio = Path(temporal)
            primera, _ = self.guardar(directorio, INSTANTE)
            indice = directorio / validacion.NOMBRE_INDICE_EVIDENCIAS
            antes = (primera.read_text(encoding="utf-8"), indice.read_text(encoding="utf-8"))
            with self.assertRaises(SystemExit):
                self.guardar(directorio, INSTANTE)
            self.assertEqual((primera.read_text(encoding="utf-8"), indice.read_text(encoding="utf-8")), antes)
            with mock.patch.object(validacion, "DIRECTORIO_EVIDENCIA_FINAL", directorio), \
                 self.assertRaises(SystemExit):
                validacion.exigir_carpeta_nueva(validacion.carpeta_evidencia("ri", INSTANTE))

    def test_prueba_local_se_sobrescribe_y_no_usa_indice(self):
        with tempfile.TemporaryDirectory() as temporal:
            directorio = Path(temporal)
            with mock.patch.object(validacion, "DIRECTORIO_PRUEBA_LOCAL", directorio / "prueba_local"):
                primera, _ = self.guardar(directorio, INSTANTE, evidencia_final=False)
                segunda, _ = self.guardar(directorio, INSTANTE, evidencia_final=False)
            self.assertEqual(primera, segunda)
            self.assertFalse((directorio / validacion.NOMBRE_INDICE_EVIDENCIAS).exists())


class PruebasCasos(unittest.TestCase):
    def test_casos_cubren_los_criterios_de_p03_10_y_p08(self):
        casos = validacion.leer_casos()
        criterios = {c["criterio"] for c in casos}
        self.assertTrue({"mayusculas_acentos", "stopwords", "morfologia", "morfologia_protegida",
                         validacion.CRITERIO_SINONIMOS} <= criterios)
        self.assertGreaterEqual(sum(c["criterio"] == validacion.CRITERIO_SINONIMOS for c in casos), 2)
        self.assertEqual(len({c["id"] for c in casos}), len(casos))

    def test_sin_expansion_usa_term_en_titulo_y_contenido(self):
        parametros = validacion.parametros_sin_expansion(["rellen"])
        self.assertEqual(parametros["q"], "{!bool should=$t0 should=$t1}")
        self.assertEqual(parametros["t0"], "{!term f=titulo}rellen")
        self.assertEqual(parametros["t1"], "{!term f=contenido}rellen")

    def test_consulta_real_es_la_de_la_api_con_orden_estable(self):
        parametros = validacion.parametros_consulta_real("x")
        self.assertEqual(parametros["qf"], f"titulo^{validacion.PESO_TITULO} contenido")
        self.assertEqual(parametros["sort"], "score desc,id asc")

    def test_sinonimos_calcula_ids_nuevos_por_expansion(self):
        respuestas = {"relleno": documentos("d1", "d2", "d3"), "padding": documentos("d1", "d2", "d3")}

        def buscar(_core, parametros):
            if parametros.get("defType") == "edismax":
                return respuestas[parametros["q"]]
            return documentos("d1") if "rellen" in parametros["t0"] else documentos("d2", "d3")

        caso = {"id": "Y01", "criterio": validacion.CRITERIO_SINONIMOS,
                "consulta_a": "relleno", "consulta_b": "padding", "descripcion": ""}
        with mock.patch.object(validacion, "buscar", side_effect=buscar), \
             mock.patch.object(validacion, "tokens", side_effect=lambda _c, t, _f: [t[:6]]):
            resultado = validacion.ejecutar_caso("core", caso)
        self.assertEqual(resultado["a"]["ids_nuevos_por_expansion"], ["d2", "d3"])
        self.assertEqual(resultado["b"]["ids_nuevos_por_expansion"], ["d1"])
        self.assertTrue(resultado["mismos_documentos"])

    def test_caso_no_sinonimo_no_consulta_sin_expansion(self):
        caso = {"id": "A01", "criterio": "mayusculas_acentos",
                "consulta_a": "función", "consulta_b": "FUNCION", "descripcion": ""}
        with mock.patch.object(validacion, "buscar", side_effect=[documentos("d1"), documentos("d2")]) as buscar, \
             mock.patch.object(validacion, "tokens", return_value=["funcion"]):
            resultado = validacion.ejecutar_caso("core", caso)
        self.assertEqual(buscar.call_count, 2)
        self.assertFalse(resultado["mismos_documentos"])
        self.assertEqual((resultado["solo_en_a"], resultado["solo_en_b"]), (["d1"], ["d2"]))

    def test_tabla_estable_y_sin_metricas(self):
        observacion = {"consulta": "a|b", "tokens_consulta": ["a"], "total": 1, "ids": ["x"]}
        resultado = {"id": "A01", "criterio": "stopwords", "a": observacion, "b": observacion,
                     "mismos_documentos": True}
        encabezado = {"etiqueta": validacion.ETIQUETA_PRUEBA_LOCAL, "core": "c", "documentos": 1,
                      "huella_sinonimos": "h", "consulta": "q"}
        tabla = validacion.tabla_markdown(encabezado, [resultado])
        self.assertEqual(tabla, validacion.tabla_markdown(encabezado, [resultado]))
        self.assertIn("PRUEBA LOCAL", tabla)
        self.assertIn(r"a\|b", tabla)
        self.assertNotIn("P@5", tabla)

    def test_id_corto_quita_prefijo_mdn(self):
        self.assertEqual(validacion.id_corto(validacion.PREFIJO_URL_MDN + "CSS"), "CSS")

    def test_el_script_no_importa_enviar(self):
        self.assertFalse(hasattr(validacion, "enviar"))


if __name__ == "__main__":
    unittest.main()
