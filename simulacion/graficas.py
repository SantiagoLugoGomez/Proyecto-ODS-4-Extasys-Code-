import json, random, statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
R = json.load(open("resultados.json")); F = json.load(open("estudiantes.json")); B = json.load(open("robustez.json"))
AZUL, NARANJA, GRIS = "#2a78d6", "#eb6834", "#595959"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#8c8c8c", "axes.labelcolor": "#222", "xtick.color": "#444", "ytick.color": "#444"})

def guardar(nombre):
    plt.tight_layout(); plt.savefig(nombre, dpi=220); plt.close()

# Fig 7: mejora por grupo
fig, ax = plt.subplots(figsize=(4.2, 3.2))
rng = random.Random(3)
for i, (g, c, etiqueta) in enumerate([("plan", AZUL, "Con plan (n = 50)"), ("control", NARANJA, "Sin plan (n = 50)")]):
    v = [f["mejora"] for f in F if f["grupo"] == g]
    ax.scatter([i + rng.uniform(-0.17, 0.17) for _ in v], v, s=14, color=c, alpha=0.45, linewidths=0)
    m = statistics.mean(v); ee = statistics.stdev(v) / len(v) ** .5
    ax.errorbar(i + 0.32, m, yerr=1.96 * ee, fmt="o", color=c, markersize=7, capsize=4, lw=2)
ax.axhline(0, color="#bdbdbd", lw=1, zorder=0)
ax.set_xticks([0, 1], ["Con plan\n(n = 50)", "Sin plan\n(n = 50)"])
ax.set_ylabel("Mejora (puntos porcentuales)")
ax.set_xlim(-0.5, 1.6)
guardar("fig7_mejora.png")

# Fig 8: tiempos
fig, ax = plt.subplots(figsize=(4.2, 3.0))
n = [b["n"] for b in R["barrido"]]
ax.plot(n, [b["fuerza_ms"] for b in R["barrido"]], "-o", color=NARANJA, lw=2, ms=6, label="Fuerza bruta")
ax.plot(n, [b["mochila_ms"] for b in R["barrido"]], "-o", color=AZUL, lw=2, ms=6, label="Mochila con memorización")
ax.set_yscale("log"); ax.set_xticks(n)
ax.set_xlabel("Número de ejercicios n"); ax.set_ylabel("Tiempo mediano (ms, escala log)")
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, 1.22), ncol=2, fontsize=8.5)
guardar("fig8_tiempos.png")

# Fig 9: dominio estimado vs estado real
est = []
import importlib
fig, ax = plt.subplots(figsize=(4.2, 3.0))
sabia, no = [], []
codigo = open("simulacion.py").read().split("rng = random.Random(SEMILLA)")[0]
import sys; sys.path.insert(0, ".."); sys.argv = ["x", ".."]
g = {}; exec(codigo, g)
r = random.Random(R["semilla"]); estudiantes = [g["crear_estudiante"](r, i + 1) for i in range(100)]
for e, f in zip(estudiantes, F):
    for s in range(4):
        (sabia if e["sabe"][s] else no).append(f["dominio"][s])
bins = [i / 20 for i in range(21)]
ax.hist([no, sabia], bins=bins, stacked=True, color=[NARANJA, AZUL], label=[f"No lo dominaba ({len(no)})", f"Sí lo dominaba ({len(sabia)})"], edgecolor="white", linewidth=1)
ax.set_xlabel("Dominio estimado por BKT"); ax.set_ylabel("Subtemas")
ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(-0.02, 1.24), ncol=2, fontsize=8, handlelength=1.2, columnspacing=1)
guardar("fig9_bkt.png")

# Fig 10: efecto en 30 cohortes
fig, ax = plt.subplots(figsize=(4.2, 1.7))
ef = sorted(B["efectos"])
ax.scatter(ef, [0] * len(ef), s=40, color=AZUL, alpha=0.6, linewidths=0)
ax.axvline(10, color=GRIS, lw=1.2, ls="--")
ax.axvline(0, color="#bdbdbd", lw=1)
ax.set_yticks([]); ax.spines["left"].set_visible(False)
ax.set_xlim(-1, 12); ax.set_xlabel("Mejora con plan menos mejora sin plan (puntos)")
ax.set_xticks([0, 2, 4, 6, 8, 10], ["0", "2", "4", "6", "8", "10 (meta)"])
guardar("fig10_cohortes.png")
print("ok")
