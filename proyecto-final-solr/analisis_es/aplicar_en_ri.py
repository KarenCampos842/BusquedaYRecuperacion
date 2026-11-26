"""Aplica text_es_proyecto y sus recursos al core `ri`, con modo de prueba y confirmación.

Uso (desde proyecto-final-solr/):
    py analisis_es/aplicar_en_ri.py            # modo de prueba: solo muestra qué haría
    py analisis_es/aplicar_en_ri.py --aplicar  # pide escribir "ri" para confirmar

Qué hace al aplicar:
- Agrega (o reemplaza) solo el tipo text_es_proyecto y sincroniza los recursos
  gestionados `es_proyecto` (stopwords y sinónimos); después recarga `ri`.
- NO crea ni cambia campos, NO toca documentos y NO modifica text_es_ri.
  Cambiar `titulo`/`contenido` a text_es_proyecto y reindexar lo hace Joseph.
- Al terminar comprueba que text_es_ri sigue idéntico al kit.
"""

import argparse
import json

from configuracion import CORE_PRODUCCION, RECURSO_GESTIONADO, TIPO_CONTROL
from configurar_analizadores import configurar_tipos
from definiciones_tipos import TIPO_PROYECTO, definir_text_es_proyecto
from recursos_linguisticos import leer_grupos_sinonimos, leer_stopwords
from solr_cliente import ErrorSolr, exigir_solr, obtener
from verificar_linea_base import estado_tipo_en_produccion

TEXTO_CONFIRMACION = CORE_PRODUCCION
ESTADO_CONTROL_CORRECTO = "presente e idéntico al kit"


def describir_cambios() -> dict:
    """Lo que se enviaría a `ri` (sin red): útil para revisar antes de aplicar."""
    return {
        "core": CORE_PRODUCCION,
        "tipo": definir_text_es_proyecto(),
        "recurso_gestionado": RECURSO_GESTIONADO,
        "stopwords": len(leer_stopwords()),
        "grupos_sinonimos": len(leer_grupos_sinonimos()),
        "no_se_modifica": [TIPO_CONTROL, "campos", "documentos"],
    }


def tipo_existe(core: str, tipo: str) -> bool:
    try:
        obtener(core, f"schema/fieldtypes/{tipo}")
        return True
    except ErrorSolr as error:
        if error.estado == 404:
            return False
        raise


def estado_actual() -> dict:
    total = obtener(CORE_PRODUCCION, "select", {"q": "*:*", "rows": 0})["response"]["numFound"]
    return {
        TIPO_CONTROL: estado_tipo_en_produccion(),
        TIPO_PROYECTO: "existe (se reemplazaría)" if tipo_existe(CORE_PRODUCCION, TIPO_PROYECTO) else "no existe (se crearía)",
        "documentos": total,
    }


def confirmado(leer_respuesta=input) -> bool:
    respuesta = leer_respuesta(f'Escriba "{TEXTO_CONFIRMACION}" para aplicar los cambios en el core {CORE_PRODUCCION}: ')
    return respuesta.strip() == TEXTO_CONFIRMACION


def aplicar() -> None:
    configurar_tipos(CORE_PRODUCCION, [TIPO_PROYECTO])
    estado_control = estado_tipo_en_produccion()
    if estado_control != ESTADO_CONTROL_CORRECTO:
        raise SystemExit(f"ALERTA: {TIPO_CONTROL} quedó '{estado_control}'. Revisar antes de continuar.")
    print(f"Listo. {TIPO_CONTROL}: {estado_control}.")


def leer_argumentos(argumentos=None) -> argparse.Namespace:
    lector = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    lector.add_argument("--aplicar", action="store_true", help="aplica los cambios tras confirmar")
    return lector.parse_args(argumentos)


def main(argumentos=None, leer_respuesta=input) -> None:
    opciones = leer_argumentos(argumentos)
    exigir_solr()
    print("Estado actual de 'ri':", json.dumps(estado_actual(), ensure_ascii=False, indent=2))
    print("Cambios previstos:", json.dumps(describir_cambios(), ensure_ascii=False, indent=2))
    if not opciones.aplicar:
        print("\nModo de prueba: no se envió nada. Use --aplicar para ejecutar.")
        return
    if not confirmado(leer_respuesta):
        print("Cancelado: no se modificó 'ri'.")
        return
    aplicar()


if __name__ == "__main__":
    main()
