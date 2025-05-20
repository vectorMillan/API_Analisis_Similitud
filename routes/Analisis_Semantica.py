from flask import Blueprint, render_template, request, redirect
from config.config import db
from models.BotonTematica import Tematicas
from models.Tolerancia_Porcentajes import ToleranciasPorcentajes
from sqlalchemy import text
import math

semantica = Blueprint('analisis', __name__)

@semantica.route('/proyecto/<int:proyecto_id>/analisis')
def mostrar_detalles_proyecto(proyecto_id):
    # Obtenemos el nombre del proyecto
    sql_proyecto = text("SELECT name FROM project WHERE id = :proyecto_id")
    proyecto = db.session.execute(sql_proyecto, {"proyecto_id": proyecto_id}).fetchone()
    
    if not proyecto:
        return redirect('/analisis-similitud')
    
    # Consulta para obtener los detalles de similitud
    sql_detalles = text("""
        SELECT
            CONCAT(
                u1.name, ' ', u1.falastname, ' ', u1.molastname,
                '\nvs\n',
                u2.name, ' ', u2.falastname, ' ', u2.molastname
            ) AS usuarios_analizados,
            cs.introduccion,
            cs.marcoteorico,
            cs.metodo,
            cs.resultados,
            cs.discusion,
            cs.conclusiones,
            cs.secciones_similares,
            cs.status_analisis
        FROM comparacion_similitud cs
        JOIN `user` u1 ON cs.usuario_1_id = u1.id
        JOIN `user` u2 ON cs.usuario_2_id = u2.id
        WHERE cs.project_id = :proyecto_id
        ORDER BY cs.id
    """)
    
    detalles = db.session.execute(sql_detalles, {"proyecto_id": proyecto_id}).fetchall()
    
    # Crear un diccionario con las tolerancias por sección
    tolerancias = {}
    todas_tolerancias = ToleranciasPorcentajes.query.all()
    
    for t in todas_tolerancias:
        # Convertimos los nombres de sección a minúsculas para mayor compatibilidad
        tolerancias[t.seccion.lower()] = t.tolerancia
        # IMPRIMIR TOLERANCIAS
        print(f"Sección: {t.seccion}, Tolerancia: {t.tolerancia}")

    return render_template('Detalles_Proyectos.html', 
                            proyecto=proyecto,
                            proyecto_id=proyecto_id,
                            detalles=detalles,
                            tolerancias=tolerancias)