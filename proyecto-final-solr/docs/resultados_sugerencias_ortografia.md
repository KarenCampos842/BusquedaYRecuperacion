# Autocompletado y corrección ortográfica en Solr (P05-01, P05-02, P05-03, P05-06)

**Autora:** Karen (integrante B) · **Fecha:** 26-nov-2026 · **Solr:** 10.0.0
**Corpus:** `corpus_solr.json` de P02-09 (60 documentos MDN)
**Core:** `ri_sugerencias_es` (aislado, con los campos del contrato P00-03; `ri` no se modificó)

Reproducir desde `proyecto-final-solr/`: `py analisis_es/probar_sugerencias_ortografia.py`.
Los datos completos están en `analisis_es/resultados/sugerencias_ortografia.json`. La configuración se describe en `analisis_es/README.md` (sección P05).

## Autocompletado: handler `/sugerencias` (diccionario `titulos_es`, 5 sugerencias)

| Prefijo | Títulos sugeridos |
|---|---|
| jav | Una reintroducción a JavaScript (Tutorial de JS); Tipos de datos y estructuras en JavaScript; JavaScript; Guía de JavaScript |
| sel | Selectores de tipo; Selectores de clase; Selectores de ID; Selectores universales |
| her | Herencia y la cadena de prototipos; Herencia |
| cad | Herencia y la cadena de prototipos; String — Cadena de caracteres |
| pro | Herencia y la cadena de prototipos; Procesamiento del valor de las propiedades CSS; Propiedades abreviadas |
| prom | — |
| elem | `<link>` elemento de enlace a recurso externo HTML; Elemento de metadatos HTML `<meta>`; `<script>`: The Script element; `<title>`: El elemento Título del documento; `<body>`: El elemento body del documento |
| ESPEC | Especificidad |
| func | Function |
| xyz | — |

- Cada sugerencia es un título completo que contiene una palabra que empieza por el prefijo, en cualquier posición («cad» → «… la cadena de prototipos»).
- «ESPEC» en mayúsculas devuelve «Especificidad».
- «prom» no devuelve nada: ningún título contiene una palabra que empiece por «prom». «promesa» solo aparece en el contenido.
- «elem» devolvió 5 sugerencias, el máximo configurado.

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

- Dos ejecuciones seguidas sin errores. En la segunda, los tipos y campos se reemplazan, los componentes se actualizan y no se duplican los `copyField`.
- El overlay del core de prueba solo contiene `sugerencias_es`, `ortografia_es`, `/sugerencias` y `/ortografia`. El componente `spellcheck` del configset sigue apuntando a `_text_`.
- `ri` local sin cambios: mismos campos y overlay vacío.

## Limitaciones

- Índice de prueba con 60 documentos. La validación en la aplicación final corresponde a P05-09, P08-08 y P08-09.
- No se evaluó la utilidad de las sugerencias con usuarios ni con juicios de relevancia; las tablas solo registran lo que devuelve Solr.
