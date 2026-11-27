# P09-03 · Evidencia de preprocesamiento (P08-03)

**Estado: carpeta preparada, sin capturas.** Las capturas se toman sobre el **índice
definitivo, el `ri` de Joseph**, en su equipo (o juntos, con pantalla compartida),
después de P02-11/P08-02 y de ejecutar
`py analisis_es/validar_espanol_final.py --core ri --evidencia-final`.
Capturas hechas sobre otro Solr o sobre un core de prueba **no** sirven aquí.

Las URL de Solr Admin funcionan en el navegador del equipo donde corre ese Solr.
Cada captura debe mostrar la URL o la consulta y los títulos de los resultados.

| Archivo | URL | Qué debe verse |
|---|---|---|
| `preprocesamiento_01_acentos_analysis.png` | <http://localhost:8983/solr/#/ri/analysis?analysis.fieldvalue=Funci%C3%B3n%20de%20B%C3%9ASQUEDA&analysis.query=funcion%20de%20busqueda&analysis.fieldname=contenido&verbose_output=1> | Etapas del índice y de la consulta: `función`/`BÚSQUEDA` y `funcion`/`busqueda` terminan en los mismos tokens tras LowerCase y ASCIIFolding. |
| `preprocesamiento_02_acentos_busqueda.png` | <http://localhost:8983/solr/ri/select?q=FUNCION&defType=edismax&q.op=OR&qf=titulo%5E4%20contenido&fl=id%2Ctitulo&rows=10> | Resultados de `FUNCION`; comparar con la captura 03. |
| `preprocesamiento_03_acentos_busqueda.png` | <http://localhost:8983/solr/ri/select?q=funci%C3%B3n&defType=edismax&q.op=OR&qf=titulo%5E4%20contenido&fl=id%2Ctitulo&rows=10> | Resultados de `función` (casos A01 de la tabla). |
| `preprocesamiento_04_stopwords_analysis.png` | <http://localhost:8983/solr/#/ri/analysis?analysis.fieldvalue=la%20cadena%20de%20prototipos&analysis.fieldname=contenido&verbose_output=1> | Tras el filtro de palabras vacías desaparecen `la` y `de`; quedan `cadena` y `prototipos` (raíces). |
| `preprocesamiento_05_stopwords_busqueda.png` | <http://localhost:8983/solr/ri/select?q=la%20cadena%20de%20prototipos&defType=edismax&q.op=OR&qf=titulo%5E4%20contenido&fl=id%2Ctitulo&rows=10> | Resultados de la frase con palabras vacías (caso S01). |
| `preprocesamiento_06_stemming_analysis.png` | <http://localhost:8983/solr/#/ri/analysis?analysis.fieldvalue=promesas%20promesa%20selectores%20selector&analysis.fieldname=contenido&verbose_output=1> | SpanishLightStem: plural y singular comparten raíz. |
| `preprocesamiento_07_protegidas_analysis.png` | <http://localhost:8983/solr/#/ri/analysis?analysis.fieldvalue=media%20medio%20arrays%20array&analysis.fieldname=contenido&verbose_output=1> | KeywordMarker: `media` y `array` se conservan (protwords_es.txt); `medio` y `arrays` se recortan. |
| `preprocesamiento_08_aplicacion.png` | pendiente: ruta de la aplicación (Carlos/Mauricio); en `main` aún no hay API ni frontend | Buscador de la aplicación con `FUNCION` y los títulos devueltos. |

## Nota para la entrega (completar después de tomar las capturas)

- Qué se probó: mayúsculas y acentos, palabras vacías, variantes morfológicas y términos protegidos en `contenido` (`text_es_proyecto`).
- Por qué cubre el criterio: muestra los tokens del analizador real y los resultados de la consulta de la API sobre el índice definitivo.
- Resultados: ver `analisis_es/resultados/evidencia_final/validacion_final_ri.md`.
  No escribir aquí cifras que no salgan de esa tabla.
