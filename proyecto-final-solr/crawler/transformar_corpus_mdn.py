"""P02-09: transformar y validar el corpus limpio local, sin indexar en Solr."""

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from uuid import uuid4

from limpiar_corpus_mdn import sha256, sha256_normalizado, ruta_reporte
from mdn_piloto import PilotoError, normalizar_url, validar_url


PROYECTO = Path(__file__).resolve().parents[1]
ENTRADA = PROYECTO / "data/mdn/limpieza/limpieza_20261125T043642044138Z_c21372d7d7c14eaa9055b2593fd866be/corpus_limpio.json"
CONTRATO = PROYECTO / "docs/P00-03_contrato_solr_v1.1.md"
VERSION_REGLAS = "P02-09-v1"
OBLIGATORIOS = ("id", "titulo", "contenido", "categoria", "tipo_fuente", "fuente", "idioma", "url")
OPCIONALES = (
    "atribucion", "profundidad", "fecha_rastreo", "enlaces_salientes",
    "descubierta_desde", "tipo_documento", "titulo_original", "titulo_descriptivo",
    "titulo_documento", "sha256_contenido", "sha256_contenido_normalizado", "pagerank",
)
CUOTAS = {"JavaScript": 20, "HTML": 20, "CSS": 20}


class TransformacionError(ValueError):
    """Fallo de lote completo con comprobaciones serializables."""

    def __init__(self, reporte):
        self.reporte = reporte
        super().__init__(json.dumps(reporte["errores"], ensure_ascii=False))


def fecha_solr(valor):
    """ISO 8601 con zona explícita → UTC Z, precisión de milisegundos de pdate."""
    if not isinstance(valor, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", valor
    ):
        raise ValueError("fecha_rastreo requiere ISO 8601 con hora y zona explícita")
    fecha = datetime.fromisoformat(valor.replace("Z", "+00:00")).astimezone(timezone.utc)
    return fecha.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def url_mdn(valor):
    if not isinstance(valor, str) or not valor or any(c.isspace() for c in valor):
        raise ValueError("se requiere URL MDN normalizada sin espacios")
    try:
        if normalizar_url(valor) != valor:
            raise ValueError("URL MDN sin normalizar")
        return validar_url(valor)
    except PilotoError as exc:
        raise ValueError(str(exc)) from exc


def transformar_documento(doc):
    """Validar sin reparar datos; devolver campos mínimos y metadatos separados."""
    if not isinstance(doc, dict):
        raise ValueError("el documento debe ser un objeto JSON")
    inesperados = set(doc) - set(OBLIGATORIOS) - set(OPCIONALES)
    if inesperados:
        raise ValueError(f"campos fuera de P00-03: {sorted(inesperados)}")
    for campo in OBLIGATORIOS:
        if not isinstance(doc.get(campo), str) or not doc[campo].strip():
            raise ValueError(f"{campo}: cadena obligatoria no vacía")
    if doc["categoria"] not in CUOTAS:
        raise ValueError("categoria: se requiere JavaScript, HTML o CSS para MDN")
    if doc["idioma"] != "es" or doc["tipo_fuente"] != "web" or doc["fuente"] != "MDN Web Docs":
        raise ValueError("MDN requiere idioma=es, tipo_fuente=web y fuente=MDN Web Docs")
    if doc["id"] != doc["url"]:
        raise ValueError("id debe ser la URL normalizada del crawler")
    if url_mdn(doc["url"]) != doc["categoria"]:
        raise ValueError("categoria no corresponde con la ruta de la URL")
    metadata = {}
    for campo in OPCIONALES:
        valor = doc.get(campo)
        # Ausentes y null significan ausencia, por ejemplo las tres semillas.
        if valor is None:
            continue
        if campo == "fecha_rastreo":
            valor = fecha_solr(valor)
        elif campo == "profundidad":
            if type(valor) is not int or not 0 <= valor <= 2**31 - 1:
                raise ValueError("profundidad: entero pint no negativo")
        elif campo == "pagerank":
            if type(valor) not in (int, float) or not math.isfinite(valor) or valor < 0:
                raise ValueError("pagerank: número finito no negativo")
        elif campo == "enlaces_salientes":
            if not isinstance(valor, list):
                raise ValueError("enlaces_salientes: se requiere un arreglo multivaluado")
            for enlace in valor:
                url_mdn(enlace)
        else:
            if not isinstance(valor, str) or not valor.strip():
                raise ValueError(f"{campo}: cadena no vacía")
            if campo == "descubierta_desde":
                url_mdn(valor)
            elif campo == "tipo_documento" and valor not in {"indice", "articulo_explicativo"}:
                raise ValueError("tipo_documento desconocido del crawler MDN")
            elif campo.startswith("sha256_"):
                esperado = (sha256(doc["contenido"]) if campo == "sha256_contenido"
                            else sha256_normalizado(doc["contenido"]))
                if valor != esperado:
                    raise ValueError(f"{campo}: hash no corresponde al contenido limpio")
        metadata[campo] = deepcopy(valor)
    return {campo: doc[campo] for campo in OBLIGATORIOS}, metadata


def transformar_corpus(documentos, incluir_metadatos=False):
    errores, nuevos, metadatos, detalles = [], [], [], []
    ids = set()
    categorias = Counter()
    if not isinstance(documentos, list):
        documentos = []
        errores.append({"motivo": "la raíz debe ser un arreglo JSON"})
    if len(documentos) != 60:
        errores.append({"motivo": f"se requieren exactamente 60 documentos; recibidos: {len(documentos)}"})
    for indice, doc in enumerate(documentos):
        try:
            minimo, metadata = transformar_documento(doc)
            if minimo["id"] in ids:
                raise ValueError("id duplicado")
            ids.add(minimo["id"])
            categorias[minimo["categoria"]] += 1
            nuevos.append({**minimo, **metadata} if incluir_metadatos else minimo)
            metadatos.append({"id": minimo["id"], **metadata})
            detalles.append({
                "indice": indice, "id": minimo["id"],
                "id_titulo_contenido_preservados": all(nuevos[-1][k] == doc[k] for k in ("id", "titulo", "contenido")),
                "caracteres_contenido": len(minimo["contenido"]),
                "sha256_contenido": sha256(minimo["contenido"]),
                "fecha_original": doc.get("fecha_rastreo"),
                "fecha_solr": metadata.get("fecha_rastreo"),
                "total_enlaces": len(metadata.get("enlaces_salientes", [])),
            })
        except (ValueError, OverflowError) as exc:
            errores.append({"indice": indice, "id": doc.get("id") if isinstance(doc, dict) else None,
                            "motivo": str(exc)})
    if dict(categorias) != CUOTAS:
        errores.append({"motivo": "se requiere reparto 20/20/20 entre documentos válidos", "categorias_validas": dict(categorias)})
    reporte = {
        "estado": "rechazado" if errores else "exitoso",
        "version_reglas": VERSION_REGLAS,
        "contrato": ruta_reporte(CONTRATO),
        "sha256_contrato": hashlib.sha256(CONTRATO.read_bytes()).hexdigest(),
        "modo_metadatos": "incluidos" if incluir_metadatos else "separados",
        "campos_obligatorios": list(OBLIGATORIOS), "campos_opcionales_autorizados": list(OPCIONALES),
        "facetas": ["categoria", "tipo_fuente"],
        "politica_fecha": "UTC Z con milisegundos; se truncan microsegundos inferiores al milisegundo",
        "resumen": {"total_entrada": len(documentos), "documentos_validos": len(nuevos),
                    "documentos_transformados": 0 if errores else len(nuevos),
                    "ids_unicos_validos": len(ids), "categorias_validas": dict(categorias)},
        "comprobaciones": {
            "cantidad_60": len(documentos) == 60, "cuotas_20_20_20": dict(categorias) == CUOTAS,
            "todos_documentos_validos": not errores,
            "preservacion_id_titulo_contenido": len(detalles) == len(documentos) and all(d["id_titulo_contenido_preservados"] for d in detalles),
        },
        "errores": errores, "documentos": detalles,
    }
    if errores:
        raise TransformacionError(reporte)
    return nuevos, metadatos, reporte


def serializar(datos):
    return (json.dumps(datos, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def ejecutar_transformacion(entrada=ENTRADA, salida=None, incluir_metadatos=False):
    entrada = Path(entrada).resolve()
    raw = entrada.read_bytes()
    fallo = None
    try:
        documentos = json.loads(raw.decode("utf-8-sig"))
        nuevos, metadatos, reporte = transformar_corpus(documentos, incluir_metadatos)
    except (UnicodeError, ValueError) as exc:
        fallo = exc
        reporte = (exc.reporte if isinstance(exc, TransformacionError) else
                   {"estado": "rechazado", "version_reglas": VERSION_REGLAS,
                    "errores": [{"motivo": f"JSON de entrada inválido: {exc}"}]})
    if salida is None:
        nombre = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        salida = PROYECTO / "data/mdn/transformacion" / f"transformacion_{nombre}_{uuid4().hex}"
    salida = Path(salida).resolve()
    # Protección también para quienes llaman directamente al módulo, no solo CLI.
    if not salida.is_relative_to(PROYECTO):
        raise ValueError("--salida debe estar dentro de proyecto-final-solr/")
    salida.mkdir(parents=True, exist_ok=False)
    reporte.update({
        "operacion": "transformacion_local_sin_red_sin_indexacion",
        "fecha_transformacion": datetime.now(timezone.utc).isoformat(),
        "archivo_entrada": ruta_reporte(entrada),
        "sha256_archivo_entrada": hashlib.sha256(raw).hexdigest(),
        "archivo_salida": None, "sha256_archivo_salida": None,
    })
    try:
        if entrada.read_bytes() != raw:
            raise OSError("el archivo de entrada cambió durante la transformación")
        reporte["entrada_intacta"] = True
        if fallo is None:
            corpus_bytes = serializar(nuevos)
            with (salida / "metadatos_crawler.json").open("xb") as archivo:
                archivo.write(serializar(metadatos))
            with (salida / "corpus_solr.json").open("xb") as archivo:
                archivo.write(corpus_bytes)
            reporte.update({"archivo_salida": ruta_reporte(salida / "corpus_solr.json"),
                            "sha256_archivo_salida": hashlib.sha256(corpus_bytes).hexdigest(),
                            "archivo_metadatos": ruta_reporte(salida / "metadatos_crawler.json")})
    except OSError as exc:
        fallo = exc
        reporte["estado"] = "rechazado"
        if "resumen" in reporte:
            reporte["resumen"]["documentos_transformados"] = 0
        reporte["errores"].append({"motivo": str(exc)})
    # El reporte exitoso se escribe al final: sin él, una ejecución no es aprobada.
    with (salida / "reporte_transformacion.json").open("xb") as archivo:
        archivo.write(serializar(reporte))
    if fallo is not None:
        print(f"Reporte de rechazo: {salida / 'reporte_transformacion.json'}")
        raise TransformacionError(reporte)
    print(json.dumps(reporte["resumen"], ensure_ascii=False, indent=2))
    print(f"Salida: {salida}")
    return salida


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=ENTRADA)
    parser.add_argument("--salida", type=Path, help="Carpeta NUEVA dentro del proyecto")
    parser.add_argument("--incluir-metadatos", action="store_true",
                        help="Incluir opcionales P00-03; requiere definir esos campos en el futuro esquema")
    args = parser.parse_args()
    try:
        ejecutar_transformacion(args.entrada, args.salida, args.incluir_metadatos)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"TRANSFORMACIÓN DETENIDA: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
