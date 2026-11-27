"""P02-11: validar y planificar por defecto; aplicar solo tras integrar P05."""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

from configurar_esquema import (CORE, PROYECTO, CAMPOS_AUXILIARES_P05, COPIAS_P05,
                                instantanea, planificar, comprobar_analizador,
                                enviar, guardar_nuevo)
from indexar_piloto import (CORPUS, cargar_corpus, seleccionar, consultar, exigir,
                            transformar_corpus)
from transformar_corpus_mdn import OBLIGATORIOS, OPCIONALES, CUOTAS, fecha_solr

CONFIRMACION = "INDEXAR 60 DOCUMENTOS EN ri"


class IndexacionError(RuntimeError):
    def __init__(self, reporte, salida):
        self.reporte = reporte
        super().__init__(f"{reporte['error']}; evidencia: {salida / 'resultado.json'}")


def cargar_completo(corpus=CORPUS):
    documentos, validacion = cargar_corpus(corpus)
    ruta = Path(corpus).with_name("metadatos_crawler.json")
    raw = ruta.read_bytes()
    metadatos = json.loads(raw.decode("utf-8"))
    exigir(isinstance(metadatos, list), "Metadatos: se requiere un arreglo")
    por_id = {}
    for metadata in metadatos:
        exigir(isinstance(metadata, dict) and isinstance(metadata.get("id"), str),
               "Metadatos: objeto con id obligatorio")
        exigir(set(metadata) <= {"id", *OPCIONALES}, "Metadatos: campos inesperados")
        exigir(metadata["id"] not in por_id, "Metadatos: id duplicado")
        por_id[metadata["id"]] = metadata
    exigir(set(por_id) == {d["id"] for d in documentos}, "Metadatos sin correspondencia exacta con el corpus")
    completos = []
    for doc in documentos:
        metadata = por_id[doc["id"]]
        exigir(all(doc[k] == v for k, v in metadata.items() if k in doc),
               "Metadatos en conflicto con el corpus")
        completos.append({**doc, **metadata})
    nuevos, _, reporte = transformar_corpus(completos, incluir_metadatos=True)
    exigir(nuevos == completos, "Metadatos requieren transformación; fechas deben ser UTC Z con milisegundos")
    validacion.update(sha256_metadatos=hashlib.sha256(raw).hexdigest(),
                      sha256_reporte=hashlib.sha256(Path(corpus).with_name("reporte_transformacion.json").read_bytes()).hexdigest(),
                      resumen_completo=reporte["resumen"])
    return sorted(completos, key=lambda d: d["id"]), validacion


def revisar_esquema(estado):
    """Reutilizar el contrato de P01-05 y exigir además la instalación completa P05."""
    nuevos = planificar(estado)
    pendientes = [f"Campo ausente: {c['name']}" for c in nuevos]
    presentes = {c["name"] for c in estado["fields"]}
    pendientes += [f"P05: campo ausente {c['name']}" for c in CAMPOS_AUXILIARES_P05
                   if c["name"] not in presentes]
    copias = {(c["source"], c["dest"]) for c in estado["schema"].get("copyFields", [])}
    pendientes += [f"P05: copyField ausente {src} -> {dest}" for src, dest in sorted(COPIAS_P05 - copias)]
    return pendientes


def leer_indice():
    # rows=61 permite detectar incluso un documento ajeno, sin ocultar el total.
    return consultar(rows=61, sort="id asc", fl="*")


def comprobar_estado(documentos, respuesta):
    actual = respuesta["response"]
    docs = actual["docs"]
    ids = [d["id"] for d in docs]
    exigir(actual["numFound"] == len(ids) == len(set(ids)), "Estado incompleto, duplicado o inesperado del core")
    esperados = {d["id"] for d in documentos}
    piloto = seleccionar(documentos)
    exigir(set(ids) in (set(), {d["id"] for d in piloto}, esperados),
           "Documentos ajenos o lote parcial; se requiere core vacío, piloto esperado o los mismos 60 IDs")
    if len(ids) == 3:
        por_id = {d["id"]: d for d in docs}
        # El piloto se cargó sin metadatos: exigir sus valores originales obligatorios.
        exigir(all(all(por_id[d["id"]].get(k) == d[k] for k in OBLIGATORIOS) for d in piloto),
               "El piloto existente difiere del corpus aprobado")
    return set(ids)


def verificar(documentos):
    """Verificación completa de solo lectura, independiente de las pruebas del piloto."""
    resultados = {}
    total = leer_indice()
    comprobar_estado(documentos, total)
    exigir(total["response"]["numFound"] == 60, "Se requieren exactamente 60 documentos")
    actuales = {d["id"]: d for d in total["response"]["docs"]}
    exigir(Counter(d["categoria"] for d in actuales.values()) == CUOTAS, "Reparto distinto de 20/20/20")
    exigir(all(d["tipo_fuente"] == "web" for d in actuales.values()), "tipo_fuente debe ser web en los 60")
    for doc in documentos:
        actual = actuales[doc["id"]]
        # pdate puede serializar la misma fecha con distinta precisión textual.
        # Solr puede omitir enlaces_salientes cuando su lista no tiene valores.
        exigir(all((fecha_solr(actual.get(k)) == v if k == "fecha_rastreo"
                    else ((k == "enlaces_salientes" and v == [] and k not in actual)
                          or actual.get(k) == v)) for k, v in doc.items()),
               f"Campos o metadatos alterados: {doc['id']}")
        exigir(actuales[doc["id"]].get("titulo_sugerencia") == doc["titulo"],
               f"copyField de título sin valor preservado: {doc['id']}")
    resultados["documentos"] = total
    facetas = consultar(rows=0, facet="true", **{"facet.field": ["categoria", "tipo_fuente"], "facet.mincount": 1})
    for campo, esperado in (("categoria", CUOTAS), ("tipo_fuente", {"web": 60})):
        valores = facetas["facet_counts"]["facet_fields"][campo]
        exigir(dict(zip(valores[::2], valores[1::2])) == esperado, f"Facetas incorrectas: {campo}")
    resultados["facetas"] = facetas
    # Los dos auxiliares de contenido NO son stored: comprobar presencia en el índice invertido.
    resultados["auxiliares"] = {}
    for campo in ("titulo_sugerencia", "contenido_ortografia", "contenido_vocabulario"):
        respuesta = consultar(q=f"{campo}:[* TO *]", rows=0)
        exigir(respuesta["response"]["numFound"] == 60, f"P05 sin valores en los 60 documentos: {campo}")
        resultados["auxiliares"][campo] = respuesta
    consultas = []
    for doc in seleccionar(documentos):
        for campo in ("titulo", "contenido"):
            texto = doc[campo] if campo == "titulo" else " ".join(doc[campo].split()[:50])
            consultas.append((campo, texto, doc["id"]))
    for categoria in CUOTAS:
        doc = next(d for d in documentos if d["categoria"] == categoria)
        consultas.append(("contenido", categoria, doc["id"]))
    # Elegir un término acentuado real, con prueba de recuperación de su documento.
    acentuado = next(((d, re.search(r"\b[^\W\d_]*[áéíóúñ][^\W\d_]*\b", d["contenido"], re.I))
                      for d in documentos if re.search(r"\b[^\W\d_]*[áéíóúñ][^\W\d_]*\b", d["contenido"], re.I)), None)
    exigir(acentuado is not None, "No hay término acentuado para verificar")
    consultas.append(("contenido", acentuado[1].group(), acentuado[0]["id"]))
    resultados["busquedas"] = []
    for campo, texto, esperado in consultas:
        parametros = dict(q=texto, defType="edismax", qf=campo, uf="-of-all-fields",
                          mm="1", sow="false", rows=61, sort="score desc,id asc", fl="id,score")
        primera, segunda = consultar(**parametros), consultar(**parametros)
        exigir(esperado in {d["id"] for d in primera["response"]["docs"]}, f"Búsqueda sin documento esperado: {texto[:80]}")
        exigir(primera["response"] == segunda["response"], "Resultados inconsistentes al repetir consulta")
        resultados["busquedas"].append({"parametros": parametros, "esperado": esperado,
                                       "primera": primera, "segunda": segunda})
    return resultados


def respuesta_exitosa(respuesta):
    exigir(respuesta.get("responseHeader", {}).get("status") == 0 and "error" not in respuesta,
           f"Solr no confirmó la operación: {respuesta}")


def ejecutar(corpus=CORPUS, aplicar=False, confirmacion=None, salida=None):
    # Reservar evidencias antes de cualquier operación. Nunca sobrescribir una ejecución.
    salida = Path(salida) if salida else PROYECTO / "indexacion/evidencias/p02-11" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + uuid4().hex)
    salida = salida.resolve()
    exigir(salida.is_relative_to(PROYECTO) and not salida.is_relative_to(PROYECTO / "data"),
           "Las evidencias deben estar dentro del proyecto y fuera de data/")
    salida.mkdir(parents=True, exist_ok=False)
    reporte = dict(tarea="P02-11", core=CORE, modo="aplicar" if aplicar else "prueba",
                   fecha_utc=datetime.now(timezone.utc).isoformat(), estado="iniciado",
                   escritura_intentada=False, commit_confirmado=False, bloqueos=[], salida=str(salida))
    try:
        exigir(not aplicar or confirmacion == CONFIRMACION, "Falta confirmación explícita para modificar ri")
        documentos, validacion = cargar_completo(corpus)
        reporte["validacion"] = validacion
        reporte["corpus"] = str(Path(corpus).resolve())
        reporte["plan"] = [{**{k: d[k] for k in ("id", "titulo", "categoria")},
                            "accion": "pendiente_inspeccion_solr"} for d in documentos]
        try:
            estado = instantanea()
        except (OSError, RuntimeError) as exc:
            if aplicar:
                raise
            reporte["bloqueos"].append(f"Solr no disponible: {exc}")
            reporte["estado"] = "prueba_local_solr_no_disponible"
        else:
            reporte["esquema_antes"] = estado
            reporte["bloqueos"] = revisar_esquema(estado)
            reporte["analisis_espanol"] = comprobar_analizador()
            antes = leer_indice()
            reporte["antes"] = antes
            ids = comprobar_estado(documentos, antes)
            for doc in reporte["plan"]:
                doc["accion"] = "sustituir" if doc["id"] in ids else "crear"
            reporte["estado"] = "prueba_bloqueada" if reporte["bloqueos"] else "prueba_lista"
            if aplicar:
                exigir(not reporte["bloqueos"], "; ".join(reporte["bloqueos"]))
                guardar_nuevo(salida / "preparacion.json", reporte)
                guardar_nuevo(salida / "documentos.json", documentos)
                # Revisar otra vez justo antes del update; requiere ausencia de escritores concurrentes.
                exigir(instantanea() == estado, "El esquema cambió antes de escribir")
                comprobar_estado(documentos, leer_indice())
                exigir(cargar_completo(corpus) == (documentos, validacion), "Los archivos de entrada cambiaron")
                reporte["escritura_intentada"] = True
                # Lista de documentos normales: sustitución completa por uniqueKey; nunca actualizaciones atómicas.
                reporte["update"] = enviar(CORE, "update", documentos, parametros={"overwrite": "true"})
                respuesta_exitosa(reporte["update"])
                reporte["commit"] = enviar(CORE, "update", {"commit": {"waitSearcher": True}})
                respuesta_exitosa(reporte["commit"])
                reporte["commit_confirmado"] = True
                reporte["verificacion"] = verificar(documentos)
                exigir(instantanea() == estado, "El esquema cambió durante la operación")
                exigir(cargar_completo(corpus) == (documentos, validacion), "Los archivos de entrada cambiaron")
                reporte["estado"] = "carga_verificada"
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        reporte.update(estado="error", error=str(exc))
        try:
            reporte["estado_tras_error"] = leer_indice()
        except (OSError, ValueError, RuntimeError, KeyError, TypeError) as lectura:
            reporte["error_lectura_estado"] = str(lectura)
        guardar_nuevo(salida / "resultado.json", reporte)
        raise IndexacionError(reporte, salida) from exc
    guardar_nuevo(salida / "resultado.json", reporte)
    return reporte


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=CORPUS)
    parser.add_argument("--salida", type=Path, help="Carpeta nueva de evidencias")
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--confirmar", help=f"Confirmación literal: {CONFIRMACION}")
    args = parser.parse_args()
    if args.aplicar and args.confirmar != CONFIRMACION:
        parser.error(f'--aplicar requiere --confirmar "{CONFIRMACION}"')
    try:
        reporte = ejecutar(args.corpus, args.aplicar, args.confirmar, args.salida)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"INDEXACIÓN DETENIDA: {exc}\n")
    print(json.dumps({k: reporte[k] for k in ("estado", "validacion", "bloqueos", "plan", "salida")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
