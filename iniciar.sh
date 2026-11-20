#!/usr/bin/env bash
# Inicia TutorIA en macOS o Linux. La primera vez crea un entorno virtual e instala
# las dependencias (requiere Internet solo esa vez).
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "No se encontró Python 3. Instale Python 3.10 o superior." >&2
    exit 1
fi

if [ ! -f .venv/instalado ]; then
    echo "Preparando TutorIA por primera vez..."
    "$PYTHON" -m venv .venv
    .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
    touch .venv/instalado
fi

echo "Recuerde tener LM Studio abierto con el servidor local encendido (puerto 1234)."
echo "Para cerrar TutorIA presione Ctrl+C."
export TUTORIA_ABRIR_NAVEGADOR="${TUTORIA_ABRIR_NAVEGADOR:-1}"
exec .venv/bin/python app.py
