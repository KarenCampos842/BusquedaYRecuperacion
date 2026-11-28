# P09-03 · Evidencia de sinonimia (P08-04)

**Estado: cinco capturas de Solr Admin disponibles.** Las capturas se toman sobre el **índice
definitivo, el `ri` de Joseph**, en su equipo (o juntos, con pantalla compartida),
después de P02-11/P08-02 y de ejecutar
`py analisis_es/validar_espanol_final.py --core ri --evidencia-final`.
Capturas hechas sobre otro Solr o sobre un core de prueba **no** sirven aquí.

Las URL de Solr Admin funcionan en el navegador del equipo donde corre ese Solr.
Cada captura debe mostrar la URL o la consulta y los títulos de los resultados.

| Archivo | URL | Qué debe verse |
|---|---|---|
| `sinonimos_01_relleno_analysis.png` | <http://localhost:8983/solr/#/ri/analysis?analysis.query=relleno&analysis.fieldname=contenido&verbose_output=1> | Analizador de consulta: SynonymGraph añade `padding` a `relleno`. |
| `sinonimos_02_relleno_sin_expansion.png` | <http://localhost:8983/solr/ri/select?q=%7B%21bool%20should%3D%24t0%20should%3D%24t1%7D&t0=%7B%21term%20f%3Dtitulo%7Drellen&t1=%7B%21term%20f%3Dcontenido%7Drellen&fl=id%2Ctitulo&rows=10> | Sin expansión: documentos que contienen la forma indexada de `relleno`. Antes de capturar, comprobar el token exacto en `tokens_indice` de Y01 (`validacion_final_ri.json` de la carpeta de la ejecución elegida); si difiere de `rellen`, cambiarlo en la URL. |
| `sinonimos_03_relleno_con_expansion.png` | <http://localhost:8983/solr/ri/select?q=relleno&defType=edismax&q.op=OR&qf=titulo%5E4%20contenido&fl=id%2Ctitulo&rows=10> | Con expansión: consulta real; deben aparecer los documentos nuevos de la tabla (Y01). |
| `sinonimos_04_margen_analysis.png` | <http://localhost:8983/solr/#/ri/analysis?analysis.query=margen&analysis.fieldname=contenido&verbose_output=1> | Analizador de consulta: `margen` se expande a `margin`. |
| `sinonimos_05_margen_con_expansion.png` | <http://localhost:8983/solr/ri/select?q=margen&defType=edismax&q.op=OR&qf=titulo%5E4%20contenido&fl=id%2Ctitulo&rows=10> | Consulta real de `margen` (caso Y02). |
| `sinonimos_06_aplicacion_relleno.png` | Captura de Angular pendiente, asignada a Mauricio | Buscador de la aplicación con `relleno` mostrando títulos que solo dicen `padding` (sin escribir OR). |
| `sinonimos_07_aplicacion_margen.png` | Captura de Angular pendiente, asignada a Mauricio | Buscador de la aplicación con `margen`. |

## Nota para la entrega

Se probó la expansión de `relleno` a `padding` y de `margen` a `margin` en el analizador de consulta de `contenido`. Analysis muestra en qué etapa aparece cada sinónimo. Las búsquedas contrastan la recuperación con y sin pasar por ese analizador.

- **Y01 · `relleno`.** `SynonymGraph` añade `padding`. La forma indexada de `relleno` es `rellen`, según `tokens_indice`. La búsqueda exacta de ese token en `titulo` o `contenido` devolvió 3 documentos. La búsqueda normal de `relleno` devolvió 8. La comparación por ID muestra los 3 originales y 5 adicionales, entre ellos «Referencia CSS» y «Procesamiento del valor de las propiedades CSS».
- **Y02 · `margen`.** `SynonymGraph` añade `margin`. La captura de búsqueda confirma 15 coincidencias y muestra los primeros diez títulos. La validación registra 6 sin expansión y 15 con expansión. La búsqueda de `margin` con expansión recuperó el mismo conjunto.

Las cifras describen los conjuntos recuperados. La validación no mide precisión ni relevancia. La fuente es la ejecución final [2026-11-28T014018Z_ri](../../../../analisis_es/resultados/evidencia_final/2026-11-28T014018Z_ri/validacion_final_ri.md) y el [registro de capturas](../registro_capturas_solr.json). Las dos evidencias de Angular quedan pendientes de Mauricio y el cierre compartido queda sujeto a revisión de Karen.
