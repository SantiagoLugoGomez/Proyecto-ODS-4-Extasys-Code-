"""Pruebas del producto P-05, P-06 y P-07 (Tabla 9 del paper).

Los 50 estudiantes simulados recorren la aplicación real con el cliente de pruebas de
Flask: cada uno se registra, presenta dos evaluaciones y pide dos planes; luego un
docente abre el panel y exporta el curso. LM Studio se reemplaza por un generador con
subtemas conocidos, porque el entorno de pruebas no tiene el modelo. Se usa una base de
datos temporal: nunca se toca ``data/tutoria.db``.

Uso: ``python -m simulacion.integracion``
"""

import json
import random
import sqlite3
import tempfile
import time
from pathlib import Path

import config
from simulacion import RESULTADOS

N = 50
SUBTEMAS = ["limites", "derivadas", "continuidad", "asintotas"]
CANTIDADES = [3, 3, 2, 2]


def integracion(n=N, semilla=2026):
    carpeta = Path(tempfile.mkdtemp(prefix="tutoria-integracion-"))
    config.RUTA_DATA = carpeta
    config.RUTA_BD = carpeta / "tutoria.db"

    import app as aplicacion
    from base_datos import crear_base_datos
    from indicadores import resumen_curso

    crear_base_datos()
    estado = {}

    def preguntas_falsas(materia, tema, nivel):
        return [
            {"pregunta": f"P{i}", "opciones": ["a1", "b2", "c3", "d4"], "correcta": 1,
             "subtema": s}
            for s, c in zip(SUBTEMAS, CANTIDADES) for i in range(c)
        ]

    def ejercicios_falsos(materia, tema, nivel, subtemas):
        return [
            {"nombre": s, "ejercicio": "x", "subtema": s,
             "tiempo": estado["tiempos"][SUBTEMAS.index(s)]}
            for s in subtemas
        ]

    originales = (aplicacion.generar_preguntas, aplicacion.generar_ejercicios_refuerzo)
    aplicacion.generar_preguntas = preguntas_falsas
    aplicacion.generar_ejercicios_refuerzo = ejercicios_falsos
    aplicacion.app.config["TESTING"] = True

    rng = random.Random(semilla)
    tiempos_ms = []
    try:
        for i in range(n):
            cliente = aplicacion.app.test_client()
            sabe = [rng.random() < rng.uniform(0.15, 0.85) for _ in range(4)]
            estado["tiempos"] = [rng.choice([10, 15, 20]) for _ in range(4)]
            capacidad = rng.choice([20, 30, 40, 60])
            datos = {
                "numero_lista": str(i + 1), "nombre": f"Estudiante {i + 1:03d}",
                "colegio": "Colegio Simulado", "edad": "16",
                "curso": ["1001", "1002", "1101"][i % 3], "materia": "calculo diferencial",
                "tema": "Limites", "nivel": "basico",
            }
            for ronda in range(2):
                assert cliente.post("/evaluacion", data=datos).status_code == 200
                respuestas, k = {}, 0
                for s, cantidad in enumerate(CANTIDADES):
                    for _ in range(cantidad):
                        acierta = rng.random() < (0.9 if sabe[s] else 0.2)
                        respuestas[f"pregunta_{k}"] = "1" if acierta else "2"
                        k += 1
                assert cliente.post("/resultado", data=respuestas).status_code == 200
                inicio = time.perf_counter()
                r = cliente.post("/recomendacion", data={"tiempo_disponible": str(capacidad)})
                tiempos_ms.append((time.perf_counter() - inicio) * 1000)
                assert r.status_code == 200
                if ronda == 0:
                    sabe = [x or rng.random() < 0.4 for x in sabe]

        with sqlite3.connect(config.RUTA_BD) as conexion:
            planes = conexion.execute(
                "SELECT tiempo_disponible, tiempo_usado FROM planes").fetchall()
            evaluaciones = conexion.execute("SELECT count(*) FROM resultados").fetchone()[0]
            filas_bkt = conexion.execute("SELECT count(*) FROM progreso_bkt").fetchone()[0]

        docente = aplicacion.app.test_client()
        docente.post("/docente/registro", data={
            "nombre": "Docente", "usuario": "doc", "colegio": "colegio simulado",
            "clave": "1234",
        })
        inicio = time.perf_counter()
        panel = docente.get("/docente/panel")
        panel_ms = (time.perf_counter() - inicio) * 1000
        csv_texto = docente.get("/docente/exportar").data.decode("utf-8-sig")
        kpis, filas, subtemas = resumen_curso("Colegio Simulado")
    finally:
        aplicacion.generar_preguntas, aplicacion.generar_ejercicios_refuerzo = originales

    tiempos_ms.sort()
    return {
        "estudiantes": len(filas),
        "evaluaciones": evaluaciones,
        "planes": len(planes),
        "planes_que_exceden_el_tiempo": sum(usado > disponible for disponible, usado in planes),
        "filas_bkt": filas_bkt,
        "recomendacion_ms_mediana": tiempos_ms[len(tiempos_ms) // 2],
        "recomendacion_ms_max": tiempos_ms[-1],
        "panel_status": panel.status_code,
        "panel_ms": panel_ms,
        "csv_filas": len(csv_texto.strip().splitlines()) - 1,
        "kpis": kpis,
        "subtema_debil": subtemas[0],
    }


def main():
    r = integracion()
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    with open(RESULTADOS / "integracion.json", "w", encoding="utf-8") as archivo:
        json.dump(r, archivo, indent=1, ensure_ascii=False)
    print(f"Integración con {r['estudiantes']} estudiantes")
    print(f"  P-05: {r['planes_que_exceden_el_tiempo']} planes exceden el tiempo, "
          f"de {r['planes']}")
    print(f"  P-06: {r['filas_bkt']} registros de dominio guardados y retomados")
    print(f"  P-07: panel en {r['panel_ms']:.0f} ms (HTTP {r['panel_status']}), "
          f"CSV con {r['csv_filas']} filas")
    print(f"  Petición del plan: mediana {r['recomendacion_ms_mediana']:.1f} ms")


if __name__ == "__main__":
    main()
