# services/Procesamiento_Completo.py

import json
import time
import traceback
from flask import current_app

# Importar las funciones de servicio de los otros módulos
from services.Procesamiento_Similitud import analizar_todos_los_proyectos_service as analizar_sintactico
from services.Procesamiento_Semantico import analizar_todos_los_proyectos_semantico_service as analizar_semantico
from services.Procesamiento_Filtro import filtrar_y_guardar_reportes_service as filtrar_reportes

def format_sse_event(data):
    """Formatea un diccionario como un evento SSE."""
    return f"data: {json.dumps(data)}\n\n"

def realizar_analisis_completo_sse(app):
    """
    Generador que orquesta la ejecución secuencial de todos los análisis
    y envía eventos de progreso (SSE) al cliente.
    
    Recibe la instancia de la aplicación Flask para crear su propio contexto.
    """
    # Usar la instancia de la aplicación pasada como argumento para crear el contexto.
    with app.app_context():
        total_pasos = 3
        try:
            # --- PASO 0: INICIO ---
            yield format_sse_event({
                "paso_actual": 0, "total_pasos": total_pasos, "estado": "iniciando",
                "mensaje": "Iniciando proceso de análisis completo..."
            })
            time.sleep(1)

            # --- PASO 1: ANÁLISIS SINTÁCTICO ---
            yield format_sse_event({
                "paso_actual": 1, "total_pasos": total_pasos, "estado": "procesando",
                "mensaje": "Paso 1/3: Ejecutando análisis SINTÁCTICO de todos los proyectos..."
            })
            resultado_sintactico = analizar_sintactico()
            # Asumiendo que tus servicios devuelven 'estado' para errores
            if resultado_sintactico.get("estado") == "error":
                raise Exception(f"Falló el análisis sintáctico: {resultado_sintactico.get('mensaje')}")
            
            yield format_sse_event({
                "paso_actual": 1, "total_pasos": total_pasos, "estado": "paso_completado",
                "mensaje": f"Paso 1/3 completado. {resultado_sintactico.get('mensaje', 'Análisis sintáctico finalizado.')}"
            })
            time.sleep(1)

            # --- PASO 2: ANÁLISIS SEMÁNTICO ---
            yield format_sse_event({
                "paso_actual": 2, "total_pasos": total_pasos, "estado": "procesando",
                "mensaje": "Paso 2/3: Ejecutando análisis SEMÁNTICO de todos los proyectos..."
            })
            resultado_semantico = analizar_semantico()
            if resultado_semantico.get("estado") == "error":
                raise Exception(f"Falló el análisis semántico: {resultado_semantico.get('mensaje')}")
            
            yield format_sse_event({
                "paso_actual": 2, "total_pasos": total_pasos, "estado": "paso_completado",
                "mensaje": f"Paso 2/3 completado. {resultado_semantico.get('mensaje', 'Análisis semántico finalizado.')}"
            })
            time.sleep(1)

            # --- PASO 3: FILTRADO DE REPORTES ---
            yield format_sse_event({
                "paso_actual": 3, "total_pasos": total_pasos, "estado": "procesando",
                "mensaje": "Paso 3/3: Filtrando reportes sin similitudes..."
            })
            resultado_filtro = filtrar_reportes()
            # Asumiendo que el servicio de filtro devuelve 'status' para errores
            if resultado_filtro.get("status") == "error":
                raise Exception(f"Falló el filtrado de reportes: {resultado_filtro.get('message')}")
            
            yield format_sse_event({
                "paso_actual": 3, "total_pasos": total_pasos, "estado": "paso_completado",
                "mensaje": f"Paso 3/3 completado. {resultado_filtro.get('message', 'Filtrado de reportes finalizado.')}"
            })
            time.sleep(1)

            # --- FINALIZACIÓN ---
            yield format_sse_event({
                "paso_actual": 3, "total_pasos": total_pasos, "estado": "finalizado",
                "mensaje": "¡Proceso de análisis completo finalizado con éxito!"
            })

        except Exception as e:
            error_message = f"Error durante el proceso de análisis: {str(e)}"
            current_app.logger.error(error_message, exc_info=True)
            traceback.print_exc()
            yield format_sse_event({
                "paso_actual": 0, "total_pasos": total_pasos, "estado": "error_fatal",
                "mensaje": error_message
            })
        finally:
            current_app.logger.info("Flujo de análisis completo finalizado.")
