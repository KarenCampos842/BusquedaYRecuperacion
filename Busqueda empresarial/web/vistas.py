"""Construye el HTML de las páginas a partir de las plantillas."""
import html
from string import Template
from urllib.parse import quote

from base_datos.repositorios.repositorio_fulltext import ConfiguracionFulltext
from busqueda.ranking import MODOS, Busqueda, Modo, Resultado
from config import ajustes
import texto


def renderizar(nombre_plantilla: str, valores: dict[str, str]) -> str:
    """Lee una plantilla y sustituye sus marcadores."""
    ruta = ajustes.CARPETA_PLANTILLAS / nombre_plantilla
    return Template(ruta.read_text(encoding="utf-8")).safe_substitute(valores)


def construir_mensaje(tipo: str, texto_mensaje: str) -> str:
    """Construye una alerta con el texto escapado."""
    return renderizar("parcial_mensaje.html", {"tipo": tipo, "texto": html.escape(texto_mensaje)})


def _opciones_modo(seleccionado: Modo) -> str:
    """Construye los botones de radio para elegir el modo de búsqueda."""
    opciones = []
    for modo in MODOS.values():
        marcado = " checked" if modo.clave == seleccionado.clave else ""
        opciones.append(
            f'<label class="modo" title="{html.escape(modo.descripcion)}">'
            f'<input type="radio" name="modo" value="{modo.clave}" form="form-busqueda"{marcado}>'
            f"<span>{html.escape(modo.nombre)}</span></label>"
        )
    return "".join(opciones)


def _ayuda_modos() -> str:
    """Construye la explicación de cada modo."""
    return "".join(
        f"<li><strong>{html.escape(modo.nombre)}</strong>: {html.escape(modo.descripcion)}</li>"
        for modo in MODOS.values()
    )


def construir_inicio(
    total_documentos: int,
    total_palabras: int,
    total_stopwords: int,
    configuracion: ConfiguracionFulltext,
    mensaje: tuple[str, str] | None = None,
) -> str:
    """Construye la página de inicio con los totales, la configuración y un mensaje opcional."""
    return renderizar(
        "index.html",
        {
            "total_documentos": str(total_documentos),
            "total_palabras": str(total_palabras),
            "total_stopwords": str(total_stopwords),
            "version": html.escape(configuracion.version),
            "longitud_minima": str(configuracion.longitud_minima),
            "longitud_maxima": str(configuracion.longitud_maxima),
            "opciones_modo": _opciones_modo(MODOS["natural"]),
            "ayuda_modos": _ayuda_modos(),
            "mensaje": construir_mensaje(*mensaje) if mensaje else "",
        },
    )


def _titulo(nombre_archivo: str) -> str:
    """Convierte 'java_café.txt' en 'Java café'."""
    base = nombre_archivo[:-4] if nombre_archivo.lower().endswith(".txt") else nombre_archivo
    base = " ".join(base.replace("_", " ").replace("-", " ").split())
    return base[:1].upper() + base[1:] if base else nombre_archivo


def _tamano(bytes_: int) -> str:
    """Da formato legible a un tamaño en bytes."""
    if bytes_ < 1024:
        return f"{bytes_} B"
    if bytes_ < 1024 ** 2:
        return f"{bytes_ / 1024:.1f} KB"
    return f"{bytes_ / 1024 ** 2:.1f} MB"


def _plural(cantidad: int, singular: str, plural: str) -> str:
    """Devuelve '1 palabra' o 'N palabras'."""
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _resaltar(fragmento: str, palabras: frozenset[str], prefijos: tuple[str, ...]) -> str:
    """Escapa el fragmento y envuelve en <mark> las palabras de la consulta."""
    normalizado = texto.normalizar(fragmento)
    partes = []
    cursor = 0
    for coincidencia in texto.PATRON_PALABRA.finditer(normalizado):
        if texto.coincide(coincidencia.group(), palabras, prefijos):
            partes.append(html.escape(fragmento[cursor:coincidencia.start()]))
            partes.append(f"<mark>{html.escape(fragmento[coincidencia.start():coincidencia.end()])}</mark>")
            cursor = coincidencia.end()
    partes.append(html.escape(fragmento[cursor:]))
    return "".join(partes)


def _construir_resultado(
    posicion: int, resultado: Resultado, palabras: frozenset[str], prefijos: tuple[str, ...]
) -> str:
    """Construye el HTML de un resultado."""
    return renderizar(
        "parcial_resultado.html",
        {
            "posicion": str(posicion),
            "url_descarga": "/archivos/" + quote(resultado.nombre_archivo),
            "titulo": html.escape(_titulo(resultado.nombre_archivo)),
            "nombre_archivo": html.escape(resultado.nombre_archivo),
            "fragmento": _resaltar(resultado.fragmento, palabras, prefijos),
            "palabras": _plural(resultado.palabras, "palabra", "palabras"),
            "tokens": _plural(resultado.tokens, "token indexable", "tokens indexables"),
            "tamano": _tamano(resultado.tamano),
            "fecha": html.escape(resultado.fecha),
            "relevancia": f"{resultado.relevancia:.6f}",
        },
    )


def _resumen(total: int) -> str:
    """Redacta cuántos documentos se encontraron."""
    return "1 documento encontrado" if total == 1 else f"{total} documentos encontrados"


def _aviso(busqueda: Busqueda) -> str:
    """Avisa de errores y de las palabras que MySQL no busca."""
    avisos = []
    if busqueda.error:
        avisos.append(construir_mensaje("danger", busqueda.error))
    if busqueda.ignorados:
        avisos.append(
            construir_mensaje("warning", "MySQL no busca estas palabras: " + ", ".join(busqueda.ignorados) + ".")
        )
    if busqueda.total_documentos == 0:
        avisos.append(construir_mensaje("info", "Todavía no hay documentos. Sube archivos .txt para buscar en ellos."))
    return "".join(avisos)


def construir_resultados(consulta: str, busqueda: Busqueda) -> str:
    """Construye la página de resultados de una consulta."""
    consulta_segura = html.escape(consulta)
    palabras = frozenset(busqueda.palabras)
    if busqueda.resultados:
        lista = "".join(
            _construir_resultado(numero, resultado, palabras, busqueda.prefijos)
            for numero, resultado in enumerate(busqueda.resultados, start=1)
        )
    else:
        lista = renderizar("parcial_sin_resultados.html", {"consulta": consulta_segura})
    return renderizar(
        "resultados.html",
        {
            "consulta": consulta_segura,
            "total_resultados": _resumen(len(busqueda.resultados)),
            "nombre_modo": html.escape(busqueda.modo.nombre),
            "descripcion_modo": html.escape(busqueda.modo.descripcion),
            "segundos": f"{busqueda.segundos:.4f}",
            "total_documentos": str(busqueda.total_documentos),
            "opciones_modo": _opciones_modo(busqueda.modo),
            "sql": html.escape(busqueda.sql or "La consulta no llegó a ejecutarse."),
            "lista_resultados": lista,
            "mensaje": _aviso(busqueda),
        },
    )
