from flask import Blueprint, render_template, request, redirect, jsonify, current_app, url_for, flash, Response
from config.config import db
from models.BotonTematica import Tematicas # Asumo que este modelo existe y se llama así
from models.Tolerancia_Porcentajes import ToleranciasPorcentajes
from models.Reportes_Finales import ReportesFinales  #Importar para la ruta de análisis individual
from models.Comparacion_Similitud import ComparacionSimilitud # Para verificar estados si es necesario
# Importar los servicios de análisis NLP
from services.Procesamiento_Similitud import (
    analizar_todos_los_proyectos_service, 
    analizar_proyecto as analizar_proyecto_individual_service,
    obtener_tolerancias # Importar para usar en la ruta de análisis individual
)
from services.Procesamiento_Semantico import ( # Importar el nuevo servicio SEMÁNTICO
    analizar_todos_los_proyectos_semantico_service,
    analizar_proyecto_semantico as analizar_proyecto_semantico_individual_service,
    obtener_tolerancias_semantico
)
from services.Procesamiento_Completo import realizar_analisis_completo_sse
from sqlalchemy import text
import math
from services.Procesamiento_Filtro import filtrar_y_guardar_reportes_service

analisis = Blueprint('analisis', __name__)

@analisis.route('/')
def index():
    # Redirigir a la vista principal de análisis de similitud o cargarla directamente
    return redirect(url_for('analisis.mostrar_tematicas_base'))

@analisis.route('/analisis-similitud') 
def mostrar_tematicas_base():
    tematicas_activas = Tematicas.query.filter_by(status=1).all()
    return render_template('AnalisisSimilitud.html', 
                        tematicas=tematicas_activas, 
                        tematica_actual=None, 
                        proyectos=None,
                        total_paginas=0,
                        pagina_actual=1)

@analisis.route('/analisis-similitud/<int:tematica_id>')
def mostrar_proyectos_por_tematica(tematica_id):
    # Obtenemos las temáticas para el menú
    tematicas = Tematicas.query.filter_by(status=1).all()
    
    # Parámetros de paginación
    pagina = request.args.get('pagina', 1, type=int)
    registros_por_pagina = 10
    
    # Corregimos la consulta de conteo para reflejar la agrupación correcta
    count_query = text("""
        SELECT COUNT(*) as total
        FROM (
            SELECT p.id
            FROM project p
            JOIN reportes_finales rf ON rf.project_id = p.id
            WHERE p.id_thematic = :tematica_id
            GROUP BY p.id, p.name
        ) as proyecto_count
    """)
    
    result = db.session.execute(count_query, {"tematica_id": tematica_id}).fetchone()
    total_registros = result[0] if result else 0
    total_paginas = math.ceil(total_registros / registros_por_pagina)
    
    # Si la página solicitada es mayor que el total de páginas, redireccionamos a la última página
    if pagina > total_paginas and total_paginas > 0:
        return redirect(f'/analisis-similitud/{tematica_id}?pagina={total_paginas}')
    
    # Calculamos el offset para la paginación
    offset = (pagina - 1) * registros_por_pagina
    
    # Consulta paginada
    sql_query = text("""
        SELECT
            p.id,
            p.name AS nombre_proyecto,
            COUNT(DISTINCT rf.user_id) AS num_integrantes,
            
            -- Se usa COALESCE para mostrar 0 si un proyecto no tiene similitudes
            COALESCE(sc.count_integrantes_con_similitud, 0) AS integrantes_con_similitud,
            
            -- Se mantiene la lógica del CASE, que ahora opera sobre el LEFT JOIN principal
            CASE
                WHEN COUNT(cs.id) = 0 THEN '❌' -- No hay análisis si no hay registros en comparacion_similitud
                WHEN MIN(cs.status_analisis) = 0 THEN '❌' -- Algún análisis está pendiente
                ELSE '✅' -- Todos los análisis están completos
            END AS analizado
            
        FROM project p
        JOIN reportes_finales rf ON rf.project_id = p.id
        LEFT JOIN comparacion_similitud cs ON cs.project_id = p.id
        
        -- Subconsulta en el FROM (tabla derivada) para precalcular los conteos de similitud
        LEFT JOIN (
            SELECT
                project_id,
                COUNT(DISTINCT user_id_similitud) AS count_integrantes_con_similitud
            FROM (
                SELECT project_id, usuario_1_id AS user_id_similitud
                FROM comparacion_similitud
                WHERE similitud_detectada = 1
                
                UNION -- UNION ya obtiene valores únicos de (project_id, user_id_similitud)
                
                SELECT project_id, usuario_2_id AS user_id_similitud
                FROM comparacion_similitud
                WHERE similitud_detectada = 1
            ) AS all_users_with_similarity
            GROUP BY project_id
        ) AS sc ON sc.project_id = p.id

        WHERE p.id_thematic = :tematica_id
        -- Agrupar por todas las columnas no agregadas del SELECT principal
        GROUP BY p.id, p.name, sc.count_integrantes_con_similitud
        ORDER BY p.id -- Añadir un ORDER BY para resultados consistentes en la paginación
        LIMIT :limit OFFSET :offset
    """)
    
    proyectos = db.session.execute(
        sql_query, 
        {
            "tematica_id": tematica_id,
            "limit": registros_por_pagina,
            "offset": offset
        }
    ).fetchall()
    
    return render_template('AnalisisSimilitud.html', 
                            tematicas=tematicas, 
                            proyectos=proyectos,
                            tematica_actual=tematica_id,
                            pagina_actual=pagina,
                            total_paginas=total_paginas)

@analisis.route('/proyecto/<int:proyecto_id>/analisis')
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
            '\n vs \n',
            u2.name, ' ', u2.falastname, ' ', u2.molastname
        ) AS usuarios_analizados,

        -- Campos de comparacion_similitud
        cs1.introduccion      AS intro_cs1,
        cs1.marcoteorico      AS marco_cs1,
        cs1.metodo            AS metodo_cs1,
        cs1.resultados        AS res_cs1,
        cs1.discusion         AS disc_cs1,
        cs1.conclusiones      AS concl_cs1,
        cs1.secciones_similares AS secs_cs1,
        cs1.status_analisis as status_cs1,

        -- Campos de comparacion_similitud2
        cs2.introduccion      AS intro_cs2,
        cs2.marcoteorico      AS marco_cs2,
        cs2.metodo            AS metodo_cs2,
        cs2.resultados        AS res_cs2,
        cs2.discusion         AS disc_cs2,
        cs2.conclusiones      AS concl_cs2,
        cs2.secciones_similares AS secs_cs2,
        cs2.status_analisis as status_cs2

    FROM comparacion_similitud  cs1
    JOIN comparacion_similitud2 cs2
    ON cs1.project_id    = cs2.project_id
    AND cs1.usuario_1_id  = cs2.usuario_1_id
    AND cs1.usuario_2_id  = cs2.usuario_2_id

    JOIN `user` u1
    ON cs1.usuario_1_id = u1.id
    JOIN `user` u2
    ON cs1.usuario_2_id = u2.id

    WHERE cs1.project_id = :proyecto_id
    ORDER BY cs1.id;
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
                            tolerancias=tolerancias,
                            tipo_analisis="sintactico")

@analisis.route('/proyecto/<int:proyecto_id>/analisis-semantico')
def mostrar_detalles_proyecto_semantico(proyecto_id):
    sql_proyecto = text("SELECT name FROM project WHERE id = :proyecto_id")
    proyecto_db_row = db.session.execute(sql_proyecto, {"proyecto_id": proyecto_id}).fetchone()
    if not proyecto_db_row:
        flash(f"Proyecto con ID {proyecto_id} no encontrado.", "warning")
        return redirect(url_for('analisis.mostrar_tematicas_base'))
        
    # Asumiendo que 'comparacion_similitud2' es tu tabla para análisis semántico
    sql_detalles_semantico = text("""
        SELECT
            CONCAT(u1.name, ' ', u1.falastname, ' ', u1.molastname,
                    ' (ID: ', u1.id, ')',
                    '\nvs\n',
                    u2.name, ' ', u2.falastname, ' ', u2.molastname,
                    ' (ID: ', u2.id, ')') AS usuarios_analizados,
            cs.introduccion, cs.marcoteorico, cs.metodo, cs.resultados,
            cs.discusion, cs.conclusiones, cs.secciones_similares, cs.status_analisis
        FROM comparacion_similitud2 cs 
        JOIN user u1 ON cs.usuario_1_id = u1.id
        JOIN user u2 ON cs.usuario_2_id = u2.id
        WHERE cs.project_id = :proyecto_id
        ORDER BY cs.id
    """)
    detalles = db.session.execute(sql_detalles_semantico, {"proyecto_id": proyecto_id}).fetchall()
    tolerancias_db = ToleranciasPorcentajes.query.all()
    tolerancias_dict = {t.seccion.strip().lower(): t.tolerancia for t in tolerancias_db}

    return render_template('Detalles_Proyectos.html', 
                            proyecto=proyecto_db_row,
                            proyecto_id=proyecto_id,
                            detalles=detalles,
                            tolerancias=tolerancias_dict,
                            tipo_analisis="semantico")


@analisis.route('/iniciar-analisis-global-sintactico', methods=['POST'])
def iniciar_analisis_global_sintactico_route():
    """
    Ruta para iniciar el análisis de similitud para todos los proyectos.
    """
    current_app.logger.info("Solicitud POST recibida en /iniciar-analisis-global")
    try:
        # En producción, considera tareas en segundo plano (Celery, RQ) para no bloquear.
        resultado_analisis = analizar_todos_los_proyectos_service()
        current_app.logger.info(f"Resultado del análisis global: {resultado_analisis}")
        
        if resultado_analisis.get("estado") == "error":
            return jsonify(resultado_analisis), 500 
        return jsonify(resultado_analisis), 200
        
    except Exception as e:
        current_app.logger.error(f"Excepción no controlada en iniciar_analisis_global_route: {str(e)}", exc_info=True)
        return jsonify({"estado": "error", "mensaje": "Error inesperado en el servidor al procesar la solicitud."}), 500
    
@analisis.route('/iniciar-analisis-global-semantico', methods=['POST'])
def iniciar_analisis_global_semantico_route():
    current_app.logger.info("Solicitud POST recibida en /iniciar-analisis-global-semantico")
    try:
        # Llama a la función de servicio para el análisis semántico global
        resultado_analisis = analizar_todos_los_proyectos_semantico_service() 
        current_app.logger.info(f"Resultado del análisis SEMÁNTICO global: {resultado_analisis}")
        
        if resultado_analisis.get("estado") == "error":
            return jsonify(resultado_analisis), 500 # Error interno del servidor
        
        return jsonify(resultado_analisis), 200 # Éxito
        
    except Exception as e:
        current_app.logger.error(f"Excepción no controlada en iniciar_analisis_global_semantico_route: {str(e)}", exc_info=True)
        return jsonify({"estado": "error", "mensaje": "Error inesperado en el servidor al procesar la solicitud de análisis semántico."}), 500

@analisis.route('/iniciar-analisis-individual-sintactico/<int:proyecto_id>', methods=['POST'])
def iniciar_analisis_individual_sintactico_route(proyecto_id):
    """
    Ruta para iniciar el análisis de un proyecto específico.
    Llamada por el botón "Analizar" de la tabla.
    """
    current_app.logger.info(f"Solicitud POST recibida en /iniciar-analisis/{proyecto_id}")
    try:
        tolerancias = obtener_tolerancias() 
        if tolerancias is None:
            current_app.logger.error(f"No se pudieron obtener tolerancias para el análisis individual del proyecto {proyecto_id}")
            flash("Error crítico: No se pudieron obtener las configuraciones de tolerancia. El análisis no pudo iniciar.", "danger")
            return redirect(request.referrer or url_for('analisis.mostrar_tematicas_base'))

        analizar_proyecto_individual_service(proyecto_id, tolerancias) 
        
        flash(f"Análisis para el proyecto ID {proyecto_id} ha sido procesado. Revisa los detalles o la tabla para ver el estado actualizado.", "success")
        current_app.logger.info(f"Análisis para el proyecto {proyecto_id} procesado.")
        
        # Redirigir a la página anterior para que el usuario vea la tabla actualizada (potencialmente)
        # o los mensajes flash.
        return redirect(request.referrer or url_for('analisis.mostrar_proyectos_por_tematica', tematica_id=request.args.get('tematica_actual', 1))) # Asume que tematica_actual podría estar en args o usa un default

    except Exception as e:
        current_app.logger.error(f"Error en análisis individual del proyecto {proyecto_id}: {str(e)}", exc_info=True)
        flash(f"Error al procesar el análisis del proyecto {proyecto_id}. Detalles: {str(e)}", "danger")
        return redirect(request.referrer or url_for('analisis.mostrar_tematicas_base'))

# --- NUEVA RUTA PARA FILTRAR REPORTES ---
@analisis.route('/filtrar-reportes', methods=['POST'])
def filtrar_reportes_route():
    """
    Endpoint de la API para iniciar el proceso de filtrado de reportes.
    """
    current_app.logger.info("Solicitud POST recibida en /filtrar-reportes")
    try:
        # Llama a la función de servicio que hace el trabajo pesado
        resultado = filtrar_y_guardar_reportes_service()
        
        if resultado.get("status") == "error":
            # Si el servicio reportó un error, devolverlo con un código de error del servidor
            return jsonify(resultado), 500
        
        # Si todo fue bien, devolver el resultado con un código de éxito
        return jsonify(resultado), 200
        
    except Exception as e:
        current_app.logger.error(f"Excepción no controlada en filtrar_reportes_route: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": "Error inesperado en el servidor al procesar la solicitud de filtrado."}), 500
    
@analisis.route('/iniciar-analisis-completo-stream')
def analisis_completo_stream():
    """
    Endpoint que transmite el progreso del análisis completo (sintáctico, semántico y filtro)
    usando Server-Sent Events.
    """
    current_app.logger.info("Cliente conectado a /iniciar-analisis-completo-stream")
    
    # 1. Obtener la instancia de la aplicación actual DENTRO de la ruta
    #    donde el contexto de la aplicación está activo.

    ngram_value = request.args.get('ngram', default=1, type=int)
    current_app.logger.info(f"Análisis solicitado con n-gramas de tamaño: {ngram_value}")

    app_instance = current_app._get_current_object()
    
    # 2. Pasar la instancia de la aplicación al generador.
    #    Esta es la línea que soluciona el TypeError.
    return Response(realizar_analisis_completo_sse(app_instance, ngram_value=ngram_value), mimetype='text/event-stream')
