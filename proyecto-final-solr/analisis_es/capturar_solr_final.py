"""Captura las doce evidencias de Solr Admin sobre el escritorio de Windows."""

import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, quote, urlsplit
from urllib.request import urlopen
from uuid import uuid4

RAIZ = Path(__file__).resolve().parents[1]
VALIDACIONES = RAIZ / "analisis_es/resultados/evidencia_final"
DESTINO = RAIZ / "docs/evidencias/P09-03"
BASE = "http://localhost:8983"
GRUPOS = {"preprocesamiento": 7, "sinonimos": 5}
CONSULTAS = {
    ("preprocesamiento", 2): ("A01", "b"),
    ("preprocesamiento", 3): ("A01", "a"),
    ("preprocesamiento", 5): ("S01", "a"),
    ("sinonimos", 2): ("Y01", "a"),
    ("sinonimos", 3): ("Y01", "a"),
    ("sinonimos", 5): ("Y02", "a"),
}


def fecha():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def leer_solr(ruta):
    with urlopen(BASE + ruta, timeout=15) as respuesta:
        datos = json.load(respuesta)
    if datos.get("responseHeader", {}).get("status") != 0:
        raise ValueError(f"Respuesta de error de Solr en {ruta}")
    return datos


def preflight(seleccion):
    conteo = leer_solr("/solr/ri/select?q=*:*&rows=0&facet=true&facet.field=tipo_fuente&json.nl=map&wt=json")
    fuentes = conteo["facet_counts"]["facet_fields"]["tipo_fuente"]
    if conteo["response"]["numFound"] != 62 or fuentes != {"web": 60, "pdf": 2}:
        raise ValueError("Se requieren 62 documentos (60 web y 2 PDF) en ri")
    indice = VALIDACIONES / "INDICE.md"
    patron_carpeta = r"\d{4}-\d{2}-\d{2}T\d{6}Z_ri"
    if indice.is_file():
        entradas = re.findall(
            r"^\| ([^|]+?) \| ri \| 62 \| \[([^\]]+)\]\(\2/\) \|$",
            indice.read_text(encoding="utf-8-sig"), re.M,
        )
        elegida = next(((instante, carpeta) for instante, carpeta in reversed(entradas)
                        if seleccion is None or seleccion == carpeta), None)
    elif seleccion and re.fullmatch(patron_carpeta, seleccion):
        # Una copia de la entrega puede contener solo la ejecución seleccionada.
        instante = datetime.strptime(seleccion, "%Y-%m-%dT%H%M%SZ_ri")
        elegida = instante.strftime("%Y-%m-%dT%H:%M:%SZ"), seleccion
    else:
        raise ValueError("Sin INDICE.md, selecciona explícitamente una ejecución final con --validacion")
    if not elegida or not re.fullmatch(patron_carpeta, elegida[1]):
        raise ValueError("Falta una ejecución final de ri con 62 documentos en INDICE.md")
    instante, carpeta = elegida
    ruta = VALIDACIONES / carpeta / "validacion_final_ri.json"
    datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
    cabecera = datos["encabezado"]
    if (cabecera["core"], cabecera["documentos"], cabecera["fecha_utc"]) != ("ri", 62, instante) or (
        not cabecera["etiqueta"].startswith("EVIDENCIA FINAL —")
        or "EVIDENCIA FINAL" not in ruta.with_suffix(".md").read_text(encoding="utf-8-sig")
    ):
        raise ValueError("La validación seleccionada no acredita el índice definitivo")
    for campo in ("titulo", "contenido"):
        esquema = leer_solr(f"/solr/ri/schema/fields/{campo}?wt=json")
        if esquema["field"]["type"] != "text_es_proyecto":
            raise ValueError(f"El campo {campo} de ri no usa text_es_proyecto")
    sinonimos = leer_solr("/solr/ri/schema/analysis/synonyms/es_proyecto?wt=json")
    mapa = sinonimos["synonymMappings"]["managedMap"]
    huella = hashlib.sha256(json.dumps(mapa, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
    if huella != cabecera["huella_sinonimos"]:
        raise ValueError("Los sinónimos de ri difieren de la validación elegida")
    casos = {caso["id"]: caso for caso in datos["casos"]}
    for caso, lado in CONSULTAS.values():
        observacion = casos[caso][lado]
        if not observacion["ids"] or len(set(observacion["ids"])) != observacion["total"]:
            raise ValueError(f"Validación incompleta para {caso}")
    if not all(casos[k]["mismos_documentos"] for k in ("A01", "S01", "Y01", "Y02")):
        raise ValueError("La validación final no cumple los casos A01, S01, Y01 y Y02")
    y01 = casos["Y01"]["a"]
    tokens = y01["tokens_indice"]
    if y01["consulta"] != "relleno" or not isinstance(tokens, list) or len(tokens) != 1 or not tokens[0]:
        raise ValueError("Y01 debe indicar un token de índice para relleno")
    if not y01["ids_nuevos_por_expansion"] or not casos["Y02"]["a"]["ids_nuevos_por_expansion"]:
        raise ValueError("La validación final no muestra nuevos resultados por expansión")
    return ruta, casos, tokens[0], fuentes


def plan_capturas(token):
    for grupo, cantidad in GRUPOS.items():
        leeme = (DESTINO / grupo / "README.md").read_text(encoding="utf-8")
        filas = re.findall(r"^\| `([^/]+\.png)` \| <([^>]+)> \| (.+?) \|$", leeme, re.M)
        if len(filas) != cantidad:
            raise ValueError(f"Se esperaban {cantidad} URL en el README de {grupo}")
        for numero, (archivo, url, criterio) in enumerate(filas, 1):
            if not archivo.startswith(f"{grupo}_{numero:02}_") or not url.startswith(BASE + "/solr/"):
                raise ValueError(f"Fila inesperada: {archivo}")
            if archivo == "sinonimos_02_relleno_sin_expansion.png":
                url, reemplazos = re.subn(r"(%7D)rellen(?=&|$)", lambda m: m[1] + quote(token, safe=""), url)
                if reemplazos != 2:
                    raise ValueError("La URL sin expansión no contiene los dos términos de referencia")
            yield grupo, numero, archivo, url, criterio


def permitir(ruta):
    req = ruta.request
    url = urlsplit(req.url)
    params = {k.lower(): v for k, v in parse_qs(url.query, keep_blank_values=True).items()}
    accion = params.get("action")
    if (req.method == "GET" and f"{url.scheme}://{url.netloc}" == BASE
            and url.path.startswith("/solr/")
            and not any(p in url.path.split("/") for p in ("update", "config", "replication"))
            and (accion is None or (url.path == "/solr/admin/cores" and accion == ["STATUS"]))
            and not ({"commit", "optimize", "stream.body"} & params.keys())):
        ruta.continue_()
    else:
        ruta.abort()


def verificar_busqueda(pagina, grupo, numero, casos):
    # Edge representa la respuesta HTTP original como texto; conserva las URL de Karen.
    texto = pagina.locator("body").inner_text()
    respuesta = json.loads(texto)["response"]
    caso, lado = CONSULTAS[grupo, numero]
    esperado = casos[caso][lado]
    sin_expansion = grupo == "sinonimos" and numero == 2
    ids = esperado["ids_sin_expansion"] if sin_expansion else esperado["ids"]
    docs = respuesta["docs"]
    visibles = {d["id"] for d in docs}
    coincide = (respuesta["numFound"] == len(ids) and len(docs) == min(10, len(ids))
                and visibles <= set(ids) and all(d.get("titulo") for d in docs))
    if grupo == "sinonimos" and numero == 3:
        coincide &= set(esperado["ids_nuevos_por_expansion"]) <= visibles
    return {"caso": caso, "numFound": respuesta["numFound"], "documentos_visibles": docs}, coincide


def verificar_analisis(pagina, grupo, numero):
    etapas = pagina.locator("#analysis-result .step").evaluate_all("""filas => filas.map(f => ({
        fase: f.closest('#analysis-result > div').classList.contains('query') ? 'query' : 'index',
        etapa: f.querySelector('abbr').title.split('.').pop(),
        tokens: [...f.querySelectorAll('tr.text td')].map(t => t.innerText)
    }))""")
    fases = {fase: {e["etapa"]: e["tokens"] for e in etapas if e["fase"] == fase}
             for fase in ("index", "query")}
    indice, consulta = fases["index"], fases["query"]
    if grupo == "sinonimos":
        fuente, expansion = ("relleno", "padding") if numero == 1 else ("margen", "margin")
        coincide = any("SynonymGraph" in clase and {fuente, expansion} <= set(tokens)
                       for clase, tokens in consulta.items())
    elif numero == 1:
        coincide = indice.get("ASCIIFoldingFilter") == consulta.get("ASCIIFoldingFilter") == ["funcion", "de", "busqueda"]
    elif numero == 4:
        coincide = indice.get("StopFilter") == ["cadena", "prototipos"] and indice.get("SpanishLightStemFilter") == ["caden", "prototip"]
    elif numero == 6:
        stem = indice.get("SpanishLightStemFilter", [])
        coincide = len(stem) == 4 and stem[0] == stem[1] and stem[2] == stem[3]
    else:
        coincide = (any("KeywordMarker" in clase for clase in indice)
                    and indice.get("SpanishLightStemFilter") == ["media", "medi", "arrays", "array"])
    return etapas, coincide


def guardar_png(imagen, ruta):
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    with ruta.open("xb") as archivo:
        archivo.write(buffer.getvalue())


def ventanas_chromium():
    win = ctypes.windll.user32
    ventanas = set()
    callback_tipo = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_tipo
    def recoger(hwnd, _):
        clase = ctypes.create_unicode_buffer(256)
        win.GetClassNameW(hwnd, clase, len(clase))
        if clase.value == "Chrome_WidgetWin_1" and win.IsWindowVisible(hwnd):
            ventanas.add(hwnd)
        return True

    win.EnumWindows(recoger, 0)
    return ventanas


def ventana_nativa(hwnd, image_grab):
    """Captura los píxeles de la ventana activa, incluida su interfaz nativa."""
    win = ctypes.windll.user32
    win.GetForegroundWindow.restype = wintypes.HWND
    if win.GetForegroundWindow() != hwnd:
        raise RuntimeError("Edge no está en primer plano en el escritorio interactivo")
    rect = wintypes.RECT()
    # Extended frame bounds son píxeles físicos y excluyen el borde invisible.
    if ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(rect), ctypes.sizeof(rect)):
        raise RuntimeError("Windows no devolvió los límites de la ventana Edge")
    imagen = image_grab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True)
    if win.GetForegroundWindow() != hwnd:
        raise RuntimeError("El foco de Windows cambió durante la captura")
    return imagen


def enfocar_y_encuadrar(pagina, hwnd, es_analisis):
    pagina.bring_to_front()
    # Zoom nativo de Edge. El documento, los resultados y la URL se conservan.
    win = ctypes.windll.user32
    def tecla(codigo):
        win.keybd_event(0x11, 0, 0, 0)
        win.keybd_event(codigo, 0, 0, 0)
        win.keybd_event(codigo, 0, 2, 0)
        win.keybd_event(0x11, 0, 2, 0)

    def medidas():
        return pagina.evaluate("""selector => {
          const el = document.querySelector(selector);
          if (!el) return null;
          const r = el.getBoundingClientRect();
          return {cabe: r.top >= -1 && r.bottom <= innerHeight + 1 &&
                       r.right <= innerWidth + 1 && el.scrollWidth <= innerWidth + 1,
                  escala: devicePixelRatio};
        }""", "#analysis" if es_analisis else "body")

    # Las teclas actúan sobre ventanas reales. Comprobar el foco antes de usarlas.
    win.GetForegroundWindow.restype = wintypes.HWND
    if win.GetForegroundWindow() != hwnd:
        win.ShowWindow(hwnd, 3)
        win.SetForegroundWindow(hwnd)
        pagina.wait_for_timeout(250)
    if win.GetForegroundWindow() != hwnd:
        # Windows permite activar una ventana tras una pulsación de Alt.
        win.keybd_event(0x12, 0, 0, 0)
        win.keybd_event(0x12, 0, 2, 0)
        win.SetForegroundWindow(hwnd)
        pagina.wait_for_timeout(250)
    if win.GetForegroundWindow() != hwnd:
        raise RuntimeError("No se pudo enfocar Edge. Ejecutar desde el escritorio desbloqueado")
    tecla(0x30)
    pagina.wait_for_timeout(250)
    for _ in range(7):
        pagina.evaluate("window.scrollTo(0, 0)")
        estado = medidas()
        if estado and estado["cabe"]:
            break
        tecla(0xBD)
        pagina.wait_for_timeout(250)
    # Edge muestra brevemente el diálogo de zoom sobre la página.
    win.keybd_event(0x1B, 0, 0, 0)
    win.keybd_event(0x1B, 0, 2, 0)
    pagina.wait_for_timeout(2200)
    return medidas()


def capturar(plan, casos, destino, registro, semiautomatico, escala_unitaria=False):
    from PIL import ImageGrab
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        anteriores = ventanas_chromium()
        argumentos = ["--start-maximized", "--disable-features=Translate,msEdgeTranslate"]
        if escala_unitaria:
            argumentos.append("--force-device-scale-factor=1")
        navegador = playwright.chromium.launch(
            channel="msedge", headless=False, args=argumentos,
        )
        try:
            contexto = navegador.new_context(no_viewport=True, service_workers="block")
            contexto.route("**/*", permitir)
            pagina = contexto.new_page()
            sesion = contexto.new_cdp_session(pagina)
            ventana = sesion.send("Browser.getWindowForTarget")["windowId"]
            sesion.send("Browser.setWindowBounds", {"windowId": ventana, "bounds": {"windowState": "maximized"}})
            pagina.wait_for_timeout(500)
            nuevas = ventanas_chromium() - anteriores
            hwnd = next(iter(nuevas)) if len(nuevas) == 1 else None
            for grupo, numero, nombre, url, criterio in plan:
                ruta = destino / grupo / nombre
                entrada = {"archivo": ruta.relative_to(RAIZ).as_posix(), "url": url, "criterio": criterio,
                           "fecha_utc": fecha(), "incidencias": []}
                registro["capturas"].append(entrada)
                print(nombre, flush=True)
                analisis = bool(urlsplit(url).fragment)
                try:
                    respuesta = pagina.goto(url, wait_until="load", timeout=20000)
                    if respuesta and not respuesta.ok:
                        raise RuntimeError(f"HTTP {respuesta.status}")
                    if analisis:
                        pagina.locator("#analysis-result .step tr.text").first.wait_for(timeout=12000)
                        observado, correcto = verificar_analisis(pagina, grupo, numero)
                    else:
                        observado, correcto = verificar_busqueda(pagina, grupo, numero, casos)
                    entrada["observado"] = observado
                    if not correcto:
                        entrada["incidencias"].append("La respuesta visible difiere del criterio o de la validación")
                except Exception as exc:
                    entrada["incidencias"].append(f"Página o comprobación: {exc}")
                entrada["url_visible"] = pagina.url
                try:
                    ruta.parent.mkdir(parents=True, exist_ok=True)
                    if semiautomatico:
                        input(f"Guarda la ventana de Edge con su barra de direcciones en {ruta}. Pulsa Enter después. ")
                        if not ruta.is_file():
                            raise RuntimeError("No se guardó el PNG manual")
                        entrada["modo"] = "captura manual: revisar encuadre y legibilidad"
                    else:
                        if hwnd is None:
                            raise RuntimeError("No se identificó una única ventana nueva de Edge")
                        estado = enfocar_y_encuadrar(pagina, hwnd, analisis)
                        entrada["encuadre"] = estado
                        if not estado or not estado["cabe"]:
                            entrada["incidencias"].append("La página completa no cabe en la ventana")
                        imagen = ventana_nativa(hwnd, ImageGrab)
                        guardar_png(imagen, ruta)
                        entrada["dimensiones_px"] = list(imagen.size)
                    entrada["fecha_captura_utc"] = fecha()
                    entrada["sha256_png"] = hashlib.sha256(ruta.read_bytes()).hexdigest()
                except Exception as exc:
                    entrada["incidencias"].append(f"Captura de ventana: {exc}")
                entrada["resultado"] = "incidencia" if entrada["incidencias"] else "verificado"
        finally:
            navegador.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validacion", help="Nombre de carpeta en INDICE.md. Por defecto, la última de ri con 62")
    parser.add_argument("--escala-unitaria", action="store_true",
                        help="Fija la escala de Edge en 1 para ajustar mejor el zoom de las tablas largas")
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--revision", action="store_true", help="Guardar la ejecución en una carpeta nueva")
    modo.add_argument("--manual", action="store_true", help="Modo de revisión con captura manual de la ventana")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("La captura requiere Windows")
    ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    try:
        validacion, casos, token, fuentes = preflight(args.validacion)
        plan = list(plan_capturas(token))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Requisito de captura no cumplido: {exc}\n")
    destino = DESTINO
    if args.revision or args.manual:
        destino /= f"revision_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid4().hex[:8]}"
        destino.mkdir()
    informe = destino / "registro_capturas_solr.json"
    if informe.exists() or any((destino / g / n).exists() for g, _, n, _, _ in plan):
        parser.exit(1, "Ya existen evidencias. Usa --revision para ejecutar sin sobrescribir.\n")
    registro = {"inicio_utc": fecha(), "core": "ri", "documentos": 62, "tipo_fuente": fuentes,
                "validacion": validacion.relative_to(RAIZ).as_posix(),
                "sha256_validacion": hashlib.sha256(validacion.read_bytes()).hexdigest(),
                "token_indice_y01": token, "capturas": []}
    with informe.open("x", encoding="utf-8") as salida:
        try:
            capturar(plan, casos, destino, registro, args.manual, args.escala_unitaria)
        except Exception as exc:
            registro["error_ejecucion"] = str(exc)
            print(f"Captura interrumpida: {exc}", file=sys.stderr)
        finally:
            registro["fin_utc"] = fecha()
            json.dump(registro, salida, ensure_ascii=False, indent=2)
            salida.write("\n")
    print(informe.relative_to(RAIZ))
    return int(len(registro["capturas"]) != 12 or any(e["resultado"] != "verificado" for e in registro["capturas"]))


if __name__ == "__main__":
    raise SystemExit(main())
