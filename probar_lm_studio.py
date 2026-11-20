"""Diagnóstico de LM Studio y medición de la prueba P-04 del paper.

Uso:
    python probar_lm_studio.py                    # revisa la conexión y genera 1 evaluación
    python probar_lm_studio.py --evaluaciones 20  # mide tiempo de generación y % válidas

Con ``--evaluaciones N`` se piden N evaluaciones y se guardan los KPIs técnicos
"Tiempo de generación" y "Preguntas válidas" (Tabla 7) en
``simulacion/resultados/lm_studio.json``.
"""

import argparse
import json
import platform
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import config
import ia

TEMAS_DE_PRUEBA = [
    ("Ingles", "Verb to be", "Basico"),
    ("Calculo Diferencial", "Limites", "Intermedio"),
    ("Fisica", "Leyes de Newton", "Basico"),
    ("Calculo Diferencial", "Derivadas", "Avanzado"),
    ("Ingles", "Past simple", "Intermedio"),
    ("Fisica", "Vectores", "Intermedio"),
]


def revisar_conexion():
    print(f"Servidor: {config.LM_STUDIO_URL}")
    print(f"Modelo configurado: {config.MODELO}")
    try:
        modelos = [m.id for m in ia.client.models.list().data]
    except Exception as error:  # se informa cualquier fallo de conexión
        print(f"\n[X] No se pudo conectar con LM Studio: {error}")
        print("    Abra LM Studio, cargue el modelo y encienda el servidor local (puerto 1234).")
        return False

    print("Modelos disponibles:", ", ".join(modelos) or "(ninguno)")
    if config.MODELO.lower() not in (m.lower() for m in modelos):
        print(f"\n[!] El modelo {config.MODELO} no aparece cargado. Cárguelo en LM Studio o "
              "cambie TUTORIA_MODELO.")
        return False
    print("[OK] Conexión correcta.")
    return True


def medir(cantidad):
    tiempos, validas, errores = [], 0, []
    for i in range(cantidad):
        materia, tema, nivel = TEMAS_DE_PRUEBA[i % len(TEMAS_DE_PRUEBA)]
        inicio = time.perf_counter()
        try:
            ia.generar_preguntas(materia, tema, nivel)
        except ia.ErrorIA as error:
            errores.append(f"{materia} / {tema}: {error}")
            estado = "inválida"
        else:
            validas += 1
            estado = "válida"
        segundos = time.perf_counter() - inicio
        tiempos.append(segundos)
        print(f"{i + 1:>3}/{cantidad}  {materia} / {tema} / {nivel}: {segundos:6.1f} s  {estado}")

    resultado = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "modelo": config.MODELO,
        "equipo": f"{platform.processor() or platform.machine()} · {platform.system()}",
        "python": platform.python_version(),
        "evaluaciones_solicitadas": cantidad,
        "evaluaciones_validas": validas,
        "porcentaje_validas": validas / cantidad * 100,
        "tiempo_mediano_s": statistics.median(tiempos),
        "tiempo_promedio_s": statistics.mean(tiempos),
        "tiempo_maximo_s": max(tiempos),
        "intentos_por_evaluacion": config.INTENTOS_IA,
        "errores": errores,
    }
    destino = Path(__file__).parent / "simulacion" / "resultados" / "lm_studio.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"\nPreguntas válidas: {validas} de {cantidad} ({resultado['porcentaje_validas']:.0f} %,"
          " meta ≥ 95 %)")
    print(f"Tiempo de generación: mediana {resultado['tiempo_mediano_s']:.1f} s, "
          f"máximo {resultado['tiempo_maximo_s']:.1f} s")
    print(f"Resultados guardados en {destino}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--evaluaciones", type=int, default=0,
                        help="cantidad de evaluaciones para medir P-04")
    args = parser.parse_args()

    if not revisar_conexion():
        sys.exit(1)

    if args.evaluaciones > 0:
        medir(args.evaluaciones)
        return

    print("\nGenerando una evaluación de prueba...")
    inicio = time.perf_counter()
    preguntas = ia.generar_preguntas("Ingles", "Verb to be", "Basico")
    print(f"[OK] {len(preguntas)} preguntas válidas en {time.perf_counter() - inicio:.1f} s")
    p = preguntas[0]
    print(f"\nEjemplo: {p['pregunta']}")
    for letra, opcion in zip("ABCD", p["opciones"]):
        print(f"  {letra}. {opcion}")


if __name__ == "__main__":
    main()
