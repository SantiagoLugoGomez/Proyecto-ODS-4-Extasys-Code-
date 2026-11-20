"""Configuración de TutorIA.

Todos los valores tienen un valor por defecto pensado para el computador del colegio
y se pueden cambiar con variables de entorno, sin tocar el código.
"""

import os
import secrets
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# Datos locales: base de datos SQLite y clave de las sesiones.
RUTA_DATA = Path(os.environ.get("TUTORIA_DATA", RAIZ / "data"))
RUTA_BD = Path(os.environ.get("TUTORIA_BD", RUTA_DATA / "tutoria.db"))

# Servidor local de LM Studio (API compatible con OpenAI).
LM_STUDIO_URL = os.environ.get("TUTORIA_LM_URL", "http://localhost:1234/v1")
MODELO = os.environ.get("TUTORIA_MODELO", "qwen2.5-vl-3b-instruct")
TIEMPO_ESPERA_IA = float(os.environ.get("TUTORIA_TIEMPO_ESPERA_IA", "300"))  # segundos
INTENTOS_IA = int(os.environ.get("TUTORIA_INTENTOS_IA", "2"))

# Servidor web.
HOST = os.environ.get("TUTORIA_HOST", "127.0.0.1")
PUERTO = int(os.environ.get("TUTORIA_PUERTO", "5000"))
DEBUG = os.environ.get("TUTORIA_DEBUG", "0") == "1"
ABRIR_NAVEGADOR = os.environ.get("TUTORIA_ABRIR_NAVEGADOR", "0") == "1"


def clave_secreta() -> str:
    """Devuelve la clave que firma las sesiones.

    Se toma de ``TUTORIA_SECRET_KEY`` o se genera una sola vez y se guarda en
    ``data/clave_secreta.txt``, para que las sesiones sobrevivan a un reinicio
    sin dejar la clave escrita en el repositorio.
    """
    if valor := os.environ.get("TUTORIA_SECRET_KEY"):
        return valor

    archivo = RUTA_DATA / "clave_secreta.txt"
    if archivo.exists():
        return archivo.read_text(encoding="utf-8").strip()

    RUTA_DATA.mkdir(parents=True, exist_ok=True)
    clave = secrets.token_hex(32)
    archivo.write_text(clave, encoding="utf-8")
    return clave
