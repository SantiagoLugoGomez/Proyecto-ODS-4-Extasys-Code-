# ==========================================
# INDICADORES DEL PANEL DOCENTE
# ==========================================

from base_datos import (
    obtener_estudiantes,
    obtener_resultados_de,
    obtener_planes_de,
    obtener_ultimos_dominios_de
)


UMBRAL_APOYO = 0.5


def promedio(valores):

    if not valores:
        return None

    return sum(valores) / len(valores)


def resumen_curso(colegio, curso=None):

    estudiantes = obtener_estudiantes(colegio, curso)
    ids = [e[0] for e in estudiantes]

    resultados = obtener_resultados_de(ids)
    planes = obtener_planes_de(ids)
    dominios = obtener_ultimos_dominios_de(ids)

    porcentajes = {}
    for estudiante_id, materia, tema, porcentaje, fecha in resultados:
        porcentajes.setdefault(estudiante_id, []).append(porcentaje)

    dominio_por_estudiante = {}
    for estudiante_id, materia, tema, subtema, dominio in dominios:
        dominio_por_estudiante.setdefault(estudiante_id, []).append(dominio)

    planes_por_estudiante = {}
    for estudiante_id, disponible, usado, beneficio in planes:
        planes_por_estudiante[estudiante_id] = planes_por_estudiante.get(estudiante_id, 0) + 1

    filas = []
    for estudiante_id, numero_lista, nombre, curso_e, edad in estudiantes:
        notas = porcentajes.get(estudiante_id, [])
        dominio = promedio(dominio_por_estudiante.get(estudiante_id, []))
        ultima = notas[-1] if notas else None
        mejora = notas[-1] - notas[0] if len(notas) >= 2 else None
        apoyo = (dominio is not None and dominio < UMBRAL_APOYO) or (ultima is not None and ultima < 60)
        filas.append({
            "id": estudiante_id,
            "numero_lista": numero_lista,
            "nombre": nombre,
            "curso": curso_e,
            "evaluaciones": len(notas),
            "planes": planes_por_estudiante.get(estudiante_id, 0),
            "ultima": ultima,
            "mejora": mejora,
            "dominio": dominio,
            "estado": "Sin actividad" if not notas else ("Necesita apoyo" if apoyo else "Al día")
        })

    activos = [f for f in filas if f["evaluaciones"] > 0]
    que_vuelven = [f for f in activos if f["evaluaciones"] >= 2]
    mejoras = [f["mejora"] for f in filas if f["mejora"] is not None]
    todas_las_notas = [p for notas in porcentajes.values() for p in notas]

    kpis = {
        "registrados": len(filas),
        "activos": len(activos),
        "evaluaciones": len(todas_las_notas),
        "acierto": promedio(todas_las_notas),
        "mejora": promedio(mejoras),
        "retorno": len(que_vuelven) / len(activos) * 100 if activos else None,
        "uso_plan": min(len(planes) / len(todas_las_notas) * 100, 100) if todas_las_notas else None,
        "apoyo": sum(1 for f in filas if f["estado"] == "Necesita apoyo")
    }

    por_subtema = {}
    nombres = {}
    for estudiante_id, materia, tema, subtema, dominio in dominios:
        clave = (materia.lower(), tema.lower(), subtema.lower())
        nombres.setdefault(clave, (materia, tema.capitalize(), subtema.capitalize()))
        por_subtema.setdefault(clave, []).append(dominio)

    subtemas = sorted(
        (
            {
                "materia": materia,
                "tema": tema,
                "subtema": subtema,
                "dominio": promedio(valores),
                "estudiantes": len(valores)
            }
            for (materia, tema, subtema), valores in (
                (nombres[clave], valores) for clave, valores in por_subtema.items()
            )
        ),
        key=lambda s: s["dominio"]
    )

    return kpis, filas, subtemas
