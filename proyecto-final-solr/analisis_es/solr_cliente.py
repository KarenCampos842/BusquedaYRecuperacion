"""Cliente HTTP mínimo para Solr (solo biblioteca estándar, como el kit)."""

import json
import subprocess
import urllib.error
import urllib.parse
import urllib.request

from configuracion import (
    CONJUNTO_CONFIGURACION_PRUEBA,
    CONTENEDOR_SOLR,
    CORE_PRODUCCION,
    TIEMPO_ESPERA_SEGUNDOS,
    URL_SOLR,
)

TIPO_JSON = "application/json"
MARCAS_YA_EXISTE = ("already exists", "duplicate")


class ErrorSolr(RuntimeError):
    def __init__(self, estado: int, mensaje: str):
        super().__init__(f"Solr respondió {estado}: {mensaje}")
        self.estado = estado
        self.mensaje = mensaje

    @property
    def es_ya_existe(self) -> bool:
        return any(marca in self.mensaje.lower() for marca in MARCAS_YA_EXISTE)


def url_core(core: str, ruta: str, parametros: dict | None = None) -> str:
    consulta = urllib.parse.urlencode({**(parametros or {}), "wt": "json"}, doseq=True)
    return f"{URL_SOLR}/{core}/{ruta.lstrip('/')}?{consulta}"


def solicitar(metodo: str, url: str, cuerpo=None) -> dict:
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    peticion = urllib.request.Request(
        url, data=datos, method=metodo, headers={"Content-Type": TIPO_JSON}
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_ESPERA_SEGUNDOS) as respuesta:
            return json.loads(respuesta.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raise ErrorSolr(error.code, error.read().decode("utf-8", "replace")) from error


def obtener(core: str, ruta: str, parametros: dict | None = None) -> dict:
    return solicitar("GET", url_core(core, ruta, parametros))


def enviar(core: str, ruta: str, cuerpo, metodo: str = "POST", parametros: dict | None = None) -> dict:
    return solicitar(metodo, url_core(core, ruta, parametros), cuerpo)


def solr_disponible() -> bool:
    try:
        solicitar("GET", f"{URL_SOLR}/admin/info/system?wt=json")
        return True
    except (OSError, ErrorSolr):
        return False


def exigir_solr() -> None:
    """Termina con un mensaje claro si Solr no responde."""
    if not solr_disponible():
        raise SystemExit(
            f"Solr no responde en {URL_SOLR}. Abra Docker Desktop y ejecute, desde "
            "proyecto-final-solr/kit/01_instalacion:  docker compose up -d"
        )


def core_existe(core: str) -> bool:
    estado = solicitar("GET", f"{URL_SOLR}/admin/cores?action=STATUS&core={core}&wt=json")
    return bool(estado.get("status", {}).get(core))


def recargar_core(core: str) -> None:
    solicitar("GET", f"{URL_SOLR}/admin/cores?action=RELOAD&core={core}&wt=json")


def crear_core_de_prueba(core: str) -> None:
    """Crea un core con copia propia del configset _default dentro del contenedor.

    Se usa `solr create` (y no CoreAdmin CREATE) porque copia el configset;
    así los cambios de esquema no alteran _default ni el core `ri`.
    """
    if core == CORE_PRODUCCION:
        raise ValueError("El core de producción no se crea desde estos scripts.")
    comando = [
        "docker", "exec", CONTENEDOR_SOLR,
        "solr", "create", "-c", core, "-d", CONJUNTO_CONFIGURACION_PRUEBA,
    ]
    subprocess.run(comando, check=True)


def asegurar_core_de_prueba(core: str) -> None:
    if not core_existe(core):
        crear_core_de_prueba(core)
