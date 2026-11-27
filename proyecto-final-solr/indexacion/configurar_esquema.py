"""P01-05: agregar únicamente campos compatibles con P00-03 v1.2 al core ri."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

PROYECTO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROYECTO / "analisis_es"))
from solr_cliente import obtener, enviar  # noqa: E402

CORE = "ri"
CONTRATO = PROYECTO / "docs/P00-03_contrato_solr_v1.2.md"
TIPOS_PROTEGIDOS = ("text_es_ri", "text_es_proyecto")


def campo(nombre, tipo="string", obligatorio=False, faceta=False, multiple=False):
    definicion = dict(name=nombre, type=tipo, stored=True, indexed=True,
                      required=obligatorio, multiValued=multiple)
    if faceta:
        definicion["docValues"] = True
    return definicion


CAMPOS = [
    campo("id", obligatorio=True),
    campo("titulo", "text_es_proyecto", True),
    campo("contenido", "text_es_proyecto", True),
    campo("categoria", obligatorio=True, faceta=True),
    campo("tipo_fuente", obligatorio=True, faceta=True),
    campo("fuente", obligatorio=True), campo("idioma", obligatorio=True),
    campo("url"),  # Solo obligatorio para web: se valida en el documento.
    campo("atribucion"), campo("profundidad", "pint"), campo("fecha_rastreo", "pdate"),
    campo("enlaces_salientes", "strings", multiple=True), campo("descubierta_desde"),
    campo("tipo_documento"), campo("titulo_original"), campo("titulo_descriptivo"),
    campo("titulo_documento"), campo("sha256_contenido"),
    campo("sha256_contenido_normalizado"), campo("pagerank", "pdouble"),
]

# Contrato de compatibilidad con P05, revisado en la rama de Karen (671ae7d).
# No se agregan a CAMPOS: su creación y sus analizadores pertenecen a P05.
CAMPOS_AUXILIARES_P05 = [
    {**campo("titulo_sugerencia", "text_sugerencia_es"), "docValues": False},
    {**campo("contenido_ortografia", "text_ortografia_es"), "stored": False, "docValues": False},
    {**campo("contenido_vocabulario", "text_vocabulario_es"), "stored": False, "docValues": False},
]
COPIAS_P05 = {
    ("titulo", "titulo_sugerencia"),
    ("contenido", "contenido_ortografia"),
    ("contenido", "contenido_vocabulario"),
}


def validar_p05(esquema, actuales, tipos):
    """Valida lo que ya existe; no exige instalar P05 ni propone reparaciones."""
    errores = []
    for esperado in CAMPOS_AUXILIARES_P05:
        actual = actuales.get(esperado["name"])
        if actual is None:
            continue
        for propiedad, valor in esperado.items():
            # Solr puede omitir propiedades booleanas cuyo valor efectivo es false.
            defecto = False if propiedad in {"required", "multiValued", "docValues"} else None
            if actual.get(propiedad, defecto) != valor:
                errores.append(f"{esperado['name']}.{propiedad}: {actual.get(propiedad, defecto)!r} != {valor!r}")
        if esperado["type"] not in tipos:
            errores.append(f"Falta tipo P05 preexistente: {esperado['type']}")
        if "default" in actual:
            errores.append(f"Valor default inesperado: {esperado['name']}")
    vistas = set()
    for copia in esquema.get("copyFields", []):
        par = (copia.get("source"), copia.get("dest"))
        if par not in COPIAS_P05:
            errores.append(f"Regla copyField no autorizada: {copia!r}")
            continue
        if par in vistas:
            errores.append(f"Regla copyField duplicada: {par}")
        vistas.add(par)
        # Sin maxChars (o 0) se copia todo el texto; truncarlo cambia P05.
        if set(copia) - {"source", "dest", "maxChars"} or (
                "maxChars" in copia and (type(copia["maxChars"]) is not int or copia["maxChars"] != 0)):
            errores.append(f"Propiedades copyField incompatibles: {copia!r}")
        if par[1] not in actuales:
            errores.append(f"Destino copyField P05 ausente: {par[1]}")
    return errores


def guardar_nuevo(ruta, datos):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("x", encoding="utf-8") as archivo:
        json.dump(datos, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def instantanea():
    return {
        "schema": obtener(CORE, "schema")["schema"],
        "fields": obtener(CORE, "schema/fields", {"showDefaults": "true"})["fields"],
    }


def planificar(estado):
    esquema = estado["schema"]
    if esquema.get("uniqueKey") != "id":
        raise ValueError("uniqueKey debe ser id; no se modifica el esquema")
    tipos = {t["name"] for t in esquema["fieldTypes"]}
    faltantes = (set(TIPOS_PROTEGIDOS) | {c["type"] for c in CAMPOS}) - tipos
    if faltantes:
        raise ValueError(f"Faltan tipos preexistentes: {sorted(faltantes)}")
    actuales = {c["name"]: c for c in estado["fields"]}
    nuevos, errores = [], []
    for esperado in CAMPOS:
        actual = actuales.get(esperado["name"])
        if actual is None:
            nuevos.append(esperado)
        else:
            for propiedad, valor in esperado.items():
                if actual.get(propiedad) != valor:
                    errores.append(f"{esperado['name']}.{propiedad}: {actual.get(propiedad)!r} != {valor!r}")
    # Otros campos required/default/copyField pueden impedir cargar o alterar el piloto.
    nombres = {c["name"] for c in CAMPOS}
    for actual in actuales.values():
        if actual.get("required") and actual["name"] not in nombres:
            errores.append(f"Campo obligatorio ajeno al contrato: {actual['name']}")
        if actual["name"] in nombres and "default" in actual:
            errores.append(f"Valor default inesperado: {actual['name']}")
    errores.extend(validar_p05(esquema, actuales, tipos))
    if errores:
        raise ValueError("Esquema incompatible; sin sobrescrituras: " + "; ".join(errores))
    return nuevos


def protegidos(estado):
    return {t["name"]: t for t in estado["schema"]["fieldTypes"] if t["name"] in TIPOS_PROTEGIDOS}


def comprobar_analizador():
    texto = "la Programación JavaScript HTML CSS"
    respuesta = obtener(CORE, "analysis/field", {
        "analysis.fieldtype": "text_es_proyecto", "analysis.fieldvalue": texto,
        "analysis.query": texto,
    })
    analisis = respuesta["analysis"]["field_types"]["text_es_proyecto"]
    for modo in ("index", "query"):
        tokens = {t["text"] for t in analisis[modo][-1]}
        if not {"programacion", "javascript", "html", "css"} <= tokens or "la" in tokens:
            raise ValueError(f"Análisis español inesperado ({modo}): {tokens}")
    return respuesta


def configurar(aplicar=False, evidencia=None):
    antes = instantanea()
    nuevos = planificar(antes)  # Revisar TODO antes de enviar una sola mutación.
    analisis = comprobar_analizador()
    reporte = {"tarea": "P01-05", "fecha_utc": datetime.now(timezone.utc).isoformat(),
               "core": CORE, "contrato": str(CONTRATO.relative_to(PROYECTO)),
               "sha256_contrato": hashlib.sha256(CONTRATO.read_bytes()).hexdigest(),
               "aplicado": aplicar, "campos_por_agregar": nuevos, "antes": antes,
               "analisis_espanol": analisis}
    if evidencia:
        guardar_nuevo(evidencia, reporte)  # Copia del esquema ANTES de modificar.
    if aplicar and nuevos:
        enviar(CORE, "schema", {"add-field": nuevos})
    despues = instantanea()
    if protegidos(antes) != protegidos(despues):
        raise ValueError("Los tipos protegidos cambiaron durante la operación")
    if aplicar and planificar(despues):
        raise ValueError("Faltan campos después de aplicar")
    reporte.update(tipos_protegidos_intactos=True, despues=despues)
    if evidencia:
        guardar_nuevo(str(evidencia) + ".resultado.json", reporte)
    return {"aplicado": aplicar, "campos_agregados" if aplicar else "campos_por_agregar":
            [c["name"] for c in nuevos], "tipos_protegidos_intactos": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--evidencia", type=Path)
    args = parser.parse_args()
    if args.aplicar and args.evidencia is None:
        parser.error("--aplicar requiere --evidencia con una ruta nueva para respaldar el esquema")
    try:
        print(json.dumps(configurar(args.aplicar, args.evidencia), ensure_ascii=False, indent=2))
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"CONFIGURACIÓN DETENIDA: {exc}\n")


if __name__ == "__main__":
    main()
