"""Experimento principal: H1 (aprendizaje), H2 (rendimiento) y H3 (exactitud).

Se generan 50 estudiantes con semilla fija (2026). Cada uno tiene un estado real por
subtema (domina o no) que la aplicación no conoce: solo ve sus respuestas. Se asignan al
azar a dos grupos de 25 (con plan de la mochila / sin plan) y además se aplica cada
condición a todos los estudiantes (análisis contrafactual). Ver la Tabla 8 del paper.

Uso: ``python -m simulacion.experimento``
"""

import itertools
import json
import random
import statistics
import time

from scipy import stats

from beneficio import calcular_beneficio
from bkt import PROBABILIDAD_INICIAL, actualizar_bkt
from mochila import recomendar_ejercicios
from simulacion import RESULTADOS

SEMILLA = 2026
N = 50
PREGUNTAS = [3, 3, 2, 2]
TIEMPOS = [20, 30, 40, 60]


# ------------------------------------------------------------------
# Modelo del estudiante simulado (Tabla 8)
# ------------------------------------------------------------------


def crear_estudiante(rng, numero):
    return {
        "id": numero,
        "sabe": [rng.random() < rng.uniform(0.15, 0.85) for _ in range(4)],
        "descuido": rng.uniform(0.05, 0.15),
        "adivina": rng.uniform(0.15, 0.30),
        "aprende": rng.uniform(0.25, 0.55),
        "tiempo": rng.choice(TIEMPOS),
        "ejercicios": [rng.choice([10, 15, 20]) for _ in range(4)],
    }


def evaluar(rng, estudiante, sabe):
    """Evaluación de 10 preguntas (3, 3, 2, 2). Devuelve la nota (0-100) y las respuestas."""
    respuestas = []
    for subtema, cantidad in enumerate(PREGUNTAS):
        for _ in range(cantidad):
            p = 1 - estudiante["descuido"] if sabe[subtema] else estudiante["adivina"]
            respuestas.append((subtema, rng.random() < p))
    nota = sum(correcta for _, correcta in respuestas) * 10
    return nota, respuestas


def estimar(respuestas):
    """Dominio por subtema con el BKT de la aplicación (parámetros fijos)."""
    dominio = [PROBABILIDAD_INICIAL] * 4
    for subtema, correcta in respuestas:
        dominio[subtema] = actualizar_bkt(dominio[subtema], correcta)
    return dominio


def candidatos(estudiante, dominio):
    return [
        {"subtema": s, "tiempo": estudiante["ejercicios"][s],
         "beneficio": calcular_beneficio(dominio[s])}
        for s in range(4)
    ]


def plan_mochila(estudiante, dominio):
    ejercicios = candidatos(estudiante, dominio)
    elegidos, usado, beneficio = recomendar_ejercicios(ejercicios, estudiante["tiempo"])
    return [x["subtema"] for x in elegidos], usado, beneficio, ejercicios


def plan_azar(rng, estudiante):
    """Repaso sin guía: ejercicios en orden aleatorio hasta llenar el tiempo."""
    orden = list(range(4))
    rng.shuffle(orden)
    elegidos, usado = [], 0
    for s in orden:
        if usado + estudiante["ejercicios"][s] <= estudiante["tiempo"]:
            elegidos.append(s)
            usado += estudiante["ejercicios"][s]
    return elegidos, usado


def plan_voraz(ejercicios, tiempo):
    """Voraz por beneficio por minuto (no garantiza el óptimo en la mochila 0/1)."""
    orden = sorted(ejercicios, key=lambda x: x["beneficio"] / x["tiempo"], reverse=True)
    elegidos, usado, beneficio = [], 0, 0
    for x in orden:
        if usado + x["tiempo"] <= tiempo:
            elegidos.append(x["subtema"])
            usado += x["tiempo"]
            beneficio += x["beneficio"]
    return elegidos, usado, beneficio


def estudiar(rng, estudiante, sabe, elegidos):
    """Un ejercicio solo hace aprender si el subtema no se dominaba."""
    nuevo = list(sabe)
    for s in elegidos:
        if not nuevo[s]:
            p = 1 - (1 - estudiante["aprende"]) ** (estudiante["ejercicios"][s] / 10)
            nuevo[s] = rng.random() < p
    return nuevo


def fuerza_bruta(ejercicios, tiempo):
    """Mejor beneficio revisando los 2^n subconjuntos."""
    mejor = 0
    for k in range(len(ejercicios) + 1):
        for combo in itertools.combinations(ejercicios, k):
            if sum(x["tiempo"] for x in combo) <= tiempo:
                mejor = max(mejor, sum(x["beneficio"] for x in combo))
    return mejor


def sesion(semilla, estudiante, condicion):
    """Evaluación, estudio de T minutos según la condición y segunda evaluación."""
    rng = random.Random(semilla)
    nota1, respuestas = evaluar(rng, estudiante, estudiante["sabe"])
    dominio = estimar(respuestas)
    elegidos_m, usado_m, _beneficio_m, ejercicios = plan_mochila(estudiante, dominio)
    if condicion == "plan":
        elegidos, usado = elegidos_m, usado_m
    elif condicion == "voraz":
        elegidos, usado, _ = plan_voraz(ejercicios, estudiante["tiempo"])
    else:
        elegidos, usado = plan_azar(rng, estudiante)
    rng2 = random.Random(semilla * 7 + 1)
    sabe2 = estudiar(rng2, estudiante, estudiante["sabe"], elegidos)
    nota2, _ = evaluar(rng2, estudiante, sabe2)
    return {
        "nota1": nota1, "nota2": nota2, "mejora": nota2 - nota1, "usado": usado,
        "dominio": dominio, "subtemas_aprendidos": sum(sabe2) - sum(estudiante["sabe"]),
        "elegidos": elegidos,
    }


# ------------------------------------------------------------------
# Estadística
# ------------------------------------------------------------------


def welch(a, b):
    """Estadístico t de Welch, grados de libertad y d de Cohen."""
    ma, mb = statistics.mean(a), statistics.mean(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    ee = (va / len(a) + vb / len(b)) ** 0.5
    t = (ma - mb) / ee
    gl = ee**4 / ((va / len(a)) ** 2 / (len(a) - 1) + (vb / len(b)) ** 2 / (len(b) - 1))
    sp = (((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2)) ** 0.5
    return t, gl, (ma - mb) / sp, ee


def bootstrap(a, b, rng, veces=10000):
    """IC del 95 % de la diferencia de medias por remuestreo."""
    difs = sorted(
        statistics.mean(rng.choices(a, k=len(a))) - statistics.mean(rng.choices(b, k=len(b)))
        for _ in range(veces)
    )
    return difs[int(0.025 * veces)], difs[int(0.975 * veces)]


def ancova(filas):
    """Regresión mejora ~ grupo + nota inicial. Devuelve efecto, error estándar y p."""
    import numpy as np

    y = np.array([f["mejora"] for f in filas], float)
    grupo = np.array([f["grupo"] == "plan" for f in filas], float)
    x = np.column_stack([np.ones_like(grupo), grupo, [f["nota1"] for f in filas]])
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    residuos = y - x @ beta
    gl = len(y) - x.shape[1]
    covarianza = residuos @ residuos / gl * np.linalg.inv(x.T @ x)
    ee = float(covarianza[1, 1] ** 0.5)
    t = float(beta[1]) / ee
    return {"efecto": float(beta[1]), "ee": ee, "t": t, "p": float(2 * stats.t.sf(abs(t), gl))}


def resumen(valores):
    return {"media": statistics.mean(valores), "de": statistics.stdev(valores),
            "mediana": statistics.median(valores)}


# ------------------------------------------------------------------
# Experimento
# ------------------------------------------------------------------


def experimento(n=N, semilla=SEMILLA):
    """Ejecuta el experimento completo. Devuelve (resultados, filas por estudiante)."""
    rng = random.Random(semilla)
    estudiantes = [crear_estudiante(rng, i + 1) for i in range(n)]
    grupos = ["plan"] * (n // 2) + ["control"] * (n // 2)
    rng.shuffle(grupos)

    filas = []
    for e, g in zip(estudiantes, grupos):
        semilla_e = semilla * 1000 + e["id"]
        r = sesion(semilla_e, e, g)
        contrafactual = {c: sesion(semilla_e, e, c) for c in ["plan", "control", "voraz"]}
        filas.append({
            "id": e["id"], "grupo": g, "tiempo": e["tiempo"], "sabia": sum(e["sabe"]),
            "sabe": e["sabe"], **r, "cf": {c: v["mejora"] for c, v in contrafactual.items()},
        })

    # H1: comparación entre grupos (Welch, bootstrap, d de Cohen y ANCOVA).
    plan = [f["mejora"] for f in filas if f["grupo"] == "plan"]
    control = [f["mejora"] for f in filas if f["grupo"] == "control"]
    t, gl, d, ee = welch(plan, control)
    p = stats.ttest_ind(plan, control, equal_var=False, alternative="greater").pvalue
    ic = bootstrap(plan, control, random.Random(1))

    # H1: análisis contrafactual (las dos condiciones en los mismos estudiantes).
    cf_plan = [f["cf"]["plan"] for f in filas]
    cf_control = [f["cf"]["control"] for f in filas]
    cf_voraz = [f["cf"]["voraz"] for f in filas]
    pareado = [a - b for a, b in zip(cf_plan, cf_control)]
    p_pareado = stats.ttest_rel(cf_plan, cf_control, alternative="greater").pvalue
    ic_pareado = stats.ttest_rel(cf_plan, cf_control).confidence_interval(0.95)

    # Calidad del BKT: AUC del dominio estimado frente al estado real.
    conocidos, desconocidos = [], []
    for e, f in zip(estudiantes, filas):
        for s in range(4):
            (conocidos if e["sabe"][s] else desconocidos).append(f["dominio"][s])
    auc = stats.mannwhitneyu(conocidos, desconocidos).statistic / (
        len(conocidos) * len(desconocidos)
    )

    # H2 y H3 sobre las instancias reales de los estudiantes.
    tiempos_ms, iguales, voraz_peor = [], 0, 0
    for e, f in zip(estudiantes, filas):
        ejercicios = candidatos(e, f["dominio"])
        inicio = time.perf_counter()
        _, usado, beneficio = recomendar_ejercicios(ejercicios, e["tiempo"])
        tiempos_ms.append((time.perf_counter() - inicio) * 1000)
        iguales += abs(beneficio - fuerza_bruta(ejercicios, e["tiempo"])) < 1e-9
        assert usado <= e["tiempo"]
        voraz_peor += plan_voraz(ejercicios, e["tiempo"])[2] < beneficio - 1e-9

    # H2 y H3 sobre 100 instancias aleatorias con n entre 4 y 20 (Figura 9).
    rng3 = random.Random(7)
    barrido, extra_iguales, extra_total = [], 0, 0
    for n_ej in [4, 8, 12, 16, 20]:
        medidas_m, medidas_f = [], []
        for _ in range(20):
            ejercicios = [
                {"subtema": i, "tiempo": rng3.choice([5, 10, 15, 20]),
                 "beneficio": round(rng3.uniform(0, 10), 2)}
                for i in range(n_ej)
            ]
            capacidad = rng3.choice([20, 30, 40, 60])
            a = time.perf_counter()
            _, _, bm = recomendar_ejercicios(ejercicios, capacidad)
            medidas_m.append((time.perf_counter() - a) * 1000)
            a = time.perf_counter()
            bf = fuerza_bruta(ejercicios, capacidad)
            medidas_f.append((time.perf_counter() - a) * 1000)
            extra_iguales += abs(bm - bf) < 1e-9
            extra_total += 1
        barrido.append({"n": n_ej, "mochila_ms": statistics.median(medidas_m),
                        "fuerza_ms": statistics.median(medidas_f)})

    grande = [{"subtema": i, "tiempo": rng3.randint(5, 30), "beneficio": rng3.uniform(0, 10)}
              for i in range(200)]
    a = time.perf_counter()
    recomendar_ejercicios(grande, 120)
    grande_ms = (time.perf_counter() - a) * 1000

    # P-03: secuencia conocida de la sección VI-A.
    dominio, secuencia = PROBABILIDAD_INICIAL, []
    for correcta in [True, True, False, True, True]:
        dominio = actualizar_bkt(dominio, correcta)
        secuencia.append(round(dominio, 4))

    def media_grupo(clave, grupo):
        return statistics.mean(f[clave] for f in filas if f["grupo"] == grupo)

    resultados = {
        "n": n, "semilla": semilla,
        "plan": resumen(plan), "control": resumen(control),
        "n_plan": len(plan), "n_control": len(control),
        "nota1_plan": media_grupo("nota1", "plan"),
        "nota1_control": media_grupo("nota1", "control"),
        "nota2_plan": media_grupo("nota2", "plan"),
        "nota2_control": media_grupo("nota2", "control"),
        "diferencia": statistics.mean(plan) - statistics.mean(control),
        "ee_diferencia": ee, "t": t, "gl": gl, "p": p, "d": d, "ic": list(ic),
        "ancova": ancova(filas),
        "pareado": resumen(pareado), "p_pareado": p_pareado,
        "ic_pareado": [ic_pareado.low, ic_pareado.high],
        "cf_plan": statistics.mean(cf_plan), "cf_control": statistics.mean(cf_control),
        "cf_voraz": statistics.mean(cf_voraz),
        "por_tiempo": {
            capacidad: statistics.mean(
                f["cf"]["plan"] - f["cf"]["control"] for f in filas if f["tiempo"] == capacidad
            )
            for capacidad in TIEMPOS
            if any(f["tiempo"] == capacidad for f in filas)
        },
        "auc": auc, "subtemas_dominados": len(conocidos),
        "subtemas_no_dominados": len(desconocidos),
        "dom_conocidos": statistics.mean(conocidos),
        "dom_desconocidos": statistics.mean(desconocidos),
        "h2_max_ms": max(tiempos_ms), "h2_mediana_ms": statistics.median(tiempos_ms),
        "h3_iguales": iguales, "voraz_peor": voraz_peor,
        "extra_iguales": extra_iguales, "extra_total": extra_total,
        "barrido": barrido, "grande_ms": grande_ms, "secuencia": secuencia,
        "uso_tiempo": statistics.mean(
            f["usado"] / f["tiempo"] for f in filas if f["grupo"] == "plan") * 100,
        "uso_tiempo_control": statistics.mean(
            f["usado"] / f["tiempo"] for f in filas if f["grupo"] == "control") * 100,
    }
    return resultados, filas


def imprimir(r):
    print(f"Experimento con {r['n']} estudiantes (semilla {r['semilla']})")
    print(f"  Con plan:  nota {r['nota1_plan']:.1f} -> {r['nota2_plan']:.1f}, "
          f"mejora {r['plan']['media']:.1f} (DE {r['plan']['de']:.1f})")
    print(f"  Sin plan:  nota {r['nota1_control']:.1f} -> {r['nota2_control']:.1f}, "
          f"mejora {r['control']['media']:.1f} (DE {r['control']['de']:.1f})")
    print(f"  Diferencia {r['diferencia']:.1f} pp, IC 95 % [{r['ic'][0]:.1f}; {r['ic'][1]:.1f}], "
          f"t = {r['t']:.2f}, d = {r['d']:.2f}")
    print(f"  Ajustada por nota inicial (ANCOVA): {r['ancova']['efecto']:.1f} pp "
          f"(EE {r['ancova']['ee']:.1f}, p = {r['ancova']['p']:.2f})")
    print(f"  Contrafactual: +{r['pareado']['media']:.1f} pp, p = {r['p_pareado']:.3f}")
    print(f"  BKT: AUC {r['auc']:.2f} ({r['subtemas_dominados']} dominados, "
          f"{r['subtemas_no_dominados']} no dominados)")
    print(f"  H3: {r['h3_iguales'] + r['extra_iguales']} de {r['n'] + r['extra_total']} "
          f"iguales a la fuerza bruta; voraz peor en {r['voraz_peor']} de {r['n']}")
    print(f"  H2: máx {r['h2_max_ms']:.3f} ms (n = 4); n = 20: mochila "
          f"{r['barrido'][-1]['mochila_ms']:.2f} ms, fuerza bruta "
          f"{r['barrido'][-1]['fuerza_ms']:.0f} ms; n = 200: {r['grande_ms']:.1f} ms")


def main():
    resultados, filas = experimento()
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    with open(RESULTADOS / "experimento.json", "w", encoding="utf-8") as archivo:
        json.dump(resultados, archivo, indent=1)
    with open(RESULTADOS / "estudiantes.json", "w", encoding="utf-8") as archivo:
        json.dump(filas, archivo, indent=None)
    imprimir(resultados)


if __name__ == "__main__":
    main()
