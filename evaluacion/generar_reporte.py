"""Genera el PDF y las curvas a partir de una ejecución comprobada."""
import argparse
from datetime import datetime
from html import escape
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent.parent / "tmp/matplotlib"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

RAIZ = Path(__file__).resolve().parent
REPO = RAIZ.parent
SALIDA = REPO / "output" / "pdf"
NOMBRES = {"buscador2": "buscador2", "empresarial": "Búsqueda empresarial"}
PALETA = {"buscador2": "#000000", "empresarial": "#555555"}
NEGRO = colors.black


def curvas(datos):
    carpeta = SALIDA / "figuras"
    carpeta.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.dpi": 190})
    for consulta in datos["protocolo"]["consultas"]:
        fig, ax = plt.subplots(figsize=(7.1, 2.7), layout="constrained")
        for indice, (sistema, resultados) in enumerate(datos["sistemas"].items()):
            puntos = resultados["metricas"][consulta["id"]]["puntos"]
            x = [p["recall"] for p in puntos]
            y = [p["precision"] for p in puntos]
            ax.plot(x, y, color=PALETA[sistema], label=NOMBRES[sistema],
                    marker="o" if indice == 0 else "s", markersize=5,
                    linestyle="-" if indice == 0 else "--", linewidth=1.7,
                    markerfacecolor="none" if indice else PALETA[sistema])
            for p in puntos:
                ax.annotate(str(p["posicion"]), (p["recall"], p["precision"]),
                            xytext=(4, 7 if indice == 0 else -12),
                            textcoords="offset points", fontsize=8, color=PALETA[sistema])
        configurar_ejes(ax)
        fig.savefig(carpeta / f"{consulta['id']}.png")
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(7.1, 3.25), layout="constrained")
    for sistema, resultados in datos["sistemas"].items():
        ax.plot([i / 10 for i in range(11)], resultados["curva_media"],
                marker="o" if sistema == "buscador2" else "s", color=PALETA[sistema],
                label=NOMBRES[sistema], linestyle="-" if sistema == "buscador2" else "--")
    configurar_ejes(ax)
    fig.savefig(carpeta / "media_interpolada.png")
    plt.close(fig)


def configurar_ejes(ax):
    ax.set(xlim=(-0.035, 1.035), ylim=(-0.035, 1.065),
           xlabel="Exhaustividad (recall)", ylabel="Precisión",
           xticks=[i / 10 for i in range(11)], yticks=[i / 5 for i in range(6)])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.24), ncol=2,
              fontsize=9, frameon=False)


def generar(archivo):
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    protocolo = datos["protocolo"]
    sistemas = datos["sistemas"]
    assert len(protocolo["documentos"]) == 30 and len(protocolo["consultas"]) == 5
    SALIDA.mkdir(parents=True, exist_ok=True)
    curvas(datos)
    # Arial admite los acentos de los textos y mantiene el PDF autocontenido.
    fuentes = Path("C:/Windows/Fonts")
    if (fuentes / "arial.ttf").exists():
        normal, negrita = fuentes / "arial.ttf", fuentes / "arialbd.ttf"
    else:
        normal = Path(matplotlib.get_data_path()) / "fonts/ttf/DejaVuSans.ttf"
        negrita = normal.with_name("DejaVuSans-Bold.ttf")
    pdfmetrics.registerFont(TTFont("Texto", str(normal)))
    pdfmetrics.registerFont(TTFont("TextoBold", str(negrita)))
    pdfmetrics.registerFontFamily("Texto", normal="Texto", bold="TextoBold", italic="Texto", boldItalic="TextoBold")
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle("TituloReporte", fontName="TextoBold", fontSize=25,
                              leading=30, textColor=NEGRO, spaceAfter=15))
    estilos.add(ParagraphStyle("Seccion", fontName="TextoBold", fontSize=16,
                              leading=20, textColor=NEGRO, spaceAfter=12))
    estilos.add(ParagraphStyle("Apartado", fontName="TextoBold", fontSize=11,
                              leading=15, textColor=NEGRO, spaceBefore=9, spaceAfter=6))
    estilos.add(ParagraphStyle("TextoReporte", fontName="Texto", fontSize=9.6,
                              leading=14, spaceAfter=9))
    estilos.add(ParagraphStyle("Pequeno", fontName="Texto", fontSize=8,
                              leading=11, spaceAfter=6))
    estilos.add(ParagraphStyle("Celda", fontName="Texto", fontSize=8,
                              leading=10))
    estilos.add(ParagraphStyle("CabeceraTabla", fontName="TextoBold", fontSize=8,
                              leading=10, textColor=NEGRO))
    historia = []
    ancho = A4[0] - 96

    def par(texto, estilo="TextoReporte"):
        return Paragraph(texto, estilos[estilo])

    def escribir(texto, estilo="TextoReporte"):
        historia.append(par(texto, estilo))

    def titulo(texto):
        escribir(texto, "Seccion")

    def apartado(texto):
        escribir(texto, "Apartado")

    def tabla(filas, anchos=None, compacto=False):
        contenido = [
            [par(escape(str(c)), "CabeceraTabla" if i == 0 else "Celda") for c in fila]
            for i, fila in enumerate(filas)
        ]
        t = Table(contenido, colWidths=anchos, repeatRows=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3 if compacto else 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 if compacto else 4),
        ]))
        historia.extend([t, Spacer(1, 10)])

    fecha = datetime.fromisoformat(datos["fecha"]).strftime("%d/%m/%Y")
    mapa = {s: x["MAP"] for s, x in sistemas.items()}
    diferencia = mapa["buscador2"] - mapa["empresarial"]
    ganador = max(mapa, key=mapa.get)
    escribir("Comparación de buscadores", "TituloReporte")
    escribir("Precisión, exhaustividad y Mean Average Precision", "Seccion")
    escribir(f"Búsqueda y recuperación de información en la web | {fecha}", "Pequeno")
    escribir("Se evaluaron las aplicaciones del repositorio con 30 documentos sintéticos en español y cinco necesidades de información. Cada consulta tiene cuatro documentos relevantes. Ambos sistemas recibieron la misma colección mediante el formulario HTTP de carga y ejecutaron las mismas cadenas de consulta.")
    apartado("Resultado de la evaluación")
    filas = [["Consulta", "AP buscador2", "AP empresarial"]]
    for q in protocolo["consultas"]:
        filas.append([q["id"], *[f"{sistemas[s]['metricas'][q['id']]['AP']:.4f}" for s in sistemas]])
    filas.append(["MAP", f"{mapa['buscador2']:.4f}", f"{mapa['empresarial']:.4f}"])
    tabla(filas, [ancho * 0.28, ancho * 0.36, ancho * 0.36])
    escribir(f"<b>{NOMBRES[ganador]} obtuvo el mayor MAP en esta colección.</b> La diferencia absoluta fue {abs(diferencia):.4f}, equivalente a {abs(diferencia) * 100:.2f} puntos porcentuales. En las cinco consultas, ambos sistemas recuperaron tres relevantes y dos irrelevantes. La precisión final fue 0.60, la exhaustividad 0.75 y la accuracy 0.90.")
    escribir("La diferencia de MAP se relaciona con el orden de resultados empatados en relevancia. buscador2 utiliza el coseno como desempate y Búsqueda empresarial utiliza el nombre del archivo. Las tablas por consulta conservan ese orden original.")
    apartado("Alcance de la conclusión")
    escribir("La colección fue redactada con asistencia de IA y sus etiquetas se fijaron antes de la ejecución definitiva. Los identificadores de archivo se asignaron con una semilla fija y no expresan su relevancia. Los textos incluyen distractores léxicos y paráfrasis. El tamaño, el contexto compartido por tema y los empates limitan la generalización del resultado.")
    escribir(f"Ejecución definitiva {datos['ejecucion']}. El protocolo, los hashes, los HTML y los puntajes completos se conservan en evaluacion/resultados/.", "Pequeno")

    historia.append(PageBreak())
    titulo("Funcionamiento y uso de las aplicaciones")
    apartado("buscador2")
    escribir("Construye un índice invertido incremental en MySQL con tablas de documentos, diccionario, postings y posiciones. Guarda los archivos originales en disco y un fragmento de hasta 50 caracteres por término y documento. Normaliza minúsculas y acentos, conserva la ñ, elimina palabras vacías y admite términos de 2 a 100 caracteres.")
    escribir("El peso es tf × log10(N/df). El ranking utiliza la suma de pesos de los términos de consulta presentes en el documento. Ante un empate utiliza el coseno y después el nombre. El coseno considera los vectores tf-idf de consulta y documento. Un término presente en toda la colección tiene idf igual a cero.")
    apartado("Búsqueda empresarial")
    escribir("Almacena el texto completo en una columna MEDIUMTEXT con índice FULLTEXT de InnoDB. MySQL mantiene el índice y calcula la relevancia mediante MATCH(contenido) AGAINST(...). La aplicación ofrece lenguaje natural, booleano y expansión de consulta. Ordena por relevancia descendente y luego por nombre. Genera fragmentos de hasta 180 caracteres y descarga el texto almacenado en UTF-8.")
    escribir("La comparación utiliza lenguaje natural. Los límites de longitud y la colación se registraron porque influyen en los términos recuperables. La aplicación carga una lista española de stopwords al crear el índice. [2]")
    apartado("Inicio manual desde PowerShell")
    escribir("Con Python 3.10 o superior y MySQL en ejecución, abrir una terminal por aplicación. Desde la carpeta correspondiente, crear un entorno e instalar su archivo requirements.txt.")
    tabla([
        ["Paso", "buscador2", "Búsqueda empresarial"],
        ["Carpeta", "buscador2", "Busqueda empresarial"],
        ["Instalación", "python -m venv .venv", "python -m venv .venv"],
        ["Dependencia", ".venv/Scripts/python.exe -m pip install -r requirements.txt", ".venv/Scripts/python.exe -m pip install -r requirements.txt"],
        ["Inicio", ".venv/Scripts/python.exe main.py", ".venv/Scripts/python.exe main.py"],
        ["URL predeterminada", "http://localhost:8000", "http://localhost:8001"],
        ["Base predeterminada", "indexador", "busqueda_empresarial"],
        ["Variables", "INDEXADOR_DB_*", "EMPRESARIAL_DB_*"],
    ], [ancho * 0.2, ancho * 0.4, ancho * 0.4])
    escribir("La conexión predeterminada usa localhost:3306, usuario root y contraseña vacía. Configurar DB_HOST, DB_PUERTO, DB_USUARIO y DB_CONTRASENA con el prefijo indicado cuando corresponda. El usuario necesita permisos para crear las bases y tablas.")
    escribir("En la interfaz, abrir la carga, seleccionar los .txt y pulsar Subir e indizar. Después escribir la consulta y revisar o descargar los resultados. El límite predeterminado es 5 MiB por petición. Cargar un archivo con el mismo nombre reemplaza su documento.")

    historia.append(PageBreak())
    titulo("Colección y juicios de relevancia")
    escribir("La colección contiene cinco grupos de seis textos. Cada grupo tiene tres relevantes con vocabulario directo, un relevante expresado mediante paráfrasis y dos distractores. Todos los textos tienen entre 150 y 250 palabras y comparten un párrafo contextual dentro de su tema. El título forma parte del contenido indizado.")
    escribir("La relevancia se determina por el propósito y contenido del texto respecto a la necesidad de información. Un documento relevante para una consulta se considera irrelevante para las otras cuatro. El inventario siguiente permite identificar todos los juicios. El protocolo incluye sus hashes SHA-256 y criterios.", "Pequeno")
    filas = [["Archivo", "Título", "Relevante"]]
    for doc in sorted(protocolo["documentos"], key=lambda d: d["nombre"]):
        filas.append([doc["nombre"], doc["titulo"], ", ".join(doc["relevante_para"]) or "Ninguna"])
    tabla(filas, [85, ancho - 155, 70], compacto=True)
    escribir("Los nombres doc001 a doc030 se asignaron mediante random.Random(20261116).shuffle antes de la ejecución definitiva. Esto evita que el identificador codifique directamente la etiqueta utilizada para evaluar.", "Pequeno")

    historia.append(PageBreak())
    titulo("Protocolo de evaluación y métricas")
    escribir("Se crearon dos bases nuevas y un almacén independiente para buscador2. Un proceso por aplicación utilizó su servidor, controladores, indexador y motor originales. Se enviaron los mismos 30 archivos al endpoint /subir mediante multipart/form-data, igual que en el formulario. Después se ejecutaron las cinco consultas mediante /buscar.")
    escribir("Se capturaron las páginas completas y se verificó que su orden coincidiera con el devuelto por el motor. Los puntajes completos proceden de las estructuras originales del buscador. Todos los documentos devueltos se consideran recuperados para la tabla de contingencia. Se conservan los resultados con puntaje cero si la aplicación los devuelve.")
    tabla([
        ["", "Relevante", "Irrelevante"],
        ["Recuperado", "TP", "FP"],
        ["Sin recuperar", "FN", "TN"],
    ], [ancho / 3] * 3)
    escribir("<b>Precisión</b> = TP / (TP + FP). <b>Exhaustividad o recall</b> = TP / (TP + FN). <b>Accuracy</b> = (TP + TN) / N. Para cada posición k se calculan P(k) y recall(k) con los primeros k resultados.")
    escribir("<b>AP</b> = suma de P(k) en las posiciones relevantes / R, donde R es el total de relevantes de la consulta, incluidos los ausentes. <b>MAP</b> = promedio de los cinco valores AP. Si no hay resultados, precisión y AP se registran como cero. [1]")
    escribir("Las curvas por consulta conectan los puntos en el orden real del ranking y señalan la posición k. La curva media utiliza once niveles de recall. En cada nivel r, la precisión interpolada es el máximo P(k) entre los puntos con recall(k) mayor o igual que r. Si no existen, se utiliza cero. Después se promedian las cinco consultas. MAP se calcula directamente con los rankings. [1]")
    apartado("Configuración efectiva")
    empresarial = sistemas["empresarial"]
    variables = empresarial["variables_fulltext"]
    tabla([
        ["Parámetro", "Valor"],
        ["MySQL / Python", f"{empresarial['mysql']} / {datos['python'].split()[0]}"],
        ["Motor / modo FULLTEXT", "InnoDB / IN NATURAL LANGUAGE MODE"],
        ["Límites FULLTEXT", f"{variables['innodb_ft_min_token_size']} a {variables['innodb_ft_max_token_size']} caracteres"],
        ["Stopwords", f"{len(empresarial['stopwords_mysql'])} palabras españolas, filtro activo"],
        ["Colación del contenido FULLTEXT", "utf8mb4_unicode_ci"],
        ["Puertos del experimento", "MySQL 3307; HTTP 8100 y 8101"],
    ], [ancho * 0.46, ancho * 0.54])
    escribir("Las dos listas de stopwords son iguales. La selección de la tabla personalizada se hace en la sesión que crea el índice. La variable de sesión aparece vacía al consultarla desde una conexión posterior. Las variables observadas y la tabla cargada se conservan en la evidencia.", "Pequeno")

    historia.append(PageBreak())
    titulo("Curva media y tablas de contingencia")
    historia.append(Image(str(SALIDA / "figuras/media_interpolada.png"), width=ancho, height=ancho * 3.25 / 7.1))
    escribir("Figura 1. Precisión media interpolada en once niveles de exhaustividad. Los niveles superiores a 0.75 tienen valor cero porque ningún sistema recuperó el cuarto relevante de cada consulta.", "Pequeno")
    filas = [["Sistema", "Q", "TP", "FP", "FN", "TN", "Prec.", "Recall", "Accuracy"]]
    for sistema, resultados in sistemas.items():
        for clave, m in resultados["metricas"].items():
            filas.append(["buscador2" if sistema == "buscador2" else "Empresarial", clave,
                          m["TP"], m["FP"], m["FN"], m["TN"],
                          f"{m['precision']:.2f}", f"{m['recall']:.2f}", f"{m['accuracy']:.2f}"])
    tabla(filas, [88, 28, 29, 29, 29, 29, 53, 51, ancho - 436])
    escribir("La accuracy de 0.90 incluye 24 verdaderos negativos por consulta. Ambos recuperan el mismo conjunto de cinco documentos y omiten el relevante redactado mediante paráfrasis. Las diferencias de AP provienen del orden de los aciertos dentro de ese conjunto.")

    for numero, q in enumerate(protocolo["consultas"], 2):
        historia.append(PageBreak())
        titulo(f"{q['id']} | {escape(q['consulta'])}")
        escribir(escape(q["criterio"]))
        escribir("Relevantes fijados previamente: " + ", ".join(q["relevantes"]), "Pequeno")
        for sistema, resultados in sistemas.items():
            m = resultados["metricas"][q["id"]]
            apartado(f"{NOMBRES[sistema]} | AP {m['AP']:.4f}")
            resultados_doc = resultados["consultas"][q["id"]]["resultados"]
            filas = [["k", "Archivo", "Rel.", "Puntaje", "Coseno" if sistema == "buscador2" else "P(k)", "Recall(k)"]]
            for p, r in zip(m["puntos"], resultados_doc):
                filas.append([p["posicion"], p["nombre"], "Sí" if p["relevante"] else "No",
                              f"{r['relevancia']:.6f}",
                              f"{r['coseno']:.4f}" if sistema == "buscador2" else f"{p['precision']:.4f}",
                              f"{p['recall']:.2f}"])
            tabla(filas, [28, 93, 33, 100, 100, ancho - 354])
            sumandos = [f"{i}/{p['posicion']}" for i, p in enumerate(
                [p for p in m["puntos"] if p["relevante"]], 1)]
            escribir(f"AP = ({' + '.join(sumandos)}) / 4 = {m['AP']:.6f}. Relevante ausente: {', '.join(m['relevantes_ausentes'])}.", "Pequeno")
        historia.append(Image(str(SALIDA / f"figuras/{q['id']}.png"), width=ancho, height=ancho * 2.7 / 7.1))
        escribir(f"Figura {numero}. Curvas sin interpolar de {q['id']}. Cada número identifica k. Los puntos coincidentes se superponen. P(k) y recall(k) completos, fragmentos y puntajes sin redondear se conservan en el JSON.", "Pequeno")

    historia.append(PageBreak())
    titulo("Conclusiones y reproducibilidad")
    escribir(f"En el experimento definitivo, buscador2 obtuvo MAP {mapa['buscador2']:.4f} y Búsqueda empresarial {mapa['empresarial']:.4f}. La ventaja absoluta de buscador2 fue {diferencia:.4f}. Empataron en AP para Q1, Q3 y Q4; buscador2 obtuvo valores superiores en Q2 y Q5.")
    escribir("En Q2 ambos ubican un relevante en el primer lugar y otro en el tercero. buscador2 coloca el tercer relevante en la cuarta posición y empresarial en la quinta. En Q5 sucede la misma diferencia para el último relevante. En ambos casos el coseno de buscador2 resuelve un empate de la puntuación principal, mientras FULLTEXT utiliza el nombre. Esta característica explica la ventaja observada en MAP.")
    escribir("La recuperación final fue idéntica. Cada consulta tuvo TP=3, FP=2, FN=1 y TN=24. Los distractores comparten palabras con la consulta, y las paráfrasis omiten sus términos literales. Esto permite observar los límites de la coincidencia léxica en esta colección.")
    escribir("Para esta actividad, buscador2 presenta mejor ordenación según MAP. Búsqueda empresarial ofrece ventajas de implementación al delegar la indización y el cálculo de relevancia a MySQL y disponer de modos adicionales de consulta. La decisión de uso depende de esos requisitos. El experimento cubre el modo natural y una colección sintética pequeña con un único conjunto de juicios.")
    apartado("Comprobaciones realizadas")
    escribir("Se verificaron 30 altas y 30 descargas idénticas por sistema, cinco rankings HTML coincidentes con el motor, una consulta sin coincidencias y una recarga sin duplicados. Los rankings y puntajes se mantuvieron tras la recarga. Cada tabla suma 30 documentos y contiene cuatro relevantes. AP se comprobó con aritmética racional independiente. Las cuatro pruebas automatizadas de métricas pasaron.")
    apartado("Repetir la evaluación")
    escribir("Desde la raíz del repositorio, instalar evaluacion/requirements.txt en un entorno virtual. Con MySQL disponible, configurar EVAL_DB_HOST, EVAL_DB_PUERTO, EVAL_DB_USUARIO y EVAL_DB_CONTRASENA. Ejecutar evaluacion/evaluar.py y después evaluacion/generar_reporte.py. El evaluador crea bases nuevas en cada ejecución. Las instrucciones completas y la configuración de la instancia aislada están en evaluacion/README.md.")
    escribir("La ejecución inicial utilizó identificadores que expresaban la etiqueta y reveló un sesgo en el desempate por nombre. La ejecución definitiva usa nombres neutrales asignados con semilla 20261116. Los textos y los juicios se conservaron. Ambos registros permanecen como evidencia y este PDF utiliza únicamente la ejecución definitiva.", "Pequeno")
    apartado("Fuentes")
    escribir('[1] Manning, Raghavan y Schütze. Introduction to Information Retrieval, sección 8.4. <link href="https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html" color="#000000">Evaluation of ranked retrieval results</link>. AP, MAP y precisión interpolada.', "Pequeno")
    escribir('[2] Oracle. MySQL 8.0 Reference Manual. <link href="https://dev.mysql.com/doc/refman/8.0/en/fulltext-natural-language.html" color="#000000">Natural Language Full-Text Searches</link>. Relevancia, límites de términos y stopwords.', "Pequeno")
    escribir("[3] Código local de ambos buscadores y evidencia de la ejecución. Los archivos resultados.json contienen el commit de origen y los hashes del código. El enunciado utilizado fue el proporcionado por el usuario; los enlaces del curso no fueron accesibles.", "Pequeno")

    def pie(canvas, documento):
        canvas.saveState()
        canvas.setFont("Texto", 8)
        canvas.setFillColor(NEGRO)
        canvas.drawString(48, 26, "Comparación de buscadores | Colección sintética | " + fecha)
        canvas.drawRightString(A4[0] - 48, 26, str(documento.page))
        canvas.restoreState()

    ruta = SALIDA / "comparacion_buscadores.pdf"
    documento = SimpleDocTemplate(str(ruta), pagesize=A4, rightMargin=48, leftMargin=48,
                                  topMargin=45, bottomMargin=52,
                                  title="Comparación de buscadores mediante precisión, exhaustividad y MAP",
                                  author="Equipo de Búsqueda y Recuperación")
    documento.build(historia, onFirstPage=pie, onLaterPages=pie)
    lector = PdfReader(ruta)
    assert len(lector.pages) == 11, f"Revisar paginación: {len(lector.pages)} páginas"
    contenido = "\n".join(p.extract_text() for p in lector.pages)
    for palabra in (f"{mapa['buscador2']:.4f}", f"{mapa['empresarial']:.4f}", "Q1", "Q2", "Q3", "Q4", "Q5", "Accuracy"):
        assert palabra in contenido
    print(f"PDF generado y comprobado: {ruta} ({len(lector.pages)} páginas)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resultados", type=Path, default=RAIZ / "resultados/ultima_ejecucion.json")
    generar(parser.parse_args().resultados)
