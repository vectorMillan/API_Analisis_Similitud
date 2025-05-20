from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.ejemplo import ToleranciasSimilitud
from config.config import db


ejemplo = Blueprint('ejemplo', __name__)

@ejemplo.route('/ejemplo')
def index():
    secciones = ToleranciasSimilitud.query.all()
    return render_template('index.html', secciones=secciones)


@ejemplo.route('/new', methods=['POST'])
def add_seccion():
    seccion = request.form['seccion']
    tolerancia = request.form['tolerancia']

    try:
        tolerancia_float = float(tolerancia)
        new_seccion = ToleranciasSimilitud(seccion=seccion, tolerancia=tolerancia_float)
        db.session.add(new_seccion)
        db.session.commit()

        flash('Sección agregada correctamente', 'success')
        return redirect(url_for('ejemplo.index'))
    except Exception as e:
        db.session.rollback()
        return f'Error al guardar: {str(e)}'
    
@ejemplo.route('/update/<id>', methods=['POST', 'GET'])
def update(id):
    
    seccion = ToleranciasSimilitud.query.get(id)
    
    if request.method == 'POST':
        seccion.seccion = request.form['seccion']
        seccion.tolerancia = request.form['tolerancia']
        
        try:
            tolerancia_float = float(seccion.tolerancia)
            seccion.tolerancia = tolerancia_float
            db.session.commit()

            flash('Sección actualizada correctamente', 'success')
            return redirect(url_for('ejemplo.index'))
        except Exception as e:
            db.session.rollback()
            return f'Error al actualizar: {str(e)}'
    return render_template('update.html', seccion=seccion)

@ejemplo.route('/delete/<id>')
def delete(id):
    id_seccion = ToleranciasSimilitud.query.get(id)
    db.session.delete(id_seccion)
    db.session.commit()
    print(id_seccion)
    flash('Sección eliminada correctamente', 'success')
    return redirect(url_for('ejemplo.index'))