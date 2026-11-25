# AGENTS.md — Proyecto final de Búsqueda y Recuperación

## Contexto y alcance
- Proyecto académico de 4 integrantes. Entrega: 2 de diciembre de 2026.
- Motor de búsqueda: Apache Solr 10. Backend: Python + FastAPI. Frontend: Angular + TypeScript. Crawler e indexación: Python.
- El corpus web **debe proceder de páginas reales de Internet**, según aclaración del profesor; no usar páginas HTML locales como corpus final.
- Fuente candidata para el piloto: MDN Web Docs (`https://developer.mozilla.org/es/docs/Web/`). No se ha aprobado como fuente definitiva hasta evaluar el piloto.
- Alcance del piloto: **1 página primero**; después hasta **12 artículos útiles** (4 JavaScript, 4 HTML, 4 CSS), solo si el acceso está permitido.
- Objetivo general: nueve funciones obligatorias de la rúbrica y dos extras (PDF con texto y recomendaciones). No implementar otras fases hasta indicación explícita.

## Material docente y rutas
- El ZIP docente v2 contiene `estudiante/03_recuperacion_web/crawler/crawler_basico.py`, un crawler introductorio basado en `HTMLParser`, `urllib` y recorrido con `deque`.
- Conservar el archivo original. Implementar la adaptación de MDN en un módulo independiente y pequeño, reutilizando lo adecuado.
- El crawler original no comprueba `robots.txt`, no fija límite de páginas, no incorpora pausas, no extrae solo el contenido central y no gestiona errores HTTP con robustez.
- Los scripts de Solr están en `estudiante/03_recuperacion_web/solr/`. No es necesario iniciar Solr para la primera prueba de extracción.
- No usar `docente/soluciones/` como reemplazo automático de código probado.

## Reglas del crawling externo
1. Antes de descargar cualquier artículo, consultar `https://developer.mozilla.org/robots.txt`; comprobar la autorización de la URL con `urllib.robotparser` y el User-Agent configurado. Si la política no puede recuperarse o interpretarse de modo seguro, **detener el rastreo** y reportarlo.
2. Enviar un User-Agent identificable con propósito académico; no falsear Googlebot u otros agentes.
3. Seguir solo URLs HTTPS dentro de `developer.mozilla.org` y rutas autorizadas bajo `/es/docs/Web/JavaScript/`, `/es/docs/Web/HTML/` y `/es/docs/Web/CSS/`; incluir las páginas raíz de las categorías cuando corresponda. Verificar también el destino de cada redirección antes de descargarlo.
4. Respetar `robots.txt`, indicaciones aplicables de frecuencia, términos de uso, `Retry-After` y bloqueos. Ejecutar secuencialmente con una pausa conservadora configurable (inicialmente 3 segundos). No intentar eludir límites ni sistemas antibots.
5. No aceptar contenido que no sea HTML; fijar timeout y controlar errores de red, HTTP 403/404/429/5xx, redirecciones, páginas en otro idioma y HTML inválido.
6. Normalizar URLs, eliminar fragmentos, evitar duplicados y descartar enlaces fuera del alcance. Fijar máximo de artículos y profundidad.
7. Seleccionar el contenido principal del artículo (evaluar `article.main-page-content`, con comprobación real del HTML). No indexar menús, navegación, footer ni texto de toda la página sin filtrar.
8. Conservar atribución y URL de origen de MDN; revisar las condiciones CC BY-SA y excepciones antes de distribuir el corpus. No descargar imágenes, archivos multimedia ni recursos innecesarios.

## Esquema provisional del piloto
Guardar JSON UTF-8 con, como mínimo: `id`, `titulo`, `contenido`, `url`, `categoria`, `idioma`, `tipo_fuente`, `profundidad`, `fecha_rastreo`.
- `categoria` a partir de JavaScript, HTML o CSS según la ruta.
- `tipo_fuente` = `web`.
- Mantener `enlaces_salientes` si resulta útil para justificar el crawling.
- Los datos y cifras de evaluación deben venir de ejecuciones reales, nunca inventarse.
- Guardar un reporte separado con URLs visitadas, aceptadas, rechazadas, códigos HTTP y motivos.

## Organización del repositorio
- Trabajar exclusivamente dentro de `proyecto-final-solr/`; no modificar `Busqueda empresarial/`, `buscador2/`, `evaluacion/`, `Img/` u otras entregas anteriores.
- Crear una rama de trabajo propia; no hacer push a `main`, merge, commits ni cambios en Todoist sin autorización expresa.
- No borrar volúmenes de Docker, índices o archivos de otros integrantes.
- No agregar secretos, claves o datos pesados innecesarios al control de versiones.

## Flujo de Codex para cada solicitud
1. Leer primero `AGENTS.md` y los archivos involucrados. **No recorrer todo el repositorio** si no es necesario.
2. Trabajar en una sola tarea por petición. Primero explicar plan breve; modificar solo si el usuario lo solicita.
3. Antes de usar Internet desde el código, comprobar la política de rastreo y solicitar aprobación de la ejecución si corresponde.
4. Ejecutar pruebas mínimas; distinguir explícitamente pruebas ejecutadas de pruebas propuestas.
5. Responder en español, de forma breve: archivos modificados, comandos ejecutados, resultado, errores y siguiente paso.
6. Para el primer turno de Codex: **analizar solamente**, sin crear ni modificar archivos y sin ejecutar crawling.
