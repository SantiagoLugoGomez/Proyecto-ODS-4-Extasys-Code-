"""Evaluación de TutorIA con estudiantes generados por computador (secciones IX y X del paper).

Ejecute ``python -m simulacion`` desde la raíz del repositorio para reproducir todas las
cifras y figuras; los resultados quedan en ``simulacion/resultados``.
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RESULTADOS = Path(__file__).resolve().parent / "resultados"

# Los módulos de la aplicación (bkt, mochila, app...) viven en la raíz del repositorio.
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
