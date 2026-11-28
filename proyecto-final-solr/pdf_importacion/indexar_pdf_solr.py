"""P07-04: importación PDF idempotente en el core ``ri``.

Modo predeterminado: SOLO LECTURA (preflight). Para escribir, se necesitan
--aplicar y una frase exacta. No borra documentos, no crea esquemas ni cores.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from pdf_importacion.documento_solr import (
    CAMPOS, ErrorDocumentoPDF, convertir_pdf_a_documento, validar_documento_pdf,
)

BASE = "http://localhost:8983/solr"
CORE = "ri"
CONFIRMACION = "INDEXAR PDF EN ri"
CAMPOS_MD = ("id", "categoria", "tipo_fuente")


class ErrorIndicePDF(RuntimeError):
    pass


def _json_http(metodo: str, url: str, cuerpo=None):
    datos = None if cuerpo is None else json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
    peticion = Request(url, data=datos, method=metodo,
                       headers={"Content-Type": "application/json; charset=utf-8", "Accept": "application/json"})
    try:
        with urlopen(peticion, timeout=20) as respuesta:
            salida = json.loads(respuesta.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        raise ErrorIndicePDF(f"Solr no respondió correctamente: {exc}") from exc
    if salida.get("responseHeader", {}).get("status", 0) != 0:
        raise ErrorIndicePDF(f"Solr respondió con error: {salida}")
    return salida


def _consultar(endpoint: str, params: dict):
    return _json_http("GET", f"{BASE}/{CORE}/{endpoint}?" + urlencode(params))


def _ids_mdn_aprobados() -> dict[str, str]:
    """Usa el corpus aprobado de la transformación, sin acceso al crawler ni a MDN."""
    root = Path(__file__).resolve().parents[1]
    ruta = root / "data/mdn/transformacion/transformacion_20261126T061527349966Z_68284317199543fbb7b8f960224db1d0/corpus_solr.json"
    if not ruta.is_file():
        raise ErrorIndicePDF(f"Falta el corpus aprobado; no se autoriza escribir: {ruta}")
    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ErrorIndicePDF("No se puede leer el corpus MDN aprobado") from exc
    if not isinstance(contenido, list) or len(contenido) != 60:
        raise ErrorIndicePDF("El corpus aprobado no contiene exactamente 60 documentos")
    ids = {}
    for doc in contenido:
        if not isinstance(doc, dict) or not isinstance(doc.get("id"), str) or doc.get("categoria") not in {"JavaScript", "HTML", "CSS"} or doc.get("tipo_fuente") != "web" or doc["id"] in ids:
            raise ErrorIndicePDF("IDs o categorías inválidos en el corpus aprobado")
        ids[doc["id"]] = doc["categoria"]
    if sorted(ids.values()).count("CSS") != 20 or sorted(ids.values()).count("HTML") != 20 or sorted(ids.values()).count("JavaScript") != 20:
        raise ErrorIndicePDF("Cuotas 20/20/20 del corpus aprobado inválidas")
    return ids


def _solr_por_ids(ids: list[str], campos: str):
    if not ids:
        return []
    # {!terms} evita que los caracteres de la URL o del hash se interpreten como operadores.
    encontrados = _consultar("select", {"q": "{!terms f=id}" + ",".join(ids), "rows": len(ids), "fl": campos, "wt": "json"})["response"]
    return encontrados["docs"]


def _validar_60_mdn():
    ids = _ids_mdn_aprobados()
    docs = _solr_por_ids(list(ids), ",".join(CAMPOS_MD))
    hallados = {}
    for d in docs:
        if d.get("id") in hallados:
            raise ErrorIndicePDF("Solr devolvió un ID MDN duplicado")
        hallados[d.get("id")] = d
    if set(hallados) != set(ids):
        faltan = list(set(ids)-set(hallados))
        raise ErrorIndicePDF(f"Índice no contiene los 60 MDN aprobados; faltan {len(faltan)}")
    for ident, cat in ids.items():
        d = hallados[ident]
        if d.get("categoria") != cat or d.get("tipo_fuente") != "web":
            raise ErrorIndicePDF(f"MDN alterado en ri: {ident}")
    return ids


def _validar_esquema():
    salida = _consultar("schema/fields", {"wt": "json"})
    campos = {x["name"]: x for x in salida.get("fields", [])}
    for campo in CAMPOS:
        if campo not in campos or not campos[campo].get("stored") or not campos[campo].get("indexed"):
            raise ErrorIndicePDF(f"Campo Solr obligatorio no disponible: {campo}")
    for campo in ("categoria", "tipo_fuente"):
        if not campos[campo].get("docValues") or campos[campo].get("multiValued"):
            raise ErrorIndicePDF(f"Faceta incompatible: {campo}")
    for campo in ("titulo", "contenido"):
        if campos[campo].get("type") != "text_es_proyecto":
            raise ErrorIndicePDF(f"Analizador no definitivo en campo {campo}")


def _normalizar_solr(doc: dict) -> dict:
    return {k: (v[0] if isinstance(v, list) and len(v) == 1 else v) for k, v in doc.items()}


def _preflight(documento: dict):
    validar_documento_pdf(documento)
    _validar_esquema()
    _validar_60_mdn()
    actuales = _solr_por_ids([documento["id"]], ",".join(sorted(CAMPOS)))
    if len(actuales) > 1:
        raise ErrorIndicePDF("Solr devolvió múltiples registros con el mismo ID")
    if actuales:
        ya = _normalizar_solr(actuales[0])
        if any(ya.get(k) != documento[k] for k in CAMPOS):
            raise ErrorIndicePDF("ID PDF ya existe con contenido o metadatos diferentes; se requiere revisión manual")
        return "existente"
    return "nuevo"


def importar_documento_pdf(documento: dict, *, aplicar: bool = False, confirmar: str = "") -> dict:
    """Función reutilizable por FastAPI; no importa dependencias HTTP del backend.

    Verifica 60 MDN y esquema antes de escribir. No garantiza aislamiento si
    otra aplicación escribe simultáneamente en Solr: usar un solo escritor.
    """
    if aplicar and confirmar != CONFIRMACION:
        raise ErrorIndicePDF(f"Falta confirmación explícita: {CONFIRMACION!r}")
    estado = _preflight(documento)
    if not aplicar:
        return {"estado": "simulacion", "accion": "omitir" if estado == "existente" else "crear", "id": documento["id"]}
    if estado == "existente":
        return {"estado": "ya_indexado", "id": documento["id"]}
    url = f"{BASE}/{CORE}/update?" + urlencode({"overwrite": "true", "wt": "json"})
    _json_http("POST", url, [documento])
    _json_http("POST", f"{BASE}/{CORE}/update?wt=json", {"commit": {"waitSearcher": True}})
    # Comprobación de estado después de commit, sin reintento automático.
    if _preflight(documento) != "existente":
        raise ErrorIndicePDF("No se pudo confirmar el PDF tras el commit; revisar ri manualmente")
    return {"estado": "indexado_verificado", "id": documento["id"]}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archivo", type=Path, help="PDF con texto seleccionable")
    p.add_argument("--titulo", help="Título explícito; de otro modo se deriva del nombre")
    p.add_argument("--categoria", choices=sorted({"JavaScript", "HTML", "CSS", "General"}), default="General")
    p.add_argument("--aplicar", action="store_true", help="Habilita POST únicamente con --confirmar")
    p.add_argument("--solo-documento", action="store_true", help="P07-03: genera JSON, sin conectarse a Solr")
    p.add_argument("--confirmar", default="", help=f'Frase exacta: {CONFIRMACION}')
    p.add_argument("--json-salida", type=Path, help="Guardar documento JSON en archivo NUEVO, no sobrescribe")
    a = p.parse_args(argv)
    try:
        doc = convertir_pdf_a_documento(a.archivo, titulo=a.titulo, categoria=a.categoria)
        if a.json_salida:
            with a.json_salida.open("x", encoding="utf-8") as f:
                json.dump(doc, f, ensure_ascii=False, indent=2)
                f.write("\n")
        if a.solo_documento:
            if a.aplicar:
                raise ErrorIndicePDF("--solo-documento no admite --aplicar")
            resultado = {"estado": "documento_local_generado", "id": doc["id"], "categoria": doc["categoria"], "caracteres": len(doc["contenido"])}
        else:
            resultado = importar_documento_pdf(doc, aplicar=a.aplicar, confirmar=a.confirmar)
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0
    except (ErrorDocumentoPDF, ErrorIndicePDF, OSError, FileExistsError) as e:
        print(f"Importación detenida: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
