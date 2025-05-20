from flask import Flask
from routes.Ajuste_Tolerancia import tolerancia
from routes.Analisis_Similitud import analisis
from config.config import db

app = Flask(__name__)

app.secret_key = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:1234@localhost/verano_cientifico'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

app.register_blueprint(analisis)
app.register_blueprint(tolerancia) 
