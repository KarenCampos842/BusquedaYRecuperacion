# Autocompletado y corrección ortográfica en Solr (P05-01, P05-02, P05-03, P05-06)

**Autora:** Karen (integrante B) · **Fecha:** 26-nov-2026 · **Solr:** 10.0.0
**Corpus:** `corpus_solr.json` de P02-09 (60 documentos MDN)
**Core:** `ri_sugerencias_es` (aislado, con los campos del contrato P00-03; `ri` no se modificó)

Reproducir desde `proyecto-final-solr/`: `py analisis_es/probar_sugerencias_ortografia.py`.
Los datos completos están en `analisis_es/resultados/sugerencias_ortografia.json`. La configuración se describe en `analisis_es/README.md` (sección P05).

## Autocompletado: handler `/sugerencias` (diccionarios `terminos_es` y `titulos_es`, 5 sugerencias cada uno)

| Prefijo | `terminos_es` (palabras del contenido) | `titulos_es` (títulos completos) |
|---|---|---|
| jav | javascript; java; javascript.js | Una reintroducción a JavaScript (Tutorial de JS); Tipos de datos y estructuras en JavaScript; JavaScript; Guía de JavaScript |
| sel | selector; selectores; selectors; selecciona; seleccionando | Selectores de tipo; Selectores de clase; Selectores de ID; Selectores universales |
| her | herencia; hereda; heredada; heredan; herramientas | Herencia y la cadena de prototipos; Herencia |
| cad | cadena; cadenas | Herencia y la cadena de prototipos; String — Cadena de caracteres |
| pro | pro; propiedad; propiedades; properties; proporciona | Herencia y la cadena de prototipos; Procesamiento del valor de las propiedades CSS; Propiedades abreviadas |
| prom | promedio; promesa; promesas; prompt | — |
| elem | elem; elemento; elementos; element; elements | `<link>` elemento de enlace a recurso externo HTML; Elemento de metadatos HTML `<meta>`; `<script>`: The Script element; `<title>`: El elemento Título del documento; `<body>`: El elemento body del documento |
| ESPEC | especificación; especificaciones; especifica; especificado; especificar | Especificidad |
| func | función; function; funciona; funciones; funcionalidad | Function |
| xyz | — | — |

- 9 de los 10 prefijos devuelven términos; 8 devuelven títulos. «xyz» no devuelve nada en ninguno de los dos.
- «prom» devuelve 4 términos del contenido (promedio, promesa, promesas, prompt) y ningún título: ningún título contiene una palabra que empiece por «prom».
- Los términos se ordenan por número de documentos que los contienen. Los 4 de «prom» aparecen en 1 documento cada uno, así que quedan en orden alfabético.
- Cuando el prefijo coincide con una palabra completa del contenido, esa palabra va primero (`exactMatchFirst`): «pro» y «elem» existen como palabras en el corpus.
- Las sugerencias de términos conservan los acentos («función», «especificación») aunque el prefijo se escriba sin ellos o en mayúsculas («ESPEC»).
- El vocabulario descarta tokens con números o símbolos: en `contenido_ortografia` existe «javascript:void» y en `contenido_vocabulario` no. Conserva nombres de API con punto entre letras («javascript.js», «function.length»).
- Los ejemplos del contrato P00-04 «promesa en javascript» y «promise.all» no aparecen: el corpus no contiene «promise.all», y el vocabulario es de palabras sueltas, no de frases.

## Corrección: handler `/ortografia` (diccionario `contenido_es`)

| Consulta | ¿Correcta? | Alternativas | Consulta sugerida |
|---|---|---|---|
| javasript | no | javascript | javascript |
| fucion | no | función, function, funciona, funcione | función |
| selectr | no | selector, select, selectors | selector |
| prototpo | no | prototipo, prototipos, prototype | prototipo |
| herensia | no | herencia | herencia |
| promesaz | no | promesas, promesa, procesar, procesan, procesa | promesas |
| propiedadez | no | propiedades, propiedad | propiedades |
| javascript | sí | — | — |
| javasript selectr | no | javasript → javascript; selectr → selector, select, selectors | javascript selector |

- Las 8 consultas con errores reciben al menos una alternativa y una consulta sugerida. La consulta escrita correctamente («javascript») se marca como correcta y no recibe sugerencias.
- Las sugerencias conservan los acentos («fucion» → «función») porque `contenido_ortografia` no pliega acentos ni aplica stemming.
- Las alternativas incluyen términos en inglés presentes en el corpus («function», «prototype», «selectors»).

## Verificaciones

- Ejecuciones repetidas sin errores. En la segunda, los tipos y campos se reemplazan, los componentes se actualizan y no se duplican los `copyField`.
- El overlay del core de prueba solo contiene `sugerencias_es`, `ortografia_es`, `/sugerencias` y `/ortografia`. El componente `spellcheck` del configset sigue apuntando a `_text_`.
- `ri` local sin cambios: mismos campos y overlay vacío.

## Limitaciones

- Índice de prueba con 60 documentos. La validación en la aplicación final corresponde a P05-09, P08-08 y P08-09.
- No se evaluó la utilidad de las sugerencias con usuarios ni con juicios de relevancia; las tablas solo registran lo que devuelve Solr.
