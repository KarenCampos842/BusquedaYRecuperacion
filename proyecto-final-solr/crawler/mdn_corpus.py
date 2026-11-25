"""Rastreo limitado con cuotas, reutilización local y prioridad de artículos."""

import argparse
import hashlib
import json
import math
import re
from collections import Counter, deque
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from mdn_piloto import (
    DATA, PAUSA, ROBOTS_URL, USER_AGENT, Cliente, PilotoError, RastreoDetenido,
    descargar_articulo, extraer, interpretar_robots, normalizar_url,
    validar_url,
    filtrar_enlaces,
    crear_ejecucion, guardar_nuevo,
    clasificar_documento,
)

CATEGORIAS = ("JavaScript", "HTML", "CSS")
SEMILLAS = tuple(f"https://developer.mozilla.org/es/docs/Web/{cat}" for cat in CATEGORIAS)
CUOTAS = {cat: 20 for cat in CATEGORIAS}
CORPUS_VALIDADO = DATA / "corpus_piloto_v2.json"


def huella(documento):
    """SHA-256 exacto del campo contenido codificado en UTF-8."""
    return hashlib.sha256(documento["contenido"].encode("utf-8")).hexdigest()


def huella_normalizada(documento):
    """Clave de deduplicación: compactar espacios, strip y casefold."""
    texto = re.sub(r"\s+", " ", documento["contenido"]).strip().casefold()
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


class Unicos:
    def __init__(self):
        self.urls = set()
        self.huellas = set()

    def aceptar(self, documento):
        url = normalizar_url(documento["url"])
        digest = huella_normalizada(documento)
        if url in self.urls or digest in self.huellas:
            return False
        self.urls.add(url)
        self.huellas.add(digest)
        documento["sha256_contenido"] = huella(documento)
        documento["sha256_contenido_normalizado"] = digest
        return True


class LimiteSolicitudes(PilotoError):
    pass


class ClienteLimitado:
    """El presupuesto incluye robots y cada salto de redirección."""

    def __init__(self, cliente, limite, reporte):
        self.cliente, self.limite, self.usadas = cliente, limite, 0
        self.reporte = reporte

    @property
    def intervalo(self):
        return self.cliente.intervalo

    @intervalo.setter
    def intervalo(self, valor):
        self.cliente.intervalo = valor

    def obtener(self, url):
        if self.usadas >= self.limite:
            raise LimiteSolicitudes("límite global de solicitudes alcanzado")
        self.usadas += 1
        return self.cliente.obtener(url)


def cargar_validados(path):
    """Comprobar integridad local; no corregir ni volver a fechar documentos."""
    raw = Path(path).read_bytes()
    documentos = json.loads(raw)
    if not isinstance(documentos, list):
        raise PilotoError("El corpus validado debe ser una lista JSON")
    urls, hashes = set(), set()
    for doc in documentos:
        if not isinstance(doc, dict) or not all(k in doc for k in (
            "id", "url", "titulo", "contenido", "categoria", "idioma", "fuente",
            "tipo_fuente", "tipo_documento", "profundidad", "fecha_rastreo",
            "sha256_contenido", "sha256_contenido_normalizado", "enlaces_salientes",
        )):
            raise PilotoError("Documento validado con esquema incompleto")
        url = normalizar_url(doc["url"])
        if (doc["categoria"] != validar_url(url) or doc["tipo_documento"] not in
                {"indice", "articulo_explicativo"} or not isinstance(doc["contenido"], str)
                or len(doc["contenido"]) < 100 or not isinstance(doc["idioma"], str)
                or doc["idioma"].lower().split("-")[0] != "es"
                or not isinstance(doc["enlaces_salientes"], list)):
            raise PilotoError(f"Documento validado no admisible: {url}")
        if doc["sha256_contenido"] != huella(doc) or doc["sha256_contenido_normalizado"] != huella_normalizada(doc):
            raise PilotoError(f"Integridad incorrecta en corpus validado: {url}")
        if url in urls or huella_normalizada(doc) in hashes:
            raise PilotoError(f"Duplicado en corpus validado: {url}")
        urls.add(url)
        hashes.add(huella_normalizada(doc))
    return documentos, {"archivo": str(Path(path).resolve()),
                        "sha256_archivo": hashlib.sha256(raw).hexdigest(), "documentos": len(documentos)}


def ejecutar(pausa=PAUSA, max_solicitudes=180, max_profundidad=4, cliente_factory=Cliente,
             *, cuotas=None, max_indices_por_categoria=2, corpus_previo=CORPUS_VALIDADO):
    cuotas = dict(CUOTAS if cuotas is None else cuotas)
    if (set(cuotas) != set(CATEGORIAS) or any(type(v) is not int or v < 0 for v in cuotas.values())
            or sum(cuotas.values()) == 0 or type(max_indices_por_categoria) is not int
            or max_indices_por_categoria < 0 or not math.isfinite(pausa) or pausa < 3
            or type(max_solicitudes) is not int or max_solicitudes < 1
            or type(max_profundidad) is not int or max_profundidad < 0):
        raise ValueError("Cuotas enteras >= 0 (total > 0), índices >= 0, pausa >= 3, solicitudes >= 1 y profundidad >= 0")
    objetivo = sum(cuotas.values())
    reporte = {
        "fecha_inicio": datetime.now(timezone.utc).isoformat(), "user_agent": USER_AGENT,
        "semillas": list(SEMILLAS), "solicitudes": [], "visitadas": [],
        "descubiertas": [], "aceptadas": [], "rechazadas": [], "errores": [],
        "reutilizados": [], "solo_descubrimiento": [], "indices_no_incorporados": [],
        "robots_verificado": False, "objetivo_documentos": objetivo,
        "limites": {"por_categoria": cuotas, "max_solicitudes": max_solicitudes,
                    "max_profundidad": max_profundidad, "max_indices_por_categoria": max_indices_por_categoria},
        "profundidad_relativa_a": "raíces y documentos locales validados (nivel cero de esta ejecución)",
    }
    documentos, conteo, indices = [], Counter(), Counter()
    solicitadas, encoladas = set(), set()
    articulos, portadas, pendientes = deque(), deque(), []
    unicos = Unicos()

    def completo():
        return all(conteo[c] >= cuotas[c] for c in CATEGORIAS)

    def encolar(url, profundidad, origen):
        if profundidad > max_profundidad or url in encoladas:
            return
        encoladas.add(url)
        cola = portadas if clasificar_documento(url) == "indice" else articulos
        cola.append((url, profundidad, origen))
        if origen:
            reporte["descubiertas"].append({"url": url, "desde": origen, "profundidad": profundidad})

    def descubrir(doc, profundidad):
        if profundidad < max_profundidad:
            for enlace in filtrar_enlaces(doc["enlaces_salientes"], doc["url"]):
                encolar(enlace, profundidad + 1, doc["url"])

    def incorporar(doc, reutilizado=False):
        cat = doc["categoria"]
        if conteo[cat] >= cuotas[cat] or (doc["tipo_documento"] == "indice" and indices[cat] >= max_indices_por_categoria):
            return False
        if not unicos.aceptar(doc):
            return False
        documentos.append(doc)
        conteo[cat] += 1
        indices[cat] += doc["tipo_documento"] == "indice"
        entrada = {"url": doc["url"], "categoria": cat, "tipo_documento": doc["tipo_documento"],
                   "titulo": doc["titulo"], "caracteres": len(doc["contenido"]), "reutilizado": reutilizado}
        reporte["aceptadas"].append(entrada)
        if reutilizado:
            reporte["reutilizados"].append(entrada.copy())
        print(f"{'REUTILIZADO' if reutilizado else 'ACEPTADO'} {len(documentos)}/{objetivo} "
              f"[{cat} {conteo[cat]}/{cuotas[cat]}] {doc['titulo']} — {doc['url']}", flush=True)
        return True

    try:
        previos = []
        if corpus_previo is not None:
            previos, reporte["corpus_origen"] = cargar_validados(corpus_previo)
        # Todos los validados evitan redescargas, aunque una cuota o el cupo
        # de índices los deje fuera del nuevo corpus. Se usan sus enlaces.
        solicitadas.update(normalizar_url(d["url"]) for d in previos)
        encoladas.update(solicitadas)
        for doc in sorted(previos, key=lambda d: d["tipo_documento"] == "indice"):
            copia = deepcopy(doc)
            if not incorporar(copia, reutilizado=True):
                reporte["solo_descubrimiento"].append({"url": doc["url"], "motivo": "cuota o límite de índices"})
            descubrir(doc, 0)
        for url in SEMILLAS:
            encolar(url, 0, None)
        if completo():
            reporte["motivo_fin"] = "cuotas cubiertas con documentos validados; sin acceso a red"
        else:
            cliente = ClienteLimitado(cliente_factory(reporte), max_solicitudes, reporte)
            cliente.intervalo = pausa
            # Cualquier fallo aquí aborta todo el rastreo, nunca implica permiso.
            body, headers = cliente.obtener(ROBOTS_URL)
            if body is None or headers.get_content_type() != "text/plain":
                raise RastreoDetenido("robots.txt no verificable: redirección o tipo inesperado")
            robots = interpretar_robots(body.decode("utf-8-sig", errors="strict"))
            delay = robots.crawl_delay(USER_AGENT)
            rate = robots.request_rate(USER_AGENT)
            cliente.intervalo = max(pausa, delay or 0, rate.seconds if rate else 0)
            reporte["robots_verificado"] = True
            reporte["intervalo_segundos"] = cliente.intervalo
        while (articulos or portadas) and not completo():
            cola = articulos if articulos else portadas
            url, profundidad, origen = cola.popleft()
            categoria = validar_url(url)
            if conteo[categoria] >= cuotas[categoria] or url in solicitadas:
                continue
            reporte["visitadas"].append({"url": url, "profundidad": profundidad, "descubierta_desde": origen})
            try:
                final, html, charset = descargar_articulo(cliente, robots, url, solicitadas)
                doc = extraer(final, html, charset)
                doc["profundidad"] = profundidad
                doc["descubierta_desde"] = origen
                descubrir(doc, profundidad)
                if doc["tipo_documento"] == "indice":
                    # Solo rellenar con índices al terminar de buscar artículos.
                    pendientes.append(doc)
                elif not incorporar(doc):
                    reporte["rechazadas"].append({"url": final, "motivo": "cuota cubierta o duplicado"})
            except (RastreoDetenido, LimiteSolicitudes):
                raise
            except (PilotoError, UnicodeError, ValueError) as exc:
                if not reporte["rechazadas"] or reporte["rechazadas"][-1]["url"] != url:
                    reporte["rechazadas"].append({"url": url, "motivo": str(exc)})
                if "Error de red" in str(exc) or "HTTP " in str(exc):
                    reporte["errores"].append({"url": url, "motivo": str(exc)})
                print(f"RECHAZADO {url}: {exc}", flush=True)
        reporte.setdefault("motivo_fin", "cuotas cubiertas" if completo() else "cola agotada o profundidad máxima")
    except LimiteSolicitudes as exc:
        reporte["motivo_fin"] = str(exc)
    except (PilotoError, UnicodeError, ValueError, OSError, TypeError, KeyError) as exc:
        reporte["resultado"] = "detenido"
        reporte["motivo_fin"] = str(exc)
        reporte["errores"].append({"motivo": str(exc)})
        print(f"DETENIDO: {exc}", flush=True)
    for doc in pendientes:
        if not incorporar(doc):
            reporte["indices_no_incorporados"].append({"url": doc["url"], "motivo": "cuota, límite de índices o duplicado"})
    if reporte.get("resultado") != "detenido":
        reporte["resultado"] = "completo" if completo() else "parcial"
    reporte["indices_por_categoria"] = {cat: indices[cat] for cat in CATEGORIAS}
    reporte["conteo_por_categoria"] = {cat: conteo[cat] for cat in CATEGORIAS}
    reporte["faltantes_por_categoria"] = {cat: cuotas[cat] - conteo[cat] for cat in CATEGORIAS}
    reporte["total_reutilizados"] = len(reporte["reutilizados"])
    reporte["total_nuevos"] = len(documentos) - reporte["total_reutilizados"]
    reporte["total_documentos"] = len(documentos)
    reporte["fecha_fin"] = datetime.now(timezone.utc).isoformat()
    return documentos, reporte


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pausa", type=float, default=PAUSA)
    parser.add_argument("--max-solicitudes", type=int, default=180)
    parser.add_argument("--max-profundidad", type=int, default=4)
    parser.add_argument("--cuota-javascript", type=int, default=20)
    parser.add_argument("--cuota-html", type=int, default=20)
    parser.add_argument("--cuota-css", type=int, default=20)
    parser.add_argument("--max-indices-por-categoria", type=int, default=2)
    parser.add_argument("--corpus-previo", type=Path, default=CORPUS_VALIDADO)
    args = parser.parse_args()
    cuotas = dict(zip(CATEGORIAS, (args.cuota_javascript, args.cuota_html, args.cuota_css)))
    if (not math.isfinite(args.pausa) or args.pausa < 3 or args.max_solicitudes < 1
            or args.max_profundidad < 0 or min(cuotas.values()) < 0
            or sum(cuotas.values()) == 0 or args.max_indices_por_categoria < 0):
        parser.error("Cuotas >= 0 (total > 0), índices >= 0, pausa >= 3, solicitudes >= 1 y profundidad >= 0")
    ejecucion = crear_ejecucion(DATA / "ejecuciones", "corpus")
    docs, reporte = ejecutar(args.pausa, args.max_solicitudes, args.max_profundidad,
                            cuotas=cuotas, max_indices_por_categoria=args.max_indices_por_categoria,
                            corpus_previo=args.corpus_previo)
    guardar_nuevo(ejecucion / "corpus.json", docs)
    guardar_nuevo(ejecucion / "reporte.json", reporte)
    print(f"Resultado real: {reporte['resultado']}; {len(docs)}/{sum(cuotas.values())} documentos; "
          f"{reporte['conteo_por_categoria']}")
    print(f"Corpus y reporte: {ejecucion}")
    return 0 if reporte["resultado"] == "completo" else 1


if __name__ == "__main__":
    raise SystemExit(main())
