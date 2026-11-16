# ==========================================
# CALCULO DEL BENEFICIO
# ==========================================


def calcular_beneficio(
    probabilidad_dominio
):

    beneficio = (
        1 - probabilidad_dominio
    ) * 10

    return beneficio


# ==========================================
# PRUEBA
# ==========================================

if __name__ == "__main__":

    dominio = 0.20

    beneficio = calcular_beneficio(
        dominio
    )

    print("Dominio:", dominio)

    print("Beneficio:", beneficio)