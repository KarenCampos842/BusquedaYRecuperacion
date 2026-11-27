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

No se reindexa `ri` desde aquí: se avisa a Joseph, que es quien indexa (P02-11, P08-02).

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
  `--evidencia-final`, que solo se acepta con `--core ri` y pide escribir `indice definitivo`.
  La prueba local **se sobrescribe** en cada ejecución.
- Con `--evidencia-final`, antes de ejecutar los casos, se comprueba que el índice tiene los
  **60 documentos MDN aprobados**:
  - los IDs de `corpus_solr.json`, consultados por ID;
  - cada uno con su categoría y `tipo_fuente=web`;
  - 20/20/20 por categoría.
  Si falta algo, el script se detiene sin escribir nada y lista IDs faltantes, categorías
  o `tipo_fuente` incorrectos y conteos. **No exige 60 documentos en total**: los
  documentos adicionales (por ejemplo, los PDF) no provocan rechazo.
- Cada ejecución de evidencia final se guarda en una **carpeta nueva** con fecha y hora
  UTC, `resultados/evidencia_final/<AAAA-MM-DDTHHMMSSZ>_ri/`, y nunca sobrescribe: si la
  carpeta existe, se detiene. Además añade una línea (fecha, core, documentos, carpeta) a
  `resultados/evidencia_final/INDICE.md`, que solo crece. Para la entrega se usa la
  carpeta de la ejecución elegida (normalmente la última del índice).
- **La evidencia final solo vale sobre el índice definitivo: el `ri` de Joseph.** Por
  eso se ejecuta en su equipo (o juntos, con pantalla compartida). Ejecutarlo sobre otro
  `ri` local no es evidencia final.
- Guion de la demostración: `../docs/guion_demostracion_espanol.md`. Capturas de
  P09-03: `../docs/evidencias/P09-03/`.

## Juicios de relevancia

`juicios_relevancia.csv` (`consulta_id,doc_id`, 20 juicios) fue **revisado y confirmado
por Karen**. `comparar_analizadores.py` lo lee automáticamente y calcula P@5 y
Recall@10 para estas consultas.

**Criterio:** un documento es relevante si contiene información directa sobre el tema
consultado, aunque no sea su tema único.

| Consulta | Texto | Documentos relevantes |
|---|---|---|
| C03 | `arreglos` | 3 |
| C05 | `selectores` | 7 |
| C09 | `la cadena de prototipos` | 4 |
| C10 | `el modelo de caja` | 2 |
| C13 | `relleno` | 2 |
| C15 | `expresión regular` | 2 |

**Casos dudosos y decisión** (`CSS/Reference` se decidió por separado en C05 y en C13):

| Consulta | Documento | Decisión |
|---|---|---|
| C05 `selectores` | `CSS/Reference` | Incluido |
| C09 `la cadena de prototipos` | `JavaScript/Reference/Classes` | Incluido |
| C13 `relleno` | `CSS/Reference` | Excluido |
| C13 `relleno` | `CSS/Guides/Cascade/Property_value_processing` | Excluido |
| C15 `expresión regular` | `JavaScript/Reference/Global_Objects/Symbol` | Excluido |

Las demás consultas de `consultas_comparacion.csv` no tienen juicios: para ellas no se
calcula ninguna métrica.

## P05 · Autocompletado y corrección ortográfica

### Estrategia (P05-01)

| Función | Componente | Fuente | Handler |
|---|---|---|---|
| Autocompletado: títulos | `SuggestComponent` `sugerencias_es`, diccionario `titulos_es` (`AnalyzingInfixLookupFactory` + `DocumentDictionaryFactory`) | `titulo_sugerencia` (`copyField` de `titulo`; minúsculas y sin acentos, sin stemming) | `/sugerencias` |
| Autocompletado: términos | mismo componente, diccionario `terminos_es` (`AnalyzingLookupFactory` + `HighFrequencyDictionaryFactory`) | `contenido_vocabulario` (`copyField` de `contenido`; minúsculas y palabras vacías, **sin stemming ni plegado**; descarta tokens de menos de 3 letras y los que tienen números o símbolos) | `/sugerencias` |
| Corrección | `SpellCheckComponent` `ortografia_es`, diccionario `contenido_es` (`DirectSolrSpellChecker`) | `contenido_ortografia` (`copyField` de `contenido`; minúsculas y palabras vacías, **sin stemming ni plegado**) | `/ortografia` |

- Son nombres nuevos: no se tocan `spellcheck` ni `/spell` del configset. Se crean con la Config API, que los guarda en `configoverlay.json` del core sin editar `solrconfig.xml`.
- Autocompletado: `/sugerencias` consulta los dos diccionarios a la vez (5 sugerencias por diccionario, mínimo 3 letras, contrato P00-04).
  - `terminos_es`: palabras del contenido que empiezan por el prefijo, ordenadas por número de documentos que las contienen (`prom` → promedio, promesa, promesas, prompt). Conserva nombres de API con punto (`function.length`).
  - `titulos_es`: títulos completos que contienen una palabra que empieza por el prefijo.
  - En ambos, el prefijo se compara sin distinguir acentos ni mayúsculas.
  - El vocabulario es de palabras sueltas: ejemplos del contrato P00-04 como «promise.all» o «promesa en javascript» no son reproducibles con este corpus («promise.all» no aparece y no hay diccionario de frases).
- Corrección: sugiere palabras con acentos (`fucion` → `función`) y una consulta completa (`collate`).

### Uso (desde `proyecto-final-solr/`)

```bash
py analisis_es/probar_sugerencias_ortografia.py                          # core aislado ri_sugerencias_es + prueba
py analisis_es/configurar_sugerencias_ortografia.py --core ri            # modo de prueba en ri: solo muestra
py analisis_es/configurar_sugerencias_ortografia.py --core ri --aplicar  # pide escribir "ri"
py analisis_es/configurar_sugerencias_ortografia.py --reemplazar         # solo ri_sugerencias_es
```

En `ri` se ejecuta en la máquina del Solr de destino (Joseph, en su equipo), **después** de `aplicar_en_ri.py`: usa los recursos `es_proyecto`. Además exige que existan `titulo` y `contenido`, porque no los crea.

**Revisión previa, sin escrituras.** Antes de enviar nada, el script revisa en modo de solo lectura los 3 tipos, los 3 campos auxiliares y las reglas `copyField`, y clasifica cada elemento:

- **Falta:** se crea.
- **Existe y es compatible:** no se toca.
- **Existe y es incompatible:** el script se detiene, muestra las diferencias y **no envía ninguna petición**, tampoco a la Config API.

Criterios, los mismos que `validar_p05()` en `indexacion/configurar_esquema.py` de Joseph:

- **Tipos:** misma `class` y los mismos analizadores de índice y de consulta.
- **Campos:** `type`, `indexed`, `stored`, y `required`, `multiValued` y `docValues` en `false`. Si Solr omite un booleano, cuenta como `false`. Un `default` es incompatible.
- **`copyField`:** solo las 3 reglas autorizadas (`titulo→titulo_sugerencia`, `contenido→contenido_ortografia`, `contenido→contenido_vocabulario`), sin duplicados ni propiedades extra. `maxChars` debe faltar o ser el entero `0` (sin límite); cualquier otro valor, incluido `"0"` como texto, detiene el script. También lo detiene una regla no autorizada que escriba en un campo auxiliar.

En modo de prueba (`--core ri` sin `--aplicar`) se muestra esta misma revisión.

**`--reemplazar`** sustituye lo incompatible (tipos, campos y `copyField` con `maxChars`) y **solo se acepta con el core de prueba `ri_sugerencias_es`**. Está apagado por defecto. Con cualquier otro core (`ri`, `ri_analisis_es` o un nombre desconocido) se rechaza sin leer ni modificar ese core: lo rechaza argparse antes de conectarse a Solr y también `configurar()` si se llama desde código. Las reglas duplicadas o no autorizadas detienen el script incluso con `--reemplazar`.

### Vocabulario y reconstrucción del diccionario (P05-02, P05-03)

- El vocabulario sale de los documentos indexados (60 MDN; después, también los PDF): títulos (`titulo_sugerencia`) y palabras del contenido (`contenido_vocabulario`). No hay archivo aparte.
- `buildOnCommit=true`: los dos diccionarios se reconstruyen en cada `commit`. Para reconstruirlos a mano: `GET /solr/<core>/sugerencias?suggest.buildAll=true`.
- `HighFrequencyDictionaryFactory` no lleva `threshold`: la Config API lo guarda como texto y Solr 10 falla al construir (`ClassCastException`). Sin él incluye todos los términos (umbral 0).
- El corrector (`DirectSolrSpellChecker`) lee el índice directamente: no necesita reconstrucción.

### Para Carlos (P05-04, P05-07)

- Sugerencias: `GET /solr/ri/sugerencias?suggest.q=<prefijo>&suggest.count=<n>`. La respuesta trae un bloque por diccionario:

  ```json
  {"suggest": {
     "terminos_es": {"prom": {"numFound": 4, "suggestions": [
         {"term": "promedio", "weight": 1, "payload": ""},
         {"term": "promesa",  "weight": 1, "payload": ""}, "..."]}},
     "titulos_es":  {"prom": {"numFound": 0, "suggestions": []}}}}
  ```

  `term` es el texto que se muestra y `weight` es el número de documentos en `terminos_es`. `suggest.count` se aplica a cada diccionario por separado. Para convertirlo al formato del contrato, una propuesta: tomar primero los `term` de `terminos_es` y después los de `titulos_es`, quitar duplicados sin distinguir mayúsculas ni acentos y recortar al `limit` (5 por defecto, máx. 8).
- Corrección: `GET /solr/ri/ortografia?q=<consulta>&json.nl=map` → `spellcheck.correctlySpelled`, `spellcheck.suggestions.<término>.suggestion[].word` y `spellcheck.collations` (consulta sugerida).
