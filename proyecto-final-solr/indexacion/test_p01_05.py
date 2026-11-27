"""Pruebas locales sin red; integración real optativa de solo lectura."""

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import configurar_esquema as esquema
import indexar_piloto as piloto


def estado_base(completo=False):
    return {"schema": {"uniqueKey": "id", "copyFields": [],
                       "fieldTypes": [{"name": t} for t in
                                      {c["type"] for c in esquema.CAMPOS} | set(esquema.TIPOS_PROTEGIDOS)]},
            "fields": deepcopy(esquema.CAMPOS if completo else esquema.CAMPOS[:1])}


class EsquemaTests(unittest.TestCase):
    def test_plan_idempotente_y_sin_mutacion(self):
        estado = estado_base()
        antes = deepcopy(estado)
        cambios = esquema.planificar(estado)
        self.assertEqual(len(cambios), 19)
        self.assertTrue(all(c["name"] != "id" for c in cambios))
        self.assertEqual(estado, antes)
        self.assertEqual(esquema.planificar(estado_base(True)), [])

    def test_contrato_tipos_facetas_y_opcionales(self):
        campos = {c["name"]: c for c in esquema.CAMPOS}
        for c in ("titulo", "contenido"):
            self.assertEqual(campos[c]["type"], "text_es_proyecto")
            self.assertTrue(campos[c]["required"])
        for c in ("categoria", "tipo_fuente"):
            self.assertEqual(campos[c]["type"], "string")
            self.assertTrue(campos[c]["docValues"])
        for c, tipo in {"profundidad": "pint", "fecha_rastreo": "pdate",
                        "enlaces_salientes": "strings", "pagerank": "pdouble"}.items():
            self.assertEqual(campos[c]["type"], tipo)
            self.assertFalse(campos[c]["required"])
        self.assertTrue(campos["enlaces_salientes"]["multiValued"])
        self.assertFalse(campos["url"]["required"])  # PDF sin URL permitido.
        self.assertFalse({"score", "snippet", "tema", "titulo_web"} & campos.keys())

    def test_incompatibilidades_bloquean_antes_de_escribir(self):
        for campo, propiedad, valor in (("titulo", "type", "text_es_ri"),
                                        ("categoria", "docValues", False),
                                        ("contenido", "multiValued", True),
                                        ("url", "required", True)):
            with self.subTest(campo=campo), patch.object(esquema, "enviar") as enviar:
                estado = estado_base(True)
                next(c for c in estado["fields"] if c["name"] == campo)[propiedad] = valor
                with patch.object(esquema, "instantanea", return_value=estado):
                    with self.assertRaisesRegex(ValueError, "incompatible"):
                        esquema.configurar(True)
                enviar.assert_not_called()

    def test_unique_key_tipos_copyfield_y_required_ajeno(self):
        estados = []
        estado = estado_base(); estado["schema"]["uniqueKey"] = "otro"; estados.append(estado)
        estado = estado_base(); estado["schema"]["fieldTypes"] = []; estados.append(estado)
        estado = estado_base(); estado["schema"]["copyFields"] = [{"source": "*", "dest": "_text_"}]; estados.append(estado)
        estado = estado_base(); estado["fields"].append({"name": "otro", "required": True}); estados.append(estado)
        for estado in estados:
            with self.assertRaises(ValueError):
                esquema.planificar(estado)

    def test_aplicar_solo_add_field_y_conserva_tipos(self):
        with patch.object(esquema, "instantanea", side_effect=[estado_base(), estado_base(True)]), \
                patch.object(esquema, "comprobar_analizador", return_value={}), \
                patch.object(esquema, "enviar") as enviar:
            esquema.configurar(True)
            comandos = enviar.call_args.args[2]
            self.assertEqual(set(comandos), {"add-field"})
            self.assertEqual(len(comandos["add-field"]), 19)

    def test_evidencia_no_se_sobrescribe(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "evidencia.json"
            esquema.guardar_nuevo(ruta, {"original": True})
            with self.assertRaises(FileExistsError):
                esquema.guardar_nuevo(ruta, {})
            self.assertEqual(json.loads(ruta.read_text()), {"original": True})


class PilotoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = piloto.CORPUS.read_bytes()
        cls.documentos, cls.validacion = piloto.cargar_corpus(piloto.CORPUS)

    def test_60_validos_y_seleccion_exacta_estable(self):
        self.assertEqual(self.validacion["resumen"]["ids_unicos_validos"], 60)
        self.assertEqual(self.validacion["resumen"]["categorias_validas"], {"JavaScript": 20, "HTML": 20, "CSS": 20})
        seleccion = piloto.seleccionar(self.documentos)
        self.assertEqual([d["categoria"] for d in seleccion], ["JavaScript", "HTML", "CSS"])
        self.assertEqual(len({d["id"] for d in seleccion}), 3)
        self.assertEqual(seleccion, piloto.seleccionar(list(reversed(self.documentos))))
        self.assertTrue(all(d in self.documentos for d in seleccion))
        self.assertEqual(piloto.CORPUS.read_bytes(), self.raw)

    def test_hash_o_reporte_invalido_rechazado(self):
        for estado, sha in (("rechazado", self.validacion["sha256_corpus"]), ("exitoso", "incorrecto")):
            with tempfile.TemporaryDirectory() as carpeta:
                ruta = Path(carpeta) / "corpus_solr.json"
                ruta.write_bytes(self.raw)
                ruta.with_name("reporte_transformacion.json").write_text(json.dumps({"estado": estado, "sha256_archivo_salida": sha}))
                with self.assertRaises(ValueError):
                    piloto.cargar_corpus(ruta)

    def test_metadatos_reales_60_compatibles_sin_indexarlos(self):
        metadatos = json.loads(piloto.CORPUS.with_name("metadatos_crawler.json").read_text(encoding="utf-8"))
        por_id = {d["id"]: d for d in metadatos}
        self.assertEqual(set(por_id), {d["id"] for d in self.documentos})
        completos = [{**d, **por_id[d["id"]]} for d in self.documentos]
        nuevos, _, reporte = piloto.transformar_corpus(completos, True)
        self.assertEqual(nuevos, completos)
        self.assertEqual(reporte["resumen"]["documentos_validos"], 60)
        campos = {c["name"] for c in esquema.CAMPOS}
        self.assertTrue(all(set(d) <= campos for d in completos))

    def test_duplicados_campos_ajenos_y_cuotas_rechazados(self):
        for mutar in (lambda d: d.__setitem__(0, deepcopy(d[1])),
                      lambda d: d[0].update(score=2), lambda d: d.pop()):
            documentos = deepcopy(self.documentos)
            mutar(documentos)
            with self.assertRaises(ValueError):
                piloto.transformar_corpus(documentos, True)

    def test_core_ajeno_y_contenido_distinto_rechazados(self):
        seleccion = piloto.seleccionar(self.documentos)
        for docs in ([{"id": "ajeno"}], [{"id": "ajeno"}] * 3,
                     [{**d, "titulo": "alterado"} for d in seleccion]):
            with self.assertRaises(ValueError):
                piloto.comprobar_entorno(seleccion, {"response": {"numFound": len(docs), "docs": docs}})
        for docs in ([], seleccion):
            piloto.comprobar_entorno(seleccion, {"response": {"numFound": len(docs), "docs": docs}})

    def test_core_ocupado_no_recibe_update(self):
        with patch.object(piloto, "instantanea", return_value=estado_base(True)), \
                patch.object(piloto, "comprobar_analizador", return_value={}), \
                patch.object(piloto, "consultar", return_value={"response": {"numFound": 60, "docs": []}}), \
                patch.object(piloto, "enviar") as enviar:
            with self.assertRaises(ValueError):
                piloto.ejecutar(aplicar=True)
            enviar.assert_not_called()


@unittest.skipUnless(os.environ.get("P01_05_SOLR_INTEGRACION") == "1", "Integración optativa con ri; solo lectura")
class IntegracionTests(unittest.TestCase):
    def test_piloto_real_esquema_preservacion_busquedas_facetas(self):
        documentos, _ = piloto.cargar_corpus(piloto.CORPUS)
        self.assertEqual(esquema.planificar(esquema.instantanea()), [])
        esquema.comprobar_analizador()
        resultados = piloto.verificar(piloto.seleccionar(documentos))
        self.assertEqual(len(resultados), 11)


if __name__ == "__main__":
    unittest.main()
