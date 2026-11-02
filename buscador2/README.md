## Requisitos

- Python 3.10 o superior
- MySQL 8 o MariaDB en ejecución (por ejemplo, XAMPP)

## Ejecutar

```bash
git clone https://github.com/KarenCampos842/BusquedaYRecuperacion.git
cd <carpeta-del-repositorio>
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

Se abre `http://localhost:8000/` en el navegador. La base de datos `indexador` y sus tablas se crean solas.

## Configuración de MySQL

Por defecto se conecta a `localhost:3306` con usuario `root` y sin contraseña. Para cambiarlo, define variables de entorno antes de `python main.py`:

| Variable | Por defecto |
|---|---|
| `INDEXADOR_DB_HOST` | `localhost` |
| `INDEXADOR_DB_PUERTO` | `3306` |
| `INDEXADOR_DB_USUARIO` | `root` |
| `INDEXADOR_DB_CONTRASENA` | *(vacía)* |
| `INDEXADOR_DB_NOMBRE` | `indexador` |
| `INDEXADOR_PUERTO` | `8000` |

PowerShell: `$env:INDEXADOR_DB_CONTRASENA="mi_clave"`
Linux / macOS: `export INDEXADOR_DB_CONTRASENA="mi_clave"`

## Uso

1. Clic en la flecha de arriba a la derecha y sube uno o varios `.txt`.
2. Escribe tu búsqueda en la caja y pulsa Enter.
3. Descarga los archivos desde los resultados.

