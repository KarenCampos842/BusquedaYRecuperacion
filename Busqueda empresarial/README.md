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
