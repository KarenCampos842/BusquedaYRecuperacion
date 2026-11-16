# Comparación de buscadores

El reporte final está en [`output/pdf/comparacion_buscadores.pdf`](../output/pdf/comparacion_buscadores.pdf).

La evaluación definitiva usa 30 documentos sintéticos, cinco consultas y etiquetas binarias fijadas previamente. Se ejecutaron los buscadores originales mediante sus controladores HTTP, con bases nuevas y el modo natural de FULLTEXT.

| Sistema | MAP | Precisión final | Recall final | Accuracy |
|---|---|---|---|---|
| buscador2 | 0.473333 | 0.60 | 0.75 | 0.90 |
| Búsqueda empresarial | 0.458333 | 0.60 | 0.75 | 0.90 |

Cada una de las cinco consultas tiene TP=3, FP=2, FN=1 y TN=24 en ambos sistemas. La ventaja de MAP proviene de los desempates en Q2 y Q5. La colección tiene un relevante con paráfrasis por consulta que ninguno de los sistemas recupera.

## Materiales

- `coleccion/` contiene los 30 archivos UTF-8 que deben cargarse en ambos sistemas.
- `protocolo.json` contiene consultas literales, criterios, títulos, etiquetas y hashes SHA-256.
- `resultados/ultima_ejecucion.json` contiene la ejecución definitiva completa.
- `resultados/20261116_113239_660314/` conserva HTML, logs, configuración y respuestas del motor para la ejecución definitiva.
- `resultados/20261116_113114_990363/` conserva la ejecución exploratoria con nombres que codificaban las etiquetas. Se detectó que estos nombres sesgaban el desempate por nombre. El reporte final utiliza la ejecución con identificadores neutrales, asignados mediante `random.Random(20261116).shuffle`.
- `../output/pdf/figuras/` contiene las seis curvas en PNG.

Los textos fueron redactados con asistencia de IA. Cada grupo temático comparte un párrafo contextual. Las etiquetas reflejan el propósito del documento respecto a la necesidad de información. Los documentos relevantes para una consulta se consideran irrelevantes para las otras. El tamaño y el diseño sintético limitan la generalización.

## Repetir desde PowerShell

Ejecutar desde la raíz del repositorio con Python 3.10 o superior y MySQL 8.0 disponible. La ejecución original utilizó Python 3.14 y MySQL 8.0.44. El usuario de MySQL necesita permisos para crear bases, tablas y configurar la tabla de stopwords en la sesión.

```powershell
python -m venv .venv-evaluacion
.\.venv-evaluacion\Scripts\python.exe -m pip install -r evaluacion/requirements.txt
$env:EVAL_DB_HOST = '127.0.0.1'
$env:EVAL_DB_PUERTO = '3307'
$env:EVAL_DB_USUARIO = 'root'
$env:EVAL_DB_CONTRASENA = ''
.\.venv-evaluacion\Scripts\python.exe -m unittest discover -s evaluacion -p test_metricas.py -v
.\.venv-evaluacion\Scripts\python.exe evaluacion/evaluar.py
.\.venv-evaluacion\Scripts\python.exe evaluacion/generar_reporte.py
.\.venv-evaluacion\Scripts\python.exe evaluacion/verificar_reporte.py
```

Si MySQL utiliza el puerto habitual, establecer `EVAL_DB_PUERTO` en `3306`. Los valores predeterminados son host `127.0.0.1`, puerto `3306`, usuario `root` y contraseña vacía. Los servidores HTTP del experimento usan `8100` y `8101`. `--puerto-base` permite elegir otro par consecutivo.

Cada ejecución crea bases con el prefijo `eval_` y una marca temporal. El almacén de buscador2 se ubica en `tmp/` y los servidores HTTP se cierran al finalizar. Las bases quedan disponibles para inspección. El evaluador guarda hashes del código de las aplicaciones, versión del servidor, dependencias y configuración. Los datos finales se publican en `ultima_ejecucion.json` solo después de pasar las comprobaciones de ambos sistemas.

Los archivos de la colección ya están preparados. Para regenerarlos desde su definición, ejecutar `generar_coleccion.py` antes de evaluar. Si se modifican textos o etiquetas, volver a ejecutar todo el proceso para que el reporte corresponda a los nuevos datos.

`requirements.lock.txt` registra las versiones exactas instaladas durante la ejecución original en Windows con Python 3.14. Puede usarse en lugar de `requirements.txt` al reproducir ese mismo entorno.

## Instancia aislada utilizada

Se empleó el ejecutable de MySQL 8.0 instalado en `C:/Program Files/MySQL/MySQL Server 8.0/bin/`, con datos en `tmp/mysql-evaluacion`, puerto `3307`, enlace a `127.0.0.1` y MySQL X desactivado. La instancia se cerró después de verificar el reporte.

Para preparar esta instancia en una copia nueva del repositorio, ejecutar la inicialización una sola vez con el directorio de datos vacío.

```powershell
$mysqlBin = 'C:/Program Files/MySQL/MySQL Server 8.0/bin'
$evaluationData = Join-Path (Get-Location).Path 'tmp/mysql-evaluacion'
New-Item -ItemType Directory -Force $evaluationData | Out-Null
& "$mysqlBin/mysqld.exe" --no-defaults --initialize-insecure "--datadir=$evaluationData" --console
```

Para arrancar una instancia ya inicializada, ejecutar el siguiente bloque. La inicialización anterior crea el usuario root local con contraseña vacía para este experimento.

```powershell
$mysqlBin = 'C:/Program Files/MySQL/MySQL Server 8.0/bin'
$evaluationData = Join-Path (Get-Location).Path 'tmp/mysql-evaluacion'
$mysqlArgs = @('--no-defaults', ('--datadir="' + $evaluationData + '"'), '--port=3307', '--bind-address=127.0.0.1', '--mysqlx=OFF')
Start-Process -FilePath "$mysqlBin/mysqld.exe" -ArgumentList $mysqlArgs -WindowStyle Hidden
```

Después del experimento, cerrar esta instancia con su cliente administrativo.

```powershell
& 'C:/Program Files/MySQL/MySQL Server 8.0/bin/mysqladmin.exe' --host=127.0.0.1 --port=3307 --user=root shutdown
```

## Revisión visual

`verificar_reporte.py` comprueba hashes, métricas, contenido y límites de página del PDF. Además renderiza sus once páginas mediante PyMuPDF en `tmp/pdfs/` y produce una hoja de contacto. La ejecución original utilizó PyMuPDF porque Poppler no estaba instalado. La inspección visual debe comprobar legibilidad, tablas completas, curvas y paginación.

La precisión de una consulta sin resultados se fija en cero. AP conserva en su denominador los cuatro relevantes, incluidos los ausentes. MAP promedia AP de las cinco consultas. La curva media usa interpolación de precisión en once niveles de recall. El JSON conserva todos los puntos sin interpolar y los puntajes originales.
