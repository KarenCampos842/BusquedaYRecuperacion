# Capturas de Solr Admin para P03-09, P03-10 y P09-03

La herramienta usa las doce filas con URL de los README de [preprocesamiento](preprocesamiento/README.md) y [sinónimos](sinonimos/README.md). En Windows abre Edge con Playwright y captura los píxeles de la ventana real, incluida la barra de direcciones. El registro JSON conserva las URL, los criterios de Karen y los resultados observados.

## Ejecutar desde PowerShell

Desde `proyecto-final-solr`, con Edge instalado, la sesión de Windows desbloqueada y Solr escuchando en `http://localhost:8983`:

```powershell
# Si no tienes todavía el entorno virtual del proyecto:
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r analisis_es\requirements-capturas.txt
.\.venv\Scripts\python.exe -X utf8 analisis_es\capturar_solr_final.py --validacion 2026-11-28T014018Z_ri --revision --escala-unitaria
```

El programa comprueba primero 62 documentos en `ri` (60 web y 2 PDF). Si existe `INDICE.md`, verifica que la ejecución elegida figure allí y usa la última si omites `--validacion`. En una copia que trae solo la ejecución de esta entrega, indica el nombre de la carpeta como en el ejemplo. En ambos casos comprueba el JSON, el informe Markdown y la huella de los sinónimos del core. El segundo caso de sinónimos construye los dos términos de su URL a partir de `tokens_indice` de Y01. Deja Edge en primer plano y mantén el cursor dentro de la página para evitar vistas previas de Windows. `--escala-unitaria` fija la escala de Edge en 1 y permite ajustar el zoom nativo según el espacio disponible.

La ejecución normal escribe los PNG en `preprocesamiento/` y `sinonimos/`, y el informe en `registro_capturas_solr.json`. Si ya hay archivos, el comando se detiene. Usa `--revision` para una ejecución en una carpeta nueva con la misma estructura. Revisa las imágenes a tamaño original y contrasta el informe antes de publicar.

Si Windows impide la captura automática, usa `--manual`. Playwright abre y comprueba cada página, y espera en PowerShell mientras guardas el PNG en la ruta indicada. Ajusta el zoom de Edge si hace falta y usa la captura de ventana de Recortes de Windows para incluir la barra de direcciones. Vuelve a PowerShell y pulsa Enter después de guardar cada imagen.

La validación de Analysis lee las etapas y los tokens del HTML visible. En `/select`, compara el total y los IDs visibles con los resultados de la ejecución elegida. Como las URL de Karen no incluyen el desempate del validador, el orden de resultados con la misma puntuación puede variar. El registro incluye incidencias de carga, criterio y encuadre. Una ejecución con incidencias termina con código 1 y deja los archivos observados para revisión.

## Resultado de la ejecución

La captura inicial fue el 27 de noviembre de 2026, de 19:46 a 19:47 en Ciudad de México. La fuente de resultados es [2026-11-28T014018Z_ri](../../../analisis_es/resultados/evidencia_final/2026-11-28T014018Z_ri/validacion_final_ri.md), registrada en el `INDICE.md` local a las 01:40:18 UTC. El SHA-256 del JSON coincide con el registrado en la captura. Las comprobaciones de los doce PNG pasaron y el recuento posterior siguió en 62 documentos. La suite local de `analisis_es` pasó 95 pruebas.

- `FUNCION` y `función` devolvieron 35 coincidencias cada una y mostraron los mismos diez IDs. La frase con palabras vacías devolvió 26 coincidencias.
- La consulta de Y01 usó el token indexado `rellen`. Se observaron 3 coincidencias sin expansión y 8 con ella. Las cinco nuevas aparecen en la captura con expansión. `margen` devolvió 15 coincidencias.
- En Analysis, índice y consulta coinciden al terminar `ASCIIFolding`. A continuación, la consulta añade `function`. Esa diferencia posterior precisa el criterio de acentos. Las notas de entrega distinguen además el efecto del stemmer de los sinónimos que aparecen en consulta.
- Se volvieron a tomar las tres tablas al 33 % con zoom nativo al 50 % y escala unitaria, de 19:58 a 19:59. Las tres versiones seleccionadas conservan la URL, todas las etapas y los mismos tokens. Se revisaron visualmente y se conservaron los originales y el registro inicial en `revision_originales_analysis_33/`. En algunas de las otras nueve imágenes queda el aviso de batería, fuera de la información evaluada.
- Las revisiones descartadas incluyen fallos de foco, avisos del escritorio y un intento de captura directa de ventana que produjo PNG negros. El [registro final](registro_capturas_solr.json) conserva la fecha, el resultado y el hash por imagen. Solo los PNG seleccionados forman parte de la lista de entrega.

Las tres capturas de Angular quedan pendientes de Mauricio. Las evidencias de Solr se entregan para revisión de Karen.

## Archivos para la PR

Título propuesto `docs: P03-09, P03-10 y P09-03 - evidencias finales de español y sinónimos`.

Preparar los siguientes **20 archivos**, con rutas relativas a `proyecto-final-solr`. Los doce PNG seleccionados, su registro y el par JSON/Markdown de la ejecución elegida contienen los resultados definitivos para revisión. Los dos README y esta guía explican esos resultados. El script y sus dependencias permiten reproducirlos.

```text
analisis_es/capturar_solr_final.py
analisis_es/requirements-capturas.txt
analisis_es/resultados/evidencia_final/2026-11-28T014018Z_ri/validacion_final_ri.json
analisis_es/resultados/evidencia_final/2026-11-28T014018Z_ri/validacion_final_ri.md
docs/evidencias/P09-03/CAPTURAS_SOLR.md
docs/evidencias/P09-03/registro_capturas_solr.json
docs/evidencias/P09-03/preprocesamiento/README.md
docs/evidencias/P09-03/preprocesamiento/preprocesamiento_01_acentos_analysis.png
docs/evidencias/P09-03/preprocesamiento/preprocesamiento_02_acentos_busqueda.png
docs/evidencias/P09-03/preprocesamiento/preprocesamiento_03_acentos_busqueda.png
docs/evidencias/P09-03/preprocesamiento/preprocesamiento_04_stopwords_analysis.png
docs/evidencias/P09-03/preprocesamiento/preprocesamiento_05_stopwords_busqueda.png
docs/evidencias/P09-03/preprocesamiento/preprocesamiento_06_stemming_analysis.png
docs/evidencias/P09-03/preprocesamiento/preprocesamiento_07_protegidas_analysis.png
docs/evidencias/P09-03/sinonimos/README.md
docs/evidencias/P09-03/sinonimos/sinonimos_01_relleno_analysis.png
docs/evidencias/P09-03/sinonimos/sinonimos_02_relleno_sin_expansion.png
docs/evidencias/P09-03/sinonimos/sinonimos_03_relleno_con_expansion.png
docs/evidencias/P09-03/sinonimos/sinonimos_04_margen_analysis.png
docs/evidencias/P09-03/sinonimos/sinonimos_05_margen_con_expansion.png
```

El índice completo y la ejecución anterior `2026-11-28T013136Z_ri` quedan como historial local. Sus casos son idénticos a los de la ejecución seleccionada. Las carpetas `revision_*`, los candidatos en `.venv/`, los cachés y las salidas de otras actividades quedan fuera de la PR.
