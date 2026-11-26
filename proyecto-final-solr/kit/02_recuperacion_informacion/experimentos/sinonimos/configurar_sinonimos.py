"""P03-08 · Tipo con sinónimos solo en el analizador de consulta.

Plantilla del kit completada por Karen (integrante B). La lógica vive en
proyecto-final-solr/analisis_es/ para no duplicarla; este script solo
configura el tipo `text_es_proyecto`: text_es_proyecto (palabras vacías, términos protegidos, stemming y SynonymGraph en consulta).
text_es_ri se conserva sin cambios como control experimental.

Uso (desde proyecto-final-solr/):
    py kit/02_recuperacion_informacion/experimentos/sinonimos/configurar_sinonimos.py              # core de prueba ri_analisis_es
    py kit/02_recuperacion_informacion/experimentos/sinonimos/configurar_sinonimos.py --core ri    # solo tras acordarlo con Joseph
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "analisis_es"))

from configurar_analizadores import main  # noqa: E402

if __name__ == "__main__":
    main(["--tipos", "text_es_proyecto", *sys.argv[1:]])
