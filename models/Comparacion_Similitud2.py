from config.config import db
from datetime import datetime

class ComparacionSimilitud(db.Model):
    __tablename__ = 'comparacion_similitud2'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario_1_id = db.Column(db.Integer, nullable=False)
    usuario_2_id = db.Column(db.Integer, nullable=False) # Para proyectos individuales, este podría ser 0
    project_id = db.Column(db.Integer, nullable=False)
    introduccion = db.Column(db.Float, default=0.0)
    marcoteorico = db.Column(db.Float, default=0.0)
    metodo = db.Column(db.Float, default=0.0)
    resultados = db.Column(db.Float, default=0.0)
    discusion = db.Column(db.Float, default=0.0)
    conclusiones = db.Column(db.Float, default=0.0)
    secciones_similares = db.Column(db.Integer, default=0)
    similitud_detectada = db.Column(db.Integer, default=0) # 0 o 1
    status_analisis = db.Column(db.Integer, default=0) # ¡Este campo es importante! 1 para analizado, 0 para pendiente/no analizado
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Un __init__ más completo podría ser así, aunque SQLAlchemy puede inferirlo.
    # Los defaults en las columnas ya manejan valores iniciales si no se proveen.
    def __init__(self, usuario_1_id, usuario_2_id, project_id, 
                introduccion=0.0, marcoteorico=0.0, metodo=0.0, 
                resultados=0.0, discusion=0.0, conclusiones=0.0,
                secciones_similares=0, similitud_detectada=0, status_analisis=0):
        self.usuario_1_id = usuario_1_id
        self.usuario_2_id = usuario_2_id
        self.project_id = project_id
        self.introduccion = introduccion
        self.marcoteorico = marcoteorico
        self.metodo = metodo
        self.resultados = resultados
        self.discusion = discusion
        self.conclusiones = conclusiones
        self.secciones_similares = secciones_similares
        self.similitud_detectada = similitud_detectada
        self.status_analisis = status_analisis