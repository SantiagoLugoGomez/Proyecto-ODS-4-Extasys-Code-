"""Mochila 0/1 con programación dinámica top-down y memoización.

Cada ejercicio candidato i tiene una duración t_i (minutos) y un beneficio b_i.
M(i, r) es el mayor beneficio que se obtiene con los candidatos desde i cuando
quedan r minutos (ecuación 5 del paper):

    M(i, r) = 0                                   si i = n
    M(i, r) = M(i + 1, r)                         si t_i > r
    M(i, r) = max(M(i + 1, r), b_i + M(i + 1, r - t_i))   en otro caso

Cada estado (i, r) se resuelve una sola vez y se guarda en un diccionario, así que
hay a lo sumo (n + 1)(T + 1) estados: tiempo y espacio O(n·T), frente a O(2^n) de
la fuerza bruta.
"""


def recomendar_ejercicios(ejercicios: list[dict], tiempo_disponible: int):
    """Elige los ejercicios de mayor beneficio total sin pasarse del tiempo disponible.

    Cada ejercicio es un diccionario con al menos las llaves ``tiempo`` y ``beneficio``.
    Devuelve ``(seleccionados, tiempo_total, beneficio_total)``. Los seleccionados
    conservan el orden en que llegaron. Ante un empate se prefiere no incluir el
    ejercicio, de modo que el resultado es determinista.
    """
    n = len(ejercicios)
    memo: dict[tuple[int, int], float] = {}

    def mochila(i: int, restante: int) -> float:
        if i == n:
            return 0

        clave = (i, restante)
        if clave in memo:
            return memo[clave]

        mejor = mochila(i + 1, restante)

        tiempo = ejercicios[i]["tiempo"]
        if tiempo <= restante:
            con_ejercicio = ejercicios[i]["beneficio"] + mochila(i + 1, restante - tiempo)
            if con_ejercicio > mejor:
                mejor = con_ejercicio

        memo[clave] = mejor
        return mejor

    beneficio_total = mochila(0, tiempo_disponible)

    # Reconstrucción: el ejercicio i entra si incluirlo da un valor mayor que omitirlo.
    seleccionados = []
    restante = tiempo_disponible
    for i, ejercicio in enumerate(ejercicios):
        tiempo = ejercicio["tiempo"]
        if tiempo <= restante and (
            ejercicio["beneficio"] + mochila(i + 1, restante - tiempo) > mochila(i + 1, restante)
        ):
            seleccionados.append(ejercicio)
            restante -= tiempo

    tiempo_total = sum(ejercicio["tiempo"] for ejercicio in seleccionados)
    return seleccionados, tiempo_total, beneficio_total


if __name__ == "__main__":
    from beneficio import calcular_beneficio
    from bkt import PROBABILIDAD_INICIAL, actualizar_bkt

    def dominio(respuestas):
        p = PROBABILIDAD_INICIAL
        for correcta in respuestas:
            p = actualizar_bkt(p, correcta)
        return p

    # Tabla 5 del paper: plan para 30 minutos en el tema Límites.
    candidatos = [
        {"nombre": "Límites directos", "tiempo": 10, "respuestas": [True, True, True]},
        {"nombre": "Factorización", "tiempo": 15, "respuestas": [True, False, False]},
        {"nombre": "Racionalización", "tiempo": 20, "respuestas": [False, False]},
        {"nombre": "Límites laterales", "tiempo": 15, "respuestas": [True, True]},
    ]
    for c in candidatos:
        c["dominio"] = dominio(c["respuestas"])
        c["beneficio"] = calcular_beneficio(c["dominio"])
        print(
            f"{c['nombre']:<18} P = {c['dominio']:.3f}  b = {c['beneficio']:.2f}"
            f"  t = {c['tiempo']} min"
        )

    elegidos, usado, total = recomendar_ejercicios(candidatos, 30)
    print(f"\nPlan óptimo (30 min): {', '.join(c['nombre'] for c in elegidos)}")
    print(f"Tiempo usado: {usado} min · beneficio total: {total:.2f}")
