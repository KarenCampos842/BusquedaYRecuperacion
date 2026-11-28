"""P07-03: PDF -> exactamente los siete campos obligatorios de P00-03 v1.2.

No guarda el fichero ni accede a Solr. ``origen`` puede ser bytes o ruta.
La procedencia es local: NO inventa ``url``, ``tema`` ni ruta pública.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import unicodedata

from pdf_importacion.extractor_pdf import ErrorExtraccionPDF, extraer_texto_pdf, _leer_bytes

CATEGORIAS = frozenset({"JavaScript", "HTML", "CSS", "General"})
CAMPOS = frozenset({"id", "titulo", "contenido", "categoria", "tipo_fuente", "fuente", "idioma"})


class ErrorDocumentoPDF(ValueError):
    """Error de validación antes de construir un documento Solr."""


def _texto_corto(valor: str, campo: str) -> str:
    if not isinstance(valor, str):
        raise ErrorDocumentoPDF(f"{campo} debe ser texto")
    texto = unicodedata.normalize("NFC", valor).strip()
    if not texto or not any(c.isalnum() for c in texto):
        raise ErrorDocumentoPDF(f"{campo} no puede estar vacío")
    if any(ord(c) < 32 or ord(c) == 127 for c in texto):
        raise ErrorDocumentoPDF(f"{campo} contiene caracteres de control")
    return texto


def convertir_pdf_a_documento(
    origen: bytes | bytearray | str | Path,
    *,
    titulo: str | None = None,
    categoria: str = "General",
    nombre_archivo: str | None = None,
) -> dict[str, str]:
    """Transforma contenido PDF en el contrato Solr, sin efectos secundarios.

    Para bytes sin título explícito se exige ``nombre_archivo``. Para rutas
    se deriva de su nombre (no se leen ni publican rutas en el documento).
    """
    if categoria not in CATEGORIAS:
        raise ErrorDocumentoPDF(f"Categoría no permitida: {categoria!r}")
    if titulo is None:
        nombre = nombre_archivo if nombre_archivo is not None else (
            Path(origen).name if isinstance(origen, (str, Path)) else None
        )
        if nombre is None:
            raise ErrorDocumentoPDF("Para PDF en bytes proporciona título o nombre_archivo")
        if not isinstance(nombre, str) or not nombre.lower().endswith(".pdf"):
            raise ErrorDocumentoPDF("nombre_archivo debe terminar en .pdf")
        titulo = Path(nombre.replace("\\", "/")).stem.replace("_", " ").replace("-", " ")
    titulo = _texto_corto(titulo, "titulo")
    try:
        datos = _leer_bytes(origen)
        contenido = extraer_texto_pdf(datos)
    except ErrorExtraccionPDF as exc:
        raise ErrorDocumentoPDF(str(exc)) from exc
    if not contenido or not any(c.isalnum() for c in contenido):
        raise ErrorDocumentoPDF("contenido extraído vacío")
    documento = {
        "id": "pdf:" + hashlib.sha256(datos).hexdigest(),
        "titulo": titulo,
        "contenido": contenido,
        "categoria": categoria,
        "tipo_fuente": "pdf",
        "fuente": "PDF local",
        "idioma": "es",
    }
    assert set(documento) == CAMPOS
    return documento


def validar_documento_pdf(doc: dict) -> None:
    if not isinstance(doc, dict) or set(doc) != CAMPOS:
        raise ErrorDocumentoPDF("Documento PDF con campos ausentes o no autorizados")
    if not isinstance(doc["id"], str) or len(doc["id"]) != 68 or not doc["id"].startswith("pdf:") or any(x not in "0123456789abcdef" for x in doc["id"][4:]):
        raise ErrorDocumentoPDF("ID PDF inválido: se requiere pdf: + SHA-256 completo")
    if doc["categoria"] not in CATEGORIAS or doc["tipo_fuente"] != "pdf" or doc["fuente"] != "PDF local" or doc["idioma"] != "es":
        raise ErrorDocumentoPDF("Metadatos incompatibles con P00-03")
    _texto_corto(doc["titulo"], "titulo")
    if not isinstance(doc["contenido"], str) or not doc["contenido"].strip() or not any(c.isalnum() for c in doc["contenido"]):
        raise ErrorDocumentoPDF("Contenido PDF no válido")
