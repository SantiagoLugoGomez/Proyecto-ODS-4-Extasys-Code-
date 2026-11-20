"""KPIs del panel docente (Tabla 6 del paper).

Se calculan con consultas a la base de datos local; no hay datos fuera del colegio.
"""

from base_datos import (
    obtener_estudiantes,
    obtener_planes_de,
    obtener_resultados_de,
    obtener_ultimos_dominios_de,
)

# Un estudiante necesita apoyo si su dominio promedio es menor que este valor...
UMBRAL_APOYO = 0.5
# ...o si su última evaluación tiene un acierto menor que este porcentaje.
UMBRAL_NOTA_APOYO = 60


def promedio(valores):
    return sum(valores) / len(valores) if valores else None


def resumen_curso(colegio, curso=None):
    """Calcula los KPIs del curso, la fila de cada estudiante y los subtemas más débiles.

    Devuelve ``(kpis, filas, subtemas)``; los subtemas van del menor al mayor dominio.
    """
    estudiantes = obtener_estudiantes(colegio, curso)
    ids = [e[0] for e in estudiantes]

    resultados = obtener_resultados_de(ids)
    planes = obtener_planes_de(ids)
    dominios = obtener_ultimos_dominios_de(ids)

    notas_por_estudiante = {}
    for estudiante_id, _materia, _tema, porcentaje, _fecha in resultados:
        notas_por_estudiante.setdefault(estudiante_id, []).append(porcentaje)

    dominio_por_estudiante = {}
    for estudiante_id, _materia, _tema, _subtema, dominio in dominios:
        dominio_por_estudiante.setdefault(estudiante_id, []).append(dominio)

    planes_por_estudiante = {}
    for estudiante_id, *_ in planes:
        planes_por_estudiante[estudiante_id] = planes_por_estudiante.get(estudiante_id, 0) + 1

    filas = []
    for estudiante_id, numero_lista, nombre, curso_estudiante, _edad in estudiantes:
        notas = notas_por_estudiante.get(estudiante_id, [])
        dominio = promedio(dominio_por_estudiante.get(estudiante_id, []))
        ultima = notas[-1] if notas else None
        mejora = notas[-1] - notas[0] if len(notas) >= 2 else None
        necesita_apoyo = (dominio is not None and dominio < UMBRAL_APOYO) or (
            ultima is not None and ultima < UMBRAL_NOTA_APOYO
        )

        if not notas:
            estado = "Sin actividad"
        elif necesita_apoyo:
            estado = "Necesita apoyo"
        else:
            estado = "Al día"

        filas.append({
            "id": estudiante_id,
            "numero_lista": numero_lista,
            "nombre": nombre,
            "curso": curso_estudiante,
            "evaluaciones": len(notas),
            "planes": planes_por_estudiante.get(estudiante_id, 0),
            "ultima": ultima,
            "mejora": mejora,
            "dominio": dominio,
            "estado": estado,
        })

    activos = [f for f in filas if f["evaluaciones"] > 0]
    que_vuelven = [f for f in activos if f["evaluaciones"] >= 2]
    mejoras = [f["mejora"] for f in filas if f["mejora"] is not None]
    todas_las_notas = [nota for notas in notas_por_estudiante.values() for nota in notas]

    kpis = {
        "registrados": len(filas),
        "activos": len(activos),
        "evaluaciones": len(todas_las_notas),
        "acierto": promedio(todas_las_notas),
        "mejora": promedio(mejoras),
        "retorno": len(que_vuelven) / len(activos) * 100 if activos else None,
        "uso_plan": (
            min(len(planes) / len(todas_las_notas) * 100, 100) if todas_las_notas else None
        ),
        "apoyo": sum(1 for f in filas if f["estado"] == "Necesita apoyo"),
    }

    # Dominio promedio del grupo por subtema (sin distinguir mayúsculas).
    por_subtema = {}
    nombres = {}
    for _estudiante_id, materia, tema, subtema, dominio in dominios:
        clave = (materia.lower(), tema.lower(), subtema.lower())
        nombres.setdefault(clave, (materia, tema.capitalize(), subtema.capitalize()))
        por_subtema.setdefault(clave, []).append(dominio)

    subtemas = sorted(
        (
            {
                "materia": nombres[clave][0],
                "tema": nombres[clave][1],
                "subtema": nombres[clave][2],
                "dominio": promedio(valores),
                "estudiantes": len(valores),
            }
            for clave, valores in por_subtema.items()
        ),
        key=lambda s: s["dominio"],
    )

    return kpis, filas, subtemas
