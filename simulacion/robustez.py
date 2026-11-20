import sys, random, statistics, json
codigo = open("simulacion.py").read().split("rng = random.Random(SEMILLA)")[0]
exec(codigo)
efectos, voraz, todos = [], [], []
for semilla in range(1, 31):
    rng = random.Random(semilla)
    est = [crear_estudiante(rng, i + 1) for i in range(100)]
    p = [sesion(semilla * 1000 + e["id"], e, "plan")["mejora"] for e in est]
    c = [sesion(semilla * 1000 + e["id"], e, "control")["mejora"] for e in est]
    v = [sesion(semilla * 1000 + e["id"], e, "voraz")["mejora"] for e in est]
    efectos.append(statistics.mean(p) - statistics.mean(c))
    voraz.append(statistics.mean(p) - statistics.mean(v))
    todos.append(statistics.mean(p))
efectos.sort()
print("efecto medio", statistics.mean(efectos), "min", efectos[0], "max", efectos[-1], "p2.5", efectos[0], "mejora plan media", statistics.mean(todos))
print("plan - voraz", statistics.mean(voraz))
# sensibilidad a la tasa de aprendizaje
for lo, hi in [(0.1, 0.25), (0.25, 0.55), (0.55, 0.85)]:
    ef = []
    for semilla in range(1, 11):
        rng = random.Random(semilla)
        est = [crear_estudiante(rng, i + 1) for i in range(100)]
        for e in est: e["aprende"] = random.Random(e["id"] + semilla).uniform(lo, hi)
        p = [sesion(semilla * 1000 + e["id"], e, "plan")["mejora"] for e in est]
        c = [sesion(semilla * 1000 + e["id"], e, "control")["mejora"] for e in est]
        ef.append(statistics.mean(p) - statistics.mean(c))
    print("aprende", lo, hi, "efecto", round(statistics.mean(ef), 2))
json.dump({"efectos": efectos, "voraz": statistics.mean(voraz)}, open("robustez.json", "w"))
