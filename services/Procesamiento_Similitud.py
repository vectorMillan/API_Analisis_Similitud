import spacy
import pandas as pd
from sqlalchemy import or_, distinct # distinct para obtener project_id únicos
from datetime import datetime
from itertools import combinations 
import time # Para la temporización

# Importaciones de Scikit-learn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Modelos y DB
from models.Reportes_Finales import ReportesFinales
from models.Tolerancia_Porcentajes import ToleranciasPorcentajes
from models.Comparacion_Similitud import ComparacionSimilitud
# Asegúrate que tu modelo Project (si existe) o el modelo que contiene los IDs de proyecto esté importado.
# Si no hay un modelo Project, obtendremos los IDs de ReportesFinales.
# from models.Project import Project # Ejemplo si tuvieras un modelo Project
from config.config import db

# --- Carga del modelo spaCy ---
try:
    nlp = spacy.load("es_core_news_md")
except OSError:
    print("Modelo 'es_core_news_md' no encontrado. "
        "Por favor, descárgalo ejecutando: python -m spacy download es_core_news_md")
    nlp = None
    # En una app Flask real, esto podría ser un error crítico.
    # Considerar usar current_app.logger.critical() y posiblemente detener la app.

# --- Función de preprocesamiento ---
def preprocesar_texto(texto):
    if not nlp:
        print("Error: El modelo de spaCy 'es_core_news_md' no está cargado.")
        # from flask import current_app
        # current_app.logger.error("El modelo de spaCy 'es_core_news_md' no está cargado.")
        return "" 
    if pd.isna(texto) or not texto:
        return ""
    doc = nlp(str(texto))
    lemas = [token.lemma_.lower() for token in doc if not token.is_stop and not token.is_punct and token.lemma_.strip()]
    return " ".join(lemas)

# --- Función para obtener tolerancias ---
def obtener_tolerancias():
    try:
        registros_tolerancia = ToleranciasPorcentajes.query.all()
        tolerancias_dict = {}
        for registro in registros_tolerancia:
            seccion_normalizada = registro.seccion.strip().lower()
            tolerancias_dict[seccion_normalizada] = registro.tolerancia
        if not tolerancias_dict:
            print("Advertencia: No se encontraron registros de tolerancia en la base de datos.")
            # from flask import current_app
            # current_app.logger.warning("No se encontraron registros de tolerancia en la base de datos.")
        return tolerancias_dict
    except Exception as e:
        print(f"Error obteniendo tolerancias desde la base de datos: {str(e)}")
        # from flask import current_app
        # current_app.logger.error(f"Error obteniendo tolerancias desde la base de datos: {str(e)}")
        return None

# --- Función para insertar o actualizar comparación ---
def insertar_o_actualizar_comparacion(usuario_1_id, usuario_2_id, project_id, similitudes_dict, secciones_similares_count):
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

        registro_existente = ComparacionSimilitud.query.filter(
            ComparacionSimilitud.project_id == proj_id,
            ComparacionSimilitud.usuario_1_id == id_menor,
            ComparacionSimilitud.usuario_2_id == id_mayor
        ).first()

        if registro_existente:
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
            # db.session.add(registro_existente) # No es estrictamente necesario para objetos ya en sesión
            print(f"Actualizada la comparación (Usuarios: {u1_id}, {u2_id}; Proyecto: {proj_id}).")
        else:
            nuevo_registro = ComparacionSimilitud(
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
            print(f"Guardada nueva comparación (Usuarios: {u1_id}, {u2_id}; Proyecto: {proj_id}).")
            
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error al interactuar con comparacion_similitud DB: {e}")
        # from flask import current_app
        # current_app.logger.error(f"Error al interactuar con comparacion_similitud DB: {e}")
        import traceback
        traceback.print_exc()

# --- Función para analizar un proyecto individual ---
def analizar_proyecto(project_id_param, tolerancias): # Pasamos tolerancias como argumento
    """
    Analiza la similitud de los reportes dentro de un proyecto dado.
    Tolerancias se obtienen una vez y se pasan para evitar consultas repetidas.
    """
    print(f"Iniciando análisis para el proyecto ID: {project_id_param}")
    # Las tolerancias ahora se pasan como argumento, no se obtienen aquí.
    # if tolerancias is None:
    #     print(f"Error crítico: No se pudieron obtener las tolerancias para el proyecto {project_id_param}.")
    #     return

    reportes_del_proyecto = ReportesFinales.query.filter_by(project_id=project_id_param).all()

    if not reportes_del_proyecto:
        print(f"No se encontraron reportes para el proyecto {project_id_param}. No se realizará análisis.")
        return

    reportes_por_usuario = {}
    for reporte in reportes_del_proyecto:
        if reporte.user_id not in reportes_por_usuario: # Tomar el primer reporte por usuario
            reportes_por_usuario[reporte.user_id] = reporte
    
    lista_usuarios_con_reporte = list(reportes_por_usuario.keys())
    print(f"Usuarios con reportes en el proyecto {project_id_param}: {len(lista_usuarios_con_reporte)}. IDs: {lista_usuarios_con_reporte}")
    columnas_secciones = ['introduccion', 'marcoteorico', 'metodo', 'resultados', 'discusion', 'conclusiones']

    if len(lista_usuarios_con_reporte) <= 1:
        if len(lista_usuarios_con_reporte) == 1:
            user_id = lista_usuarios_con_reporte[0]
            print(f"El proyecto {project_id_param} tiene solo un integrante ({user_id}). Registrando con 0% de similitud.")
            similitudes_vacias = {col: 0.0 for col in columnas_secciones}
            insertar_o_actualizar_comparacion(
                usuario_1_id=user_id,
                usuario_2_id=0, 
                project_id=project_id_param,
                similitudes_dict=similitudes_vacias,
                secciones_similares_count=0
            )
        else:
            print(f"No hay usuarios con reportes en el proyecto {project_id_param}. No se creará ningún registro de comparación.")
        return

    pares_de_usuarios = list(combinations(lista_usuarios_con_reporte, 2))
    print(f"Se analizarán {len(pares_de_usuarios)} pares de usuarios para el proyecto {project_id_param}.")

    for user1_id, user2_id in pares_de_usuarios:
        reporte_user1 = reportes_por_usuario[user1_id]
        reporte_user2 = reportes_por_usuario[user2_id]
        similitudes_calculadas = {}
        secciones_con_similitud_alta = 0
        print(f"\nComparando Usuario {user1_id} vs Usuario {user2_id} para proyecto {project_id_param}")

        for seccion_nombre in columnas_secciones:
            texto1 = preprocesar_texto(getattr(reporte_user1, seccion_nombre, ""))
            texto2 = preprocesar_texto(getattr(reporte_user2, seccion_nombre, ""))
            similitud_actual = 0.0
            if texto1 and texto2: 
                try:
                    vectorizador = TfidfVectorizer()
                    vectores = vectorizador.fit_transform([texto1, texto2])
                    if vectores.shape[1] > 0:
                        similitud_actual = cosine_similarity(vectores[0:1], vectores[1:2])[0][0]
                    else:
                        similitud_actual = 0.0 
                except ValueError:
                    similitud_actual = 0.0
                    print(f"  Advertencia: ValueError al calcular similitud para la sección '{seccion_nombre}'.")
            similitud_actual = round(similitud_actual, 4)
            similitudes_calculadas[seccion_nombre] = similitud_actual
            nombre_seccion_normalizado = seccion_nombre.lower().strip()
            umbral_tolerancia = tolerancias.get(nombre_seccion_normalizado, 0.0)
            if nombre_seccion_normalizado not in tolerancias:
                print(f"  Advertencia: No existe config de tolerancia para '{nombre_seccion_normalizado}'. Usando umbral 0.0.")
            if similitud_actual > umbral_tolerancia:
                secciones_con_similitud_alta += 1
            print(f"  Sección '{seccion_nombre}': Similitud = {similitud_actual*100:.2f}%, Umbral = {umbral_tolerancia*100:.2f}%")
        print(f"  Total secciones con similitud por encima del umbral: {secciones_con_similitud_alta}")
        insertar_o_actualizar_comparacion(
            usuario_1_id=user1_id,
            usuario_2_id=user2_id,
            project_id=project_id_param,
            similitudes_dict=similitudes_calculadas,
            secciones_similares_count=secciones_con_similitud_alta
        )
    print(f"Análisis completado para el proyecto ID: {project_id_param}")


# --- Nueva función para analizar todos los proyectos (adaptada) ---
def analizar_todos_los_proyectos_service():
    """
    Analiza todos los proyectos que tienen reportes finales.
    Retorna estadísticas del análisis.
    """
    # from flask import current_app # Para logging en Flask

    print("Iniciando el análisis de todos los proyectos...")
    # current_app.logger.info("Iniciando el análisis de todos los proyectos...")

    # Obtener tolerancias una sola vez al inicio
    tolerancias = obtener_tolerancias()
    if tolerancias is None:
        msg = "Error crítico: No se pudieron obtener las tolerancias generales. Abortando análisis global."
        print(msg)
        # current_app.logger.error(msg)
        return {"estado": "error", "mensaje": msg, "proyectos_analizados": 0, "tiempo_total": 0}

    try:
        # Obtener todos los IDs de proyectos únicos desde la tabla de reportes finales
        # Esto asume que si un proyecto existe, tiene al menos un reporte final.
        # Si tienes una tabla 'Project' separada, sería mejor obtener los IDs de ahí.
        query_proyectos = db.session.query(distinct(ReportesFinales.project_id)).all()
        project_ids = [pid[0] for pid in query_proyectos if pid[0] is not None]
        
        total_proyectos_encontrados = len(project_ids)
        
        if not project_ids:
            msg = "No se encontraron proyectos con reportes para analizar."
            print(msg)
            # current_app.logger.info(msg)
            return {"estado": "completado", "mensaje": msg, "proyectos_analizados": 0, "tiempo_total": 0}

        print(f"Se encontraron {total_proyectos_encontrados} proyectos únicos con reportes para analizar.")
        # current_app.logger.info(f"Se encontraron {total_proyectos_encontrados} proyectos para analizar.")
            
        tiempo_inicio_total = time.time()
        proyectos_procesados_count = 0
        
        # No usaremos tqdm aquí, el progreso se manejaría en el frontend si es asíncrono.
        # Por ahora, esto es síncrono y los prints van al log del servidor.
        for i, project_id in enumerate(project_ids, 1):
            print(f"\n{'=' * 40}")
            print(f"Procesando proyecto {i}/{total_proyectos_encontrados}: ID {project_id}")
            # current_app.logger.info(f"Procesando proyecto {i}/{total_proyectos_encontrados}: ID {project_id}")
            print(f"{'=' * 40}\n")
            
            analizar_proyecto(project_id, tolerancias) # Pasar las tolerancias obtenidas
            proyectos_procesados_count +=1
            
            # Aquí podrías emitir un evento de progreso si usaras SSE o WebSockets
            # Ejemplo: emit_event('progress_update', {'current': i, 'total': total_proyectos_encontrados, 'project_id': project_id})

        tiempo_total_segundos = time.time() - tiempo_inicio_total
        
        # Formato de tiempo total
        horas, resto = divmod(tiempo_total_segundos, 3600)
        minutos, segundos = divmod(resto, 60)
        tiempo_total_formateado = f"{int(horas)}h {int(minutos)}m {int(segundos)}s"

        msg_final = (f"Análisis de todos los proyectos ({proyectos_procesados_count}) completado. "
                    f"Tiempo total: {tiempo_total_formateado}")
        print(msg_final)
        # current_app.logger.info(msg_final)
        
        return {
            "estado": "completado",
            "mensaje": msg_final,
            "proyectos_analizados": proyectos_procesados_count,
            "tiempo_total_segundos": round(tiempo_total_segundos, 2),
            "tiempo_total_formateado": tiempo_total_formateado
        }

    except Exception as e:
        error_msg = f"Error durante el análisis de todos los proyectos: {str(e)}"
        print(error_msg)
        # current_app.logger.error(error_msg)
        import traceback
        traceback.print_exc() # Para log detallado del error en el servidor
        return {"estado": "error", "mensaje": error_msg, "proyectos_analizados": proyectos_procesados_count if 'proyectos_procesados_count' in locals() else 0, "tiempo_total": 0}