"""Pruebas sin red, Docker, Solr ni OCR para P07-02."""

from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader, PdfWriter

from pdf_importacion.extractor_pdf import ErrorExtraccionPDF, extraer_texto_pdf, main

ROOT = Path(__file__).resolve().parent
MUESTRAS = ROOT / "muestras"


class ExtractorPDFTests(unittest.TestCase):
    def test_los_dos_pdf_de_muestra_son_texto_seleccionable(self):
        casos = (
            ("guia_formularios_html.pdf", "LinceFormulario2026", "Validación", "HTML"),
            ("guia_diseno_css_responsivo.pdf", "FaroRejilla2026", "cuadrícula", "CSS"),
        )
        for archivo, etiqueta, palabra_acentuada, categoria in casos:
            with self.subTest(pdf=archivo):
                ruta = MUESTRAS / archivo
                self.assertEqual(len(PdfReader(ruta).pages), 2)
                texto_ruta = extraer_texto_pdf(ruta)
                texto_bytes = extraer_texto_pdf(ruta.read_bytes())
                self.assertEqual(texto_ruta, texto_bytes)
                self.assertIn(etiqueta, texto_ruta)
                self.assertIn(palabra_acentuada, texto_ruta)
                self.assertIn(categoria, texto_ruta)
                self.assertIn(etiqueta, PdfReader(ruta).pages[1].extract_text())
                self.assertGreater(len(texto_ruta), 1000)
                self.assertTrue(texto_ruta.encode("utf-8"))

    def test_pdf_con_imagen_pero_sin_capa_textual_no_es_aceptado(self):
        ruta = ROOT / "pruebas" / "fixtures" / "imagen_sin_texto.pdf"
        self.assertEqual(len(PdfReader(ruta).pages), 1)
        self.assertTrue(PdfReader(ruta).pages[0].images)
        with self.assertRaisesRegex(ErrorExtraccionPDF, "no contiene texto seleccionable"):
            extraer_texto_pdf(ruta)

    def test_pdf_vacio_sin_texto_no_es_aceptado(self):
        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        memoria = BytesIO()
        writer.write(memoria)
        with self.assertRaisesRegex(ErrorExtraccionPDF, "no contiene texto seleccionable"):
            extraer_texto_pdf(memoria.getvalue())

    def test_bytes_invalidos_y_no_pdf(self):
        for datos in (b"", b"hola mundo", b"%PDF-1.7\ncontenido roto"):
            with self.subTest(datos=datos), self.assertRaises(ErrorExtraccionPDF):
                extraer_texto_pdf(datos)

    def test_ruta_inexistente(self):
        with self.assertRaisesRegex(ErrorExtraccionPDF, "No existe"):
            extraer_texto_pdf(MUESTRAS / "inexistente.pdf")

    def test_pdf_protegido_se_rechaza(self):
        writer = PdfWriter()
        writer.add_page(PdfReader(MUESTRAS / "guia_formularios_html.pdf").pages[0])
        writer.encrypt("clave")
        memoria = BytesIO()
        writer.write(memoria)
        with self.assertRaisesRegex(ErrorExtraccionPDF, "cifrado"):
            extraer_texto_pdf(memoria.getvalue())

    def test_entrada_de_tipo_no_soportado(self):
        with self.assertRaises(TypeError):
            extraer_texto_pdf(123)  # type: ignore[arg-type]

    def test_cli_guarda_texto_utf8_y_no_sobrescribe(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "resultado.txt"
            pdf = MUESTRAS / "guia_formularios_html.pdf"
            self.assertEqual(main([str(pdf), "--salida", str(ruta)]), 0)
            self.assertIn("LinceFormulario2026", ruta.read_text(encoding="utf-8"))
            original = ruta.read_bytes()
            self.assertEqual(main([str(pdf), "--salida", str(ruta)]), 1)
            self.assertEqual(ruta.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
