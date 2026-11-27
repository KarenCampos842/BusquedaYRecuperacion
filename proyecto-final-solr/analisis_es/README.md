# Análisis del español para Solr (integrante B · Karen)

Tipos de campo, recursos lingüísticos y pruebas del analizador `text_es_proyecto`,
que el contrato P00-03 asigna a `titulo` y `contenido`. `text_es_ri` (kit) **no se
modifica**: es el control experimental.

## Tipos de campo

| Tipo | Tarea | Índice | Consulta |
|---|---|---|---|
| `text_es_ri` (kit) | control | estándar → minúsculas → plegado (conserva original) | igual |
| `text_es_stop` | P03-03 | `text_es_ri` + palabras vacías | igual |
| `text_es_stem` | P03-05 | estándar → minúsculas → plegado → `SpanishLightStem` | igual |
| `text_es_proyecto` | P00-03 | estándar → minúsculas → plegado → palabras vacías → términos protegidos → `SpanishLightStem` | igual + **sinónimos** tras el plegado |

- Palabras vacías y sinónimos son **recursos gestionados** de Solr (`ManagedStopFilterFactory`,
  `ManagedSynonymGraphFilterFactory`, nombre `es_proyecto`). Se cargan por HTTP desde
  `recursos/`, así que no hace falta copiar archivos al contenedor.
- Los términos protegidos se convierten en el atributo `pattern` de `KeywordMarkerFilterFactory`.
- Los sinónimos solo actúan en la consulta: se cambian **sin reindexar**.

## Recursos (`recursos/`)

| Archivo | Contenido |
|---|---|
| `stopwords_es.txt` | artículos, preposiciones, conjunciones, pronombres y auxiliares. Excluye `no`, `sin` y vocabulario del dominio (`estado`, `valor`, `tipo`…) y letras que son elementos HTML (`b`, `i`, `p`, `q`, `s`, `u`). |
| `protwords_es.txt` | lenguajes (JavaScript, HTML, CSS…) e identificadores que el stemmer recortaría o confundiría (`media` → `medi`, igual que «medio»). |
| `synonyms_es.txt` | grupos español ↔ inglés técnico de MDN (`promesa, promise`; `relleno, padding`…), en singular y plural porque se aplican antes del stemming. |

Se escriben con acentos; los scripts los suben en minúsculas y sin acentos.

## Uso (desde `proyecto-final-solr/`)

```bash
# Pruebas sin Solr (un solo comando)
py -m unittest discover -s analisis_es -v

# Con Solr encendido (kit/01_instalacion: docker compose up -d)
py analisis_es/verificar_linea_base.py      # P01-04 / P03-01
py analisis_es/comparar_analizadores.py     # P03-04 / P03-06 / P03-08
py analisis_es/configurar_analizadores.py   # solo los tipos, core de prueba
```

Plantillas del kit completadas (delegan en esta carpeta, no duplican lógica):
`kit/02_recuperacion_informacion/experimentos/{stopwords,stemming,sinonimos}/configurar_*.py`.

Todo se ejecuta por defecto en el core aislado **`ri_analisis_es`**, creado con
`docker exec solr-ri solr create -c ri_analisis_es -d _default`. El core `ri` solo se
**lee** (`verificar_linea_base.py`). Los scripts se pueden repetir: si un tipo o campo
ya existe se reemplaza con la definición del repositorio; `text_es_ri` nunca se reemplaza.

La comparación indexa `data/mdn/transformacion/transformacion_*/corpus_solr.json`
(P02-09, solo lectura). Resultados: `resultados/` y `../docs/resultados_comparacion_analizadores.md`.

## Integración en `ri`

**Dónde se ejecuta:** en la máquina donde corre el Solr de destino, porque el script
se conecta a `http://localhost:8983/solr` (`URL_SOLR` en `configuracion.py`). Para el
`ri` de Joseph, **Joseph lo ejecuta en su equipo**, primero en modo de prueba (sin
`--aplicar`), revisa la salida y solo después aplica. Si lo ejecuta otra persona en su
propio equipo, cambia su Solr local, no el de Joseph.

```bash
py analisis_es/aplicar_en_ri.py            # modo de prueba: estado de ri y JSON que se enviaría
py analisis_es/aplicar_en_ri.py --aplicar  # pide escribir "ri"; solo con aprobación de Karen
```

Al aplicar, en este orden:

1. **`text_es_ri` (P01-04).** Si falta en `ri`, crea **solo el tipo** con la definición
   leída del kit (`kit/.../configurar_esquema.py`, sin ejecutarlo y sin copiarla a mano).
   No se ejecuta `configurar_esquema.py` porque además crearía `titulo` y `contenido` con
   `text_es_ri`, contra el contrato P00-03 §5. Si ya existe, comprueba que sea idéntico al
   kit y no lo toca. Si es distinto, se detiene sin enviar nada.
2. **`text_es_proyecto`.** Lo agrega (o reemplaza), sincroniza los recursos `es_proyecto`
   y recarga `ri`.
3. Comprueba que `text_es_ri` quedó idéntico al kit.

Solo envía tipos de campo y recursos. **No crea ni modifica campos** (`titulo`,
`contenido`, `tema`, `vector`…) **ni documentos**. Asignar `"type": "text_es_proyecto"`
a `titulo` y `contenido` e indexar le corresponde a Joseph en su script de esquema.

## Notas de Solr 10

- La REST API de sinónimos gestionados rechaza «lista de listas»; se envía un mapa
  término → grupo completo (`recursos_gestionados.mapa_equivalencias`).
- Desde Git Bash, `docker exec` necesita `MSYS_NO_PATHCONV=1`; en PowerShell no.

## P03-09 · Cuándo y cómo reindexar

**Qué se reindexa.** `titulo` y `contenido` usan `text_es_proyecto` y están en **todos**
los documentos. Un cambio en el análisis de índice obliga a reindexar los 60 documentos
del corpus (no hay un subconjunto afectado). Los sinónimos solo actúan en la consulta.

| Cambio | ¿Reindexar? | Qué hacer |
|---|---|---|
| `synonyms_es.txt` | **No** (solo consulta) | Pasos 1 y 2. |
| `stopwords_es.txt` o `protwords_es.txt` | **Sí**: los 60 documentos | Pasos 1 a 4. |
| Filtros del `indexAnalyzer` de `text_es_proyecto` | **Sí**: los 60 documentos | Pasos 1 a 4. |
| Solo el `queryAnalyzer` | No | Pasos 1 y 2. |

**Procedimiento en `ri`** (en el equipo de Joseph, que es quien indexa: P02-11, P08-02):

1. `py analisis_es/aplicar_en_ri.py` (modo de prueba) y revisar la salida.
2. `py analisis_es/aplicar_en_ri.py --aplicar` (pide escribir `ri`): reemplaza
   `text_es_proyecto`, sincroniza los recursos `es_proyecto` y recarga `ri`.
   `text_es_ri` no se toca.
3. Si el cambio afecta al índice: Joseph vuelve a indexar los 60 documentos con su
   script de indexación completa (`indexacion/indexar_corpus_mdn.py`, PR #9), que
   sustituye cada documento por su ID.
4. Comprobar en la consulta real (no en un campo experimental):
   `py analisis_es/validar_espanol_final.py --core ri`, que usa la misma consulta que
   la API. Para la evidencia final, con `--evidencia-final` (ver abajo).

Cuando se integre P05 (PR #6): `contenido_ortografia` y `contenido_vocabulario` usan
las mismas palabras vacías, así que un cambio en `stopwords_es.txt` también obliga a
reconstruir `/sugerencias` (`suggest.buildAll=true`) y `/ortografia`
(`spellcheck.build=true`) después de reindexar.

No se reindexa `ri` desde aquí: se avisa a Joseph.

## P03-10 / P08-03 / P08-04 · Validación sobre el índice

`validar_espanol_final.py` ejecuta los casos de `consultas_validacion_final.csv`
(mayúsculas y acentos, palabras vacías, variantes morfológicas con y sin protección y
tres grupos de sinónimos: relleno, margen y arreglo) con la consulta de la API (`edismax`, `qf=titulo^4 contenido`).
Guarda tokens de índice y de consulta de `contenido`, IDs recuperados y si dos
consultas recuperan los mismos documentos. En los sinónimos compara con y sin
expansión en el mismo índice (sin expansión = `{!term}` con la forma indexada, que no
pasa por el analizador de consulta). No calcula métricas de calidad.

```bash
py analisis_es/validar_espanol_final.py --preparar-core-de-prueba  # crea e indexa ri_validacion_es
py analisis_es/validar_espanol_final.py                            # repite sobre ri_validacion_es
py analisis_es/validar_espanol_final.py --core ri                  # solo lectura; sigue siendo PRUEBA LOCAL
py analisis_es/validar_espanol_final.py --core ri --evidencia-final
```

- Sobre el core indicado **solo hace lecturas**. La única escritura es
  `--preparar-core-de-prueba`, que solo se acepta con `ri_validacion_es`.
- La salida va a `resultados/prueba_local/` con la etiqueta **PRUEBA LOCAL** salvo con
  `--evidencia-final`, que solo se acepta con `--core ri`, pide escribir
  `indice definitivo` y guarda en `resultados/evidencia_final/`.
- **La evidencia final solo vale sobre el índice definitivo: el `ri` de Joseph.** Por
  eso se ejecuta en su equipo (o juntos, con pantalla compartida). Ejecutarlo sobre otro
  `ri` local no es evidencia final.
- Guion de la demostración: `../docs/guion_demostracion_espanol.md`. Capturas de
  P09-03: `../docs/evidencias/P09-03/`.

## Juicios de relevancia (BORRADOR)

`juicios_relevancia_BORRADOR.csv` (`consulta_id,doc_id`) es una **propuesta sin
revisar** para 6 consultas de `consultas_comparacion.csv` (C03, C05, C09, C10, C13,
C15). Criterio: un documento es relevante si **trata el tema** (lo nombra el título o
le dedica una sección), no si solo lo menciona de pasada. Casos dudosos que se dejaron
fuera y Karen debe decidir:

- C05 `selectores`: `CSS/Reference` (lista de referencia con muchos selectores).
- C09 `la cadena de prototipos`: `JavaScript/Reference/Classes` (las clases se apoyan en prototipos).
- C13 `relleno`: `CSS/Reference` y `CSS/Guides/Cascade/Property_value_processing` (solo ejemplos de `padding`).
- C15 `expresión regular`: `JavaScript/Reference/Global_Objects/Symbol` (`Symbol.match`).

Mientras se llame `_BORRADOR`, **ningún script lo usa** y no se calcula ninguna
métrica. Cuando Karen lo confirme, se renombra a `juicios_relevancia.csv` y
`comparar_analizadores.py` calculará P@5 y Recall@10.
