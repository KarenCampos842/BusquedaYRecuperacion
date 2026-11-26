"""Lectura del corpus oficial (corpus_solr.json, P02-09) e indexación en el core de prueba (nunca en `ri`)."""

import json
from pathlib import Path

from configuracion import CORE_PRODUCCION, DIRECTORIO_PROYECTO, PATRON_CORPUS_SOLR
from solr_cliente import enviar

TOTAL_DOCUMENTOS_ESPERADOS = 60
CAMPOS_OBLIGATORIOS = ("id", "titulo", "contenido", "categoria")


def ruta_corpus_solr() -> Path:
    candidatos = sorted(DIRECTORIO_PROYECTO.glob(PATRON_CORPUS_SOLR))
    if not candidatos:
        raise FileNotFoundError(f"No hay corpus en {PATRON_CORPUS_SOLR}")
    return candidatos[-1]  # el nombre lleva marca de tiempo: el último es el más reciente


def cargar_corpus(ruta: Path | None = None) -> list[dict]:
    """Lee el JSON (solo lectura) y valida 60 documentos con IDs únicos."""
    documentos = json.loads((ruta or ruta_corpus_solr()).read_text(encoding="utf-8"))
    identificadores = {documento["id"] for documento in documentos}
    if len(documentos) != TOTAL_DOCUMENTOS_ESPERADOS or len(identificadores) != len(documentos):
        raise ValueError(f"Se esperaban {TOTAL_DOCUMENTOS_ESPERADOS} documentos con IDs únicos.")
    for documento in documentos:
        faltantes = [campo for campo in CAMPOS_OBLIGATORIOS if not documento.get(campo)]
        if faltantes:
            raise ValueError(f"{documento['id']} no tiene {faltantes}")
    return documentos


def reindexar_core_de_prueba(core: str, documentos: list[dict]) -> None:
    """Vacía el core de prueba y carga los documentos ya mapeados."""
    if core == CORE_PRODUCCION:
        raise ValueError("Estos scripts no indexan en el core de producción.")
    enviar(core, "update", {"delete": {"query": "*:*"}})
    enviar(core, "update", documentos, parametros={"commit": "true"})
