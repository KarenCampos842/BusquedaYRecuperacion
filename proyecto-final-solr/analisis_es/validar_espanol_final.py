"""P03-10, P08-03 y P08-04 · Valida el análisis del español sobre un core con titulo/contenido.

Uso (desde proyecto-final-solr/, con Solr encendido):
    py analisis_es/validar_espanol_final.py --preparar-core-de-prueba   # crea e indexa ri_validacion_es
    py analisis_es/validar_espanol_final.py                             # vuelve a validar ri_validacion_es
    py analisis_es/validar_espanol_final.py --core ri                   # solo lectura; sigue siendo "PRUEBA LOCAL"
    py analisis_es/validar_espanol_final.py --core ri --evidencia-final # pide confirmación escrita

Ejecuta los casos de consultas_validacion_final.csv con la misma consulta que usará
la API (edismax, qf=titulo^4 contenido) y guarda, por caso: tokens de índice y de
consulta del campo `contenido`, IDs recuperados por cada consulta y si coinciden.
En los casos de sinónimos compara con y sin expansión en el mismo índice:
- con expansión: la consulta real (el queryAnalyzer aplica los sinónimos);
- sin expansión: {!term} con la forma indexada del término (no pasa por el
  queryAnalyzer, así que no hay sinónimos).
Solo registra hechos observados: no calcula precisión ni afirma mejoras.

Sobre el core indicado solo hace lecturas (GET). La única escritura es
--preparar-core-de-prueba, que solo se acepta con ri_validacion_es.
La salida se etiqueta "PRUEBA LOCAL" salvo con --evidencia-final, que solo vale
sobre el índice definitivo (el `ri` de Joseph) y en el equipo donde corre ese Solr.
"""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone

from analisis_tokens import FASE_CONSULTA, FASE_INDICE, analizar_campo_por_etapas, ultimos_tokens
from comparar_analizadores import PESO_TITULO
from configuracion import CORE_PRODUCCION, DIRECTORIO_ANALISIS, DIRECTORIO_RESULTADOS, RECURSO_GESTIONADO
from configurar_analizadores import agregar_o_reemplazar, configurar_tipos
from corpus_prueba import TOTAL_DOCUMENTOS_ESPERADOS, cargar_corpus, reindexar_core_de_prueba
from definiciones_tipos import TIPO_PROYECTO
from solr_cliente import ErrorSolr, core_existe, exigir_solr, obtener

CORE_VALIDACION = "ri_validacion_es"
CAMPO_TITULO = "titulo"
CAMPO_CONTENIDO = "contenido"
CAMPOS_ANALIZADOS = (CAMPO_TITULO, CAMPO_CONTENIDO)
CAMPO_CATEGORIA = "categoria"
CRITERIO_SINONIMOS = "sinonimos"
MAXIMO_RESULTADOS = TOTAL_DOCUMENTOS_ESPERADOS
ORDEN_ESTABLE = "score desc,id asc"  # desempata por id para que dos ejecuciones coincidan

ETIQUETA_PRUEBA_LOCAL = "PRUEBA LOCAL — no es evidencia final"
ETIQUETA_EVIDENCIA_FINAL = "EVIDENCIA FINAL — índice definitivo confirmado por quien ejecuta"
CONFIRMACION_EVIDENCIA_FINAL = "indice definitivo"

RUTA_CASOS = DIRECTORIO_ANALISIS / "consultas_validacion_final.csv"
DIRECTORIO_PRUEBA_LOCAL = DIRECTORIO_RESULTADOS / "prueba_local"
DIRECTORIO_EVIDENCIA_FINAL = DIRECTORIO_RESULTADOS / "evidencia_final"
PREFIJO_URL_MDN = "https://developer.mozilla.org/es/docs/Web/"


# ---------- Casos y consultas (solo lectura) ----------

def leer_casos() -> list[dict]:
    with RUTA_CASOS.open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def parametros_consulta_real(texto: str) -> dict:
    """La misma consulta que usará la API (P00-03)."""
    return {
        "q": texto,
        "defType": "edismax",
        "q.op": "OR",
        "qf": f"{CAMPO_TITULO}^{PESO_TITULO} {CAMPO_CONTENIDO}",
        "fl": f"id,{CAMPO_TITULO}",
        "rows": MAXIMO_RESULTADOS,
        "sort": ORDEN_ESTABLE,
    }


def parametros_sin_expansion(tokens_indexados: list[str]) -> dict:
    """Busca la forma indexada exacta en titulo o contenido, sin queryAnalyzer."""
    parametros = {"fl": f"id,{CAMPO_TITULO}", "rows": MAXIMO_RESULTADOS, "sort": ORDEN_ESTABLE}
    clausulas = []
    for numero, (campo, token) in enumerate((c, t) for t in tokens_indexados for c in CAMPOS_ANALIZADOS):
        nombre = f"t{numero}"
        parametros[nombre] = f"{{!term f={campo}}}{token}"
        clausulas.append(f"should=${nombre}")
    parametros["q"] = "{!bool " + " ".join(clausulas) + "}"
    return parametros


def buscar(core: str, parametros: dict) -> list[dict]:
    documentos = obtener(core, "select", parametros)["response"]["docs"]
    return [{"id": d["id"], "titulo": texto_titulo(d.get(CAMPO_TITULO))} for d in documentos]


def texto_titulo(valor) -> str:
    return valor[0] if isinstance(valor, list) else (valor or "")


def tokens(core: str, texto: str, fase: str) -> list[str]:
    return ultimos_tokens(analizar_campo_por_etapas(core, CAMPO_CONTENIDO, texto, fase))


def observar_consulta(core: str, texto: str) -> dict:
    documentos = buscar(core, parametros_consulta_real(texto))
    return {
        "consulta": texto,
        "tokens_consulta": tokens(core, texto, FASE_CONSULTA),
        "tokens_indice": tokens(core, texto, FASE_INDICE),
        "total": len(documentos),
        "ids": [d["id"] for d in documentos],
        "titulos": {d["id"]: d["titulo"] for d in documentos},
    }


def observar_sin_expansion(core: str, observacion: dict) -> dict:
    sin_expansion = [d["id"] for d in buscar(core, parametros_sin_expansion(observacion["tokens_indice"]))]
    nuevos = [i for i in observacion["ids"] if i not in set(sin_expansion)]
    return {"total_sin_expansion": len(sin_expansion), "ids_sin_expansion": sin_expansion,
            "ids_nuevos_por_expansion": nuevos}


def comparar_conjuntos(a: dict, b: dict) -> dict:
    ids_a, ids_b = set(a["ids"]), set(b["ids"])
    return {
        "mismos_documentos": ids_a == ids_b,
        "solo_en_a": sorted(ids_a - ids_b),
        "solo_en_b": sorted(ids_b - ids_a),
    }


def ejecutar_caso(core: str, caso: dict) -> dict:
    a = observar_consulta(core, caso["consulta_a"])
    b = observar_consulta(core, caso["consulta_b"])
    if caso["criterio"] == CRITERIO_SINONIMOS:
        a.update(observar_sin_expansion(core, a))
        b.update(observar_sin_expansion(core, b))
    return {**caso, "a": a, "b": b, **comparar_conjuntos(a, b)}


# ---------- Estado del core (solo lectura) ----------

def tipo_de_campo(core: str, campo: str) -> str | None:
    try:
        return obtener(core, f"schema/fields/{campo}")["field"]["type"]
    except ErrorSolr as error:
        if error.estado == 404:
            return None
        raise


def contar_documentos(core: str) -> int:
    return obtener(core, "select", {"q": "*:*", "rows": 0})["response"]["numFound"]


def huella_sinonimos(core: str) -> str:
    """SHA-256 corto de los sinónimos gestionados que usa el core (para saber qué versión se probó)."""
    mapa = obtener(core, f"schema/analysis/synonyms/{RECURSO_GESTIONADO}")["synonymMappings"]["managedMap"]
    contenido = json.dumps(mapa, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(contenido).hexdigest()[:16]


def exigir_core_listo(core: str) -> int:
    if not core_existe(core):
        raise SystemExit(f"El core '{core}' no existe.")
    distintos = {c: t for c in CAMPOS_ANALIZADOS if (t := tipo_de_campo(core, c)) != TIPO_PROYECTO}
    if distintos:
        raise SystemExit(f"En '{core}' estos campos no usan {TIPO_PROYECTO}: {distintos}")
    total = contar_documentos(core)
    if total == 0:
        raise SystemExit(f"El core '{core}' no tiene documentos indexados.")
    return total


# ---------- Core de prueba (única escritura, nunca en ri) ----------

def definiciones_campos_prueba() -> list[dict]:
    return [
        {"name": CAMPO_TITULO, "type": TIPO_PROYECTO, "stored": True, "indexed": True},
        {"name": CAMPO_CONTENIDO, "type": TIPO_PROYECTO, "stored": True, "indexed": True},
        {"name": CAMPO_CATEGORIA, "type": "string", "stored": True, "indexed": True},
    ]


def mapear_documento(documento: dict) -> dict:
    return {campo: documento[campo] for campo in ("id", CAMPO_TITULO, CAMPO_CONTENIDO, CAMPO_CATEGORIA)}


def preparar_core_de_prueba(core: str) -> None:
    if core != CORE_VALIDACION:
        raise ValueError(f"Solo se prepara '{CORE_VALIDACION}', no '{core}'.")
    configurar_tipos(core, [TIPO_PROYECTO])  # crea el core si falta y sincroniza recursos
    for definicion in definiciones_campos_prueba():
        agregar_o_reemplazar(core, "field", definicion)
    documentos = cargar_corpus()  # el JSON solo se lee
    reindexar_core_de_prueba(core, [mapear_documento(d) for d in documentos])
    print(f"Indexados {len(documentos)} documentos en '{core}'.")


# ---------- Salida ----------

def id_corto(identificador: str) -> str:
    return identificador.removeprefix(PREFIJO_URL_MDN)


def lista_corta(ids: list[str], maximo: int = 3) -> str:
    if not ids:
        return "—"
    extra = f" (+{len(ids) - maximo})" if len(ids) > maximo else ""
    return "; ".join(id_corto(i) for i in ids[:maximo]) + extra


def celda(texto: str) -> str:
    return str(texto).replace("|", "\\|")


def tabla_markdown(encabezado: dict, resultados: list[dict]) -> str:
    lineas = [
        f"# Validación del español · {encabezado['etiqueta']}",
        "",
        f"- Core: `{encabezado['core']}` · documentos: {encabezado['documentos']} · "
        f"sinónimos (huella): `{encabezado['huella_sinonimos']}`",
        f"- Consulta: `{encabezado['consulta']}`",
        "- Solo hechos observados; no se calculan métricas de calidad.",
        "",
        "| ID | Criterio | Consulta A | Tokens A | Consulta B | Tokens B | Docs A | Docs B | ¿Mismos docs? |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in resultados:
        lineas.append(
            f"| {r['id']} | {r['criterio']} | {celda(r['a']['consulta'])} | {' '.join(r['a']['tokens_consulta'])} | "
            f"{celda(r['b']['consulta'])} | {' '.join(r['b']['tokens_consulta'])} | {r['a']['total']} | "
            f"{r['b']['total']} | {'sí' if r['mismos_documentos'] else 'no'} |")
    sinonimos = [r for r in resultados if r["criterio"] == CRITERIO_SINONIMOS]
    if sinonimos:
        lineas += ["", "## Sinónimos: con y sin expansión", "",
                   "| ID | Consulta | Sin expansión | Con expansión | Nuevos por expansión |", "|---|---|---|---|---|"]
        for r in sinonimos:
            for lado in ("a", "b"):
                o = r[lado]
                lineas.append(f"| {r['id']} | {celda(o['consulta'])} | {o['total_sin_expansion']} | {o['total']} | "
                              f"{lista_corta(o['ids_nuevos_por_expansion'])} |")
    return "\n".join(lineas) + "\n"


def directorio_salida(evidencia_final: bool):
    return DIRECTORIO_EVIDENCIA_FINAL if evidencia_final else DIRECTORIO_PRUEBA_LOCAL


def guardar(encabezado: dict, resultados: list[dict], evidencia_final: bool) -> tuple:
    directorio = directorio_salida(evidencia_final)
    directorio.mkdir(parents=True, exist_ok=True)
    ruta_json = directorio / f"validacion_final_{encabezado['core']}.json"
    ruta_tabla = directorio / f"validacion_final_{encabezado['core']}.md"
    ruta_json.write_text(json.dumps({"encabezado": encabezado, "casos": resultados},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    ruta_tabla.write_text(tabla_markdown(encabezado, resultados), encoding="utf-8")
    return ruta_json, ruta_tabla


def construir_encabezado(core: str, documentos: int, evidencia_final: bool) -> dict:
    consulta = parametros_consulta_real("<consulta>")
    return {
        "etiqueta": ETIQUETA_EVIDENCIA_FINAL if evidencia_final else ETIQUETA_PRUEBA_LOCAL,
        "core": core,
        "documentos": documentos,
        "huella_sinonimos": huella_sinonimos(core),
        "consulta": f"defType={consulta['defType']} q.op={consulta['q.op']} qf={consulta['qf']}",
        "fecha_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ---------- Línea de comandos ----------

def leer_argumentos(argumentos=None) -> argparse.Namespace:
    lector = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    lector.add_argument("--core", default=CORE_VALIDACION, help=f"core a validar (por defecto {CORE_VALIDACION})")
    lector.add_argument("--preparar-core-de-prueba", action="store_true",
                        help=f"crea e indexa el core aislado; solo con --core {CORE_VALIDACION}")
    lector.add_argument("--evidencia-final", action="store_true",
                        help=f"marca la salida como evidencia final; solo con --core {CORE_PRODUCCION} "
                             "sobre el índice definitivo y pide confirmación")
    opciones = lector.parse_args(argumentos)
    if opciones.preparar_core_de_prueba and opciones.core != CORE_VALIDACION:
        lector.error(f"--preparar-core-de-prueba solo se permite con --core {CORE_VALIDACION}")
    if opciones.evidencia_final and opciones.core != CORE_PRODUCCION:
        lector.error(f"--evidencia-final solo se permite con --core {CORE_PRODUCCION}")
    return opciones


def confirmar_evidencia_final(leer_respuesta=input) -> bool:
    print(f"La evidencia final solo vale si este Solr es el de quien ejecuta el script y si "
          f"'{CORE_PRODUCCION}' es el índice definitivo (P02-11 / P08-02) con los 60 documentos.")
    respuesta = leer_respuesta(f"Escriba '{CONFIRMACION_EVIDENCIA_FINAL}' para confirmar: ")
    return respuesta.strip().lower() == CONFIRMACION_EVIDENCIA_FINAL


def main(argumentos=None, leer_respuesta=input) -> None:
    opciones = leer_argumentos(argumentos)
    if opciones.evidencia_final and not confirmar_evidencia_final(leer_respuesta):
        raise SystemExit("Sin confirmación: no se generó evidencia final.")
    exigir_solr()
    if opciones.preparar_core_de_prueba:
        preparar_core_de_prueba(opciones.core)
    documentos = exigir_core_listo(opciones.core)
    encabezado = construir_encabezado(opciones.core, documentos, opciones.evidencia_final)
    resultados = [ejecutar_caso(opciones.core, caso) for caso in leer_casos()]
    ruta_json, ruta_tabla = guardar(encabezado, resultados, opciones.evidencia_final)
    print(tabla_markdown(encabezado, resultados))
    print(f"Detalle: {ruta_json}\nTabla: {ruta_tabla}")


if __name__ == "__main__":
    main()
