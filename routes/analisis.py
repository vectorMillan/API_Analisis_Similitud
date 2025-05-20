from flask import Blueprint, render_template, jsonify, request
import pandas as pd
from sqlalchemy import create_engine
import spacy
import time
from datetime import datetime
from itertools import combinations
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import threading
import json
from config.config import db

# Crear Blueprint
analisis = Blueprint('analisis', __name__)

# Variables globales para seguimiento del progreso
progreso_analisis = {
    'total_proyectos': 0,
    'proyectos_analizados': 0,
    'tiempo_inicio': None,
    'tiempo_fin': None,
    'en_progreso': False,
    'tiempos_proyecto': []
}

# Conexión a la base de datos
con = create_engine(f'mysql://root:1234@localhost/verano_cientifico')

# Cargar modelo de lenguaje
try:
    nlp = spacy.load("es_core_news_md")
except:
    print("Es necesario descargar el modelo de lenguaje español: python -m spacy download es_core_news_md")
    nlp = None

    # Función para preprocesar texto
def preprocesar_texto(texto):
    if pd.isna(texto):  # Manejar NaN
        return ""
    doc = nlp(str(texto))
    lemas = [token.lemma_.lower() for token in doc if not token.is_stop and not token.is_punct]
    return " ".join(lemas)

# Función para obtener tolerancias
def obtener_tolerancias():
    try:
        tolerancias_df = pd.read_sql("SELECT * FROM tolerancias_similitud", con)
        if tolerancias_df.empty:
            return {}
        
        # Convertir DataFrame a diccionario
        tolerancias = {}
        for _, row in tolerancias_df.iterrows():
            tolerancias[row['seccion']] = float(row['valor_tolerancia'])
        
        return tolerancias
    except Exception as e:
        print(f"Error al obtener tolerancias: {e}")
        return {}

# Función para insertar comparación de similitud
def insertar_comparacion_similitud(usuario_1_id, usuario_2_id, project_id, similitudes, secciones_similares):
    try:
        # Convertir a tipos nativos de Python
        usuario_1_id = int(usuario_1_id)
        usuario_2_id = int(usuario_2_id)
        project_id = int(project_id)
        secciones_similares = int(secciones_similares)
        
        # Convertir los valores de similitud a float
        for key in similitudes:
            similitudes[key] = float(similitudes[key])
        
        # Determinar si se detectó similitud (1 si hay al menos una sección similar, 0 si no)
        similitud_detectada = 1 if secciones_similares > 0 else 0
        
        # Verificar si ya existe una entrada para estos usuarios y proyecto
        query = f"""
        SELECT id FROM comparacion_similitud 
        WHERE usuario_1_id = {usuario_1_id} 
        AND usuario_2_id = {usuario_2_id} 
        AND project_id = {project_id}
        """
        
        # También verificar si existe con los usuarios en orden inverso
        query_inverso = f"""
        SELECT id FROM comparacion_similitud 
        WHERE usuario_1_id = {usuario_2_id} 
        AND usuario_2_id = {usuario_1_id} 
        AND project_id = {project_id}
        """
        
        # Ejecutar consultas
        resultado = pd.read_sql(query, con)
        resultado_inverso = pd.read_sql(query_inverso, con)
        
        # Preparar datos para inserción/actualización
        data = {
            'usuario_1_id': usuario_1_id,
            'usuario_2_id': usuario_2_id,
            'project_id': project_id,
            'introduccion': similitudes.get('introduccion', 0.0),
            'marcoteorico': similitudes.get('marcoteorico', 0.0),
            'metodo': similitudes.get('metodo', 0.0),
            'resultados': similitudes.get('resultados', 0.0),
            'discusion': similitudes.get('discusion', 0.0),
            'conclusiones': similitudes.get('conclusiones', 0.0),
            'secciones_similares': secciones_similares,
            'similitud_detectada': similitud_detectada,
            'status_analisis': 1  # Marcamos como analizado
        }
        
        # Si existe el registro (en cualquier orden de usuarios)
        if not resultado.empty:
            # Actualizar registro existente
            registro_id = int(resultado.iloc[0]['id'])  # Convertir a int nativo de Python
            
            # Usar text() para ejecutar SQL directamente con SQLAlchemy
            from sqlalchemy.sql import text
            
            # Construir consulta parametrizada - NOTE: No incluimos updated_at
            update_query = text("""
            UPDATE comparacion_similitud
            SET usuario_1_id = :usuario_1_id,
                usuario_2_id = :usuario_2_id,
                project_id = :project_id,
                introduccion = :introduccion,
                marcoteorico = :marcoteorico,
                metodo = :metodo,
                resultados = :resultados,
                discusion = :discusion,
                conclusiones = :conclusiones,
                secciones_similares = :secciones_similares,
                similitud_detectada = :similitud_detectada,
                status_analisis = :status_analisis
            WHERE id = :id
            """)
            
            # Añadir el ID al diccionario de datos
            data['id'] = registro_id
            
            # Ejecutar la actualización
            with con.connect() as connection:
                connection.execute(update_query, data)
                connection.commit()
            
        elif not resultado_inverso.empty:
            # Actualizar registro existente (con usuarios en orden inverso)
            registro_id = int(resultado_inverso.iloc[0]['id'])  # Convertir a int nativo de Python
            
            # Intercambiar usuario_1_id y usuario_2_id para mantener la coherencia
            data['usuario_1_id'] = usuario_2_id
            data['usuario_2_id'] = usuario_1_id
            
            # Usar text() para ejecutar SQL directamente con SQLAlchemy
            from sqlalchemy.sql import text
            
            # Construir consulta parametrizada - NOTE: No incluimos updated_at
            update_query = text("""
            UPDATE comparacion_similitud
            SET usuario_1_id = :usuario_1_id,
                usuario_2_id = :usuario_2_id,
                project_id = :project_id,
                introduccion = :introduccion,
                marcoteorico = :marcoteorico,
                metodo = :metodo,
                resultados = :resultados,
                discusion = :discusion,
                conclusiones = :conclusiones,
                secciones_similares = :secciones_similares,
                similitud_detectada = :similitud_detectada,
                status_analisis = :status_analisis
            WHERE id = :id
            """)
            
            # Añadir el ID al diccionario de datos
            data['id'] = registro_id
            
            # Ejecutar la actualización
            with con.connect() as connection:
                connection.execute(update_query, data)
                connection.commit()
            
        else:
            for key in data:
                if hasattr(data[key], 'item'):  # Método para convertir tipos numpy a Python
                    data[key] = data[key].item()

            df_insert = pd.DataFrame([data])
            df_insert.to_sql('comparacion_similitud', con, if_exists='append', index=False)
        
        return True
    
    except Exception as e:
        print(f"Error al interactuar con la base de datos: {e}")
        import traceback
        traceback.print_exc()  # Esto imprime el stack trace completo para un mejor diagnóstico
        return False

# Función para analizar un proyecto
def analizar_proyecto(project_id, df):
    inicio_tiempo = time.time()
    
    # Obtener tolerancias desde DB
    tolerancias = obtener_tolerancias()
    
    if not tolerancias:
        print("No se pueden obtener tolerancias. Verificar conexión o datos.")
        return False
    
    # Obtener usuarios en el proyecto
    usuarios_proyecto = df[df['project_id'] == project_id]['user_id'].unique()
    
    # Verificar si hay solo un usuario en el proyecto
    if len(usuarios_proyecto) <= 1:
        # Si hay un usuario, registrar con 0% de similitud
        if len(usuarios_proyecto) == 1:
            user_id = usuarios_proyecto[0]
            # Crear diccionario con todas las secciones en 0.0
            columnas = ['introduccion', 'marcoteorico', 'metodo', 'resultados', 'discusion', 'conclusiones']
            similitudes_dict = {col: 0.0 for col in columnas}
            
            # Insertar en la base de datos con usuario_2_id = 0
            insertar_comparacion_similitud(
                user_id,  # usuario_1_id
                0,        # usuario_2_id = 0 para proyectos de un solo integrante
                project_id,
                similitudes_dict,
                0         # secciones_similares = 0
            )
        
        return True  # Proyecto analizado correctamente
    
    # Continuar con el análisis normal para proyectos con múltiples usuarios
    docs = df[df['user_id'].isin(usuarios_proyecto)].groupby('user_id').first().reset_index()
    
    columnas = ['introduccion', 'marcoteorico', 'metodo', 'resultados', 'discusion', 'conclusiones']
    
    pares = list(combinations(docs['user_id'], 2))
    
    for user1, user2 in pares:
        doc1 = docs[docs['user_id'] == user1].iloc[0]
        doc2 = docs[docs['user_id'] == user2].iloc[0]
        
        similitudes = []
        plagios = []
        similitudes_dict = {}  # Diccionario para almacenar los valores de similitud por columna
        
        for col in columnas:
            texto1 = preprocesar_texto(doc1[col])
            texto2 = preprocesar_texto(doc2[col])
            
            # Vectorización y similitud
            vectorizador = TfidfVectorizer()
            try:
                vectores = vectorizador.fit_transform([texto1, texto2])
                similitud = cosine_similarity(vectores[0], vectores[1])[0][0]
                similitud = round(similitud, 4)
            except ValueError:
                similitud = 0.0
            
            # Almacenar similitud en el diccionario para DB
            similitudes_dict[col] = similitud
            
            # Usar tolerancia desde DB
            umbral = tolerancias.get(col, 0.0)  # Default 0 si no existe la sección
            
            plagio = similitud < umbral
            
            similitudes.append(similitud)
            plagios.append(plagio)
        
        # Calcular totales de plagio
        total_plagios = sum(plagios)
        
        # Insertar resultados en la base de datos
        insertar_comparacion_similitud(
            user1, 
            user2, 
            project_id, 
            similitudes_dict,
            total_plagios
        )
    
    fin_tiempo = time.time()
    tiempo_ejecucion = fin_tiempo - inicio_tiempo
    return tiempo_ejecucion  # Devuelve el tiempo que tomó analizar el proyecto

# Función para iniciar el análisis en segundo plano
def iniciar_analisis_proyectos():
    global progreso_analisis
    
    # Marcar como en progreso
    progreso_analisis['en_progreso'] = True
    progreso_analisis['tiempo_inicio'] = time.time()
    progreso_analisis['proyectos_analizados'] = 0
    progreso_analisis['tiempos_proyecto'] = []
    
    # Cargar datos
    df = pd.read_sql(sql='SELECT * FROM reportes_finales', con=con)
    
    # Obtener proyectos únicos
    proyectos = df['project_id'].unique()
    progreso_analisis['total_proyectos'] = len(proyectos)
    
    # Analizar cada proyecto
    for project_id in proyectos:
        tiempo_proyecto = analizar_proyecto(project_id, df)
        progreso_analisis['proyectos_analizados'] += 1
        progreso_analisis['tiempos_proyecto'].append(tiempo_proyecto)
    
    # Finalizar análisis
    progreso_analisis['tiempo_fin'] = time.time()
    progreso_analisis['en_progreso'] = False

# Rutas
@analisis.route('/')
def index():
    return render_template('index.html')

@analisis.route('/proyectos/contar', methods=['GET'])
def contar_proyectos():
    try:
        df = pd.read_sql(sql='SELECT DISTINCT project_id FROM reportes_finales', con=con)
        total_proyectos = len(df)
        return jsonify({'total_proyectos': total_proyectos, 'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'})

@analisis.route('/proyectos/analizar', methods=['POST'])
def analizar_proyectos():
    global progreso_analisis
    
    # Verificar si ya hay un análisis en progreso
    if progreso_analisis['en_progreso']:
        return jsonify({
            'status': 'error', 
            'message': 'Ya hay un análisis en progreso'
        })
    
    # Iniciar análisis en un hilo separado
    thread = threading.Thread(target=iniciar_analisis_proyectos)
    thread.daemon = True  # El hilo se cerrará cuando el programa principal termine
    thread.start()
    
    return jsonify({
        'status': 'success', 
        'message': 'Análisis iniciado'
    })

@analisis.route('/proyectos/progreso', methods=['GET'])
def obtener_progreso():
    global progreso_analisis
    
    # Calcular tiempo estimado restante
    tiempo_estimado_restante = None
    tiempo_promedio = None
    tiempo_total = None
    
    if progreso_analisis['proyectos_analizados'] > 0:
        if progreso_analisis['tiempo_fin']:
            # Si el análisis ha terminado
            tiempo_total = progreso_analisis['tiempo_fin'] - progreso_analisis['tiempo_inicio']
            tiempo_promedio = sum(progreso_analisis['tiempos_proyecto']) / len(progreso_analisis['tiempos_proyecto'])
        else:
            # Si está en progreso
            tiempo_actual = time.time() - progreso_analisis['tiempo_inicio']
            tiempo_promedio = tiempo_actual / progreso_analisis['proyectos_analizados']
            proyectos_restantes = progreso_analisis['total_proyectos'] - progreso_analisis['proyectos_analizados']
            tiempo_estimado_restante = tiempo_promedio * proyectos_restantes
    
    # Formatear tiempos
    if tiempo_estimado_restante is not None:
        horas, rem = divmod(tiempo_estimado_restante, 3600)
        minutos, segundos = divmod(rem, 60)
        tiempo_estimado_str = f"{int(horas)}h {int(minutos)}m {int(segundos)}s"
    else:
        tiempo_estimado_str = "Calculando..."
    
    if tiempo_total is not None:
        horas, rem = divmod(tiempo_total, 3600)
        minutos, segundos = divmod(rem, 60)
        tiempo_total_str = f"{int(horas)}h {int(minutos)}m {int(segundos)}s"
    else:
        tiempo_total_str = None
    
    if tiempo_promedio is not None:
        tiempo_promedio_str = f"{tiempo_promedio:.2f} segundos"
    else:
        tiempo_promedio_str = None
    
    return jsonify({
        'total_proyectos': progreso_analisis['total_proyectos'],
        'proyectos_analizados': progreso_analisis['proyectos_analizados'],
        'en_progreso': progreso_analisis['en_progreso'],
        'porcentaje': (progreso_analisis['proyectos_analizados'] / progreso_analisis['total_proyectos'] * 100) if progreso_analisis['total_proyectos'] > 0 else 0,
        'tiempo_estimado_restante': tiempo_estimado_str,
        'tiempo_total': tiempo_total_str,
        'tiempo_promedio': tiempo_promedio_str,
        'status': 'success'
    })