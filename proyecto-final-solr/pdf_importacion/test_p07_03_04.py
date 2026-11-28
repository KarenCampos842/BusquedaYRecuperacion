"""Pruebas locales de P07-03/P07-04; NO hay llamadas a Solr real."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from unittest import TestCase, main, mock

from pdf_importacion.documento_solr import (
    CAMPOS, ErrorDocumentoPDF, convertir_pdf_a_documento, validar_documento_pdf,
)
from pdf_importacion.indexar_pdf_solr import (
    ErrorIndicePDF, importar_documento_pdf, CONFIRMACION, _normalizar_solr,
)

M = Path(__file__).resolve().parent / "muestras"


class TransformacionPDF(TestCase):
    def test_dos_pdf_reales_y_esquema_exactamente_siete_campos(self):
        for nombre, categoria, titulo, term in (
            ("guia_formularios_html.pdf", "HTML", "Formularios HTML", "LinceFormulario2026"),
            ("guia_diseno_css_responsivo.pdf", "CSS", "Responsivo CSS", "FaroRejilla2026"),
        ):
            with self.subTest(nombre=nombre):
                ruta = M / nombre
                doc = convertir_pdf_a_documento(ruta, titulo=titulo, categoria=categoria)
                self.assertEqual(set(doc), CAMPOS)
                self.assertEqual(doc["id"], "pdf:"+hashlib.sha256(ruta.read_bytes()).hexdigest())
                self.assertEqual(doc["tipo_fuente"], "pdf")
                self.assertEqual(doc["fuente"], "PDF local")
                self.assertEqual(doc["idioma"], "es")
                self.assertIn(term, doc["contenido"])
                self.assertNotIn("url", doc)
                self.assertNotIn("tema", doc)
                self.assertNotIn("ruta", doc)
                self.assertEqual(json.loads(json.dumps(doc, ensure_ascii=False)), doc)
                self.assertEqual(doc, convertir_pdf_a_documento(ruta.read_bytes(), titulo=titulo, categoria=categoria))
                validar_documento_pdf(doc)

    def test_categoria_por_defecto_y_titulo_derivado(self):
        doc = convertir_pdf_a_documento(M / "guia_formularios_html.pdf")
        self.assertEqual(doc["categoria"], "General")
        self.assertEqual(doc["titulo"], "guia formularios html")

    def test_bytes_requieren_titulo_o_nombre(self):
        datos = (M / "guia_formularios_html.pdf").read_bytes()
        with self.assertRaises(ErrorDocumentoPDF):
            convertir_pdf_a_documento(datos)
        self.assertEqual(convertir_pdf_a_documento(datos, nombre_archivo="explicación.pdf")["titulo"], "explicación")

    def test_categorias_no_autorizadas(self):
        for cat in ("", "html", "Otros", "Java Script"):
            with self.subTest(cat=cat), self.assertRaises(ErrorDocumentoPDF):
                convertir_pdf_a_documento(M / "guia_formularios_html.pdf", categoria=cat)

    def test_titulos_vacios_ilegibles_y_control(self):
        for titulo in ("", "  ", "--", "Hola\nMundo"):
            with self.subTest(titulo=titulo), self.assertRaises(ErrorDocumentoPDF):
                convertir_pdf_a_documento(M / "guia_formularios_html.pdf", titulo=titulo)

    def test_pdf_invalido_o_sin_capa_texto(self):
        with self.assertRaises(ErrorDocumentoPDF):
            convertir_pdf_a_documento(b"no es pdf", titulo="test")
        with self.assertRaises(ErrorDocumentoPDF):
            convertir_pdf_a_documento(Path(__file__).resolve().parent / "pruebas/fixtures/imagen_sin_texto.pdf")

    def test_documento_que_incluye_url_o_tema_se_rechaza(self):
        doc = convertir_pdf_a_documento(M / "guia_formularios_html.pdf")
        doc["tema"] = "algo"
        with self.assertRaises(ErrorDocumentoPDF):
            validar_documento_pdf(doc)

    def test_sha_no_depende_del_titulo(self):
        a = convertir_pdf_a_documento(M / "guia_formularios_html.pdf", titulo="A")
        b = convertir_pdf_a_documento(M / "guia_formularios_html.pdf", titulo="B")
        self.assertEqual(a["id"], b["id"])


class IndexacionPDF(TestCase):
    def setUp(self):
        self.doc = convertir_pdf_a_documento(M / "guia_formularios_html.pdf", titulo="Formularios", categoria="HTML")

    @mock.patch("pdf_importacion.indexar_pdf_solr._preflight", return_value="nuevo")
    @mock.patch("pdf_importacion.indexar_pdf_solr._json_http")
    def test_simulacion_no_escribe(self, http, preflight):
        self.assertEqual(importar_documento_pdf(self.doc), {"estado": "simulacion", "accion": "crear", "id": self.doc["id"]})
        http.assert_not_called()
        preflight.assert_called_once()

    @mock.patch("pdf_importacion.indexar_pdf_solr._preflight", return_value="existente")
    @mock.patch("pdf_importacion.indexar_pdf_solr._json_http")
    def test_documento_existente_no_se_duplica(self, http, preflight):
        self.assertEqual(importar_documento_pdf(self.doc, aplicar=True, confirmar=CONFIRMACION)["estado"], "ya_indexado")
        http.assert_not_called()

    @mock.patch("pdf_importacion.indexar_pdf_solr._preflight")
    @mock.patch("pdf_importacion.indexar_pdf_solr._json_http")
    def test_escribe_solo_confirmado_y_comprueba_commit(self, http, preflight):
        preflight.side_effect = ["nuevo", "existente"]
        self.assertEqual(importar_documento_pdf(self.doc, aplicar=True, confirmar=CONFIRMACION)["estado"], "indexado_verificado")
        self.assertEqual(http.call_count, 2)
        self.assertEqual(http.call_args_list[0].args[2], [self.doc])
        self.assertEqual(http.call_args_list[1].args[2], {"commit": {"waitSearcher": True}})

    @mock.patch("pdf_importacion.indexar_pdf_solr._preflight")
    @mock.patch("pdf_importacion.indexar_pdf_solr._json_http")
    def test_confirmacion_faltante_detiene_antes_de_solr(self, http, preflight):
        with self.assertRaises(ErrorIndicePDF):
            importar_documento_pdf(self.doc, aplicar=True, confirmar="acepto")
        preflight.assert_not_called()
        http.assert_not_called()

    @mock.patch("pdf_importacion.indexar_pdf_solr._preflight", side_effect=ErrorIndicePDF("faltan MDN"))
    @mock.patch("pdf_importacion.indexar_pdf_solr._json_http")
    def test_preflight_fallido_bloquea_escritura(self, http, preflight):
        with self.assertRaises(ErrorIndicePDF):
            importar_documento_pdf(self.doc, aplicar=True, confirmar=CONFIRMACION)
        http.assert_not_called()

    @mock.patch("pdf_importacion.indexar_pdf_solr._preflight", side_effect=["nuevo", "nuevo"])
    @mock.patch("pdf_importacion.indexar_pdf_solr._json_http")
    def test_post_sin_documento_verificado_da_error(self, http, preflight):
        with self.assertRaises(ErrorIndicePDF):
            importar_documento_pdf(self.doc, aplicar=True, confirmar=CONFIRMACION)
        self.assertEqual(http.call_count, 2)

    def test_normalizacion_solr_monovalor(self):
        self.assertEqual(_normalizar_solr({"categoria": ["CSS"], "id": "123"}), {"categoria": "CSS", "id": "123"})


if __name__ == "__main__":
    main()

class SeguridadPreflight(TestCase):
    @mock.patch("pdf_importacion.indexar_pdf_solr._consultar")
    def test_esquema_exige_texto_es_y_facetas(self, consultar):
        from pdf_importacion.indexar_pdf_solr import _validar_esquema
        nombres = sorted(CAMPOS)
        campos = [{"name": n, "stored": True, "indexed": True,
                   "type": "text_es_proyecto" if n in ("titulo", "contenido") else "string",
                   "docValues": n in ("categoria", "tipo_fuente"), "multiValued": False} for n in nombres]
        consultar.return_value = {"fields": campos}
        _validar_esquema()
        campos[0]["stored"] = False
        with self.assertRaises(ErrorIndicePDF):
            _validar_esquema()

    @mock.patch("pdf_importacion.indexar_pdf_solr._solr_por_ids")
    @mock.patch("pdf_importacion.indexar_pdf_solr._ids_mdn_aprobados")
    def test_los_60_mdn_son_condicion_para_escribir(self, ids, consulta):
        from pdf_importacion.indexar_pdf_solr import _validar_60_mdn
        esperado = {f"https://developer.mozilla.org/es/docs/Web/{cat}/articulo_{i}": cat
                    for cat in ("JavaScript", "HTML", "CSS") for i in range(20)}
        ids.return_value = esperado
        consulta.return_value = [{"id": k, "categoria": v, "tipo_fuente": "web"} for k,v in esperado.items()]
        self.assertEqual(_validar_60_mdn(), esperado)
        consulta.return_value.pop()
        with self.assertRaisesRegex(ErrorIndicePDF, "faltan 1"):
            _validar_60_mdn()

    @mock.patch("pdf_importacion.indexar_pdf_solr._validar_esquema")
    @mock.patch("pdf_importacion.indexar_pdf_solr._validar_60_mdn")
    @mock.patch("pdf_importacion.indexar_pdf_solr._solr_por_ids")
    def test_mismo_id_con_distinto_titulo_se_rechaza(self, consulta, mdn, esquema):
        from pdf_importacion.indexar_pdf_solr import _preflight
        doc = convertir_pdf_a_documento(M / "guia_formularios_html.pdf", titulo="Título A")
        consulta.return_value = [{**doc, "titulo":"Título diferente"}]
        with self.assertRaisesRegex(ErrorIndicePDF, "diferentes"):
            _preflight(doc)

    def test_cli_solo_documento_no_intenta_solr(self):
        import tempfile
        from pdf_importacion.indexar_pdf_solr import main as cli
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "pdf.json"
            with mock.patch("pdf_importacion.indexar_pdf_solr._consultar", side_effect=AssertionError("Solr NO")):
                self.assertEqual(cli([str(M / "guia_formularios_html.pdf"), "--solo-documento", "--json-salida", str(salida)]), 0)
                doc=json.loads(salida.read_text(encoding="utf-8"))
                self.assertEqual(set(doc), CAMPOS)
