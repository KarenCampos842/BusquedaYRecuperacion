"""P05-02, P05-03 y P05-06 · Prueba autocompletado y corrección en un core aislado.

Uso (desde proyecto-final-solr/, con Solr encendido):
    py analisis_es/probar_sugerencias_ortografia.py

1. Crea ri_sugerencias_es (si falta) con los campos del contrato P00-03 y
   titulo/contenido con text_es_proyecto. `ri` no se toca.
2. Aplica configurar_sugerencias_ortografia.py en ese core.
3. Indexa los 60 documentos de corpus_solr.json tal como vienen (solo lectura).
4. Reconstruye el diccionario del Suggester (P05-02: el vocabulario son los
   60 títulos) y consulta prefijos y errores de escritura.
5. Guarda resultados/sugerencias_ortografia.json y una tabla Markdown.
"""

import json

from configuracion import CORE_SUGERENCIAS, DIRECTORIO_RESULTADOS
from configurar_analizadores import agregar_o_reemplazar, configurar_tipos
from configurar_sugerencias_ortografia import configurar
from corpus_prueba import cargar_corpus, reindexar_core_de_prueba
from definiciones_sugerencias import (
    DICCIONARIO_SUGERENCIAS,
    HANDLER_ORTOGRAFIA,
    HANDLER_SUGERENCIAS,
)
from definiciones_tipos import TIPO_PROYECTO
from solr_cliente import asegurar_core_de_prueba, exigir_solr, obtener

# Campos del contrato P00-03 (solo en el core de prueba; en `ri` los define Joseph).
CAMPOS_CONTRATO = [
    {"name": "titulo", "type": TIPO_PROYECTO, "stored": True, "indexed": True},
    {"name": "contenido", "type": TIPO_PROYECTO, "stored": True, "indexed": True},
    *({"name": nombre, "type": "string", "stored": True, "indexed": True}
      for nombre in ("categoria", "tipo_fuente", "fuente", "idioma", "url")),
]

PREFIJOS = ["jav", "sel", "her", "cad", "pro", "prom", "elem", "ESPEC", "func", "xyz"]
ERRORES = ["javasript", "fucion", "selectr", "prototpo", "herensia", "promesaz",
           "propiedadez", "javascript", "javasript selectr"]

RUTA_JSON = DIRECTORIO_RESULTADOS / "sugerencias_ortografia.json"
RUTA_TABLA = DIRECTORIO_RESULTADOS / "tabla_sugerencias_ortografia.md"


def preparar_core() -> None:
    asegurar_core_de_prueba(CORE_SUGERENCIAS)
    configurar_tipos(CORE_SUGERENCIAS, [TIPO_PROYECTO])
    for campo in CAMPOS_CONTRATO:
        agregar_o_reemplazar(CORE_SUGERENCIAS, "field", campo)
    configurar(CORE_SUGERENCIAS)


def reconstruir_diccionario() -> None:
    obtener(CORE_SUGERENCIAS, HANDLER_SUGERENCIAS, {"suggest.build": "true", "suggest.q": "x"})


def sugerir(prefijo: str) -> list[str]:
    respuesta = obtener(CORE_SUGERENCIAS, HANDLER_SUGERENCIAS, {"suggest.q": prefijo})
    sugerencias = respuesta["suggest"][DICCIONARIO_SUGERENCIAS][prefijo]["suggestions"]
    return [s["term"] for s in sugerencias]


def corregir(consulta: str) -> dict:
    respuesta = obtener(CORE_SUGERENCIAS, HANDLER_ORTOGRAFIA, {"q": consulta, "json.nl": "map"})
    corrector = respuesta.get("spellcheck", {})
    alternativas = {
        termino: [s["word"] for s in datos.get("suggestion", [])]
        for termino, datos in corrector.get("suggestions", {}).items()
    }
    colaciones = [c["collationQuery"] if isinstance(c, dict) else c
                  for c in corrector.get("collations", {}).values()]
    return {
        "correcta": corrector.get("correctlySpelled"),
        "alternativas": alternativas,
        "consulta_sugerida": colaciones[0] if colaciones else None,
    }


def tabla_markdown(sugerencias: dict, correcciones: dict) -> str:
    filas = ["| Prefijo | Sugerencias (títulos) |", "|---|---|"]
    filas += [f"| {p} | {'; '.join(s) or '—'} |" for p, s in sugerencias.items()]
    filas += ["", "| Consulta | ¿Correcta? | Alternativas | Consulta sugerida |", "|---|---|---|---|"]
    for consulta, c in correcciones.items():
        alternativas = "; ".join(f"{t} → {', '.join(a)}" for t, a in c["alternativas"].items()) or "—"
        filas.append(f"| {consulta} | {c['correcta']} | {alternativas} | {c['consulta_sugerida'] or '—'} |")
    return "\n".join(filas) + "\n"


def main() -> None:
    exigir_solr()
    preparar_core()
    documentos = cargar_corpus()
    reindexar_core_de_prueba(CORE_SUGERENCIAS, documentos)
    print(f"Indexados {len(documentos)} documentos en '{CORE_SUGERENCIAS}'.")
    reconstruir_diccionario()
    sugerencias = {prefijo: sugerir(prefijo) for prefijo in PREFIJOS}
    correcciones = {consulta: corregir(consulta) for consulta in ERRORES}
    DIRECTORIO_RESULTADOS.mkdir(exist_ok=True)
    RUTA_JSON.write_text(json.dumps({"sugerencias": sugerencias, "correcciones": correcciones},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    tabla = tabla_markdown(sugerencias, correcciones)
    RUTA_TABLA.write_text(tabla, encoding="utf-8")
    print(tabla)


if __name__ == "__main__":
    main()
