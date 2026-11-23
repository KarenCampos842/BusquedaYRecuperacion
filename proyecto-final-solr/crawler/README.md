# Piloto MDN: un artículo

Desde `proyecto-final-solr/`, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r crawler/requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s crawler -v
.\.venv\Scripts\python.exe -X utf8 crawler/mdn_piloto.py
```

Solo el último comando consulta MDN: primero robots.txt y después el artículo
fijo de Introducción a JavaScript, si está permitido. No recorre enlaces.
El intervalo mínimo es de tres segundos y el timeout es de veinte segundos.
Las redirecciones se validan antes de seguirlas. No hay reintentos automáticos.

El resultado se escribe en `data/mdn/piloto_1.json`, relativo al proyecto,
con independencia del directorio de ejecución. El reporte separado
`data/mdn/piloto_1_reporte.json` registra los estados HTTP y errores.
La consola muestra título, idioma, categoría, tamaño y una vista previa.
Una ejecución fallida devuelve código 1; no genera un nuevo documento ni
borra un resultado anterior: revisar siempre el reporte de la última ejecución.

El selector del diseño actual es `main#content .reference-layout__body`;
también se admite `article.main-page-content`. Se conserva la atribución a
MDN; revisar las condiciones CC BY-SA y sus excepciones antes de redistribuir.
Los ejemplos de las pruebas son sintéticos y solo verifican el extractor;
el JSON del piloto procede de la descarga real.
