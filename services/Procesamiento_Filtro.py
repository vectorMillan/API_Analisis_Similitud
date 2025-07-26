from sqlalchemy import text
from config.config import db
import traceback

def filtrar_y_guardar_reportes_service():
    """
    Filtra los reportes de usuarios sin similitudes detectadas desde 'reportes_finales'
    y los guarda en 'reportes_finales_analisis'.
    
    La operación consiste en dos pasos:
    1. Vaciar la tabla de destino ('reportes_finales_analisis') para empezar de cero.
    2. Insertar los nuevos registros filtrados.
    
    Retorna un diccionario con el estado de la operación.
    """
    # from flask import current_app # Descomentar para usar el logger de Flask

    # Consulta para vaciar la tabla de destino.
    # Esto asegura que cada vez que se filtra, se obtiene un conjunto de datos fresco.
    sql_delete_query = text("DELETE FROM reportes_finales_analisis;")

    # Consulta para seleccionar los reportes de usuarios "limpios" e insertarlos.
    # Nota: Se ha simplificado la subconsulta 'WHERE' para mayor claridad y eficiencia.
    sql_insert_query = text("""
        INSERT INTO reportes_finales_analisis (
            id, user_id, project_id, thematic_id, subtematica_id, introduccion,
            marcoteorico, metodo, resultados, discusion, conclusiones,
            nombre_reporte, revisor_id, status, calificacion_final, created_at, updated_at
        )
        SELECT
            rf.id, rf.user_id, rf.project_id, rf.thematic_id, rf.subtematica_id, rf.introduccion,
            rf.marcoteorico, rf.metodo, rf.resultados, rf.discusion, rf.conclusiones,
            rf.nombre_reporte,
            0, -- Valor fijo para revisor_id
            0, -- Valor fijo para status
            0, -- Valor fijo para calificacion_final
            rf.created_at, 
            rf.updated_at
        FROM reportes_finales rf
        WHERE rf.user_id NOT IN (
            -- Subconsulta para obtener todos los IDs de usuarios con similitud detectada
            SELECT usuario_1_id FROM comparacion_similitud WHERE similitud_detectada = 1
            UNION
            SELECT usuario_2_id FROM comparacion_similitud WHERE similitud_detectada = 1
        );
    """)
    
    try:
        # Usar db.session.execute para ejecutar las consultas
        with db.session.begin(): # Usar una transacción para asegurar que ambas operaciones se completen o ninguna
            # Paso 1: Vaciar la tabla
            db.session.execute(sql_delete_query)
            print("Tabla 'reportes_finales_analisis' vaciada correctamente.")
            # current_app.logger.info("Tabla 'reportes_finales_analisis' vaciada.")

            # Paso 2: Insertar los nuevos datos filtrados
            result = db.session.execute(sql_insert_query)
        
        # db.session.commit() # No es necesario si se usa with db.session.begin()
        
        message = f"¡Éxito! Se filtraron e insertaron {result.rowcount} reportes en la tabla de análisis."
        print(message)
        # current_app.logger.info(message)
        
        return {"status": "success", "message": message, "rows_affected": result.rowcount}

    except Exception as e:
        db.session.rollback() # Revertir cambios en caso de error
        error_message = f"Ocurrió un error durante la operación de filtrado: {e}"
        print(error_message)
        traceback.print_exc()
        # current_app.logger.error(error_message, exc_info=True)
        return {"status": "error", "message": error_message}