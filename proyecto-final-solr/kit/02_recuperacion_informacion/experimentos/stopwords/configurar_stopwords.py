"""P03-03 · Tipo alternativo con palabras vacías (StopFilter gestionado).

Plantilla del kit completada por Karen (integrante B). La lógica vive en
proyecto-final-solr/analisis_es/ para no duplicarla; este script solo
configura el tipo `text_es_stop`: text_es_ri + filtro de palabras vacías.
text_es_ri se conserva sin cambios como control experimental.

Uso (desde proyecto-final-solr/):
    py kit/02_recuperacion_informacion/experimentos/stopwords/configurar_stopwords.py              # core de prueba ri_analisis_es
    py kit/02_recuperacion_informacion/experimentos/stopwords/configurar_stopwords.py --core ri    # solo tras acordarlo con Joseph
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "analisis_es"))

from configurar_analizadores import main  # noqa: E402

if __name__ == "__main__":
    main(["--tipos", "text_es_stop", *sys.argv[1:]])
