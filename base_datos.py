"""Capa de datos: único módulo que lee y escribe en SQLite.

Tablas: estudiantes, resultados, progreso_bkt, planes y docentes. Todas las consultas
usan parámetros (``?``), nunca texto concatenado del usuario.
"""

import sqlite3
from contextlib import contextmanager

import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS estudiantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_lista INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    colegio TEXT NOT NULL,
    edad INTEGER NOT NULL,
    curso TEXT NOT NULL,
    UNIQUE (colegio, curso, numero_lista)
);

CREATE TABLE IF NOT EXISTS resultados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id),
    materia TEXT NOT NULL,
    tema TEXT NOT NULL,
    nivel TEXT NOT NULL,
    puntaje INTEGER NOT NULL,
    total INTEGER NOT NULL,
    porcentaje REAL NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS progreso_bkt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id),
    materia TEXT NOT NULL,
    tema TEXT NOT NULL,
    subtema TEXT NOT NULL,
    dominio REAL NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS docentes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    usuario TEXT NOT NULL UNIQUE,
    colegio TEXT NOT NULL,
    clave_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS planes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    estudiante_id INTEGER NOT NULL REFERENCES estudiantes(id),
    materia TEXT NOT NULL,
    tema TEXT NOT NULL,
    tiempo_disponible INTEGER NOT NULL,
    tiempo_usado INTEGER NOT NULL,
    beneficio REAL NOT NULL,
    ejercicios INTEGER NOT NULL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_resultados_estudiante ON resultados (estudiante_id);
CREATE INDEX IF NOT EXISTS idx_progreso_estudiante
    ON progreso_bkt (estudiante_id, materia, tema, subtema);
CREATE INDEX IF NOT EXISTS idx_planes_estudiante ON planes (estudiante_id);
"""


@contextmanager
def conectar():
    """Abre una conexión, confirma los cambios al salir y siempre la cierra."""
    conexion = sqlite3.connect(config.RUTA_BD)
    conexion.execute("PRAGMA foreign_keys = ON")
    try:
        yield conexion
        conexion.commit()
    except Exception:
        conexion.rollback()
        raise
    finally:
        conexion.close()


def crear_base_datos():
    """Crea la carpeta de datos, las tablas y los índices si no existen."""
    config.RUTA_BD.parent.mkdir(parents=True, exist_ok=True)
    with conectar() as conexion:
        conexion.executescript(ESQUEMA)


def _marcas(cantidad):
    return ",".join("?" * cantidad)


# ------------------------------------------------------------------
# Estudiantes
# ------------------------------------------------------------------


def obtener_o_crear_estudiante(numero_lista, nombre, colegio, edad, curso):
    """Devuelve el id del estudiante (colegio, curso, lista); si no existe, lo crea.

    Si ya existe, actualiza su nombre y edad con los últimos datos escritos.
    """
    with conectar() as conexion:
        fila = conexion.execute(
            "SELECT id FROM estudiantes WHERE colegio = ? AND curso = ? AND numero_lista = ?",
            (colegio, curso, numero_lista),
        ).fetchone()

        if fila is not None:
            conexion.execute(
                "UPDATE estudiantes SET nombre = ?, edad = ? WHERE id = ?",
                (nombre, edad, fila[0]),
            )
            return fila[0]

        cursor = conexion.execute(
            "INSERT INTO estudiantes (numero_lista, nombre, colegio, edad, curso) "
            "VALUES (?, ?, ?, ?, ?)",
            (numero_lista, nombre, colegio, edad, curso),
        )
        return cursor.lastrowid


def buscar_estudiante(numero_lista, colegio, curso):
    """(id, nombre, colegio, edad, curso, numero_lista) o None."""
    with conectar() as conexion:
        return conexion.execute(
            "SELECT id, nombre, colegio, edad, curso, numero_lista FROM estudiantes "
            "WHERE colegio = ? AND curso = ? AND numero_lista = ?",
            (colegio, curso, numero_lista),
        ).fetchone()


def obtener_estudiante(estudiante_id):
    """(id, nombre, colegio, edad, curso, numero_lista) o None."""
    with conectar() as conexion:
        return conexion.execute(
            "SELECT id, nombre, colegio, edad, curso, numero_lista FROM estudiantes WHERE id = ?",
            (estudiante_id,),
        ).fetchone()


# ------------------------------------------------------------------
# Resultados, dominio y planes
# ------------------------------------------------------------------


def guardar_resultado(estudiante_id, materia, tema, nivel, puntaje, total, porcentaje):
    with conectar() as conexion:
        conexion.execute(
            "INSERT INTO resultados (estudiante_id, materia, tema, nivel, puntaje, total, "
            "porcentaje) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (estudiante_id, materia, tema, nivel, puntaje, total, porcentaje),
        )


def guardar_dominio_bkt(estudiante_id, materia, tema, subtema, dominio):
    with conectar() as conexion:
        conexion.execute(
            "INSERT INTO progreso_bkt (estudiante_id, materia, tema, subtema, dominio) "
            "VALUES (?, ?, ?, ?, ?)",
            (estudiante_id, materia, tema, subtema, dominio),
        )


def cargar_dominio_bkt(estudiante_id, materia, tema, subtema):
    """Último dominio guardado de un subtema, o None si nunca lo ha trabajado."""
    with conectar() as conexion:
        fila = conexion.execute(
            "SELECT dominio FROM progreso_bkt "
            "WHERE estudiante_id = ? AND materia = ? AND tema = ? AND subtema = ? "
            "ORDER BY fecha DESC, id DESC LIMIT 1",
            (estudiante_id, materia, tema, subtema),
        ).fetchone()
    return None if fila is None else fila[0]


def obtener_historial(estudiante_id):
    """Evaluaciones del estudiante, de la más reciente a la más antigua.

    Cada fila es (materia, tema, nivel, puntaje, total, porcentaje, fecha). La fecha se
    convierte a la hora local del computador (SQLite la guarda en UTC).
    """
    with conectar() as conexion:
        return conexion.execute(
            "SELECT materia, tema, nivel, puntaje, total, porcentaje, "
            "datetime(fecha, 'localtime') FROM resultados WHERE estudiante_id = ? "
            "ORDER BY fecha DESC, id DESC",
            (estudiante_id,),
        ).fetchall()


def _registros_bkt(estudiante_id, orden):
    with conectar() as conexion:
        return conexion.execute(
            "SELECT materia, tema, subtema, dominio, fecha FROM progreso_bkt "
            f"WHERE estudiante_id = ? ORDER BY fecha {orden}, id {orden}",
            (estudiante_id,),
        ).fetchall()


def obtener_dominios_actuales(estudiante_id):
    """Último dominio de cada (materia, tema, subtema) del estudiante."""
    dominios = {}
    for materia, tema, subtema, dominio, fecha in _registros_bkt(estudiante_id, "DESC"):
        dominios.setdefault(
            (materia, tema, subtema),
            {"materia": materia, "tema": tema, "subtema": subtema, "dominio": dominio,
             "fecha": fecha},
        )
    return list(dominios.values())


def obtener_evolucion_bkt(estudiante_id):
    """Historial del dominio agrupado por subtema, en orden cronológico."""
    grupos = {}
    for materia, tema, subtema, dominio, fecha in _registros_bkt(estudiante_id, "ASC"):
        grupo = grupos.setdefault(
            (materia, tema, subtema),
            {"materia": materia, "tema": tema, "subtema": subtema, "registros": []},
        )
        grupo["registros"].append({"dominio": dominio, "fecha": fecha})
    return list(grupos.values())


def guardar_plan(estudiante_id, materia, tema, tiempo_disponible, tiempo_usado, beneficio,
                 ejercicios):
    with conectar() as conexion:
        conexion.execute(
            "INSERT INTO planes (estudiante_id, materia, tema, tiempo_disponible, "
            "tiempo_usado, beneficio, ejercicios) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (estudiante_id, materia, tema, tiempo_disponible, tiempo_usado, beneficio,
             ejercicios),
        )


# ------------------------------------------------------------------
# Docentes
# ------------------------------------------------------------------


def crear_docente(nombre, usuario, colegio, clave_hash):
    """Crea la cuenta y devuelve su id, o None si el usuario ya existe."""
    with conectar() as conexion:
        try:
            cursor = conexion.execute(
                "INSERT INTO docentes (nombre, usuario, colegio, clave_hash) VALUES (?, ?, ?, ?)",
                (nombre, usuario, colegio, clave_hash),
            )
        except sqlite3.IntegrityError:
            return None
        return cursor.lastrowid


def buscar_docente(usuario):
    """(id, nombre, usuario, colegio, clave_hash) o None."""
    with conectar() as conexion:
        return conexion.execute(
            "SELECT id, nombre, usuario, colegio, clave_hash FROM docentes WHERE usuario = ?",
            (usuario,),
        ).fetchone()


def obtener_docente(docente_id):
    """(id, nombre, usuario, colegio) o None."""
    with conectar() as conexion:
        return conexion.execute(
            "SELECT id, nombre, usuario, colegio FROM docentes WHERE id = ?",
            (docente_id,),
        ).fetchone()


# ------------------------------------------------------------------
# Datos para el panel docente (el colegio se compara sin mayúsculas ni espacios)
# ------------------------------------------------------------------


def obtener_cursos(colegio):
    with conectar() as conexion:
        filas = conexion.execute(
            "SELECT DISTINCT curso FROM estudiantes "
            "WHERE lower(trim(colegio)) = lower(trim(?)) ORDER BY curso",
            (colegio,),
        ).fetchall()
    return [fila[0] for fila in filas]


def obtener_estudiantes(colegio, curso=None):
    """Filas (id, numero_lista, nombre, curso, edad) del colegio, opcionalmente de un curso."""
    consulta = (
        "SELECT id, numero_lista, nombre, curso, edad FROM estudiantes "
        "WHERE lower(trim(colegio)) = lower(trim(?))"
    )
    parametros = [colegio]
    if curso:
        consulta += " AND curso = ?"
        parametros.append(curso)
    consulta += " ORDER BY curso, numero_lista"

    with conectar() as conexion:
        return conexion.execute(consulta, parametros).fetchall()


def obtener_resultados_de(estudiantes_ids):
    """Filas (estudiante_id, materia, tema, porcentaje, fecha) en orden cronológico."""
    if not estudiantes_ids:
        return []
    with conectar() as conexion:
        return conexion.execute(
            "SELECT estudiante_id, materia, tema, porcentaje, fecha FROM resultados "
            f"WHERE estudiante_id IN ({_marcas(len(estudiantes_ids))}) "
            "ORDER BY fecha ASC, id ASC",
            list(estudiantes_ids),
        ).fetchall()


def obtener_planes_de(estudiantes_ids):
    """Filas (estudiante_id, tiempo_disponible, tiempo_usado, beneficio)."""
    if not estudiantes_ids:
        return []
    with conectar() as conexion:
        return conexion.execute(
            "SELECT estudiante_id, tiempo_disponible, tiempo_usado, beneficio FROM planes "
            f"WHERE estudiante_id IN ({_marcas(len(estudiantes_ids))})",
            list(estudiantes_ids),
        ).fetchall()


def obtener_ultimos_dominios_de(estudiantes_ids):
    """Último dominio de cada (estudiante, materia, tema, subtema)."""
    if not estudiantes_ids:
        return []
    with conectar() as conexion:
        filas = conexion.execute(
            "SELECT estudiante_id, materia, tema, subtema, dominio FROM progreso_bkt "
            f"WHERE estudiante_id IN ({_marcas(len(estudiantes_ids))}) "
            "ORDER BY fecha ASC, id ASC",
            list(estudiantes_ids),
        ).fetchall()

    ultimos = {}
    for estudiante_id, materia, tema, subtema, dominio in filas:
        ultimos[(estudiante_id, materia, tema, subtema)] = dominio
    return [(*clave, dominio) for clave, dominio in ultimos.items()]


if __name__ == "__main__":
    crear_base_datos()
    print(f"Base de datos lista en {config.RUTA_BD}")
