"""Generación y validación de contenido con LM Studio (con un cliente falso)."""

import json
from types import SimpleNamespace

import openai
import pytest

import ia


class ClienteFalso:
    """Imita ``client.chat.completions.create`` devolviendo respuestas preparadas."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.llamadas.append(kwargs)
        respuesta = self.respuestas.pop(0)
        if isinstance(respuesta, Exception):
            raise respuesta
        contenido = respuesta if isinstance(respuesta, str) else json.dumps(respuesta)
        mensaje = SimpleNamespace(content=contenido)
        return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)])


def pregunta(texto="¿Cuál es la forma correcta?", correcta=1, opciones=None):
    return {
        "pregunta": texto,
        "opciones": opciones or ["I am a student", "I is a student", "I are a student",
                                 "I be a student"],
        "correcta": correcta,
    }


def evaluacion_valida():
    return {f"subtema_{i}": [pregunta(f"Pregunta {i}.{j}") for j in range(c)]
            for i, c in zip(range(1, 5), [3, 3, 2, 2])}


@pytest.fixture
def cliente_falso(monkeypatch):
    def instalar(*respuestas):
        falso = ClienteFalso(*respuestas)
        monkeypatch.setattr(ia, "client", falso)
        return falso
    return instalar


def test_normalizar_y_subtemas():
    assert ia.normalizar_texto("  Cálculo Diferencial ") == "calculo diferencial"
    assert ia.obtener_subtemas("Física", "Leyes de Newton")[0] == "Primera ley"
    assert ia.obtener_subtemas("Historia", "Independencia") == ia.SUBTEMAS_GENERICOS


@pytest.mark.parametrize(("opciones", "valida"), [
    (["París", "Lima", "Quito", "Bogotá"], True),
    (["1", "2", "3", "4"], False),
    (["París", "Lima", "Quito"], False),
    (["París", "Lima", "Quito", "x"], False),
    (["París", "Lima", "Quito", "paris "], False),
])
def test_opciones_validas(opciones, valida):
    assert ia.opciones_validas(opciones) is valida


def test_generar_preguntas_reparte_10_preguntas(cliente_falso):
    falso = cliente_falso(evaluacion_valida())
    preguntas = ia.generar_preguntas("Ingles", "Verb to be", "Basico")

    assert len(preguntas) == 10
    conteo = [sum(p["subtema"] == s for p in preguntas)
              for s in ia.obtener_subtemas("Ingles", "Verb to be")]
    assert conteo == [3, 3, 2, 2]
    assert falso.llamadas[0]["response_format"]["type"] == "json_schema"
    assert falso.llamadas[0]["model"] == ia.MODELO


def test_salida_invalida_se_reintenta(cliente_falso, monkeypatch):
    monkeypatch.setattr(ia.config, "INTENTOS_IA", 2)
    invalida = evaluacion_valida()
    invalida["subtema_1"][0] = pregunta(opciones=["1", "2", "3", "4"])
    falso = cliente_falso(invalida, evaluacion_valida())

    assert len(ia.generar_preguntas("Ingles", "Verb to be", "Basico")) == 10
    assert len(falso.llamadas) == 2


def test_salida_invalida_siempre_lanza_error_ia(cliente_falso, monkeypatch):
    monkeypatch.setattr(ia.config, "INTENTOS_IA", 2)
    sin_correcta = evaluacion_valida()
    sin_correcta["subtema_4"][1]["correcta"] = 7
    cliente_falso("esto no es JSON", sin_correcta)

    with pytest.raises(ia.ErrorIA, match="inválidas 2 veces"):
        ia.generar_preguntas("Ingles", "Verb to be", "Basico")


def test_lm_studio_apagado_da_un_mensaje_claro(cliente_falso):
    cliente_falso(openai.APIConnectionError(request=None))

    with pytest.raises(ia.ErrorIA, match="No se pudo conectar con LM Studio"):
        ia.generar_preguntas("Ingles", "Verb to be", "Basico")


def test_ejercicios_uno_por_subtema(cliente_falso, monkeypatch):
    monkeypatch.setattr(ia.config, "INTENTOS_IA", 2)
    subtemas = ["Affirmative", "Negative"]
    repetido = {"ejercicios": [
        {"nombre": "A", "ejercicio": "x", "subtema": "Affirmative", "tiempo": 10},
        {"nombre": "B", "ejercicio": "y", "subtema": "Affirmative", "tiempo": 15},
    ]}
    correcto = {"ejercicios": [
        {"nombre": "A", "ejercicio": "x", "subtema": "Affirmative", "tiempo": 10},
        {"nombre": "B", "ejercicio": "y", "subtema": "Negative", "tiempo": 20},
    ]}
    falso = cliente_falso(repetido, correcto)

    ejercicios = ia.generar_ejercicios_refuerzo("Ingles", "Verb to be", "Basico", subtemas)

    assert sorted(e["subtema"] for e in ejercicios) == subtemas
    assert len(falso.llamadas) == 2
