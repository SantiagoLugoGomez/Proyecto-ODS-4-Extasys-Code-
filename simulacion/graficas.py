"""Figuras 6 a 9 del paper a partir de los resultados guardados.

Uso: ``python -m simulacion.graficas`` (después de experimento y robustez).
"""

import json
import random
import statistics

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from simulacion import RESULTADOS  # noqa: E402

AZUL, NARANJA, GRIS, CAFE = "#2a78d6", "#eb6834", "#bdbdbd", "#8b4513"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#8c8c8c",
    "axes.labelcolor": "#222222",
    "axes.titleweight": "bold",
    "axes.titlesize": 11,
    "axes.titlelocation": "left",
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": "#e6e6e6",
    "axes.axisbelow": True,
    "xtick.color": "#444444",
    "ytick.color": "#444444",
})


def cargar(nombre):
    with open(RESULTADOS / nombre, encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar(figura, nombre):
    figura.tight_layout()
    figura.savefig(RESULTADOS / nombre, dpi=200)
    plt.close(figura)
    print(f"  {RESULTADOS.name}/{nombre}")


def figura_6_mejora(filas):
    """Mejora individual por grupo, con la media y su IC del 95 %."""
    figura, ejes = plt.subplots(figsize=(4.6, 3.4))
    rng = random.Random(3)
    etiquetas = []
    for i, (grupo, color, nombre) in enumerate([("plan", AZUL, "Con plan"),
                                                ("control", NARANJA, "Sin plan")]):
        valores = [f["mejora"] for f in filas if f["grupo"] == grupo]
        etiquetas.append(f"{nombre} (n = {len(valores)})")
        ejes.scatter([i + rng.uniform(-0.15, 0.15) for _ in valores], valores, s=14,
                     color=color, alpha=0.45, linewidths=0)
        media = statistics.mean(valores)
        ee = statistics.stdev(valores) / len(valores) ** 0.5
        ejes.errorbar(i + 0.3, media, yerr=1.96 * ee, fmt="o", color=color, markersize=7,
                      capsize=4, lw=2)
    ejes.axhline(0, color=GRIS, lw=1, zorder=0)
    ejes.set_xticks([0, 1], etiquetas)
    ejes.set_xlim(-0.5, 1.6)
    ejes.set_xlabel("Grupo")
    ejes.set_ylabel("Mejora (puntos porcentuales)")
    ejes.set_title("Mejora por grupo")
    guardar(figura, "fig6_mejora.png")


def figura_7_cohortes(robustez):
    """Distribución de la ventaja del plan en las cohortes."""
    figura, ejes = plt.subplots(figsize=(4.6, 3.0))
    efectos = robustez["efectos"]
    bordes = [x / 2 for x in range(0, 22)]
    ejes.hist(efectos, bins=bordes, color=AZUL, edgecolor="white", linewidth=1)
    ejes.axvline(0, color=AZUL, lw=1.2)
    ejes.axvline(10, color=CAFE, lw=1, ls="--")
    ejes.text(9.85, ejes.get_ylim()[1] * 0.95, "Meta H1", color=CAFE, ha="right", va="top",
              fontsize=8)
    ejes.set_xlim(-0.5, 10.5)
    ejes.set_xticks(range(0, 11, 2))
    ejes.set_xlabel("Ventaja del plan (puntos porcentuales)")
    ejes.set_ylabel("Número de cohortes")
    ejes.set_title(f"Ventaja del plan en {robustez['cohortes']} cohortes")
    guardar(figura, "fig7_cohortes.png")


def figura_8_bkt(filas):
    """Dominio estimado por el BKT frente al estado real de cada subtema."""
    dominaba = [f["dominio"][s] for f in filas for s in range(4) if f["sabe"][s]]
    no_dominaba = [f["dominio"][s] for f in filas for s in range(4) if not f["sabe"][s]]
    figura, ejes = plt.subplots(figsize=(4.6, 3.5))
    ejes.hist([no_dominaba, dominaba], bins=[i / 20 for i in range(21)], stacked=True,
              color=[NARANJA, AZUL], edgecolor="white", linewidth=1,
              label=[f"No lo dominaba ({len(no_dominaba)})", f"Sí lo dominaba ({len(dominaba)})"])
    ejes.set_xlabel("Dominio estimado por BKT (probabilidad, 0 a 1)")
    ejes.set_ylabel("Número de subtemas")
    ejes.set_title("Dominio estimado frente al estado real")
    ejes.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2,
                fontsize=8.5)
    guardar(figura, "fig8_bkt.png")


def figura_9_tiempos(experimento):
    """Tiempo mediano de cálculo del plan según el número de ejercicios."""
    barrido = experimento["barrido"]
    n = [b["n"] for b in barrido]
    figura, ejes = plt.subplots(figsize=(4.6, 3.4))
    ejes.plot(n, [b["fuerza_ms"] for b in barrido], "-o", color=NARANJA, lw=2, ms=5,
              label="Fuerza bruta")
    ejes.plot(n, [b["mochila_ms"] for b in barrido], "-o", color=AZUL, lw=2, ms=5,
              label="Mochila con memoización")
    ejes.set_yscale("log")
    ejes.set_xticks(n)
    ejes.set_xlabel("Número de ejercicios n")
    ejes.set_ylabel("Tiempo mediano (ms, escala log)")
    ejes.set_title("Tiempo de cálculo del plan")
    ejes.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2,
                fontsize=8.5)
    guardar(figura, "fig9_tiempos.png")


def main():
    experimento = cargar("experimento.json")
    filas = cargar("estudiantes.json")
    robustez = cargar("robustez.json")
    print("Figuras:")
    figura_6_mejora(filas)
    figura_7_cohortes(robustez)
    figura_8_bkt(filas)
    figura_9_tiempos(experimento)


if __name__ == "__main__":
    main()
