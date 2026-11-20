import csv
import io

from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for,
    Response
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from ia import (
    generar_preguntas,
    generar_ejercicios_refuerzo,
    SUBTEMAS_FIJOS
)

from bkt import (
    actualizar_bkt,
    PROBABILIDAD_INICIAL
)

from beneficio import (
    calcular_beneficio
)

from mochila import (
    recomendar_ejercicios
)

from base_datos import (
    crear_base_datos,
    obtener_o_crear_estudiante,
    buscar_estudiante,
    guardar_resultado,
    guardar_dominio_bkt,
    cargar_dominio_bkt,
    obtener_historial,
    obtener_dominios_actuales,
    obtener_evolucion_bkt,
    guardar_plan,
    crear_docente,
    buscar_docente,
    obtener_docente,
    obtener_cursos,
    obtener_estudiante
)

from indicadores import (
    resumen_curso
)


# ==========================================
# CONFIGURACION DE FLASK
# ==========================================

app = Flask(__name__)

app.secret_key = "tutoria-educativa-local-2026"

crear_base_datos()


# ==========================================
# TEMAS DISPONIBLES EN EL FORMULARIO
# ==========================================

MATERIAS = {
    "Calculo Diferencial": "calculo diferencial",
    "Ingles": "ingles",
    "Fisica": "fisica"
}

TEMAS = {
    materia: [tema.capitalize() for tema in SUBTEMAS_FIJOS[clave]]
    for materia, clave in MATERIAS.items()
}


def render_inicio(**datos):

    return render_template(
        "index.html",
        temas=TEMAS,
        **datos
    )


# ==========================================
# FILTRO: TEXTO CON TILDES PARA MOSTRAR
# ==========================================

TILDES = {
    "calculo": "cálculo", "limites": "límites", "factorizacion": "factorización",
    "racionalizacion": "racionalización", "trigonometricas": "trigonométricas",
    "fisica": "física", "ingles": "inglés", "direccion": "dirección",
    "posicion": "posición", "aceleracion": "aceleración", "basico": "básico",
    "aplicacion": "aplicación", "interpretacion": "interpretación",
    "resolucion": "resolución"
}


@app.template_filter("bonito")
def bonito(texto):

    palabras = [TILDES.get(p.lower(), p) for p in str(texto).split()]
    texto = " ".join(palabras)

    return texto[:1].upper() + texto[1:]


# ==========================================
# FILTRO: PUNTOS DE UNA MINI GRAFICA
# ==========================================

@app.template_filter("puntos")
def puntos(valores, ancho=160, alto=48):

    if len(valores) == 1:
        valores = valores * 2

    paso = ancho / (len(valores) - 1)

    return " ".join(
        f"{i * paso:.1f},{alto - v * alto:.1f}"
        for i, v in enumerate(valores)
    )


# ==========================================
# INICIO
# ==========================================

@app.route("/")
def inicio():

    return render_inicio()


# ==========================================
# GENERAR EVALUACION
# ==========================================

@app.route(
    "/evaluacion",
    methods=["POST"]
)
def evaluacion():

    numero_lista = int(
        request.form["numero_lista"]
    )

    nombre = request.form[
        "nombre"
    ]

    colegio = request.form[
        "colegio"
    ]

    edad = int(
        request.form["edad"]
    )

    curso = request.form[
        "curso"
    ]

    materia = request.form[
        "materia"
    ]

    tema = request.form[
        "tema"
    ]

    if tema == "__otro__":

        tema = request.form.get(
            "tema_otro",
            ""
        ).strip() or "General"

    nivel = request.form[
        "nivel"
    ]


    # ======================================
    # BUSCAR O CREAR ESTUDIANTE
    # ======================================

    estudiante_id = obtener_o_crear_estudiante(
        numero_lista,
        nombre,
        colegio,
        edad,
        curso
    )


    # ======================================
    # GUARDAR DATOS EN SESION
    # ======================================

    session["estudiante_id"] = estudiante_id

    session["numero_lista"] = numero_lista

    session["nombre"] = nombre

    session["colegio"] = colegio

    session["edad"] = edad

    session["curso"] = curso

    session["materia"] = materia

    session["tema"] = tema

    session["nivel"] = nivel


    print(
        "\n======================================"
    )

    print(
        "GENERANDO EVALUACION"
    )

    print(
        "======================================"
    )


    # ======================================
    # GENERAR PREGUNTAS CON LM STUDIO
    # ======================================

    preguntas = generar_preguntas(
        materia,
        tema,
        nivel
    )


    session["preguntas"] = preguntas


    return render_template(
        "evaluacion.html",

        preguntas=preguntas,

        materia=materia,

        tema=tema,

        nivel=nivel
    )


# ==========================================
# RESULTADOS
# ==========================================

@app.route(
    "/resultado",
    methods=["POST"]
)
def resultado():

    preguntas = session.get(
        "preguntas",
        []
    )

    estudiante_id = session.get(
        "estudiante_id"
    )

    materia = session.get(
        "materia"
    )

    tema = session.get(
        "tema"
    )

    nivel = session.get(
        "nivel"
    )


    # ======================================
    # PROTECCION
    # ======================================

    if (
        not preguntas
        or estudiante_id is None
    ):

        return redirect(
            url_for("inicio")
        )


    puntaje = 0

    resultados = []

    dominios_bkt = {}

    dominios_anteriores = {}

    beneficios = {}


    # ======================================
    # CALIFICAR PREGUNTAS
    # ======================================

    for indice, pregunta in enumerate(
        preguntas
    ):

        respuesta = request.form.get(
            f"pregunta_{indice}"
        )


        correcta = str(
            pregunta["correcta"]
        )


        es_correcta = (
            respuesta == correcta
        )


        if es_correcta:

            puntaje += 1


        subtema = pregunta[
            "subtema"
        ]


        # ==================================
        # CARGAR BKT ANTERIOR
        # ==================================

        if subtema not in dominios_bkt:

            dominio_guardado = cargar_dominio_bkt(
                estudiante_id,
                materia,
                tema,
                subtema
            )


            if dominio_guardado is None:

                dominios_anteriores[
                    subtema
                ] = None


                dominios_bkt[
                    subtema
                ] = PROBABILIDAD_INICIAL

            else:

                dominios_anteriores[
                    subtema
                ] = dominio_guardado


                dominios_bkt[
                    subtema
                ] = dominio_guardado


        # ==================================
        # ACTUALIZAR BKT
        # ==================================

        dominios_bkt[
            subtema
        ] = actualizar_bkt(
            dominios_bkt[
                subtema
            ],
            es_correcta
        )


        # ==================================
        # GUARDAR RESULTADO DE PREGUNTA
        # ==================================

        resultados.append(
            {

                "pregunta":
                    pregunta["pregunta"],

                "respuesta":
                    respuesta,

                "correcta":
                    correcta,

                "opciones":
                    pregunta["opciones"],

                "es_correcta":
                    es_correcta,

                "subtema":
                    subtema
            }
        )


    # ======================================
    # RESULTADO GENERAL
    # ======================================

    total = len(
        preguntas
    )


    porcentaje = (
        puntaje
        / total
        * 100
    )


    # ======================================
    # GUARDAR RESULTADO EN SQLITE
    # ======================================

    guardar_resultado(
        estudiante_id,
        materia,
        tema,
        nivel,
        puntaje,
        total,
        porcentaje
    )


    # ======================================
    # GUARDAR BKT Y CALCULAR BENEFICIO
    # ======================================

    for subtema, dominio in (
        dominios_bkt.items()
    ):

        guardar_dominio_bkt(
            estudiante_id,
            materia,
            tema,
            subtema,
            dominio
        )


        beneficios[
            subtema
        ] = calcular_beneficio(
            dominio
        )


    # ======================================
    # GUARDAR PARA RECOMENDACIONES
    # ======================================

    session[
        "dominios_bkt"
    ] = dominios_bkt


    session[
        "beneficios"
    ] = beneficios


    # ======================================
    # MOSTRAR RESULTADOS
    # ======================================

    return render_template(
        "resultados.html",

        puntaje=puntaje,

        total=total,

        porcentaje=porcentaje,

        resultados=resultados,

        dominios_bkt=dominios_bkt,

        dominios_anteriores=dominios_anteriores,

        materia=materia,

        tema=tema,

        nivel=nivel
    )


# ==========================================
# RECOMENDACIONES
# ==========================================

@app.route(
    "/recomendacion",
    methods=["POST"]
)
def recomendacion():

    # ======================================
    # OBTENER TIEMPO DE FORMA SEGURA
    # ======================================

    tiempo_recibido = request.form.get(
        "tiempo_disponible"
    )


    if tiempo_recibido is None:

        print(
            "ERROR: No se recibio tiempo_disponible."
        )

        return redirect(
            url_for("inicio")
        )


    try:

        tiempo_disponible = int(
            tiempo_recibido
        )

    except ValueError:

        return redirect(
            url_for("inicio")
        )


    # ======================================
    # DATOS DE LA EVALUACION
    # ======================================

    materia = session.get(
        "materia"
    )

    tema = session.get(
        "tema"
    )

    nivel = session.get(
        "nivel"
    )


    beneficios = session.get(
        "beneficios",
        {}
    )


    # ======================================
    # PROTECCION
    # ======================================

    if (
        materia is None
        or tema is None
        or nivel is None
        or not beneficios
    ):

        return redirect(
            url_for("inicio")
        )


    subtemas = list(
        beneficios.keys()
    )


    print(
        "\n======================================"
    )

    print(
        "GENERANDO EJERCICIOS DE REFUERZO"
    )

    print(
        "======================================"
    )

    print(
        "Tiempo disponible:",
        tiempo_disponible
    )

    print(
        "Subtemas:",
        subtemas
    )


    # ======================================
    # GENERAR EJERCICIOS CON IA
    # ======================================

    ejercicios = generar_ejercicios_refuerzo(
        materia,
        tema,
        nivel,
        subtemas
    )


    # ======================================
    # ASIGNAR BENEFICIO
    # ======================================

    for ejercicio in ejercicios:

        subtema = ejercicio[
            "subtema"
        ]


        ejercicio[
            "beneficio"
        ] = beneficios.get(
            subtema,
            0
        )


    # ======================================
    # QUITAR SUBTEMAS QUE YA DOMINA
    # (beneficio menor a 0.5 = dominio de 95% o mas)
    # ======================================

    ejercicios = [
        ejercicio
        for ejercicio in ejercicios
        if ejercicio["beneficio"] >= 0.5
    ]


    # ======================================
    # ALGORITMO DE MOCHILA
    # ======================================

    (
        seleccionados,
        tiempo_total,
        beneficio_total

    ) = recomendar_ejercicios(
        ejercicios,
        tiempo_disponible
    )


    estudiante_id = session.get(
        "estudiante_id"
    )

    if estudiante_id is not None:

        guardar_plan(
            estudiante_id,
            materia,
            tema,
            tiempo_disponible,
            tiempo_total,
            beneficio_total,
            len(seleccionados)
        )


    print(
        "Tiempo seleccionado:",
        tiempo_total
    )

    print(
        "Beneficio total:",
        beneficio_total
    )


    # ======================================
    # MOSTRAR RECOMENDACIONES
    # ======================================

    return render_template(
        "recomendaciones.html",

        ejercicios=seleccionados,

        tiempo_disponible=tiempo_disponible,

        tiempo_total=tiempo_total,

        beneficio_total=beneficio_total,

        materia=materia,

        tema=tema,

        nivel=nivel
    )


# ==========================================
# MI PROGRESO
# ==========================================

@app.route(
    "/progreso"
)
def progreso():

    estudiante_id = session.get(
        "estudiante_id"
    )


    if estudiante_id is None:

        return redirect(
            url_for("inicio")
        )


    historial = obtener_historial(
        estudiante_id
    )


    dominios = obtener_dominios_actuales(
        estudiante_id
    )


    evolucion = obtener_evolucion_bkt(
        estudiante_id
    )


    return render_template(
        "progreso.html",

        nombre=session.get(
            "nombre",
            ""
        ),

        numero_lista=session.get(
            "numero_lista",
            ""
        ),

        colegio=session.get(
            "colegio",
            ""
        ),

        curso=session.get(
            "curso",
            ""
        ),

        historial=historial,

        dominios=dominios,

        evolucion=evolucion
    )


# ==========================================
# CONSULTAR PROGRESO DESDE INICIO
# ==========================================

@app.route(
    "/consultar-progreso",
    methods=["POST"]
)
def consultar_progreso():

    numero_lista_recibido = request.form.get(
        "numero_lista_progreso"
    )

    colegio = request.form.get(
        "colegio_progreso",
        ""
    ).strip()

    curso = request.form.get(
        "curso_progreso",
        ""
    ).strip()


    if (
        not numero_lista_recibido
        or not colegio
        or not curso
    ):

        return render_inicio(

            error_progreso=(
                "Debes completar todos "
                "los datos para consultar."
            )
        )


    try:

        numero_lista = int(
            numero_lista_recibido
        )

    except ValueError:

        return render_inicio(

            error_progreso=(
                "El número de lista "
                "debe ser válido."
            )
        )


    # ======================================
    # BUSCAR ESTUDIANTE
    # ======================================

    estudiante = buscar_estudiante(
        numero_lista,
        colegio,
        curso
    )


    if estudiante is None:

        return render_inicio(

            error_progreso=(
                "No se encontró un estudiante "
                "con esos datos."
            )
        )


    # ======================================
    # RECUPERAR DATOS
    # ======================================

    estudiante_id = estudiante[0]

    nombre = estudiante[1]

    colegio = estudiante[2]

    edad = estudiante[3]

    curso = estudiante[4]

    numero_lista = estudiante[5]


    # ======================================
    # CREAR SESION
    # ======================================

    session[
        "estudiante_id"
    ] = estudiante_id

    session[
        "nombre"
    ] = nombre

    session[
        "colegio"
    ] = colegio

    session[
        "edad"
    ] = edad

    session[
        "curso"
    ] = curso

    session[
        "numero_lista"
    ] = numero_lista


    return redirect(
        url_for(
            "progreso"
        )
    )


# ==========================================
# ROL DOCENTE
# ==========================================

def docente_actual():

    docente_id = session.get(
        "docente_id"
    )

    if docente_id is None:
        return None

    return obtener_docente(
        docente_id
    )


@app.route("/docente")
def docente_acceso():

    if docente_actual() is not None:
        return redirect(url_for("docente_panel"))

    return render_template(
        "docente_acceso.html"
    )


@app.route(
    "/docente/registro",
    methods=["POST"]
)
def docente_registro():

    nombre = request.form.get("nombre", "").strip()
    usuario = request.form.get("usuario", "").strip().lower()
    colegio = request.form.get("colegio", "").strip()
    clave = request.form.get("clave", "")

    if not nombre or not usuario or not colegio or len(clave) < 4:

        return render_template(
            "docente_acceso.html",
            pestana="registro",
            error_registro="Completa todos los datos. La clave debe tener al menos 4 caracteres."
        )

    docente_id = crear_docente(
        nombre,
        usuario,
        colegio,
        generate_password_hash(clave)
    )

    if docente_id is None:

        return render_template(
            "docente_acceso.html",
            pestana="registro",
            error_registro="Ese usuario ya existe. Elige otro o inicia sesión."
        )

    session["docente_id"] = docente_id

    return redirect(url_for("docente_panel"))


@app.route(
    "/docente/ingresar",
    methods=["POST"]
)
def docente_ingresar():

    usuario = request.form.get("usuario", "").strip().lower()
    clave = request.form.get("clave", "")

    docente = buscar_docente(usuario)

    if docente is None or not check_password_hash(docente[4], clave):

        return render_template(
            "docente_acceso.html",
            error_ingreso="Usuario o clave incorrectos."
        )

    session["docente_id"] = docente[0]

    return redirect(url_for("docente_panel"))


@app.route("/docente/panel")
def docente_panel():

    docente = docente_actual()

    if docente is None:
        return redirect(url_for("docente_acceso"))

    colegio = docente[3]
    curso = request.args.get("curso") or None

    kpis, estudiantes, subtemas = resumen_curso(
        colegio,
        curso
    )

    return render_template(
        "docente_panel.html",
        docente=docente,
        cursos=obtener_cursos(colegio),
        curso=curso,
        kpis=kpis,
        estudiantes=estudiantes,
        subtemas=subtemas[:6]
    )


@app.route("/docente/estudiante/<int:estudiante_id>")
def docente_estudiante(estudiante_id):

    docente = docente_actual()

    if docente is None:
        return redirect(url_for("docente_acceso"))

    estudiante = obtener_estudiante(estudiante_id)

    if estudiante is None or estudiante[2].strip().lower() != docente[3].strip().lower():
        return redirect(url_for("docente_panel"))

    return render_template(
        "docente_estudiante.html",
        docente=docente,
        nombre=estudiante[1],
        curso=estudiante[4],
        numero_lista=estudiante[5],
        colegio=estudiante[2],
        historial=obtener_historial(estudiante_id),
        dominios=obtener_dominios_actuales(estudiante_id),
        evolucion=obtener_evolucion_bkt(estudiante_id)
    )


@app.route("/docente/exportar")
def docente_exportar():

    docente = docente_actual()

    if docente is None:
        return redirect(url_for("docente_acceso"))

    curso = request.args.get("curso") or None

    kpis, estudiantes, subtemas = resumen_curso(
        docente[3],
        curso
    )

    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")

    escritor.writerow([
        "Curso", "Numero de lista", "Nombre", "Evaluaciones", "Planes",
        "Ultima evaluacion (%)", "Mejora (puntos)", "Dominio promedio", "Estado"
    ])

    for e in estudiantes:
        escritor.writerow([
            e["curso"],
            e["numero_lista"],
            e["nombre"],
            e["evaluaciones"],
            e["planes"],
            "" if e["ultima"] is None else round(e["ultima"], 1),
            "" if e["mejora"] is None else round(e["mejora"], 1),
            "" if e["dominio"] is None else round(e["dominio"], 2),
            e["estado"]
        ])

    nombre_archivo = f"tutoria_{curso or 'todos'}.csv"

    return Response(
        "\ufeff" + salida.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={nombre_archivo}"}
    )


@app.route("/docente/salir")
def docente_salir():

    session.pop("docente_id", None)

    return redirect(url_for("inicio"))


# ==========================================
# SALIR DEL ESTUDIANTE
# ==========================================

@app.route("/salir")
def salir():

    docente_id = session.get("docente_id")

    session.clear()

    if docente_id is not None:
        session["docente_id"] = docente_id

    return redirect(url_for("inicio"))


# ==========================================
# EJECUTAR
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=True
    )