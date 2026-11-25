# Laboratorio opcional: Apache Nutch + Solr

Este directorio cierra la brecha de los capítulos 12 y 13 del Manual Web sin
sustituir el crawler didáctico.

## Alcance
Nutch se introduce después de comprender semilla, frontera, visitados, profundidad,
normalización y extracción. La práctica requiere instalar Apache Nutch por separado.

Nutch 1.22 dispone de un `indexwriter.solr`, es decir, un plugin de escritura para
enviar documentos a Apache Solr. La configuración concreta puede variar según la
distribución y el entorno del laboratorio; por ello este kit incluye una guía de
verificación y no distribuye binarios de terceros.

## Evidencias mínimas
1. Crear una lista de semillas controlada.
2. Limitar el rastreo al sitio de práctica.
3. Ejecutar un ciclo pequeño de crawling.
4. Configurar el escritor Solr.
5. Comprobar en Solr los documentos recibidos.
6. Comparar los campos obtenidos con los del crawler básico.

Referencias oficiales:
- Apache Nutch 1.22 API: paquete `org.apache.nutch.indexwriter.solr`.
- Apache Solr: documentación del endpoint e indexación.
