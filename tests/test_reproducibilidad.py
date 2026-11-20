"""El código del repositorio reproduce las cifras de la evaluación del paper.

Los tiempos dependen del equipo y no se comparan; todo lo demás usa semillas fijas.
"""

import pytest

pytest.importorskip("scipy")
pytest.importorskip("numpy")

from simulacion.experimento import experimento  # noqa: E402
from simulacion.robustez import robustez  # noqa: E402


@pytest.fixture(scope="module")
def resultados():
    return experimento()[0]


def test_tabla_10_experimento_con_50_estudiantes(resultados):
    r = resultados
    assert (r["n_plan"], r["n_control"]) == (25, 25)
    assert round(r["nota1_plan"], 1) == 52.8
    assert round(r["nota1_control"], 1) == 47.2
    assert round(r["nota2_plan"], 1) == 61.2
    assert round(r["nota2_control"], 1) == 64.4
    assert round(r["plan"]["media"], 1) == 8.4
    assert round(r["plan"]["de"], 1) == 16.2
    assert round(r["control"]["media"], 1) == 17.2
    assert round(r["control"]["de"], 1) == 21.1
    assert round(r["uso_tiempo"], 1) == 86.2
    assert round(r["uso_tiempo_control"], 1) == 89.5


def test_seccion_x_a_estadistica(resultados):
    r = resultados
    assert round(r["diferencia"], 1) == -8.8
    assert [round(x, 1) for x in r["ic"]] == [-18.8, 1.6]
    assert round(r["t"], 2) == -1.65
    assert round(r["d"], 2) == -0.47
    assert round(r["ee_diferencia"], 1) == 5.3
    assert round(r["ancova"]["efecto"], 1) == -6.3
    assert round(r["ancova"]["ee"], 1) == 4.7
    assert round(r["pareado"]["media"], 1) == 4.2
    assert round(r["p_pareado"], 3) == 0.006


def test_seccion_x_b_c_bkt_y_mochila(resultados):
    r = resultados
    assert round(r["auc"], 2) == 0.95
    assert round(r["dom_conocidos"], 2) == 0.88
    assert round(r["dom_desconocidos"], 2) == 0.28
    assert (r["subtemas_dominados"], r["subtemas_no_dominados"]) == (89, 111)
    assert r["h3_iguales"] + r["extra_iguales"] == 150
    assert r["n"] + r["extra_total"] == 150
    assert r["voraz_peor"] == 7
    assert r["secuencia"] == [0.8364, 0.9625, 0.7861, 0.9487, 0.9893]


def test_figura_7_y_seccion_xi_robustez():
    r = robustez()
    assert round(r["efecto_medio"], 1) == 4.0
    assert round(r["efecto_min"], 1) == 0.6
    assert round(r["efecto_max"], 1) == 7.0
    assert r["cohortes_a_favor"] == 30
    assert round(r["plan_menos_voraz"], 1) == 0.6
    ventajas = [round(s["ventaja"], 1) for s in r["sensibilidad_aprendizaje"].values()]
    assert ventajas == [1.6, 3.9, 5.3]
