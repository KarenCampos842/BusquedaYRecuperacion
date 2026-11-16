"""Interpreta cuerpos multipart/form-data."""
from email import policy
from email.message import Message
from email.parser import BytesParser
from typing import Mapping


def _nombre_de_parte(parte: Message) -> str:
    """Obtiene el nombre de archivo de una parte corrigiendo el utf-8 crudo."""
    nombre = parte.get_filename() or ""
    try:
        return nombre.encode("utf-8", "surrogateescape").decode("utf-8")
    except UnicodeError:
        return nombre


def leer_archivos(encabezados: Mapping[str, str], cuerpo: bytes) -> list[tuple[str, bytes]]:
    """Devuelve los pares nombre y contenido de los archivos del formulario."""
    tipo = encabezados.get("Content-Type", "")
    mensaje = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: " + tipo.encode("latin-1") + b"\r\nMIME-Version: 1.0\r\n\r\n" + cuerpo
    )
    if not mensaje.is_multipart():
        return []
    archivos = []
    for parte in mensaje.iter_parts():
        nombre = _nombre_de_parte(parte)
        if nombre:
            archivos.append((nombre, parte.get_payload(decode=True) or b""))
    return archivos
