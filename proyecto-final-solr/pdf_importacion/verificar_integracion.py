"""Captura P07-04 de solo lectura. No contiene operaciones de actualización Solr."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

from pdf_importacion.documento_solr import convertir_pdf_a_documento
from pdf_importacion import indexar_pdf_solr as importador


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", required=True, type=Path, help="Directorio NUEVO")
    salida = parser.parse_args().salida
    salida.mkdir(parents=True, exist_ok=False)
    base = Path(__file__).resolve().parent
    registro = {"inicio_utc": datetime.now(timezone.utc).isoformat(),
                "operaciones": "Solo GET; no se ejecuta importación real", "consultas": []}

    def guardar(nombre, datos):
        (salida / nombre).write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def consultar(params):
        url = "http://localhost:8983/solr/ri/select?" + urlencode(params, doseq=True)
        with urlopen(url, timeout=20) as respuesta:
            datos = json.load(respuesta)
        registro["consultas"].append({"fecha_utc": datetime.now(timezone.utc).isoformat(), "metodo": "GET", "url": url})
        if datos.get("responseHeader", {}).get("status") != 0:
            raise RuntimeError("Solr devolvió un estado de error")
        return datos

    try:
        recuento = consultar({"q": "*:*", "rows": 0, "facet": "true", "facet.field": ["tipo_fuente", "categoria"], "json.nl": "map", "wt": "json"})
        guardar("recuento_facetas.json", recuento)
        assert recuento["response"]["numFound"] == 62, "Total distinto de 62"
        facetas = recuento["facet_counts"]["facet_fields"]
        assert facetas["tipo_fuente"] == {"web": 60, "pdf": 2}, "Fuentes distintas de 60/2"
        assert {k: v for k, v in facetas["categoria"].items() if v} == {"JavaScript": 20, "HTML": 21, "CSS": 21}, "Categorías inesperadas"

        manifiesto = json.loads((base / "muestras/manifiesto_p07_01.json").read_text(encoding="utf-8"))
        originales = {}
        for muestra, nombre in zip(manifiesto, ("html", "css")):
            ruta = base / "muestras" / muestra["archivo"]
            assert hashlib.sha256(ruta.read_bytes()).hexdigest() == muestra["sha256_pdf"]
            doc = convertir_pdf_a_documento(ruta, titulo=muestra["titulo"], categoria=muestra["categoria"])
            anterior = base / "evidencias/p07-03" / (nombre + ".json")
            assert doc == json.loads(anterior.read_text(encoding="utf-8")), "P07-03 difiere de la transformación actual"
            originales[ruta.relative_to(base).as_posix()] = muestra["sha256_pdf"]
            originales[anterior.relative_to(base).as_posix()] = hashlib.sha256(anterior.read_bytes()).hexdigest()
            respuesta = consultar({"q": muestra["consulta_exclusiva"], "defType": "edismax", "qf": "titulo^4 contenido", "rows": 10, "fl": "id,titulo,categoria,tipo_fuente", "wt": "json"})
            guardar("busqueda_" + nombre + ".json", respuesta)
            assert respuesta["response"]["numFound"] == 1, "Consulta exclusiva sin resultado único"
            assert respuesta["response"]["docs"] == [{k: doc[k] for k in ("id", "titulo", "categoria", "tipo_fuente")}]

        # Comparar cada campo presente en el corpus aprobado; no solo ID/categoría.
        corpus = base.parent / "data/mdn/transformacion/transformacion_20261126T061527349966Z_68284317199543fbb7b8f960224db1d0/corpus_solr.json"
        aprobados = json.loads(corpus.read_text(encoding="utf-8"))
        importador._ids_mdn_aprobados()
        campos = sorted(set().union(*(d.keys() for d in aprobados)))
        respuesta = consultar({"q": "tipo_fuente:web", "rows": 100, "fl": ",".join(campos), "wt": "json"})
        actuales = {d["id"]: d for d in respuesta["response"]["docs"]}
        assert respuesta["response"]["numFound"] == 60
        assert set(actuales) == {d["id"] for d in aprobados}
        diferencias = [{"id": d["id"], "campo": k} for d in aprobados for k, v in d.items() if actuales[d["id"]].get(k) != v]
        guardar("conservacion_mdn.json", {"corpus": corpus.relative_to(base.parent).as_posix(), "sha256_corpus": hashlib.sha256(corpus.read_bytes()).hexdigest(), "documentos_comparados": len(aprobados), "campos_comparados": campos, "diferencias": diferencias, "alcance": "Campos almacenados presentes en el corpus aprobado; no acredita estado histórico, analizadores ni campos derivados por copyField."})
        assert not diferencias, "Hay campos MDN distintos del corpus aprobado"

        # Defensa adicional: cualquier intento de POST en la simulación se bloquea.
        http_original = importador._json_http

        def solo_lectura(metodo, url, cuerpo=None):
            if metodo != "GET" or cuerpo is not None:
                raise RuntimeError("Verificación limitada a GET")
            datos = http_original(metodo, url)
            registro["consultas"].append({"fecha_utc": datetime.now(timezone.utc).isoformat(), "metodo": metodo, "url": url})
            return datos

        importador._json_http = solo_lectura
        try:
            simulaciones = []
            for muestra in manifiesto:
                doc = convertir_pdf_a_documento(base / "muestras" / muestra["archivo"], titulo=muestra["titulo"], categoria=muestra["categoria"])
                resultado = importador.importar_documento_pdf(doc)
                simulaciones.append(resultado)
                assert resultado["estado"] == "simulacion" and resultado["accion"] == "omitir"
            guardar("simulacion_idempotencia.json", simulaciones)
        finally:
            importador._json_http = http_original
        registro.update(resultado="OK", archivos_preservados_sha256=originales)
    except Exception as exc:
        registro.update(resultado="ERROR", error=str(exc))
        raise
    finally:
        registro["fin_utc"] = datetime.now(timezone.utc).isoformat()
        guardar("registro.json", registro)
    print("Verificación de lectura: OK; evidencias en", salida.as_posix())


if __name__ == "__main__":
    main()
