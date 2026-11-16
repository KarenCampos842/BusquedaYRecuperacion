# Búsqueda empresarial

Versión del buscador de "Indización y búsqueda" (`buscador2`) que guarda el texto completo de cada archivo en MySQL, en una columna con índice `FULLTEXT`, y deja que MySQL calcule la relevancia y el ranking con `MATCH(...) AGAINST(...)`.

Usa **otra base de datos** (`busqueda_empresarial`) y **otro puerto** (`8001`), así que puede correr al mismo tiempo que `buscador2` (base `indexador`, puerto `8000`) para comparar resultados con los mismos archivos.

## Requisitos

- Python 3.10 o superior
- MySQL 8 o MariaDB 10.0.5 o superior (por ejemplo, XAMPP)

## Ejecutar

```bash
cd "Busqueda empresarial"
python -m venv .venv
```

Activar el entorno virtual:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Linux / macOS: `source .venv/bin/activate`

Instalar y arrancar:

```bash
pip install -r requirements.txt
python main.py
```

Se abre `http://localhost:8001/`. La base `busqueda_empresarial`, la tabla `documentos` con su índice FULLTEXT y la tabla `stopwords_es` se crean solas.

## Configuración de MySQL

Las variables usan el prefijo `EMPRESARIAL_` para no chocar con las de `buscador2`:

| Variable | Por defecto |
|---|---|
| `EMPRESARIAL_DB_HOST` | `localhost` |
| `EMPRESARIAL_DB_PUERTO` | `3306` |
| `EMPRESARIAL_DB_USUARIO` | `root` |
| `EMPRESARIAL_DB_CONTRASENA` | *(vacía)* |
| `EMPRESARIAL_DB_NOMBRE` | `busqueda_empresarial` |
| `EMPRESARIAL_PUERTO` | `8001` |

PowerShell: `$env:EMPRESARIAL_DB_CONTRASENA="mi_clave"`

### Ajustes recomendados para una comparación justa

Por defecto MySQL no indexa palabras de menos de 3 caracteres; `buscador2` indexa desde 2. Para igualarlos, agrega en `my.ini` (XAMPP: `xampp\mysql\bin\my.ini`), dentro de `[mysqld]`:

```ini
innodb_ft_min_token_size=2
```

Reinicia MySQL y reconstruye el índice (los documentos no se borran):

```bash
python reconstruir_indice.py
```

Si un archivo grande se rechaza al subirlo, revisa `max_allowed_packet` en el mismo `my.ini` (por ejemplo `max_allowed_packet=16M`).

## Uso

1. Clic en la flecha de arriba a la derecha y sube uno o varios `.txt`.
2. Elige el modo de búsqueda:
   - **Lenguaje natural**: equivalente a `buscador2`.
   - **Booleano**: `+obligatoria -excluida palabra* "frase exacta"`.
   - **Expansión de consulta**: agrega palabras de los mejores resultados.
3. Escribe tu búsqueda y pulsa Enter.
4. Debajo de los resultados, "Ver la consulta SQL enviada a MySQL" muestra la sentencia exacta.

## Qué cambió respecto a buscador2

| | buscador2 | Búsqueda empresarial |
|---|---|---|
| Texto del archivo | En la carpeta `almacen/` | En `documentos.contenido` (`MEDIUMTEXT`) |
| Índice invertido | Tablas `diccionario`, `posting`, `posicion` hechas en Python | Índice `FULLTEXT ft_contenido`, mantenido por MySQL |
| Normalización | `texto.normalizar()` | Collation `utf8mb4_unicode_ci` de la columna |
| Palabras vacías | `stopwords_es.txt` en Python | La misma lista, cargada en la tabla `stopwords_es` y usada por InnoDB |
| Relevancia | Σ tf·idf en `ranking.py` | `MATCH(contenido) AGAINST(...)`: Σ tf·idf² |
| Ranking | `ranking.ordenar()` con desempate por coseno | `ORDER BY relevancia DESC, nombre_archivo` |
| Coseno y detalle tf-idf | Sí | No (MySQL no los calcula) |
| Operadores | No | Modo booleano y expansión de consulta |

Archivos principales:

- `base_datos/esquema.sql`: tabla `documentos` con la columna y el índice FULLTEXT.
- `base_datos/esquema_stopwords.sql` y `base_datos/inicializador.py`: palabras vacías en español para InnoDB.
- `base_datos/repositorios/repositorio_fulltext.py`: la consulta `MATCH ... AGAINST`.
- `busqueda/motor_busqueda.py`: prepara avisos, fragmentos y mide el tiempo.
- `busqueda/ranking.py`: los tres modos de búsqueda; ya no calcula pesos.
- `reconstruir_indice.py`: vuelve a crear el índice tras cambiar la configuración.
