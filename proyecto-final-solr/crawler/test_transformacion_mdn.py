"""P02-09: contrato, rechazo integral, preservación y reproducibilidad sin red."""

from copy import deepcopy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import transformar_corpus_mdn as tr


class TransformacionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = tr.ENTRADA.read_bytes()
        cls.corpus = json.loads(cls.raw.decode("utf-8"))

    def test_corpus_real_cuotas_campos_preservacion_y_no_mutacion(self):
        antes = deepcopy(self.corpus)
        nuevos, metadata, reporte = tr.transformar_corpus(self.corpus)
        self.assertEqual(len(nuevos), 60)
        self.assertEqual(reporte["resumen"]["categorias_validas"], tr.CUOTAS)
        self.assertEqual(reporte["resumen"]["ids_unicos_validos"], 60)
        self.assertTrue(all(reporte["comprobaciones"].values()))
        self.assertEqual(reporte["facetas"], ["categoria", "tipo_fuente"])
        for original, nuevo, meta in zip(self.corpus, nuevos, metadata):
            # Lista explícita: evitar que la prueba replique una constante incorrecta.
            self.assertEqual(set(nuevo), {"id", "titulo", "contenido", "categoria",
                                         "tipo_fuente", "fuente", "idioma", "url"})
            self.assertEqual(nuevo, {k: original[k] for k in nuevo})
            self.assertEqual(meta["id"], nuevo["id"])
            self.assertEqual(meta["enlaces_salientes"], original["enlaces_salientes"])
            self.assertEqual(meta["sha256_contenido"], hashlib.sha256(nuevo["contenido"].encode("utf-8")).hexdigest())
            self.assertRegex(meta["fecha_rastreo"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
        self.assertEqual(self.corpus, antes)
        metadata[0]["enlaces_salientes"].clear()
        self.assertEqual(self.corpus, antes)

    def test_metadatos_incluidos_solo_autorizados(self):
        nuevos, metadatos, reporte = tr.transformar_corpus(self.corpus, True)
        self.assertEqual(reporte["modo_metadatos"], "incluidos")
        for original, nuevo, meta in zip(self.corpus, nuevos, metadatos):
            self.assertEqual(nuevo, {**{k: original[k] for k in tr.OBLIGATORIOS}, **meta})
            self.assertLessEqual(set(nuevo), set(tr.OBLIGATORIOS) | set(tr.OPCIONALES))
            for campo in tr.OPCIONALES:
                if original.get(campo) is not None and campo != "fecha_rastreo":
                    self.assertEqual(nuevo[campo], original[campo])
            for campo in ("score", "snippet", "tema", "titulo_web", "contenido_web"):
                self.assertNotIn(campo, nuevo)

    def test_fechas_utc_offsets_y_precision(self):
        for original, esperado in (
            ("2026-11-23T22:15:40.286254+00:00", "2026-11-23T22:15:40.286Z"),
            ("2026-11-23T23:15:40.999999-06:00", "2026-11-24T05:15:40.999Z"),
            ("2026-11-23T00:15:40+02:00", "2026-11-22T22:15:40.000Z"),
            ("2026-11-23T22:15:40Z", "2026-11-23T22:15:40.000Z"),
        ):
            with self.subTest(original=original):
                self.assertEqual(tr.fecha_solr(original), esperado)
                self.assertEqual(tr.fecha_solr(esperado), esperado)
        for valor in (None, 10, "2026-11-23", "2026-11-23T22:15:40", "2026-02-30T22:15:40Z", "ayer"):
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                tr.fecha_solr(valor)

    def test_opcionales_ausentes_null_y_listas_vacias(self):
        minimo = {k: self.corpus[0][k] for k in tr.OBLIGATORIOS}
        self.assertEqual(tr.transformar_documento(minimo), (minimo, {}))
        for campo in tr.OPCIONALES:
            minimo[campo] = None
        self.assertEqual(tr.transformar_documento(minimo)[1], {})
        minimo["enlaces_salientes"] = []
        minimo["profundidad"] = 0
        minimo["pagerank"] = 0.5
        self.assertEqual(tr.transformar_documento(minimo)[1],
                         {"enlaces_salientes": [], "profundidad": 0, "pagerank": 0.5})

    def test_rechaza_cantidad_cuotas_raiz_y_duplicados(self):
        casos = [[], self.corpus[:-1], self.corpus + [self.corpus[0]], {}, [None] * 60]
        duplicado = deepcopy(self.corpus)
        duplicado[1] = deepcopy(duplicado[0])
        casos.append(duplicado)
        cuotas = deepcopy(self.corpus)
        indice = next(i for i, doc in enumerate(cuotas) if doc["categoria"] == "HTML")
        cuotas[indice] = deepcopy(cuotas[0])
        cuotas[indice]["url"] += "/Otro"
        cuotas[indice]["id"] = cuotas[indice]["url"]
        casos.append(cuotas)
        for docs in casos:
            with self.subTest(caso=str(type(docs))), self.assertRaises(tr.TransformacionError) as ctx:
                tr.transformar_corpus(docs)
            self.assertEqual(ctx.exception.reporte["estado"], "rechazado")
            self.assertEqual(ctx.exception.reporte["resumen"]["documentos_transformados"], 0)

    def test_rechaza_campos_obligatorios_faltantes_y_vacios(self):
        for campo in tr.OBLIGATORIOS:
            for valor in (None, "", "  \n", [], 12):
                doc = deepcopy(self.corpus[0])
                doc[campo] = valor
                with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                    tr.transformar_documento(doc)
            del doc[campo]
            with self.assertRaises(ValueError):
                tr.transformar_documento(doc)

    def test_rechaza_valores_invalidos_y_campos_ajenos(self):
        casos = {
            "idioma": ["en", "es-MX"], "categoria": ["General", "html", "CSS"],
            "fuente": ["otra"], "tipo_fuente": ["pdf"], "id": ["otro"],
            "fecha_rastreo": ["sin fecha", "2026-11-23T00:00:00"],
            "enlaces_salientes": ["https://developer.mozilla.org/es/docs/Web/CSS", [None], ["https://otro.org/"]],
            "profundidad": [True, -1, 1.5, 2**31], "pagerank": [True, -1, float("nan"), float("inf"), "1"],
            "sha256_contenido": ["a" * 64], "sha256_contenido_normalizado": ["b" * 64],
            "descubierta_desde": ["/relativo"], "tipo_documento": ["faceta"],
            "titulo_original": [123], "atribucion": [""], "score": [1], "snippet": ["texto"],
        }
        for campo, valores in casos.items():
            for valor in valores:
                doc = deepcopy(self.corpus[0])
                doc[campo] = valor
                with self.subTest(campo=campo, valor=valor), self.assertRaises(ValueError):
                    tr.transformar_documento(doc)

    def test_urls_invalidas_y_sin_normalizar_no_se_reparan(self):
        url = self.corpus[0]["url"]
        for valor in (url + "#fragmento", url + "?q=1", url + "/", url.replace("https", "http"),
                      url.replace("/es/", "/en/"), url + "/../otra", url + "/%252e", url + " ",
                      url.replace("developer.mozilla.org", "usuario@developer.mozilla.org"),
                      url.replace("developer.mozilla.org", "otro.org")):
            doc = deepcopy(self.corpus[0])
            doc["id"] = doc["url"] = valor
            with self.subTest(url=valor), self.assertRaises(ValueError):
                tr.transformar_documento(doc)

    def test_generacion_reproducible_entrada_intacta_y_no_sobrescritura(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp).resolve()
            entrada = raiz / "entrada.json"
            entrada.write_bytes(self.raw)
            evidencia = raiz / "reporte_previo.json"
            evidencia.write_bytes(b"evidencia intacta")
            with patch.object(tr, "PROYECTO", raiz), contextlib.redirect_stdout(io.StringIO()):
                a = tr.ejecutar_transformacion(entrada, raiz / "a")
                b = tr.ejecutar_transformacion(entrada, raiz / "b")
                with self.assertRaises(FileExistsError):
                    tr.ejecutar_transformacion(entrada, a)
                with self.assertRaisesRegex(ValueError, "dentro"):
                    tr.ejecutar_transformacion(entrada, raiz.parent / "fuera")
            for nombre in ("corpus_solr.json", "metadatos_crawler.json"):
                self.assertEqual((a / nombre).read_bytes(), (b / nombre).read_bytes())
            reporte = json.loads((a / "reporte_transformacion.json").read_text("utf-8"))
            nuevos = json.loads((a / "corpus_solr.json").read_text("utf-8"))
            self.assertEqual(len(nuevos), 60)
            self.assertEqual(reporte["estado"], "exitoso")
            self.assertEqual(reporte["sha256_archivo_salida"], hashlib.sha256((a / "corpus_solr.json").read_bytes()).hexdigest())
            self.assertEqual(reporte["sha256_archivo_entrada"], hashlib.sha256(self.raw).hexdigest())
            self.assertTrue(reporte["entrada_intacta"])
            self.assertEqual(entrada.read_bytes(), self.raw)
            self.assertEqual(evidencia.read_bytes(), b"evidencia intacta")

    def test_rechazo_persistido_sin_corpus_parcial(self):
        malo = deepcopy(self.corpus)
        malo[5]["titulo"] = ""
        malo[9]["idioma"] = "en"
        for raw in (b"[]", b"{json invalido", b"\xff", tr.serializar(malo)):
            with self.subTest(raw=raw[:10]), tempfile.TemporaryDirectory() as tmp:
                raiz = Path(tmp).resolve()
                entrada = raiz / "entrada.json"
                entrada.write_bytes(raw)
                salida = raiz / "salida"
                with patch.object(tr, "PROYECTO", raiz), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(tr.TransformacionError):
                    tr.ejecutar_transformacion(entrada, salida)
                self.assertEqual([p.name for p in salida.iterdir()], ["reporte_transformacion.json"])
                reporte = json.loads((salida / "reporte_transformacion.json").read_text("utf-8"))
                self.assertEqual(reporte["estado"], "rechazado")
                self.assertIsNone(reporte["archivo_salida"])
                self.assertTrue(reporte["errores"])
                self.assertEqual(entrada.read_bytes(), raw)

    def test_cli_exito_y_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz = Path(tmp).resolve()
            with patch.object(tr, "PROYECTO", raiz), contextlib.redirect_stdout(io.StringIO()):
                with patch("sys.argv", ["transformar", "--salida", str(raiz / "ok"), "--incluir-metadatos"]):
                    self.assertEqual(tr.main(), 0)
                docs = json.loads((raiz / "ok/corpus_solr.json").read_text("utf-8"))
                self.assertIn("fecha_rastreo", docs[0])
                entrada = raiz / "invalido.json"
                entrada.write_text("[]", encoding="utf-8")
                with patch("sys.argv", ["transformar", "--entrada", str(entrada), "--salida", str(raiz / "error")]), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
                    tr.main()
                self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
