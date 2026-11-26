# P00-03 · Contrato común de documentos Solr (web y PDF)

**Versión:** 1.1 — consolidación Solr ↔ API; pendiente de ratificación por el equipo  
**Fecha:** 26 de noviembre de 2026  
**Proyecto:** Búsqueda y Recuperación de Información  
**Motor:** Apache Solr 10 · **Core de trabajo:** `ri`  
**Participantes:** Joseph (infraestructura, documentos, indexación y PDF), Karen (análisis de español), Carlos (consultas y FastAPI). Mauricio consume el contrato HTTP desde Angular.

> **Estado del acuerdo.** Los campos comunes, el analizador y las facetas recogen las respuestas de Karen y Carlos. La interfaz HTTP toma como referencia **P00-04 · Contrato de API FastAPI–Angular v1.0**, recibido de Carlos. Este documento fija la correspondencia entre los datos y la API; **no constituye todavía la ratificación formal de P00-03 v1.1 ni de P00-04**. Algunos detalles de HTTP siguen abiertos en la sección 7.3. Tampoco acredita que el esquema esté aplicado o que haya documentos indexados.

## 1. Objetivo y límites

Definir un único contrato para indexar y consultar páginas MDN en español y documentos PDF locales. Las consultas del backend usarán los mismos campos de título y cuerpo independientemente de la procedencia. No se alterará el corpus original ni se ejecutarán indiscriminadamente los scripts docentes que definan campos incompatibles.

**Datos disponibles:** 60 documentos MDN, 20 JavaScript, 20 HTML y 20 CSS; limpieza P02-07 concluida y registrada en el commit `7d0ddc8` (34 documentos modificados, 26 sin cambios, 13 060 caracteres eliminados, 55 pruebas exitosas). Estos son datos de la limpieza, no de una indexación en Solr.

## 2. Esquema mínimo obligatorio

Las propiedades `stored` e `indexed` de la tabla indican la configuración objetivo de Solr; `docValues` se utiliza para las facetas exactas. Los campos marcados como obligatorios se exigen en **cada documento indexable**, no en todos los archivos del crawler original.

| Campo | Tipo Solr objetivo | Obligatorio | Propiedades | Significado y valores |
|---|---|---|---|---|
| `id` | `string` | Sí | `stored=true`, `indexed=true` | Clave única estable. Web: URL normalizada; PDF: `pdf:<sha256>` de los bytes del archivo. |
| `titulo` | `text_es_proyecto` | Sí | `stored=true`, `indexed=true` | Texto consultable y visible del título. |
| `contenido` | `text_es_proyecto` | Sí | `stored=true`, `indexed=true` | Texto consultable; fuente para snippets/highlighting. |
| `categoria` | `string` | Sí | `stored=true`, `indexed=true`, `docValues=true` | `JavaScript`, `HTML`, `CSS` o `General`. Faceta exacta. |
| `tipo_fuente` | `string` | Sí | `stored=true`, `indexed=true`, `docValues=true` | `web` o `pdf`. Faceta exacta. |
| `fuente` | `string` | Sí | `stored=true`, `indexed=true` | Ejemplos: `MDN Web Docs`, `PDF local`. Texto de procedencia para la API. |
| `idioma` | `string` | Sí | `stored=true`, `indexed=true` | `es` para los documentos actualmente admitidos en español. |
| `url` | `string` | Solo web | `stored=true`, `indexed=true` | URL canónica de una página. Omitir en documentos PDF locales; la API enviará `null`. |

**Reglas:** `titulo` y `contenido` no pueden ser cadenas vacías tras la validación; cada `id` debe ser único. La categoría por defecto de PDF sin clasificación explícita es `General`. El origen `pdf` no presupone que exista una URL pública. `score` y `snippet` **no son campos persistidos** del documento: se producen al consultar Solr.

## 3. Metadatos adicionales no obligatorios

Se conservan cuando son pertinentes y existen en la fuente, pero ni la búsqueda básica ni las facetas dependen de ellos.

| Campo | Tipo Solr sugerido | Origen / uso |
|---|---|---|
| `atribucion` | `string` o campo de texto almacenado, no analizado | Reconocimiento de procedencia MDN cuando aplique. |
| `profundidad` | `pint` | Nivel histórico de rastreo web. |
| `fecha_rastreo` | `pdate` | Fecha UTC de la captura web, convertida a formato admitido por Solr. |
| `enlaces_salientes` | `strings`, multivaluado | URLs descubiertas por el crawler; no aplica a PDF ordinarios. |
| `descubierta_desde` | `string` | Enlace de procedencia del rastreo. |
| `tipo_documento` | `string` | Metadato interno del crawler (`articulo_explicativo`, `indice`); **no es faceta obligatoria ni campo de respuesta de la API**. |
| `titulo_original`, `titulo_descriptivo`, `titulo_documento` | `string` | Metadatos editoriales del crawler, si se decide preservarlos en Solr. |
| `sha256_contenido`, `sha256_contenido_normalizado` | `string` | Auditoría de contenido MDN; no son facetas. |
| `pagerank` | `pdouble` | Opcional para páginas web si se calcula posteriormente; no exigido a PDF. |

Los tipos opcionales se concretarán en el script de esquema; la ausencia de un campo opcional no deberá invalidar el documento. El **hash de bytes del PDF que determina su `id`** es distinto de los hashes del texto MDN; no debe sustituirse por uno de ellos.

## 4. Análisis del español — Karen

- Nuevo tipo de campo **`text_es_proyecto`**, aplicado a `titulo` y `contenido`.
- Basado en `text_es_ri`: minúsculas y tratamiento de acentos, incorporando palabras vacías en español, stemming y protección de términos técnicos como `JavaScript`, `HTML` y `CSS`.
- **Sinónimos solamente en el análisis de consultas**, no durante la indexación.
- **`text_es_ri` se conserva sin modificaciones** para comparaciones de las prácticas del kit.
- Karen prepara la definición del tipo y los recursos de stopwords, sinónimos y términos protegidos en su propia rama; Joseph integra la configuración del esquema y comprueba su reproducibilidad.
- `titulo_sugerencia` y `contenido_ortografia` son **campos opcionales futuros**; su creación depende del diseño efectivo de Suggester/SpellCheck, y no bloquea el contrato principal.

**Condición para indexar:** el tipo `text_es_proyecto` debe existir y analizar correctamente ejemplos en español antes de crear/cargar el índice definitivo. Cualquier cambio posterior al *indexAnalyzer* puede exigir reconstrucción/reindexación.

## 5. Compatibilidad con el kit docente

El kit incluye `text_es_ri` y scripts que crean `titulo` y `contenido` con ese tipo, además de `tema`, `vector` y campos web `titulo_web`, `contenido_web`, `url`, `profundidad`, `enlaces_salientes` y `pagerank`.

Para el **buscador integrado**, las consultas utilizan **`titulo` y `contenido`**, ambos con `text_es_proyecto`. No se duplicará por defecto cada texto en `titulo_web` y `contenido_web` ni se exigirá `tema` o `tipo_documento` como facetas. Se conservarán sin alterar los scripts originales del profesor; los campos heredados y `pagerank` podrán mantenerse para prácticas o experimentos independientes.

**No ejecutar `kit/02_recuperacion_informacion/configuracion/configurar_esquema.py` sin revisar el destino:** en su forma original crea `titulo` y `contenido` con `text_es_ri`. El esquema del sistema integrado debe configurarse mediante un script propio y reproducible, comprobando antes el estado del core `ri`; no sobrescribir campos incompatibles ni borrar un índice sin respaldo.

## 6. Identificación y transformación de documentos

### 6.1 Páginas MDN

- Leer exclusivamente la **versión limpia validada** del corpus de 60 documentos; conservar intactos el corpus original y el reporte de limpieza.
- Reutilizar el `id` y la `url` normalizados por el crawler.
- Mapear `titulo`, `contenido`, `categoria`, `idioma`, `fuente`, `tipo_fuente` y los metadatos opcionales autorizados.
- Validar exactamente 60 IDs únicos y el reparto 20/20/20 antes de la indexación final.
- No transmitir al esquema campos inesperados ni formatos incompatibles (p. ej., convertir fechas de forma explícita y mantener los enlaces como lista multivaluada).

### 6.2 PDF locales

- El módulo reutilizable a cargo de Joseph recibe bytes o una ruta de PDF, extrae texto seleccionable **sin OCR** en la primera versión y devuelve un documento indexable; no implementa rutas HTTP.
- Carlos recibe el archivo por **`POST /api/v1/documents/pdf`**, en `multipart/form-data`: `file` obligatorio (máximo **10 MB** según P00-04), `titulo` opcional y `categoria` opcional (`JavaScript`, `HTML`, `CSS`, `General`; por defecto `General`). La validación del tamaño, tipo MIME y parámetros HTTP pertenece a FastAPI; el módulo de Joseph valida integridad y texto recuperable. El límite exacto en bytes y la política de reimportación se confirman con Carlos.
- Formar `id = "pdf:" + SHA256(bytes_del_pdf).hexdigest()` (**64 caracteres hexadecimales tras `pdf:`**). La reimportación de **los mismos bytes** conserva el mismo ID; una versión binariamente distinta se considera un archivo distinto aunque tenga el mismo nombre. Los hashes truncados que figuran en ejemplos de P00-04 son **ilustrativos**, no IDs válidos finales.
- Asignar `titulo` desde el parámetro explícito cuando exista y sea válido; de lo contrario, usar un título derivado del archivo o metadatos fiables. Validar que sea legible y no vacío.
- Asignar `contenido` al texto extraído, `tipo_fuente="pdf"`, `fuente="PDF local"`, `idioma="es"` y la `categoria` validada.
- No inventar URL pública. Rechazar con mensaje claro los PDF ilegibles, dañados o sin texto recuperable; OCR es una ampliación fuera del alcance inicial.
- Mantener el archivo original fuera de Solr salvo que se implemente explícitamente un sistema de almacenamiento; **el campo `contenido` almacena texto, no bytes del PDF**.
- `201 Created` y `status="indexed"` en FastAPI se enviarán solo después de confirmar indexación exitosa; el comportamiento al reimportar un PDF idéntico y el código para archivos mayores de 10 MB están **pendientes de acuerdo en P00-04**.

### 6.3 Ejemplos de documentos indexables

**Web (ejemplo ilustrativo con texto abreviado):**

```json
{
  "id": "https://developer.mozilla.org/es/docs/Web/JavaScript/Guide/Language_overview",
  "titulo": "Una reintroducción a JavaScript (Tutorial de JS)",
  "contenido": "Información general. JavaScript es un lenguaje dinámico...",
  "categoria": "JavaScript",
  "tipo_fuente": "web",
  "fuente": "MDN Web Docs",
  "idioma": "es",
  "url": "https://developer.mozilla.org/es/docs/Web/JavaScript/Guide/Language_overview"
}
```

**PDF (ejemplo ficticio; el identificador es un marcador, no un SHA-256 real):**

```json
{
  "id": "pdf:<sha256-hexadecimal-del-archivo>",
  "titulo": "Introducción a la recuperación de información",
  "contenido": "Texto extraído del documento PDF...",
  "categoria": "General",
  "tipo_fuente": "pdf",
  "fuente": "PDF local",
  "idioma": "es"
}
```

Estos ejemplos **no** deben enviarse directamente a Solr: los contenidos están abreviados y el hash PDF es ilustrativo. La salida real deberá validarse automáticamente.

## 7. Compatibilidad con P00-04 — FastAPI → Angular

**Fuente del contrato HTTP:** `contrato_api_v1.md` (P00-04 v1.0, entregado por Carlos). El documento P00-04 es la fuente de verdad para **rutas, parámetros, códigos y cuerpos HTTP**, mientras que P00-03 gobierna **campos, tipos, IDs, indexación y metadatos de Solr**. El siguiente ejemplo refleja la forma de `/search` acordada; no debe mantenerse como copia divergente cuando cambie P00-04:

```json
{
  "query": "javascript",
  "total": 2,
  "page": 1,
  "page_size": 10,
  "results": [
    {
      "id": "https://developer.mozilla.org/es/docs/Web/JavaScript/Guide/Language_overview",
      "titulo": "Una reintroducción a JavaScript (Tutorial de JS)",
      "url": "https://developer.mozilla.org/es/docs/Web/JavaScript/Guide/Language_overview",
      "categoria": "JavaScript",
      "tipo_fuente": "web",
      "fuente": "MDN Web Docs",
      "score": 1.73,
      "snippet": "...<em>JavaScript</em> es un lenguaje..."
    },
    {
      "id": "pdf:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "titulo": "Introducción a JavaScript",
      "url": null,
      "categoria": "General",
      "tipo_fuente": "pdf",
      "fuente": "PDF local",
      "score": 1.12,
      "snippet": "...uso de <em>JavaScript</em>..."
    }
  ],
  "facets": {
    "categoria": [
      { "value": "JavaScript", "count": 1 },
      { "value": "General", "count": 1 }
    ],
    "tipo_fuente": [
      { "value": "web", "count": 1 },
      { "value": "pdf", "count": 1 }
    ]
  }
}
```

**Semántica del contrato:**

- `query`: consulta recibida por FastAPI.
- `total`: número total de documentos coincidentes antes de paginar; no es el tamaño del arreglo `results`.
- `page`, `page_size`: página solicitada y tamaño de página; **convención sugerida para la implementación: numeración desde 1**. Carlos la validará al crear el endpoint.
- `results`: documentos de la página actual ordenados por relevancia; `score` numérico proviene de Solr.
- `snippet`: fragmento de contenido con marcas de resaltado `<em>...</em>`; si no existe fragmento, devolver `""`.
- `url`: `string` para web, `null` para PDF local; el frontend no debe tratar `null` como enlace.
- `facets.categoria` y `facets.tipo_fuente`: conteos correspondientes a filtros de campos exactos; el detalle de cómo se aplican conjuntamente con filtros activos se verificará en las pruebas de API.
- El texto del fragmento se escapará antes de incorporar las etiquetas de resaltado, y Angular no deberá renderizar HTML arbitrario recibido de documentos de terceros.

**Responsabilidades:** Carlos define y prueba la ruta HTTP y el procesamiento de consultas, paginación, facetas y snippets; Mauricio consume los datos en Angular.

### 7.1 Endpoints que consumen o dependen de Solr

| Endpoint de P00-04 | Campo/recurso Solr relacionado | Quién integra |
|---|---|---|
| `GET /api/v1/health` | Conectividad del core `ri` | Carlos |
| `GET /api/v1/search` | `titulo`, `contenido`, `categoria`, `tipo_fuente`; highlighting | Carlos; Joseph configura campos |
| `GET /api/v1/suggest` | Recursos Suggester; `titulo_sugerencia` si Karen lo requiere | Karen + Carlos |
| `GET /api/v1/spellcheck` | Recursos SpellCheck; `contenido_ortografia` si Karen lo requiere | Karen + Carlos |
| `GET /api/v1/documents/{doc_id}/related` | ID URL o PDF, MoreLikeThis o estrategia equivalente | Carlos; Mauricio consume |
| `POST /api/v1/documents/pdf` | Validación HTTP → extracción/transformación → indexación Solr | Carlos + Joseph |

Las rutas de sugerencias y corrección **no convierten** automáticamente los campos opcionales correspondientes en requisitos del índice; se precisará qué componentes y recursos configure Karen antes de usarlos.

### 7.2 Límite de responsabilidad para subir PDF

1. **Mauricio (Angular)** construye el formulario y envía `multipart/form-data` al endpoint de Carlos.
2. **Carlos (FastAPI)** valida archivo, límite de tamaño, título y categoría; llama al módulo reutilizable de Joseph y traduce resultados/errores a HTTP.
3. **Joseph (módulo Python)** extrae el texto del PDF, calcula ID completo por SHA-256, construye los campos P00-03 e indexa mediante una interfaz reutilizable. El módulo no requiere importar FastAPI ni Angular.
4. **Solr** almacena el texto y sus metadatos; no almacena los bytes originales del PDF.

### 7.3 Ajustes **pendientes de ratificar en P00-04** (no bloquean P02-09)

- **Paginación:** P00-04 establece `page_size=10` fijo, pero su ejemplo usa `page_size=3` y envía ese parámetro. Preferencia propuesta: dejar 10 fijo y corregir el ejemplo; Carlos decide.
- **IDs web en `/related`:** al ser URLs con diagonales, `encodeURIComponent` no garantiza por sí solo que todos los servidores preserven la ruta. Propuesta: transmitir el ID como `?id=...`, o sustituirlo por un identificador opaco; Carlos y Mauricio definen la solución. **El ID almacenado en Solr no cambia**.
- **Reimportación PDF idéntico:** mismo SHA-256 implica mismo ID. Acordar si responde `200` (existente/actualizado) o una alternativa documentada, sin generar duplicados.
- **Archivo > 10 MB:** proponer `413 Payload Too Large` y un `error.code` consistente con el formato estándar de P00-04. Confirmar si se usa 10 000 000 o 10 × 1024 × 1024 bytes.
- **Ejemplo JSON de P00-04:** eliminar el comentario `//aqui el ejemplo es con 3`; JSON real no admite comentarios. Los ejemplos de identificadores PDF abreviados deben etiquetarse como ilustrativos.
- **Errores / HTML:** Carlos normaliza las excepciones del módulo PDF al contrato de errores y escapa el texto de snippets antes de introducir únicamente las marcas `<em>`; Mauricio evita renderizar HTML arbitrario.

## 8. Responsabilidades e integración

| Responsable | Implementación | Entregable |
|---|---|---|
| **Joseph** | Esquema Solr reproducible, transformación MDN, indexación; módulo reutilizable de extracción/transformación/indexación PDF, sin rutas HTTP | Scripts, JSON indexable, pruebas y documentación. |
| **Karen** | `text_es_proyecto` y recursos lingüísticos; posteriormente Suggester/SpellCheck | Tipo de campo y recursos versionados, pruebas de análisis. |
| **Carlos** | Consultas a Solr, facetas, ranking, snippets, serialización FastAPI y endpoint `POST /api/v1/documents/pdf` | Respuestas API conformes a P00-04 y llamada al módulo de Joseph. |
| **Mauricio** | Interfaz Angular | Consumo seguro del contrato HTTP. |

Cada implementación se desarrolla en una rama por funcionalidad, mediante Pull Request hacia `main`. En particular, **Karen no modifica el esquema final en paralelo con Joseph**: entrega sus recursos y Joseph los integra. La integración no debe reemplazar la configuración docente ni borrar datos del core.

## 9. Criterios de aceptación de P00-03 y siguientes fases

**P00-03 (contrato):**

- [x] Nombres de campos principales y analizador acordados con Karen y Carlos.
- [x] Facetas limitadas a `categoria` y `tipo_fuente` para la API.
- [x] `titulo` y `contenido` almacenados e indexados; `idioma="es"` para el corpus actual.
- [x] Estructura JSON de FastAPI referenciada a P00-04 según Carlos.
- [x] Convenciones de ID, categoría y campos para PDF establecidas en este documento.
- [x] Ejemplos de web y PDF incluidos.
- [x] Alcance HTTP de subida PDF identificado en P00-04; reparto de responsabilidades documentado.
- [ ] Karen y Carlos ratifican P00-03 v1.1 y se versiona el Markdown en el repositorio (verificar tras la Pull Request).
- [ ] Carlos y Mauricio resuelven los puntos abiertos de P00-04 para el cierre formal de **esa** tarea; no bloquean el contrato de campos Solr.

**Tareas posteriores, no incluidas en el cierre de P00-03:**

1. **P02-09:** transformar los 60 documentos limpios al esquema común; probar unicidad, tipos y conservación de texto.
2. **P01-04 / P01-05:** integrar el analizador y configurar el esquema, luego indexar tres documentos representativos de prueba y verificar búsquedas y facetas.
3. **P02-11 / P02-13:** indexar y validar los 60 documentos y congelar el artefacto indexable.
4. **P07-01 a P07-04:** seleccionar PDF de prueba, extraer contenido, mapear e indexar.
5. **Integración API:** implementar con Carlos el endpoint de subida conforme a P00-04, solucionar los detalles abiertos y probar FastAPI y Angular de extremo a extremo.

**Regla de seguridad operacional:** cualquier reconstrucción del core o del índice requiere copia de respaldo y coordinación previa; no ejecutar operaciones destructivas de Docker ni reindexar automáticamente ante cambios de análisis.

## 10. Registro de revisiones

| Versión | Fecha | Cambio | Estado |
|---|---|---|---|
| 1.0 | 2026-11-25 | Campos comunes, analizador y respuesta de búsqueda acordados; convenciones web/PDF propuestas. | Preparada para revisión |
| **1.1** | **2026-11-26** | Alineación con P00-04 v1.0, endpoint PDF, límite 10 MB, responsabilidades y decisiones HTTP abiertas. | **Pendiente de ratificación y PR** |

**Nota de control de alcance:** Los cambios de P00-04 no modifican el esquema mínimo ni los documentos MDN ya limpiados. No se configura Solr ni se cargan documentos como parte de actualizar este contrato.
