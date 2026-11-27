"""Definiciones para autocompletado (P05-01 a P05-03) y corrección ortográfica (P05-06).

Estrategia (P05-01):
- Autocompletado: un SuggestComponent con DOS diccionarios, consultados juntos:
  * `titulos_es` (AnalyzingInfixLookupFactory sobre `titulo_sugerencia`, copia de
    `titulo`): títulos completos que contienen una palabra que empieza por el prefijo.
  * `terminos_es` (AnalyzingLookupFactory + HighFrequencyDictionaryFactory sobre
    `contenido_vocabulario`, copia de `contenido`): palabras del contenido de los
    60 documentos que empiezan por el prefijo, ordenadas por número de documentos.
    El campo no aplica stemming ni quita acentos y descarta palabras vacías, tokens
    de menos de 3 letras y restos de código con números o símbolos («javascript:void»).
  En ambos, el prefijo se compara sin distinguir acentos ni mayúsculas.
- Corrección: SpellCheckComponent con DirectSolrSpellChecker sobre
  `contenido_ortografia` (copia de `contenido` SIN stemming ni plegado de acentos),
  para que las sugerencias sean palabras reales: «función», no la raíz ni la forma sin acento.

Todos los nombres son nuevos para no tocar el componente `spellcheck` ni el
handler `/spell` que trae el configset _default.
"""

from definiciones_tipos import FILTRO_MINUSCULAS, FILTRO_PALABRAS_VACIAS, FILTRO_PLEGADO, tipo_texto

TIPO_SUGERENCIA = "text_sugerencia_es"
TIPO_ORTOGRAFIA = "text_ortografia_es"
TIPO_VOCABULARIO = "text_vocabulario_es"

CAMPO_TITULO = "titulo"
CAMPO_CONTENIDO = "contenido"
CAMPO_SUGERENCIA = "titulo_sugerencia"
CAMPO_ORTOGRAFIA = "contenido_ortografia"
CAMPO_VOCABULARIO = "contenido_vocabulario"

COMPONENTE_SUGERENCIAS = "sugerencias_es"
DICCIONARIO_SUGERENCIAS = "titulos_es"
DICCIONARIO_TERMINOS = "terminos_es"
DICCIONARIOS_AUTOCOMPLETADO = [DICCIONARIO_TERMINOS, DICCIONARIO_SUGERENCIAS]
HANDLER_SUGERENCIAS = "/sugerencias"

COMPONENTE_ORTOGRAFIA = "ortografia_es"
DICCIONARIO_ORTOGRAFIA = "contenido_es"
HANDLER_ORTOGRAFIA = "/ortografia"

# Contrato P00-04: /suggest y /spellcheck exigen al menos 3 letras; /suggest devuelve 5 (máx. 8).
LONGITUD_MINIMA_CONSULTA = 3
LONGITUD_MAXIMA_TERMINO = 40
# Token válido para el vocabulario: letras, con puntos solo entre letras («promise.all»).
PATRON_TOKEN_VALIDO = r"\p{L}+(?:\.\p{L}+)*"
SUGERENCIAS_POR_DEFECTO = 5
ALTERNATIVAS_ORTOGRAFICAS = 5


def definir_text_sugerencia_es() -> dict:
    # Sin palabras vacías ni stemming: el usuario escribe prefijos de palabras reales.
    return tipo_texto(TIPO_SUGERENCIA, [FILTRO_MINUSCULAS, FILTRO_PLEGADO])


def definir_text_ortografia_es() -> dict:
    # Sin plegado ni stemming: el diccionario debe conservar la forma correcta con acentos.
    return tipo_texto(TIPO_ORTOGRAFIA, [FILTRO_MINUSCULAS, FILTRO_PALABRAS_VACIAS])


def definir_text_vocabulario_es() -> dict:
    # Como text_ortografia_es, pero vacía los tokens con números o símbolos y
    # LengthFilter descarta los vacíos y los de menos de 3 letras.
    descartar_codigo = {
        "class": "solr.PatternReplaceFilterFactory",
        "pattern": f"^(?!{PATRON_TOKEN_VALIDO}$).*$",
        "replacement": "",
        "replace": "all",
    }
    longitud = {
        "class": "solr.LengthFilterFactory",
        "min": str(LONGITUD_MINIMA_CONSULTA),
        "max": str(LONGITUD_MAXIMA_TERMINO),
    }
    return tipo_texto(TIPO_VOCABULARIO, [FILTRO_MINUSCULAS, FILTRO_PALABRAS_VACIAS, descartar_codigo, longitud])


DEFINIDORES_TIPOS_SUGERENCIAS = {
    TIPO_SUGERENCIA: definir_text_sugerencia_es,
    TIPO_ORTOGRAFIA: definir_text_ortografia_es,
    TIPO_VOCABULARIO: definir_text_vocabulario_es,
}

def campo_auxiliar(nombre: str, tipo: str, almacenado: bool) -> dict:
    """Mismas propiedades que valida validar_p05() en indexacion/configurar_esquema.py (Joseph)."""
    return {"name": nombre, "type": tipo, "stored": almacenado, "indexed": True,
            "required": False, "multiValued": False, "docValues": False}


CAMPOS_AUXILIARES = [
    # stored=true: DocumentDictionaryFactory lee el valor almacenado para armar el diccionario.
    campo_auxiliar(CAMPO_SUGERENCIA, TIPO_SUGERENCIA, almacenado=True),
    campo_auxiliar(CAMPO_ORTOGRAFIA, TIPO_ORTOGRAFIA, almacenado=False),
    campo_auxiliar(CAMPO_VOCABULARIO, TIPO_VOCABULARIO, almacenado=False),
]

# copyField sin límite: maxChars ausente o el entero 0 (mismo criterio que validar_p05()).
MAX_CHARS_ILIMITADO = 0

COPIAS = [
    {"source": CAMPO_TITULO, "dest": CAMPO_SUGERENCIA},
    {"source": CAMPO_CONTENIDO, "dest": CAMPO_ORTOGRAFIA},
    {"source": CAMPO_CONTENIDO, "dest": CAMPO_VOCABULARIO},
]

COMPONENTE_SUGGESTER = {
    "name": COMPONENTE_SUGERENCIAS,
    "class": "solr.SuggestComponent",
    "suggester": [{
        "name": DICCIONARIO_SUGERENCIAS,
        "lookupImpl": "AnalyzingInfixLookupFactory",
        "dictionaryImpl": "DocumentDictionaryFactory",
        "field": CAMPO_SUGERENCIA,
        "suggestAnalyzerFieldType": TIPO_SUGERENCIA,
        "indexPath": "suggester_titulos_es",
        "highlight": "false",
        "buildOnStartup": "false",
        "buildOnCommit": "true",
    }, {
        "name": DICCIONARIO_TERMINOS,
        "lookupImpl": "AnalyzingLookupFactory",
        "dictionaryImpl": "HighFrequencyDictionaryFactory",
        "field": CAMPO_VOCABULARIO,
        # Sin "threshold": la Config API lo guarda como texto y Solr 10 exige número
        # (ClassCastException). El valor por defecto, 0, incluye todos los términos.
        "suggestAnalyzerFieldType": TIPO_SUGERENCIA,
        "exactMatchFirst": "true",
        "buildOnStartup": "false",
        "buildOnCommit": "true",
    }],
}

HANDLER_SUGGESTER = {
    "name": HANDLER_SUGERENCIAS,
    "class": "solr.SearchHandler",
    "startup": "lazy",
    "defaults": {
        "suggest": "true",
        "suggest.dictionary": DICCIONARIOS_AUTOCOMPLETADO,
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
