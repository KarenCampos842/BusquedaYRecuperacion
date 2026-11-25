# Recuperación Web
1. Sirva `miniweb`: `python -m http.server 8000`.
2. En `crawler`: `python crawler_basico.py`.
3. En `pagerank`: `python calcular_pagerank.py`.
4. Desde este directorio: `python solr/configurar_campos_web.py` y `python solr/indexar_web.py`.

Pipeline: HTML → extracción → enlaces → grafo → PageRank → Solr.
