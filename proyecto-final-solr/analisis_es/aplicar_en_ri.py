"""Aplica los tipos de español al core `ri`, con modo de prueba y confirmación.

Uso (desde proyecto-final-solr/):
    py analisis_es/aplicar_en_ri.py            # modo de prueba: solo muestra qué haría
    py analisis_es/aplicar_en_ri.py --aplicar  # pide escribir "ri" para confirmar

Qué hace al aplicar, en este orden:
1. text_es_ri (P01-04): si falta, crea SOLO el tipo con la definición leída de
   kit/.../configurar_esquema.py (sin ejecutar ese script, que además crearía
   campos). Si ya existe, comprueba que sea idéntico al kit y no lo toca; si es
   distinto, se detiene sin cambiar nada.
2. text_es_proyecto: lo agrega (o reemplaza) y sincroniza los recursos
   gestionados `es_proyecto` (stopwords y sinónimos); después recarga `ri`.
3. Comprueba que text_es_ri quedó idéntico al kit.

NO crea ni cambia campos (titulo, contenido, tema, vector...) ni documentos:
solo tipos de campo y recursos. Asignar text_es_proyecto a titulo/contenido
e indexar lo hace Joseph.
"""

import argparse
import json

from configuracion import CORE_PRODUCCION, RECURSO_GESTIONADO, TIPO_CONTROL
from configurar_analizadores import asegurar_tipo_control, configurar_tipos
from definiciones_tipos import TIPO_PROYECTO, definir_text_es_proyecto, leer_text_es_ri_del_kit
from recursos_linguisticos import leer_grupos_sinonimos, leer_stopwords
from solr_cliente import ErrorSolr, exigir_solr, obtener
from verificar_linea_base import (
    ESTADO_AUSENTE,
    ESTADO_DISTINTO,
    ESTADO_IDENTICO,
    ESTADO_SIN_CORE,
    estado_tipo_en_produccion,
)

TEXTO_CONFIRMACION = CORE_PRODUCCION
ESTADOS_QUE_BLOQUEAN = {
    ESTADO_SIN_CORE: f"El core '{CORE_PRODUCCION}' no existe.",
    ESTADO_DISTINTO: f"{TIPO_CONTROL} existe pero no coincide con el kit; no se toca nada.",
}


def accion_sobre_control(estado_control: str) -> str:
    if estado_control == ESTADO_AUSENTE:
        return "se crea desde el kit (solo el tipo)"
    if estado_control == ESTADO_IDENTICO:
        return "sin cambios (ya es idéntico al kit)"
    return "bloquea la aplicación"


def describir_cambios(estado_control: str) -> dict:
    """Lo que se enviaría a `ri` (sin red): útil para revisar antes de aplicar."""
    cambios = {
        "core": CORE_PRODUCCION,
        TIPO_CONTROL: accion_sobre_control(estado_control),
        TIPO_PROYECTO: definir_text_es_proyecto(),
        "recurso_gestionado": RECURSO_GESTIONADO,
        "stopwords": len(leer_stopwords()),
        "grupos_sinonimos": len(leer_grupos_sinonimos()),
        "no_se_modifica": ["campos", "documentos"],
    }
    if estado_control == ESTADO_AUSENTE:
        cambios["definicion_" + TIPO_CONTROL] = leer_text_es_ri_del_kit()
    return cambios


def tipo_existe(core: str, tipo: str) -> bool:
    try:
        obtener(core, f"schema/fieldtypes/{tipo}")
        return True
    except ErrorSolr as error:
        if error.estado == 404:
            return False
        raise


def estado_actual(estado_control: str) -> dict:
    estado = {TIPO_CONTROL: estado_control}
    if estado_control != ESTADO_SIN_CORE:
        existe = tipo_existe(CORE_PRODUCCION, TIPO_PROYECTO)
        estado[TIPO_PROYECTO] = "existe (se reemplazaría)" if existe else "no existe (se crearía)"
    return estado


def confirmado(leer_respuesta=input) -> bool:
    respuesta = leer_respuesta(f'Escriba "{TEXTO_CONFIRMACION}" para aplicar los cambios en el core {CORE_PRODUCCION}: ')
    return respuesta.strip() == TEXTO_CONFIRMACION


def exigir_control_identico(momento: str) -> None:
    estado = estado_tipo_en_produccion()
    if estado != ESTADO_IDENTICO:
        raise SystemExit(f"ALERTA ({momento}): {TIPO_CONTROL} quedó '{estado}'. Revisar antes de continuar.")


def aplicar() -> None:
    """Vuelve a leer el estado (no confía en el modo de prueba) y aplica en orden."""
    estado_control = estado_tipo_en_produccion()
    if estado_control in ESTADOS_QUE_BLOQUEAN:
        raise SystemExit(ESTADOS_QUE_BLOQUEAN[estado_control])
    if estado_control == ESTADO_AUSENTE:
        print(f"{TIPO_CONTROL}: {asegurar_tipo_control(CORE_PRODUCCION)}")
        exigir_control_identico("tras crear el control")
    configurar_tipos(CORE_PRODUCCION, [TIPO_PROYECTO])
    exigir_control_identico("tras configurar text_es_proyecto")
    print(f"Listo. {TIPO_CONTROL}: {ESTADO_IDENTICO}; {TIPO_PROYECTO} configurado.")


def leer_argumentos(argumentos=None) -> argparse.Namespace:
    lector = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    lector.add_argument("--aplicar", action="store_true", help="aplica los cambios tras confirmar")
    return lector.parse_args(argumentos)


def main(argumentos=None, leer_respuesta=input) -> None:
    opciones = leer_argumentos(argumentos)
    exigir_solr()
    estado_control = estado_tipo_en_produccion()
    print("Estado actual de 'ri':", json.dumps(estado_actual(estado_control), ensure_ascii=False, indent=2))
    print("Cambios previstos:", json.dumps(describir_cambios(estado_control), ensure_ascii=False, indent=2))
    if estado_control in ESTADOS_QUE_BLOQUEAN:
        print("\nNo se puede aplicar:", ESTADOS_QUE_BLOQUEAN[estado_control])
        return
    if not opciones.aplicar:
        print("\nModo de prueba: no se envió nada. Use --aplicar para ejecutar.")
        return
    if not confirmado(leer_respuesta):
        print("Cancelado: no se modificó 'ri'.")
        return
    aplicar()


if __name__ == "__main__":
    main()
