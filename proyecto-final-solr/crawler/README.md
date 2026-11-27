# Pilotos de MDN

Desde `proyecto-final-solr/`, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r crawler/requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s crawler -v
.\.venv\Scripts\python.exe -X utf8 crawler/mdn_piloto.py
```

Solo el último comando consulta MDN: primero robots.txt y después el artículo
fijo de Introducción a JavaScript, si está permitido. No recorre enlaces.
El intervalo mínimo es de tres segundos y el timeout es de veinte segundos.
Las redirecciones se validan antes de seguirlas. No hay reintentos automáticos.

Las ejecuciones nuevas guardan `documento.json` y `reporte.json` en una carpeta
única `data/mdn/ejecuciones/pagina_<fecha-UTC>_<UUID>/`, con independencia del
directorio de ejecución. El reporte registra los estados HTTP y errores.
La consola muestra título, idioma, categoría, tamaño y una vista previa.
Una ejecución fallida devuelve código 1 y guarda su reporte sin generar documento.
Los archivos de la prueba original permanecen intactos.

El selector del diseño actual es `main#content .reference-layout__body`;
también se admite `article.main-page-content`. Se conserva la atribución a
MDN; revisar las condiciones CC BY-SA y sus excepciones antes de redistribuir.
Los ejemplos de las pruebas son sintéticos y solo verifican el extractor;
el JSON del piloto procede de la descarga real.

## Ampliación controlada: objetivo inicial de sesenta documentos

```powershell
.\.venv\Scripts\python.exe -X utf8 crawler/mdn_corpus.py --corpus-previo data/mdn/corpus_piloto_v2.json --cuota-javascript 20 --cuota-html 20 --cuota-css 20 --max-indices-por-categoria 2 --max-profundidad 4 --max-solicitudes 180 --pausa 3
```

Ejecutar desde `proyecto-final-solr/`. Este comando sí accede a Internet cuando
faltan documentos; no forma parte de las pruebas locales. Sesenta es el objetivo
total, incluidos los documentos reutilizados, no sesenta descargas adicionales.

Las cuotas son independientes y configurables; cero desactiva la incorporación
de una categoría. Se usan dos colas `deque`, con BFS dentro de cada prioridad:
primero candidatos explicativos, después índices. Los índices nuevos se usan
para descubrir enlaces y se guardan como candidatos de relleno; solo se incorporan
al terminar, si quedan plazas y cupo. El límite de índices es por categoría e
incluye los reutilizados. Con el valor inicial de dos se admiten los doce de V2
(dos índices JS, uno HTML y dos CSS). Con límite cero, los índices locales sirven
para descubrimiento, pero no se incorporan al nuevo corpus.

La fuente predeterminada es `data/mdn/corpus_piloto_v2.json`, relativa al proyecto
con independencia del directorio de trabajo. Un `--corpus-previo` explícito es
relativo al directorio de ejecución. Antes de cualquier solicitud se validan el
esquema, las categorías, el idioma, las URLs, la ausencia de duplicados y ambos
hashes de todos sus documentos. Si falla, se guarda un reporte de detención.
Los documentos reutilizados se copian completos sin alterar contenido, campos,
procedencia, profundidad ni fecha de rastreo. La procedencia de la reutilización
se registra en el reporte con ruta y SHA-256 del archivo fuente.

Las URLs de todos los validados se excluyen de las descargas, incluso cuando sus
documentos no se incorporan por cuota o cupo de índices. Sus enlaces son la primera
fuente de candidatos; se mantienen las tres raíces españolas para explorar lo que
falte. Los enlaces posteriores siempre se descubren desde HTML o desde los enlaces
conservados en el corpus validado; no hay una lista fija de sesenta páginas.

Para documentos nuevos, la profundidad se mide desde las raíces y las páginas
locales validadas, consideradas nivel cero de esta ejecución. La profundidad de
los documentos reutilizados permanece como evidencia histórica. El reporte
conserva cada enlace descubierto y su página de procedencia.

Se comprueba robots.txt al inicio y su permiso para cada URL y redirección. Un
fallo de comprobación detiene todo el rastreo. Los bloqueos HTTP 401/403/429/503
y las respuestas con Retry-After también detienen el proceso sin reintentos.
La pausa configurable tiene un mínimo de tres segundos y aumenta si robots.txt
impone una frecuencia más conservadora. El límite global se comprueba antes de
cada petición, incluidos robots y cada redirección, sin excederlo ni reservar
peticiones sin usar. Agotar el presupuesto produce un resultado parcial. Si las
cuotas ya están cubiertas con documentos validados, no se consulta la red y el
reporte indica que robots no se verificó porque no hubo nuevas solicitudes.

Se eliminan fragmentos, se normalizan escapes y barra final y se rechazan consultas,
otros dominios, idiomas y rutas. Se evita volver a solicitar una URL incluso si
aparece como destino de redirección. Además se descartan contenidos repetidos por
SHA-256 del texto normalizado. No se realiza indexación.

El extractor conserva `titulo` y `titulo_original` (h1), `titulo_documento` (title)
y `titulo_descriptivo` (og:title o title, sin el sufijo MDN; si faltan, usa h1).
El texto inline conserva el espaciado del HTML, los bloques se separan por párrafos
y los ejemplos pre conservan indentación. La comprobación de idioma combina lang
con una heurística conservadora: al menos tres palabras funcionales españolas
distintas. No equivale a un detector lingüístico y puede rechazar textos breves.

Resultados de nuevas ejecuciones: `corpus.json` y `reporte.json` dentro de una
carpeta nueva `data/mdn/ejecuciones/corpus_<fecha-UTC>_<UUID>/`. Se reserva antes
del rastreo y cada archivo se crea con modo exclusivo (`x`); una colisión produce
un error, nunca sobrescribe datos. Una ejecución detenida guarda su corpus parcial
o vacío y reporte en su propia carpeta. Código de salida 0 significa cuotas completas;
1 indica resultado parcial o detención. Se preservan todos los originales y V2.

La carpeta separada identifica una ejecución, no una versión validada ni una
promoción automática del corpus. No se genera ni actualiza un alias «último corpus».

El reporte separa `reutilizados`, nuevas aceptaciones, páginas usadas solo para
descubrimiento, índices no incorporados, rechazos, errores y solicitudes HTTP.
Incluye `total_reutilizados`, `total_nuevos`, conteos y faltantes por categoría,
cupos de índices, límites efectivos y motivo de finalización. Los corpus siguen
siendo listas de documentos con el esquema JSON existente.

## Codificación y reglas de robots.txt

Los bytes HTML se decodifican estrictamente con el charset HTTP declarado o con
`utf-8-sig` cuando falta (admite UTF-8 con o sin BOM). Después BeautifulSoup recibe
Unicode; no usa autodetección de codificación ni depende de paquetes opcionales.
Un charset desconocido o bytes inválidos rechazan la página; no se reemplazan
caracteres silenciosamente. En ausencia de charset HTTP, una etiqueta meta no
cambia la decisión UTF-8 del piloto MDN. Los ejemplos sintéticos se codifican
explícitamente como UTF-8; la regresión incluye una respuesta sin meta ni charset.

`RobotsConPatrones` conserva `urllib.robotparser` para interpretar frecuencias,
y evalúa las reglas Allow/Disallow con coincidencia desde el inicio, comodín `*`
y ancla final `$`. Selecciona el grupo de User-agent más específico, combina
grupos de igual especificidad y usa `*` como alternativa. La regla de ruta más
específica gana; en empate prevalece Allow. Se normalizan escapes de caracteres
no reservados y se conservan escapes reservados, como `%2F`, sin convertirlos en `/`.

La regresión `Disallow: /*/files/` comprueba que ni una URL prohibida ni un destino
de redirección prohibido llegan al cliente HTTP. Una política inaccesible o no
interpretable con seguridad sigue deteniendo el rastreo completo. Estas pruebas
son locales y no suponen una consulta nueva a la política actual de MDN.

## Hashes, filtros y clasificación

En el corpus original, `sha256_contenido` era el hash del texto normalizado:
compactar cualquier secuencia de espacios con `re.sub(r"\s+", " ", texto)`,
aplicar `strip()` y `casefold()`, codificar UTF-8 y calcular SHA-256. Por eso no
coincide con el hash del texto almacenado. Se conserva ese archivo sin cambios.

En la versión corregida se separan los dos campos:

- `sha256_contenido`: `hashlib.sha256(doc["contenido"].encode("utf-8")).hexdigest()`.
  Incluye exactamente espacios, saltos e indentación del campo JSON decodificado;
  no es el hash del archivo JSON ni de su representación con escapes.
- `sha256_contenido_normalizado`: el cálculo anterior, usado para deduplicar.
  Ignora diferencias de mayúsculas y espacios, incluso dentro de código.

El descubrimiento, la cola y los destinos de redirección rechazan extensiones de
recursos como `.txt` (incluido `contributors.txt`), `.json`, `.pdf`, imágenes,
multimedia y archivos comprimidos. El extractor también omite enlaces con
`download` o tipo declarado distinto de HTML. Se eliminan las autorreferencias
tras normalizar barra final y fragmentos. Estos filtros detectan recursos conocidos;
una URL sin extensión aún debe superar la comprobación HTTP de Content-Type.
Los puntos de nombres como `Object.assign` siguen permitidos.

`tipo_documento` es independiente de `categoria`: las raíces JavaScript/HTML/CSS
y las rutas que terminan en `Guide`, `Guides`, `Reference` o `Tutorials` se marcan
como `indice`; las demás, como `articulo_explicativo`. Es una clasificación básica
por ruta, no una evaluación semántica ni una modificación de las cuotas.

Para derivar la versión corregida sin descargar páginas:

```powershell
.\.venv\Scripts\python.exe -X utf8 crawler/actualizar_corpus_piloto.py
```

Este comando conserva textos, fechas, URLs y categorías del original y genera
`corpus_piloto_v2.json` y `corpus_piloto_v2_ajustes.json`. El reporte de ajustes
identifica la operación local y el SHA-256 del archivo de origen; no representa
una ejecución nueva de crawling. Se niega a sobrescribir una versión v2 existente.

## P02-07: limpieza local del corpus de sesenta documentos

Desde `proyecto-final-solr/`, en PowerShell, sin acceso a Internet:

```powershell
.\.venv\Scripts\python.exe -X utf8 crawler\limpiar_corpus_mdn.py `
  --entrada data\mdn\ejecuciones\corpus_20261123T224903260669Z_b2f55364aeef4f189bdaf1e69021058e\corpus.json
```

La entrada predeterminada es ese mismo corpus; `--entrada` permite seleccionar
otro archivo local. Por defecto se exigen 60 documentos; `--esperados` permite
indicar explícitamente otra cantidad. El programa valida esquema, IDs y URLs
únicos, categorías y ambos hashes antes de producir archivos. Si encuentra una
inconsistencia o dejaría un documento vacío, se detiene sin descartar documentos
ni escribir un corpus incompleto.

Cada ejecución crea una carpeta única en:

```text
data/mdn/limpieza/limpieza_<fecha-UTC>_<UUID>/
  corpus_limpio.json
  reporte_limpieza.json
```

Opcionalmente `--salida data\mdn\limpieza\revision_manual_01` permite elegir una
carpeta NUEVA dentro del proyecto. Si ya existe, la operación falla; los archivos
se crean con modo exclusivo. No se sobrescriben corpus originales, V2 ni reportes
de rastreo. No se accede a MDN, no se llama al crawler y no se configura ni indexa
Solr. El módulo de limpieza solo utiliza la biblioteca estándar de Python.

### Regla de eliminación P02-07-v1

La inspección local encontró 34 apariciones del mismo CSS minificado de interfaz
(276 caracteres), distribuidas entre JavaScript (14), HTML (13) y CSS (7). No se
elimina CSS por selectores, por llaves ni por pertenecer a una categoría.
Se exige la secuencia completa, en párrafos separados:

1. Cabecera exacta `Compatibilidad con navegadores` o `Compatibilidad con los navegadores`.
2. Firma CSS completa `CSS_INTERFAZ`, definida en `limpiar_corpus_mdn.py`, que empieza
   por `*,:after,:before{box-sizing:border-box}` y termina en
   `#content{scroll-margin-block-start:var(--sticky-header-height)}`.
3. Aviso exacto `Activa JavaScript para ver esta tabla de compatibilidad con navegadores.`

Se retira esa sección sin datos de compatibilidad, incluido el título que quedaría
vacío y un separador vecino. No se vuelve a interpretar `contenido` como HTML.
No se normalizan globalmente espacios, saltos, indentación, idiomas o etiquetas:
se conservan ejemplos `<style>`, selectores, código JS y enlaces editoriales.
Los textos conservados quedan idénticos; limpiar de nuevo no introduce cambios.

### Esquema y trazabilidad

El corpus limpio mantiene los 60 documentos en su orden original y con las mismas
19 claves. Solo pueden cambiar `contenido`, `sha256_contenido` y
`sha256_contenido_normalizado`; ambos hashes se recalculan con las definiciones
documentadas arriba. Títulos, URLs, atribución, categoría, idioma, procedencia,
profundidad y `fecha_rastreo` se preservan. La fecha de limpieza va exclusivamente
en el reporte, no sustituye la fecha de descarga.

El reporte incluye ruta y SHA-256 del archivo original, versión de reglas,
conteos por categoría, hashes antes/después, caracteres y texto exacto eliminado
con offsets en el contenido ORIGINAL (índices de caracteres Unicode). Las
advertencias indican contexto y posición en el texto LIMPIO. Si dos documentos
quedaran duplicados tras limpiar, se señalan en el resumen; no se borran para
mantener la evidencia y la cantidad de documentos.

### Casos conservados para revisión manual

Las firmas incompletas o sin contexto no se eliminan. Se reportan avisos de
compatibilidad aislados, variantes con `--sticky-header-height`, resúmenes
`CSS Key Concepts:`, avisos `¡Estamos en obras!` y taxonomías históricas como
`interwiki links` e `Interwiki Languages`. No se puede inferir con certeza si
son navegación, explicación o contenido editorial a partir del texto plano.
La lista de detectores no es exhaustiva: otras variantes de interfaz se conservan.
Si un artículo citase literalmente la secuencia completa de la regla, requeriría
revisión; no disponemos del DOM original para distinguir esa cita del componente.

### Pruebas y resultado local

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s crawler -v
```

La batería completa incluye filtros, robots, persistencia, ampliación y limpieza.
Las regresiones de limpieza comprueban límites de bloques, variantes ambiguas,
preservación de ejemplos reales CSS/HTML/JS, idempotencia, hashes, esquema, orden,
persistencia exclusiva y validación de los 60 documentos de entrada.

Resultado de P02-07: 55 pruebas correctas, ejecutadas con conexiones bloqueadas
y cero intentos de conexión. La copia generada modificó 34 documentos y dejó 26
sin cambios, eliminó 34 bloques (13 060 caracteres), conservó las cuotas 20/20/20
y no produjo duplicados normalizados. Hay 12 advertencias en 10 documentos:
7 resúmenes en inglés, 2 avisos antiguos y 3 marcas de taxonomía.

Salida generada en esta revisión:
`data/mdn/limpieza/limpieza_20261125T041126771671Z_baee495b391749e5b8d409724c26be31/`.
Es una copia derivada para revisión; no se declara aprobada ni se ha indexado.

## P02-09: transformación local al contrato Solr

Referencia vigente: [P00-03 v1.2](../docs/P00-03_contrato_solr_v1.2.md),
secciones 2, 3 y 6.1, ratificado por Karen y Carlos. El transformador valida
contra v1.2; los reportes históricos conservan la versión utilizada al generarse.

Desde `proyecto-final-solr/`, en PowerShell:

```powershell
.\.venv\Scripts\python.exe -X utf8 crawler\transformar_corpus_mdn.py
```

La entrada predeterminada es exclusivamente la limpieza validada de P02-07:
`data/mdn/limpieza/limpieza_20261125T043642044138Z_c21372d7d7c14eaa9055b2593fd866be/corpus_limpio.json`.
`--entrada <archivo>` selecciona otra copia local, con las mismas exigencias.
No hay opción para relajar las cuotas: se requieren exactamente 60 documentos,
20 de JavaScript, 20 de HTML y 20 de CSS, con IDs únicos. No se descarga nada ni
se configura o contacta Solr. Se reutilizan únicamente las funciones locales de
URL del crawler y hashes de limpieza; se mantienen las dependencias existentes
de `crawler/requirements.txt`.

Cada ejecución crea una carpeta nueva con fecha UTC y UUID:

```text
data/mdn/transformacion/transformacion_<fecha-UTC>_<UUID>/
  corpus_solr.json
  metadatos_crawler.json
  reporte_transformacion.json
```

También se puede elegir una carpeta NUEVA mediante
`--salida data\mdn\transformacion\revision_01`. La carpeta debe estar dentro del
proyecto, incluso al invocar la función Python. Nunca se reutiliza una carpeta
existente ni se sobrescriben el corpus de entrada o reportes anteriores.

### Campos mínimos y metadatos opcionales

Por defecto, `corpus_solr.json` es un arreglo de objetos con exactamente los
ocho campos web obligatorios de P00-03: `id`, `titulo`, `contenido`, `categoria`,
`tipo_fuente`, `fuente`, `idioma` y `url`. Se preservan sus valores y el orden de
los documentos sin recortar, limpiar ni volver a normalizar textos o IDs.
Se exige `idioma="es"`, `tipo_fuente="web"`, `fuente="MDN Web Docs"`, URL MDN
canónica dentro del alcance del crawler, `id=url` y categoría coherente con la
ruta. Se rechazan cadenas obligatorias vacías, IDs repetidos y campos ajenos al
contrato, incluidos `score`, `snippet`, `tema`, `titulo_web` y `contenido_web`.

`metadatos_crawler.json` contiene un arreglo asociado por `id`, en el mismo orden,
con los opcionales autorizados presentes y válidos. Esta separación permite
preparar el JSON mínimo mientras se concretan los tipos opcionales del esquema.
Este archivo auxiliar **no es otro lote para enviar a Solr**. No convierte
`tipo_documento` ni otros metadatos en facetas; las facetas siguen siendo
`categoria` y `tipo_fuente`.

Para preparar un lote que incluya también los opcionales autorizados:

```powershell
.\.venv\Scripts\python.exe -X utf8 crawler\transformar_corpus_mdn.py --incluir-metadatos
```

Esa opción requiere que posteriormente se definan los campos opcionales en el
esquema antes de indexar. Siempre se genera también la copia auxiliar. Los
opcionales ausentes o `null` se omiten, incluidas las tres semillas sin
`descubierta_desde`; no se inventan valores. Si están presentes se validan:

- `fecha_rastreo`: ISO 8601 con hora y zona explícita, convertida a UTC
  `YYYY-MM-DDTHH:mm:ss.SSSZ`. Se truncan las fracciones inferiores al milisegundo
  para la precisión de `pdate`; el reporte conserva la fecha original y la
  transformada. No se sustituye por la fecha de ejecución.
- `enlaces_salientes`: arreglo de URLs MDN normalizadas; se conservan valores y
  orden, incluso el arreglo vacío. `descubierta_desde` también se valida como URL.
- `profundidad`: entero no negativo en rango de `pint`, excluyendo booleanos.
  `pagerank`: número finito no negativo, si existe; no se calcula.
- Atribución, títulos editoriales y tipo de documento: cadenas; para el corpus
  actual se admiten los tipos `indice` y `articulo_explicativo` del crawler.
  Ambos SHA-256 deben corresponder al contenido limpio si están presentes.

### Reporte, fallos y reproducibilidad

El reporte registra estado, reglas, ruta y SHA-256 del contrato y de la entrada,
cuotas, IDs únicos, campos permitidos, modo de metadatos y comprobaciones por
documento. Registra la preservación exacta de ID/título/contenido, longitud y hash
del contenido, fecha antes/después y cantidad de enlaces. Al finalizar vuelve a
comprobar los bytes de entrada y calcula el SHA-256 del archivo de salida.

Si hay un documento inválido se rechaza **todo el lote**, con código de salida 1:
solo se escribe `reporte_transformacion.json` con `estado="rechazado"`, motivos e
índices (desde cero). No se produce un corpus parcial de documentos válidos.
Una entrada inexistente o una carpeta ya existente falla sin alterar archivos.
Un fallo de escritura puede dejar archivos incompletos: únicamente una ejecución
con reporte `estado="exitoso"` y hash de salida coincidente es válida.

Los mismos bytes de entrada y opciones generan los mismos bytes de
`corpus_solr.json` y `metadatos_crawler.json`. Las carpetas, fecha de ejecución y
rutas/hash de evidencia del reporte identifican cada ejecución; no se espera que
los reportes de ejecuciones distintas sean idénticos.

Pruebas específicas y batería completa, respectivamente:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s crawler -p test_transformacion_mdn.py -v
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s crawler -v
```

Las pruebas usan el corpus limpio real y casos inválidos. Comprueban las cuotas,
preservación exacta y ausencia de mutación, campos mínimos/opcionales, fechas con
distintas zonas, enlaces multivaluados, rechazo integral, CLI, persistencia del
reporte y reproducción byte a byte en dos ejecuciones. Las pruebas existentes
del crawler usan clientes simulados; no requieren consultas a Internet.

Resultado verificado de P02-09: **60 documentos, 60 IDs únicos, reparto 20/20/20**,
66 pruebas aprobadas (55 existentes y 11 nuevas), con `socket.socket.connect`
bloqueado y cero intentos de conexión. La ejecución conservada es:

`data/mdn/transformacion/transformacion_20261126T061527349966Z_68284317199543fbb7b8f960224db1d0/`.

La comprobación independiente de esa ejecución se guardó en
`verificacion_reproducibilidad.json`: compara los ocho campos obligatorios de
los 60 documentos con la entrada, valida cuotas y hashes y verifica que una
segunda ejecución temporal produzca corpus y metadatos idénticos byte a byte.
La entrada mantiene SHA-256
`c318361a13acdbbdc0886c91c1209d1123c1dd89147c63a19ef588806d196483`;
el archivo `corpus_solr.json` generado tiene SHA-256
`8d9aa15d1239c92b84c9e9009444781bc201f04489a75ddc28f13ca3fdf4ab11`.
Estos resultados acreditan la transformación de datos a P00-03; la definición
del esquema real y su validación mediante indexación pertenecen a tareas posteriores.
