# Cómo contribuir

## Entorno de desarrollo

```bash
python -m venv .venv
```

```bash
.venv/bin/pip install -r requirements-dev.txt     # Windows: .venv\Scripts\pip ...
```

## Antes de subir un cambio

```bash
ruff check .
```

```bash
pytest
```

Las pruebas no necesitan LM Studio: usan un generador de preguntas falso y una base de datos temporal. Si el cambio toca `bkt.py`, `beneficio.py`, `mochila.py` o `simulacion/`, ejecute también `python -m simulacion`: `tests/test_reproducibilidad.py` falla si las cifras dejan de coincidir con el paper.

## Convenciones

- Código, comentarios y mensajes de commit en español, igual que el resto del proyecto.
- `ia.py` es el único módulo que habla con LM Studio y `base_datos.py` el único que toca SQLite; mantenga esa separación.
- Toda consulta SQL usa parámetros (`?`), nunca texto concatenado del usuario.
- Los mensajes que ve el usuario explican qué pasó y qué hacer, sin trazas de Python.
- Un cambio de comportamiento viene con su prueba en `tests/`.
- Trabaje en una rama y abra un pull request hacia `main`; el CI debe quedar en verde.
