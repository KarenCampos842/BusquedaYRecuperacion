# Guion de demostración · Español y sinonimia (P03-10)

**Duración:** unos 5 minutos. **Dónde:** Solr Admin del índice definitivo (el `ri` de
Joseph) y el buscador de la aplicación. **Antes:** ejecutar
`py analisis_es/validar_espanol_final.py --core ri --evidencia-final` en el equipo de
Joseph y tener abierta la tabla `validacion_final_ri.md` de la carpeta de la ejecución elegida en `analisis_es/resultados/evidencia_final/` (listada en `analisis_es/resultados/evidencia_final/INDICE.md`; la última línea es la más reciente).
Las cifras se leen de esa tabla en el momento; este guion no las anticipa.

**Idea central:** `titulo` y `contenido` usan `text_es_proyecto` en lugar de
`text_es_ri` (el analizador base del kit). Lo que cambió:

| `text_es_ri` (kit) | `text_es_proyecto` (proyecto) |
|---|---|
| minúsculas y plegado de acentos | igual |
| — | palabras vacías del español (`stopwords_es.txt`) |
| — | términos protegidos (`protwords_es.txt`) |
| — | raíz común en español (`SpanishLightStem`) |
| — | sinónimos español ↔ inglés de MDN, solo en la consulta (`synonyms_es.txt`) |

## 1. Mayúsculas y acentos (P08-03)

- **Qué escribir:** `FUNCION` y después `función`.
- **Dónde mirar:** Analysis de `contenido` (captura `preprocesamiento_01`) y el buscador.
- **Qué cambió y por qué:** nada respecto a `text_es_ri`; ya pasaba en la línea base y
  se conserva. Los usuarios escriben sin tildes o en mayúsculas y MDN usa tildes.
- **Qué mostrar:** caso A01 de la tabla, columna «¿Mismos docs?».

## 2. Palabras vacías (P08-03)

- **Qué escribir:** `la cadena de prototipos`.
- **Dónde mirar:** Analysis (captura `preprocesamiento_04`): `la` y `de` desaparecen.
- **Qué cambió y por qué:** con `text_es_ri` y `q.op=OR`, «la» y «de» hacían que el índice de
  prueba devolviera los 60 documentos (`docs/resultados_comparacion_analizadores.md`, C09); ahora la consulta queda en las palabras que discriminan.
- **Qué mostrar:** caso S01 (frase completa frente a `cadena prototipos`).

## 3. Variantes morfológicas (P08-03)

- **Qué escribir:** `selectores` y después `selector`.
- **Dónde mirar:** Analysis (captura `preprocesamiento_06`): ambas formas terminan en la
  misma raíz.
- **Qué cambió y por qué:** `text_es_ri` no recorta palabras; ahora plural y singular
  se buscan igual.
- **Qué mostrar:** casos M01–M03.

## 4. Términos protegidos (P08-03)

- **Qué escribir:** `media` y `medio`.
- **Dónde mirar:** Analysis (captura `preprocesamiento_07`).
- **Qué cambió y por qué:** el stemmer uniría `media` (la regla CSS `@media`) con
  `medio`. `media` está en `protwords_es.txt`, así que se conserva entera.
- **Qué mostrar:** casos P01 y P02.

## 5. Sinónimos (P08-04)

- **Qué escribir:** `relleno` y después `margen`, sin escribir `OR`.
- **Dónde mirar:** Analysis del analizador de consulta (capturas `sinonimos_01` y
  `sinonimos_04`) y el buscador de la aplicación.
- **Qué cambió y por qué:** MDN en español mezcla «relleno» con la propiedad
  `padding` (y «margen» con `margin`). La expansión ocurre solo en la consulta, así que
  cambiar sinónimos no exige reindexar.
- **Qué mostrar:** casos Y01–Y03, columnas «Sin expansión», «Con expansión» y
  «Nuevos por expansión». Abrir uno de los documentos nuevos y señalar que contiene la
  otra variante.

## Cierre

Una frase: «el índice definitivo usa `text_es_proyecto`; todo lo mostrado sale de la
consulta real de la aplicación y se puede repetir con `validar_espanol_final.py`».
No hablar de mejora de calidad hasta tener los juicios de relevancia confirmados.
