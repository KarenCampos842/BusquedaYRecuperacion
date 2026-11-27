"""P01-05: validar 60 documentos locales, indexar SOLO tres y comprobar Solr."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from configurar_esquema import (CORE, CONTRATO, PROYECTO, enviar, obtener, guardar_nuevo,
                                instantanea, planificar, protegidos, comprobar_analizador)

sys.path.insert(0, str(PROYECTO / "crawler"))
from transformar_corpus_mdn import transformar_corpus, CUOTAS  # noqa: E402

CORPUS = PROYECTO / "data/mdn/transformacion/transformacion_20261126T061527349966Z_68284317199543fbb7b8f960224db1d0/corpus_solr.json"


def cargar_corpus(ruta):
    ruta = Path(ruta)
    raw = ruta.read_bytes()
    reporte = json.loads(ruta.with_name("reporte_transformacion.json").read_text(encoding="utf-8"))
    if reporte.get("estado") != "exitoso" or reporte.get("sha256_archivo_salida") != hashlib.sha256(raw).hexdigest():
        raise ValueError("El corpus no corresponde a una transformación validada exitosa")
    documentos = json.loads(raw.decode("utf-8"))
    # Reutiliza validadores sin ejecutar la transformación ni escribir sus artefactos.
    nuevos, _, validacion = transformar_corpus(documentos, incluir_metadatos=True)
    if nuevos != documentos:
        raise ValueError("El corpus requeriría transformación; se rechaza sin repararlo")
    return documentos, {"sha256_corpus": hashlib.sha256(raw).hexdigest(),
                        "resumen": validacion["resumen"],
                        "contrato_original": reporte.get("contrato"),
                        "contrato_verificado": str(CONTRATO.relative_to(PROYECTO)),
                        "sha256_contrato": hashlib.sha256(CONTRATO.read_bytes()).hexdigest()}


def seleccionar(documentos):
    # Orden fijo por categoría y URL, independiente del orden del archivo.
    return [deepcopy(min((d for d in documentos if d["categoria"] == categoria),
                         key=lambda d: d["id"])) for categoria in CUOTAS]


def consultar(**parametros):
    return obtener(CORE, "select", {"q": "*:*", "rows": 10, **parametros})


def exigir(condicion, mensaje):
    if not condicion:
        raise ValueError(mensaje)


def comprobar_entorno(documentos, respuesta):
    encontrados = respuesta["response"]
    ids = [d["id"] for d in encontrados["docs"]]
    esperados = {d["id"] for d in documentos}
    exigir(encontrados["numFound"] in (0, 3), "El core debe estar vacío o contener exactamente el mismo piloto")
    exigir(encontrados["numFound"] == 0 or (len(ids) == len(set(ids)) == 3 and set(ids) == esperados),
           "Hay documentos ajenos al piloto; no se borra ni se indexa nada")
    if ids:
        por_id = {d["id"]: d for d in encontrados["docs"]}
        exigir(all(all(por_id[d["id"]].get(k) == v for k, v in d.items()) for d in documentos),
               "El piloto existente difiere del corpus; no se sobrescribe")


def verificar(documentos):
    resultados = {}
    total = consultar(rows=10)
    comprobar_entorno(documentos, total)
    exigir(total["response"]["numFound"] == 3, "Se requieren exactamente tres documentos")
    resultados["recuento_y_documentos"] = total
    for doc in documentos:
        por_id = {d["id"]: d for d in total["response"]["docs"]}
        exigir(all(por_id[doc["id"]].get(k) == v for k, v in doc.items()), "Se alteraron campos almacenados")
        categoria = doc["categoria"]
        filtro = consultar(fq=f'categoria:"{categoria}"')
        exigir([d["id"] for d in filtro["response"]["docs"]] == [doc["id"]], "Filtro de categoría incorrecto")
        resultados[f"filtro_{categoria}"] = filtro
        for campo in ("titulo", "contenido"):
            # edismax recibe texto literal de cada documento sin interpolar sintaxis Lucene.
            texto = doc[campo] if campo == "titulo" else " ".join(doc[campo].split()[:50])
            parametros = dict(q=texto, defType="edismax", qf=campo, uf="-of-all-fields",
                              mm="1", sow="false", fq=f'categoria:"{categoria}"')
            respuesta = consultar(**parametros)
            exigir(doc["id"] in {d["id"] for d in respuesta["response"]["docs"]}, f"Sin coincidencia en {campo}: {categoria}")
            resultados[f"busqueda_{campo}_{categoria}"] = respuesta
    facetas = consultar(rows=0, facet="true", **{"facet.field": ["categoria", "tipo_fuente"], "facet.mincount": 1})
    campos = facetas["facet_counts"]["facet_fields"]
    for campo, esperado in (("categoria", {c: 1 for c in CUOTAS}), ("tipo_fuente", {"web": 3})):
        valores = campos[campo]
        exigir(dict(zip(valores[::2], valores[1::2])) == esperado, f"Facetas incorrectas: {campo}")
    resultados["facetas"] = facetas
    return resultados


def ejecutar(corpus=CORPUS, aplicar=False, salida=None):
    documentos, validacion = cargar_corpus(corpus)
    piloto = seleccionar(documentos)
    estado = instantanea()
    exigir(not planificar(estado), "Faltan campos: ejecutar primero configurar_esquema.py")
    analisis = comprobar_analizador()
    existentes = consultar(rows=10)
    comprobar_entorno(piloto, existentes)
    reporte = {"tarea": "P01-05", "fecha_utc": datetime.now(timezone.utc).isoformat(), "core": CORE,
               "corpus": str(Path(corpus).resolve().relative_to(PROYECTO)), "validacion_60": validacion,
               "seleccion": [{k: d[k] for k in ("id", "titulo", "url", "categoria")} for d in piloto],
               "antes": existentes, "aplicado": aplicar, "analisis_espanol": analisis}
    if aplicar:
        exigir(salida is not None, "Se requiere carpeta nueva --salida para evidencias")
        salida = Path(salida)
        salida.mkdir(parents=True, exist_ok=False)
        guardar_nuevo(salida / "preparacion.json", reporte)
        guardar_nuevo(salida / "piloto.json", piloto)
        # Segunda comprobación inmediatamente antes de escribir; nunca delete ni carga completa.
        comprobar_entorno(piloto, consultar(rows=10))
        reporte["update"] = enviar(CORE, "update", piloto)
        reporte["commit"] = enviar(CORE, "update", {"commit": {"waitSearcher": True}})
        reporte["verificaciones"] = verificar(piloto)
        despues = instantanea()
        exigir(protegidos(estado) == protegidos(despues), "Los analizadores cambiaron durante la prueba")
        exigir(not planificar(despues), "Esquema alterado durante la prueba")
        exigir(hashlib.sha256(Path(corpus).read_bytes()).hexdigest() == validacion["sha256_corpus"], "Corpus modificado durante la operación")
        reporte.update(estado="exitoso", tipos_protegidos_intactos=True, corpus_intacto=True)
        guardar_nuevo(salida / "evidencias.json", reporte)
    return reporte


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--salida", type=Path)
    args = parser.parse_args()
    if args.aplicar and args.salida is None:
        parser.error("--aplicar requiere --salida con una carpeta nueva")
    try:
        reporte = ejecutar(args.corpus, args.aplicar, args.salida)
        print(json.dumps({k: reporte[k] for k in ("aplicado", "seleccion", "validacion_60")}, ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"PILOTO DETENIDO: {exc}\n")


if __name__ == "__main__":
    main()
