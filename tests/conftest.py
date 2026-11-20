"""Configuración común de las pruebas.

Cada prueba usa una base de datos temporal y un generador de preguntas falso, así que
no se necesita LM Studio ni se toca ``data/tutoria.db``.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# Antes de importar la aplicación: datos y clave de sesión en una carpeta temporal.
os.environ["TUTORIA_DATA"] = tempfile.mkdtemp(prefix="tutoria-pruebas-")
os.environ.setdefault("TUTORIA_SECRET_KEY", "clave-de-pruebas")

import app as aplicacion  # noqa: E402
import config  # noqa: E402
from base_datos import crear_base_datos  # noqa: E402

SUBTEMAS_LIMITES = ["Limites directos", "Factorizacion", "Racionalizacion", "Limites laterales"]


def preguntas_falsas(materia, tema, nivel):
    """10 preguntas (3, 3, 2, 2) cuya respuesta correcta siempre es la opción 1."""
    preguntas = []
    for subtema, cantidad in zip(SUBTEMAS_LIMITES, [3, 3, 2, 2]):
        for i in range(cantidad):
            preguntas.append({
                "pregunta": f"Pregunta {i + 1} de {subtema}",
                "opciones": ["Correcta", "Distractor A", "Distractor B", "Distractor C"],
                "correcta": 1,
                "subtema": subtema,
            })
    return preguntas


def ejercicios_falsos(materia, tema, nivel, subtemas):
    tiempos = {"Limites directos": 10, "Factorizacion": 15, "Racionalizacion": 20,
               "Limites laterales": 15}
    return [
        {"nombre": f"Ejercicio de {s}", "ejercicio": "Resuelva el límite.", "subtema": s,
         "tiempo": tiempos.get(s, 10)}
        for s in subtemas
    ]


@pytest.fixture(autouse=True)
def base_temporal(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "RUTA_BD", tmp_path / "tutoria.db")
    crear_base_datos()
    yield tmp_path / "tutoria.db"


@pytest.fixture
def ia_falsa(monkeypatch):
    monkeypatch.setattr(aplicacion, "generar_preguntas", preguntas_falsas)
    monkeypatch.setattr(aplicacion, "generar_ejercicios_refuerzo", ejercicios_falsos)


@pytest.fixture
def cliente(ia_falsa):
    aplicacion.app.config["TESTING"] = True
    return aplicacion.app.test_client()


DATOS_ESTUDIANTE = {
    "nombre": "Ana Gómez",
    "colegio": "Colegio Rural El Progreso",
    "curso": "1101",
    "numero_lista": "7",
    "edad": "16",
    "nivel": "Basico",
    "materia": "Calculo Diferencial",
    "tema": "Limites",
}


def responder(cliente, aciertos_por_pregunta):
    """Envía la evaluación: True responde la opción correcta (1) y False la opción 2."""
    respuestas = {
        f"pregunta_{i}": "1" if acierta else "2" for i, acierta in enumerate(aciertos_por_pregunta)
    }
    return cliente.post("/resultado", data=respuestas)
