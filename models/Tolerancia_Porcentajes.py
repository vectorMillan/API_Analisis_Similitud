from config.config import db
from datetime import datetime

class ToleranciasPorcentajes(db.Model):
    __tablename__ = 'tolerancias_similitud'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    seccion = db.Column(db.String(50), unique=True, nullable=False) 
    tolerancia = db.Column(db.Float, nullable=False) # Tolerancia porcentual
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, seccion, tolerancia):
        self.seccion = seccion
        self.tolerancia = tolerancia