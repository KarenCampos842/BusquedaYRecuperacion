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


def _analizar(core: str, parametro: str, clave_respuesta: str, nombre: str, texto: str, fase: str) -> list[dict]:
    respuesta = obtener(core, "analysis/field", {parametro: nombre, PARAMETRO_POR_FASE[fase]: texto})
    etapas = respuesta["analysis"][clave_respuesta][nombre][fase]
    return [
        {"etapa": _nombre_corto(clase), "tokens": [token["text"] for token in tokens]}
        for clase, tokens in _pares(etapas)
    ]


def analizar_por_etapas(core: str, tipo: str, texto: str, fase: str = FASE_INDICE) -> list[dict]:
    """Analiza con un tipo de campo (analysis.fieldtype)."""
    return _analizar(core, "analysis.fieldtype", "field_types", tipo, texto, fase)


def analizar_campo_por_etapas(core: str, campo: str, texto: str, fase: str = FASE_INDICE) -> list[dict]:
    """Analiza con el analizador de un campo real del esquema (analysis.fieldname)."""
    return _analizar(core, "analysis.fieldname", "field_names", campo, texto, fase)


def ultimos_tokens(etapas: list[dict]) -> list[str]:
    return etapas[-1]["tokens"] if etapas else []


def tokens_finales(core: str, tipo: str, texto: str, fase: str = FASE_INDICE) -> list[str]:
    return ultimos_tokens(analizar_por_etapas(core, tipo, texto, fase))
