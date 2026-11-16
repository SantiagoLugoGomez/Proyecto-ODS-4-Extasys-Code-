# ==========================================
# BKT - BAYESIAN KNOWLEDGE TRACING
# ==========================================

# Probabilidad inicial de que el estudiante
# domine un subtema
PROBABILIDAD_INICIAL = 0.5

# Probabilidad de equivocarse aun sabiendo
SLIP = 0.1

# Probabilidad de acertar por casualidad
GUESS = 0.2

# Probabilidad de aprendizaje despues
# de cada intento
APRENDIZAJE = 0.1


def actualizar_bkt(
    probabilidad_dominio,
    respuesta_correcta
):

    # ======================================
    # SI LA RESPUESTA FUE CORRECTA
    # ======================================

    if respuesta_correcta:

        numerador = (
            probabilidad_dominio
            * (1 - SLIP)
        )

        denominador = (
            probabilidad_dominio
            * (1 - SLIP)
            +
            (1 - probabilidad_dominio)
            * GUESS
        )


    # ======================================
    # SI LA RESPUESTA FUE INCORRECTA
    # ======================================

    else:

        numerador = (
            probabilidad_dominio
            * SLIP
        )

        denominador = (
            probabilidad_dominio
            * SLIP
            +
            (1 - probabilidad_dominio)
            * (1 - GUESS)
        )


    # ======================================
    # PROBABILIDAD POSTERIOR
    # ======================================

    probabilidad_posterior = (
        numerador / denominador
    )


    # ======================================
    # APLICAR PROBABILIDAD DE APRENDIZAJE
    # ======================================

    nueva_probabilidad = (
        probabilidad_posterior
        +
        (
            1 - probabilidad_posterior
        )
        * APRENDIZAJE
    )


    return nueva_probabilidad


# ==========================================
# PRUEBA DEL BKT
# ==========================================

if __name__ == "__main__":

    dominio = PROBABILIDAD_INICIAL

    print("======================================")
    print("           PRUEBA DEL BKT")
    print("======================================")

    print(
        "\nDominio inicial:",
        round(dominio * 100, 2),
        "%"
    )


    dominio = actualizar_bkt(
        dominio,
        True
    )

    print(
        "Despues de una respuesta correcta:",
        round(dominio * 100, 2),
        "%"
    )


    dominio = actualizar_bkt(
        dominio,
        True
    )

    print(
        "Despues de otra respuesta correcta:",
        round(dominio * 100, 2),
        "%"
    )


    dominio = actualizar_bkt(
        dominio,
        False
    )

    print(
        "Despues de una respuesta incorrecta:",
        round(dominio * 100, 2),
        "%"
    )

    print("======================================")