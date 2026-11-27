"""Definiciones para autocompletado (P05-01 a P05-03) y corrección ortográfica (P05-06).

Estrategia (P05-01):
- Autocompletado: SuggestComponent con AnalyzingInfixLookupFactory sobre
  `titulo_sugerencia` (copia de `titulo`). Propone títulos completos que contienen
  una palabra que empieza por el prefijo escrito, sin distinguir acentos ni mayúsculas.
- Corrección: SpellCheckComponent con DirectSolrSpellChecker sobre
  `contenido_ortografia` (copia de `contenido` SIN stemming ni plegado de acentos),
  para que las sugerencias sean palabras reales: «función», no la raíz ni la forma sin acento.

Todos los nombres son nuevos para no tocar el componente `spellcheck` ni el
handler `/spell` que trae el configset _default.
"""

from definiciones_tipos import FILTRO_MINUSCULAS, FILTRO_PALABRAS_VACIAS, FILTRO_PLEGADO, tipo_texto

TIPO_SUGERENCIA = "text_sugerencia_es"
TIPO_ORTOGRAFIA = "text_ortografia_es"

CAMPO_TITULO = "titulo"
CAMPO_CONTENIDO = "contenido"
CAMPO_SUGERENCIA = "titulo_sugerencia"
CAMPO_ORTOGRAFIA = "contenido_ortografia"

COMPONENTE_SUGERENCIAS = "sugerencias_es"
DICCIONARIO_SUGERENCIAS = "titulos_es"
HANDLER_SUGERENCIAS = "/sugerencias"

COMPONENTE_ORTOGRAFIA = "ortografia_es"
DICCIONARIO_ORTOGRAFIA = "contenido_es"
HANDLER_ORTOGRAFIA = "/ortografia"

# Contrato P00-04: /suggest y /spellcheck exigen al menos 3 letras; /suggest devuelve 5 (máx. 8).
LONGITUD_MINIMA_CONSULTA = 3
SUGERENCIAS_POR_DEFECTO = 5
ALTERNATIVAS_ORTOGRAFICAS = 5


def definir_text_sugerencia_es() -> dict:
    # Sin palabras vacías ni stemming: el usuario escribe prefijos de palabras reales.
    return tipo_texto(TIPO_SUGERENCIA, [FILTRO_MINUSCULAS, FILTRO_PLEGADO])


def definir_text_ortografia_es() -> dict:
    # Sin plegado ni stemming: el diccionario debe conservar la forma correcta con acentos.
    return tipo_texto(TIPO_ORTOGRAFIA, [FILTRO_MINUSCULAS, FILTRO_PALABRAS_VACIAS])


DEFINIDORES_TIPOS_SUGERENCIAS = {
    TIPO_SUGERENCIA: definir_text_sugerencia_es,
    TIPO_ORTOGRAFIA: definir_text_ortografia_es,
}

CAMPOS_AUXILIARES = [
    # stored=true: DocumentDictionaryFactory lee el valor almacenado para armar el diccionario.
    {"name": CAMPO_SUGERENCIA, "type": TIPO_SUGERENCIA, "stored": True, "indexed": True},
    {"name": CAMPO_ORTOGRAFIA, "type": TIPO_ORTOGRAFIA, "stored": False, "indexed": True},
]

COPIAS = [
    {"source": CAMPO_TITULO, "dest": CAMPO_SUGERENCIA},
    {"source": CAMPO_CONTENIDO, "dest": CAMPO_ORTOGRAFIA},
]

COMPONENTE_SUGGESTER = {
    "name": COMPONENTE_SUGERENCIAS,
    "class": "solr.SuggestComponent",
    "suggester": {
        "name": DICCIONARIO_SUGERENCIAS,
        "lookupImpl": "AnalyzingInfixLookupFactory",
        "dictionaryImpl": "DocumentDictionaryFactory",
        "field": CAMPO_SUGERENCIA,
        "suggestAnalyzerFieldType": TIPO_SUGERENCIA,
        "indexPath": "suggester_titulos_es",
        "highlight": "false",
        "buildOnStartup": "false",
        "buildOnCommit": "true",
    },
}

HANDLER_SUGGESTER = {
    "name": HANDLER_SUGERENCIAS,
    "class": "solr.SearchHandler",
    "startup": "lazy",
    "defaults": {
        "suggest": "true",
        "suggest.dictionary": DICCIONARIO_SUGERENCIAS,
        "suggest.count": str(SUGERENCIAS_POR_DEFECTO),
    },
    "components": [COMPONENTE_SUGERENCIAS],
}

COMPONENTE_SPELLCHECK = {
    "name": COMPONENTE_ORTOGRAFIA,
    "class": "solr.SpellCheckComponent",
    "queryAnalyzerFieldType": TIPO_ORTOGRAFIA,
    "spellchecker": {
        "name": DICCIONARIO_ORTOGRAFIA,
        "classname": "solr.DirectSolrSpellChecker",
        "field": CAMPO_ORTOGRAFIA,
        "distanceMeasure": "internal",
        "accuracy": "0.5",
        "maxEdits": "2",
        "minPrefix": "1",
        "maxInspections": "5",
        "minQueryLength": str(LONGITUD_MINIMA_CONSULTA),
    },
}

HANDLER_SPELLCHECK = {
    "name": HANDLER_ORTOGRAFIA,
    "class": "solr.SearchHandler",
    "startup": "lazy",
    "defaults": {
        "df": CAMPO_ORTOGRAFIA,
        "rows": "0",
        "spellcheck": "true",
        "spellcheck.dictionary": DICCIONARIO_ORTOGRAFIA,
        "spellcheck.count": str(ALTERNATIVAS_ORTOGRAFICAS),
        "spellcheck.extendedResults": "true",
        "spellcheck.collate": "true",
        "spellcheck.maxCollationTries": "5",
        "spellcheck.collateExtendedResults": "true",
    },
    "last-components": [COMPONENTE_ORTOGRAFIA],
}

# (comando de la Config API, definición) en el orden en que deben aplicarse.
CONFIGURACION_SOLRCONFIG = [
    ("searchcomponent", COMPONENTE_SUGGESTER),
    ("requesthandler", HANDLER_SUGGESTER),
    ("searchcomponent", COMPONENTE_SPELLCHECK),
    ("requesthandler", HANDLER_SPELLCHECK),
]

NOMBRES_DEL_CONFIGSET_QUE_NO_SE_TOCAN = {"spellcheck", "/spell", "suggest", "/suggest"}
