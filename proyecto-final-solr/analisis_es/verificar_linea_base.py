"""P01-04 y P03-01 · Verifica text_es_ri y registra cómo trata acentos y mayúsculas.

Uso (desde proyecto-final-solr/):
    py analisis_es/verificar_linea_base.py

1. Consulta (solo lectura) si text_es_ri existe en `ri` y si es idéntico al kit.
   No ejecuta kit/.../configurar_esquema.py: crearía `titulo` y `contenido`
   con text_es_ri, contra el contrato P00-03 (deben usar text_es_proyecto).
2. Analiza los pares de P03-01 con text_es_ri en el core de prueba y guarda
   los tokens en analisis_es/resultados/linea_base_text_es_ri.json.
"""

import json

from analisis_tokens import analizar_por_etapas
from configuracion import CORE_PRODUCCION, CORE_PRUEBA, DIRECTORIO_RESULTADOS, TIPO_CONTROL
from configurar_analizadores import asegurar_tipo_control
from definiciones_tipos import leer_text_es_ri_del_kit
from solr_cliente import ErrorSolr, asegurar_core_de_prueba, core_existe, exigir_solr, obtener

TEXTOS_P03_01 = ("BÚSQUEDA de Información", "busqueda de informacion")
RUTA_RESULTADO = DIRECTORIO_RESULTADOS / "linea_base_text_es_ri.json"
CLAVES_ANALIZADOR = ("indexAnalyzer", "queryAnalyzer")

ESTADO_SIN_CORE = f"el core '{CORE_PRODUCCION}' no existe"
ESTADO_AUSENTE = "ausente (se crea solo el tipo con aplicar_en_ri.py)"
ESTADO_IDENTICO = "presente e idéntico al kit"
ESTADO_DISTINTO = "presente pero DISTINTO al kit"


def firma_analizador(analizador: dict) -> list:
    """Representación comparable: clase y atributos de tokenizador y filtros."""
    partes = [analizador["tokenizer"], *analizador.get("filters", [])]
    return [sorted((clave, str(valor)) for clave, valor in parte.items()) for parte in partes]


def estado_tipo_en_produccion() -> str:
    if not core_existe(CORE_PRODUCCION):
        return ESTADO_SIN_CORE
    try:
        actual = obtener(CORE_PRODUCCION, f"schema/fieldtypes/{TIPO_CONTROL}")["fieldType"]
    except ErrorSolr as error:
        if error.estado == 404:
            return ESTADO_AUSENTE
        raise
    kit = leer_text_es_ri_del_kit()
    iguales = all(firma_analizador(actual[c]) == firma_analizador(kit[c]) for c in CLAVES_ANALIZADOR)
    return ESTADO_IDENTICO if iguales else ESTADO_DISTINTO


def analizar_pares() -> dict:
    asegurar_core_de_prueba(CORE_PRUEBA)
    asegurar_tipo_control(CORE_PRUEBA)
    return {texto: analizar_por_etapas(CORE_PRUEBA, TIPO_CONTROL, texto) for texto in TEXTOS_P03_01}


def imprimir_etapas(analisis: dict) -> None:
    for texto, etapas in analisis.items():
        print(f"\n«{texto}»")
        for etapa in etapas:
            print(f"  {etapa['etapa']:<28} {etapa['tokens']}")


def main() -> None:
    exigir_solr()
    estado = estado_tipo_en_produccion()
    print(f"{TIPO_CONTROL} en '{CORE_PRODUCCION}': {estado}")
    analisis = analizar_pares()
    imprimir_etapas(analisis)
    DIRECTORIO_RESULTADOS.mkdir(exist_ok=True)
    RUTA_RESULTADO.write_text(
        json.dumps({"estado_en_ri": estado, "analisis": analisis}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nGuardado en {RUTA_RESULTADO}")


if __name__ == "__main__":
    main()
