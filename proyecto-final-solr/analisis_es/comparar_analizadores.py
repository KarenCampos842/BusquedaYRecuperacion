"""P03-04, P03-06 y P03-08 · Compara text_es_ri con los tipos alternativos.

Uso (desde proyecto-final-solr/, con Solr encendido):
    py analisis_es/comparar_analizadores.py

Pasos (todos en el core aislado ri_analisis_es; `ri` no se toca):
1. Crea el core si falta y configura text_es_ri (copia del kit) y los tipos nuevos.
2. Crea campos espejo titulo_<variante> y contenido_<variante> por cada tipo.
3. Indexa los 60 documentos de corpus_solr.json (P02-09; el JSON solo se lee).
4. Ejecuta las mismas consultas en cada variante y guarda totales, primeros
   resultados y documentos ganados/perdidos frente a text_es_ri.
5. Guarda tokens de ejemplos para la evidencia (equivale a Solr Admin > Analysis).
Si existe analisis_es/juicios_relevancia.csv (consulta_id,doc_id) también
calcula P@5 y Recall@10. Los juicios no se inventan: los define Karen.
"""

import csv
import json

from analisis_tokens import FASE_CONSULTA, FASE_INDICE, analizar_por_etapas
from configuracion import CORE_PRUEBA, DIRECTORIO_ANALISIS, DIRECTORIO_RESULTADOS, TIPO_CONTROL
from configurar_analizadores import agregar_o_reemplazar, asegurar_tipo_control, configurar_tipos
from corpus_prueba import TOTAL_DOCUMENTOS_ESPERADOS, cargar_corpus, reindexar_core_de_prueba
from definiciones_tipos import DEFINIDORES_TIPOS, TIPO_PROYECTO, TIPO_STEMMING, TIPO_STOPWORDS
from solr_cliente import asegurar_core_de_prueba, exigir_solr, obtener

VARIANTES = {"ri": TIPO_CONTROL, "stop": TIPO_STOPWORDS, "stem": TIPO_STEMMING, "proyecto": TIPO_PROYECTO}
VARIANTE_CONTROL = "ri"
CAMPO_CATEGORIA = "categoria"
PESO_TITULO = 4  # mismo boost que usará Carlos (qf=titulo^4 contenido)
RESULTADOS_VISIBLES = 10
CORTE_PRECISION = 5

RUTA_CONSULTAS = DIRECTORIO_ANALISIS / "consultas_comparacion.csv"
RUTA_JUICIOS = DIRECTORIO_ANALISIS / "juicios_relevancia.csv"
RUTA_JSON = DIRECTORIO_RESULTADOS / "comparacion_analizadores.json"
RUTA_TABLA = DIRECTORIO_RESULTADOS / "tabla_comparacion.md"

EJEMPLOS_TOKENS = [
    ("BÚSQUEDA de Información", FASE_INDICE),
    ("la cadena de prototipos", FASE_INDICE),
    ("promesa promesas funciones función arreglos", FASE_INDICE),
    ("JavaScript CSS HTML fetch array media canvas", FASE_INDICE),
    ("promise", FASE_CONSULTA),
    ("relleno", FASE_CONSULTA),
    ("expresión regular", FASE_CONSULTA),
]


def campo(prefijo: str, variante: str) -> str:
    return f"{prefijo}_{variante}"


def definiciones_campos() -> list[dict]:
    campos = [{"name": CAMPO_CATEGORIA, "type": "string", "stored": True, "indexed": True}]
    for variante, tipo in VARIANTES.items():
        guardar = variante == VARIANTE_CONTROL  # solo se guarda una copia del texto
        campos.append({"name": campo("titulo", variante), "type": tipo, "stored": guardar, "indexed": True})
        campos.append({"name": campo("contenido", variante), "type": tipo, "stored": False, "indexed": True})
    return campos


def preparar_esquema() -> None:
    asegurar_core_de_prueba(CORE_PRUEBA)
    asegurar_tipo_control(CORE_PRUEBA)
    configurar_tipos(CORE_PRUEBA, list(DEFINIDORES_TIPOS))
    for definicion in definiciones_campos():
        agregar_o_reemplazar(CORE_PRUEBA, "field", definicion)


def mapear_documento(documento: dict) -> dict:
    mapeado = {"id": documento["id"], CAMPO_CATEGORIA: documento["categoria"]}
    for variante in VARIANTES:
        mapeado[campo("titulo", variante)] = documento["titulo"]
        mapeado[campo("contenido", variante)] = documento["contenido"]
    return mapeado


def buscar(variante: str, consulta: str) -> list[dict]:
    """Devuelve TODOS los documentos coincidentes (el corpus tiene 60) ordenados por score."""
    respuesta = obtener(CORE_PRUEBA, "select", {
        "q": consulta,
        "defType": "edismax",
        "q.op": "OR",
        "qf": f"{campo('titulo', variante)}^{PESO_TITULO} {campo('contenido', variante)}",
        "fl": f"id,{campo('titulo', VARIANTE_CONTROL)}",
        "rows": TOTAL_DOCUMENTOS_ESPERADOS,
    })
    return [
        {"id": doc["id"], "titulo": doc[campo("titulo", VARIANTE_CONTROL)]}
        for doc in respuesta["response"]["docs"]
    ]


def leer_consultas() -> list[dict]:
    with RUTA_CONSULTAS.open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def leer_juicios() -> dict[str, set[str]]:
    if not RUTA_JUICIOS.exists():
        return {}
    juicios: dict[str, set[str]] = {}
    with RUTA_JUICIOS.open(encoding="utf-8", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            juicios.setdefault(fila["consulta_id"], set()).add(fila["doc_id"])
    return juicios


def metricas(ids: list[str], relevantes: set[str]) -> dict:
    if not relevantes:
        return {}
    primeros = ids[:RESULTADOS_VISIBLES]
    return {
        "p_at_5": round(sum(i in relevantes for i in ids[:CORTE_PRECISION]) / CORTE_PRECISION, 2),
        "recall_at_10": round(sum(i in relevantes for i in primeros) / len(relevantes), 2),
    }


def comparar_consulta(consulta: dict, juicios: dict) -> dict:
    por_variante = {variante: buscar(variante, consulta["consulta"]) for variante in VARIANTES}
    ids_control = {doc["id"] for doc in por_variante[VARIANTE_CONTROL]}
    resultado = {**consulta, "variantes": {}}
    for variante, documentos in por_variante.items():
        ids = [doc["id"] for doc in documentos]
        titulos = {doc["id"]: doc["titulo"] for doc in documentos}
        resultado["variantes"][variante] = {
            "total": len(ids),
            "primeros": [titulos[i] for i in ids[:RESULTADOS_VISIBLES]],
            "ganados_vs_ri": sorted(titulos[i] for i in set(ids) - ids_control),
            "perdidos_vs_ri": sorted(ids_control - set(ids)),
            **metricas(ids, juicios.get(consulta["id"], set())),
        }
    return resultado


def tokens_de_ejemplo() -> list[dict]:
    return [
        {"texto": texto, "fase": fase, "tipo": tipo,
         "etapas": analizar_por_etapas(CORE_PRUEBA, tipo, texto, fase)}
        for texto, fase in EJEMPLOS_TOKENS
        for tipo in VARIANTES.values()
    ]


def celda_ganados(datos: dict, maximo: int = 3) -> str:
    ganados = datos["ganados_vs_ri"]
    if not ganados:
        return "—"
    extra = f" (+{len(ganados) - maximo})" if len(ganados) > maximo else ""
    return "; ".join(ganados[:maximo]) + extra


def tabla_markdown(comparaciones: list[dict]) -> str:
    encabezado = "| ID | Consulta | Propósito | " + " | ".join(VARIANTES) + " | Nuevos con proyecto (vs ri) | Perdidos con proyecto |"
    separador = "|" + "---|" * (len(VARIANTES) + 5)
    filas = [encabezado, separador]
    for c in comparaciones:
        totales = " | ".join(str(c["variantes"][v]["total"]) for v in VARIANTES)
        proyecto = c["variantes"]["proyecto"]
        consulta = c["consulta"].replace("|", "\\|")
        filas.append(f"| {c['id']} | {consulta} | {c['proposito']} | {totales} | "
                     f"{celda_ganados(proyecto)} | {len(proyecto['perdidos_vs_ri'])} |")
    return "\n".join(filas) + "\n"


def guardar(comparaciones: list[dict], tokens: list[dict]) -> None:
    DIRECTORIO_RESULTADOS.mkdir(exist_ok=True)
    RUTA_JSON.write_text(json.dumps({"consultas": comparaciones, "tokens": tokens},
                                    ensure_ascii=False, indent=2), encoding="utf-8")
    RUTA_TABLA.write_text(tabla_markdown(comparaciones), encoding="utf-8")


def main() -> None:
    exigir_solr()
    preparar_esquema()
    documentos = cargar_corpus()
    reindexar_core_de_prueba(CORE_PRUEBA, [mapear_documento(d) for d in documentos])
    print(f"Indexados {len(documentos)} documentos en '{CORE_PRUEBA}'.")
    juicios = leer_juicios()
    comparaciones = [comparar_consulta(consulta, juicios) for consulta in leer_consultas()]
    guardar(comparaciones, tokens_de_ejemplo())
    print(tabla_markdown(comparaciones))
    print(f"Detalle: {RUTA_JSON}")


if __name__ == "__main__":
    main()
