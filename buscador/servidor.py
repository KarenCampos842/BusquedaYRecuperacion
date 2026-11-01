"""Servidor web local. Ejecuta:

    python servidor.py             # indexa si hace falta y abre el buscador
    python servidor.py --indexar   # solo reconstruye el índice
"""
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, quote, urlparse

import config
import db
import indexador
import interfaz
import ranking


def _resumen(r):
    return (f'Índice listo: {r["documentos"]} documentos, {r["terminos"]} términos, '
            f'{r["postings"]} postings y {r["posiciones"]} posiciones '
            f'({r["segundos"]:.2f} s).')


class Manejador(BaseHTTPRequestHandler):
    def _enviar(self, html, codigo=200):
        datos = html.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _redirigir(self, destino):
        self.send_response(303)
        self.send_header("Location", destino)
        self.end_headers()

    def do_GET(self):
        url = urlparse(self.path)
        params = parse_qs(url.query)
        q = params.get("q", [""])[0].strip()
        try:
            with db.Conexion() as con:
                if url.path == "/":
                    mensaje = params.get("msg", [""])[0]
                    self._enviar(interfaz.inicio(ranking.estadisticas(con), mensaje))

                elif url.path == "/buscar":
                    if not q:
                        self._redirigir("/")
                    else:
                        self._enviar(interfaz.resultados(ranking.buscar(con, q)))

                elif url.path == "/documento":
                    try:
                        id_doc = int(params.get("id", ["0"])[0])
                    except ValueError:
                        id_doc = 0
                    filas = con.consultar(
                        "SELECT id_documento, archivo, fecha, palabras, tokens, tamano "
                        "FROM Documento WHERE id_documento = ?", (id_doc,))
                    if filas:
                        self._enviar(interfaz.documento(filas[0], q))
                    else:
                        self._enviar(interfaz.error("Documento no encontrado",
                                                    "Ese documento no existe en el índice."), 404)
                else:
                    self._enviar(interfaz.error("Página no encontrada",
                                                "La dirección no existe."), 404)
        except Exception as e:
            self._enviar(interfaz.error("Algo salió mal", f"{type(e).__name__}: {e}"), 500)

    def do_POST(self):
        if urlparse(self.path).path != "/reindexar":
            self._enviar(interfaz.error("Página no encontrada", "La dirección no existe."), 404)
            return
        try:
            with db.Conexion() as con:
                resumen = indexador.indexar(con)
            ranking.invalidar_cache()
            self._redirigir("/?msg=" + quote(_resumen(resumen)))
        except Exception as e:
            self._enviar(interfaz.error("No se pudo reindexar", f"{type(e).__name__}: {e}"), 500)

    def log_message(self, formato, *args):
        print("  " + (formato % args))


def preparar_indice(forzar=False):
    db.crear_base_si_falta()
    with db.Conexion() as con:
        vacio = (not db.esquema_existe(con)
                 or con.consultar("SELECT COUNT(*) FROM Documento")[0][0] == 0)
        if forzar or vacio:
            print("Indexando documentos…")
            print(_resumen(indexador.indexar(con)))
    ranking.invalidar_cache()


def main():
    forzar = "--indexar" in sys.argv[1:]
    try:
        preparar_indice(forzar)
    except SystemExit:
        raise
    except Exception as e:
        print(f"\nNo se pudo preparar la base de datos ({type(e).__name__}: {e}).")
        if config.MOTOR == "mysql":
            print("Revisa que MySQL esté iniciado en el panel de XAMPP y que los datos de "
                  "conexión en config.py sean correctos.")
        return
    if forzar:
        return

    direccion = f"http://localhost:{config.PUERTO}"
    servidor = HTTPServer(("127.0.0.1", config.PUERTO), Manejador)
    print(f"\nBuscador en {direccion}  (Ctrl+C para detener)")
    webbrowser.open(direccion)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
