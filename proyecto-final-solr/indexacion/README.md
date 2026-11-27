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
en campos del contrato y reglas `copyField` sin revisión. Nunca envía
`replace-field`, `delete-field` ni operaciones sobre tipos.

La validación actual de `copyField` es estricta: rechaza cualquier regla existente.
Cuando se integren Suggester/SpellCheck, deberá ajustarse para admitir las reglas
autorizadas por el equipo y seguir rechazando las no autorizadas. Esa adaptación
y las funcionalidades de esos componentes quedan fuera de P01-05.

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

## Antes de P02-11

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
