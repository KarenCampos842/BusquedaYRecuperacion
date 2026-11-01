BUSCADOR TF-IDF  (Python, solo biblioteca estándar + conector de MySQL)

1. Abre XAMPP y pulsa "Start" en MySQL.
2. Instala el conector (una sola vez):   pip install mysql-connector-python
3. Pon tus archivos .txt en la carpeta documentos/
4. Ejecuta: python servidor.py
   Se abre http://localhost:8000. La base de datos "buscador_ri" se crea sola.

Si no quieres instalar nada: en config.py cambia MOTOR = "sqlite".
Para reconstruir el índice: botón "Reindexar documentos" o  python servidor.py --indexar

Archivos:
  config.py      ajustes (BD, carpeta, puerto, IDF suavizado)
  db.py          conexión y esquema: Vocabulario, Posting, Posicion, Documento
  texto.py       tokenización, normalización, stopwords
  indexador.py   lee los .txt y llena las 4 tablas
  ranking.py     TF-IDF + similitud coseno
  interfaz.py    HTML/CSS     servidor.py   servidor web local
