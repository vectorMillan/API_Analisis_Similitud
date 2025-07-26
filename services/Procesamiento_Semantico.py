import pandas as pd
import spacy
import numpy as np
from itertools import combinations
from sentence_transformers import SentenceTransformer, util as sentence_util
import time
import traceback
from sqlalchemy import or_, distinct # distinct para obtener project_id únicos
from datetime import datetime

# Modelos de la base de datos
from models.Reportes_Finales import ReportesFinales
from models.Tolerancia_Porcentajes import ToleranciasPorcentajes
from models.Comparacion_Similitud2 import ComparacionSimilitud as ComparacionSimilitudSemantica 
from config.config import db

# Carga de modelos NLP
print("Cargando modelo spaCy 'es_core_news_md' para análisis semántico (si es necesario para preprocesamiento)...")
try:
    nlp_spacy = spacy.load("es_core_news_md")
    print("Modelo spaCy 'es_core_news_md' cargado exitosamente.")
except OSError:
    print("Error: Modelo de spaCy 'es_core_news_md' no encontrado. "
        "Por favor, descárgalo ejecutando: python -m spacy download es_core_news_md")
    nlp_spacy = None

print("Cargando modelo SentenceTransformer 'paraphrase-multilingual-MiniLM-L12-v2' para análisis semántico...")
try:
    model_sentence_transformer = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    print("Modelo SentenceTransformer 'paraphrase-multilingual-MiniLM-L12-v2' cargado exitosamente.")
except Exception as e:
    print(f"Error cargando el modelo SentenceTransformer 'paraphrase-multilingual-MiniLM-L12-v2': {e}")
    traceback.print_exc()
    model_sentence_transformer = None

def obtener_tolerancias_semantico():
    try:
        registros_tolerancia = ToleranciasPorcentajes.query.all()
        tolerancias_dict = {}
        for registro in registros_tolerancia:
            seccion_normalizada = registro.seccion.strip().lower()
            tolerancias_dict[seccion_normalizada] = registro.tolerancia
        if not tolerancias_dict:
            print("Advertencia (Semántico): No se encontraron registros de tolerancia en la base de datos.")
        return tolerancias_dict
    except Exception as e:
        print(f"Error obteniendo tolerancias (Semántico) desde la base de datos: {str(e)}")
        traceback.print_exc()
        return None

def insertar_o_actualizar_comparacion_semantica(usuario_1_id, usuario_2_id, project_id, 
                                            similitudes_dict, secciones_similares_count):
    """
    Inserta o actualiza un registro de comparación de similitud semántica
    en la tabla 'comparacion_similitud2'.
    """
    # from flask import current_app # Para logging
    try:
        u1_id = int(usuario_1_id)
        u2_id = int(usuario_2_id)
        proj_id = int(project_id)
        num_secciones_similares = int(secciones_similares_count)

        sim_introduccion = float(similitudes_dict.get('introduccion', 0.0))
        sim_marcoteorico = float(similitudes_dict.get('marcoteorico', 0.0))
        sim_metodo = float(similitudes_dict.get('metodo', 0.0))
        sim_resultados = float(similitudes_dict.get('resultados', 0.0))
        sim_discusion = float(similitudes_dict.get('discusion', 0.0))
        sim_conclusiones = float(similitudes_dict.get('conclusiones', 0.0))
        similitud_detectada_flag = 1 if num_secciones_similares > 0 else 0
        
        if u2_id == 0: 
            id_menor = u1_id
            id_mayor = 0 
        else:
            id_menor = min(u1_id, u2_id)
            id_mayor = max(u1_id, u2_id)

        registro_existente = ComparacionSimilitudSemantica.query.filter(
            ComparacionSimilitudSemantica.project_id == proj_id,
            ComparacionSimilitudSemantica.usuario_1_id == id_menor,
            ComparacionSimilitudSemantica.usuario_2_id == id_mayor
        ).first()

        if registro_existente:
            print(f"Actualizando registro semántico existente para proyecto {proj_id}, usuarios ({u1_id}, {u2_id}) -> normalizados ({id_menor}, {id_mayor})")
            registro_existente.introduccion = sim_introduccion
            registro_existente.marcoteorico = sim_marcoteorico
            registro_existente.metodo = sim_metodo
            registro_existente.resultados = sim_resultados
            registro_existente.discusion = sim_discusion
            registro_existente.conclusiones = sim_conclusiones
            registro_existente.secciones_similares = num_secciones_similares
            registro_existente.similitud_detectada = similitud_detectada_flag
            registro_existente.status_analisis = 1 
            registro_existente.updated_at = datetime.utcnow()
        else:
            print(f"Creando nuevo registro semántico para proyecto {proj_id}, usuarios ({u1_id}, {u2_id}) -> normalizados ({id_menor}, {id_mayor})")
            nuevo_registro = ComparacionSimilitudSemantica(
                usuario_1_id=id_menor,
                usuario_2_id=id_mayor,
                project_id=proj_id,
                introduccion=sim_introduccion,
                marcoteorico=sim_marcoteorico,
                metodo=sim_metodo,
                resultados=sim_resultados,
                discusion=sim_discusion,
                conclusiones=sim_conclusiones,
                secciones_similares=num_secciones_similares,
                similitud_detectada=similitud_detectada_flag,
                status_analisis=1
            )
            db.session.add(nuevo_registro)
            
        db.session.commit()
        print(f"Comparación semántica para proyecto {proj_id}, usuarios ({u1_id}, {u2_id}) guardada/actualizada.")

    except Exception as e:
        db.session.rollback()
        error_msg = f"Error al interactuar con la BD (comparacion_similitud2): {str(e)}"
        print(error_msg)
        traceback.print_exc()

def analizar_proyecto_semantico(project_id_param, tolerancias_externas=None):
    if not model_sentence_transformer:
        error_msg = "Error crítico (Semántico): El modelo SentenceTransformer no está cargado. Abortando análisis."
        print(error_msg)
        return {"status": "error_modelo", "message": error_msg}

    print(f"Iniciando análisis SEMÁNTICO para el proyecto ID: {project_id_param}")
    
    tolerancias = tolerancias_externas
    if tolerancias is None:
        print("Obteniendo tolerancias para análisis semántico individual...")
        tolerancias = obtener_tolerancias_semantico()

    if tolerancias is None: 
        error_msg = f"Error crítico (Semántico): No se pudieron obtener las tolerancias para el proyecto {project_id_param}. Abortando."
        print(error_msg)
        return {"status": "error_tolerancias", "message": error_msg}

    reportes_del_proyecto = ReportesFinales.query.filter_by(project_id=project_id_param).all()

    if not reportes_del_proyecto:
        msg = f"No se encontraron reportes para el proyecto {project_id_param} (análisis semántico)."
        print(msg)
        return {"status": "skip_no_reportes", "message": msg}

    reportes_por_usuario = {}
    for reporte in reportes_del_proyecto:
        if reporte.user_id not in reportes_por_usuario:
            reportes_por_usuario[reporte.user_id] = reporte
    
    lista_usuarios_con_reporte = list(reportes_por_usuario.keys())
    
    print(f"Usuarios con reportes en el proyecto {project_id_param} (Semántico): {len(lista_usuarios_con_reporte)}. IDs: {lista_usuarios_con_reporte}")

    columnas_secciones = ['introduccion', 'marcoteorico', 'metodo', 'resultados', 'discusion', 'conclusiones']

    if len(lista_usuarios_con_reporte) <= 1:
        if len(lista_usuarios_con_reporte) == 1:
            user_id = lista_usuarios_con_reporte[0]
            print(f"El proyecto {project_id_param} (Semántico) tiene solo un integrante ({user_id}). Registrando con 0% de similitud.")
            similitudes_vacias = {col: 0.0 for col in columnas_secciones}
            insertar_o_actualizar_comparacion_semantica(
                usuario_1_id=user_id,
                usuario_2_id=0, 
                project_id=project_id_param,
                similitudes_dict=similitudes_vacias,
                secciones_similares_count=0
            )
            return {"status": "single_user", "message": f"Proyecto {project_id_param} con un solo usuario."}
        else:
            msg = f"No hay usuarios con reportes en el proyecto {project_id_param} (Semántico)."
            print(msg)
            return {"status": "no_users", "message": msg}

    pares_de_usuarios = list(combinations(lista_usuarios_con_reporte, 2))
    print(f"Se analizarán {len(pares_de_usuarios)} pares de usuarios para el proyecto {project_id_param} (Semántico).")

    for user1_id, user2_id in pares_de_usuarios:
        reporte_user1 = reportes_por_usuario[user1_id]
        reporte_user2 = reportes_por_usuario[user2_id]
        
        similitudes_calculadas_semanticas = {}
        secciones_semanticas_similares_alta = 0
        
        print(f"\nComparando SEMÁNTICAMENTE Usuario {user1_id} vs Usuario {user2_id} para proyecto {project_id_param}")

        for seccion_nombre in columnas_secciones:
            texto1_crudo = getattr(reporte_user1, seccion_nombre, "")
            texto2_crudo = getattr(reporte_user2, seccion_nombre, "")
            
            similitud_semantica_actual = 0.0
            if texto1_crudo and texto1_crudo.strip() and texto2_crudo and texto2_crudo.strip():
                try:
                    embedding1 = model_sentence_transformer.encode(texto1_crudo, convert_to_tensor=True)
                    embedding2 = model_sentence_transformer.encode(texto2_crudo, convert_to_tensor=True)
                    cosine_scores = sentence_util.cos_sim(embedding1, embedding2)
                    similitud_semantica_actual = cosine_scores[0][0].item()
                except Exception as e_encode: 
                    similitud_semantica_actual = 0.0
                    print(f"  Advertencia (Semántico): Error al generar embeddings o calcular similitud para la sección '{seccion_nombre}'. Error: {e_encode}")
                    traceback.print_exc()
            else:
                print(f"  Info (Semántico): Uno o ambos textos para la sección '{seccion_nombre}' están vacíos. Similitud establecida a 0.0.")
                similitud_semantica_actual = 0.0

            similitud_semantica_actual = round(similitud_semantica_actual, 4)
            similitudes_calculadas_semanticas[seccion_nombre] = similitud_semantica_actual
            
            nombre_seccion_normalizado = seccion_nombre.lower().strip()
            umbral_tolerancia = tolerancias.get(nombre_seccion_normalizado, 0.0) 
            
            if nombre_seccion_normalizado not in tolerancias:
                print(f"  Advertencia (Semántico): No existe configuración de tolerancia para la sección '{nombre_seccion_normalizado}'. Usando umbral 0.0.")

            if similitud_semantica_actual > umbral_tolerancia:
                secciones_semanticas_similares_alta += 1
            
            print(f"  Sección '{seccion_nombre}' (Semántico): Similitud = {similitud_semantica_actual*100:.2f}%, Umbral = {umbral_tolerancia*100:.2f}%")

        print(f"  Total secciones con similitud semántica por encima del umbral para par ({user1_id} vs {user2_id}): {secciones_semanticas_similares_alta}")
        
        insertar_o_actualizar_comparacion_semantica(
            usuario_1_id=user1_id,
            usuario_2_id=user2_id,
            project_id=project_id_param,
            similitudes_dict=similitudes_calculadas_semanticas,
            secciones_similares_count=secciones_semanticas_similares_alta
        )
    
    msg_final_proyecto = f"Análisis SEMÁNTICO completado para el proyecto ID: {project_id_param}"
    print(msg_final_proyecto)
    return {"status": "success", "message": msg_final_proyecto}

# --- Nueva función para analizar todos los proyectos semánticamente (versión no-SSE) ---
def analizar_todos_los_proyectos_semantico_service():

    print("Iniciando el análisis SEMÁNTICO de todos los proyectos...")
    # current_app.logger.info("Iniciando el análisis SEMÁNTICO de todos los proyectos...")

    # Obtener tolerancias una sola vez al inicio
    tolerancias = obtener_tolerancias_semantico()
    if tolerancias is None:
        msg = "Error crítico (Semántico): No se pudieron obtener las tolerancias generales. Abortando análisis global."
        print(msg)
        # current_app.logger.error(msg)
        return {"estado": "error", "mensaje": msg, "proyectos_analizados": 0, "total_proyectos":0, "tiempo_total_segundos": 0, "tiempo_total_formateado": "0s"}

    try:
        # Obtener todos los IDs de proyectos únicos desde la tabla de reportes finales
        query_proyectos = db.session.query(distinct(ReportesFinales.project_id)).all()
        project_ids = [pid[0] for pid in query_proyectos if pid[0] is not None]
        
        total_proyectos_encontrados = len(project_ids)
        
        if not project_ids:
            msg = "No se encontraron proyectos con reportes para el análisis semántico."
            print(msg)
            # current_app.logger.info(msg)
            return {"estado": "completado_sin_proyectos", "mensaje": msg, "proyectos_analizados": 0, "total_proyectos":0, "tiempo_total_segundos": 0, "tiempo_total_formateado": "0s"}

        print(f"Se encontraron {total_proyectos_encontrados} proyectos únicos con reportes para el análisis SEMÁNTICO.")
            
        tiempo_inicio_total = time.time()
        proyectos_procesados_con_exito = 0
        proyectos_intentados = 0
        
        for i, project_id in enumerate(project_ids, 1):
            proyectos_intentados += 1
            print(f"\n{'=' * 40}")
            print(f"Procesando SEMÁNTICAMENTE proyecto {i}/{total_proyectos_encontrados}: ID {project_id}")
            # current_app.logger.info(f"Procesando SEMÁNTICAMENTE proyecto {i}/{total_proyectos_encontrados}: ID {project_id}")
            print(f"{'=' * 40}\n")
            
            resultado_proyecto = analizar_proyecto_semantico(project_id, tolerancias) # Pasar las tolerancias obtenidas
            
            if resultado_proyecto and resultado_proyecto.get("status") == "success":
                proyectos_procesados_con_exito +=1
            elif resultado_proyecto: # Loguear si hubo otro estado (skip, error_modelo, etc.)
                print(f"Resultado del análisis semántico para proyecto {project_id}: {resultado_proyecto.get('status')} - {resultado_proyecto.get('message')}")
            else:
                print(f"Análisis semántico para proyecto {project_id} no devolvió un resultado esperado.")


        tiempo_total_segundos = time.time() - tiempo_inicio_total
        
        # Formato de tiempo total
        horas, resto = divmod(tiempo_total_segundos, 3600)
        minutos, segundos_finales = divmod(resto, 60) # Renombrado para evitar conflicto con 'segundos' de json
        tiempo_total_formateado = f"{int(horas)}h {int(minutos)}m {int(segundos_finales)}s"

        msg_final = (f"Análisis SEMÁNTICO de todos los proyectos ({proyectos_intentados} intentados, {proyectos_procesados_con_exito} completados con éxito) finalizado. "
                    f"Tiempo total: {tiempo_total_formateado}")
        print(msg_final)
        # current_app.logger.info(msg_final)
        
        return {
            "estado": "completado",
            "mensaje": msg_final,
            "proyectos_analizados": proyectos_procesados_con_exito, # O proyectos_intentados, según se prefiera reportar
            "total_proyectos": total_proyectos_encontrados,
            "tiempo_total_segundos": round(tiempo_total_segundos, 2),
            "tiempo_total_formateado": tiempo_total_formateado
        }

    except Exception as e:
        error_msg = f"Error durante el análisis SEMÁNTICO de todos los proyectos: {str(e)}"
        print(error_msg)
        # current_app.logger.error(error_msg, exc_info=True)
        traceback.print_exc()
        return {"estado": "error", "mensaje": error_msg, 
                "proyectos_analizados": proyectos_procesados_con_exito if 'proyectos_procesados_con_exito' in locals() else 0, 
                "total_proyectos": total_proyectos_encontrados if 'total_proyectos_encontrados' in locals() else 0,
                "tiempo_total_segundos": 0, 
                "tiempo_total_formateado": "0s"}

