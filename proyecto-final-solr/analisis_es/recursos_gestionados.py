"""Sincroniza stopwords y sinónimos con los recursos gestionados de Solr (REST API).

Los archivos .txt del repositorio son la fuente de verdad: lo que sobra en
Solr se borra y lo que falta se agrega, así que se puede ejecutar varias veces.
"""

import urllib.parse

from configuracion import RECURSO_GESTIONADO
from recursos_linguisticos import leer_grupos_sinonimos, leer_stopwords
from solr_cliente import enviar, obtener

RUTA_STOPWORDS = f"schema/analysis/stopwords/{RECURSO_GESTIONADO}"
RUTA_SINONIMOS = f"schema/analysis/synonyms/{RECURSO_GESTIONADO}"


def _borrar_entrada(core: str, ruta_recurso: str, entrada: str) -> None:
    enviar(core, f"{ruta_recurso}/{urllib.parse.quote(entrada, safe='')}", None, metodo="DELETE")


def sincronizar_stopwords(core: str) -> int:
    deseadas = set(leer_stopwords())
    actuales = set(obtener(core, RUTA_STOPWORDS)["wordSet"]["managedList"])
    for sobrante in actuales - deseadas:
        _borrar_entrada(core, RUTA_STOPWORDS, sobrante)
    enviar(core, RUTA_STOPWORDS, sorted(deseadas), metodo="PUT")
    return len(deseadas)


def sincronizar_sinonimos(core: str) -> int:
    grupos = leer_grupos_sinonimos()
    actuales = obtener(core, RUTA_SINONIMOS)["synonymMappings"]["managedMap"]
    for termino in actuales:
        _borrar_entrada(core, RUTA_SINONIMOS, termino)
    # Una lista de listas se interpreta como grupos de equivalentes.
    enviar(core, RUTA_SINONIMOS, grupos, metodo="PUT")
    return len(grupos)
