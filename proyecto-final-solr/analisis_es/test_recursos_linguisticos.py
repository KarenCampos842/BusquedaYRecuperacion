"""Pruebas sin Solr de los recursos lingüísticos.

Ejecutar desde proyecto-final-solr/:  py -m unittest discover -s analisis_es -v
"""

import re
import tempfile
import unittest
from pathlib import Path

from recursos_linguisticos import (
    leer_grupos_sinonimos,
    leer_stopwords,
    leer_terminos_protegidos,
    normalizar_termino,
    patron_terminos_protegidos,
)

# Palabras que nunca deben ser vacías: cambian el sentido o son del dominio.
PALABRAS_QUE_NO_SON_VACIAS = {
    "no", "sin", "estado", "valor", "tipo", "nombre", "uno", "dos",
    "b", "i", "p", "q", "s", "u",
    "javascript", "html", "css", "array", "funcion", "elemento", "selector",
}


class PruebasNormalizacion(unittest.TestCase):
    def test_quita_acentos_y_mayusculas(self):
        self.assertEqual(normalizar_termino("  FUNCIÓN "), "funcion")

    def test_conserva_la_enie(self):
        # NFKD separa la tilde de la ñ igual que ASCIIFolding de Solr.
        self.assertEqual(normalizar_termino("Diseño"), "diseno")

    def test_compacta_espacios_internos(self):
        self.assertEqual(normalizar_termino("expresión   regular"), "expresion regular")


class PruebasStopwords(unittest.TestCase):
    def setUp(self):
        self.stopwords = set(leer_stopwords())

    def test_lista_no_vacia(self):
        self.assertGreater(len(self.stopwords), 50)

    def test_incluye_forma_original_y_plegada(self):
        self.assertIn("más", self.stopwords)
        self.assertIn("mas", self.stopwords)

    def test_no_elimina_terminos_del_dominio(self):
        self.assertFalse(self.stopwords & PALABRAS_QUE_NO_SON_VACIAS)


class PruebasTerminosProtegidos(unittest.TestCase):
    def setUp(self):
        self.protegidos = leer_terminos_protegidos()

    def test_incluye_terminos_del_contrato(self):
        for termino in ("javascript", "html", "css", "array", "fetch"):
            self.assertIn(termino, self.protegidos)

    def test_ninguno_es_palabra_vacia(self):
        self.assertFalse(set(self.protegidos) & set(leer_stopwords()))

    def test_patron_coincide_solo_con_terminos_completos(self):
        patron = re.compile(patron_terminos_protegidos(self.protegidos))
        self.assertTrue(patron.match("css"))
        self.assertFalse(patron.match("csss"))
        self.assertFalse(patron.match("xcss"))

    def test_patron_rechaza_lista_vacia(self):
        with self.assertRaises(ValueError):
            patron_terminos_protegidos([])


class PruebasSinonimos(unittest.TestCase):
    def setUp(self):
        self.grupos = leer_grupos_sinonimos()

    def test_grupos_normalizados(self):
        for grupo in self.grupos:
            for termino in grupo:
                self.assertEqual(termino, normalizar_termino(termino))

    def test_un_termino_pertenece_a_un_solo_grupo(self):
        terminos = [termino for grupo in self.grupos for termino in grupo]
        self.assertEqual(len(terminos), len(set(terminos)))

    def test_ningun_sinonimo_de_una_palabra_es_vacio(self):
        palabras_sueltas = {t for grupo in self.grupos for t in grupo if " " not in t}
        self.assertFalse(palabras_sueltas & set(leer_stopwords()))

    def test_incluye_par_promesa_promise(self):
        self.assertIn(["promesa", "promise"], self.grupos)

    def test_rechaza_reglas_de_reemplazo(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "sinonimos.txt"
            ruta.write_text("auto => coche\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                leer_grupos_sinonimos(ruta)


if __name__ == "__main__":
    unittest.main()
