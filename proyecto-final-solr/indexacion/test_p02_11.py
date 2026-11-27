"""P02-11: simulaciones sin red; integración completa optativa de solo lectura."""

from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import indexar_corpus_mdn as modulo
from test_p01_05 import estado_base, estado_p05


class SolrSimulado:
    def __init__(self, documentos=()):
        self.documentos = deepcopy(list(documentos))
        self.escrituras = []
        self.esquema = estado_p05()
        self.fallo = None
        self.facetas_malas = False
        self.busqueda_vacia = False
        self.inconsistente = False
        self.consultas = 0
        self.auxiliar_vacio = False

    def consultar(self, **parametros):
        docs = sorted(deepcopy(self.documentos), key=lambda d: d["id"])
        # Las respuestas reales de Solr omiten multivaluados sin valores.
        for doc in docs:
            if doc.get("enlaces_salientes") == []:
                del doc["enlaces_salientes"]
        if parametros.get("facet"):
            categorias = modulo.Counter(d["categoria"] for d in docs)
            if self.facetas_malas:
                categorias["CSS"] = 19
            return {"facet_counts": {"facet_fields": {
                "categoria": [v for par in categorias.items() for v in par],
                "tipo_fuente": ["web", len(docs)]}}}
        q = parametros.get("q", "*:*")
        if q.endswith(":[* TO *]"):
            return {"response": {"numFound": 0 if self.auxiliar_vacio else len(docs), "docs": []}}
        if q != "*:*":
            self.consultas += 1
            if self.busqueda_vacia or (self.inconsistente and self.consultas % 2 == 0):
                docs = []
            else:
                docs = [{"id": d["id"], "score": 1.0} for d in docs]
        return {"response": {"numFound": len(docs), "docs": docs[:parametros.get("rows", 10)]}}

    def enviar(self, core, ruta, cuerpo, **kwargs):
        self.escrituras.append(deepcopy(cuerpo))
        if isinstance(cuerpo, list):
            # Simula una aceptación parcial sin commit ante desconexión.
            if self.fallo == "parcial":
                self.documentos = deepcopy(cuerpo[:7])
                raise RuntimeError("Conexión interrumpida durante update")
            if self.fallo == "update":
                return {"responseHeader": {"status": 1}, "error": "update fallido"}
            self.documentos = [{**deepcopy(d), "titulo_sugerencia": d["titulo"]} for d in cuerpo]
        elif self.fallo == "commit":
            raise RuntimeError("Commit fallido")
        return {"responseHeader": {"status": 0}}


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=modulo.PROYECTO)
        self.addCleanup(self.temp.cleanup)
        self.ruta = Path(self.temp.name) / "corpus_solr.json"
        for nombre in ("corpus_solr.json", "metadatos_crawler.json", "reporte_transformacion.json"):
            self.ruta.with_name(nombre).write_bytes(modulo.CORPUS.with_name(nombre).read_bytes())

    def modificar(self, nombre, funcion):
        ruta = self.ruta.with_name(nombre)
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
        funcion(contenido)
        raw = json.dumps(contenido, ensure_ascii=False).encode("utf-8")
        ruta.write_bytes(raw)
        if nombre == "corpus_solr.json":
            reporte = self.ruta.with_name("reporte_transformacion.json")
            datos = json.loads(reporte.read_text(encoding="utf-8"))
            datos["sha256_archivo_salida"] = modulo.hashlib.sha256(raw).hexdigest()
            reporte.write_text(json.dumps(datos), encoding="utf-8")

    def test_corpus_real_60_con_metadatos_preservados(self):
        documentos, validacion = modulo.cargar_completo(self.ruta)
        self.assertEqual(len({d["id"] for d in documentos}), 60)
        self.assertEqual(validacion["resumen_completo"]["categorias_validas"], modulo.CUOTAS)
        originales = json.loads(self.ruta.read_text(encoding="utf-8"))
        por_id = {d["id"]: d for d in documentos}
        self.assertTrue(all(all(por_id[d["id"]][k] == v for k, v in d.items()) for d in originales))

    def test_corpus_incompleto_duplicado_ajeno_cuotas(self):
        for mutar in (lambda d: d.pop(), lambda d: d.__setitem__(0, d[1]),
                      lambda d: d[0].update(score=1), lambda d: d[0].update(categoria="HTML")):
            with self.subTest(mutar=mutar):
                self.ruta.write_bytes(modulo.CORPUS.read_bytes())
                self.modificar("corpus_solr.json", mutar)
                with self.assertRaises(ValueError):
                    modulo.cargar_completo(self.ruta)

    def test_hash_y_reporte(self):
        for mutar in (lambda r: r.update(estado="rechazado"),
                      lambda r: r.update(sha256_archivo_salida="incorrecto")):
            self.modificar("reporte_transformacion.json", mutar)
            with self.assertRaises(ValueError):
                modulo.cargar_completo(self.ruta)

    def test_metadatos_invalidos(self):
        for mutar in (lambda m: m.pop(), lambda m: m.append(deepcopy(m[0])),
                      lambda m: m[0].update(id="ajeno"), lambda m: m[0].update(score=2),
                      lambda m: m[0].update(fecha_rastreo="2026-11-27"),
                      lambda m: m[0].update(fecha_rastreo="2026-11-27T01:02:03-06:00"),
                      lambda m: m[0].update(profundidad=True),
                      lambda m: m[0].update(enlaces_salientes="url"),
                      lambda m: m[0].update(sha256_contenido="incorrecto")):
            with self.subTest(mutar=mutar):
                self.ruta.with_name("metadatos_crawler.json").write_bytes(modulo.CORPUS.with_name("metadatos_crawler.json").read_bytes())
                self.modificar("metadatos_crawler.json", mutar)
                with self.assertRaises(ValueError):
                    modulo.cargar_completo(self.ruta)


class IndexadorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.documentos, _ = modulo.cargar_completo()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=modulo.PROYECTO)
        self.addCleanup(self.temp.cleanup)
        self.numero = 0
        self.solr = SolrSimulado()
        for nombre, sustituto in (("instantanea", lambda: deepcopy(self.solr.esquema)),
                                  ("comprobar_analizador", lambda: {"simulado": True}),
                                  ("consultar", self.solr.consultar), ("enviar", self.solr.enviar)):
            parche = patch.object(modulo, nombre, sustituto)
            parche.start()
            self.addCleanup(parche.stop)

    def ejecutar(self, aplicar=False, confirmar=True):
        self.numero += 1
        return modulo.ejecutar(aplicar=aplicar,
                              confirmacion=modulo.CONFIRMACION if confirmar else None,
                              salida=Path(self.temp.name) / str(self.numero))

    def cargar(self):
        return self.ejecutar(True)

    def test_esquema_completo(self):
        self.assertEqual(modulo.revisar_esquema(estado_p05()), [])

    def test_p05_ausente_y_parcial(self):
        for estado in (estado_base(True), estado_p05()):
            estado["schema"]["copyFields"] = []
            self.solr.esquema = estado
            reporte = self.ejecutar()
            self.assertEqual(reporte["estado"], "prueba_bloqueada")
            with self.assertRaises(modulo.IndexacionError):
                self.cargar()
        self.assertEqual(self.solr.escrituras, [])

    def test_campo_principal_faltante_bloquea(self):
        self.solr.esquema["fields"] = [c for c in self.solr.esquema["fields"] if c["name"] != "fuente"]
        with self.assertRaises(modulo.IndexacionError):
            self.cargar()
        self.assertEqual(self.solr.escrituras, [])

    def test_esquemas_incompatibles(self):
        for campo, propiedad, valor in (("titulo", "type", "text_es_ri"),
                                        ("contenido", "stored", False),
                                        ("categoria", "docValues", False),
                                        ("contenido_ortografia", "stored", True)):
            self.solr.esquema = estado_p05()
            next(c for c in self.solr.esquema["fields"] if c["name"] == campo)[propiedad] = valor
            with self.assertRaises(modulo.IndexacionError):
                self.cargar()
        self.assertEqual(self.solr.escrituras, [])

    def test_prueba_piloto_sin_escrituras(self):
        self.solr.documentos = modulo.seleccionar(self.documentos)
        reporte = self.ejecutar()
        self.assertEqual(reporte["estado"], "prueba_lista")
        self.assertEqual(modulo.Counter(d["accion"] for d in reporte["plan"]), {"crear": 57, "sustituir": 3})
        self.assertEqual(self.solr.escrituras, [])

    def test_sin_confirmacion(self):
        with self.assertRaises(modulo.IndexacionError):
            self.ejecutar(True, False)
        self.assertEqual(self.solr.escrituras, [])

    def test_solr_no_disponible_prueba_y_aplicacion(self):
        with patch.object(modulo, "instantanea", side_effect=OSError("Solr apagado")):
            self.assertEqual(self.ejecutar()["estado"], "prueba_local_solr_no_disponible")
            with self.assertRaises(modulo.IndexacionError):
                self.cargar()
        self.assertEqual(self.solr.escrituras, [])

    def test_estados_ajenos_parciales_y_piloto_alterado(self):
        piloto = modulo.seleccionar(self.documentos)
        piloto[0]["titulo"] = "Alterado"
        for docs in ([{"id": "ajeno"}], self.documentos[:7], piloto,
                     [*self.documentos, {"id": "ajeno"}], [self.documentos[0]] * 60):
            self.solr.documentos = deepcopy(docs)
            with self.assertRaises(modulo.IndexacionError):
                self.cargar()
        self.assertEqual(self.solr.escrituras, [])

    def test_carga_vacia_piloto_y_repeticion_segura(self):
        for inicial in ([], modulo.seleccionar(self.documentos)):
            self.solr.documentos = inicial
            for _ in range(2):
                reporte = self.cargar()
                self.assertEqual(reporte["estado"], "carga_verificada")
                self.assertTrue(reporte["commit_confirmado"])
                self.assertEqual(len(self.solr.documentos), 60)
                self.assertEqual(len({d["id"] for d in self.solr.documentos}), 60)
                self.assertEqual(self.solr.escrituras[-1], {"commit": {"waitSearcher": True}})
                self.assertEqual(self.solr.escrituras[-2], self.documentos)
                busquedas = reporte["verificacion"]["busquedas"]
                self.assertEqual(len(busquedas), 10)
                self.assertEqual({b["parametros"]["qf"] for b in busquedas}, {"titulo", "contenido"})
                self.assertRegex(busquedas[-1]["parametros"]["q"], "[áéíóúñ]")

    def test_recuento_y_preservacion_completa(self):
        self.cargar()
        originales = deepcopy(self.solr.documentos)
        for campo, valor in (("tipo_fuente", "pdf"), ("categoria", "HTML"),
                             ("titulo", "Distinto"), ("url", "distinta"),
                             ("contenido", "Distinto"), ("fuente", "Distinta"),
                             ("titulo_sugerencia", "Distinto"),
                             ("fecha_rastreo", "2026-01-01T00:00:00.000Z")):
            self.solr.documentos = deepcopy(originales)
            self.solr.documentos[0][campo] = valor
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                modulo.verificar(self.documentos)
        self.solr.documentos = originales[:3]
        with self.assertRaises(ValueError):
            modulo.verificar(self.documentos)

    def test_fallo_verificacion_despues_del_commit_registra_estado(self):
        self.solr.facetas_malas = True
        with self.assertRaises(modulo.IndexacionError) as error:
            self.cargar()
        self.assertTrue(error.exception.reporte["commit_confirmado"])
        self.assertEqual(error.exception.reporte["estado_tras_error"]["response"]["numFound"], 60)
        self.assertEqual(len(self.solr.escrituras), 2)

    def test_fecha_solr_equivalente_preserva_instante(self):
        self.cargar()
        doc = next(d for d in self.solr.documentos if d["fecha_rastreo"].endswith("0Z"))
        doc["fecha_rastreo"] = doc["fecha_rastreo"][:-2] + "Z"
        modulo.verificar(self.documentos)

    def test_enlaces_vacios_omitidos_por_solr(self):
        vacios = {d["id"] for d in self.documentos if d.get("enlaces_salientes") == []}
        self.assertEqual(len(vacios), 5)
        self.solr.documentos = [{**deepcopy(d), "titulo_sugerencia": d["titulo"]}
                                for d in self.documentos]
        respuesta = self.solr.consultar(rows=61)
        self.assertTrue(all("enlaces_salientes" not in d for d in respuesta["response"]["docs"]
                            if d["id"] in vacios))
        modulo.verificar(self.documentos)
        self.assertEqual(self.solr.escrituras, [])
        self.assertTrue(all(d["enlaces_salientes"] == [] for d in self.documentos if d["id"] in vacios))

    def test_enlaces_no_vacios_exigen_lista_exacta(self):
        originales = [{**deepcopy(d), "titulo_sugerencia": d["titulo"]} for d in self.documentos]
        indice = next(i for i, d in enumerate(originales) if len(d.get("enlaces_salientes", [])) >= 2)
        enlaces = originales[indice]["enlaces_salientes"]
        for caso, valor in (("incompleta", enlaces[:-1]),
                            ("alterada", [enlaces[1], *enlaces[1:]]),
                            ("diferente", [originales[indice]["id"] + "/otro", *enlaces[1:]]),
                            ("orden_distinto", list(reversed(enlaces))),
                            ("adicional", [*enlaces, "https://developer.mozilla.org/es/docs/Web/CSS"]),
                            ("vacia", []), ("null", None), ("ausente", None)):
            self.solr.documentos = deepcopy(originales)
            if caso == "ausente":
                del self.solr.documentos[indice]["enlaces_salientes"]
            else:
                self.solr.documentos[indice]["enlaces_salientes"] = valor
            with self.subTest(caso=caso), self.assertRaisesRegex(ValueError, "Campos o metadatos alterados"):
                modulo.verificar(self.documentos)
        self.assertEqual(self.solr.escrituras, [])

    def test_excepcion_de_lista_vacia_no_flexibiliza_otros_valores(self):
        originales = [{**deepcopy(d), "titulo_sugerencia": d["titulo"]} for d in self.documentos]
        indice = next(i for i, d in enumerate(originales) if d.get("enlaces_salientes") == [])
        for campo, valor in (("enlaces_salientes", None), ("enlaces_salientes", ""),
                             ("enlaces_salientes", [originales[indice]["id"]]),
                             ("atribucion", None), ("titulo", None), ("fuente", None)):
            self.solr.documentos = deepcopy(originales)
            self.solr.documentos[indice][campo] = valor
            with self.subTest(campo=campo, valor=valor), self.assertRaisesRegex(ValueError, "Campos o metadatos alterados"):
                modulo.verificar(self.documentos)
        for campo in ("atribucion", "titulo", "fuente"):
            self.solr.documentos = deepcopy(originales)
            del self.solr.documentos[indice][campo]
            with self.subTest(ausente=campo), self.assertRaisesRegex(ValueError, "Campos o metadatos alterados"):
                modulo.verificar(self.documentos)
        self.assertEqual(self.solr.escrituras, [])

    def test_fallos_solr_con_evidencia_sin_limpieza(self):
        for fallo in ("update", "parcial", "commit"):
            self.solr = SolrSimulado()
            # Los mocks de métodos originales se enlazaron en setUp.
            with patch.object(modulo, "consultar", self.solr.consultar), patch.object(modulo, "enviar", self.solr.enviar):
                self.solr.fallo = fallo
                with self.assertRaises(modulo.IndexacionError) as error:
                    self.cargar()
                reporte = error.exception.reporte
                self.assertTrue(reporte["escritura_intentada"])
                self.assertFalse(reporte["commit_confirmado"])
                evidencia = Path(reporte["salida"]) / "resultado.json"
                self.assertEqual(json.loads(evidencia.read_text(encoding="utf-8"))["estado"], "error")
                self.assertLessEqual(len(self.solr.escrituras), 2)
                if fallo == "parcial":
                    self.assertEqual(reporte["estado_tras_error"]["response"]["numFound"], 7)

    def test_errores_de_verificacion(self):
        self.cargar()
        for atributo in ("facetas_malas", "busqueda_vacia", "inconsistente", "auxiliar_vacio"):
            setattr(self.solr, atributo, True)
            with self.assertRaises(ValueError):
                modulo.verificar(self.documentos)
            setattr(self.solr, atributo, False)
        self.solr.documentos[0]["atribucion"] = "Alterada"
        with self.assertRaisesRegex(ValueError, "alterados"):
            modulo.verificar(self.documentos)

    def test_estado_cambia_antes_de_escribir(self):
        with patch.object(modulo, "leer_indice", side_effect=[
                {"response": {"numFound": 0, "docs": []}},
                {"response": {"numFound": 1, "docs": [{"id": "ajeno"}]}},
                {"response": {"numFound": 1, "docs": [{"id": "ajeno"}]}}]):
            with self.assertRaises(modulo.IndexacionError):
                self.cargar()
        self.assertEqual(self.solr.escrituras, [])


@unittest.skipUnless(os.environ.get("P02_11_SOLR_INTEGRACION") == "1", "Integración de 60 documentos optativa, solo lectura; requiere carga futura")
class IntegracionCompletaTests(unittest.TestCase):
    def test_indice_real_completo(self):
        documentos, _ = modulo.cargar_completo()
        self.assertEqual(modulo.revisar_esquema(modulo.instantanea()), [])
        modulo.comprobar_analizador()
        modulo.verificar(documentos)


if __name__ == "__main__":
    unittest.main()
