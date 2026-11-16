"""Comprueba resultados y PDF; renderiza sus páginas para revisión visual."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw
from pypdf import PdfReader

from evaluar import validar_metricas

RAIZ = Path(__file__).resolve().parent
REPO = RAIZ.parent


def verificar():
    datos = json.loads((RAIZ / "resultados/ultima_ejecucion.json").read_text(encoding="utf-8"))
    protocolo = datos["protocolo"]
    universo = {d["nombre"] for d in protocolo["documentos"]}
    assert hashlib.sha256((RAIZ / "protocolo.json").read_bytes()).hexdigest() == datos["protocolo_sha256"]
    for documento in protocolo["documentos"]:
        assert hashlib.sha256((RAIZ / "coleccion" / documento["nombre"]).read_bytes()).hexdigest() == documento["sha256"]
    for sistema in datos["sistemas"].values():
        ap_exactas = []
        for consulta in protocolo["consultas"]:
            m = sistema["metricas"][consulta["id"]]
            validar_metricas(m, consulta["relevantes"], universo)
            posiciones = [p["posicion"] for p in m["puntos"] if p["relevante"]]
            ap_exactas.append(sum((Fraction(i, k) for i, k in enumerate(posiciones, 1)), Fraction()) / 4)
        assert abs(float(sum(ap_exactas) / 5) - sistema["MAP"]) < 1e-12
    ruta = REPO / "output/pdf/comparacion_buscadores.pdf"
    lector = PdfReader(ruta)
    assert len(lector.pages) == 11
    texto = "\n".join(p.extract_text() for p in lector.pages)
    assert "\ufffd" not in texto and "\u25a0" not in texto
    for nombre in universo:
        assert nombre in texto
    for sistema in datos["sistemas"].values():
        assert f"{sistema['MAP']:.4f}" in texto
    carpeta = REPO / "tmp/pdfs"
    carpeta.mkdir(parents=True, exist_ok=True)
    documento = pymupdf.open(ruta)
    miniaturas = []
    for numero, pagina in enumerate(documento, 1):
        for bloque in pagina.get_text("blocks"):
            x0, y0, x1, y1 = bloque[:4]
            assert x0 >= 0 and y0 >= 0 and x1 <= pagina.rect.width + 1 and y1 <= pagina.rect.height + 1
        imagen = pagina.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        imagen.save(carpeta / f"pagina_{numero:02}.png")
        miniatura = Image.open(carpeta / f"pagina_{numero:02}.png").convert("RGB")
        miniatura.thumbnail((360, 510))
        miniaturas.append(miniatura.copy())
    contacto = Image.new("RGB", (3 * 380, 4 * 540), "#d9e0e5")
    dibujo = ImageDraw.Draw(contacto)
    for i, miniatura in enumerate(miniaturas):
        x, y = (i % 3) * 380 + 10, (i // 3) * 540 + 20
        contacto.paste(miniatura, (x, y))
        dibujo.text((x, y - 15), f"Página {i + 1}", fill="black")
    contacto.save(carpeta / "contacto.png")
    print("Resultados, hashes, AP/MAP y PDF comprobados. Once páginas renderizadas en tmp/pdfs.")


if __name__ == "__main__":
    verificar()
