"""Conexión con el modelo de lenguaje local (LM Studio).

Es el único módulo que habla con LM Studio. El servidor recibe un esquema JSON y
restringe la generación a ese formato; aquí además se validan las preguntas y los
ejercicios antes de mostrarlos. Si la salida no es válida se reintenta; si LM Studio
no responde se lanza ``ErrorIA`` con un mensaje que la aplicación muestra tal cual.
"""

import json
import logging
import unicodedata

import openai
from openai import OpenAI

import config

logger = logging.getLogger(__name__)

client = OpenAI(
    base_url=config.LM_STUDIO_URL,
    api_key="lm-studio",  # LM Studio no valida la clave, pero el cliente exige una.
    timeout=config.TIEMPO_ESPERA_IA,
)

MODELO = config.MODELO

# Preguntas por subtema: 3 + 3 + 2 + 2 = 10.
PREGUNTAS_POR_SUBTEMA = [3, 3, 2, 2]

TIEMPOS_EJERCICIO = [10, 15, 20]


class ErrorIA(Exception):
    """LM Studio no respondió o no generó contenido válido. El mensaje es para el usuario."""


class SalidaInvalida(ValueError):
    """La respuesta del modelo no cumple las reglas; se puede reintentar."""


# ==========================================
# SUBTEMAS
# ==========================================


def normalizar_texto(texto):
    """Minúsculas, sin espacios en los extremos ni tildes: 'Cálculo ' -> 'calculo'."""
    texto = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


SUBTEMAS_FIJOS = {
    "calculo diferencial": {
        "limites": ["Limites directos", "Factorizacion", "Racionalizacion", "Limites laterales"],
        "derivadas": [
            "Regla de la potencia",
            "Derivadas exponenciales",
            "Derivadas trigonometricas",
            "Regla de la cadena",
        ],
    },
    "ingles": {
        "verb to be": ["Affirmative", "Negative", "Questions", "Short answers"],
        "present simple": ["Affirmative", "Negative", "Questions", "Third person"],
        "past simple": ["Regular verbs", "Irregular verbs", "Negative", "Questions"],
    },
    "fisica": {
        "vectores": ["Componentes", "Magnitud", "Producto escalar", "Direccion"],
        "movimiento": ["Posicion", "Velocidad", "Aceleracion", "Movimiento uniforme"],
        "leyes de newton": ["Primera ley", "Segunda ley", "Tercera ley", "Fuerza neta"],
    },
}

SUBTEMAS_GENERICOS = [
    "Concepto principal",
    "Aplicacion",
    "Interpretacion",
    "Resolucion de problemas",
]


def obtener_subtemas(materia, tema):
    """Los cuatro subtemas fijos del tema, o cuatro genéricos si el tema no está registrado."""
    temas = SUBTEMAS_FIJOS.get(normalizar_texto(materia), {})
    return temas.get(normalizar_texto(tema), SUBTEMAS_GENERICOS)


# ==========================================
# VALIDACIÓN
# ==========================================


def opciones_validas(opciones):
    """Exactamente 4 opciones reales y distintas: ni números sueltos ni textos vacíos."""
    if len(opciones) != 4:
        return False

    textos = [str(opcion).strip() for opcion in opciones]
    if any(texto in {"1", "2", "3", "4"} or len(texto) < 2 for texto in textos):
        return False

    return len({normalizar_texto(texto) for texto in textos}) == 4


def validar_pregunta(pregunta):
    if not str(pregunta.get("pregunta", "")).strip():
        raise SalidaInvalida("Pregunta sin enunciado.")
    if not opciones_validas(pregunta.get("opciones", [])):
        raise SalidaInvalida("LM Studio generó opciones de respuesta inválidas.")
    correcta = pregunta.get("correcta")
    if not isinstance(correcta, int) or isinstance(correcta, bool) or not 1 <= correcta <= 4:
        raise SalidaInvalida("La respuesta correcta debe ser un entero entre 1 y 4.")


# ==========================================
# LLAMADA AL MODELO
# ==========================================


def _pedir_json(sistema, prompt, esquema, max_tokens):
    """Pide a LM Studio una respuesta con el esquema dado y la devuelve como diccionario."""
    try:
        respuesta = client.chat.completions.create(
            model=MODELO,
            messages=[
                {"role": "system", "content": sistema},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=max_tokens,
            response_format=esquema,
        )
    except openai.APITimeoutError as error:
        raise ErrorIA(
            "LM Studio tardó demasiado en responder. Revise que el modelo esté cargado "
            "y vuelva a intentarlo."
        ) from error
    except openai.APIConnectionError as error:
        raise ErrorIA(
            f"No se pudo conectar con LM Studio en {config.LM_STUDIO_URL}. Abra LM Studio, "
            f"cargue el modelo {MODELO} y encienda el servidor local."
        ) from error
    except openai.APIStatusError as error:
        raise ErrorIA(
            f"LM Studio respondió con un error ({error.status_code}). Revise que el modelo "
            f"{MODELO} esté cargado."
        ) from error

    texto = respuesta.choices[0].message.content or ""
    try:
        return json.loads(texto)
    except json.JSONDecodeError as error:
        raise SalidaInvalida("LM Studio no devolvió un JSON válido.") from error


def _con_reintentos(generar, descripcion):
    """Ejecuta ``generar`` hasta ``config.INTENTOS_IA`` veces si la salida es inválida."""
    intentos = max(1, config.INTENTOS_IA)
    for intento in range(1, intentos + 1):
        try:
            return generar()
        except SalidaInvalida as error:
            logger.warning("%s inválidas (intento %d de %d): %s", descripcion, intento,
                           intentos, error)
    raise ErrorIA(
        f"La IA generó {descripcion} inválidas {intentos} veces seguidas. "
        "Vuelva a intentarlo; si persiste, pruebe con otro tema o nivel."
    )


# ==========================================
# GENERAR PREGUNTAS
# ==========================================


def construir_prompt_preguntas(materia, tema, nivel, subtemas):
    return f"""
Crea una evaluacion educativa de seleccion multiple.

Materia:
{materia}

Tema:
{tema}

Nivel:
{nivel}


Debes crear preguntas para estos cuatro subtemas:


SUBTEMA 1:
{subtemas[0]}

Genera exactamente 3 preguntas.


SUBTEMA 2:
{subtemas[1]}

Genera exactamente 3 preguntas.


SUBTEMA 3:
{subtemas[2]}

Genera exactamente 2 preguntas.


SUBTEMA 4:
{subtemas[3]}

Genera exactamente 2 preguntas.


REGLAS PARA CADA PREGUNTA:

- Debe tener una pregunta clara.
- Debe tener exactamente 4 opciones.
- Las cuatro opciones deben ser respuestas reales.
- No uses numeros como opciones.
- No uses "1", "2", "3" o "4" como texto de respuesta.
- Debe existir solamente una respuesta correcta.
- El campo correcta debe ser un entero del 1 al 4.
- Las preguntas deben ser diferentes.
- Deben corresponder al nivel indicado.
- No uses Markdown.
- No agregues explicaciones fuera de la estructura solicitada.


EJEMPLO DE OPCIONES CORRECTAS:

[
    "I am a student",
    "I is a student",
    "I are a student",
    "I be a student"
]


EJEMPLO INCORRECTO:

[
    "1",
    "2",
    "3",
    "4"
]
"""


ESQUEMA_PREGUNTA = {
    "type": "object",
    "properties": {
        "pregunta": {"type": "string", "minLength": 5},
        "opciones": {
            "type": "array",
            "minItems": 4,
            "maxItems": 4,
            "items": {"type": "string", "minLength": 2},
        },
        "correcta": {"type": "integer", "minimum": 1, "maximum": 4},
    },
    "required": ["pregunta", "opciones", "correcta"],
    "additionalProperties": False,
}


def esquema_evaluacion():
    propiedades = {
        f"subtema_{i}": {
            "type": "array",
            "minItems": cantidad,
            "maxItems": cantidad,
            "items": ESQUEMA_PREGUNTA,
        }
        for i, cantidad in enumerate(PREGUNTAS_POR_SUBTEMA, start=1)
    }
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "evaluacion",
            "schema": {
                "type": "object",
                "properties": propiedades,
                "required": list(propiedades),
                "additionalProperties": False,
            },
        },
    }


def generar_preguntas(materia, tema, nivel):
    """Genera y valida las 10 preguntas de la evaluación (RF-02).

    Devuelve una lista de diccionarios con ``pregunta``, ``opciones``, ``correcta``
    (1 a 4) y ``subtema``. Lanza ``ErrorIA`` si no se logra una evaluación válida.
    """
    subtemas = obtener_subtemas(materia, tema)
    prompt = construir_prompt_preguntas(materia, tema, nivel, subtemas)

    def intentar():
        datos = _pedir_json(
            "Eres un tutor educativo experto en crear evaluaciones de seleccion multiple. "
            "Debes crear opciones reales y educativas.",
            prompt,
            esquema_evaluacion(),
            max_tokens=3000,
        )
        preguntas = []
        for i, (subtema, cantidad) in enumerate(zip(subtemas, PREGUNTAS_POR_SUBTEMA), start=1):
            grupo = datos.get(f"subtema_{i}")
            if not isinstance(grupo, list) or len(grupo) != cantidad:
                raise SalidaInvalida(f"El subtema {i} no tiene {cantidad} preguntas.")
            for pregunta in grupo:
                validar_pregunta(pregunta)
                preguntas.append({
                    "pregunta": pregunta["pregunta"].strip(),
                    "opciones": [str(opcion).strip() for opcion in pregunta["opciones"]],
                    "correcta": pregunta["correcta"],
                    "subtema": subtema,
                })
        return preguntas

    logger.info("Generando evaluación: %s / %s / %s", materia, tema, nivel)
    preguntas = _con_reintentos(intentar, "preguntas")
    logger.info("Evaluación generada: %d preguntas en %s", len(preguntas), ", ".join(subtemas))
    return preguntas


# ==========================================
# GENERAR EJERCICIOS DE REFUERZO
# ==========================================


def construir_prompt_ejercicios(materia, tema, nivel, subtemas):
    return f"""
Genera exactamente {len(subtemas)}
ejercicios de practica.

Materia:
{materia}

Tema:
{tema}

Nivel:
{nivel}

Subtemas:
{subtemas}


Debes generar exactamente UN ejercicio
para cada subtema.


REGLAS:

- El ejercicio debe corresponder al nivel.
- Debe ser claro.
- Debe ser concreto.
- Debe parecer un ejercicio tipo parcial.
- No des la respuesta.
- El subtema debe coincidir exactamente.
- El tiempo debe ser 10, 15 o 20 minutos.
- No uses Markdown.
"""


def esquema_ejercicios(subtemas):
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "ejercicios_refuerzo",
            "schema": {
                "type": "object",
                "properties": {
                    "ejercicios": {
                        "type": "array",
                        "minItems": len(subtemas),
                        "maxItems": len(subtemas),
                        "items": {
                            "type": "object",
                            "properties": {
                                "nombre": {"type": "string"},
                                "ejercicio": {"type": "string"},
                                "subtema": {"type": "string", "enum": list(subtemas)},
                                "tiempo": {"type": "integer", "enum": TIEMPOS_EJERCICIO},
                            },
                            "required": ["nombre", "ejercicio", "subtema", "tiempo"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["ejercicios"],
                "additionalProperties": False,
            },
        },
    }


def generar_ejercicios_refuerzo(materia, tema, nivel, subtemas):
    """Genera un ejercicio de 10, 15 o 20 minutos por subtema (RF-04)."""
    subtemas = list(subtemas)
    prompt = construir_prompt_ejercicios(materia, tema, nivel, subtemas)

    def intentar():
        datos = _pedir_json(
            "Eres un tutor educativo que genera ejercicios de refuerzo personalizados.",
            prompt,
            esquema_ejercicios(subtemas),
            max_tokens=1200,
        )
        ejercicios = datos.get("ejercicios")
        if not isinstance(ejercicios, list):
            raise SalidaInvalida("La respuesta no trae la lista de ejercicios.")
        if sorted(e.get("subtema", "") for e in ejercicios) != sorted(subtemas):
            raise SalidaInvalida("No hay exactamente un ejercicio por subtema.")
        for e in ejercicios:
            if e.get("tiempo") not in TIEMPOS_EJERCICIO:
                raise SalidaInvalida("El tiempo de un ejercicio no es 10, 15 o 20 minutos.")
            if not str(e.get("nombre", "")).strip() or not str(e.get("ejercicio", "")).strip():
                raise SalidaInvalida("Un ejercicio no tiene nombre o enunciado.")
        return ejercicios

    logger.info("Generando ejercicios de refuerzo para %d subtemas", len(subtemas))
    return _con_reintentos(intentar, "ejercicios")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for numero, p in enumerate(generar_preguntas("Ingles", "verb to be", "Basico"), start=1):
        print(f"\n{numero}. [{p['subtema']}] {p['pregunta']}")
        for letra, opcion in zip("ABCD", p["opciones"]):
            print(f"   {letra}. {opcion}")
        print(f"   Correcta: {'ABCD'[p['correcta'] - 1]}")
