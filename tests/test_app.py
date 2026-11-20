"""Flujo completo de la aplicación web: estudiante y docente."""

import sqlite3

import pytest
from conftest import DATOS_ESTUDIANTE, responder

import app as aplicacion
from ia import ErrorIA

TODAS_BIEN = [True] * 10
# Límites directos 3/3, Factorización 1/3, Racionalización 0/2, Límites laterales 2/2.
TABLA_5 = [True, True, True, True, False, False, False, False, True, True]


def contar(base, tabla):
    with sqlite3.connect(base) as conexion:
        return conexion.execute(f"SELECT count(*) FROM {tabla}").fetchone()[0]


def iniciar_evaluacion(cliente, **cambios):
    return cliente.post("/evaluacion", data={**DATOS_ESTUDIANTE, **cambios})


# ------------------------------------------------------------------
# Estudiante
# ------------------------------------------------------------------


def test_inicio(cliente):
    respuesta = cliente.get("/")
    assert respuesta.status_code == 200
    assert "Generar evaluación".encode() in respuesta.data
    assert respuesta.headers["X-Frame-Options"] == "DENY"


def test_flujo_completo_del_estudiante(cliente, base_temporal):
    respuesta = iniciar_evaluacion(cliente)
    assert respuesta.status_code == 200
    assert respuesta.data.count(b'class="tarjeta pregunta"') == 10

    resultado = responder(cliente, TABLA_5)
    assert resultado.status_code == 200
    assert b"6 de 10 correctas" in resultado.data

    plan = cliente.post("/recomendacion", data={"tiempo_disponible": "30"})
    assert plan.status_code == 200
    # Límites directos (dominio 0,99) y Límites laterales (0,96) ya se dominan y no
    # entran; entre Factorización (15 min) y Racionalización (20 min) solo cabe una.
    assert b"Ejercicio de Racionalizacion" in plan.data
    assert b"Ejercicio de Factorizacion" not in plan.data
    assert b"Ejercicio de Limites directos" not in plan.data

    progreso = cliente.get("/progreso")
    assert progreso.status_code == 200
    assert "Ana Gómez".encode() in progreso.data

    assert contar(base_temporal, "resultados") == 1
    assert contar(base_temporal, "progreso_bkt") == 4
    assert contar(base_temporal, "planes") == 1


def test_el_dominio_se_retoma_entre_sesiones(cliente):
    iniciar_evaluacion(cliente)
    responder(cliente, TODAS_BIEN)
    iniciar_evaluacion(cliente)
    respuesta = responder(cliente, TODAS_BIEN)
    # La segunda vez el BKT parte del dominio guardado y lo muestra como "Antes".
    assert b"Antes" in respuesta.data
    assert b"Primera vez" not in respuesta.data


def test_una_evaluacion_se_califica_una_sola_vez(cliente, base_temporal):
    iniciar_evaluacion(cliente)
    assert responder(cliente, TODAS_BIEN).status_code == 200
    reenvio = responder(cliente, TODAS_BIEN)
    assert reenvio.status_code == 302
    assert contar(base_temporal, "resultados") == 1


def test_las_respuestas_correctas_no_viajan_en_la_cookie(cliente):
    iniciar_evaluacion(cliente)
    with cliente.session_transaction() as sesion:
        assert "preguntas" not in sesion
        assert "evaluacion_id" in sesion


def test_plan_sin_evaluacion_vuelve_al_inicio(cliente):
    assert cliente.post("/recomendacion", data={"tiempo_disponible": "30"}).status_code == 302


def test_el_plan_respeta_el_tiempo(cliente, base_temporal):
    for minutos in [20, 30, 40, 60]:
        iniciar_evaluacion(cliente)
        responder(cliente, [False] * 10)
        assert cliente.post("/recomendacion",
                            data={"tiempo_disponible": str(minutos)}).status_code == 200
    with sqlite3.connect(base_temporal) as conexion:
        planes = conexion.execute("SELECT tiempo_disponible, tiempo_usado FROM planes").fetchall()
    assert len(planes) == 4
    assert all(usado <= disponible for disponible, usado in planes)


@pytest.mark.parametrize(("campo", "valor"), [("numero_lista", "abc"), ("edad", "200"),
                                              ("nombre", ""), ("nivel", "Experto")])
def test_datos_invalidos_muestran_un_mensaje(cliente, base_temporal, campo, valor):
    respuesta = iniciar_evaluacion(cliente, **{campo: valor})
    assert respuesta.status_code == 400
    assert b'class="alerta"' in respuesta.data
    assert contar(base_temporal, "estudiantes") == 0


def test_lm_studio_apagado_muestra_reintentar(cliente, monkeypatch, base_temporal):
    def falla(*_):
        raise ErrorIA("No se pudo conectar con LM Studio en http://localhost:1234/v1.")

    monkeypatch.setattr(aplicacion, "generar_preguntas", falla)
    respuesta = iniciar_evaluacion(cliente)

    assert respuesta.status_code == 503
    assert b"No se pudo conectar con LM Studio" in respuesta.data
    assert b"Reintentar" in respuesta.data
    assert 'value="Ana Gómez"'.encode() in respuesta.data  # el formulario se conserva
    assert contar(base_temporal, "estudiantes") == 0


def test_consultar_progreso(cliente):
    datos = {"colegio_progreso": DATOS_ESTUDIANTE["colegio"],
             "curso_progreso": DATOS_ESTUDIANTE["curso"], "numero_lista_progreso": "7"}
    no_existe = cliente.post("/consultar-progreso", data=datos)
    assert "No se encontró".encode() in no_existe.data

    iniciar_evaluacion(cliente)
    responder(cliente, TODAS_BIEN)
    cliente.get("/salir")

    existe = cliente.post("/consultar-progreso", data=datos)
    assert existe.status_code == 302
    assert existe.headers["Location"].endswith("/progreso")


def test_pagina_no_encontrada(cliente):
    respuesta = cliente.get("/no-existe")
    assert respuesta.status_code == 404
    assert "Página no encontrada".encode() in respuesta.data


# ------------------------------------------------------------------
# Docente
# ------------------------------------------------------------------


def registrar_docente(cliente, colegio="colegio rural el progreso", usuario="profe"):
    return cliente.post("/docente/registro", data={
        "nombre": "Profe Rocío", "usuario": usuario, "colegio": colegio, "clave": "secreta",
    })


def test_panel_docente_y_exportacion(cliente, ia_falsa):
    iniciar_evaluacion(cliente)
    responder(cliente, TABLA_5)
    cliente.post("/recomendacion", data={"tiempo_disponible": "30"})

    docente = aplicacion.app.test_client()
    assert registrar_docente(docente).status_code == 302

    panel = docente.get("/docente/panel")
    assert panel.status_code == 200
    assert "Ana Gómez".encode() in panel.data
    assert "Racionalización".encode() in panel.data  # subtema más débil

    csv = docente.get("/docente/exportar?curso=1101")
    assert csv.mimetype == "text/csv"
    assert 'filename="tutoria_1101.csv"' in csv.headers["Content-Disposition"]
    lineas = csv.data.decode("utf-8-sig").strip().splitlines()
    assert lineas[0].startswith("Curso;Numero de lista;Nombre")
    assert lineas[1].startswith("1101;7;Ana Gómez;1;1;60.0")


def test_docente_no_ve_estudiantes_de_otro_colegio(cliente):
    iniciar_evaluacion(cliente)
    responder(cliente, TODAS_BIEN)
    with cliente.session_transaction() as sesion:
        estudiante_id = sesion["estudiante_id"]

    otro = aplicacion.app.test_client()
    registrar_docente(otro, colegio="Otro colegio", usuario="otro")
    assert otro.get(f"/docente/estudiante/{estudiante_id}").status_code == 302

    propio = aplicacion.app.test_client()
    registrar_docente(propio)
    assert propio.get(f"/docente/estudiante/{estudiante_id}").status_code == 200


def test_ingreso_docente(cliente):
    assert registrar_docente(cliente).status_code == 302
    cliente.get("/docente/salir")
    assert cliente.get("/docente/panel").status_code == 302

    mala = cliente.post("/docente/ingresar", data={"usuario": "profe", "clave": "otra"})
    assert mala.status_code == 401
    buena = cliente.post("/docente/ingresar", data={"usuario": "PROFE", "clave": "secreta"})
    assert buena.status_code == 302

    repetido = registrar_docente(aplicacion.app.test_client())
    assert repetido.status_code == 409


def test_la_clave_se_guarda_con_hash(cliente, base_temporal):
    registrar_docente(cliente)
    with sqlite3.connect(base_temporal) as conexion:
        clave = conexion.execute("SELECT clave_hash FROM docentes").fetchone()[0]
    assert clave != "secreta"
    assert clave.startswith(("scrypt:", "pbkdf2:"))
