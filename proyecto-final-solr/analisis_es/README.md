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

```bash
py analisis_es/aplicar_en_ri.py            # modo de prueba: estado de ri y JSON que se enviaría
py analisis_es/aplicar_en_ri.py --aplicar  # pide escribir "ri"; solo con aprobación de Karen
```

Agrega solo el tipo `text_es_proyecto` y los recursos `es_proyecto`, recarga `ri` y
comprueba que `text_es_ri` sigue idéntico al kit. No toca campos ni documentos: los
campos `titulo` y `contenido` los cambia Joseph a `"type": "text_es_proyecto"` en su
script de esquema (cambiar el tipo de un campo exige vaciar y reindexar).

Estado de `ri` al 26-nov-2026: tiene el esquema del kit (`titulo`/`contenido` con
`text_es_ri`, `tema`, `vector`) y **30 documentos didácticos** (D01…), no los de MDN.

## Notas de Solr 10

- La REST API de sinónimos gestionados rechaza «lista de listas»; se envía un mapa
  término → grupo completo (`recursos_gestionados.mapa_equivalencias`).
- Desde Git Bash, `docker exec` necesita `MSYS_NO_PATHCONV=1`; en PowerShell no.

## P03-09 · Cuándo reindexar

| Cambio | ¿Reindexar `titulo`/`contenido`? | Qué hacer |
|---|---|---|
| `synonyms_es.txt` | **No** (solo consulta) | Repetir `configurar_analizadores.py --core ri --tipos text_es_proyecto` (sincroniza y recarga). |
| `stopwords_es.txt` o `protwords_es.txt` | **Sí** (afectan el índice) | Repetir el script anterior y pedir a Joseph que vuelva a indexar los documentos. |
| Filtros del `indexAnalyzer` de `text_es_proyecto` | **Sí** | Igual que el caso anterior. |
| Solo el `queryAnalyzer` | No | Repetir el script. |

No se reindexa `ri` desde aquí: se avisa a Joseph, que es quien indexa (P02-11, P08-02).
