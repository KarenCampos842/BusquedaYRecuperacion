"""P05-03 y P05-06 · Configura Suggester y SpellCheck con sus campos y copyField.

Uso (desde proyecto-final-solr/):
    py analisis_es/configurar_sugerencias_ortografia.py                       # core de prueba ri_sugerencias_es
    py analisis_es/configurar_sugerencias_ortografia.py --core ri             # modo de prueba: solo muestra
    py analisis_es/configurar_sugerencias_ortografia.py --core ri --aplicar   # pide escribir "ri"

Aplica, en orden y de forma repetible:
1. Tipos text_sugerencia_es y text_ortografia_es (Schema API).
2. Campos titulo_sugerencia y contenido_ortografia y sus copyField desde
   titulo y contenido. NO crea ni modifica titulo ni contenido: deben existir.
3. Componentes sugerencias_es y ortografia_es y handlers /sugerencias y
   /ortografia (Config API). No toca `spellcheck` ni `/spell` del configset.
En `ri` se ejecuta en la máquina del Solr de destino y solo con confirmación.
"""

import argparse
import json

from aplicar_en_ri import confirmado
from configuracion import CORE_PRODUCCION, CORE_SUGERENCIAS
from configurar_analizadores import agregar_o_reemplazar
from definiciones_sugerencias import (
    CAMPO_CONTENIDO,
    CAMPO_TITULO,
    CAMPOS_AUXILIARES,
    CONFIGURACION_SOLRCONFIG,
    COPIAS,
    DEFINIDORES_TIPOS_SUGERENCIAS,
)
from solr_cliente import ErrorSolr, enviar, exigir_solr, obtener

CAMPOS_REQUERIDOS = (CAMPO_TITULO, CAMPO_CONTENIDO)


def campo_existe(core: str, campo: str) -> bool:
    try:
        obtener(core, f"schema/fields/{campo}")
        return True
    except ErrorSolr as error:
        if error.estado == 404:
            return False
        raise


def exigir_campos_origen(core: str) -> None:
    faltantes = [campo for campo in CAMPOS_REQUERIDOS if not campo_existe(core, campo)]
    if faltantes:
        raise SystemExit(f"En '{core}' faltan {faltantes}: los define Joseph antes de crear los copyField.")


def agregar_copias_faltantes(core: str) -> list[str]:
    existentes = {(c["source"], c["dest"]) for c in obtener(core, "schema/copyfields")["copyFields"]}
    agregadas = []
    for copia in COPIAS:
        if (copia["source"], copia["dest"]) not in existentes:
            enviar(core, "schema", {"add-copy-field": copia})
            agregadas.append(f"{copia['source']} -> {copia['dest']}")
    return agregadas


def agregar_o_actualizar_config(core: str, comando: str, definicion: dict) -> str:
    """Config API: add-<comando>; si ya existe, update-<comando>."""
    try:
        enviar(core, "config", {f"add-{comando}": definicion})
        return "creado"
    except ErrorSolr as error:
        if not error.es_ya_existe:
            raise
    enviar(core, "config", {f"update-{comando}": definicion})
    return "actualizado"


def configurar(core: str) -> None:
    exigir_campos_origen(core)
    for nombre, definir in DEFINIDORES_TIPOS_SUGERENCIAS.items():
        print(f"  tipo {nombre}: {agregar_o_reemplazar(core, 'field-type', definir())}")
    for campo in CAMPOS_AUXILIARES:
        print(f"  campo {campo['name']}: {agregar_o_reemplazar(core, 'field', campo)}")
    print(f"  copyField nuevos: {agregar_copias_faltantes(core) or 'ninguno (ya existían)'}")
    for comando, definicion in CONFIGURACION_SOLRCONFIG:
        print(f"  {comando} {definicion['name']}: {agregar_o_actualizar_config(core, comando, definicion)}")


def describir_cambios(core: str) -> dict:
    return {
        "core": core,
        "tipos": [definir() for definir in DEFINIDORES_TIPOS_SUGERENCIAS.values()],
        "campos": CAMPOS_AUXILIARES,
        "copyField": COPIAS,
        "solrconfig (Config API)": [definicion for _, definicion in CONFIGURACION_SOLRCONFIG],
        "no_se_modifica": [CAMPO_TITULO, CAMPO_CONTENIDO, "documentos", "spellcheck", "/spell"],
    }


def leer_argumentos(argumentos=None) -> argparse.Namespace:
    lector = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    lector.add_argument("--core", default=CORE_SUGERENCIAS, help=f"core destino (por defecto {CORE_SUGERENCIAS})")
    lector.add_argument("--aplicar", action="store_true", help=f"obligatorio para aplicar en '{CORE_PRODUCCION}'")
    return lector.parse_args(argumentos)


def main(argumentos=None, leer_respuesta=input) -> None:
    opciones = leer_argumentos(argumentos)
    exigir_solr()
    if opciones.core == CORE_PRODUCCION:
        print("Cambios previstos:", json.dumps(describir_cambios(opciones.core), ensure_ascii=False, indent=2))
        if not opciones.aplicar:
            print("\nModo de prueba: no se envió nada. Use --aplicar para ejecutar.")
            return
        if not confirmado(leer_respuesta):
            print(f"Cancelado: no se modificó '{CORE_PRODUCCION}'.")
            return
    print(f"Core '{opciones.core}':")
    configurar(opciones.core)


if __name__ == "__main__":
    main()
