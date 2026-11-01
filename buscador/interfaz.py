"""Pantallas HTML (inicio, resultados y lector de documento)."""
from html import escape
from urllib.parse import quote_plus

import config
import indexador
import texto

FUENTES = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
    'family=Instrument+Sans:wght@400;500;600&display=swap">'
)

CSS = """
:root {
  --bg: #F6F7F9;  --surface: #FFFFFF;  --ink: #171A21;  --muted: #6A7385;
  --line: #E2E5EA;  --accent: #0E7C86;  --on-accent: #FFFFFF;
  --accent-soft: rgba(14, 124, 134, .13);
  --fuente: "Instrument Sans", "Segoe UI Variable", "Segoe UI", system-ui, sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0E1215;  --surface: #161B1F;  --ink: #E8ECEF;  --muted: #8C96A4;
    --line: #262D34;  --accent: #4CC2CB;  --on-accent: #062428;
    --accent-soft: rgba(76, 194, 203, .18);
  }
}
* { box-sizing: border-box; }
html { color-scheme: light dark; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 400 16px/1.55 var(--fuente); -webkit-font-smoothing: antialiased;
}
a { color: inherit; text-decoration: none; }
button { font: inherit; cursor: pointer; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; border-radius: 6px; }

/* Campo de búsqueda */
.buscador {
  display: flex; align-items: center; gap: 8px;
  background: var(--surface); border: 1px solid var(--line); border-radius: 999px;
  padding: 6px 6px 6px 22px; transition: border-color .15s, box-shadow .15s;
}
.buscador:focus-within { border-color: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft); }
.buscador input {
  flex: 1; min-width: 0; border: 0; outline: 0; background: transparent;
  color: var(--ink); font: inherit; font-size: 1.08rem; padding: 11px 0;
}
.buscador input::placeholder { color: var(--muted); }
.buscador button {
  border: 0; border-radius: 999px; background: var(--accent); color: var(--on-accent);
  font-weight: 500; padding: 11px 22px;
}
.buscador button:hover { filter: brightness(1.08); }

/* Inicio */
.inicio {
  min-height: 100vh; max-width: 660px; margin: 0 auto; padding: 32px 22px 48px;
  display: flex; flex-direction: column; justify-content: center;
}
.marca { margin: 0 0 10px; font-size: clamp(3rem, 11vw, 4.6rem); font-weight: 600; letter-spacing: -.045em; line-height: 1; }
.lema { margin: 0 0 32px; color: var(--muted); font-size: 1.1rem; max-width: 34ch; }
.estado { margin: 18px 0 0 22px; color: var(--muted); font-size: .95rem; }
.aviso { margin: 8px 0 0 22px; color: var(--accent); font-size: .95rem; }
.reindexar { margin: 36px 0 0 22px; }
.texto-btn { border: 0; background: none; padding: 0; color: var(--muted); font-size: .92rem; text-decoration: underline; text-underline-offset: 3px; }
.texto-btn:hover { color: var(--ink); }

/* Resultados */
.cabecera {
  position: sticky; top: 0; z-index: 5; background: var(--bg);
  border-bottom: 1px solid var(--line);
}
.cabecera-in {
  max-width: 820px; margin: 0 auto; padding: 14px 22px;
  display: flex; align-items: center; gap: 24px;
}
.logo { font-weight: 600; font-size: 1.25rem; letter-spacing: -.03em; }
.cabecera .buscador { flex: 1; }
.cabecera .buscador input { padding: 8px 0; font-size: 1rem; }
.cabecera .buscador button { padding: 8px 18px; }

.contenido { max-width: 820px; margin: 0 auto; padding: 26px 22px 72px; }
.resumen { margin: 0 0 4px; color: var(--muted); font-size: .95rem; }
.nota { margin: 4px 0 0; color: var(--muted); font-size: .95rem; }
.nota b { color: var(--ink); font-weight: 500; }

.lista { list-style: none; margin: 18px 0 0; padding: 0; }
.res { display: grid; grid-template-columns: 34px 1fr; gap: 0 6px; padding: 24px 0; border-top: 1px solid var(--line); }
.res:first-child { border-top: 0; }
.rango { color: var(--muted); font-size: .95rem; padding-top: 3px; font-variant-numeric: tabular-nums; }
.res h2 { margin: 0; font-size: 1.22rem; font-weight: 600; letter-spacing: -.015em; line-height: 1.3; }
.res h2 a:hover { color: var(--accent); }

.puntaje { display: flex; align-items: center; gap: 12px; margin: 9px 0 11px; }
.pista { flex: 0 1 220px; width: 220px; height: 5px; border-radius: 99px; background: var(--line); overflow: hidden; }
.pista i { display: block; height: 100%; background: var(--accent); border-radius: 99px; }
.valor { color: var(--ink); font-size: .9rem; font-weight: 500; font-variant-numeric: tabular-nums; }
.etiqueta { color: var(--muted); font-size: .9rem; }

.frag { margin: 0; color: var(--muted); max-width: 68ch; }
mark { background: var(--accent-soft); color: var(--ink); border-radius: 4px; padding: 0 2px; }
.meta { display: flex; flex-wrap: wrap; gap: 4px 18px; margin-top: 12px; color: var(--muted); font-size: .88rem; }

details { margin-top: 12px; }
summary { cursor: pointer; width: fit-content; color: var(--muted); font-size: .9rem; list-style: none; }
summary::-webkit-details-marker { display: none; }
summary::before { content: "+"; display: inline-block; width: 1.1em; }
details[open] summary::before { content: "−"; }
summary:hover { color: var(--ink); }
.calculo { margin-top: 12px; background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 12px 16px; overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: .9rem; font-variant-numeric: tabular-nums; }
th, td { padding: 6px 14px 6px 0; text-align: right; white-space: nowrap; }
th:first-child, td:first-child { text-align: left; }
th { color: var(--muted); font-weight: 500; border-bottom: 1px solid var(--line); }
.formula { margin: 10px 0 0; color: var(--muted); font-size: .85rem; }

.vacio { margin-top: 56px; max-width: 46ch; }
.vacio h2 { margin: 0 0 6px; font-size: 1.2rem; font-weight: 600; }
.vacio p { margin: 0; color: var(--muted); }

/* Lector */
.lector { max-width: 700px; margin: 0 auto; padding: 36px 22px 80px; }
.volver { color: var(--muted); font-size: .95rem; }
.volver:hover { color: var(--ink); }
.lector h1 { margin: 22px 0 8px; font-size: clamp(1.8rem, 5vw, 2.4rem); font-weight: 600; letter-spacing: -.03em; line-height: 1.15; }
.lector .meta { margin: 0 0 30px; }
.cuerpo-doc { white-space: pre-wrap; font-size: 1.05rem; line-height: 1.75; max-width: 68ch; }

@media (max-width: 560px) {
  .cabecera-in { flex-wrap: wrap; gap: 10px; }
  .cabecera .buscador { flex-basis: 100%; }
  .res { grid-template-columns: 26px 1fr; }
  .pista { width: 140px; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""


# ── Utilidades ───────────────────────────────────────────────────────────────
def _pagina(titulo, cuerpo):
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(titulo)}</title>{FUENTES}<style>{CSS}</style></head>"
        f"<body>{cuerpo}</body></html>"
    )


def _formulario(q="", foco=False):
    return (
        '<form class="buscador" action="/buscar" method="get" role="search">'
        f'<input type="search" name="q" value="{escape(q, quote=True)}" '
        'placeholder="Escribe lo que quieres encontrar" aria-label="Consulta" '
        f'autocomplete="off"{" autofocus" if foco else ""}>'
        '<button type="submit">Buscar</button></form>'
    )


def _tamano(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.1f} MB"


def _titulo(archivo):
    nombre = archivo.rsplit("/", 1)[-1]
    if nombre.lower().endswith(".txt"):
        nombre = nombre[:-4]
    nombre = nombre.replace("_", " ").replace("-", " ").strip()
    return nombre[:1].upper() + nombre[1:]


def _plural(n, singular, plural):
    return f"{n} {singular if n == 1 else plural}"


def _leer(archivo):
    return indexador.leer_archivo(config.CARPETA_DOCUMENTOS / archivo)


def _resaltar(trozo, terminos):
    """Escapa el texto y envuelve en <mark> las palabras de la consulta."""
    salida, cursor = [], 0
    for m in texto.PATRON.finditer(trozo):
        salida.append(escape(trozo[cursor:m.start()]))
        palabra = escape(m.group())
        if texto.normalizar(m.group()) in terminos:
            palabra = f"<mark>{palabra}</mark>"
        salida.append(palabra)
        cursor = m.end()
    salida.append(escape(trozo[cursor:]))
    return "".join(salida)


def _fragmento(contenido, terminos, largo=240):
    """Elige la ventana de texto con más palabras de la consulta."""
    plano = " ".join(contenido.split())
    if not plano:
        return ""
    aciertos = [m.start() for m in texto.PATRON.finditer(plano)
                if texto.normalizar(m.group()) in terminos]
    ini = 0
    if aciertos:
        mejor, mejor_n = aciertos[0], 0
        for a in aciertos[:300]:
            n = sum(1 for b in aciertos if a <= b < a + largo)
            if n > mejor_n:
                mejor, mejor_n = a, n
        ini = max(0, mejor - 40)
    fin = min(len(plano), ini + largo)
    while ini > 0 and not plano[ini - 1].isspace():
        ini -= 1
    while fin < len(plano) and not plano[fin].isspace():
        fin += 1
    return (("… " if ini > 0 else "")
            + _resaltar(plano[ini:fin].strip(), terminos)
            + (" …" if fin < len(plano) else ""))


# ── Pantallas ────────────────────────────────────────────────────────────────
def inicio(stats, mensaje=""):
    if stats["documentos"]:
        estado = (f'{_plural(stats["documentos"], "documento indexado", "documentos indexados")} '
                  f'con {_plural(stats["terminos"], "término", "términos")}.')
    else:
        estado = (f"Todavía no hay documentos. Copia archivos .txt en la carpeta "
                  f"«{config.CARPETA_DOCUMENTOS.name}» y pulsa Reindexar.")
    aviso = f'<p class="aviso">{escape(mensaje)}</p>' if mensaje else ""
    cuerpo = (
        '<main class="inicio"><h1 class="marca">Buscador</h1>'
        '<p class="lema">Busca en tus documentos y ve primero los más relevantes.</p>'
        f'{_formulario(foco=True)}<p class="estado">{estado}</p>{aviso}'
        '<form class="reindexar" method="post" action="/reindexar">'
        '<button class="texto-btn" type="submit">Reindexar documentos</button></form></main>'
    )
    return _pagina("Buscador", cuerpo)


def resultados(res):
    q = res["consulta"]
    terminos = set(res["terminos"])
    cabecera = (
        '<header class="cabecera"><div class="cabecera-in">'
        f'<a class="logo" href="/">Buscador</a>{_formulario(q)}</div></header>'
    )

    notas = ""
    if res["ignorados"] and res["terminos"]:
        lista = ", ".join(f"<b>{escape(t)}</b>" for t in res["ignorados"])
        notas = f'<p class="nota">No están en el índice: {lista}.</p>'

    if not res["terminos"]:
        cuerpo = (
            '<div class="vacio"><h2>La consulta no tiene términos útiles</h2>'
            "<p>Solo contiene palabras muy comunes (como «de» o «la») o está vacía. "
            "Prueba con palabras más específicas.</p></div>")
    elif not res["resultados"]:
        extra = ""
        if res["total"] == 0 and len(res["ignorados"]) < len(res["terminos"]):
            extra = (" Los términos aparecen en todos los documentos, así que su IDF es 0 "
                     "y no ayudan a ordenar. Activa IDF_SUAVIZADO en config.py o usa un término más específico.")
        cuerpo = (
            f'<div class="vacio"><h2>Ningún documento coincide con «{escape(q)}»</h2>'
            f"<p>Prueba con otras palabras o con términos más generales.{extra}</p></div>")
    else:
        filas = []
        for i, r in enumerate(res["resultados"], start=1):
            frag = _fragmento(_leer(r["archivo"]), terminos)
            ancho = f'{r["score"] * 100:.1f}'
            tabla = "".join(
                f'<tr><td>{escape(d["token"])}</td><td>{d["tf"]}</td><td>{d["df"]}</td>'
                f'<td>{d["idf"]:.3f}</td><td>{d["peso"]:.3f}</td></tr>'
                for d in r["detalle"])
            filas.append(
                '<li class="res">'
                f'<div class="rango">{i}</div><div>'
                f'<h2><a href="/documento?id={r["id"]}&q={quote_plus(q)}">{escape(_titulo(r["archivo"]))}</a></h2>'
                f'<div class="puntaje"><span class="pista" role="img" aria-label="Similitud {r["score"]:.3f}">'
                f'<i style="width:{ancho}%"></i></span>'
                f'<span class="valor">{r["score"]:.3f}</span><span class="etiqueta">similitud</span></div>'
                f'<p class="frag">{frag}</p>'
                f'<div class="meta"><span>{escape(r["archivo"])}</span>'
                f'<span>{_plural(r["palabras"], "palabra", "palabras")}</span>'
                f'<span>{_tamano(r["tamano"])}</span><span>{escape(r["fecha"])}</span></div>'
                '<details><summary>Ver cálculo TF-IDF</summary><div class="calculo">'
                '<table><thead><tr><th>Término</th><th>TF</th><th>DF</th><th>IDF</th><th>TF·IDF</th></tr></thead>'
                f'<tbody>{tabla}</tbody></table>'
                f'<p class="formula">Similitud coseno entre la consulta y el documento, con N = {res["N"]}.</p>'
                '</div></details></div></li>')
        mostrados = len(res["resultados"])
        resumen = _plural(res["total"], "documento ordenado", "documentos ordenados") + " por similitud"
        if res["total"] > mostrados:
            resumen += f" (se muestran los {mostrados} primeros)"
        cuerpo = f'<p class="resumen">{resumen}.</p>{notas}<ol class="lista">{"".join(filas)}</ol>'
        return _pagina(f"{q} · Buscador", f'{cabecera}<main class="contenido">{cuerpo}</main>')

    return _pagina(f"{q} · Buscador", f'{cabecera}<main class="contenido">{notas}{cuerpo}</main>')


def documento(fila, q):
    id_doc, archivo, fecha, palabras, tokens, tamano = fila
    terminos = set(texto.terminos_de_consulta(q))
    volver = f"/buscar?q={quote_plus(q)}" if q else "/"
    cuerpo = (
        f'<main class="lector"><a class="volver" href="{volver}">Volver a los resultados</a>'
        f'<h1>{escape(_titulo(archivo))}</h1>'
        f'<div class="meta"><span>{escape(archivo)}</span>'
        f'<span>{_plural(palabras, "palabra", "palabras")}</span>'
        f'<span>{_plural(tokens, "token", "tokens")} tras quitar palabras vacías</span>'
        f'<span>{_tamano(tamano)}</span><span>{escape(str(fecha)[:10])}</span></div>'
        f'<div class="cuerpo-doc">{_resaltar(_leer(archivo), terminos)}</div></main>'
    )
    return _pagina(f"{_titulo(archivo)} · Buscador", cuerpo)


def error(titulo, detalle):
    cuerpo = (
        '<main class="lector"><a class="volver" href="/">Volver al inicio</a>'
        f'<h1>{escape(titulo)}</h1><p class="frag">{escape(detalle)}</p></main>'
    )
    return _pagina(titulo, cuerpo)
