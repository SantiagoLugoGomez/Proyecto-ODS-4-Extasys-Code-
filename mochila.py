# ==========================================
# MOCHILA 0/1 CON MEMORIZACION
# ==========================================


def recomendar_ejercicios(
    ejercicios,
    tiempo_disponible
):

    # Guarda resultados ya calculados
    memo = {}


    # ======================================
    # FUNCION RECURSIVA
    # ======================================

    def mochila(indice, tiempo_restante):

        # Caso base
        if indice == len(ejercicios):

            return 0, []


        # Clave para memoria
        clave = (
            indice,
            tiempo_restante
        )


        # Si ya se calculo, se reutiliza
        if clave in memo:

            return memo[clave]


        ejercicio = ejercicios[indice]

        tiempo_ejercicio = ejercicio["tiempo"]

        beneficio_ejercicio = ejercicio["beneficio"]


        # ==================================
        # OPCION 1:
        # NO TOMAR EL EJERCICIO
        # ==================================

        beneficio_sin, seleccion_sin = mochila(
            indice + 1,
            tiempo_restante
        )


        mejor_beneficio = beneficio_sin

        mejor_seleccion = seleccion_sin


        # ==================================
        # OPCION 2:
        # TOMAR EL EJERCICIO
        # ==================================

        if tiempo_ejercicio <= tiempo_restante:

            (
                beneficio_restante,
                seleccion_restante
            ) = mochila(
                indice + 1,
                tiempo_restante - tiempo_ejercicio
            )


            beneficio_con = (
                beneficio_ejercicio
                +
                beneficio_restante
            )


            # Si tomarlo da mayor beneficio
            if beneficio_con > mejor_beneficio:

                mejor_beneficio = beneficio_con

                mejor_seleccion = (
                    [ejercicio]
                    +
                    seleccion_restante
                )


        # ==================================
        # GUARDAR RESULTADO EN MEMORIA
        # ==================================

        memo[clave] = (
            mejor_beneficio,
            mejor_seleccion
        )


        return memo[clave]


    # ======================================
    # EJECUTAR MOCHILA
    # ======================================

    beneficio_total, seleccionados = mochila(
        0,
        tiempo_disponible
    )


    # ======================================
    # CALCULAR TIEMPO UTILIZADO
    # ======================================

    tiempo_total = 0

    for ejercicio in seleccionados:

        tiempo_total += ejercicio["tiempo"]


    return (
        seleccionados,
        tiempo_total,
        beneficio_total
    )


# ==========================================
# PRUEBA
# ==========================================

if __name__ == "__main__":

    ejercicios_prueba = [

        {
            "nombre": "Practica de derivada cuadratica",
            "tiempo": 10,
            "beneficio": 2
        },

        {
            "nombre": "Practica de derivada exponencial",
            "tiempo": 15,
            "beneficio": 8
        },

        {
            "nombre": "Practica de derivada trigonometrica",
            "tiempo": 20,
            "beneficio": 8
        }

    ]


    tiempo_disponible = 30


    (
        seleccionados,
        tiempo_total,
        beneficio_total
    ) = recomendar_ejercicios(
        ejercicios_prueba,
        tiempo_disponible
    )


    print("======================================")
    print("       PRUEBA MOCHILA 0/1")
    print("======================================")

    print(
        "\nTiempo disponible:",
        tiempo_disponible,
        "minutos"
    )


    print("\nEjercicios recomendados:")


    for ejercicio in seleccionados:

        print(
            "-",
            ejercicio["nombre"],
            "| Tiempo:",
            ejercicio["tiempo"],
            "| Beneficio:",
            ejercicio["beneficio"]
        )


    print(
        "\nTiempo utilizado:",
        tiempo_total,
        "minutos"
    )


    print(
        "Beneficio total:",
        beneficio_total
    )

    print("======================================")