import sys, os, json, random, time, csv, io, re, sqlite3
sys.path.insert(0, os.getcwd())
import app as m
from indicadores import resumen_curso

SUB = ["limites", "derivadas", "continuidad", "asintotas"]
CANT = [3, 3, 2, 2]
actual = {}

def preguntas(materia, tema, nivel):
    return [{"pregunta": f"P{i}", "opciones": ["a1", "b2", "c3", "d4"], "correcta": 1, "subtema": s}
            for s, c in zip(SUB, CANT) for i in range(c)]

def ejercicios(materia, tema, nivel, subtemas):
    return [{"nombre": s, "ejercicio": "x", "subtema": s, "tiempo": actual["tiempos"][SUB.index(s)]} for s in subtemas]

m.generar_preguntas = preguntas
m.generar_ejercicios_refuerzo = ejercicios
m.app.config["TESTING"] = True
rng = random.Random(2026)
violaciones, tiempos_ms, retomados = 0, [], 0
for i in range(100):
    c = m.app.test_client()
    sabe = [rng.random() < rng.uniform(0.15, 0.85) for _ in range(4)]
    actual["tiempos"] = [rng.choice([10, 15, 20]) for _ in range(4)]
    T = rng.choice([20, 30, 40, 60])
    datos = {"numero_lista": str(i % 40 + 1), "nombre": f"Estudiante {i+1:03d}", "colegio": "Colegio Simulado", "edad": "16",
             "curso": ["1001", "1002", "1101"][i % 3] if i < 40 or True else "", "materia": "calculo diferencial", "tema": "Limites", "nivel": "basico"}
    datos["numero_lista"] = str(i + 1)
    for ronda in range(2):
        assert c.post("/evaluacion", data=datos).status_code == 200
        resp = {}
        k = 0
        for s, cant in enumerate(CANT):
            for _ in range(cant):
                ok = rng.random() < (0.9 if sabe[s] else 0.2)
                resp[f"pregunta_{k}"] = "1" if ok else "2"; k += 1
        assert c.post("/resultado", data=resp).status_code == 200
        a = time.perf_counter()
        r = c.post("/recomendacion", data={"tiempo_disponible": str(T)})
        tiempos_ms.append((time.perf_counter() - a) * 1000)
        assert r.status_code == 200
        if ronda == 0:
            sabe = [x or rng.random() < 0.4 for x in sabe]
    with c.session_transaction() as ses:
        eid = ses["estudiante_id"]

con = sqlite3.connect("data/tutoria.db")
for disp, usado in con.execute("select tiempo_disponible, tiempo_usado from planes"):
    violaciones += usado > disp
planes = con.execute("select count(*) from planes").fetchone()[0]
evals = con.execute("select count(*) from resultados").fetchone()[0]
filas_bkt = con.execute("select count(*) from progreso_bkt").fetchone()[0]

d = m.app.test_client()
d.post("/docente/registro", data={"nombre": "Docente", "usuario": "doc", "colegio": "colegio simulado", "clave": "1234"})
a = time.perf_counter(); panel = d.get("/docente/panel"); panel_ms = (time.perf_counter() - a) * 1000
csv_txt = d.get("/docente/exportar").data.decode("utf-8-sig")
kpis, filas, subtemas = resumen_curso("Colegio Simulado")
R = {"estudiantes": len(filas), "evaluaciones": evals, "planes": planes, "violaciones": violaciones, "filas_bkt": filas_bkt,
     "recomendacion_ms_mediana": sorted(tiempos_ms)[len(tiempos_ms)//2], "recomendacion_ms_max": max(tiempos_ms),
     "panel_status": panel.status_code, "panel_ms": panel_ms, "csv_filas": len(csv_txt.strip().splitlines()) - 1,
     "kpis": kpis, "subtema_debil": subtemas[0]}
print(json.dumps(R, indent=1, default=str))
json.dump(R, open("simulacion/integracion.json", "w"), indent=1, default=str)
