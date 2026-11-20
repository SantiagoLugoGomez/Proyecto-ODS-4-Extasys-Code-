import sys, json, random, time, itertools, statistics
sys.path.insert(0, sys.argv[1])
from bkt import actualizar_bkt, PROBABILIDAD_INICIAL
from beneficio import calcular_beneficio
from mochila import recomendar_ejercicios

SEMILLA = 2026
N = 100
PREGUNTAS = [3, 3, 2, 2]
TIEMPOS = [20, 30, 40, 60]


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


def evaluar(rng, e, sabe):
    respuestas = []
    for s, cantidad in enumerate(PREGUNTAS):
        for _ in range(cantidad):
            p = 1 - e["descuido"] if sabe[s] else e["adivina"]
            respuestas.append((s, rng.random() < p))
    nota = sum(ok for _, ok in respuestas) * 10
    return nota, respuestas


def estimar(respuestas):
    dominio = [PROBABILIDAD_INICIAL] * 4
    for s, ok in respuestas:
        dominio[s] = actualizar_bkt(dominio[s], ok)
    return dominio


def plan_mochila(e, dominio):
    ejercicios = [{"subtema": s, "tiempo": e["ejercicios"][s], "beneficio": calcular_beneficio(dominio[s])} for s in range(4)]
    elegidos, usado, beneficio = recomendar_ejercicios(ejercicios, e["tiempo"])
    return [x["subtema"] for x in elegidos], usado, beneficio, ejercicios


def plan_azar(rng, e):
    orden = list(range(4))
    rng.shuffle(orden)
    elegidos, usado = [], 0
    for s in orden:
        if usado + e["ejercicios"][s] <= e["tiempo"]:
            elegidos.append(s)
            usado += e["ejercicios"][s]
    return elegidos, usado


def plan_voraz(ejercicios, tiempo):
    orden = sorted(ejercicios, key=lambda x: x["beneficio"] / x["tiempo"], reverse=True)
    elegidos, usado, beneficio = [], 0, 0
    for x in orden:
        if usado + x["tiempo"] <= tiempo:
            elegidos.append(x["subtema"])
            usado += x["tiempo"]
            beneficio += x["beneficio"]
    return elegidos, usado, beneficio


def estudiar(rng, e, sabe, elegidos):
    nuevo = list(sabe)
    for s in elegidos:
        if not nuevo[s]:
            p = 1 - (1 - e["aprende"]) ** (e["ejercicios"][s] / 10)
            nuevo[s] = rng.random() < p
    return nuevo


def fuerza_bruta(ejercicios, tiempo):
    mejor = 0
    for k in range(len(ejercicios) + 1):
        for combo in itertools.combinations(ejercicios, k):
            if sum(x["tiempo"] for x in combo) <= tiempo:
                mejor = max(mejor, sum(x["beneficio"] for x in combo))
    return mejor


def sesion(semilla, e, condicion):
    rng = random.Random(semilla)
    nota1, respuestas = evaluar(rng, e, e["sabe"])
    dominio = estimar(respuestas)
    elegidos_m, usado_m, beneficio_m, ejercicios = plan_mochila(e, dominio)
    if condicion == "plan":
        elegidos, usado = elegidos_m, usado_m
    elif condicion == "voraz":
        elegidos, usado, _ = plan_voraz(ejercicios, e["tiempo"])
    else:
        elegidos, usado = plan_azar(rng, e)
    rng2 = random.Random(semilla * 7 + 1)
    sabe2 = estudiar(rng2, e, e["sabe"], elegidos)
    nota2, _ = evaluar(rng2, e, sabe2)
    return {"nota1": nota1, "nota2": nota2, "mejora": nota2 - nota1, "usado": usado,
            "dominio": dominio, "subtemas_aprendidos": sum(sabe2) - sum(e["sabe"]), "elegidos": elegidos}


def welch(a, b):
    ma, mb = statistics.mean(a), statistics.mean(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    se = (va / len(a) + vb / len(b)) ** 0.5
    t = (ma - mb) / se
    gl = se ** 4 / ((va / len(a)) ** 2 / (len(a) - 1) + (vb / len(b)) ** 2 / (len(b) - 1))
    sp = (((len(a) - 1) * va + (len(b) - 1) * vb) / (len(a) + len(b) - 2)) ** 0.5
    return t, gl, (ma - mb) / sp


def bootstrap(a, b, rng, veces=10000):
    difs = sorted(statistics.mean(rng.choices(a, k=len(a))) - statistics.mean(rng.choices(b, k=len(b))) for _ in range(veces))
    return difs[int(0.025 * veces)], difs[int(0.975 * veces)]


rng = random.Random(SEMILLA)
estudiantes = [crear_estudiante(rng, i + 1) for i in range(N)]
grupos = ["plan"] * (N // 2) + ["control"] * (N // 2)
rng.shuffle(grupos)

filas = []
for e, g in zip(estudiantes, grupos):
    semilla = SEMILLA * 1000 + e["id"]
    r = sesion(semilla, e, g)
    contrafactual = {c: sesion(semilla, e, c) for c in ["plan", "control", "voraz"]}
    filas.append({"id": e["id"], "grupo": g, "tiempo": e["tiempo"], "sabia": sum(e["sabe"]), **r,
                  "cf": {c: v["mejora"] for c, v in contrafactual.items()}})

plan = [f["mejora"] for f in filas if f["grupo"] == "plan"]
control = [f["mejora"] for f in filas if f["grupo"] == "control"]
t, gl, d = welch(plan, control)
from scipy import stats
p = stats.ttest_ind(plan, control, equal_var=False, alternative="greater").pvalue
ic = bootstrap(plan, control, random.Random(1))

cf_plan = [f["cf"]["plan"] for f in filas]
cf_control = [f["cf"]["control"] for f in filas]
cf_voraz = [f["cf"]["voraz"] for f in filas]
pareado = [a - b for a, b in zip(cf_plan, cf_control)]
p_pareado = stats.ttest_rel(cf_plan, cf_control, alternative="greater").pvalue

conocidos, desconocidos = [], []
for e, f in zip(estudiantes, filas):
    for s in range(4):
        (conocidos if e["sabe"][s] else desconocidos).append(f["dominio"][s])
auc = stats.mannwhitneyu(conocidos, desconocidos).statistic / (len(conocidos) * len(desconocidos))

# H2 y H3 sobre las 100 instancias reales y un barrido
tiempos_ms, iguales, voraz_peor = [], 0, 0
for e, f in zip(estudiantes, filas):
    ejercicios = [{"subtema": s, "tiempo": e["ejercicios"][s], "beneficio": calcular_beneficio(f["dominio"][s])} for s in range(4)]
    inicio = time.perf_counter()
    _, usado, beneficio = recomendar_ejercicios(ejercicios, e["tiempo"])
    tiempos_ms.append((time.perf_counter() - inicio) * 1000)
    iguales += abs(beneficio - fuerza_bruta(ejercicios, e["tiempo"])) < 1e-9
    assert usado <= e["tiempo"]
    voraz_peor += plan_voraz(ejercicios, e["tiempo"])[2] < beneficio - 1e-9

rng3 = random.Random(7)
barrido = []
extra_iguales, extra_total = 0, 0
for n in [4, 8, 12, 16, 20]:
    medidas_m, medidas_f = [], []
    for _ in range(20):
        ejercicios = [{"subtema": i, "tiempo": rng3.choice([5, 10, 15, 20]), "beneficio": round(rng3.uniform(0, 10), 2)} for i in range(n)]
        T = rng3.choice([20, 30, 40, 60])
        a = time.perf_counter(); _, _, bm = recomendar_ejercicios(ejercicios, T); medidas_m.append((time.perf_counter() - a) * 1000)
        a = time.perf_counter(); bf = fuerza_bruta(ejercicios, T); medidas_f.append((time.perf_counter() - a) * 1000)
        extra_iguales += abs(bm - bf) < 1e-9
        extra_total += 1
    barrido.append({"n": n, "mochila_ms": statistics.median(medidas_m), "fuerza_ms": statistics.median(medidas_f)})
grande = [{"subtema": i, "tiempo": rng3.randint(5, 30), "beneficio": rng3.uniform(0, 10)} for i in range(200)]
a = time.perf_counter(); recomendar_ejercicios(grande, 120); grande_ms = (time.perf_counter() - a) * 1000

# P-03: secuencia conocida
d0 = PROBABILIDAD_INICIAL
secuencia = []
for ok in [True, True, False, True, True]:
    d0 = actualizar_bkt(d0, ok); secuencia.append(round(d0, 4))

def resumen(x):
    return {"media": statistics.mean(x), "de": statistics.stdev(x), "mediana": statistics.median(x)}

def por_tiempo(c):
    return {T: statistics.mean([f["cf"]["plan"] - f["cf"]["control"] for f in filas if f["tiempo"] == T]) for T in TIEMPOS}

R = {
    "n": N, "semilla": SEMILLA,
    "plan": resumen(plan), "control": resumen(control), "n_plan": len(plan), "n_control": len(control),
    "nota1_plan": statistics.mean(f["nota1"] for f in filas if f["grupo"] == "plan"),
    "nota1_control": statistics.mean(f["nota1"] for f in filas if f["grupo"] == "control"),
    "nota2_plan": statistics.mean(f["nota2"] for f in filas if f["grupo"] == "plan"),
    "nota2_control": statistics.mean(f["nota2"] for f in filas if f["grupo"] == "control"),
    "diferencia": statistics.mean(plan) - statistics.mean(control), "t": t, "gl": gl, "p": p, "d": d, "ic": ic,
    "pareado": resumen(pareado), "p_pareado": p_pareado,
    "cf_plan": statistics.mean(cf_plan), "cf_control": statistics.mean(cf_control), "cf_voraz": statistics.mean(cf_voraz),
    "por_tiempo": por_tiempo(None),
    "auc": auc, "dom_conocidos": statistics.mean(conocidos), "dom_desconocidos": statistics.mean(desconocidos),
    "h2_max_ms": max(tiempos_ms), "h2_mediana_ms": statistics.median(tiempos_ms),
    "h3_iguales": iguales, "voraz_peor": voraz_peor, "extra_iguales": extra_iguales, "extra_total": extra_total,
    "barrido": barrido, "grande_ms": grande_ms, "secuencia": secuencia,
    "uso_tiempo": statistics.mean(f["usado"] / f["tiempo"] for f in filas if f["grupo"] == "plan") * 100,
    "uso_tiempo_control": statistics.mean(f["usado"] / f["tiempo"] for f in filas if f["grupo"] == "control") * 100,
}
json.dump(R, open("resultados.json", "w"), indent=1)
json.dump(filas, open("estudiantes.json", "w"))
print(json.dumps({k: v for k, v in R.items() if k != "barrido"}, indent=1, default=str))
print(barrido)
