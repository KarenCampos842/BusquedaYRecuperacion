# P07-01 y P07-02 · PDF locales de prueba y extractor (sin OCR)

Este módulo se integra dentro de `proyecto-final-solr/pdf_importacion/`. Su alcance es preparar **dos documentos PDF originales en español** y extraer texto de PDF locales de forma reproducible. **No escribe en Solr**, no altera el corpus de 60 MDN, no crea endpoints HTTP y no construye documentos de índice. Esto último corresponde a P07-03/P07-04 y, para FastAPI, a Carlos.

## P07-01 · Selección de documentos y evidencia

Los dos PDFs de `muestras/` se crearon exclusivamente como fixtures del proyecto y se permite su uso académico. Son documentos de texto seleccionable, con dos páginas cada uno; **no son** PDFs escaneados, copias de manuales docentes ni documentos con datos privados.

| Archivo | Categoría del catálogo P00-03 | Tema local | Consulta exclusiva | Consulta general |
|---|---|---|---|---|
| `muestras/guia_formularios_html.pdf` | `HTML` | Validación de formularios | `LinceFormulario2026` | `formularios` |
| `muestras/guia_diseno_css_responsivo.pdf` | `CSS` | Diseño adaptable con Grid/Flexbox | `FaroRejilla2026` | `cuadrícula` |

Cada consulta exclusiva está **en la segunda página**. El nombre, tamaño en bytes, SHA-256 real del archivo, `id` previsto según P00-03 y metadatos de selección se conservan en `muestras/manifiesto_p07_01.json`. `tema` es solo metadato local de prueba: el contrato Solr P00-03 v1.2 **no define un campo indexado `tema`**, así que no debe agregarse al documento de Solr sin revisar el contrato.

El identificador definitivo para P07-03 es `pdf:` + SHA-256 hexadecimal de los **bytes exactos del PDF**, no del texto extraído. No cambiar los PDFs después de registrar sus hashes sin actualizar el manifiesto.

## P07-02 · Instalar y usar

Desde la raíz `proyecto-final-solr/` en PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r pdf_importacion\requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s pdf_importacion -p test_extractor_pdf.py -v

# Guardar UTF-8 de la primera muestra en una ruta nueva:
.\.venv\Scripts\python.exe pdf_importacion\extractor_pdf.py pdf_importacion\muestras\guia_formularios_html.pdf --salida "$env:TEMP\p07_formulario_extraido.txt"

# Guardar UTF-8 de la segunda muestra:
.\.venv\Scripts\python.exe pdf_importacion\extractor_pdf.py pdf_importacion\muestras\guia_diseno_css_responsivo.pdf --salida "$env:TEMP\p07_css_extraido.txt"
```

**No repetir `--salida` con un archivo existente**, ya que el script rechaza sobrescrituras por seguridad. Se puede omitir `--salida` para imprimir el texto a stdout.

Desde código Python:

```python
from pathlib import Path
from pdf_importacion.extractor_pdf import extraer_texto_pdf

texto_por_ruta = extraer_texto_pdf(Path("pdf_importacion/muestras/guia_formularios_html.pdf"))
texto_por_bytes = extraer_texto_pdf(Path("pdf_importacion/muestras/guia_formularios_html.pdf").read_bytes())
assert texto_por_ruta == texto_por_bytes
```

El retorno es `str` Unicode, convertible a UTF-8. Se unen páginas mediante dos saltos de línea y se normalizan acentos a NFC. No se ejecuta OCR ni se recupera texto contenido únicamente en imágenes. Se rechazan PDF dañados, cifrados y sin texto seleccionable mediante `ErrorExtraccionPDF` con un mensaje comprensible.

## Pruebas

`test_extractor_pdf.py` prueba ambos PDFs y sus términos de la segunda página, entrada por ruta y bytes, UTF-8, PDF con imagen pero sin capa de texto (`pruebas/fixtures/imagen_sin_texto.pdf`), PDF vacío, cabecera inválida, documento corrupto, PDF cifrado, ruta inexistente y CLI sin sobrescritura.

La ejecución preparatoria del 27-nov-2026 con `pypdf 5.9.0` terminó con **8 pruebas correctas**, sin acceso a Solr. El registro está en `evidencias/pruebas_p07_02.txt`.

## Siguientes tareas (NO ejecutadas)

- **P07-03**: construir el documento indexable con los siete campos obligatorios del contrato (`id`, `titulo`, `contenido`, `categoria`, `tipo_fuente`, `fuente`, `idioma`), omitiendo `url` en PDF. Usar la categoría de este manifiesto o `General` si falta.
- **P07-04**: enviar a Solr `ri` con ID estable, confirmar commit, comprobar `tipo_fuente=pdf` y que sigan existiendo los 60 MDN.
- **P07-10**: prueba extremo a extremo vía navegador cuando Carlos y Mauricio terminen sus componentes, incluyendo reimportación sin duplicados.

No marcar P07-03, P07-04 ni P07-10 como completadas con las pruebas de este módulo.
