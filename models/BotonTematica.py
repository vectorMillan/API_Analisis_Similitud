from config.config import db

class Tematicas(db.Model):
    __tablename__ = 'thematic'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    status = db.Column(db.Integer, nullable=False)

    def __init__(self, name):
        self.name = name

