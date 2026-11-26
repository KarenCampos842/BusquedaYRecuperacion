"""Obtiene los tokens de cada etapa de un analizador (equivale a Solr Admin > Analysis)."""

from solr_cliente import obtener

FASE_INDICE = "index"
FASE_CONSULTA = "query"
PARAMETRO_POR_FASE = {FASE_INDICE: "analysis.fieldvalue", FASE_CONSULTA: "analysis.query"}


def _nombre_corto(clase: str) -> str:
    return clase.rsplit(".", 1)[-1]


def _pares(lista_plana: list) -> list[tuple]:
    """Solr devuelve las etapas como [clase, tokens, clase, tokens, ...]."""
    return list(zip(lista_plana[0::2], lista_plana[1::2]))


def analizar_por_etapas(core: str, tipo: str, texto: str, fase: str = FASE_INDICE) -> list[dict]:
    respuesta = obtener(core, "analysis/field", {
        "analysis.fieldtype": tipo,
        PARAMETRO_POR_FASE[fase]: texto,
    })
    etapas = respuesta["analysis"]["field_types"][tipo][fase]
    return [
        {"etapa": _nombre_corto(clase), "tokens": [token["text"] for token in tokens]}
        for clase, tokens in _pares(etapas)
    ]


def tokens_finales(core: str, tipo: str, texto: str, fase: str = FASE_INDICE) -> list[str]:
    etapas = analizar_por_etapas(core, tipo, texto, fase)
    return etapas[-1]["tokens"] if etapas else []
