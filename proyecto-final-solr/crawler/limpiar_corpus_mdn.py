"""P02-07: limpieza conservadora y local; nunca solicita páginas ni indexa."""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4


PROYECTO = Path(__file__).resolve().parents[1]
ENTRADA = PROYECTO / "data/mdn/ejecuciones/corpus_20261123T224903260669Z_b2f55364aeef4f189bdaf1e69021058e/corpus.json"
VERSION_REGLAS = "P02-07-v1"
CSS_INTERFAZ = (
    "*,:after,:before{box-sizing:border-box}button,input,select,textarea{font:inherit}"
    "button{color:inherit;cursor:pointer}img{height:auto;max-width:100%}"
    "a{color:var(--color-link-normal)}[hidden]{display:none!important}"
    "#content{scroll-margin-block-start:var(--sticky-header-height)}"
)
AVISO_COMPATIBILIDAD = "Activa JavaScript para ver esta tabla de compatibilidad con navegadores."
CABECERAS = ("Compatibilidad con navegadores", "Compatibilidad con los navegadores")
# Solo se elimina el bloque completo con límites de párrafo y ambos testigos.
# No se buscan selectores CSS genéricos ni se interpreta el texto como HTML.
BLOQUE_INTERFAZ = re.compile(
    r"(?:\A|(?<=\n\n))(?:" + "|".join(map(re.escape, CABECERAS)) + r")\n\n"
    + re.escape(CSS_INTERFAZ) + r"\n\n" + re.escape(AVISO_COMPATIBILIDAD)
    + r"(?=\n\n|\Z)"
)
AMBIGUOS = {
    "css_interfaz_sin_contexto": ("--sticky-header-height", "Posible CSS de interfaz sin la secuencia exacta: conservar."),
    "aviso_compatibilidad_aislado": (AVISO_COMPATIBILIDAD, "Aviso sin contexto suficiente: conservar."),
    "resumen_ingles_repetido": ("CSS Key Concepts:", "Puede ser resumen editorial o navegación; revisar manualmente."),
    "aviso_documento_antiguo": ("¡Estamos en obras!", "Posible aviso editorial antiguo; no eliminar automáticamente."),
    "taxonomia_antigua": ("interwiki links", "Posible taxonomía o texto histórico; revisar manualmente."),
    "taxonomia_idiomas": ("Interwiki Languages", "Posible taxonomía o referencia editorial; revisar manualmente."),
}
CAMPOS = {
    "id", "url", "titulo", "contenido", "titulo_original", "titulo_descriptivo",
    "titulo_documento", "enlaces_salientes", "idioma", "categoria", "fuente", "tipo_fuente",
    "profundidad", "fecha_rastreo", "atribucion", "descubierta_desde", "tipo_documento",
    "sha256_contenido", "sha256_contenido_normalizado",
}
MODIFICABLES = {"contenido", "sha256_contenido", "sha256_contenido_normalizado"}


def sha256(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def sha256_normalizado(texto):
    return sha256(re.sub(r"\s+", " ", texto).strip().casefold())


def limpiar_texto(texto):
    """Devolver texto y eliminaciones con posiciones en el texto ORIGINAL."""
    eliminaciones = []
    for match in BLOQUE_INTERFAZ.finditer(texto):
        inicio, fin = match.span()
        # Consumir solo un separador vecino para no unir párrafos ni dejar
        # cuatro saltos. Nunca normalizar globalmente espacios o código.
        if texto[fin:fin + 2] == "\n\n":
            fin += 2
        elif texto[max(0, inicio - 2):inicio] == "\n\n":
            inicio -= 2
        if eliminaciones and inicio < eliminaciones[-1]["fin"]:
            inicio = eliminaciones[-1]["fin"]
        eliminaciones.append({"regla": "compatibilidad_sin_datos_css_interfaz_exacto",
                              "inicio": inicio, "fin": fin, "texto_eliminado": texto[inicio:fin]})
    limpio, cursor = [], 0
    for cambio in eliminaciones:
        limpio.append(texto[cursor:cambio["inicio"]])
        cursor = cambio["fin"]
    limpio.append(texto[cursor:])
    return "".join(limpio), eliminaciones


def advertencias(texto):
    resultado = []
    for nombre, (marca, motivo) in AMBIGUOS.items():
        for match in re.finditer(re.escape(marca), texto):
            resultado.append({"patron": nombre, "inicio_en_texto_limpio": match.start(),
                              "accion": "conservado_para_revision_manual", "motivo": motivo,
                              "contexto": texto[max(0, match.start() - 80):match.end() + 240]})
    return resultado


def procesar_corpus(documentos, esperados=60):
    if not isinstance(documentos, list) or len(documentos) != esperados:
        raise ValueError(f"Se esperaba una lista de {esperados} documentos")
    ids, urls = set(), set()
    # Validar todo ANTES de derivar una salida. Un hash incorrecto no se repara
    # silenciosamente porque rompería la trazabilidad del corpus de entrada.
    for doc in documentos:
        if not isinstance(doc, dict) or not CAMPOS <= doc.keys():
            raise ValueError("Documento con esquema incompleto")
        if not all(isinstance(doc[k], str) and doc[k] for k in ("id", "url", "contenido")):
            raise ValueError("id, url y contenido deben ser cadenas no vacías")
        if doc["id"] in ids or doc["url"] in urls:
            raise ValueError("IDs o URLs duplicados en el corpus de entrada")
        ids.add(doc["id"])
        urls.add(doc["url"])
        if doc["categoria"] not in {"JavaScript", "HTML", "CSS"}:
            raise ValueError("Categoría de entrada desconocida")
        if (doc["sha256_contenido"] != sha256(doc["contenido"])
                or doc["sha256_contenido_normalizado"] != sha256_normalizado(doc["contenido"])):
            raise ValueError(f"Hash de entrada inconsistente: {doc['url']}")
    nuevos, detalles = [], []
    for original in documentos:
        doc = deepcopy(original)
        texto, cambios = limpiar_texto(original["contenido"])
        if not texto.strip():
            raise ValueError(f"La limpieza dejaría un documento vacío: {original['url']}")
        doc["contenido"] = texto
        doc["sha256_contenido"] = sha256(texto)
        doc["sha256_contenido_normalizado"] = sha256_normalizado(texto)
        nuevos.append(doc)
        detalles.append({
            "id": doc["id"], "url": doc["url"], "categoria": doc["categoria"],
            "modificado": bool(cambios), "caracteres_antes": len(original["contenido"]),
            "caracteres_despues": len(texto), "caracteres_eliminados": len(original["contenido"]) - len(texto),
            "sha256_antes": original["sha256_contenido"], "sha256_despues": doc["sha256_contenido"],
            "sha256_normalizado_antes": original["sha256_contenido_normalizado"],
            "sha256_normalizado_despues": doc["sha256_contenido_normalizado"],
            "eliminaciones": cambios, "advertencias": advertencias(texto),
        })
    duplicados = defaultdict(list)
    for doc in nuevos:
        duplicados[doc["sha256_contenido_normalizado"]].append(doc["url"])
    resumen = {
        "total_documentos": len(nuevos), "modificados": sum(d["modificado"] for d in detalles),
        "sin_cambios": sum(not d["modificado"] for d in detalles), "rechazados": 0,
        "categorias": dict(Counter(d["categoria"] for d in nuevos)),
        "modificados_por_categoria": dict(Counter(d["categoria"] for d in detalles if d["modificado"])),
        "caracteres_eliminados": sum(d["caracteres_eliminados"] for d in detalles),
        "bloques_eliminados": sum(len(d["eliminaciones"]) for d in detalles),
        "documentos_con_advertencias": sum(bool(d["advertencias"]) for d in detalles),
        "advertencias_por_patron": dict(Counter(a["patron"] for d in detalles for a in d["advertencias"])),
        "duplicados_normalizados_despues": [urls for urls in duplicados.values() if len(urls) > 1],
    }
    return nuevos, {"resumen": resumen, "documentos": detalles}


def ruta_reporte(ruta):
    """Rutas internas relativas al proyecto y con separadores portables."""
    ruta = Path(ruta).resolve()
    try:
        return ruta.relative_to(PROYECTO).as_posix()
    except ValueError:
        return ruta.as_posix()


def ejecutar_limpieza(entrada=ENTRADA, salida=None, esperados=60):
    entrada = Path(entrada).resolve()
    raw = entrada.read_bytes()
    documentos = json.loads(raw.decode("utf-8-sig"))
    nuevos, reporte = procesar_corpus(documentos, esperados)
    if salida is None:
        nombre = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        salida = PROYECTO / "data/mdn/limpieza" / f"limpieza_{nombre}_{uuid4().hex}"
    salida = Path(salida).resolve()
    # Una salida siempre es una carpeta nueva y no puede ser el propio corpus.
    salida.mkdir(parents=True, exist_ok=False)
    reporte.update({
        "operacion": "limpieza_local_sin_red", "version_reglas": VERSION_REGLAS,
        "fecha_limpieza": datetime.now(timezone.utc).isoformat(),
        "archivo_entrada": ruta_reporte(entrada), "sha256_archivo_entrada": hashlib.sha256(raw).hexdigest(),
        "archivo_salida": ruta_reporte(salida / "corpus_limpio.json"),
        "campos_modificables": sorted(MODIFICABLES),
        "preservacion": "Mismo orden, cantidad, IDs, esquema y metadatos; fecha_rastreo original intacta.",
        "limite": "Solo firma CSS exacta con cabecera y aviso de compatibilidad; sin reconstrucción del DOM.",
    })
    for nombre, datos in (("corpus_limpio.json", nuevos), ("reporte_limpieza.json", reporte)):
        with (salida / nombre).open("x", encoding="utf-8", newline="\n") as archivo:
            archivo.write(json.dumps(datos, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(reporte["resumen"], ensure_ascii=False, indent=2))
    print(f"Salida: {salida}")
    return salida


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=ENTRADA)
    parser.add_argument("--salida", type=Path, help="Carpeta NUEVA dentro del proyecto; por defecto se genera una única")
    parser.add_argument("--esperados", type=int, default=60)
    args = parser.parse_args()
    if args.esperados < 1:
        parser.error("--esperados debe ser positivo")
    if args.salida and not args.salida.resolve().is_relative_to(PROYECTO):
        parser.error("--salida debe estar dentro de proyecto-final-solr/")
    try:
        ejecutar_limpieza(args.entrada, args.salida, args.esperados)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"LIMPIEZA DETENIDA: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
