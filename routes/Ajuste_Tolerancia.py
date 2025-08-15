from flask import Blueprint, render_template, request, url_for, flash, jsonify 
from config.config import db
from models.Tolerancia_Porcentajes import ToleranciasPorcentajes

tolerancia = Blueprint('tolerancia', __name__)

@tolerancia.route('/ajuste-tolerancia')
def ajuste_tolerancia():
    desired_order = [
        "introduccion", 
        "marcoteorico", 
        "metodo", 
        "resultados", 
        "discusion", 
        "conclusiones",
        "referencias"
    ]
    
    # Obtener todas las secciones de la base de datos
    all_secciones_db = ToleranciasPorcentajes.query.all()
    
    # Crear un diccionario para un acceso rápido a las secciones por su nombre (normalizado)
    secciones_map = {s.seccion.strip().lower(): s for s in all_secciones_db}
    
    # Construir la lista ordenada
    secciones_ordenadas = []
    secciones_encontradas_en_db = set()

    for seccion_name_desired in desired_order:
        seccion_obj = secciones_map.get(seccion_name_desired.lower())
        if seccion_obj:
            secciones_ordenadas.append(seccion_obj)
            secciones_encontradas_en_db.add(seccion_obj.seccion.strip().lower())
            
    for seccion_db in all_secciones_db:
        if seccion_db.seccion.strip().lower() not in secciones_encontradas_en_db:
            secciones_ordenadas.append(seccion_db)
            current_app.logger.warning(f"La sección '{seccion_db.seccion}' de la BD no está en el 'desired_order' y se añadió al final.")

    return render_template('Ajuste_Tolerancia.html', secciones=secciones_ordenadas)


@tolerancia.route('/ajuste-tolerancia/update', methods=['POST'])
def update_tolerancia():
    if request.method == 'POST':
        try:
            seccion_id = request.form.get('id')
            nueva_tolerancia_str = request.form.get('tolerancia')

            if not seccion_id or nueva_tolerancia_str is None: # Verificar que los datos existan
                return jsonify({'status': 'error', 'message': 'Faltan datos (ID o tolerancia).'}), 400

            seccion_obj = ToleranciasPorcentajes.query.get(seccion_id)

            if not seccion_obj:
                return jsonify({'status': 'error', 'message': 'Sección no encontrada.'}), 404

            tolerancia_float = float(nueva_tolerancia_str) # Convertir a float
            
            if not (0.0 <= tolerancia_float <= 1.0): 
                return jsonify({'status': 'error', 'message': 'El valor de tolerancia debe estar entre 0.0 y 1.0.'}), 400


            seccion_obj.tolerancia = tolerancia_float
            db.session.commit()

            return jsonify({
                'status': 'success', 
                'message': 'Sección actualizada correctamente.',
                'seccion_id': seccion_obj.id,
                'nueva_tolerancia': seccion_obj.tolerancia
            })

        except ValueError: # Error al convertir a float
            db.session.rollback()
            return jsonify({'status': 'error', 'message': 'Valor de tolerancia inválido. Debe ser un número.'}), 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al actualizar tolerancia: {str(e)}") # Loguear el error
            return jsonify({'status': 'error', 'message': f'Error al actualizar: {str(e)}'}), 500
    
    return jsonify({'status': 'error', 'message': 'Método no permitido.'}), 405
