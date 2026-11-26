"""Constantes compartidas por los scripts de análisis del español."""

from pathlib import Path

URL_SOLR = "http://localhost:8983/solr"
TIEMPO_ESPERA_SEGUNDOS = 30

# Core oficial (esquema de Joseph) y core aislado para experimentos de Karen.
CORE_PRODUCCION = "ri"
CORE_PRUEBA = "ri_analisis_es"
CONJUNTO_CONFIGURACION_PRUEBA = "_default"
CONTENEDOR_SOLR = "solr-ri"

# Tipo de control del kit: nunca se reemplaza ni se modifica.
TIPO_CONTROL = "text_es_ri"

# Nombre de los recursos gestionados (stopwords y sinónimos) en la REST API.
RECURSO_GESTIONADO = "es_proyecto"

DIRECTORIO_ANALISIS = Path(__file__).resolve().parent
DIRECTORIO_PROYECTO = DIRECTORIO_ANALISIS.parent
DIRECTORIO_RECURSOS = DIRECTORIO_ANALISIS / "recursos"
DIRECTORIO_RESULTADOS = DIRECTORIO_ANALISIS / "resultados"

RUTA_STOPWORDS = DIRECTORIO_RECURSOS / "stopwords_es.txt"
RUTA_PROTEGIDAS = DIRECTORIO_RECURSOS / "protwords_es.txt"
RUTA_SINONIMOS = DIRECTORIO_RECURSOS / "synonyms_es.txt"

RUTA_ESQUEMA_KIT = (
    DIRECTORIO_PROYECTO
    / "kit" / "02_recuperacion_informacion" / "configuracion" / "configurar_esquema.py"
)
PATRON_CORPUS_SOLR = "data/mdn/transformacion/transformacion_*/corpus_solr.json"
