"""Beneficio de reforzar un subtema (ecuación 4 del paper)."""


def calcular_beneficio(probabilidad_dominio: float) -> float:
    """b = 10 (1 - P): entre 0 y 10. Mientras menos domine el subtema, más vale reforzarlo."""
    return (1 - probabilidad_dominio) * 10


if __name__ == "__main__":
    for dominio in [0.9893, 0.5, 0.1273]:
        print(f"Dominio {dominio:.4f} -> beneficio {calcular_beneficio(dominio):.2f}")
