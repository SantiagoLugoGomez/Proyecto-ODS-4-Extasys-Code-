"""BKT, beneficio y mochila 0/1 (sección VI del paper)."""

import itertools
import random

import pytest

from beneficio import calcular_beneficio
from bkt import APRENDIZAJE, PROBABILIDAD_INICIAL, actualizar_bkt
from mochila import recomendar_ejercicios


def dominio_tras(respuestas, inicial=PROBABILIDAD_INICIAL):
    p = inicial
    for correcta in respuestas:
        p = actualizar_bkt(p, correcta)
    return p


# ------------------------------------------------------------------
# BKT
# ------------------------------------------------------------------


def test_bkt_secuencia_del_paper():
    """P-03: acierta, acierta, falla, acierta, acierta desde 0,5."""
    p, secuencia = PROBABILIDAD_INICIAL, []
    for correcta in [True, True, False, True, True]:
        p = actualizar_bkt(p, correcta)
        secuencia.append(round(p, 4))
    assert secuencia == [0.8364, 0.9625, 0.7861, 0.9487, 0.9893]


def test_bkt_dos_errores_y_beneficio_del_paper():
    """Con dos errores seguidos el dominio baja de 0,5 a 0,1273 y el beneficio sube a 8,73."""
    p = dominio_tras([False, False])
    assert p == pytest.approx(0.1273, abs=1e-4)
    assert calcular_beneficio(p) == pytest.approx(8.73, abs=1e-2)


@pytest.mark.parametrize("p", [0.0, 0.01, 0.2, 0.5, 0.8, 0.99, 1.0])
def test_bkt_es_una_probabilidad_y_acertar_sube_mas_que_fallar(p):
    acierto, error = actualizar_bkt(p, True), actualizar_bkt(p, False)
    assert APRENDIZAJE <= error <= acierto <= 1


def test_bkt_un_error_no_hunde_y_un_acierto_no_vuelve_experto():
    assert actualizar_bkt(0.9, False) > 0.5
    assert actualizar_bkt(0.5, True) < 0.95


# ------------------------------------------------------------------
# Beneficio
# ------------------------------------------------------------------


@pytest.mark.parametrize(("dominio", "esperado"), [(0, 10), (0.5, 5), (1, 0), (0.95, 0.5)])
def test_beneficio(dominio, esperado):
    assert calcular_beneficio(dominio) == pytest.approx(esperado)


# ------------------------------------------------------------------
# Mochila 0/1
# ------------------------------------------------------------------


def fuerza_bruta(ejercicios, tiempo):
    mejor = 0
    for k in range(len(ejercicios) + 1):
        for combo in itertools.combinations(ejercicios, k):
            if sum(e["tiempo"] for e in combo) <= tiempo:
                mejor = max(mejor, sum(e["beneficio"] for e in combo))
    return mejor


def test_mochila_tabla_5_del_paper():
    """Con 30 minutos la mochila elige Racionalización y Límites directos (8,80);
    el voraz por beneficio por minuto se queda con 8,53."""
    candidatos = [
        {"nombre": "Límites directos", "tiempo": 10, "respuestas": [True, True, True]},
        {"nombre": "Factorización", "tiempo": 15, "respuestas": [True, False, False]},
        {"nombre": "Racionalización", "tiempo": 20, "respuestas": [False, False]},
        {"nombre": "Límites laterales", "tiempo": 15, "respuestas": [True, True]},
    ]
    for c in candidatos:
        c["beneficio"] = calcular_beneficio(dominio_tras(c["respuestas"]))

    elegidos, usado, beneficio = recomendar_ejercicios(candidatos, 30)

    assert [c["nombre"] for c in elegidos] == ["Límites directos", "Racionalización"]
    assert usado == 30
    assert beneficio == pytest.approx(8.80, abs=5e-3)

    # El voraz escoge peor.
    voraz, tiempo, total = [], 0, 0
    for c in sorted(candidatos, key=lambda c: c["beneficio"] / c["tiempo"], reverse=True):
        if tiempo + c["tiempo"] <= 30:
            voraz.append(c["nombre"])
            tiempo += c["tiempo"]
            total += c["beneficio"]
    assert sorted(voraz) == ["Factorización", "Límites laterales"]
    assert total < beneficio


def test_mochila_igual_a_fuerza_bruta_en_instancias_aleatorias():
    """H3: el plan siempre tiene el mismo beneficio que la mejor combinación."""
    rng = random.Random(2026)
    for _ in range(300):
        n = rng.randint(0, 11)
        ejercicios = [
            {"id": i, "tiempo": rng.choice([5, 10, 15, 20, 25]),
             "beneficio": round(rng.uniform(0, 10), 2)}
            for i in range(n)
        ]
        tiempo = rng.choice([0, 10, 20, 30, 40, 60])

        elegidos, usado, beneficio = recomendar_ejercicios(ejercicios, tiempo)

        assert beneficio == pytest.approx(fuerza_bruta(ejercicios, tiempo))
        assert usado == sum(e["tiempo"] for e in elegidos) <= tiempo
        assert sum(e["beneficio"] for e in elegidos) == pytest.approx(beneficio)
        assert len({e["id"] for e in elegidos}) == len(elegidos)
        # Conserva el orden de llegada.
        assert [e["id"] for e in elegidos] == sorted(e["id"] for e in elegidos)


def test_mochila_casos_borde():
    assert recomendar_ejercicios([], 30) == ([], 0, 0)
    uno = {"tiempo": 30, "beneficio": 5}
    assert recomendar_ejercicios([uno], 29) == ([], 0, 0)
    assert recomendar_ejercicios([uno], 30) == ([uno], 30, 5)


def test_mochila_empate_prefiere_no_incluir():
    a = {"nombre": "a", "tiempo": 10, "beneficio": 4}
    b = {"nombre": "b", "tiempo": 10, "beneficio": 4}
    elegidos, _, beneficio = recomendar_ejercicios([a, b], 10)
    assert beneficio == 4
    assert elegidos == [b]


def test_mochila_escala_a_200_ejercicios():
    rng = random.Random(7)
    grandes = [{"tiempo": rng.randint(5, 30), "beneficio": rng.uniform(0, 10)}
               for _ in range(200)]
    elegidos, usado, beneficio = recomendar_ejercicios(grandes, 120)
    assert usado <= 120
    assert sum(e["beneficio"] for e in elegidos) == pytest.approx(beneficio)
