import sqlite3
import os


# ==========================================
# CONFIGURACION DE LA BASE DE DATOS
# ==========================================

RUTA_DATA = "data"

RUTA_BD = os.path.join(
    RUTA_DATA,
    "tutoria.db"
)


os.makedirs(
    RUTA_DATA,
    exist_ok=True
)


# ==========================================
# CONECTAR
# ==========================================

def conectar():

    return sqlite3.connect(
        RUTA_BD
    )


# ==========================================
# CREAR BASE DE DATOS
# ==========================================

def crear_base_datos():

    conexion = conectar()

    cursor = conexion.cursor()


    # ======================================
    # TABLA ESTUDIANTES
    # ======================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS estudiantes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            numero_lista INTEGER NOT NULL,

            nombre TEXT NOT NULL,

            colegio TEXT NOT NULL,

            edad INTEGER NOT NULL,

            curso TEXT NOT NULL,

            UNIQUE (
                colegio,
                curso,
                numero_lista
            )
        )
        """
    )


    # ======================================
    # TABLA RESULTADOS
    # ======================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS resultados (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            estudiante_id INTEGER NOT NULL,

            materia TEXT NOT NULL,

            tema TEXT NOT NULL,

            nivel TEXT NOT NULL,

            puntaje INTEGER NOT NULL,

            total INTEGER NOT NULL,

            porcentaje REAL NOT NULL,

            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                estudiante_id
            )
            REFERENCES estudiantes(id)
        )
        """
    )


    # ======================================
    # TABLA PROGRESO BKT
    # ======================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS progreso_bkt (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            estudiante_id INTEGER NOT NULL,

            materia TEXT NOT NULL,

            tema TEXT NOT NULL,

            subtema TEXT NOT NULL,

            dominio REAL NOT NULL,

            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                estudiante_id
            )
            REFERENCES estudiantes(id)
        )
        """
    )


    # ======================================
    # TABLA DOCENTES
    # ======================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS docentes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nombre TEXT NOT NULL,

            usuario TEXT NOT NULL UNIQUE,

            colegio TEXT NOT NULL,

            clave_hash TEXT NOT NULL
        )
        """
    )


    # ======================================
    # TABLA PLANES DE ESTUDIO
    # ======================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS planes (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            estudiante_id INTEGER NOT NULL,

            materia TEXT NOT NULL,

            tema TEXT NOT NULL,

            tiempo_disponible INTEGER NOT NULL,

            tiempo_usado INTEGER NOT NULL,

            beneficio REAL NOT NULL,

            ejercicios INTEGER NOT NULL,

            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (
                estudiante_id
            )
            REFERENCES estudiantes(id)
        )
        """
    )


    conexion.commit()

    conexion.close()


# ==========================================
# OBTENER O CREAR ESTUDIANTE
# ==========================================

def obtener_o_crear_estudiante(
    numero_lista,
    nombre,
    colegio,
    edad,
    curso
):

    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute(
        """
        SELECT id

        FROM estudiantes

        WHERE colegio = ?
        AND curso = ?
        AND numero_lista = ?
        """,
        (
            colegio,
            curso,
            numero_lista
        )
    )


    estudiante = cursor.fetchone()


    # ======================================
    # SI EL ESTUDIANTE YA EXISTE
    # ======================================

    if estudiante is not None:

        estudiante_id = estudiante[0]


        cursor.execute(
            """
            UPDATE estudiantes

            SET
                nombre = ?,
                edad = ?

            WHERE id = ?
            """,
            (
                nombre,
                edad,
                estudiante_id
            )
        )


        conexion.commit()

        conexion.close()


        return estudiante_id


    # ======================================
    # SI ES NUEVO ESTUDIANTE
    # ======================================

    cursor.execute(
        """
        INSERT INTO estudiantes (
            numero_lista,
            nombre,
            colegio,
            edad,
            curso
        )

        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            numero_lista,
            nombre,
            colegio,
            edad,
            curso
        )
    )


    conexion.commit()


    estudiante_id = cursor.lastrowid


    conexion.close()


    return estudiante_id


# ==========================================
# BUSCAR ESTUDIANTE
# ==========================================

def buscar_estudiante(
    numero_lista,
    colegio,
    curso
):

    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute(
        """
        SELECT
            id,
            nombre,
            colegio,
            edad,
            curso,
            numero_lista

        FROM estudiantes

        WHERE colegio = ?
        AND curso = ?
        AND numero_lista = ?
        """,
        (
            colegio,
            curso,
            numero_lista
        )
    )


    estudiante = cursor.fetchone()


    conexion.close()


    return estudiante


# ==========================================
# GUARDAR RESULTADO
# ==========================================

def guardar_resultado(
    estudiante_id,
    materia,
    tema,
    nivel,
    puntaje,
    total,
    porcentaje
):

    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute(
        """
        INSERT INTO resultados (
            estudiante_id,
            materia,
            tema,
            nivel,
            puntaje,
            total,
            porcentaje
        )

        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            estudiante_id,
            materia,
            tema,
            nivel,
            puntaje,
            total,
            porcentaje
        )
    )


    conexion.commit()

    conexion.close()


# ==========================================
# GUARDAR DOMINIO BKT
# ==========================================

def guardar_dominio_bkt(
    estudiante_id,
    materia,
    tema,
    subtema,
    dominio
):

    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute(
        """
        INSERT INTO progreso_bkt (
            estudiante_id,
            materia,
            tema,
            subtema,
            dominio
        )

        VALUES (
            ?,
            ?,
            ?,
            ?,
            ?
        )
        """,
        (
            estudiante_id,
            materia,
            tema,
            subtema,
            dominio
        )
    )


    conexion.commit()

    conexion.close()


# ==========================================
# CARGAR ULTIMO DOMINIO BKT
# ==========================================

def cargar_dominio_bkt(
    estudiante_id,
    materia,
    tema,
    subtema
):

    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute(
        """
        SELECT dominio

        FROM progreso_bkt

        WHERE estudiante_id = ?
        AND materia = ?
        AND tema = ?
        AND subtema = ?

        ORDER BY
            fecha DESC,
            id DESC

        LIMIT 1
        """,
        (
            estudiante_id,
            materia,
            tema,
            subtema
        )
    )


    resultado = cursor.fetchone()


    conexion.close()


    if resultado is None:

        return None


    return resultado[0]


# ==========================================
# OBTENER HISTORIAL DE EVALUACIONES
# ==========================================

def obtener_historial(
    estudiante_id
):

    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute(
        """
        SELECT
            materia,
            tema,
            nivel,
            puntaje,
            total,
            porcentaje,
            fecha

        FROM resultados

        WHERE estudiante_id = ?

        ORDER BY
            fecha DESC,
            id DESC
        """,
        (
            estudiante_id,
        )
    )


    historial = cursor.fetchall()


    conexion.close()


    return historial


# ==========================================
# OBTENER DOMINIOS ACTUALES
# ==========================================

def obtener_dominios_actuales(
    estudiante_id
):

    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute(
        """
        SELECT
            materia,
            tema,
            subtema,
            dominio,
            fecha,
            id

        FROM progreso_bkt

        WHERE estudiante_id = ?

        ORDER BY
            fecha DESC,
            id DESC
        """,
        (
            estudiante_id,
        )
    )


    registros = cursor.fetchall()


    conexion.close()


    dominios = {}


    # ======================================
    # CONSERVAR SOLO EL ULTIMO REGISTRO
    # DE CADA SUBTEMA
    # ======================================

    for registro in registros:

        materia = registro[0]

        tema = registro[1]

        subtema = registro[2]

        dominio = registro[3]

        fecha = registro[4]


        clave = (
            materia,
            tema,
            subtema
        )


        if clave not in dominios:

            dominios[clave] = {

                "materia": materia,

                "tema": tema,

                "subtema": subtema,

                "dominio": dominio,

                "fecha": fecha
            }


    return list(
        dominios.values()
    )


# ==========================================
# OBTENER EVOLUCION DEL BKT
# ==========================================

def obtener_evolucion_bkt(
    estudiante_id
):

    conexion = conectar()

    cursor = conexion.cursor()


    cursor.execute(
        """
        SELECT
            materia,
            tema,
            subtema,
            dominio,
            fecha,
            id

        FROM progreso_bkt

        WHERE estudiante_id = ?

        ORDER BY
            fecha ASC,
            id ASC
        """,
        (
            estudiante_id,
        )
    )


    registros = cursor.fetchall()


    conexion.close()


    grupos = {}


    # ======================================
    # AGRUPAR HISTORIAL POR SUBTEMA
    # ======================================

    for registro in registros:

        materia = registro[0]

        tema = registro[1]

        subtema = registro[2]

        dominio = registro[3]

        fecha = registro[4]


        clave = (
            materia,
            tema,
            subtema
        )


        if clave not in grupos:

            grupos[clave] = {

                "materia": materia,

                "tema": tema,

                "subtema": subtema,

                "registros": []
            }


        grupos[
            clave
        ][
            "registros"
        ].append(
            {

                "dominio": dominio,

                "fecha": fecha
            }
        )


    return list(
        grupos.values()
    )


# ==========================================
# GUARDAR PLAN DE ESTUDIO
# ==========================================

def guardar_plan(
    estudiante_id,
    materia,
    tema,
    tiempo_disponible,
    tiempo_usado,
    beneficio,
    ejercicios
):

    conexion = conectar()

    conexion.execute(
        """
        INSERT INTO planes (
            estudiante_id, materia, tema, tiempo_disponible,
            tiempo_usado, beneficio, ejercicios
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (estudiante_id, materia, tema, tiempo_disponible, tiempo_usado, beneficio, ejercicios)
    )

    conexion.commit()

    conexion.close()


# ==========================================
# DOCENTES
# ==========================================

def crear_docente(nombre, usuario, colegio, clave_hash):

    conexion = conectar()

    existe = conexion.execute(
        "SELECT id FROM docentes WHERE usuario = ?",
        (usuario,)
    ).fetchone()

    if existe is not None:
        conexion.close()
        return None

    cursor = conexion.execute(
        "INSERT INTO docentes (nombre, usuario, colegio, clave_hash) VALUES (?, ?, ?, ?)",
        (nombre, usuario, colegio, clave_hash)
    )

    conexion.commit()

    docente_id = cursor.lastrowid

    conexion.close()

    return docente_id


def buscar_docente(usuario):

    conexion = conectar()

    docente = conexion.execute(
        "SELECT id, nombre, usuario, colegio, clave_hash FROM docentes WHERE usuario = ?",
        (usuario,)
    ).fetchone()

    conexion.close()

    return docente


def obtener_docente(docente_id):

    conexion = conectar()

    docente = conexion.execute(
        "SELECT id, nombre, usuario, colegio FROM docentes WHERE id = ?",
        (docente_id,)
    ).fetchone()

    conexion.close()

    return docente


# ==========================================
# DATOS PARA EL PANEL DOCENTE
# ==========================================

def obtener_cursos(colegio):

    conexion = conectar()

    filas = conexion.execute(
        """
        SELECT DISTINCT curso FROM estudiantes
        WHERE lower(trim(colegio)) = lower(trim(?))
        ORDER BY curso
        """,
        (colegio,)
    ).fetchall()

    conexion.close()

    return [fila[0] for fila in filas]


def obtener_estudiantes(colegio, curso=None):

    conexion = conectar()

    consulta = """
        SELECT id, numero_lista, nombre, curso, edad
        FROM estudiantes
        WHERE lower(trim(colegio)) = lower(trim(?))
    """
    parametros = [colegio]

    if curso:
        consulta += " AND curso = ?"
        parametros.append(curso)

    consulta += " ORDER BY curso, numero_lista"

    filas = conexion.execute(consulta, parametros).fetchall()

    conexion.close()

    return filas


def obtener_estudiante(estudiante_id):

    conexion = conectar()

    fila = conexion.execute(
        "SELECT id, nombre, colegio, edad, curso, numero_lista FROM estudiantes WHERE id = ?",
        (estudiante_id,)
    ).fetchone()

    conexion.close()

    return fila


def obtener_resultados_de(estudiantes_ids):

    if not estudiantes_ids:
        return []

    marcas = ",".join("?" * len(estudiantes_ids))

    conexion = conectar()

    filas = conexion.execute(
        f"""
        SELECT estudiante_id, materia, tema, porcentaje, fecha
        FROM resultados
        WHERE estudiante_id IN ({marcas})
        ORDER BY fecha ASC, id ASC
        """,
        estudiantes_ids
    ).fetchall()

    conexion.close()

    return filas


def obtener_planes_de(estudiantes_ids):

    if not estudiantes_ids:
        return []

    marcas = ",".join("?" * len(estudiantes_ids))

    conexion = conectar()

    filas = conexion.execute(
        f"SELECT estudiante_id, tiempo_disponible, tiempo_usado, beneficio FROM planes WHERE estudiante_id IN ({marcas})",
        estudiantes_ids
    ).fetchall()

    conexion.close()

    return filas


def obtener_ultimos_dominios_de(estudiantes_ids):

    if not estudiantes_ids:
        return []

    marcas = ",".join("?" * len(estudiantes_ids))

    conexion = conectar()

    filas = conexion.execute(
        f"""
        SELECT estudiante_id, materia, tema, subtema, dominio
        FROM progreso_bkt
        WHERE estudiante_id IN ({marcas})
        ORDER BY fecha ASC, id ASC
        """,
        estudiantes_ids
    ).fetchall()

    conexion.close()

    ultimos = {}

    for estudiante_id, materia, tema, subtema, dominio in filas:
        ultimos[(estudiante_id, materia, tema, subtema)] = dominio

    return [
        (estudiante_id, materia, tema, subtema, dominio)
        for (estudiante_id, materia, tema, subtema), dominio in ultimos.items()
    ]


# ==========================================
# PRUEBA DIRECTA
# ==========================================

if __name__ == "__main__":

    crear_base_datos()


    print(
        "Base de datos creada correctamente."
    )


    print(
        "Ruta:",
        RUTA_BD
    )