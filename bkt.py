"""Bayesian Knowledge Tracing (BKT).

Modelo oculto de Markov de dos estados (domina / no domina) para cada subtema
(Corbett y Anderson, 1994). Después de cada respuesta se aplica la regla de Bayes
y luego la transición de aprendizaje (ecuaciones 1 a 3 del paper).
"""

# Probabilidad inicial de que el estudiante domine un subtema nuevo (P0).
PROBABILIDAD_INICIAL = 0.5

# Probabilidad de equivocarse aun sabiendo (descuido, s).
SLIP = 0.1

# Probabilidad de acertar sin saber (adivinanza, g).
GUESS = 0.2

# Probabilidad de pasar a dominar después de una oportunidad de práctica (l).
APRENDIZAJE = 0.1


def actualizar_bkt(probabilidad_dominio: float, respuesta_correcta: bool) -> float:
    """Actualiza el dominio de un subtema con una respuesta. Costo O(1).

    Si acierta:  P* = P(1 - s) / (P(1 - s) + (1 - P) g)
    Si falla:    P* = P s / (P s + (1 - P)(1 - g))
    Aprendizaje: P+ = P* + (1 - P*) l
    """
    p = probabilidad_dominio

    if respuesta_correcta:
        numerador = p * (1 - SLIP)
        denominador = numerador + (1 - p) * GUESS
    else:
        numerador = p * SLIP
        denominador = numerador + (1 - p) * (1 - GUESS)

    posterior = numerador / denominador
    return posterior + (1 - posterior) * APRENDIZAJE


if __name__ == "__main__":
    # Secuencia de la sección VI-A del paper: acierta, acierta, falla, acierta, acierta.
    dominio = PROBABILIDAD_INICIAL
    print(f"Dominio inicial: {dominio:.4f}")
    for correcta in [True, True, False, True, True]:
        dominio = actualizar_bkt(dominio, correcta)
        print(f"{'Acierta' if correcta else 'Falla  '} -> {dominio:.4f}")
