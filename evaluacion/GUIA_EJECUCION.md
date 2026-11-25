# Guía para reproducir la evaluación ADA 5 con XAMPP

Esta guía permite ejecutar ambos buscadores en Windows, cargar la colección de 30 documentos y comprobar precisión, exhaustividad, accuracy, AP y MAP. Incluye un procedimiento manual y el evaluador automatizado utilizado para obtener los resultados del reporte.

## 1. Preparar el repositorio y Python

Se requieren Git, Python 3.10 o superior y XAMPP con su servidor de bases de datos funcionando. Para descargar el proyecto por primera vez, ejecutar en PowerShell desde la carpeta donde se quiera guardar.

```powershell
git clone https://github.com/KarenCampos842/BusquedaYRecuperacion.git
Set-Location -LiteralPath '.\BusquedaYRecuperacion'
```

Si ya se tiene una copia, abrir una terminal en su carpeta `BusquedaYRecuperacion`. Todos los comandos siguientes parten de la raíz del repositorio. Este comando debe devolver `True`.

```powershell
Test-Path '.\buscador2\main.py'
```

Crear el entorno e instalar las dependencias de evaluación.

```powershell
python -m venv .venv-evaluacion
.\.venv-evaluacion\Scripts\python.exe -m pip install -r evaluacion/requirements.txt
```

Las dependencias de evaluación incluyen PyMySQL, los cálculos, gráficos y las herramientas del reporte. Las aplicaciones utilizan el mismo intérprete en los comandos de esta guía.

## 2. Encender y comprobar XAMPP

1. Abrir XAMPP Control Panel.
2. Pulsar **Start** en la fila **MySQL**.
3. Esperar a que indique que está en ejecución y anotar su puerto. Esta guía utiliza `3306`.
4. Para abrir phpMyAdmin, iniciar también Apache y visitar `http://localhost/phpmyadmin`.

Las interfaces de los buscadores las sirve Python en los puertos 8000 y 8001. Apache permite utilizar phpMyAdmin en este procedimiento.

El componente llamado MySQL en las versiones actuales de XAMPP utiliza MariaDB. El reporte de referencia se obtuvo con MySQL 8.0.44. Esta guía utiliza XAMPP para repetir el experimento y registrar la versión efectiva del servidor. La coincidencia de rankings y puntajes se comprueba con los resultados obtenidos en esa instalación. Para reproducir el entorno original se puede seguir la sección de MySQL 8.0 del [README de evaluación](README.md). [FAQ oficial de XAMPP](https://www.apachefriends.org/faq_windows.html)

En la pestaña SQL de phpMyAdmin ejecutar lo siguiente, o utilizar el cliente de XAMPP con el comando incluido después.

```sql
SELECT VERSION();
SHOW VARIABLES LIKE 'innodb_ft_min_token_size';
SHOW VARIABLES LIKE 'innodb_ft_max_token_size';
SHOW VARIABLES LIKE 'innodb_ft_enable_stopword';
```

```powershell
& 'C:\xampp\mysql\bin\mysql.exe' --host=127.0.0.1 --port=3306 --user=root --execute="SELECT VERSION();"
```

Si XAMPP está instalado en otra carpeta, ajustar la ruta del cliente. Si el usuario root tiene contraseña, agregar `-p` para que el cliente la solicite. En los bloques de los buscadores se debe establecer esa contraseña en la variable `DB_CONTRASENA` correspondiente.

En el experimento original el índice InnoDB admitía términos de 3 a 84 caracteres y tenía stopwords activas. FULLTEXT depende de estos parámetros y de la colación. Conservar la configuración observada junto con la versión y los resultados de la repetición. [Documentación de FULLTEXT en MariaDB](https://mariadb.com/docs/server/ha-and-performance/optimization-and-tuning/optimization-and-indexes/full-text-indexes/full-text-index-overview)

Si XAMPP muestra un error de arranque, revisar el registro del servidor antes de continuar. El mensaje `Incorrect file format 'db'` corresponde a un fallo al abrir una tabla de privilegios. La ejecución requiere resolver ese arranque o utilizar la instancia independiente de MySQL descrita en el README.

## 3. Ejecutar las aplicaciones manualmente

Abrir dos terminales PowerShell en la raíz del repositorio. En VS Code se puede abrir esa carpeta y utilizar **Terminal > Nueva terminal**. Comprobar `Test-Path '.\buscador2\main.py'` en cada terminal si hay dudas sobre su ubicación.

Los siguientes nombres de base están destinados a una primera comprobación manual. Para una repetición independiente, elegir un nuevo sufijo para ambas bases y para el almacén de archivos. Cada sistema debe contener exactamente los 30 documentos de la colección al evaluar.

### Terminal A, buscador2

```powershell
$env:INDEXADOR_DB_HOST = '127.0.0.1'
$env:INDEXADOR_DB_PUERTO = '3306'
$env:INDEXADOR_DB_USUARIO = 'root'
$env:INDEXADOR_DB_CONTRASENA = ''
$env:INDEXADOR_DB_NOMBRE = 'ada5_manual_indexador'
$env:INDEXADOR_HOST = '127.0.0.1'
$env:INDEXADOR_PUERTO = '8000'
$env:INDEXADOR_CARPETA_ALMACEN = Join-Path (Get-Location).Path 'tmp\ada5_manual_indexador\almacen'

& '.\.venv-evaluacion\Scripts\python.exe' '.\buscador2\main.py'
```

Abrir `http://127.0.0.1:8000` y mantener la terminal abierta.

### Terminal B, Búsqueda empresarial

```powershell
$env:EMPRESARIAL_DB_HOST = '127.0.0.1'
$env:EMPRESARIAL_DB_PUERTO = '3306'
$env:EMPRESARIAL_DB_USUARIO = 'root'
$env:EMPRESARIAL_DB_CONTRASENA = ''
$env:EMPRESARIAL_DB_NOMBRE = 'ada5_manual_empresarial'
$env:EMPRESARIAL_HOST = '127.0.0.1'
$env:EMPRESARIAL_PUERTO = '8001'

& '.\.venv-evaluacion\Scripts\python.exe' '.\Busqueda empresarial\main.py'
```

Abrir `http://127.0.0.1:8001` y mantener la terminal abierta. Las aplicaciones crean sus bases y tablas al arrancar, por lo que la cuenta de conexión necesita los permisos correspondientes.

## 4. Cargar documentos y obtener los rankings

1. En cada interfaz abrir **Subir archivos**.
2. Seleccionar los 30 archivos `doc001.txt` a `doc030.txt` de `evaluacion/coleccion/`.
3. Confirmar la carga y verificar que cada buscador indique 30 documentos.
4. En Búsqueda empresarial seleccionar **Lenguaje natural**.
5. Ejecutar las cinco consultas literales de la tabla siguiente en ambos sistemas.
6. Anotar todos los nombres de archivo devueltos, en el orden presentado. Guardar también relevancia y coseno cuando aparezcan.

La relevancia de un documento frente a una necesidad de información está fijada en `protocolo.json`. La etiqueta es binaria. Los cuatro documentos de cada fila son relevantes para esa consulta y los otros 26 son irrelevantes.

| ID | Consulta literal | Documentos relevantes |
|---|---|---|
| Q1 | energía solar viviendas | doc008.txt, doc014.txt, doc003.txt, doc002.txt |
| Q2 | prevención diabetes ejercicio | doc023.txt, doc005.txt, doc006.txt, doc016.txt |
| Q3 | seguridad contraseñas autenticación | doc010.txt, doc004.txt, doc009.txt, doc012.txt |
| Q4 | reciclaje residuos electrónicos | doc029.txt, doc025.txt, doc001.txt, doc019.txt |
| Q5 | riego eficiente agricultura | doc017.txt, doc011.txt, doc013.txt, doc021.txt |

Para confirmar los totales desde phpMyAdmin, ejecutar después de la carga lo siguiente.

```sql
SELECT COUNT(*) AS documentos FROM ada5_manual_indexador.documentos;
SELECT COUNT(*) AS documentos FROM ada5_manual_empresarial.documentos;
```

Ambas consultas deben devolver 30.

## 5. Convertir resultados por documento en métricas de evaluación

El buscador presenta el ranking y los puntajes de sus documentos. La evaluación utiliza ese ranking y las etiquetas del protocolo para calcular la calidad de recuperación.

Para cada consulta, considerar recuperados todos los documentos devueltos. Si `N=30` es el tamaño de la colección y `R=4` su total de relevantes, calcular lo siguiente.

| Cantidad | Cálculo |
|---|---|
| TP | Número de documentos recuperados que están en la lista de relevantes |
| FP | Número de recuperados que son irrelevantes |
| FN | R - TP |
| TN | N - TP - FP - FN |
| Precisión | TP / (TP + FP) |
| Exhaustividad o recall | TP / R |
| Accuracy | (TP + TN) / N |

La tabla de contingencia se organiza de esta forma.

| | Relevante | Irrelevante |
|---|---|---|
| Recuperado | TP | FP |
| Sin recuperar | FN | TN |

Para cada posición `k` del ranking, contar los relevantes acumulados hasta esa posición. Calcular `P(k) = relevantes acumulados / k` y `recall(k) = relevantes acumulados / R`. Estos pares son los puntos de la curva de precisión versus exhaustividad, con recall en el eje horizontal y precisión en el vertical.

Calcular **AP** sumando `P(k)` únicamente en las posiciones donde el documento es relevante y dividiendo entre `R=4`. Los relevantes ausentes se mantienen en el denominador. Calcular **MAP** promediando las AP de Q1, Q2, Q3, Q4 y Q5 para cada sistema. Si no hay resultados, se registra precisión y AP igual a cero. [Definición de AP, MAP y curvas interpoladas](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html)

### Ejemplo comprobable con Q2

Este fue el orden observado en el experimento original con MySQL 8.0.44.

| k | buscador2 | Relevante | P(k) | recall(k) | Empresarial | Relevante | P(k) | recall(k) |
|---|---|---|---|---|---|---|---|---|
| 1 | doc005.txt | Sí | 1.0000 | 0.25 | doc005.txt | Sí | 1.0000 | 0.25 |
| 2 | doc022.txt | No | 0.5000 | 0.25 | doc022.txt | No | 0.5000 | 0.25 |
| 3 | doc006.txt | Sí | 0.6667 | 0.50 | doc006.txt | Sí | 0.6667 | 0.50 |
| 4 | doc023.txt | Sí | 0.7500 | 0.75 | doc015.txt | No | 0.5000 | 0.50 |
| 5 | doc015.txt | No | 0.6000 | 0.75 | doc023.txt | Sí | 0.6000 | 0.75 |

En ambos sistemas el relevante `doc016.txt` quedó ausente. Por tanto, TP=3, FP=2, FN=1 y TN=24.

```text
Precisión = 3/5 = 0.60
Recall = 3/4 = 0.75
Accuracy = (3+24)/30 = 0.90

AP buscador2 = (1/1 + 2/3 + 3/4)/4 = 0.6041667
AP empresarial = (1/1 + 2/3 + 3/5)/4 = 0.5666667
```

Los puntajes tf-idf, coseno y FULLTEXT se usan para presentar y explicar el ranking de los buscadores. La precisión, recall, accuracy y AP dependen del orden recuperado y de sus etiquetas.

### Comprobar un ranking manual con el módulo de métricas

Abrir otra terminal en la raíz del repositorio. El bloque siguiente toma la lista de relevantes del protocolo y calcula las métricas del ranking de buscador2 en el ejemplo. Para comprobar otro ranking, cambiar `consulta_id` y escribir en `ranking` los nombres en el orden obtenido en la interfaz.

```powershell
@'
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path("evaluacion").resolve()))
from metricas import evaluar_ranking

protocolo = json.loads(Path("evaluacion/protocolo.json").read_text(encoding="utf-8"))
consulta_id = "Q2"
ranking = ["doc005.txt", "doc022.txt", "doc006.txt", "doc023.txt", "doc015.txt"]
consulta = next(q for q in protocolo["consultas"] if q["id"] == consulta_id)
universo = [d["nombre"] for d in protocolo["documentos"]]
metricas = evaluar_ranking(ranking, consulta["relevantes"], universo)
for clave in ("TP", "FP", "FN", "TN", "precision", "recall", "accuracy", "AP"):
    print(clave, metricas[clave])
for punto in metricas["puntos"]:
    print(punto)
'@ | .\.venv-evaluacion\Scripts\python.exe -
```

## 6. Repetir la evaluación automática en XAMPP

El evaluador automatizado puede ejecutarse desde otra terminal en la raíz del repositorio, con XAMPP funcionando. Utiliza los puertos HTTP 8100 y 8101 y crea dos bases nuevas en cada ejecución. Carga los archivos a través de los controladores HTTP de las aplicaciones y verifica el orden HTML contra el del motor.

```powershell
$env:EVAL_DB_HOST = '127.0.0.1'
$env:EVAL_DB_PUERTO = '3306'
$env:EVAL_DB_USUARIO = 'root'
$env:EVAL_DB_CONTRASENA = ''

.\.venv-evaluacion\Scripts\python.exe -m unittest discover -s evaluacion -p test_metricas.py -v
.\.venv-evaluacion\Scripts\python.exe evaluacion/evaluar.py
```

Ajustar el puerto y la contraseña al servidor de XAMPP. Si los puertos HTTP están ocupados, agregar `--puerto-base 8200` al comando de `evaluar.py` para utilizar 8200 y 8201.

Al terminar, `evaluar.py` publica la nueva ejecución en `evaluacion/resultados/ultima_ejecucion.json` y conserva su evidencia en una carpeta con fecha. Los originales de referencia permanecen en `evaluacion/resultados/20261116_113239_660314/`. Las bases de esta nueva ejecución son independientes de las bases de carga manual.

Para mostrar la tabla de resultados calculada en la nueva ejecución, ejecutar este bloque.

```powershell
$resultado = Get-Content -Raw -Encoding utf8 '.\evaluacion\resultados\ultima_ejecucion.json' | ConvertFrom-Json

foreach ($sistema in $resultado.sistemas.PSObject.Properties) {
    Write-Output $sistema.Name
    foreach ($consulta in $sistema.Value.metricas.PSObject.Properties) {
        [pscustomobject]@{
            Consulta = $consulta.Name
            TP = $consulta.Value.TP
            FP = $consulta.Value.FP
            FN = $consulta.Value.FN
            TN = $consulta.Value.TN
            Precision = $consulta.Value.precision
            Recall = $consulta.Value.recall
            Accuracy = $consulta.Value.accuracy
            AP = $consulta.Value.AP
        }
    }
    Write-Output ("MAP = " + $sistema.Value.MAP)
}
```

El PDF guardado en `output/pdf/comparacion_buscadores.pdf` documenta el experimento original con MySQL 8.0.44. La nueva ejecución con XAMPP tiene su propia versión, rankings y métricas en el JSON. El script `generar_reporte.py` contiene explicaciones específicas del experimento original; un reporte de una nueva ejecución debe adaptar esas conclusiones a lo observado.

## 7. De dónde salió la tabla final del reporte

Los cálculos se ejecutaron con código Python guardado en este repositorio.

| Componente | Trabajo realizado |
|---|---|
| Motores originales | Calculan puntajes y ordenan los documentos |
| `evaluar.py` | Carga la colección, consulta ambos sistemas y recoge rankings y respuestas |
| `protocolo.json` | Define las consultas y las etiquetas de relevancia fijadas previamente |
| `metricas.py`, función `evaluar_ranking` | Calcula TP, FP, FN, TN, precisión, recall, accuracy, AP y puntos de curva |
| `evaluar.py`, promedio de AP | Obtiene MAP y guarda los resultados JSON |
| `evaluar.py`, función `validar_metricas` | Revisa los conteos con conjuntos y AP con fracciones exactas |
| `generar_reporte.py` | Lee el JSON, dibuja las curvas y presenta tablas y cálculos en el PDF |

La curva media del PDF usa precisión interpolada en once niveles de recall. En cada nivel se toma la mayor precisión alcanzada con un recall igual o superior, o cero si no existe ese punto. Después se promedian las cinco consultas.

Estos son los valores de referencia obtenidos con MySQL 8.0.44.

| Consulta | AP buscador2 | AP empresarial |
|---|---|---|
| Q1 | 0.358333 | 0.358333 |
| Q2 | 0.604167 | 0.566667 |
| Q3 | 0.400000 | 0.400000 |
| Q4 | 0.525000 | 0.525000 |
| Q5 | 0.479167 | 0.441667 |
| MAP | 0.473333 | 0.458333 |

Las cinco tablas de contingencia dieron TP=3, FP=2, FN=1 y TN=24 en ambos sistemas. De ahí salen precisión 0.60, recall 0.75 y accuracy 0.90. La diferencia de MAP procede de la ordenación en Q2 y Q5. La evidencia definitiva incluye los HTML, los puntajes completos y los detalles del cálculo tf-idf.

## 8. Finalizar la comprobación

Detener cada aplicación con `Ctrl+C` en su terminal. En XAMPP, pulsar **Stop** en MySQL cuando se haya terminado de utilizar el servidor. Conservar la versión del servidor, las consultas, los rankings y las tablas calculadas para explicar cualquier diferencia frente al reporte de referencia.
