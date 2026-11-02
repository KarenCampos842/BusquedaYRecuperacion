"""Construye el HTML de las páginas a partir de las plantillas."""
import html
from string import Template
from urllib.parse import quote

from busqueda.ranking import Resultado
from config import ajustes


def renderizar(nombre_plantilla: str, valores: dict[str, str]) -> str:
    """Lee una plantilla y sustituye sus marcadores."""
    ruta = ajustes.CARPETA_PLANTILLAS / nombre_plantilla
    return Template(ruta.read_text(encoding="utf-8")).safe_substitute(valores)


def construir_mensaje(tipo: str, texto: str) -> str:
    """Construye una alerta de Bootstrap con el texto escapado."""
    return renderizar("parcial_mensaje.html", {"tipo": tipo, "texto": html.escape(texto)})


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


def _construir_resultado(resultado: Resultado) -> str:
    """Construye el HTML de un resultado."""
    return renderizar(
        "parcial_resultado.html",
        {
            "url_descarga": "/archivos/" + quote(resultado.nombre_archivo),
            "nombre_archivo": html.escape(resultado.nombre_archivo),
            "fragmento": html.escape(resultado.fragmento),
            "relevancia": f"{resultado.relevancia:.4f}",
            "coseno": f"{resultado.coseno:.4f}",
        },
    )


def _resumen(total: int) -> str:
    """Redacta cuántos documentos se encontraron."""
    return "1 documento encontrado" if total == 1 else f"{total} documentos encontrados"


def construir_resultados(consulta: str, resultados: list[Resultado]) -> str:
    """Construye la página de resultados de una consulta."""
    consulta_segura = html.escape(consulta)
    if resultados:
        lista = "".join(_construir_resultado(resultado) for resultado in resultados)
    else:
        lista = renderizar("parcial_sin_resultados.html", {"consulta": consulta_segura})
    return renderizar(
        "resultados.html",
        {
            "consulta": consulta_segura,
            "total_resultados": _resumen(len(resultados)),
            "lista_resultados": lista,
            "mensaje": "",
        },
    )
