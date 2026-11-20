"""Servidor Flask de TutorIA: rutas del estudiante y del docente.

Ejecución: ``python app.py`` y abrir http://127.0.0.1:5000.
"""

import csv
import io
import logging
import re
import secrets
import threading
import time
import webbrowser

from flask import Flask, Response, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

import config
from base_datos import (
    buscar_docente,
    buscar_estudiante,
    cargar_dominio_bkt,
    crear_base_datos,
    crear_docente,
    guardar_dominio_bkt,
    guardar_plan,
    guardar_resultado,
    obtener_cursos,
    obtener_docente,
    obtener_dominios_actuales,
    obtener_estudiante,
    obtener_evolucion_bkt,
    obtener_historial,
    obtener_o_crear_estudiante,
)
from beneficio import calcular_beneficio
from bkt import PROBABILIDAD_INICIAL, actualizar_bkt
from ia import SUBTEMAS_FIJOS, ErrorIA, generar_ejercicios_refuerzo, generar_preguntas
from indicadores import resumen_curso
from mochila import recomendar_ejercicios

logger = logging.getLogger("tutoria")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=config.clave_secreta(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

crear_base_datos()

# ==========================================
# CONSTANTES DE LA INTERFAZ
# ==========================================

MATERIAS = {
    "Calculo Diferencial": "calculo diferencial",
    "Ingles": "ingles",
    "Fisica": "fisica",
}

TEMAS = {
    materia: [tema.capitalize() for tema in SUBTEMAS_FIJOS[clave]]
    for materia, clave in MATERIAS.items()
}

NIVELES = ["Basico", "Intermedio", "Avanzado"]

TIEMPOS_DISPONIBLES = [20, 30, 40, 60]

# Subtemas con beneficio menor a 0,5 (dominio de 95 % o más) no entran al plan.
BENEFICIO_MINIMO = 0.5

LONGITUD_MAXIMA_TEXTO = 120
CLAVE_MINIMA = 4

TILDES = {
    "calculo": "cálculo", "limites": "límites", "factorizacion": "factorización",
    "racionalizacion": "racionalización", "trigonometricas": "trigonométricas",
    "fisica": "física", "ingles": "inglés", "direccion": "dirección",
    "posicion": "posición", "aceleracion": "aceleración", "basico": "básico",
    "aplicacion": "aplicación", "interpretacion": "interpretación",
    "resolucion": "resolución",
}


# ==========================================
# EVALUACIONES EN CURSO
# ==========================================
# Las preguntas (con su respuesta correcta) se guardan en el servidor y la sesión solo
# lleva un identificador: así el estudiante no puede leer las respuestas en la cookie y
# una evaluación larga no supera el límite de 4 KB de las cookies.


class EvaluacionesEnCurso:
    """Almacén en memoria, con límite de tamaño y de antigüedad."""

    def __init__(self, maximo=1000, vigencia_s=6 * 3600):
        self._datos = {}
        self._candado = threading.Lock()
        self._maximo = maximo
        self._vigencia = vigencia_s

    def guardar(self, preguntas):
        identificador = secrets.token_urlsafe(16)
        ahora = time.monotonic()
        with self._candado:
            self._datos = {
                k: v for k, v in self._datos.items() if ahora - v[0] < self._vigencia
            }
            while len(self._datos) >= self._maximo:
                self._datos.pop(next(iter(self._datos)))
            self._datos[identificador] = (ahora, preguntas)
        return identificador

    def tomar(self, identificador):
        """Devuelve las preguntas y las borra: cada evaluación se califica una sola vez."""
        if not identificador:
            return None
        with self._candado:
            guardado = self._datos.pop(identificador, None)
        if guardado is None or time.monotonic() - guardado[0] >= self._vigencia:
            return None
        return guardado[1]


evaluaciones_en_curso = EvaluacionesEnCurso()


# ==========================================
# UTILIDADES
# ==========================================


class DatoInvalido(ValueError):
    """Un dato del formulario no es válido. El mensaje se muestra al usuario."""


def texto(nombre, etiqueta, obligatorio=True):
    valor = request.form.get(nombre, "").strip()
    if obligatorio and not valor:
        raise DatoInvalido(f"Falta el campo «{etiqueta}».")
    if len(valor) > LONGITUD_MAXIMA_TEXTO:
        raise DatoInvalido(f"El campo «{etiqueta}» es demasiado largo.")
    return valor


def entero(nombre, etiqueta, minimo, maximo):
    try:
        valor = int(request.form.get(nombre, ""))
    except ValueError:
        raise DatoInvalido(f"El campo «{etiqueta}» debe ser un número.") from None
    if not minimo <= valor <= maximo:
        raise DatoInvalido(f"El campo «{etiqueta}» debe estar entre {minimo} y {maximo}.")
    return valor


def render_inicio(codigo=200, **datos):
    return render_template("index.html", temas=TEMAS, **datos), codigo


def error_ia(error):
    """Página con el problema de LM Studio y un botón que reenvía el mismo formulario."""
    logger.error("Error de la IA en %s: %s", request.path, error)
    return render_template(
        "error_ia.html",
        mensaje=str(error),
        accion=request.path,
        campos=list(request.form.items()),
    ), 503


def nombre_archivo_seguro(texto_libre):
    return re.sub(r"[^0-9A-Za-z_-]+", "_", texto_libre).strip("_") or "todos"


@app.template_filter("bonito")
def bonito(texto_libre):
    """Agrega tildes y pone mayúscula inicial: 'calculo diferencial' -> 'Cálculo diferencial'."""
    palabras = [TILDES.get(p.lower(), p) for p in str(texto_libre).split()]
    resultado = " ".join(palabras)
    return resultado[:1].upper() + resultado[1:]


@app.template_filter("puntos")
def puntos(valores, ancho=160, alto=48):
    """Coordenadas SVG de una mini gráfica con valores entre 0 y 1."""
    if len(valores) == 1:
        valores = valores * 2
    paso = ancho / (len(valores) - 1)
    return " ".join(f"{i * paso:.1f},{alto - v * alto:.1f}" for i, v in enumerate(valores))


@app.after_request
def cabeceras_de_seguridad(respuesta):
    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    respuesta.headers.setdefault("X-Frame-Options", "DENY")
    respuesta.headers.setdefault("Referrer-Policy", "same-origin")
    return respuesta


@app.errorhandler(404)
def no_encontrado(_error):
    return render_template(
        "error.html", titulo="Página no encontrada",
        mensaje="La dirección que abriste no existe en TutorIA.",
    ), 404


@app.errorhandler(500)
def error_interno(_error):
    return render_template(
        "error.html", titulo="Algo salió mal",
        mensaje="Ocurrió un error inesperado. Vuelve al inicio e inténtalo de nuevo.",
    ), 500


# ==========================================
# ESTUDIANTE
# ==========================================


@app.route("/")
def inicio():
    return render_inicio()


@app.route("/evaluacion", methods=["POST"])
def evaluacion():
    """RF-01 y RF-02: registra al estudiante y genera su evaluación con la IA local."""
    try:
        nombre = texto("nombre", "Nombre")
        colegio = texto("colegio", "Colegio")
        curso = texto("curso", "Curso")
        numero_lista = entero("numero_lista", "Número de lista", 1, 999)
        edad = entero("edad", "Edad", 5, 99)
        materia = texto("materia", "Materia")
        nivel = texto("nivel", "Nivel")
        tema = texto("tema", "Tema")
        if tema == "__otro__":
            tema = texto("tema_otro", "Tema", obligatorio=False) or "General"
        nivel = {n.lower(): n for n in NIVELES}.get(nivel.lower())
        if nivel is None:
            raise DatoInvalido("Elige un nivel de la lista.")
    except DatoInvalido as error:
        return render_inicio(400, error_evaluacion=str(error))

    try:
        preguntas = generar_preguntas(materia, tema, nivel)
    except ErrorIA as error:
        return error_ia(error)

    estudiante_id = obtener_o_crear_estudiante(numero_lista, nombre, colegio, edad, curso)

    session.update(
        estudiante_id=estudiante_id,
        numero_lista=numero_lista,
        nombre=nombre,
        colegio=colegio,
        edad=edad,
        curso=curso,
        materia=materia,
        tema=tema,
        nivel=nivel,
        evaluacion_id=evaluaciones_en_curso.guardar(preguntas),
    )

    return render_template(
        "evaluacion.html", preguntas=preguntas, materia=materia, tema=tema, nivel=nivel
    )


@app.route("/resultado", methods=["POST"])
def resultado():
    """RF-03: califica, actualiza el dominio con BKT y lo guarda."""
    estudiante_id = session.get("estudiante_id")
    preguntas = evaluaciones_en_curso.tomar(session.pop("evaluacion_id", None))
    if not preguntas or estudiante_id is None:
        return redirect(url_for("inicio"))

    materia, tema, nivel = session["materia"], session["tema"], session["nivel"]

    puntaje = 0
    resultados = []
    dominios_bkt = {}
    dominios_anteriores = {}

    for indice, pregunta in enumerate(preguntas):
        respuesta = request.form.get(f"pregunta_{indice}")
        correcta = str(pregunta["correcta"])
        es_correcta = respuesta == correcta
        puntaje += es_correcta
        subtema = pregunta["subtema"]

        # El dominio parte del último valor guardado; si es nuevo, de P0 = 0,5.
        if subtema not in dominios_bkt:
            guardado = cargar_dominio_bkt(estudiante_id, materia, tema, subtema)
            dominios_anteriores[subtema] = guardado
            dominios_bkt[subtema] = PROBABILIDAD_INICIAL if guardado is None else guardado

        dominios_bkt[subtema] = actualizar_bkt(dominios_bkt[subtema], es_correcta)

        resultados.append({
            "pregunta": pregunta["pregunta"],
            "respuesta": respuesta,
            "correcta": correcta,
            "opciones": pregunta["opciones"],
            "es_correcta": es_correcta,
            "subtema": subtema,
        })

    total = len(preguntas)
    porcentaje = puntaje / total * 100
    guardar_resultado(estudiante_id, materia, tema, nivel, puntaje, total, porcentaje)

    beneficios = {}
    for subtema, dominio in dominios_bkt.items():
        guardar_dominio_bkt(estudiante_id, materia, tema, subtema, dominio)
        beneficios[subtema] = calcular_beneficio(dominio)

    session["dominios_bkt"] = dominios_bkt
    session["beneficios"] = beneficios

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
        nivel=nivel,
    )


@app.route("/recomendacion", methods=["POST"])
def recomendacion():
    """RF-04 y RF-05: un ejercicio por subtema y el plan óptimo con la mochila 0/1."""
    try:
        tiempo_disponible = int(request.form.get("tiempo_disponible", ""))
    except ValueError:
        return redirect(url_for("inicio"))

    materia, tema, nivel = session.get("materia"), session.get("tema"), session.get("nivel")
    beneficios = session.get("beneficios", {})
    estudiante_id = session.get("estudiante_id")

    if (
        None in (materia, tema, nivel, estudiante_id)
        or not beneficios
        or tiempo_disponible not in TIEMPOS_DISPONIBLES
    ):
        return redirect(url_for("inicio"))

    try:
        ejercicios = generar_ejercicios_refuerzo(materia, tema, nivel, list(beneficios))
    except ErrorIA as error:
        return error_ia(error)

    for ejercicio in ejercicios:
        ejercicio["beneficio"] = beneficios.get(ejercicio["subtema"], 0)

    ejercicios = [e for e in ejercicios if e["beneficio"] >= BENEFICIO_MINIMO]

    seleccionados, tiempo_total, beneficio_total = recomendar_ejercicios(
        ejercicios, tiempo_disponible
    )

    guardar_plan(
        estudiante_id, materia, tema, tiempo_disponible, tiempo_total, beneficio_total,
        len(seleccionados),
    )
    logger.info("Plan: %d ejercicios, %d de %d min, beneficio %.2f", len(seleccionados),
                tiempo_total, tiempo_disponible, beneficio_total)

    return render_template(
        "recomendaciones.html",
        ejercicios=seleccionados,
        tiempo_disponible=tiempo_disponible,
        tiempo_total=tiempo_total,
        beneficio_total=beneficio_total,
        materia=materia,
        tema=tema,
        nivel=nivel,
    )


@app.route("/progreso")
def progreso():
    """RF-06: historial de evaluaciones y evolución del dominio."""
    estudiante_id = session.get("estudiante_id")
    if estudiante_id is None:
        return redirect(url_for("inicio"))

    return render_template(
        "progreso.html",
        nombre=session.get("nombre", ""),
        numero_lista=session.get("numero_lista", ""),
        colegio=session.get("colegio", ""),
        curso=session.get("curso", ""),
        historial=obtener_historial(estudiante_id),
        dominios=obtener_dominios_actuales(estudiante_id),
        evolucion=obtener_evolucion_bkt(estudiante_id),
    )


@app.route("/consultar-progreso", methods=["POST"])
def consultar_progreso():
    try:
        colegio = texto("colegio_progreso", "Colegio")
        curso = texto("curso_progreso", "Curso")
        numero_lista = entero("numero_lista_progreso", "Número de lista", 1, 999)
    except DatoInvalido as error:
        return render_inicio(400, error_progreso=str(error))

    estudiante = buscar_estudiante(numero_lista, colegio, curso)
    if estudiante is None:
        return render_inicio(404, error_progreso="No se encontró un estudiante con esos datos.")

    estudiante_id, nombre, colegio, edad, curso, numero_lista = estudiante
    session.update(
        estudiante_id=estudiante_id,
        nombre=nombre,
        colegio=colegio,
        edad=edad,
        curso=curso,
        numero_lista=numero_lista,
    )
    return redirect(url_for("progreso"))


@app.route("/salir")
def salir():
    """Cierra la sesión del estudiante sin cerrar la del docente."""
    docente_id = session.get("docente_id")
    session.clear()
    if docente_id is not None:
        session["docente_id"] = docente_id
    return redirect(url_for("inicio"))


# ==========================================
# DOCENTE
# ==========================================


def docente_actual():
    docente_id = session.get("docente_id")
    return None if docente_id is None else obtener_docente(docente_id)


@app.route("/docente")
def docente_acceso():
    if docente_actual() is not None:
        return redirect(url_for("docente_panel"))
    return render_template("docente_acceso.html")


@app.route("/docente/registro", methods=["POST"])
def docente_registro():
    nombre = request.form.get("nombre", "").strip()
    usuario = request.form.get("usuario", "").strip().lower()
    colegio = request.form.get("colegio", "").strip()
    clave = request.form.get("clave", "")

    if not nombre or not usuario or not colegio or len(clave) < CLAVE_MINIMA:
        return render_template(
            "docente_acceso.html",
            pestana="registro",
            error_registro=(
                f"Completa todos los datos. La clave debe tener al menos {CLAVE_MINIMA} "
                "caracteres."
            ),
        ), 400

    docente_id = crear_docente(nombre, usuario, colegio, generate_password_hash(clave))
    if docente_id is None:
        return render_template(
            "docente_acceso.html",
            pestana="registro",
            error_registro="Ese usuario ya existe. Elige otro o inicia sesión.",
        ), 409

    session["docente_id"] = docente_id
    return redirect(url_for("docente_panel"))


@app.route("/docente/ingresar", methods=["POST"])
def docente_ingresar():
    usuario = request.form.get("usuario", "").strip().lower()
    clave = request.form.get("clave", "")

    docente = buscar_docente(usuario)
    if docente is None or not check_password_hash(docente[4], clave):
        return render_template(
            "docente_acceso.html", error_ingreso="Usuario o clave incorrectos."
        ), 401

    session["docente_id"] = docente[0]
    return redirect(url_for("docente_panel"))


@app.route("/docente/panel")
def docente_panel():
    """RF-07: KPIs del curso, subtemas más débiles y estado de cada estudiante."""
    docente = docente_actual()
    if docente is None:
        return redirect(url_for("docente_acceso"))

    colegio = docente[3]
    curso = request.args.get("curso") or None
    kpis, estudiantes, subtemas = resumen_curso(colegio, curso)

    return render_template(
        "docente_panel.html",
        docente=docente,
        cursos=obtener_cursos(colegio),
        curso=curso,
        kpis=kpis,
        estudiantes=estudiantes,
        subtemas=subtemas[:6],
    )


@app.route("/docente/estudiante/<int:estudiante_id>")
def docente_estudiante(estudiante_id):
    """RF-08: detalle de un estudiante del mismo colegio del docente."""
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
        evolucion=obtener_evolucion_bkt(estudiante_id),
    )


@app.route("/docente/exportar")
def docente_exportar():
    """RF-08: exporta el curso a CSV (separado por ';' y con BOM, para abrir en Excel)."""
    docente = docente_actual()
    if docente is None:
        return redirect(url_for("docente_acceso"))

    curso = request.args.get("curso") or None
    _kpis, estudiantes, _subtemas = resumen_curso(docente[3], curso)

    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=";")
    escritor.writerow([
        "Curso", "Numero de lista", "Nombre", "Evaluaciones", "Planes",
        "Ultima evaluacion (%)", "Mejora (puntos)", "Dominio promedio", "Estado",
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
            e["estado"],
        ])

    nombre = f"tutoria_{nombre_archivo_seguro(curso or 'todos')}.csv"
    return Response(
        "﻿" + salida.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@app.route("/docente/salir")
def docente_salir():
    session.pop("docente_id", None)
    return redirect(url_for("inicio"))


# ==========================================
# EJECUTAR
# ==========================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    direccion = f"http://{config.HOST}:{config.PUERTO}"
    logger.info("TutorIA en %s (LM Studio: %s, modelo: %s)", direccion, config.LM_STUDIO_URL,
                config.MODELO)
    if config.ABRIR_NAVEGADOR:
        threading.Timer(1.5, webbrowser.open, args=[direccion]).start()
    app.run(host=config.HOST, port=config.PUERTO, debug=config.DEBUG)
