from openai import OpenAI
import json
import unicodedata


# ==========================================
# CONEXION CON LM STUDIO
# ==========================================

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)


MODELO = "qwen2.5-vl-3b-instruct"


# ==========================================
# NORMALIZAR TEXTO
# ==========================================

def normalizar_texto(texto):

    texto = texto.strip().lower()

    texto = unicodedata.normalize(
        "NFD",
        texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )

    return texto


# ==========================================
# SUBTEMAS FIJOS
# ==========================================

SUBTEMAS_FIJOS = {

    "calculo diferencial": {

        "limites": [
            "Limites directos",
            "Factorizacion",
            "Racionalizacion",
            "Limites laterales"
        ],

        "derivadas": [
            "Regla de la potencia",
            "Derivadas exponenciales",
            "Derivadas trigonometricas",
            "Regla de la cadena"
        ]
    },


    "ingles": {

        "verb to be": [
            "Affirmative",
            "Negative",
            "Questions",
            "Short answers"
        ],

        "present simple": [
            "Affirmative",
            "Negative",
            "Questions",
            "Third person"
        ],

        "past simple": [
            "Regular verbs",
            "Irregular verbs",
            "Negative",
            "Questions"
        ]
    },


    "fisica": {

        "vectores": [
            "Componentes",
            "Magnitud",
            "Producto escalar",
            "Direccion"
        ],

        "movimiento": [
            "Posicion",
            "Velocidad",
            "Aceleracion",
            "Movimiento uniforme"
        ],

        "leyes de newton": [
            "Primera ley",
            "Segunda ley",
            "Tercera ley",
            "Fuerza neta"
        ]
    }
}


# ==========================================
# OBTENER SUBTEMAS
# ==========================================

def obtener_subtemas(
    materia,
    tema
):

    materia_normalizada = normalizar_texto(
        materia
    )

    tema_normalizado = normalizar_texto(
        tema
    )


    if materia_normalizada in SUBTEMAS_FIJOS:

        temas = SUBTEMAS_FIJOS[
            materia_normalizada
        ]


        if tema_normalizado in temas:

            return temas[
                tema_normalizado
            ]


    # ======================================
    # SI EL TEMA NO ESTA REGISTRADO
    # ======================================

    return [
        "Concepto principal",
        "Aplicacion",
        "Interpretacion",
        "Resolucion de problemas"
    ]


# ==========================================
# VALIDAR OPCIONES
# ==========================================

def opciones_validas(opciones):

    if len(opciones) != 4:

        return False


    for opcion in opciones:

        texto = str(
            opcion
        ).strip()


        if texto in [
            "1",
            "2",
            "3",
            "4"
        ]:

            return False


        if len(texto) < 2:

            return False


    return True


# ==========================================
# GENERAR PREGUNTAS
# ==========================================

def generar_preguntas(
    materia,
    tema,
    nivel
):

    subtemas = obtener_subtemas(
        materia,
        tema
    )


    subtema_1 = subtemas[0]
    subtema_2 = subtemas[1]
    subtema_3 = subtemas[2]
    subtema_4 = subtemas[3]


    print(
        "\n======================================"
    )

    print(
        "SUBTEMAS SELECCIONADOS"
    )

    print(
        "======================================"
    )


    for subtema in subtemas:

        print(
            "-",
            subtema
        )


    # ======================================
    # PROMPT
    # ======================================

    prompt = f"""
Crea una evaluacion educativa de seleccion multiple.

Materia:
{materia}

Tema:
{tema}

Nivel:
{nivel}


Debes crear preguntas para estos cuatro subtemas:


SUBTEMA 1:
{subtema_1}

Genera exactamente 3 preguntas.


SUBTEMA 2:
{subtema_2}

Genera exactamente 3 preguntas.


SUBTEMA 3:
{subtema_3}

Genera exactamente 2 preguntas.


SUBTEMA 4:
{subtema_4}

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


    # ======================================
    # ESQUEMA DE UNA PREGUNTA
    # ======================================

    esquema_pregunta = {

        "type": "object",

        "properties": {

            "pregunta": {

                "type": "string",

                "minLength": 5
            },

            "opciones": {

                "type": "array",

                "minItems": 4,

                "maxItems": 4,

                "items": {

                    "type": "string",

                    "minLength": 2
                }
            },

            "correcta": {

                "type": "integer",

                "minimum": 1,

                "maximum": 4
            }
        },

        "required": [
            "pregunta",
            "opciones",
            "correcta"
        ],

        "additionalProperties": False
    }


    # ======================================
    # ESQUEMA COMPLETO
    # ======================================

    esquema = {

        "type": "json_schema",

        "json_schema": {

            "name": "evaluacion",

            "schema": {

                "type": "object",

                "properties": {

                    "subtema_1": {

                        "type": "array",

                        "minItems": 3,

                        "maxItems": 3,

                        "items": esquema_pregunta
                    },

                    "subtema_2": {

                        "type": "array",

                        "minItems": 3,

                        "maxItems": 3,

                        "items": esquema_pregunta
                    },

                    "subtema_3": {

                        "type": "array",

                        "minItems": 2,

                        "maxItems": 2,

                        "items": esquema_pregunta
                    },

                    "subtema_4": {

                        "type": "array",

                        "minItems": 2,

                        "maxItems": 2,

                        "items": esquema_pregunta
                    }
                },

                "required": [
                    "subtema_1",
                    "subtema_2",
                    "subtema_3",
                    "subtema_4"
                ],

                "additionalProperties": False
            }
        }
    }


    # ======================================
    # PEDIR RESPUESTA A LM STUDIO
    # ======================================

    respuesta = client.chat.completions.create(

        model=MODELO,

        messages=[

            {
                "role": "system",

                "content": (
                    "Eres un tutor educativo experto "
                    "en crear evaluaciones de seleccion "
                    "multiple. Debes crear opciones "
                    "reales y educativas."
                )
            },

            {
                "role": "user",

                "content": prompt
            }
        ],

        temperature=0.2,

        max_tokens=3000,

        response_format=esquema
    )


    texto = (
        respuesta
        .choices[0]
        .message
        .content
    )


    datos = json.loads(
        texto
    )


    # ======================================
    # CONVERTIR TODO A UNA LISTA
    # ======================================

    preguntas = []


    # ======================================
    # SUBTEMA 1
    # ======================================

    for pregunta in datos[
        "subtema_1"
    ]:

        pregunta[
            "subtema"
        ] = subtema_1

        preguntas.append(
            pregunta
        )


    # ======================================
    # SUBTEMA 2
    # ======================================

    for pregunta in datos[
        "subtema_2"
    ]:

        pregunta[
            "subtema"
        ] = subtema_2

        preguntas.append(
            pregunta
        )


    # ======================================
    # SUBTEMA 3
    # ======================================

    for pregunta in datos[
        "subtema_3"
    ]:

        pregunta[
            "subtema"
        ] = subtema_3

        preguntas.append(
            pregunta
        )


    # ======================================
    # SUBTEMA 4
    # ======================================

    for pregunta in datos[
        "subtema_4"
    ]:

        pregunta[
            "subtema"
        ] = subtema_4

        preguntas.append(
            pregunta
        )


    # ======================================
    # VALIDAR OPCIONES
    # ======================================

    for pregunta in preguntas:

        if not opciones_validas(
            pregunta[
                "opciones"
            ]
        ):

            raise RuntimeError(
                "LM Studio genero opciones "
                "de respuesta invalidas."
            )


    # ======================================
    # MOSTRAR DISTRIBUCION
    # ======================================

    print(
        "\n======================================"
    )

    print(
        "DISTRIBUCION DE SUBTEMAS"
    )

    print(
        "======================================"
    )


    print(
        "-",
        subtema_1,
        ": 3 preguntas"
    )

    print(
        "-",
        subtema_2,
        ": 3 preguntas"
    )

    print(
        "-",
        subtema_3,
        ": 2 preguntas"
    )

    print(
        "-",
        subtema_4,
        ": 2 preguntas"
    )


    print(
        "\nEvaluacion generada correctamente."
    )


    return preguntas


# ==========================================
# GENERAR EJERCICIOS DE REFUERZO
# ==========================================

def generar_ejercicios_refuerzo(
    materia,
    tema,
    nivel,
    subtemas
):

    cantidad = len(
        subtemas
    )


    prompt = f"""
Genera exactamente {cantidad}
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


    esquema = {

        "type": "json_schema",

        "json_schema": {

            "name": "ejercicios_refuerzo",

            "schema": {

                "type": "object",

                "properties": {

                    "ejercicios": {

                        "type": "array",

                        "minItems": cantidad,

                        "maxItems": cantidad,

                        "items": {

                            "type": "object",

                            "properties": {

                                "nombre": {

                                    "type": "string"
                                },

                                "ejercicio": {

                                    "type": "string"
                                },

                                "subtema": {

                                    "type": "string",

                                    "enum": subtemas
                                },

                                "tiempo": {

                                    "type": "integer",

                                    "enum": [
                                        10,
                                        15,
                                        20
                                    ]
                                }
                            },

                            "required": [
                                "nombre",
                                "ejercicio",
                                "subtema",
                                "tiempo"
                            ],

                            "additionalProperties": False
                        }
                    }
                },

                "required": [
                    "ejercicios"
                ],

                "additionalProperties": False
            }
        }
    }


    respuesta = client.chat.completions.create(

        model=MODELO,

        messages=[

            {
                "role": "system",

                "content": (
                    "Eres un tutor educativo "
                    "que genera ejercicios "
                    "de refuerzo personalizados."
                )
            },

            {
                "role": "user",

                "content": prompt
            }
        ],

        temperature=0.2,

        max_tokens=1200,

        response_format=esquema
    )


    texto = (
        respuesta
        .choices[0]
        .message
        .content
    )


    datos = json.loads(
        texto
    )


    return datos[
        "ejercicios"
    ]


# ==========================================
# PRUEBA DIRECTA
# ==========================================

if __name__ == "__main__":

    preguntas = generar_preguntas(
        "Ingles",
        "verb to be",
        "Basico"
    )


    print(
        "\n======================================"
    )

    print(
        "PREGUNTAS GENERADAS"
    )

    print(
        "======================================"
    )


    for numero, pregunta in enumerate(
        preguntas,
        start=1
    ):

        print(
            "\nPregunta",
            numero
        )


        print(
            pregunta[
                "pregunta"
            ]
        )


        for numero_opcion, opcion in enumerate(
            pregunta[
                "opciones"
            ],
            start=1
        ):

            print(
                str(numero_opcion) + ".",
                opcion
            )


        print(
            "Correcta:",
            pregunta[
                "correcta"
            ]
        )


        print(
            "Subtema:",
            pregunta[
                "subtema"
            ]
        )