"""Crea o actualiza los tipos de campo de español mediante la Schema API.

Uso (desde proyecto-final-solr/):
    py analisis_es/configurar_analizadores.py                      # core de prueba, todos los tipos
    py analisis_es/configurar_analizadores.py --tipos text_es_stop
    py analisis_es/configurar_analizadores.py --core ri            # integración (coordinar con Joseph)

Solo crea TIPOS (no campos). Nunca modifica text_es_ri. Se puede repetir:
si un tipo ya existe, se reemplaza por la definición actual del repositorio.
"""

import argparse

from configuracion import CORE_PRODUCCION, CORE_PRUEBA, TIPO_CONTROL
from definiciones_tipos import DEFINIDORES_TIPOS, TIPO_STEMMING, leer_text_es_ri_del_kit
from recursos_gestionados import sincronizar_sinonimos, sincronizar_stopwords
from solr_cliente import ErrorSolr, asegurar_core_de_prueba, core_existe, enviar, exigir_solr, recargar_core

TIPOS_SIN_RECURSOS_GESTIONADOS = {TIPO_STEMMING}
AVISO_REINDEXAR = (
    "Aviso: se reemplazó {tipo}. Si cambió su analizador de índice, "
    "hay que reindexar los campos que lo usan (ver README, P03-09)."
)


def agregar_o_reemplazar(core: str, entidad: str, definicion: dict) -> str:
    """Agrega un 'field-type' o 'field'; si ya existe, lo reemplaza.

    Devuelve 'creado' o 'reemplazado'.
    """
    if definicion["name"] == TIPO_CONTROL:
        raise ValueError(f"{TIPO_CONTROL} es el control del kit y no se modifica.")
    try:
        enviar(core, "schema", {f"add-{entidad}": definicion})
        return "creado"
    except ErrorSolr as error:
        if not error.es_ya_existe:
            raise
    enviar(core, "schema", {f"replace-{entidad}": definicion})
    return "reemplazado"


def crear_o_actualizar_tipo(core: str, definicion: dict) -> str:
    return agregar_o_reemplazar(core, "field-type", definicion)


def asegurar_tipo_control(core: str) -> str:
    """Crea text_es_ri idéntico al kit si falta. Nunca lo reemplaza."""
    try:
        enviar(core, "schema", {"add-field-type": leer_text_es_ri_del_kit()})
        return "creado"
    except ErrorSolr as error:
        if error.es_ya_existe:
            return "ya existía (sin cambios)"
        raise


def preparar_core(core: str) -> None:
    if core == CORE_PRODUCCION:
        if not core_existe(core):
            raise SystemExit(f"El core '{core}' no existe; debe crearlo Joseph (docker compose del kit).")
        return
    asegurar_core_de_prueba(core)


def sincronizar_recursos(core: str) -> None:
    # Solr registra los recursos gestionados al recargar el esquema.
    recargar_core(core)
    print(f"  stopwords: {sincronizar_stopwords(core)} palabras")
    print(f"  sinónimos: {sincronizar_sinonimos(core)} grupos")
    recargar_core(core)


def configurar_tipos(core: str, nombres: list[str]) -> None:
    preparar_core(core)
    print(f"Core '{core}':")
    for nombre in nombres:
        estado = crear_o_actualizar_tipo(core, DEFINIDORES_TIPOS[nombre]())
        print(f"  {nombre}: {estado}")
        if estado == "reemplazado" and core == CORE_PRODUCCION:
            print("  " + AVISO_REINDEXAR.format(tipo=nombre))
    if set(nombres) - TIPOS_SIN_RECURSOS_GESTIONADOS:
        sincronizar_recursos(core)


def leer_argumentos(argumentos=None) -> argparse.Namespace:
    lector = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    lector.add_argument("--core", default=CORE_PRUEBA, help=f"core destino (por defecto {CORE_PRUEBA})")
    lector.add_argument("--tipos", nargs="+", choices=list(DEFINIDORES_TIPOS), default=list(DEFINIDORES_TIPOS))
    return lector.parse_args(argumentos)


def main(argumentos=None) -> None:
    opciones = leer_argumentos(argumentos)
    exigir_solr()
    configurar_tipos(opciones.core, opciones.tipos)


if __name__ == "__main__":
    main()
