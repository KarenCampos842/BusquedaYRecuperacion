"""P05-03 y P05-06 · Configura Suggester y SpellCheck con sus campos y copyField.

Uso (desde proyecto-final-solr/):
    py analisis_es/configurar_sugerencias_ortografia.py                       # core de prueba ri_sugerencias_es
    py analisis_es/configurar_sugerencias_ortografia.py --reemplazar          # solo core de prueba
    py analisis_es/configurar_sugerencias_ortografia.py --core ri             # modo de prueba: solo muestra
    py analisis_es/configurar_sugerencias_ortografia.py --core ri --aplicar   # pide escribir "ri"

Funciona en dos fases:
1. Revisión (solo lectura) de los tipos text_sugerencia_es, text_ortografia_es y
   text_vocabulario_es, de los campos titulo_sugerencia, contenido_ortografia y
   contenido_vocabulario y de las tres reglas copyField autorizadas (también su
   maxChars). Cada elemento queda como "falta", "compatible" o "incompatible".
2. Escritura: si hay algo incompatible, se detiene SIN enviar nada. Si no, crea
   solo lo que falta y deja intacto lo compatible. Después agrega o actualiza los
   componentes sugerencias_es y ortografia_es y los handlers /sugerencias y
   /ortografia (Config API). No toca `spellcheck` ni `/spell` del configset.
NO crea ni modifica titulo ni contenido: deben existir.
--reemplazar (solo core de prueba, nunca en `ri`) reemplaza lo incompatible.
En `ri` se ejecuta en la máquina del Solr de destino y solo con confirmación.
"""

import argparse
import json
from dataclasses import dataclass, field

from aplicar_en_ri import confirmado
from configuracion import CORE_PRODUCCION, CORE_SUGERENCIAS
from definiciones_sugerencias import (
    CAMPO_CONTENIDO,
    CAMPO_TITULO,
    CAMPOS_AUXILIARES,
    CONFIGURACION_SOLRCONFIG,
    COPIAS,
    DEFINIDORES_TIPOS_SUGERENCIAS,
    MAX_CHARS_ILIMITADO,
)
from solr_cliente import ErrorSolr, enviar, exigir_solr, obtener
from verificar_linea_base import CLAVES_ANALIZADOR, firma_analizador

CAMPOS_REQUERIDOS = (CAMPO_TITULO, CAMPO_CONTENIDO)
PROPIEDADES_BOOLEANAS = {"stored", "indexed", "required", "multiValued", "docValues"}
PROPIEDADES_COPIA = {"source", "dest", "maxChars"}
DESTINOS_AUXILIARES = {copia["dest"] for copia in COPIAS}

FALTA = "falta"
COMPATIBLE = "compatible"


@dataclass
class RevisionEsquema:
    """Resultado de la fase de solo lectura."""
    tipos_a_crear: list = field(default_factory=list)
    campos_a_crear: list = field(default_factory=list)
    copias_a_crear: list = field(default_factory=list)
    compatibles: list = field(default_factory=list)
    incompatibles: list = field(default_factory=list)
    # (entidad, definición) que --reemplazar sustituiría en el core de prueba;
    # para copyField la definición es (regla existente, regla autorizada).
    reemplazables: list = field(default_factory=list)
    # Duplicados y reglas no autorizadas: detienen siempre, también con --reemplazar.
    irreparables: list = field(default_factory=list)


# ---------- Lectura ----------

def leer_o_none(core: str, ruta: str, clave: str, parametros: dict | None = None):
    try:
        return obtener(core, ruta, parametros)[clave]
    except ErrorSolr as error:
        if error.estado == 404:
            return None
        raise


def campo_existe(core: str, campo: str) -> bool:
    return leer_o_none(core, f"schema/fields/{campo}", "field") is not None


def exigir_campos_origen(core: str) -> None:
    faltantes = [campo for campo in CAMPOS_REQUERIDOS if not campo_existe(core, campo)]
    if faltantes:
        raise SystemExit(f"En '{core}' faltan {faltantes}: los define Joseph antes de crear los copyField.")


# ---------- Comparaciones (sin red) ----------

def normalizar_valor(propiedad: str, valor):
    """Solr puede omitir booleanos falsos o devolverlos como texto."""
    if propiedad in PROPIEDADES_BOOLEANAS:
        return str(valor).lower() == "true" if valor is not None else False
    return valor


def diferencias_tipo(esperado: dict, actual: dict) -> list[str]:
    nombre = esperado["name"]
    if actual.get("class") != esperado["class"]:
        return [f"tipo {nombre}: class {actual.get('class')!r} != {esperado['class']!r}"]
    return [
        f"tipo {nombre}: {clave} distinto del esperado"
        for clave in CLAVES_ANALIZADOR
        if clave not in actual or firma_analizador(actual[clave]) != firma_analizador(esperado[clave])
    ]


def diferencias_campo(esperado: dict, actual: dict) -> list[str]:
    nombre = esperado["name"]
    diferencias = [
        f"campo {nombre}.{propiedad}: {actual.get(propiedad)!r} != {valor!r}"
        for propiedad, valor in esperado.items()
        if normalizar_valor(propiedad, actual.get(propiedad)) != normalizar_valor(propiedad, valor)
    ]
    if "default" in actual:
        diferencias.append(f"campo {nombre}: tiene default {actual['default']!r} inesperado")
    return diferencias


def diferencias_copia(copia: dict) -> list[str]:
    """Compatible solo sin propiedades extra y con maxChars ausente o el entero 0."""
    regla = f"copyField {copia.get('source')}->{copia.get('dest')}"
    diferencias = []
    extra = set(copia) - PROPIEDADES_COPIA
    if extra:
        diferencias.append(f"{regla}: propiedades inesperadas {sorted(extra)}")
    if "maxChars" in copia:
        valor = copia["maxChars"]
        if type(valor) is not int or valor != MAX_CHARS_ILIMITADO:
            diferencias.append(f"{regla}: se esperaba sin límite y tiene maxChars={valor!r}")
    return diferencias


def marcar_irreparable(revision: RevisionEsquema, mensaje: str) -> None:
    revision.incompatibles.append(mensaje)
    revision.irreparables.append(mensaje)


def revisar_copias(existentes: list[dict], revision: RevisionEsquema) -> None:
    autorizadas = {(c["source"], c["dest"]): c for c in COPIAS}
    vistas = set()
    for copia in existentes:
        par = (copia.get("source"), copia.get("dest"))
        if par in autorizadas:
            if par in vistas:
                marcar_irreparable(revision, f"copyField {par[0]}->{par[1]}: regla duplicada")
                continue
            vistas.add(par)
            diferencias = diferencias_copia(copia)
            revision.incompatibles.extend(diferencias)
            if diferencias:
                revision.reemplazables.append(("copy-field", (copia, autorizadas[par])))
            else:
                revision.compatibles.append(f"copyField {par[0]}->{par[1]}")
        elif par[1] in DESTINOS_AUXILIARES:
            marcar_irreparable(revision, f"copyField {par[0]}->{par[1]}: regla no autorizada hacia un campo auxiliar")
    revision.copias_a_crear = [c for par, c in autorizadas.items() if par not in vistas]


# ---------- Revisión (solo lectura) ----------

def revisar_esquema(core: str) -> RevisionEsquema:
    revision = RevisionEsquema()
    for definir in DEFINIDORES_TIPOS_SUGERENCIAS.values():
        esperado = definir()
        actual = leer_o_none(core, f"schema/fieldtypes/{esperado['name']}", "fieldType")
        registrar(revision, "field-type", esperado, actual, diferencias_tipo, revision.tipos_a_crear)
    for esperado in CAMPOS_AUXILIARES:
        actual = leer_o_none(core, f"schema/fields/{esperado['name']}", "field", {"showDefaults": "true"})
        registrar(revision, "field", esperado, actual, diferencias_campo, revision.campos_a_crear)
    revisar_copias(obtener(core, "schema/copyfields")["copyFields"], revision)
    return revision


def registrar(revision, entidad, esperado, actual, comparar, faltantes) -> None:
    if actual is None:
        faltantes.append(esperado)
        return
    diferencias = comparar(esperado, actual)
    if diferencias:
        revision.incompatibles.extend(diferencias)
        revision.reemplazables.append((entidad, esperado))
    else:
        revision.compatibles.append(f"{entidad} {esperado['name']}")


# ---------- Escritura ----------

def agregar_o_actualizar_config(core: str, comando: str, definicion: dict) -> str:
    """Config API: add-<comando>; si ya existe, update-<comando>. Solo nombres propios."""
    try:
        enviar(core, "config", {f"add-{comando}": definicion})
        return "creado"
    except ErrorSolr as error:
        if not error.es_ya_existe:
            raise
    enviar(core, "config", {f"update-{comando}": definicion})
    return "actualizado"


def reemplazar_incompatibles(core: str, revision: RevisionEsquema) -> None:
    for entidad, definicion in revision.reemplazables:
        if entidad == "copy-field":
            existente, autorizada = definicion
            enviar(core, "schema", {"delete-copy-field": {"source": existente["source"], "dest": existente["dest"]}})
            enviar(core, "schema", {"add-copy-field": autorizada})
            print(f"  copyField {autorizada['source']}->{autorizada['dest']}: reemplazado (sin límite)")
        else:
            enviar(core, "schema", {f"replace-{entidad}": definicion})
            print(f"  {entidad} {definicion['name']}: reemplazado")


def crear_faltantes(core: str, revision: RevisionEsquema) -> None:
    for definicion in revision.tipos_a_crear:
        enviar(core, "schema", {"add-field-type": definicion})
        print(f"  field-type {definicion['name']}: creado")
    for definicion in revision.campos_a_crear:
        enviar(core, "schema", {"add-field": definicion})
        print(f"  field {definicion['name']}: creado")
    for copia in revision.copias_a_crear:
        enviar(core, "schema", {"add-copy-field": copia})
        print(f"  copyField {copia['source']}->{copia['dest']}: creado")


def configurar(core: str, reemplazar: bool = False) -> None:
    if reemplazar and core == CORE_PRODUCCION:
        raise ValueError(f"--reemplazar no se permite en '{CORE_PRODUCCION}'.")
    exigir_campos_origen(core)
    revision = revisar_esquema(core)
    bloqueantes = revision.irreparables if reemplazar else revision.incompatibles
    if bloqueantes:
        raise SystemExit(f"Esquema incompatible en '{core}'; no se envió nada:\n  - " + "\n  - ".join(bloqueantes))
    for elemento in revision.compatibles:
        print(f"  {elemento}: compatible, sin cambios")
    if reemplazar:
        reemplazar_incompatibles(core, revision)
    crear_faltantes(core, revision)
    for comando, definicion in CONFIGURACION_SOLRCONFIG:
        print(f"  {comando} {definicion['name']}: {agregar_o_actualizar_config(core, comando, definicion)}")


# ---------- Línea de comandos ----------

def describir_cambios(core: str) -> dict:
    """Modo de prueba: la revisión es de solo lectura."""
    revision = revisar_esquema(core)
    return {
        "core": core,
        "se_crearian": {
            "tipos": [t["name"] for t in revision.tipos_a_crear],
            "campos": [c["name"] for c in revision.campos_a_crear],
            "copyField": [f"{c['source']}->{c['dest']}" for c in revision.copias_a_crear],
        },
        "compatibles_sin_cambios": revision.compatibles,
        "incompatibles_detienen_--aplicar": revision.incompatibles,
        "solrconfig (Config API)": [definicion["name"] for _, definicion in CONFIGURACION_SOLRCONFIG],
        "no_se_modifica": [CAMPO_TITULO, CAMPO_CONTENIDO, "documentos", "spellcheck", "/spell"],
    }


def leer_argumentos(argumentos=None) -> argparse.Namespace:
    lector = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    lector.add_argument("--core", default=CORE_SUGERENCIAS, help=f"core destino (por defecto {CORE_SUGERENCIAS})")
    lector.add_argument("--aplicar", action="store_true", help=f"obligatorio para aplicar en '{CORE_PRODUCCION}'")
    lector.add_argument("--reemplazar", action="store_true",
                        help=f"reemplaza lo incompatible; solo core de prueba, nunca '{CORE_PRODUCCION}'")
    opciones = lector.parse_args(argumentos)
    if opciones.reemplazar and opciones.core == CORE_PRODUCCION:
        lector.error(f"--reemplazar no se permite con --core {CORE_PRODUCCION}")
    return opciones


def main(argumentos=None, leer_respuesta=input) -> None:
    opciones = leer_argumentos(argumentos)
    exigir_solr()
    if opciones.core == CORE_PRODUCCION:
        exigir_campos_origen(opciones.core)
        print("Cambios previstos:", json.dumps(describir_cambios(opciones.core), ensure_ascii=False, indent=2))
        if not opciones.aplicar:
            print("\nModo de prueba: no se envió nada. Use --aplicar para ejecutar.")
            return
        if not confirmado(leer_respuesta):
            print(f"Cancelado: no se modificó '{CORE_PRODUCCION}'.")
            return
    print(f"Core '{opciones.core}':")
    configurar(opciones.core, reemplazar=opciones.reemplazar)


if __name__ == "__main__":
    main()
