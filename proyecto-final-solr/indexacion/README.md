# P01-05: esquema y piloto MDN en `ri`

Implementación del contrato [P00-03 v1.2](../docs/P00-03_contrato_solr_v1.2.md).
P00-03 v1.2 ya fue ratificado por Karen y Carlos, según la confirmación del equipo.
Se indexaron **tres documentos**, uno por categoría, en `http://localhost:8983/solr/ri`.
La carga de 60 documentos corresponde a P02-11 y no está implementada aquí.

## Requisitos y ejecución

Ejecutar PowerShell desde la raíz del repositorio, con Solr iniciado y los tipos
`text_es_ri` y `text_es_proyecto` ya configurados por el trabajo de Karen.
Usar el entorno existente `proyecto-final-solr/.venv`; la reutilización del
validador del crawler requiere `beautifulsoup4` de `crawler/requirements.txt`.
En un entorno nuevo, instalar esas dependencias en su entorno virtual.
Ninguno de estos scripts descarga páginas MDN.

```powershell
$py = '.\proyecto-final-solr\.venv\Scripts\python.exe'

# Inspección, sin modificar Solr:
& $py proyecto-final-solr/indexacion/configurar_esquema.py

# Elegir nombres NUEVOS para conservar las evidencias de cada ejecución:
& $py proyecto-final-solr/indexacion/configurar_esquema.py --aplicar --evidencia proyecto-final-solr/indexacion/evidencias/reproduccion/esquema.json

# Valida los 60 documentos y muestra únicamente la selección de tres:
& $py proyecto-final-solr/indexacion/indexar_piloto.py

# Envía SOLO los tres seleccionados y después un commit con waitSearcher=true:
& $py proyecto-final-solr/indexacion/indexar_piloto.py --aplicar --salida proyecto-final-solr/indexacion/evidencias/reproduccion/piloto

# Pruebas locales, sin conexión a Solr (la integración aparece omitida):
& $py -m unittest discover -s proyecto-final-solr/indexacion -v

# Integración real de solo lectura contra el piloto de tres documentos en ri:
$env:P01_05_SOLR_INTEGRACION = '1'
& $py -m unittest discover -s proyecto-final-solr/indexacion -v
Remove-Item Env:P01_05_SOLR_INTEGRACION

# Regresiones de los componentes reutilizados:
& $py -m unittest discover -s proyecto-final-solr/crawler -p test_transformacion_mdn.py -v
& $py -m unittest discover -s proyecto-final-solr/analisis_es -v
```

El destino es fijo: core `ri` del cliente HTTP existente de `analisis_es/solr_cliente.py`.
No se modifica el código de Karen. No ejecutar el configurador del kit para esta
operación: intenta crear tipos y asigna `text_es_ri` a los campos de texto,
además de introducir campos ajenos a este alcance.

## Comportamiento y protecciones

`configurar_esquema.py` consulta los campos con sus propiedades efectivas
(`showDefaults=true`), los tipos, `uniqueKey` y las reglas `copyField`.
Comprueba todo antes de agregar campos; una discrepancia de tipo, cardinalidad,
obligatoriedad, almacenamiento, indexación o `docValues` de las facetas detiene
la operación. También rechaza campos obligatorios ajenos, valores predeterminados
en campos del contrato y reglas `copyField` no autorizadas. Nunca envía
`replace-field`, `delete-field` ni operaciones sobre tipos.

### Compatibilidad con P05 (PR #6)

Se revisaron las definiciones de `origin/feat/autocompletado-ortografia`, commit
`671ae7d`, sin fusionar sus archivos. Se admite cualquier subconjunto de estas
reglas, incluida su ausencia total:

| Origen | Destino | Tipo del destino | stored | indexed |
|---|---|---|---|---|
| `titulo` | `titulo_sugerencia` | `text_sugerencia_es` | true | true |
| `contenido` | `contenido_ortografia` | `text_ortografia_es` | false | true |
| `contenido` | `contenido_vocabulario` | `text_vocabulario_es` | false | true |

Los auxiliares son opcionales, de un valor, sin `docValues` ni `default`. Si
existen se validan aun sin reglas de copia y su tipo debe existir. Se usan las
propiedades efectivas de `showDefaults=true`; `required`, `multiValued` y
`docValues` omitidos se interpretan como false. Una regla necesita un destino
explícito compatible; no basta un campo dinámico. Se rechazan reglas ajenas,
comodines, copias inversas, duplicadas, propiedades adicionales y truncamientos
(`maxChars` solo puede faltar o ser el entero 0, copia ilimitada).

P01-05 **no crea ni modifica** auxiliares, reglas, tipos ni componentes P05.
Solo agrega los campos faltantes del contrato principal. La repetición sobre un
esquema completo compatible no envía escrituras. Esta validación no certifica
los analizadores auxiliares ni el funcionamiento de Suggester/SpellCheck.

Observaciones para revisar antes de integrar la PR #6:

- En la revisión histórica de P01-05, su configurador usaba `agregar_o_reemplazar`
  y reemplazaba tipos y campos auxiliares existentes sin comparar compatibilidad
  ni guardar una instantánea previa. Karen corrigió este problema en su
  actualización posterior de la PR #6.
- En esa revisión, la detección de copias existentes comparaba solo origen/destino
  y conservaba una copia con `maxChars` incompatible. Karen también corrigió
  este problema en su actualización posterior de la PR #6. P01-05 mantiene la
  comprobación de compatibilidad y detiene la operación ante una copia incompatible.
- Agregar `copyField` no rellena retroactivamente los auxiliares de los tres
  documentos existentes. La validación funcional con esos documentos requiere
  acordar después una actualización por ID y construcción de diccionarios.
  No ejecutar cargas o reindexaciones durante esta preparación.
- Las evidencias de Karen corresponden a `ri_sugerencias_es` con 60 documentos;
  no demuestran integración funcional sobre el piloto de `ri`. El script
  `probar_sugerencias_ortografia.py` carga esos 60 documentos en el core de prueba;
  no forma parte de las verificaciones de esta adaptación.
- La cabecera de su configurador enumera dos tipos y dos auxiliares aunque las
  definiciones actuales incluyen también `text_vocabulario_es` y
  `contenido_vocabulario`.

Las pruebas locales cubren los 27 estados de ausencia/campo/campo con copia de
los tres auxiliares, con contrato principal parcial y completo, idempotencia,
ausencia de mutaciones y rechazo previo a toda escritura. La integración
optativa del bloque anterior solo consulta esquema, análisis, documentos,
búsquedas y facetas; no construye diccionarios ni modifica Solr.

Verificación de esta adaptación (26-nov-2026), en
`fix/compatibilidad-copyfield-p05`: **19 pruebas P01-05** con
`P01_05_SOLR_INTEGRACION=1`, **66 del crawler** (incluidas las 11 de
transformación) y **39 de análisis español**, todas correctas, sin omisiones.
El configurador sin `--aplicar` informó cero campos pendientes y tipos
protegidos intactos. La integración verificó los tres documentos, sus datos,
búsquedas y facetas. `ri` no tiene todavía auxiliares ni copias P05; la
compatibilidad parcial y completa de P05 se comprobó con estados simulados.
`git diff --check` pasó. No se aplicó configuración, no se reindexaron documentos
ni se cargaron los 60; tampoco se modificaron los analizadores.

Define 20 campos contando `id`, ya existente; en esta ejecución agregó 19.
`titulo` y `contenido` usan `text_es_proyecto`. Los siete campos comunes son
obligatorios en Solr; `url` se exige en el validador web y queda opcional en Solr
para admitir PDF. Las dos facetas usan `string`, `stored=true`, `indexed=true`,
`docValues=true` y un solo valor.

Los metadatos opcionales se concretan así: `atribucion`, procedencia, títulos
editoriales y hashes usan `string`; `profundidad` usa `pint`; `fecha_rastreo`
usa `pdate`; `enlaces_salientes` usa `strings` multivaluado; `pagerank` usa
`pdouble`. Todos se almacenan e indexan y ninguno es obligatorio. No se crean
`score`, `snippet`, `tema`, campos duplicados de texto ni campos futuros de
Suggester/SpellCheck.

Se comprueba mediante Analysis API que el análisis de índice y consulta elimina
“la”, normaliza “Programación” y conserva los términos JavaScript, HTML y CSS.
Los tipos protegidos se comparan antes y después, sin redefinirlos. El modo
`--aplicar` exige una ruta de evidencia nueva y guarda el esquema previo antes
de enviar el lote de campos. El resultado posterior se guarda por separado.
Repetir la configuración compatible produce cero campos nuevos.

`indexar_piloto.py` fija por defecto el artefacto validado de P02-09:
`data/mdn/transformacion/transformacion_20261126T061527349966Z_68284317199543fbb7b8f960224db1d0/corpus_solr.json`.
Comprueba el reporte exitoso y su SHA-256, y reutiliza la validación completa de
60 IDs únicos y cuotas 20/20/20. Rechaza datos que necesitarían reparación.
No genera una nueva transformación ni altera los archivos de origen.

Selecciona la URL lexicográficamente menor de cada categoría, en orden
JavaScript, HTML, CSS. El resultado no depende del orden del corpus. Envía esos
tres objetos originales sin añadir los metadatos separados. La prueba adicional
valida localmente los 60 documentos combinados con `metadatos_crawler.json` y
comprueba que todos sus campos tienen definición, sin indexarlos.

El core debe estar vacío o contener exactamente los tres IDs elegidos con los
mismos valores del corpus. Cualquier documento ajeno, lote parcial o diferencia
de datos detiene la escritura. Las repeticiones usan los mismos IDs y no generan
duplicados. No hay comandos de borrado ni gestión de Docker. Ejecutar sin otros
procesos escribiendo en `ri`: la comprobación previa y el update no constituyen
una transacción ni un bloqueo distribuido. Si falla Solr durante una escritura,
inspeccionar el estado y las evidencias; el script no borra ni repara el índice.

## Resultado observado y evidencias

Ejecución del 26 de noviembre de 2026 en la rama
`feat/p01-05-indexacion-piloto`, creada desde `main`.

| Categoría | Título preservado | ID / URL |
|---|---|---|
| JavaScript | JavaScript | `https://developer.mozilla.org/es/docs/Web/JavaScript` |
| HTML | HTML: Lenguaje de Marcado de Hipertexto | `https://developer.mozilla.org/es/docs/Web/HTML` |
| CSS | CSS | `https://developer.mozilla.org/es/docs/Web/CSS` |

- Recuento antes: **0**. Recuento posterior al commit: **3**, con **3 IDs únicos**.
- Preservación exacta de todos los campos enviados, incluidos título, contenido, URL y categoría.
- Seis consultas `edismax`: una por título y una por las primeras 50 palabras de contenido de cada documento. Cada consulta recupera su ID esperado; sus parámetros y respuestas están en el JSON de evidencias.
- Tres filtros `fq= categoria:"..."`: un resultado correcto por categoría.
- Facetas: `JavaScript=1`, `HTML=1`, `CSS=1`; `tipo_fuente: web=3`.
- Corpus validado localmente: 60 documentos, cuotas 20/20/20; corpus y tipos de español intactos.
- Configuración posterior de solo lectura: ningún campo pendiente de crear.

Archivos de evidencia, conservados bajo [evidencias/p01-05](evidencias/p01-05/):

- [Esquema previo y análisis](evidencias/p01-05/esquema_previo.json) y [resultado posterior](evidencias/p01-05/esquema_previo.json.resultado.json).
- [Comprobación de idempotencia](evidencias/p01-05/idempotencia.json.resultado.json).
- [Selección exacta enviada](evidencias/p01-05/piloto/piloto.json), [preparación](evidencias/p01-05/piloto/preparacion.json) y [respuestas de commit, búsquedas, facetas y recuentos](evidencias/p01-05/piloto/evidencias.json).
- [13 pruebas P01-05, incluida integración real](evidencias/p01-05/pruebas_p01_05.txt), [11 de transformación](evidencias/p01-05/pruebas_transformacion.txt) y [39 de análisis español](evidencias/p01-05/pruebas_analisis_es.txt): **63 exitosas**, sin omisiones en la ejecución final, códigos de salida 0.

SHA-256 del corpus antes y después:
`8d9aa15d1239c92b84c9e9009444781bc201f04489a75ddc28f13ca3fdf4ab11`.

## Comandos ejecutados y ajustes durante la implementación

Se inspeccionaron el contrato v1.2, el transformador, las pruebas, el cliente HTTP,
los scripts del kit y los de Karen. Se consultaron `/schema`, `/schema/fields`,
`/analysis/field` y `/select` mediante `Invoke-RestMethod` y el cliente Python.
Se usaron `git status --short`, `git branch --show-current`, `git diff --check`,
`rg --files` y `git switch -c feat/p01-05-indexacion-piloto`. La creación de la rama
requirió autorización del entorno para escribir la referencia en `.git`.

Los comandos funcionales ejecutados son los del bloque de reproducción, usando
en su ejecución original las rutas `evidencias/p01-05/esquema_previo.json`,
`evidencias/p01-05/piloto` e `evidencias/p01-05/idempotencia.json` (esta última
para la comprobación posterior sin `--aplicar`). Las tres suites se ejecutaron
con `unittest discover`; sus registros finales contienen códigos de salida.

Incidencias resueltas:

1. El Python global no tenía `bs4`; se utilizó el entorno `.venv` existente.
2. El transformador referenciaba un contrato v1.1 eliminado. Se actualizó **solo
   esa constante** a v1.2 para reutilizar sus validadores. Las 11 pruebas del
   transformador pasaron. Los resultados históricos de transformación mantienen
   su referencia original a v1.1; no se editaron.
3. La primera petición de esquema usó una lista en la raíz y Solr la rechazó
   antes de aplicar campos. Se corrigió a `{"add-field": [...]}`. El archivo
   `esquema_antes.json` conserva la preparación de ese intento; el resultado
   exitoso corresponde a `esquema_previo.json.resultado.json`.
4. PowerShell interpretó la salida normal de `unittest` por stderr como error
   al canalizarla con `Tee-Object`. Los registros finales se capturaron con
   `subprocess.run`, combinando stdout/stderr y comprobando el código real de
   cada proceso: 0 en las tres suites.

## P02-11: indexación completa preparada, carga real pendiente

`indexar_corpus_mdn.py` valida los 60 documentos de la transformación aprobada
P02-09 y sus metadatos separados. Reutiliza `cargar_corpus`, `transformar_corpus`
y `planificar`; no mantiene otro contrato de validación. Comprueba el reporte
exitoso, el SHA-256 del corpus, 60 IDs únicos y cuotas 20/20/20. Asocia metadatos
por ID con correspondencia exacta, sin campos ajenos ni conflictos. Rechaza fechas
que requieran una nueva conversión: la transformación aprobada ya usa UTC Z con
milisegundos. No cambia ningún artefacto del corpus.

El reporte histórico de transformación referencia P00-03 v1.1. Se conserva como
evidencia original; los documentos se vuelven a validar con las reglas vigentes
y se registra el hash del contrato v1.2, del corpus, de los metadatos y del reporte.
El reporte P02-09 no incluía un hash de metadatos: se valida su contenido y se
registra el hash leído, sin atribuirle una firma de aprobación inexistente.

Desde `proyecto-final-solr/`, en PowerShell:

```powershell
# Predeterminado: solo validar e inspeccionar, sin POST ni commit.
.\.venv\Scripts\python.exe indexacion/indexar_corpus_mdn.py

# Evidencias en una carpeta nueva elegida explícitamente.
.\.venv\Scripts\python.exe indexacion/indexar_corpus_mdn.py --salida indexacion/evidencias/p02-11/revision-01

# Pruebas locales; la integración completa se omite por defecto.
.\.venv\Scripts\python.exe -m unittest discover -s indexacion -p test_p02_11.py -v
```

La salida predeterminada es una carpeta nueva bajo `indexacion/evidencias/p02-11/`.
`resultado.json` registra el plan de 60 IDs, sus títulos y categorías, qué IDs se
crearían o sustituirían cuando Solr responde, bloqueos y respuestas de lectura.
Sin Solr disponible, las acciones quedan pendientes de inspección y el estado
es `prueba_local_solr_no_disponible`. El código de salida 0 indica que la prueba
local fue válida; **no autoriza la carga**: revisar `estado` y `bloqueos`.
Un esquema incompatible o estado ajeno produce error y código de salida 1.

### Dependencia de P05 / PR #6

La inspección de la referencia local `origin/feat/autocompletado-ortografia`, sin
fusionarla, confirma estos requisitos, ya definidos en `configurar_esquema.py`:

| Campo auxiliar | Tipo | stored | Copia |
|---|---|---|---|
| `titulo_sugerencia` | `text_sugerencia_es` | true | `titulo` |
| `contenido_ortografia` | `text_ortografia_es` | false | `contenido` |
| `contenido_vocabulario` | `text_vocabulario_es` | false | `contenido` |

Los tres deben estar indexados, ser monovaluados, sin `docValues`, sin valores
predeterminados y con sus copias sin truncamiento. P02-11 **exige** su presencia,
aunque sean opcionales para el contrato principal. No crea tipos, campos,
`copyField`, componentes, handlers ni diccionarios. La instalación de Suggester
y SpellCheck y su validación funcional siguen perteneciendo a P05; este cargador
comprueba las dependencias de esquema de la indexación, no certifica sus endpoints.

### Aplicación futura: no ejecutada durante este desarrollo

Solo después de integrar y aplicar P05 y revisar las evidencias:

```powershell
.\.venv\Scripts\python.exe indexacion/indexar_corpus_mdn.py --aplicar --confirmar "INDEXAR 60 DOCUMENTOS EN ri" --salida indexacion/evidencias/p02-11/carga-01
```

La frase debe coincidir literalmente y también se exige al invocar `ejecutar`
desde Python. Antes de escribir se comprueban esquema completo, analizador y
documentos actuales. Se acepta un core vacío, los tres IDs piloto esperados con
sus campos obligatorios originales, o exactamente los mismos 60 IDs del corpus.
Un índice parcial o con documentos ajenos bloquea la carga. Los 60 IDs existentes
pueden actualizar sus valores desde el corpus aprobado; los auxiliares se rellenan
por `copyField`. No se envían valores auxiliares manualmente.

La carga sustituye documentos completos con `overwrite=true`, reutiliza los IDs
piloto y realiza un commit explícito con `waitSearcher=true`. Las repeticiones
mantienen 60 IDs únicos. Se guardan `preparacion.json` y `documentos.json` antes
del primer POST, y `resultado.json` al finalizar o ante errores. Se verifica el
status de update y commit. Una desconexión puede dejar una escritura parcial:
se registra el estado observable sin limpiar ni reparar automáticamente. No se
reintenta automáticamente un update ni un commit de resultado incierto.

La verificación posterior exige 60 documentos, cuotas, `tipo_fuente=web`, todos
los campos y metadatos enviados, título sugerido preservado, facetas exactas,
búsquedas por título y contenido de las tres categorías, términos técnicos y un
término acentuado del corpus. Cada consulta se repite y compara IDs, orden y
puntuaciones, ordenando por score e ID para resolver empates. Las fechas se
comparan como instantes UTC con milisegundos mediante el validador existente,
admitiendo diferencias de serialización de ceros finales en `pdate`. Para los campos
P05 no almacenados se consulta su presencia en el índice invertido; no se intenta
leerlos como stored. También se confirma que esquema y archivos no cambiaron.

Para `enlaces_salientes`, una lista vacía esperada equivale a la ausencia del
campo en la respuesta de Solr: los multivaluados sin valores pueden omitirse.
Esta excepción solo acepta el campo ausente o `[]`; un `null` explícito no se
equipara a una lista vacía. Las listas no vacías se comparan exactamente,
incluyendo valores, cantidad y orden. Las validaciones de los demás campos
conservan su comportamiento.

Ejecutar sin otros escritores en `ri`: las comprobaciones previas y el update
no son una transacción ni un bloqueo distribuido. Un error posterior al commit
se informa como error, aunque ya haya 60 documentos, y requiere inspección humana.

### Integración completa de solo lectura

Después de la carga real, esta prueba verifica el índice sin escribir:

```powershell
$env:P02_11_SOLR_INTEGRACION = '1'
.\.venv\Scripts\python.exe -m unittest discover -s indexacion -p test_p02_11.py -v
Remove-Item Env:P02_11_SOLR_INTEGRACION
```

Las pruebas P01-05 conservan su alcance de **tres** documentos. Su integración
real deja de ser aplicable tras cargar los 60; no activar `P01_05_SOLR_INTEGRACION`
para verificar el índice completo. Las pruebas P02-11 ordinarias usan un Solr
simulado, incluyendo fallos de update, commit y verificación, sin tocar el core.

Durante la ejecución inicial de desarrollo, la prueba local validó los 60 documentos y sus metadatos;
Solr rechazó la conexión en `localhost:8983`. La evidencia está en
`evidencias/p02-11/revision-final/resultado.json`. No se ejecutó la carga real
ni se modificó `ri`; en esa ejecución no se pudo reconfirmar su recuento de tres.
P02-11 permanece pendiente hasta la carga y verificación reales tras P05.

Resultados iniciales de las pruebas locales de este desarrollo (registros en
`evidencias/p02-11/pruebas_*.txt`, resumen en `resumen_desarrollo.json`):

| Suite | Exitosas | Integraciones omitidas |
|---|---:|---:|
| P02-11 | 19 | 1 |
| P01-05 | 18 | 1 |
| Transformación P02-09 | 11 | 0 |
| Análisis de español | 39 | 0 |
| Total | 87 | 2 |

Las dos omisiones corresponden a pruebas de lectura del core real. Todos los
procesos de pruebas finalizaron con código 0; no se hicieron commits ni push.

### Revisión de enlaces vacíos con Solr disponible

Se ejecutó de nuevo el indexador exclusivamente en modo de prueba:

```powershell
.\.venv\Scripts\python.exe indexacion/indexar_corpus_mdn.py --salida indexacion/evidencias/p02-11/revision-enlaces-vacios
```

La nueva evidencia `revision-enlaces-vacios/resultado.json` registra
`estado=prueba_bloqueada`, **3 documentos piloto existentes, 3 sustituciones y
57 documentos por crear**. Se detectaron los seis bloqueos esperados: faltan
`titulo_sugerencia`, `contenido_ortografia`, `contenido_vocabulario` y sus tres
reglas `copyField`. No se intentó ninguna escritura ni se ejecutó un commit.
Una segunda lectura, guardada en `estado_posterior.json`, confirmó los mismos
tres documentos y valores. Las evidencias anteriores se conservaron intactas.

Las pruebas ahora simulan la omisión de los cinco `enlaces_salientes=[]` del
corpus real y rechazan listas incompletas, alteradas, distintas, reordenadas,
con enlaces adicionales o ausentes cuando se esperan valores. También rechazan
valores incorrectos para listas vacías y campos distintos omitidos o alterados.
Registros nuevos: `revision-enlaces-vacios/pruebas_*.txt` y
`revision-enlaces-vacios/resumen_pruebas.json`: **90 pruebas exitosas y
2 integraciones reales omitidas**, con códigos de salida 0 (P02-11: 22 exitosas,
P01-05: 18, transformación: 11, análisis: 39).

## Estado histórico previo a P02-11

No se observó un bloqueo técnico de campos o del piloto. La compatibilidad de
los 60 documentos y sus metadatos se validó localmente; su indexación completa
y comportamiento conjunto en Solr quedan para P02-11.

P00-03 v1.2 ya fue ratificado por Karen y Carlos; no queda pendiente esa
coordinación. La futura carga deberá contemplar los tres IDs ya
existentes mediante una política explícita de actualización por ID y verificar
60 documentos finales. Este script rechaza un core de 60 documentos y no sirve
como cargador completo. Cualquier reconstrucción requiere respaldo y coordinación
conforme al contrato. La entrega se prepara mediante Pull Request hacia `main`,
sin fusión automática.
