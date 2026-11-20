"""Robustez de H1: 30 cohortes de 50 estudiantes y sensibilidad a la tasa de aprendizaje.

En cada cohorte se aplican las condiciones con plan, sin plan y voraz a los mismos
estudiantes y se calcula la ventaja media del plan (Figura 7 y sección XI-B del paper).

Uso: ``python -m simulacion.robustez``
"""

import json
import random
import statistics

from simulacion import RESULTADOS
from simulacion.experimento import N, crear_estudiante, sesion

COHORTES = 30
TASAS_APRENDIZAJE = {"bajo": (0.10, 0.25), "medio": (0.25, 0.55), "alto": (0.55, 0.85)}
COHORTES_SENSIBILIDAD = 10


def ventaja(semilla, estudiantes, contra="control"):
    plan = [sesion(semilla * 1000 + e["id"], e, "plan")["mejora"] for e in estudiantes]
    otro = [sesion(semilla * 1000 + e["id"], e, contra)["mejora"] for e in estudiantes]
    return statistics.mean(plan) - statistics.mean(otro), statistics.mean(plan)


def robustez(n=N, cohortes=COHORTES):
    efectos, frente_a_voraz, mejoras_plan = [], [], []
    for semilla in range(1, cohortes + 1):
        rng = random.Random(semilla)
        estudiantes = [crear_estudiante(rng, i + 1) for i in range(n)]
        efecto, mejora_plan = ventaja(semilla, estudiantes)
        efectos.append(efecto)
        mejoras_plan.append(mejora_plan)
        frente_a_voraz.append(ventaja(semilla, estudiantes, "voraz")[0])

    sensibilidad = {}
    for nombre, (bajo, alto) in TASAS_APRENDIZAJE.items():
        valores = []
        for semilla in range(1, COHORTES_SENSIBILIDAD + 1):
            rng = random.Random(semilla)
            estudiantes = [crear_estudiante(rng, i + 1) for i in range(n)]
            for e in estudiantes:
                e["aprende"] = random.Random(e["id"] + semilla).uniform(bajo, alto)
            valores.append(ventaja(semilla, estudiantes)[0])
        sensibilidad[nombre] = {"rango": [bajo, alto], "ventaja": statistics.mean(valores)}

    return {
        "n": n,
        "cohortes": cohortes,
        "efectos": sorted(efectos),
        "efecto_medio": statistics.mean(efectos),
        "efecto_min": min(efectos),
        "efecto_max": max(efectos),
        "cohortes_a_favor": sum(e > 0 for e in efectos),
        "mejora_media_plan": statistics.mean(mejoras_plan),
        "plan_menos_voraz": statistics.mean(frente_a_voraz),
        "sensibilidad_aprendizaje": sensibilidad,
    }


def main():
    r = robustez()
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    with open(RESULTADOS / "robustez.json", "w", encoding="utf-8") as archivo:
        json.dump(r, archivo, indent=1)
    print(f"{r['cohortes']} cohortes de {r['n']} estudiantes")
    print(f"  Ventaja del plan: media {r['efecto_medio']:.1f} pp, entre {r['efecto_min']:.1f} "
          f"y {r['efecto_max']:.1f}; a favor en {r['cohortes_a_favor']} de {r['cohortes']}")
    print(f"  Plan frente a voraz: {r['plan_menos_voraz']:.1f} pp")
    for nombre, s in r["sensibilidad_aprendizaje"].items():
        print(f"  Aprendizaje {nombre} {s['rango']}: ventaja {s['ventaja']:.1f} pp")


if __name__ == "__main__":
    main()
