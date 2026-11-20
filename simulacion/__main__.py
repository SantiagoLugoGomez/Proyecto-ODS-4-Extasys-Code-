"""Reproduce todas las cifras y figuras de la evaluación del paper.

Uso: ``python -m simulacion`` desde la raíz del repositorio. Tarda unos segundos.
"""

import time

from simulacion import RESULTADOS, experimento, graficas, integracion, robustez


def main():
    inicio = time.perf_counter()
    for etapa in (experimento, robustez, integracion, graficas):
        print(f"\n== {etapa.__name__.split('.')[-1]} ==")
        etapa.main()
    print(f"\nListo en {time.perf_counter() - inicio:.0f} s. Resultados en {RESULTADOS}")


if __name__ == "__main__":
    main()
