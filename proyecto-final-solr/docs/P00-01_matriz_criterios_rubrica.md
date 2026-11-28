# P00-01 · Matriz de criterios, responsables, pruebas y evidencias

**Proyecto:** Buscador web y de documentos con Apache Solr, FastAPI y Angular  
**Materia:** Búsqueda y Recuperación de Información  
**Fecha de elaboración:** 27 de noviembre de 2026  
**Coordinación:** Joseph (A)  
**Fuente de criterios y puntuaciones:** rúbrica del proyecto compartida previamente por el equipo (9 criterios obligatorios, 30 puntos; hasta 2 extras de 2 puntos).  
**Fuente de responsables y tareas:** distribución registrada en Todoist (P00–P09).  
**Nota:** Estado técnico provisional al 27 de noviembre. Las pruebas unitarias de un módulo no sustituyen una demostración desde la interfaz.

## Matriz oficial de evaluación y plan de comprobación

| ID | Criterio de rúbrica | Puntos | Responsables principales | Prueba reproducible y resultado esperado | Evidencia para la entrega | Estado comprobado / pendiente |
|---|---|---:|---|---|---|---|
| C01 | Crawling HTML | 4 | A Joseph; D Mauricio (recuperación en UI) | Verificar corpus MDN de 60 URLs únicas, 20 JavaScript/20 HTML/20 CSS; hashes, esquema y origen; ejecutar `python -X utf8 -m unittest discover -s crawler -p "test_*.py" -v` sin crawling real. Esperado: 66 pruebas `OK` y 60 documentos web recuperables. | `crawler/evidencias/p01-07_pruebas_limpias.txt`, reporte de crawling, corpus validado, consultas en Solr y capturas de resultados. | **Parcialmente demostrado:** 66 pruebas aprobadas en Windows y 60 MDN indexados/verificados. Captura del flujo completo pendiente. |
| C02 | Preprocesamiento español | 4 | B Karen; A Joseph (Solr compartido) | Consultar `analysis/field` para `titulo` y `contenido` con mayúsculas, acentos, palabras vacías y variantes morfológicas; contrastar tokens y resultados. Esperado: analizador de español aplicado al core final y comportamiento documentado. | Archivo de tipos, stopwords y stemming; salidas de análisis y capturas P09-03; evidencia final de PR #10. | **Parcial:** configuración integrada; validación final y capturas pendientes. |
| C03 | Búsqueda booleana | 2 | C Carlos; D Mauricio | Ejecutar búsquedas AND/OR/NOT y combinaciones desde API e interfaz; comparar resultados con conjuntos esperados y verificar sanitización. | Casos de prueba, respuestas JSON, capturas de UI con consulta y resultados. | **Pendiente de integración extremo a extremo.** |
| C04 | Relevancia ponderada | 4 | C Carlos; A Joseph (datos) | Ejecutar las mismas consultas con `qf=titulo contenido` y `qf=titulo^4 contenido` (eDisMax), comparar ranking y scores; comprobar que títulos relevantes suban cuando corresponda. | Tabla antes/después, configuración y parámetros Solr, capturas ordenadas por score. | **Pendiente de comparación reproducible en aplicación.** |
| C05 | Sugerencias de llenado (autocompletado) | 3 | B Karen (Suggester); C Carlos (API); D Mauricio (UI) | Construir diccionarios y consultar `/sugerencias?suggest.q=prom`; comprobar que lista términos al escribir desde el buscador. Esperado: `terminos_es` responde con `promedio`, `promesa`, `promesas` y `prompt` en el índice probado. | JSON de Solr, esquema Suggester, respuesta del endpoint y captura del desplegable en Angular. | **Parcial:** diccionario y handler comprobados en `ri`; integración visual pendiente. |
| C06 | Sugerencias de corrección ortográfica | 3 | B Karen (SpellCheck); C Carlos (API); D Mauricio (UI) | Buscar `fucion` en `/ortografia`; comprobar `correctlySpelled=false`, sugerencia `función`, propuesta `collationQuery` y acción visible para corregir. | JSON Solr con sugerencias, capturas API/UI antes y después. | **Parcial:** SpellCheck comprobado en `ri` (25 resultados para `función`); interfaz pendiente. |
| C07 | Búsqueda facetada | 4 | C Carlos (filtros/API); D Mauricio (controles) | Consultar `facet.field=categoria`, `tipo_fuente` y aplicar filtros sin perder la consulta; comprobar recuentos y exclusión de categorías. | Respuesta facetada de Solr, pruebas API, capturas de filtros web/PDF en Angular. | **Parcial:** distribución web 20/20/20 comprobada; filtros desde aplicación y PDF pendientes. |
| C08 | Snippets | 2 | C Carlos (highlighting); D Mauricio (tarjetas/UI) | Consultar `hl=true&hl.fl=contenido`, mostrar fragmento y resaltar término de manera segura; probar ausencia de coincidencias y contenido HTML. | JSON con `highlighting`, captura de tarjetas y prueba de seguridad/renderizado. | **Pendiente de integración y demostración visual.** |
| C09 | Expansión semántica / sinonimia | 4 | B Karen (sinónimos); C Carlos (búsqueda); D Mauricio (UI) | Comparar consultas equivalentes `relleno`/`padding`, `margen`/`margin`, `arreglo`/`array` con y sin expansión; mostrar tokens, ID recuperados y cambios de resultados, sin afirmar mejora sin juicio de relevancia. | Managed synonyms, tabla de validación final PR #10, capturas de Solr y aplicación. | **Parcial:** mecanismos preparados; evidencia final después de integrar PDF y aplicación. |
| E01 | Extra: importación de documentos PDF/Office (se implementará PDF) | Hasta 2 | A Joseph (muestras, extracción, mapeo, indexación); C Carlos (API); D Mauricio (UI) | Importar dos PDF de texto seleccionable, recuperar `LinceFormulario2026` y `FaroRejilla2026`, comprobar `tipo_fuente=pdf`, repetir importación sin duplicar. | PDFs originales, manifiesto, 8 pruebas P07-02, JSON de índice, consultas y capturas de carga en UI. | **Parcial:** P07-01/P07-02 probados; P07-03/P07-04 y carga desde navegador pendientes. |
| E02 | Extra: recomendaciones / documentos relacionados (MoreLikeThis) | Hasta 2 | C Carlos (Solr/endpoint); D Mauricio (UI) | Solicitar documentos relacionados por ID, validar su pertinencia básica y mostrar recomendaciones desde la interfaz. | JSON de MoreLikeThis, pruebas API, captura de sección de relacionados y justificación. | **Pendiente:** tareas P07-06/P07-07/P07-08/P07-09/P08-12. |

**Puntuación máxima obligatoria:** 4 + 4 + 2 + 4 + 3 + 3 + 4 + 2 + 4 = **30 puntos**.  
**Extras propuestos:** hasta **4 puntos**, 2 por funcionalidad.  
**Máximo contemplado:** **34 puntos** (sujeto a la aceptación docente de ambos extras).  
**Importante:** esta es una matriz de planificación, no una declaración de puntos ya obtenidos.

## Criterios transversales para dar una función por validada

1. El código relevante está integrado en `main`, con sus dependencias y configuración reproducibles.
2. La funcionalidad responde en Solr y/o FastAPI según su nivel, y desde Angular cuando el criterio pide interacción visual.
3. Existe una consulta o caso de prueba con entradas, resultado esperado y resultado observado; se registra un fallo si no coincide.
4. Hay evidencia de la versión final (JSON, registros y capturas), no únicamente capturas del core aislado de pruebas.
5. Se conservan los 60 documentos MDN aprobados; al importar PDF, el total crece sin duplicar IDs ni perder documentos web.

## Responsabilidad por módulos y evidencia

- **A — Joseph:** crawler, corpus, transformación e indexación MDN; integración y respaldo Solr; importación PDF, reconstrucción final, matriz y empaquetado.
- **B — Karen:** análisis español, stopwords, stemming, sinónimos, Suggester/SpellCheck, comparación lingüística, evidencias P09-03.
- **C — Carlos:** FastAPI, consulta booleana, ranking, facetas, highlighting, recomendaciones y endpoints PDF; evidencia P09-04.
- **D — Mauricio:** Angular, resultados, filtros, sugerencias, snippets y extras visibles; capturas P09-05 y video P09-07.

## Control de evidencias ya disponibles

- **Crawler:** `crawler/evidencias/p01-07_pruebas_limpias.txt` — 66/66 pruebas `OK`, Python 3.14.0 y BeautifulSoup 4.15.0 comprobados el 27/11/2026.
- **MDN/Solr:** `indexacion/evidencias/p02-11/20261127T190627834462Z_53a6c411debf4c5a97eddc568681bf8f/` — `carga_verificada`, 60 documentos, 20/20/20 y cero bloqueos; 23/23 pruebas P02-11.
- **Sugerencias y ortografía:** comprobaciones directas en `ri`: cuatro sugerencias para `prom`, y corrección de `fucion` a `función`.
- **PDF:** PR #11 con dos PDF y extractor; ocho pruebas ejecutadas correctamente en Windows. Verificar integración en `main` y conservar el registro de pruebas.
- **Análisis final español:** PR #10 de Karen pendiente de resolución de conflictos/revisión y ejecución sobre el índice definitivo.

## Por completar antes de la entrega (2 de diciembre de 2026)

- Cerrar P07-03/P07-04 e integrar los dos PDF sin alterar los MDN.
- Integrar API y Angular y completar pruebas de criterios C03 a C09 y los dos extras.
- Reunir las capturas y salidas del core definitivo; no reemplazar por resultados del core local de Karen.
- Ejecutar la prueba de arranque limpio, revisar once criterios, conservar fallos y correcciones, y preparar el ZIP final.

## Validación y aceptación del equipo

| Integrante | Responsabilidad revisada | Confirmación / fecha |
|---|---|---|
| Joseph (A) | Crawling, Solr, PDF, integración y evidencias | Pendiente de validar formalmente con el equipo |
| Karen (B) | Español, sinónimos y sugerencias | Pendiente de validar formalmente con el equipo |
| Carlos (C) | FastAPI, consultas, ranking, recomendaciones | Pendiente de validar formalmente con el equipo |
| Mauricio (D) | Angular, visualización y demostración | Pendiente de validar formalmente con el equipo |

**Cierre P00-01:** marcar completada solo después de que los cuatro integrantes reconozcan sus responsabilidades y acepten las pruebas/evidencias previstas; registrar la fecha de conformidad en esta tabla.
