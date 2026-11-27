"""P07-02: extracción de texto seleccionable desde PDF, sin OCR y sin acceso a Solr.

El módulo admite bytes o una ruta local y devuelve texto Python (Unicode/UTF-8).
No transforma documentos al esquema Solr (P07-03), ni indexa (P07-04),
ni implementa FastAPI (responsabilidad del integrante C).
"""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
import sys
import unicodedata

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class ErrorExtraccionPDF(ValueError):
    """Error esperado y legible durante la lectura de un PDF."""


def _leer_bytes(origen: bytes | bytearray | str | Path) -> bytes:
    if isinstance(origen, (bytes, bytearray)):
        datos = bytes(origen)
    elif isinstance(origen, (str, Path)):
        ruta = Path(origen)
        if not ruta.is_file():
            raise ErrorExtraccionPDF(f"No existe un archivo PDF legible: {ruta}")
        try:
            datos = ruta.read_bytes()
        except OSError as exc:
            raise ErrorExtraccionPDF(f"No se pudo leer el PDF: {ruta}") from exc
    else:
        raise TypeError("El origen debe ser una ruta de archivo o bytes de un PDF")

    if not datos or b"%PDF-" not in datos[:1024]:
        raise ErrorExtraccionPDF("El archivo no tiene una cabecera PDF válida")
    return datos


def extraer_texto_pdf(origen: bytes | bytearray | str | Path) -> str:
    """Extrae y une páginas con dos saltos de línea, conservando acentos.

    No ejecuta OCR. Rechaza archivos corruptos, cifrados y PDFs cuyo contenido
    no tenga texto alfanumérico recuperable. No realiza escrituras.

    Args:
        origen: bytes del archivo o ruta local (str/Path).
    Returns:
        Texto Unicode normalizado a NFC, apto para codificar en UTF-8.
    Raises:
        ErrorExtraccionPDF: PDF inválido, protegido o sin texto recuperable.
    """
    datos = _leer_bytes(origen)
    try:
        lector = PdfReader(BytesIO(datos), strict=False)
        if lector.is_encrypted:
            raise ErrorExtraccionPDF("El PDF está protegido con contraseña o cifrado")
        if not lector.pages:
            raise ErrorExtraccionPDF("El PDF no contiene páginas")
        paginas = []
        for numero, pagina in enumerate(lector.pages, start=1):
            try:
                fragmento = pagina.extract_text() or ""
            except Exception as exc:
                raise ErrorExtraccionPDF(f"No se pudo extraer el texto de la página {numero}") from exc
            fragmento = unicodedata.normalize("NFC", fragmento.replace("\x00", "")).strip()
            if fragmento:
                paginas.append(fragmento)
    except ErrorExtraccionPDF:
        raise
    except (PdfReadError, ValueError, TypeError, KeyError, OSError) as exc:
        raise ErrorExtraccionPDF("El archivo PDF está dañado o no es legible") from exc

    texto = "\n\n".join(paginas).strip()
    if not any(caracter.isalnum() for caracter in texto):
        raise ErrorExtraccionPDF(
            "El PDF no contiene texto seleccionable; los documentos escaneados "
            "o compuestos solo por imágenes requieren OCR (fuera de P07-02)"
        )
    return texto


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path, help="PDF local que se desea extraer")
    parser.add_argument("--salida", type=Path, help="Archivo .txt UTF-8 NUEVO (no se sobrescribe)")
    args = parser.parse_args(argumentos)
    try:
        texto = extraer_texto_pdf(args.archivo)
        if args.salida:
            try:
                with args.salida.open("x", encoding="utf-8", newline="\n") as destino:
                    destino.write(texto + "\n")
            except FileExistsError as exc:
                raise ErrorExtraccionPDF(f"La salida ya existe; no se sobrescribe: {args.salida}") from exc
            print(f"Texto UTF-8 guardado: {args.salida} ({len(texto)} caracteres)")
        else:
            print(texto)
    except ErrorExtraccionPDF as exc:
        print(f"Extracción detenida: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
