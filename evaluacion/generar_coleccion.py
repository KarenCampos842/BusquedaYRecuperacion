"""Construye la colección sintética y fija sus juicios antes de buscar."""
import hashlib
import json
from pathlib import Path
import random

RAIZ = Path(__file__).resolve().parent

# Cada entrada aporta un texto propio y un contexto compartido por su tema.
# El cuarto relevante expresa la necesidad mediante vocabulario alternativo.
TEMAS = [
    {
        "id": "Q1", "consulta": "energía solar viviendas",
        "criterio": "Explica el uso de energía solar para abastecer viviendas.",
        "contexto": "En el proyecto doméstico se comparan alternativas según el consumo anual y las condiciones del edificio. La revisión considera orientación, sombras, mantenimiento y presupuesto disponible. El equipo presenta un esquema de componentes, una estimación de producción y una descripción de las tareas de seguimiento. Cada propuesta distingue los supuestos del cálculo y las mediciones que todavía deben obtenerse. El propósito del documento es explicar el funcionamiento de la solución en un caso didáctico.",
        "relevantes": [
            ("Paneles en azoteas", "La energía solar puede abastecer viviendas mediante paneles fotovoltaicos instalados en la azotea. Un inversor transforma la electricidad producida para alimentar los aparatos del hogar. El ejemplo analiza una casa con refrigerador, iluminación y equipos de trabajo. La producción durante las horas de luz se compara con la demanda de sus habitantes. Se explica cómo estimar la superficie necesaria y cómo registrar la generación mensual. La energía sobrante puede gestionarse según las condiciones de conexión disponibles. El texto describe las etapas de diseño, montaje y revisión de una instalación residencial."),
            ("Acumulación doméstica", "Una instalación de energía solar para viviendas puede incorporar baterías para utilizar parte de la producción después del atardecer. Este caso describe el recorrido de la electricidad desde los módulos hasta el sistema de acumulación. La capacidad se elige a partir de los aparatos que se desea mantener activos. Se diferencian la energía generada durante el día y la potencia solicitada por los equipos. El ejemplo permite revisar pérdidas, autonomía y hábitos de consumo. También explica por qué resulta necesario registrar el estado de los componentes durante la operación doméstica."),
            ("Agua caliente en casa", "El aprovechamiento de energía solar en viviendas incluye colectores térmicos para calentar agua. El circuito recibe radiación, transfiere calor y lo conserva en un depósito aislado. Una familia utiliza el agua en actividades domésticas durante distintos horarios. El documento explica la función del tanque, las tuberías y el equipo auxiliar cuando hay poca radiación. Se analiza el tamaño del sistema a partir de la demanda de agua caliente. La propuesta compara el servicio obtenido con el consumo previo del calentador y describe un registro de funcionamiento para revisar la instalación."),
            ("Electricidad fotovoltaica residencial", "La captación fotovoltaica permite suministrar electricidad a casas mediante módulos colocados sobre el techo. Los equipos convierten la radiación del sol en corriente que luego adapta un inversor. Este documento explica cómo alimentar electrodomésticos en una residencia y cómo distribuir el consumo durante las horas de producción. Un acumulador permite reservar parte de la generación para la noche. El diseño parte de las facturas del hogar y de la superficie disponible. La explicación presenta los componentes principales y describe cómo observar el desempeño del conjunto a lo largo del año."),
        ],
        "distractores": [
            ("Catálogo de una exposición", "El museo prepara una exposición titulada Energía solar y viviendas del futuro. El documento organiza boletos, horarios y recorridos para grupos escolares. La sala principal contiene maquetas decorativas de viviendas y carteles con la palabra solar. El catálogo describe colores, materiales y autores de las piezas, además de la ubicación de la tienda. La energía es un motivo visual recurrente en la campaña. La programación incluye visitas guiadas, una conferencia sobre diseño gráfico y un taller de carteles. El texto se concentra en la organización cultural y la venta de entradas del evento."),
            ("Superficies de una urbanización", "La oficina municipal registra las viviendas de una urbanización y la superficie de cada solar. El informe utiliza la palabra solar para identificar un terreno destinado a construcción. Las viviendas se agrupan según calle y número de lote. Una sección administrativa informa sobre el contrato de energía de las oficinas y el horario de atención al público. El expediente contiene medidas, folios y responsables de la revisión. La comparación entre lotes permite corregir diferencias del padrón y preparar certificados para los propietarios. El objetivo es actualizar registros catastrales y organizar la documentación de cada inmueble."),
        ],
    },
    {
        "id": "Q2", "consulta": "prevención diabetes ejercicio",
        "criterio": "Explica cómo la actividad física contribuye a prevenir diabetes tipo 2.",
        "contexto": "El material forma parte de una colección académica de ejemplos y emplea situaciones ficticias. La explicación describe relaciones generales y señala qué variables observa un proyecto educativo. Los registros se presentan de forma agregada para discutir el diseño de una intervención comunitaria. Cada caso incluye objetivos, actividades y criterios de seguimiento. La discusión se centra en comprender el tema y en reconocer la información que haría falta para estudiar los resultados de una iniciativa real.",
        "relevantes": [
            ("Movimiento y metabolismo", "La prevención de diabetes tipo dos se relaciona con hábitos de movimiento sostenidos. El ejercicio favorece el uso de glucosa por los músculos y permite estudiar cambios en la sensibilidad a la insulina. El caso didáctico describe caminatas y actividades adaptadas a diferentes participantes. Se observan continuidad, participación y evolución de indicadores agregados. El documento explica el mecanismo que conecta actividad corporal y regulación metabólica. También distingue las metas educativas del programa y las variables necesarias para valorar sus efectos. La propuesta aborda específicamente cómo incorporar movimiento a una estrategia preventiva."),
            ("Programa de caminatas", "Un programa comunitario de prevención de diabetes incorpora ejercicio mediante caminatas organizadas. Las sesiones buscan reducir el tiempo sedentario y crear una rutina que pueda sostenerse. El documento explica que los músculos activos utilizan glucosa y describe el papel de ese proceso en la regulación del azúcar. El ejemplo registra asistencia, duración y percepción de esfuerzo. La diabetes tipo dos constituye la necesidad de información del programa y la prevención orienta sus actividades. Se discute cómo evaluar la continuidad del ejercicio durante varios meses y cómo interpretar la participación observada."),
            ("Rutinas activas cotidianas", "El ejercicio cotidiano aparece en una estrategia educativa de prevención de diabetes tipo dos. Subir escaleras y realizar desplazamientos activos son ejemplos usados para explicar la reducción del sedentarismo. El texto relaciona la contracción muscular con el aprovechamiento de glucosa y con cambios en la respuesta a la insulina. La actividad se incorpora a horarios de trabajo y convivencia familiar dentro de un caso ficticio. El documento describe cómo registrar frecuencia y continuidad. También expone qué datos permitirían comparar la participación entre etapas del programa sin atribuir efectos a una sola observación."),
            ("Actividad física y riesgo metabólico", "La actividad física contribuye a disminuir el riesgo de desarrollar alteraciones crónicas del azúcar en sangre asociadas con resistencia a la insulina. Al moverse, los músculos utilizan glucosa y participan en el control metabólico. El material explica esa relación mediante una experiencia comunitaria de caminatas, baile y desplazamientos activos. La propuesta busca evitar la aparición del trastorno de tipo dos en una población ficticia. El seguimiento registra regularidad, tiempo sedentario y participación. La explicación conecta estos hábitos con el funcionamiento del organismo y presenta preguntas para evaluar una intervención prolongada."),
        ],
        "distractores": [
            ("Ejercicio de contabilidad hospitalaria", "El curso de contabilidad plantea un ejercicio con facturas de una clínica llamada Diabetes. El ejercicio consiste en ordenar ingresos, egresos y comprobantes por fecha. La sección de prevención describe controles administrativos para evitar pagos duplicados. Los estudiantes calculan saldos y revisan la numeración de recibos. Diabetes aparece como razón social ficticia en los encabezados. El documento ofrece instrucciones para registrar operaciones y preparar un balance de cierre. Una hoja adicional contiene ejemplos de errores de captura y un calendario de entrega. El objetivo del material es practicar operaciones contables y verificar documentos financieros."),
            ("Boletín editorial de salud", "La biblioteca publica un boletín con novedades editoriales. Diabetes figura como título de una novela sobre una familia, mientras Prevención es el nombre de una revista de arquitectura. El ejercicio de catalogación pide ordenar ambas publicaciones y asignar sus claves. Los estudiantes deben identificar autor, año, editorial y número de ejemplares disponibles. Una tabla registra préstamos, devoluciones y condiciones físicas. El documento explica los pasos para corregir fichas incompletas y colocar etiquetas en los estantes. El propósito del boletín es enseñar organización bibliográfica a partir de títulos elegidos para una práctica escolar."),
        ],
    },
    {
        "id": "Q3", "consulta": "seguridad contraseñas autenticación",
        "criterio": "Explica protección de cuentas mediante contraseñas y autenticación.",
        "contexto": "El caso utiliza cuentas ficticias de una organización educativa. El equipo responsable documenta los procedimientos y revisa que los participantes comprendan cada paso. La propuesta distingue el acceso cotidiano de las tareas de recuperación y administración. Las decisiones se registran junto con su propósito y con los recursos que requieren. La evaluación incluye observación del uso, revisión de incidentes simulados y actualización del material de capacitación. Los ejemplos permiten discutir el alcance de cada medida dentro del proyecto.",
        "relevantes": [
            ("Claves únicas por cuenta", "La seguridad de las cuentas mejora al utilizar contraseñas diferentes para cada servicio. Si una clave se divulga, reutilizarla puede facilitar accesos a otros sistemas. El documento explica cómo un gestor ayuda a organizar contraseñas y cómo se integra con un proceso de autenticación. Un segundo factor añade una comprobación al inicio de sesión. El caso describe el alta de usuarios, la verificación del acceso y la recuperación de credenciales. También revisa por qué el personal debe reconocer solicitudes engañosas que intentan obtener claves mediante formularios o mensajes."),
            ("Segundo factor", "La autenticación con un segundo factor se incorpora a una política de seguridad de cuentas. Las contraseñas proporcionan una primera comprobación y un código o dispositivo aporta otra. El caso describe el registro del factor adicional y el proceso para utilizarlo al entrar al sistema. El documento explica cómo esa combinación reduce la dependencia de una sola credencial. También presenta un procedimiento de recuperación cuando el usuario pierde el dispositivo. La propuesta incluye capacitación, revisión de accesos y documentación de incidentes para valorar el funcionamiento del mecanismo en la organización."),
            ("Recuperación de credenciales", "Una política de seguridad debe considerar tanto las contraseñas como la autenticación durante la recuperación de cuentas. El texto describe la verificación de identidad antes de cambiar una credencial olvidada. El equipo registra solicitudes, revisa señales de suplantación y explica el uso de factores adicionales. Una cuenta recuperada requiere revisar sesiones activas y confirmar que el propietario puede acceder. El ejemplo relaciona estas tareas con la protección de información personal. También describe cómo informar a los usuarios y cómo revisar el procedimiento cuando aparecen errores o intentos de acceso indebido."),
            ("Protección del acceso digital", "Para proteger el acceso a servicios digitales, cada persona utiliza una clave secreta distinta y una verificación adicional al iniciar sesión. Un administrador de credenciales facilita crear claves largas y guardarlas de forma organizada. La segunda comprobación puede depender de un dispositivo registrado. El texto explica cómo ambas medidas dificultan la entrada de terceros cuando se divulga una credencial. También describe el registro inicial, el cierre de sesiones y la recuperación de acceso. El proyecto considera mensajes de suplantación y presenta un procedimiento para verificar solicitudes de cambio de clave."),
        ],
        "distractores": [
            ("Utilería para una obra", "La compañía teatral prepara una obra llamada Contraseñas. El expediente de seguridad describe salidas de emergencia, extintores y capacidad de la sala. La autenticación de las firmas del contrato se realiza ante la oficina administrativa. Contraseñas aparece en carteles, entradas y hojas de reparto. El documento registra ensayos, inventario de utilería y responsables del montaje. Los actores reciben un calendario y un plano del escenario. La sección de seguridad se ocupa del espacio físico del teatro. El propósito del expediente es coordinar la producción escénica y completar los trámites para abrir funciones al público."),
            ("Colección de documentos históricos", "El archivo conserva cartas militares con antiguas contraseñas escritas en papel. La autenticación de las piezas corresponde a especialistas que revisan tinta, sellos y procedencia. El plan de seguridad del edificio enumera vitrinas, cámaras y horarios de vigilancia. El texto describe cómo embalar manuscritos y registrar préstamos para una exposición. Una ficha presenta las contraseñas como objetos históricos y explica su ubicación en el catálogo. La atención se concentra en conservación física, atribución de autoría y transporte de documentos. El informe organiza el trabajo de curadores y restauradores durante una muestra temporal."),
        ],
    },
    {
        "id": "Q4", "consulta": "reciclaje residuos electrónicos",
        "criterio": "Explica gestión y reciclaje de aparatos electrónicos desechados.",
        "contexto": "El proyecto describe un proceso de recolección y seguimiento de materiales. El equipo registra cantidades, procedencia y destino mediante formularios sencillos. Cada etapa tiene responsables y condiciones de recepción. La propuesta considera transporte, clasificación y documentación para observar el recorrido completo de los objetos. El ejemplo permite discutir qué información necesita una organización antes de contratar un servicio y cómo revisar que los materiales lleguen al destino previsto. Las cifras del caso son ilustrativas y forman parte del escenario académico.",
        "relevantes": [
            ("Ruta de aparatos desechados", "El reciclaje de residuos electrónicos comienza con la separación de aparatos que han dejado de utilizarse. Computadoras, teléfonos y cables se reciben en un punto de acopio y se clasifican según sus componentes. El documento describe cómo registrar los equipos y trasladarlos a una instalación que recupere materiales. El desmontaje permite separar metales, plásticos y piezas que requieren manejo específico. La explicación relaciona cada etapa con el destino final de los residuos. El caso incluye un comprobante de entrega y un registro para seguir el recorrido de los aparatos desechados."),
            ("Acopio de computadoras", "Una campaña de reciclaje recibe residuos electrónicos procedentes de oficinas. El personal reúne computadoras y periféricos, revisa su estado y separa los equipos que pueden reutilizarse. Los aparatos sin posibilidad de uso pasan a clasificación para recuperar materiales. El texto explica por qué se documenta el destino de placas, carcasas y cables. Los residuos se entregan a un servicio especializado con un inventario. El caso describe las etapas de recepción, almacenamiento temporal y traslado. La propuesta permite entender cómo organizar una campaña centrada en equipos electrónicos que han terminado su vida útil."),
            ("Materiales de teléfonos", "Los teléfonos desechados forman parte de los residuos electrónicos que requieren una ruta de gestión. El reciclaje permite separar materiales de carcasas y componentes internos mediante procesos especializados. El documento explica la recepción de equipos, la clasificación y el registro de su destino. También distingue el aprovechamiento de piezas del tratamiento de materiales que necesitan cuidados particulares. Un programa ficticio reúne dispositivos en una escuela y documenta la entrega al gestor. El objetivo es comprender cómo se integra el acopio con las etapas posteriores y cómo verificar que los aparatos recibidos siguen una ruta definida."),
            ("Recuperación de equipos informáticos", "La recuperación de materiales de computadoras desechadas requiere separar carcasas, placas y cables. Un centro recibe los aparatos, elabora un inventario y clasifica piezas aprovechables. Los componentes restantes se envían a instalaciones especializadas para recuperar metales y tratar sustancias que requieren cuidados particulares. El texto explica la secuencia desde el punto de acopio hasta la entrega al gestor. La reutilización de piezas se registra por separado del procesamiento de materiales. El caso presenta formularios de recepción y comprobantes de destino para seguir el recorrido de cada lote de equipos fuera de uso."),
        ],
        "distractores": [
            ("Inscripción digital a un taller", "El taller de reciclaje de papel utiliza formularios electrónicos para registrar asistentes. Los residuos que se emplean en la actividad son hojas usadas y cajas de cartón. El documento explica cómo abrir la inscripción, confirmar lugares y enviar recordatorios electrónicos. La sesión enseña a preparar pulpa de papel y elaborar tarjetas decorativas. El reciclaje aparece en el nombre del evento y en sus materiales de difusión. Los organizadores registran mesas, horarios y cantidad de participantes. El objetivo del texto es coordinar una actividad artesanal con papel y administrar sus inscripciones mediante una página escolar."),
            ("Ejercicios de una clase de sonido", "Una clase de música utiliza sonidos electrónicos y una pieza titulada Residuos. El reciclaje de motivos musicales consiste en repetir y transformar secuencias de notas. El documento indica el orden de los ejercicios y el tiempo destinado a cada interpretación. Los instrumentos electrónicos se conectan a un equipo de grabación para escuchar el resultado. Residuos es el título de una composición creada por estudiantes. El material describe ritmo, mezcla y edición de audio. La propuesta busca comparar versiones musicales y documentar las decisiones artísticas de cada grupo durante una práctica de composición."),
        ],
    },
    {
        "id": "Q5", "consulta": "riego eficiente agricultura",
        "criterio": "Explica métodos para reducir el consumo de agua de riego agrícola.",
        "contexto": "La propuesta se desarrolla en una parcela ficticia y compara alternativas de operación. El seguimiento registra condiciones del terreno, calendario de trabajo y recursos utilizados. El equipo anota los supuestos antes de interpretar las mediciones y conserva una bitácora de los cambios. Cada alternativa se revisa según las necesidades del cultivo y las características del lugar. El caso permite discutir decisiones de manejo, tareas de mantenimiento y datos necesarios para evaluar una temporada completa con criterios comparables.",
        "relevantes": [
            ("Goteo en parcelas", "El riego por goteo permite un uso eficiente del agua en agricultura al entregarla cerca de las raíces. El documento describe tuberías, emisores y controles para distribuir el caudal de una parcela. La programación considera el cultivo y la humedad del suelo. El ejemplo compara el volumen aplicado antes y después de ajustar el sistema. La revisión de fugas y obstrucciones ayuda a mantener una distribución uniforme. El texto explica cómo estas tareas pueden reducir pérdidas y cómo registrar el agua utilizada durante una temporada para evaluar el método de riego."),
            ("Sensores de humedad", "Una estrategia de riego eficiente en agricultura utiliza sensores para observar la humedad del terreno. El equipo registra mediciones y programa aplicaciones cuando el cultivo requiere agua. La explicación relaciona la información del suelo con la duración de cada evento de riego. El caso compara un calendario fijo con decisiones basadas en registros de la parcela. También describe cómo revisar sensores y anotar cambios de clima. El propósito es comprender cómo evitar aplicaciones innecesarias y cómo medir el consumo para valorar una estrategia de manejo del agua durante el desarrollo del cultivo."),
            ("Programación del suministro", "El manejo eficiente del riego en agricultura considera el momento del día y las necesidades del cultivo. El documento explica cómo ajustar duración y frecuencia para reducir pérdidas de agua. Una bitácora registra caudal, superficie atendida y observaciones del terreno. El caso describe la revisión de tuberías y la detección de fugas antes de comparar temporadas. La propuesta utiliza las mediciones para corregir aplicaciones excesivas. El objetivo es relacionar decisiones de operación con el consumo total y establecer un procedimiento que permita revisar el aprovechamiento del agua en una parcela."),
            ("Agua para cultivos", "Para disminuir el consumo hídrico de los cultivos se colocan emisores junto a las raíces y se controla el tiempo de suministro. La humedad del terreno orienta la programación y ayuda a evitar aplicaciones excesivas. El documento explica cómo revisar pérdidas en las conducciones y cómo ajustar el volumen a las necesidades de las plantas. Un registro de caudal permite comparar jornadas y comprobar cambios en el manejo de la parcela. La propuesta describe pasos de instalación, seguimiento y mantenimiento de un sistema destinado a aprovechar mejor el agua durante la producción de alimentos."),
        ],
        "distractores": [
            ("Archivo de un congreso", "El congreso de agricultura conserva un expediente firmado por la investigadora Ana Riego. El documento describe un sistema eficiente para registrar ponencias y emitir constancias. Riego coordina la mesa de historia rural y revisa los horarios de cada presentación. Agricultura aparece en el nombre del evento y en los certificados. El informe organiza salones, equipos de proyección y turnos del personal. Una tabla compara tiempos de inscripción y señala cambios administrativos. El propósito del expediente es documentar la organización del congreso y el funcionamiento del registro digital utilizado por sus asistentes."),
            ("Jardines ornamentales urbanos", "El ayuntamiento presenta un programa de riego eficiente para jardines ornamentales de avenidas. El texto describe horarios de mantenimiento de césped y macetas en espacios públicos. Una sección informa que la oficina de agricultura prestó vehículos para transportar herramientas. El programa se ocupa de áreas decorativas y del trabajo de cuadrillas municipales. La bitácora registra turnos, rutas y estado de los jardines. El documento explica cómo organizar el suministro de agua para plantas ornamentales dentro de la ciudad. La evaluación considera la apariencia de los camellones y el tiempo destinado al mantenimiento de parques."),
        ],
    },
]


def generar():
    carpeta = RAIZ / "coleccion"
    carpeta.mkdir(parents=True, exist_ok=True)
    consultas = []
    documentos = []
    identificadores = list(range(1, 31))
    random.Random(20261116).shuffle(identificadores)
    for tema in TEMAS:
        relevantes = []
        for grupo in ("relevantes", "distractores"):
            for numero, (titulo, cuerpo) in enumerate(tema[grupo], 1):
                clase = "R" if grupo == "relevantes" else "D"
                nombre = f"doc{identificadores[len(documentos)]:03}.txt"
                contenido = f"{titulo}\n\n{cuerpo}\n\n{tema['contexto']}\n"
                datos = contenido.encode("utf-8")
                (carpeta / nombre).write_bytes(datos)
                palabras = len(contenido.split())
                if not 150 <= palabras <= 250:
                    raise ValueError(f"Longitud fuera del protocolo: {nombre}, {palabras}")
                documentos.append({
                    "nombre": nombre, "titulo": titulo, "palabras": palabras,
                    "sha256": hashlib.sha256(datos).hexdigest(),
                    "relevante_para": [tema["id"]] if clase == "R" else [],
                    "justificacion": tema["criterio"] if clase == "R" else
                    "Comparte vocabulario, pero su propósito no satisface la necesidad definida.",
                })
                if clase == "R":
                    relevantes.append(nombre)
        consultas.append({
            "id": tema["id"], "consulta": tema["consulta"],
            "criterio": tema["criterio"], "relevantes": relevantes,
        })
    protocolo = {
        "origen": "Colección sintética redactada para esta actividad con asistencia de IA.",
        "nombres": "Identificadores neutrales doc001 a doc030 asignados con random.Random(20261116).shuffle, antes de la ejecución definitiva.",
        "diseno": "Cinco temas, tres relevantes con vocabulario directo, un relevante con paráfrasis y dos distractores por tema. Los seis textos de cada tema comparten un párrafo de contexto. Etiquetas binarias fijadas antes de buscar; sin ajuste posterior a los resultados.",
        "consultas": consultas, "documentos": documentos,
    }
    (RAIZ / "protocolo.json").write_text(
        json.dumps(protocolo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Colección fijada: {len(documentos)} documentos, {len(consultas)} consultas.")


if __name__ == "__main__":
    generar()
