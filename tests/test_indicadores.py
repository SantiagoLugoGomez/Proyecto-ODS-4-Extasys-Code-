"""KPIs del panel docente (Tabla 6 del paper)."""

import pytest

from base_datos import (
    guardar_dominio_bkt,
    guardar_plan,
    guardar_resultado,
    obtener_o_crear_estudiante,
)
from indicadores import resumen_curso

COLEGIO = "Colegio Rural"


def estudiante(lista, nombre, curso="1101"):
    return obtener_o_crear_estudiante(lista, nombre, COLEGIO, 16, curso)


def evaluacion(estudiante_id, porcentaje):
    guardar_resultado(estudiante_id, "Fisica", "Vectores", "Basico", porcentaje // 10, 10,
                      porcentaje)


def test_resumen_curso():
    ana = estudiante(1, "Ana")
    beto = estudiante(2, "Beto")
    estudiante(3, "Caro")  # sin actividad
    dani = estudiante(4, "Dani", curso="1102")

    evaluacion(ana, 40)
    evaluacion(ana, 70)
    guardar_dominio_bkt(ana, "Fisica", "Vectores", "Magnitud", 0.3)
    guardar_dominio_bkt(ana, "Fisica", "Vectores", "Magnitud", 0.8)  # cuenta el último
    guardar_dominio_bkt(ana, "Fisica", "Vectores", "Direccion", 0.6)
    guardar_plan(ana, "Fisica", "Vectores", 30, 30, 8.0, 2)

    evaluacion(beto, 50)
    guardar_dominio_bkt(beto, "Fisica", "Vectores", "Magnitud", 0.2)
    guardar_dominio_bkt(beto, "Fisica", "Vectores", "Direccion", 0.3)

    evaluacion(dani, 90)

    kpis, filas, subtemas = resumen_curso(COLEGIO.upper() + "  ", "1101")

    assert kpis["registrados"] == 3
    assert kpis["activos"] == 2
    assert kpis["evaluaciones"] == 3
    assert kpis["acierto"] == pytest.approx((40 + 70 + 50) / 3)
    assert kpis["mejora"] == 30
    assert kpis["retorno"] == 50
    assert kpis["uso_plan"] == pytest.approx(100 / 3)
    assert kpis["apoyo"] == 1

    estados = {f["nombre"]: f["estado"] for f in filas}
    assert estados == {"Ana": "Al día", "Beto": "Necesita apoyo", "Caro": "Sin actividad"}

    assert [s["subtema"] for s in subtemas] == ["Direccion", "Magnitud"]
    assert subtemas[0]["dominio"] == pytest.approx(0.45)
    assert subtemas[1]["estudiantes"] == 2

    todos, _, _ = resumen_curso(COLEGIO)
    assert todos["registrados"] == 4


def test_curso_vacio():
    kpis, filas, subtemas = resumen_curso("Colegio sin estudiantes")
    assert filas == [] and subtemas == []
    assert kpis["acierto"] is None and kpis["retorno"] is None and kpis["uso_plan"] is None
