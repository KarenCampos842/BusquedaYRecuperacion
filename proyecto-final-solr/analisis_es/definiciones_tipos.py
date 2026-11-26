"""Definiciones (Schema API) de los tipos de campo de español.

Cadena de cada tipo:
- text_es_ri (kit, control):  estándar, minúsculas, plegado conservando original.
- text_es_stop (P03-03):      text_es_ri + palabras vacías.
- text_es_stem (P03-05):      estándar, minúsculas, plegado, stemming ligero.
- text_es_proyecto:           estándar, minúsculas, plegado, palabras vacías,
                              términos protegidos, stemming ligero;
                              en consulta, además, sinónimos (P03-08).
"""

import ast

from configuracion import RECURSO_GESTIONADO, RUTA_ESQUEMA_KIT, TIPO_CONTROL
from recursos_linguisticos import leer_terminos_protegidos, patron_terminos_protegidos

TIPO_STOPWORDS = "text_es_stop"
TIPO_STEMMING = "text_es_stem"
TIPO_PROYECTO = "text_es_proyecto"

TOKENIZADOR_ESTANDAR = {"class": "solr.StandardTokenizerFactory"}
FILTRO_MINUSCULAS = {"class": "solr.LowerCaseFilterFactory"}
FILTRO_PLEGADO = {"class": "solr.ASCIIFoldingFilterFactory", "preserveOriginal": "false"}
FILTRO_PLEGADO_CON_ORIGINAL = {"class": "solr.ASCIIFoldingFilterFactory", "preserveOriginal": "true"}
FILTRO_PALABRAS_VACIAS = {"class": "solr.ManagedStopFilterFactory", "managed": RECURSO_GESTIONADO}
FILTRO_STEMMING_LIGERO = {"class": "solr.SpanishLightStemFilterFactory"}
FILTRO_SINONIMOS = {"class": "solr.ManagedSynonymGraphFilterFactory", "managed": RECURSO_GESTIONADO}


def filtro_terminos_protegidos(patron: str) -> dict:
    return {"class": "solr.KeywordMarkerFilterFactory", "pattern": patron}


def tipo_texto(nombre: str, filtros_indice: list[dict], filtros_consulta: list[dict] | None = None) -> dict:
    """Arma un TextField con analizadores de índice y de consulta."""
    return {
        "name": nombre,
        "class": "solr.TextField",
        "positionIncrementGap": "100",
        "indexAnalyzer": {"tokenizer": TOKENIZADOR_ESTANDAR, "filters": filtros_indice},
        "queryAnalyzer": {
            "tokenizer": TOKENIZADOR_ESTANDAR,
            "filters": filtros_consulta if filtros_consulta is not None else filtros_indice,
        },
    }


def definir_text_es_stop() -> dict:
    return tipo_texto(TIPO_STOPWORDS, [FILTRO_MINUSCULAS, FILTRO_PLEGADO_CON_ORIGINAL, FILTRO_PALABRAS_VACIAS])


def definir_text_es_stem() -> dict:
    return tipo_texto(TIPO_STEMMING, [FILTRO_MINUSCULAS, FILTRO_PLEGADO, FILTRO_STEMMING_LIGERO])


def definir_text_es_proyecto() -> dict:
    protegidos = filtro_terminos_protegidos(patron_terminos_protegidos(leer_terminos_protegidos()))
    filtros_indice = [FILTRO_MINUSCULAS, FILTRO_PLEGADO, FILTRO_PALABRAS_VACIAS, protegidos, FILTRO_STEMMING_LIGERO]
    # Sinónimos tras el plegado y antes de palabras vacías y stemming:
    # así los grupos del archivo (sin acentos) coinciden con la consulta.
    filtros_consulta = [FILTRO_MINUSCULAS, FILTRO_PLEGADO, FILTRO_SINONIMOS, FILTRO_PALABRAS_VACIAS, protegidos, FILTRO_STEMMING_LIGERO]
    return tipo_texto(TIPO_PROYECTO, filtros_indice, filtros_consulta)


DEFINIDORES_TIPOS = {
    TIPO_STOPWORDS: definir_text_es_stop,
    TIPO_STEMMING: definir_text_es_stem,
    TIPO_PROYECTO: definir_text_es_proyecto,
}


def leer_text_es_ri_del_kit() -> dict:
    """Extrae la definición literal de text_es_ri del script del kit sin ejecutarlo.

    Evita copiar la definición: si el kit cambia, el control cambia con él.
    """
    arbol = ast.parse(RUTA_ESQUEMA_KIT.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Dict):
            try:
                literal = ast.literal_eval(nodo)
            except (ValueError, TypeError):
                continue
            tipo = literal.get("add-field-type")
            if isinstance(tipo, dict) and tipo.get("name") == TIPO_CONTROL:
                return tipo
    raise LookupError(f"No se encontró {TIPO_CONTROL} en {RUTA_ESQUEMA_KIT}")
