"""Derivar una versión corregida del JSON local, sin acceder a Internet."""

import hashlib
import json
from collections import Counter

from mdn_corpus import huella, huella_normalizada
from mdn_piloto import DATA, clasificar_documento, filtrar_enlaces, guardar_nuevo


def actualizar(documentos):
    resultado = []
    for original in documentos:
        doc = dict(original)
        doc["sha256_contenido"] = huella(doc)
        doc["sha256_contenido_normalizado"] = huella_normalizada(doc)
        doc["tipo_documento"] = clasificar_documento(doc["url"])
        doc["enlaces_salientes"] = filtrar_enlaces(doc.get("enlaces_salientes", []), doc["url"])
        resultado.append(doc)
    return resultado


def main():
    origen = DATA / "corpus_piloto.json"
    destino = DATA / "corpus_piloto_v2.json"
    reporte = DATA / "corpus_piloto_v2_ajustes.json"
    if destino.exists() or reporte.exists():
        raise SystemExit("La versión v2 ya existe; no se sobrescribirá evidencia local.")
    raw = origen.read_bytes()
    originales = json.loads(raw)
    nuevos = actualizar(originales)
    guardar_nuevo(destino, nuevos)
    guardar_nuevo(reporte, {
        "operacion": "actualizacion_local_sin_red", "archivo_origen": origen.name,
        "sha256_archivo_origen": hashlib.sha256(raw).hexdigest(),
        "archivo_resultado": destino.name, "total_documentos": len(nuevos),
        "tipo_documento": dict(Counter(doc["tipo_documento"] for doc in nuevos)),
        "enlaces_excluidos": sum(len(a.get("enlaces_salientes", [])) - len(b["enlaces_salientes"])
                                 for a, b in zip(originales, nuevos)),
        "contenido_y_fechas_rastreo": "conservados del corpus original; sin nuevas descargas",
        "sha256_contenido": "SHA-256 de contenido.encode('utf-8'), sin normalización",
        "sha256_contenido_normalizado": "SHA-256 UTF-8 tras compactar espacios, strip y casefold",
        "clasificacion": "heurística de ruta; raíces y Guide/Guides/Reference/Tutorials son índices",
    })
    print(f"Actualización local: {len(nuevos)} documentos; {destino.name}; original intacto.")


if __name__ == "__main__":
    main()
