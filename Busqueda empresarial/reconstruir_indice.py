"""Vuelve a construir el índice FULLTEXT de la tabla documentos.

Úsalo después de cambiar innodb_ft_min_token_size o innodb_ft_max_token_size en
my.ini (y reiniciar MySQL), o después de editar recursos/stopwords_es.txt.
Los documentos no se pierden: solo se borra y se vuelve a crear el índice.

    python reconstruir_indice.py
"""
from base_datos.conexion import abrir_conexion
from base_datos.inicializador import inicializar_base_datos, usar_stopwords_propias
from base_datos.repositorios import repositorio_fulltext


def reconstruir() -> None:
    """Recarga las palabras vacías y reconstruye el índice FULLTEXT."""
    inicializar_base_datos()
    conexion = abrir_conexion()
    try:
        usar_stopwords_propias(conexion)
        with conexion.cursor() as cursor:
            cursor.execute("ALTER TABLE documentos DROP INDEX ft_contenido")
            cursor.execute("ALTER TABLE documentos ADD FULLTEXT INDEX ft_contenido (contenido)")
        conexion.commit()
        configuracion = repositorio_fulltext.obtener_configuracion(conexion)
    finally:
        conexion.close()
    print("Índice FULLTEXT reconstruido.")
    print(f"Longitud de palabra indexada: {configuracion.longitud_minima} a {configuracion.longitud_maxima}")


if __name__ == "__main__":
    reconstruir()
