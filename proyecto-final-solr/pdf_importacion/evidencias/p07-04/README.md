# P07-04 · Registro de cierre técnico

Verificación del **27 de noviembre de 2026, America/Mexico_City**. Las marcas UTC de la captura corresponden al 28 de noviembre, entre 00:45 y 00:47 UTC (18:45–18:47 del día 27 en Ciudad de México). Core consultado: `http://localhost:8983/solr/ri`.

La indexación de los dos PDF fue realizada previamente, según el contexto aportado por el usuario. **En este cierre no se ejecutaron POST, indexaciones ni commits Solr**. Las observaciones siguientes proceden de consultas GET actuales y pruebas locales ejecutadas, no de una repetición de aquella importación.

| Comprobación ejecutada | Resultado |
|---|---|
| Suite local completa con conexiones bloqueadas | 27 pruebas correctas: 8 de P07-02 y 19 de P07-03/P07-04 |
| Entorno de pruebas | Python 3.14.0; pypdf 6.21.4 |
| Recuento del core | 62 |
| Faceta `tipo_fuente` | web=60; pdf=2 |
| Faceta `categoria` | JavaScript=20; HTML=21; CSS=21 |
| `LinceFormulario2026` | Exactamente 1 resultado, PDF HTML con ID del manifiesto |
| `FaroRejilla2026` | Exactamente 1 resultado, PDF CSS con ID del manifiesto |
| MDN frente al corpus aprobado | 60 IDs exactos; 8 campos comparados por documento; cero diferencias |
| Simulación de ambos PDF ya presentes | `estado: simulacion`, `accion: omitir`; sin escritura |
| Esquema consultado | `uniqueKey=id`; tipos, almacenamiento, indexación, monovalor y facetas conformes para los siete campos PDF |
| Originales y P07-03 | Hashes sin cambios; JSON iguales a su transformación actual |

ID HTML: `pdf:768847d403914513d6ac0ed74bd697e5dc634eef4e2f0bf11a78ef4c2c7af9e1`.

ID CSS: `pdf:b56830143154d57f910411aa694c32bb54e8b77b7e5a8b26020b322a1c091448`.

## Archivos y procedencia

- `pruebas_cierre.txt`: ejecución real de las 27 pruebas con `socket.connect` bloqueado. Las rutas temporales se sustituyeron por `<TEMP>` para no publicar el perfil local. El aviso `EOF marker not found` y el rechazo de sobrescritura pertenecen a casos negativos esperados; la suite terminó en `OK`.
- `cierre_2026-11-27/registro.json`: fechas, métodos y URLs completas de la captura, resultado global y SHA-256 de las muestras y JSON P07-03.
- `cierre_2026-11-27/recuento_facetas.json`: respuesta completa de recuento y facetas.
- `cierre_2026-11-27/busqueda_html.json` y `busqueda_css.json`: respuestas completas, incluyendo parámetros de consulta e identificación del único resultado.
- `cierre_2026-11-27/conservacion_mdn.json`: hash y ruta relativa del corpus aprobado, campos comparados y lista vacía de diferencias. Se compararon `id`, `titulo`, `contenido`, `categoria`, `tipo_fuente`, `fuente`, `idioma` y `url` sin normalizar sus valores.
- `cierre_2026-11-27/simulacion_idempotencia.json`: resultados reales de dos simulaciones, con barrera que bloquea métodos distintos de GET.
- `cierre_2026-11-27/esquema_contrato.json`: captura adicional de los GET a `schema/fields?wt=json` y `schema/uniquekey?wt=json`, con validación local de los campos del contrato.
- `recuento_final_62.json`, `busqueda_html.json` y `busqueda_css.json` en esta carpeta: evidencias preexistentes conservadas. El recuento incluye parámetros; los archivos de búsquedas contienen solo `response`. No permiten atribuir por sí solos una fecha o consulta completa; la captura nueva aporta esa trazabilidad.

Algunos JSON preexistentes tienen BOM UTF-8, compatible con una salida de PowerShell. Se conservaron sus bytes; para leerlos con Python usar `encoding="utf-8-sig"`. Las capturas nuevas usan UTF-8 sin BOM.

La igualdad MDN acredita el estado almacenado actual frente al corpus aprobado, no demuestra retrospectivamente el estado previo a la importación ni compara campos derivados por `copyField`. El preflight del importador comprueba solo IDs, categorías y origen de MDN. El resultado de idempotencia real de este cierre es una simulación; la rama de aplicación sin POST para un existente se verificó mediante mocks.

## Reproducir

Desde `proyecto-final-solr`, seguir [README_P07_03_04.md](../../README_P07_03_04.md) para transformación local, simulación, importación explícita y validación. Para repetir esta captura de lectura, elegir un directorio nuevo:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s pdf_importacion -p "test*.py" -v
$capturaP07 = "pdf_importacion/evidencias/p07-04/lectura-" + [guid]::NewGuid().ToString("N")
.\.venv\Scripts\python.exe -X utf8 -m pdf_importacion.verificar_integracion --salida $capturaP07
# Inspección adicional del esquema, también solo lectura:
Invoke-RestMethod 'http://localhost:8983/solr/ri/schema/fields?wt=json' | ConvertTo-Json -Depth 20
Invoke-RestMethod 'http://localhost:8983/solr/ri/schema/uniquekey?wt=json' | ConvertTo-Json -Depth 20
```

El verificador genera seis JSON en una carpeta nueva y falla si el estado se aparta del esperado. El séptimo JSON de esta captura (`esquema_contrato.json`) procede de la inspección adicional del esquema. No sobrescribir evidencias P07-03 ni PDF originales para repetir el procedimiento.

## Selección exacta para el commit

Todos los siguientes archivos están **sin seguimiento**, no preparados en el índice Git. Rutas relativas a `proyecto-final-solr/`; preparar únicamente estos **19 archivos**:

```text
pdf_importacion/README_P07_03_04.md
pdf_importacion/documento_solr.py
pdf_importacion/indexar_pdf_solr.py
pdf_importacion/test_p07_03_04.py
pdf_importacion/verificar_integracion.py
pdf_importacion/evidencias/p07-03/css.json
pdf_importacion/evidencias/p07-03/html.json
pdf_importacion/evidencias/p07-04/README.md
pdf_importacion/evidencias/p07-04/busqueda_css.json
pdf_importacion/evidencias/p07-04/busqueda_html.json
pdf_importacion/evidencias/p07-04/pruebas_cierre.txt
pdf_importacion/evidencias/p07-04/recuento_final_62.json
pdf_importacion/evidencias/p07-04/cierre_2026-11-27/busqueda_css.json
pdf_importacion/evidencias/p07-04/cierre_2026-11-27/busqueda_html.json
pdf_importacion/evidencias/p07-04/cierre_2026-11-27/conservacion_mdn.json
pdf_importacion/evidencias/p07-04/cierre_2026-11-27/esquema_contrato.json
pdf_importacion/evidencias/p07-04/cierre_2026-11-27/recuento_facetas.json
pdf_importacion/evidencias/p07-04/cierre_2026-11-27/registro.json
pdf_importacion/evidencias/p07-04/cierre_2026-11-27/simulacion_idempotencia.json
```

Se conserva P07-01/P07-02 ya versionado. No incluir `cambios.diff`, la nueva salida de `crawler/evidencias/`, las carpetas sin seguimiento de `data/mdn/limpieza/`, las ejecuciones de `indexacion/evidencias/p02-11/`, `.venv`, `__pycache__` ni temporales. Ninguno se borró ni se modificó en este cierre. La revisión del conjunto propuesto no encontró credenciales, rutas de perfiles ni datos personales; las URLs registradas son localhost y páginas públicas MDN.
