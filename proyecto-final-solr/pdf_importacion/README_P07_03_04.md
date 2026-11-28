# P07-03 / P07-04: transformar e indexar PDF sin perder los 60 MDN

**Complemento** del `README.md` anterior. No sustituye el extractor P07-02 ni modifica archivos históricos. Se usa el contrato `docs/P00-03_contrato_solr_v1.2.md` (7 campos PDF, sin `url`, `tema` ni ruta pública).

## Dependencias

Desde `proyecto-final-solr` en Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r pdf_importacion\requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s pdf_importacion -p test_p07_03_04.py -v
# Suite completa (8 de P07-02 + 19 de P07-03/P07-04):
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s pdf_importacion -p "test*.py" -v
```

Las 27 pruebas no requieren Solr ni conexión a Internet. Las operaciones de importación real se sustituyen por mocks en las pruebas; su éxito no acredita una indexación real.

## P07-03: generar documentos JSON sin tocar Solr

```powershell
# Usar rutas de salida nuevas: la herramienta no sobrescribe archivos.
$salidaP07 = Join-Path $env:TEMP ("p07-documentos-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $salidaP07 | Out-Null
.\.venv\Scripts\python.exe -X utf8 -m pdf_importacion.indexar_pdf_solr pdf_importacion\muestras\guia_formularios_html.pdf --titulo "Validación de formularios HTML: guía de prueba" --categoria HTML --solo-documento --json-salida "$salidaP07\html.json"
.\.venv\Scripts\python.exe -X utf8 -m pdf_importacion.indexar_pdf_solr pdf_importacion\muestras\guia_diseno_css_responsivo.pdf --titulo "Diseño responsivo con CSS Grid y Flexbox" --categoria CSS --solo-documento --json-salida "$salidaP07\css.json"
```

**Importante:** Si los JSON ya están presentes, la herramienta falla en lugar de sobrescribirlos. Este paquete incluye los dos JSON generados a partir de las muestras originales para revisar P07-03; no necesitas regenerarlos si los copias. Los identificadores siguen `pdf:` + SHA-256 de los bytes del archivo, no del texto.

## P07-04: simular antes de indexar

Requiere Solr 10 operativo en `http://localhost:8983/solr`, core `ri`, con los 60 MDN ya indexados y el corpus aprobado P02-09 en `data/mdn/transformacion/transformacion_20261126T061527349966Z_68284317199543fbb7b8f960224db1d0/corpus_solr.json`. La ruta se resuelve desde el módulo. No hace falta cambiar de rama ni actualizar Git para ejecutar estos pasos.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pdf_importacion.indexar_pdf_solr pdf_importacion\muestras\guia_formularios_html.pdf --titulo "Validación de formularios HTML: guía de prueba" --categoria HTML
.\.venv\Scripts\python.exe -X utf8 -m pdf_importacion.indexar_pdf_solr pdf_importacion\muestras\guia_diseno_css_responsivo.pdf --titulo "Diseño responsivo con CSS Grid y Flexbox" --categoria CSS
```

Cada salida debe tener `"estado":"simulacion"` y `"accion":"crear"` antes de la primera importación, u `"accion":"omitir"` si el PDF ya existe con los mismos siete campos. Se verifica el esquema (`text_es_proyecto`, facetas), los **60 IDs exactos de MDN con sus categorías y origen web** y el estado del PDF existente. El script bloquea si hay inconsistencias. Esta comprobación del importador no compara todo el texto MDN; el verificador de cierre descrito abajo sí compara todos los campos presentes en el corpus aprobado.

## P07-04: indexar explícitamente (SOLO DESPUÉS de revisar simulaciones)

Los siguientes comandos documentan cómo reproducir una importación en una ejecución que permita escribir. **No se ejecutaron durante este cierre**, cuyo alcance es solo lectura. Detén temporalmente otros escritores sobre `ri` durante una importación: las comprobaciones no equivalen a bloqueo transaccional.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m pdf_importacion.indexar_pdf_solr pdf_importacion\muestras\guia_formularios_html.pdf --titulo "Validación de formularios HTML: guía de prueba" --categoria HTML --aplicar --confirmar "INDEXAR PDF EN ri"
.\.venv\Scripts\python.exe -X utf8 -m pdf_importacion.indexar_pdf_solr pdf_importacion\muestras\guia_diseno_css_responsivo.pdf --titulo "Diseño responsivo con CSS Grid y Flexbox" --categoria CSS --aplicar --confirmar "INDEXAR PDF EN ri"
```

La indexación usa `overwrite=true` por ID, realiza `commit waitSearcher=true` y vuelve a verificar los 60 MDN y el documento PDF. Reimportar el mismo PDF con mismos metadatos devuelve `ya_indexado` sin POST; si cambian sus metadatos con ID idéntico, se rechaza para revisión manual.

### Comprobación independiente

```powershell
(Invoke-RestMethod 'http://localhost:8983/solr/ri/select?q=*:*&rows=0&wt=json').response.numFound
(Invoke-RestMethod 'http://localhost:8983/solr/ri/select?q=tipo_fuente%3Apdf&rows=10&fl=id%2Ctitulo%2Ccategoria%2Ctipo_fuente&wt=json').response.docs | Format-Table
(Invoke-RestMethod 'http://localhost:8983/solr/ri/select?q=LinceFormulario2026&defType=edismax&qf=titulo%5E4%20contenido&rows=10&wt=json').response.numFound
(Invoke-RestMethod 'http://localhost:8983/solr/ri/select?q=FaroRejilla2026&defType=edismax&qf=titulo%5E4%20contenido&rows=10&wt=json').response.numFound
```

Esperado después de importar ambas muestras por primera vez: **62 documentos** en total (60 MDN + 2 PDF); categorías JavaScript=20, HTML=21 y CSS=21. Cada consulta exclusiva debe devolver **exactamente un resultado**, de origen `pdf`, con el ID SHA-256 correspondiente al manifiesto. No basta comprobar solo el número de resultados: comprobar también ID, título y categoría. Si Solr rechaza un POST o commit, **no reintentar automáticamente**: inspeccionar `ri`.

### Verificación reproducible de cierre e idempotencia (solo GET)

```powershell
# Directorio nuevo en cada ejecución; conserva las evidencias existentes.
$capturaP07 = "pdf_importacion/evidencias/p07-04/lectura-" + [guid]::NewGuid().ToString("N")
.\.venv\Scripts\python.exe -X utf8 -m pdf_importacion.verificar_integracion --salida $capturaP07
```

`verificar_integracion.py` captura las respuestas completas de recuento/facetas y búsquedas exclusivas, registra fecha UTC, método y URL, verifica hashes de muestras y equivalencia de los JSON P07-03 con su transformación actual, y compara los campos almacenados de los 60 MDN con el corpus aprobado. Para evitar duplicar texto MDN, guarda el hash del corpus, campos comparados y diferencias, no los cuerpos de esos artículos.

Después ejecuta la simulación de ambos PDF con una barrera que rechaza cualquier método distinto de GET. Debe obtener dos resultados `simulacion/omitir`. Esto acredita la decisión idempotente actual sin escritura; el comportamiento `ya_indexado` con `aplicar=True` se prueba mediante mocks, no mediante una nueva importación real. Una modificación de los bytes genera otro ID; los mismos bytes con metadatos distintos se rechazan y requieren revisión manual.

El verificador requiere el estado final de 62 documentos. Termina con error y conserva `registro.json` si falla una validación; ese registro no debe presentarse como éxito. Ejecutar con Python normal, sin `-O`, pues utiliza aserciones. Consulta la captura de este cierre y sus límites en [evidencias/p07-04/README.md](evidencias/p07-04/README.md).

## Revisión del contrato y conservación

`documento_solr.py` calcula el ID con SHA-256 completo de los bytes, valida título/contenido y categorías, y produce únicamente `id`, `titulo`, `contenido`, `categoria`, `tipo_fuente`, `fuente`, `idioma`. Admite ruta o bytes, categoría `General` por defecto y título explícito o derivado del nombre. No incorpora rutas locales, `url`, `tema`, `score` ni `snippet`. Reutiliza el extractor sin OCR de P07-02; no se modificó ese módulo.

`indexar_pdf_solr.py` valida los documentos antes de consultar y solo envía un documento de ID `pdf:` por petición cuando se solicita aplicar con la frase exacta. No transmite el corpus MDN, no contiene borrados ni cambios de esquema. La comparación del cierre acredita igualdad actual de campos almacenados del corpus aprobado; no demuestra retrospectivamente el estado anterior a la indexación ni inspecciona campos derivados por `copyField`. No hay aislamiento frente a otros escritores y un `commit` afecta las actualizaciones pendientes del core; coordinar importaciones reales.

El README de P07-01/P07-02 se conserva como documento histórico: su sección «Siguientes tareas (NO ejecutadas)» describe el alcance de aquella entrega. Este complemento registra P07-03/P07-04; P07-10 y la integración HTTP siguen fuera de este cierre.

## Para integración con Carlos

```python
from pdf_importacion.documento_solr import convertir_pdf_a_documento
from pdf_importacion.indexar_pdf_solr import importar_documento_pdf, CONFIRMACION

doc = convertir_pdf_a_documento(archivo_bytes, titulo="Mi PDF", categoria="General")
# Tras validar el request HTTP, Carlos invoca explícitamente el módulo:
resultado = importar_documento_pdf(doc, aplicar=True, confirmar=CONFIRMACION)
```

El módulo no implementa FastAPI. Las respuestas HTTP y límites de subida (10 MB según contrato API) se validan por Carlos. Los archivos fuente se mantienen fuera de Solr; la importación indexa solo contenido textual y metadatos. La prueba extremo a extremo de UI corresponde a P07-10.
