"""Construye el HTML de las páginas a partir de las plantillas."""
import html
from string import Template
from urllib.parse import quote

from busqueda.ranking import Busqueda, DetalleTermino, Resultado
from config import ajustes
import texto


def renderizar(nombre_plantilla: str, valores: dict[str, str]) -> str:
    """Lee una plantilla y sustituye sus marcadores."""
    ruta = ajustes.CARPETA_PLANTILLAS / nombre_plantilla
    return Template(ruta.read_text(encoding="utf-8")).safe_substitute(valores)


def construir_mensaje(tipo: str, texto_mensaje: str) -> str:
    """Construye una alerta de Bootstrap con el texto escapado."""
    return renderizar("parcial_mensaje.html", {"tipo": tipo, "texto": html.escape(texto_mensaje)})


def construir_inicio(total_documentos: int, total_terminos: int, mensaje: tuple[str, str] | None = None) -> str:
    """Construye la página de inicio con los totales y un mensaje opcional."""
    return renderizar(
        "index.html",
        {
            "total_documentos": str(total_documentos),
            "total_terminos": str(total_terminos),
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


def _resaltar(fragmento: str, terminos: frozenset[str]) -> str:
    """Escapa el fragmento y envuelve en <mark> las palabras de la consulta."""
    normalizado = texto.normalizar(fragmento)
    partes = []
    cursor = 0
    for coincidencia in texto.PATRON_PALABRA.finditer(normalizado):
        if coincidencia.group() in terminos:
            partes.append(html.escape(fragmento[cursor:coincidencia.start()]))
            partes.append(f"<mark>{html.escape(fragmento[coincidencia.start():coincidencia.end()])}</mark>")
            cursor = coincidencia.end()
    partes.append(html.escape(fragmento[cursor:]))
    return "".join(partes)


def _filas_calculo(detalle: tuple[DetalleTermino, ...]) -> str:
    """Construye las filas de la tabla del cálculo tf-idf."""
    return "".join(
        f"<tr><td>{html.escape(d.termino)}</td><td>{d.tf}</td><td>{d.df}</td>"
        f"<td>{d.idf:.4f}</td><td>{d.peso:.4f}</td></tr>"
        for d in detalle
    )


def _construir_resultado(resultado: Resultado, terminos: frozenset[str], total_documentos: int) -> str:
    """Construye el HTML de un resultado."""
    return renderizar(
        "parcial_resultado.html",
        {
            "url_descarga": "/archivos/" + quote(resultado.nombre_archivo),
            "titulo": html.escape(_titulo(resultado.nombre_archivo)),
            "nombre_archivo": html.escape(resultado.nombre_archivo),
            "fragmento": _resaltar(resultado.fragmento, terminos),
            "palabras": _plural(resultado.palabras, "palabra", "palabras"),
            "tokens": _plural(resultado.tokens, "token indexado", "tokens indexados"),
            "tamano": _tamano(resultado.tamano),
            "fecha": html.escape(resultado.fecha),
            "filas_calculo": _filas_calculo(resultado.detalle),
            "total_documentos": str(total_documentos),
            "relevancia": f"{resultado.relevancia:.4f}",
            "coseno": f"{resultado.coseno:.4f}",
        },
    )


def _resumen(total: int) -> str:
    """Redacta cuántos documentos se encontraron."""
    return "1 documento encontrado" if total == 1 else f"{total} documentos encontrados"


def _aviso(busqueda: Busqueda) -> str:
    """Avisa de las palabras que no ayudan o que no están en el índice."""
    if not busqueda.terminos:
        return construir_mensaje(
            "info", "La consulta solo tiene palabras muy comunes. Prueba con términos más específicos."
        )
    if busqueda.ignorados:
        return construir_mensaje(
            "warning", "No aparecen en ningún documento: " + ", ".join(busqueda.ignorados) + "."
        )
    return ""


def construir_resultados(consulta: str, busqueda: Busqueda) -> str:
    """Construye la página de resultados de una consulta."""
    consulta_segura = html.escape(consulta)
    terminos = frozenset(busqueda.terminos)
    if busqueda.resultados:
        lista = "".join(
            _construir_resultado(resultado, terminos, busqueda.total_documentos)
            for resultado in busqueda.resultados
        )
    else:
        lista = renderizar("parcial_sin_resultados.html", {"consulta": consulta_segura})
    return renderizar(
        "resultados.html",
        {
            "consulta": consulta_segura,
            "total_resultados": _resumen(len(busqueda.resultados)),
            "lista_resultados": lista,
            "mensaje": _aviso(busqueda),
        },
    )