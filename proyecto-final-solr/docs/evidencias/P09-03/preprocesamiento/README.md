# P09-03 · Evidencia de preprocesamiento (P08-03)

**Estado: siete capturas de Solr Admin disponibles.** Las capturas se toman sobre el **índice
definitivo, el `ri` de Joseph**, en su equipo (o juntos, con pantalla compartida),
después de P02-11/P08-02 y de ejecutar
`py analisis_es/validar_espanol_final.py --core ri --evidencia-final`.
Capturas hechas sobre otro Solr o sobre un core de prueba **no** sirven aquí.

Las URL de Solr Admin funcionan en el navegador del equipo donde corre ese Solr.
Cada captura debe mostrar la URL o la consulta y los títulos de los resultados.

| Archivo | URL | Qué debe verse |
|---|---|---|
| `preprocesamiento_01_acentos_analysis.png` | <http://localhost:8983/solr/#/ri/analysis?analysis.fieldvalue=Funci%C3%B3n%20de%20B%C3%9ASQUEDA&analysis.query=funcion%20de%20busqueda&analysis.fieldname=contenido&verbose_output=1> | Etapas del índice y de la consulta. Los tokens coinciden tras aplicar LowerCase seguido de ASCIIFolding. Las etapas posteriores se describen en la nota de entrega. |
| `preprocesamiento_02_acentos_busqueda.png` | <http://localhost:8983/solr/ri/select?q=FUNCION&defType=edismax&q.op=OR&qf=titulo%5E4%20contenido&fl=id%2Ctitulo&rows=10> | Resultados de `FUNCION`; comparar con la captura 03. |
| `preprocesamiento_03_acentos_busqueda.png` | <http://localhost:8983/solr/ri/select?q=funci%C3%B3n&defType=edismax&q.op=OR&qf=titulo%5E4%20contenido&fl=id%2Ctitulo&rows=10> | Resultados de `función` (casos A01 de la tabla). |
| `preprocesamiento_04_stopwords_analysis.png` | <http://localhost:8983/solr/#/ri/analysis?analysis.fieldvalue=la%20cadena%20de%20prototipos&analysis.fieldname=contenido&verbose_output=1> | Tras el filtro de palabras vacías desaparecen `la` y `de`; quedan `cadena` y `prototipos` (raíces). |
| `preprocesamiento_05_stopwords_busqueda.png` | <http://localhost:8983/solr/ri/select?q=la%20cadena%20de%20prototipos&defType=edismax&q.op=OR&qf=titulo%5E4%20contenido&fl=id%2Ctitulo&rows=10> | Resultados de la frase con palabras vacías (caso S01). |
| `preprocesamiento_06_stemming_analysis.png` | <http://localhost:8983/solr/#/ri/analysis?analysis.fieldvalue=promesas%20promesa%20selectores%20selector&analysis.fieldname=contenido&verbose_output=1> | SpanishLightStem: plural y singular comparten raíz. |
| `preprocesamiento_07_protegidas_analysis.png` | <http://localhost:8983/solr/#/ri/analysis?analysis.fieldvalue=media%20medio%20arrays%20array&analysis.fieldname=contenido&verbose_output=1> | KeywordMarker: `media` y `array` se conservan (protwords_es.txt); `medio` se recorta a `medi`. `arrays` tampoco se recorta (el stemmer no lo cambia), así que en el índice no se une a `array`. |
| `preprocesamiento_08_aplicacion.png` | Captura de Angular pendiente, asignada a Mauricio | Buscador de la aplicación con `FUNCION` y los títulos devueltos. |

## Nota para la entrega

Se probó el analizador `text_es_proyecto` del campo `contenido` en el core definitivo `ri`. Analysis muestra el efecto de cada filtro y las consultas directas a Solr permiten contrastarlo con los documentos recuperados.

- **Mayúsculas y acentos · A01.** Las secuencias de índice y consulta coinciden en `funcion de busqueda` tras `LowerCase` y `ASCIIFolding`. Más adelante, `SynonymGraph` añade `function` en la consulta. `FUNCION` y `función` recuperaron el mismo conjunto de 35 documentos. Las capturas 02 y 03 muestran los mismos diez IDs.
- **Palabras vacías · S01.** El filtro quita `la` y `de` de `la cadena de prototipos` y conserva `cadena` y `prototipos`. El stemmer produce `caden` y `prototip`. En la validación, ambas variantes de la frase recuperaron los mismos 26 documentos.
- **Stemming · M01 y M02.** En Analysis, `promesas` y `promesa` generan `promes`; `selectores` y `selector` generan `selector`. En consulta, M01 añade `promis` o `promise` según la variante y ambas recuperan los mismos 2 documentos. M02 recupera los mismos 9.
- **Términos protegidos · P01 y P02.** `KeywordMarker` protege `media` y `array`. Al terminar el análisis de índice, `medio` se reduce a `medi` y `arrays` conserva su forma, distinta de `array`. La validación registra conjuntos distintos para `media` y `medio` (12 y 9) y para `arrays` y `array` (13 y 14).

Se usó la ejecución final [2026-11-28T014018Z_ri](../../../../analisis_es/resultados/evidencia_final/2026-11-28T014018Z_ri/validacion_final_ri.md). El [registro](../registro_capturas_solr.json) vincula cada imagen con su consulta y su comprobación. La evidencia de Angular queda pendiente de Mauricio y el cierre compartido queda sujeto a revisión de Karen.
