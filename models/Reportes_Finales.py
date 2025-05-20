from config.config import db
from datetime import datetime

class ReportesFinales(db.Model):
    __tablename__ = 'reportes_finales'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    project_id = db.Column(db.Integer, nullable=False)
    thematic_id = db.Column(db.Integer, nullable=False)
    subtematica_id = db.Column(db.Integer, nullable=False)
    introduccion = db.Column(db.Text)
    marcoteorico = db.Column(db.Text)
    metodo = db.Column(db.Text)
    resultados = db.Column(db.Text)
    discusion = db.Column(db.Text)
    conclusiones = db.Column(db.Text)
    nombre_reporte = db.Column(db.String(600), nullable=False)
    revisor_id = db.Column(db.Integer, nullable=True)
    status = db.Column(db.Integer)
    calificacion_final = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime)

    # El __init__ es opcional si los campos tienen defaults o son nullable,
    # o si prefieres asignar atributos después de la creación.
    # Este __init__ es selectivo, lo cual está bien si así lo requieres.
    def __init__(self, user_id, project_id, thematic_id, subtematic_id, introduccion, marcoteorico, metodo, resultados, discusion, conclusiones, nombre_reporte=None, status=None): # Añadí nombre_reporte y status como opcionales
        self.user_id = user_id
        self.project_id = project_id
        self.thematic_id = thematic_id
        self.subtematic_id = subtematic_id
        self.introduccion = introduccion
        self.marcoteorico = marcoteorico
        self.metodo = metodo
        self.resultados = resultados
        self.discusion = discusion
        self.conclusiones = conclusiones
        if nombre_reporte: # Solo asignar si se provee
            self.nombre_reporte = nombre_reporte
        if status is not None:
            self.status = status