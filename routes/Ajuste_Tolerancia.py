from flask import Blueprint, render_template, request, redirect, url_for, flash
from config.config import db
from models.Tolerancia_Porcentajes import ToleranciasPorcentajes

tolerancia = Blueprint('tolerancia', __name__)

@tolerancia.route('/ajuste-tolerancia')
def ajuste_tolerancia():
    secciones = ToleranciasPorcentajes.query.all()
    return render_template('Ajuste_Tolerancia.html', secciones=secciones)


@tolerancia.route('/ajuste-tolerancia/update', methods=['POST'])
def update_tolerancia():
    seccion_id = request.form['id']
    seccion = ToleranciasPorcentajes.query.get(seccion_id)
    
    if request.method == 'POST':
        seccion.seccion = request.form['seccion']
        seccion.tolerancia = request.form['tolerancia']
        
        try:
            tolerancia_float = float(seccion.tolerancia)
            seccion.tolerancia = tolerancia_float
            db.session.commit()

            flash('Sección actualizada correctamente', 'success')
            return redirect(url_for('tolerancia.ajuste_tolerancia'))
        except Exception as e:
            db.session.rollback()
            return f'Error al actualizar: {str(e)}'
    return render_template('update.html', seccion=seccion)
