"""Punto de entrada de la aplicación."""
import webbrowser

from base_datos.inicializador import inicializar_base_datos
from config import ajustes
from web.servidor import crear_servidor


def iniciar() -> None:
    """Inicializa la base, arranca el servidor y abre el navegador."""
    inicializar_base_datos()
    ajustes.CARPETA_ALMACEN.mkdir(parents=True, exist_ok=True)
    servidor = crear_servidor(ajustes.HOST, ajustes.PUERTO)
    direccion = f"http://{ajustes.HOST}:{ajustes.PUERTO}/"
    print(f"Servidor en {direccion} (Ctrl+C para detenerlo)")
    webbrowser.open(direccion)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("Servidor detenido.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    iniciar()
