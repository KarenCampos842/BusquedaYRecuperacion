# Comparación de analizadores de español (P03-01, P03-04, P03-06, P03-08)

**Autora:** Karen (integrante B) · **Fecha:** 26-nov-2026 · **Solr:** 10.0.0
**Corpus:** `corpus_solr.json` de P02-09 (60 documentos MDN: 20 JavaScript, 20 HTML, 20 CSS)
**Core:** `ri_analisis_es` (aislado; `ri` no se modificó)

Reproducir desde `proyecto-final-solr/`: `py analisis_es/comparar_analizadores.py`
(los datos completos quedan en `analisis_es/resultados/comparacion_analizadores.json`).

## Método

- Los mismos 60 documentos se indexan en cuatro pares de campos `titulo_<v>` y `contenido_<v>`, uno por cada tipo:
  - `ri` = `text_es_ri` (control del kit)
  - `stop` = `text_es_stop`
  - `stem` = `text_es_stem`
  - `proyecto` = `text_es_proyecto`
- Consulta: `defType=edismax`, `q.op=OR`, `qf=titulo_<v>^4 contenido_<v>`. Es el mismo peso que usará la API.
- Las columnas indican cuántos documentos coinciden (de 60).
- "Nuevos" y "perdidos" comparan el conjunto de `proyecto` con el de `ri`.

## Resultados

| ID | Consulta | Propósito | ri | stop | stem | proyecto | Nuevos con proyecto (vs ri) | Perdidos |
|---|---|---|---|---|---|---|---|---|
| C01 | promesas | morfología | 1 | 1 | 2 | 2 | Expresiones y operadores | 0 |
| C02 | promesa | morfología | 1 | 1 | 2 | 2 | Guía de JavaScript | 0 |
| C03 | arreglos | morfología | 5 | 5 | 9 | 13 | Array; BigInt; Booleano (+5) | 0 |
| C04 | funciones | morfología | 13 | 13 | 32 | 32 | 19 documentos con «función» | 0 |
| C05 | selectores | morfología | 9 | 9 | 9 | 9 | — | 0 |
| C06 | función | acentos | 25 | 25 | 32 | 35 | 10 (plural «funciones» y sinónimo «function») | 0 |
| C07 | funcion | acentos | 25 | 25 | 32 | 35 | igual que C06 | 0 |
| C08 | MÉTODOS | acentos | 20 | 20 | 25 | 25 | 5 documentos con «método» | 0 |
| C09 | la cadena de prototipos | stopwords | 60 | 24 | 60 | 26 | — | 34 |
| C10 | el modelo de caja | stopwords | 60 | 10 | 60 | 10 | — | 50 |
| C11 | "cadena de prototipos" | frase con stopword | 4 | 4 | 4 | 4 | — | 0 |
| C12 | promise | sinónimos | 0 | 0 | 0 | 2 | Expresiones y operadores; Guía de JavaScript | 0 |
| C13 | relleno | sinónimos | 2 | 2 | 3 | 8 | 6 páginas con `padding` | 0 |
| C14 | hipervínculo | sinónimos | 1 | 1 | 4 | 4 | `<base>`; `<body>`; HTML | 0 |
| C15 | expresión regular | sinónimos | 10 | 10 | 13 | 10 | Guía de JavaScript; JavaScript | 2 |
| C16 | media | protegidas | 12 | 12 | 16 | 12 | — | 0 |
| C17 | CSS selector | control | 26 | 26 | 26 | 26 | — | 0 |

## Observaciones

- **Acentos y mayúsculas (P03-01).** `text_es_ri` ya trata igual «función», «funcion» y «MÉTODOS» (C06 = C07). Es la línea base: pliega los acentos y conserva también el original (`búsqueda` → `busqueda`, `búsqueda`), pero no quita palabras vacías ni reduce plurales.
- **Stopwords (P03-04).**
  - Con `q.op=OR`, «la» y «de» hacen que `ri` devuelva **los 60 documentos** en C09 y C10. Con stopwords quedan 24–26 y 10: los documentos que contienen «cadena» o «prototipos» (C09), o «modelo» o «caja» (C10).
  - Los «perdidos» de C09 (34) y C10 (50) son documentos que coincidían solo por «la», «el» o «de».
  - La búsqueda de frase (C11) no cambia: el filtro conserva las posiciones.
- **Stemming (P03-06).**
  - Singular y plural se unifican: «promesa/promesas» pasan de 1 a 2 documentos y «funciones» de 13 a 32.
  - «selectores» (C05) no cambia porque las páginas que usan «selector» también usan «selectores».
- **Términos protegidos.**
  - Sin protección, el stemmer recorta `media` → `medi`, que coincide con «medio». C16 en `stem` pasa de 12 a 16: los 4 documentos adicionales (`<a>`, `<script>`, HTML, Tipos de datos) coinciden por la raíz `medi`.
  - Con `text_es_proyecto` vuelve a 12.
  - `canvas` → `canv` también queda protegido.
- **Sinónimos solo en consulta (P03-08).**
  - **C12 «promise»** no aparece literalmente en ningún documento: `ri` devuelve 0 y `proyecto` devuelve 2, que contienen «promesa(s)». La expansión ocurre sin que el usuario escriba `OR`.
  - **C13 «relleno»** pasa de 2 a 8 por `padding`. Los 6 documentos añadidos contienen `padding`; sus títulos (`<a>`, `<article>`, `<audio>`…) no mencionan «relleno».
  - **C15** pasa a buscar la frase «expresión regular» o `regex`/`regexp`. El total queda en 10: pierde 2 documentos que solo tenían «expresión» o «regular» por separado (selectores de ID, `Function`) y gana 2 (Guía de JavaScript, JavaScript).
  - **C14:** en todas estas cifras ya se quitó «enlace» del grupo (`fix:` `438c932`). Con él, «hipervínculo» coincidía con 11 documentos, entre ellos Herencia («enlace a un objeto prototipo»), Array («ámbito de enlace `with`») y String («enlace a URL», en `String.prototype.link()`). Sin él coincide con 4, el mismo total que `stem` (por el plural `hipervínculos`).
- **Control (C17).** «CSS selector» da 26 en las cuatro variantes.

## Evidencias (capturas de Solr Admin, core `ri_analisis_es`)

Capturas tomadas por Karen el 26-nov-2026 sobre el índice de prueba de 60 documentos, no sobre la colección final. Cuando la tabla de tokens no cabía en una pantalla, la captura se dividió en dos partes.

| Tarea | Captura | Qué muestra |
|---|---|---|
| P03-01 | [parte 1](evidencias/P03-01_linea_base_1.png), [parte 2](evidencias/P03-01_linea_base_2.png) | Analysis de `titulo_ri` (`text_es_ri`). En índice, «BÚSQUEDA de Información» pasa a `búsqueda`, `información` (minúsculas) y después a `busqueda`/`búsqueda` e `informacion`/`información` (plegado con original); `de` se conserva. En consulta, «busqueda de informacion» queda `busqueda`, `de`, `informacion`. |
| P03-03 | [captura](evidencias/P03-03_stopwords.png) | Analysis de `contenido_stop` con «la búsqueda de los documentos». Tras el filtro de palabras vacías (SF) quedan `busqueda`, `búsqueda` y `documentos`; `la`, `de` y `los` se eliminan y las posiciones 2 y 5 se mantienen. |
| P03-05 | [captura](evidencias/P03-05_stemming.png) | Analysis de `contenido_stem` (el desplegable aparece recortado como «contenido_st…»; la etapa SLSF identifica el tipo). «buscar buscando documento documentos» termina en `buscar`, `buscand`, `document`, `document`: `documento` y `documentos` comparten raíz; `buscar` y `buscando` no. |
| P03-08 | [análisis, parte 1](evidencias/P03-08_sinonimos_analysis_1.png), [parte 2](evidencias/P03-08_sinonimos_analysis_2.png) | Analysis de consulta en `contenido_proyecto` con «promise». El filtro de sinónimos (SGF) produce `promesa` y `promise` (tipo SYNONYM) en la misma posición; PKMF marca `promise` como `keyword=true` y el stemming deja `promes` y `promise`. |
| P03-08 | [búsqueda](evidencias/P03-08_sinonimos_busqueda.png) | Respuesta JSON de `/select` (la captura no incluye la barra de direcciones). En `params` se ven `q=promise`, `defType=edismax`, `qf=titulo_proyecto^4 contenido_proyecto` y `fl=id,titulo_ri`; devuelve `numFound: 2`: «Guía de JavaScript» y «Expresiones y operadores». La consulta se hizo en `ri_analisis_es`, único core con esos campos. |

## Limitaciones

- **Precisión y exhaustividad no se calcularon** porque no hay juicios de relevancia aprobados. El script calcula P@5 y Recall@10 si se agrega `analisis_es/juicios_relevancia.csv` (`consulta_id,doc_id`). Los juicios los define el equipo, no el script.
- Es un índice de prueba con 60 documentos. La validación sobre el índice final corresponde a P08-03 y P08-04.

## Hallazgos técnicos de Solr 10

- `ManagedStopFilterFactory` y `ManagedSynonymGraphFilterFactory` **sí funcionan**. No hizo falta copiar archivos al contenedor.
- La REST API de sinónimos gestionados **rechaza la forma «lista de listas»** (error 500). Se envía un mapa en el que cada término apunta a su grupo completo (`fix:` `1c8b9f3`).
- Los cambios en los recursos gestionados se aplican después de recargar el core; el script recarga solo.
