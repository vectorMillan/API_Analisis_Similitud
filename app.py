from flask import Flask
from routes.Ajuste_Tolerancia import tolerancia
from routes.Analisis_Similitud import analisis
from config.config import db
from flask_cors import CORS

app = Flask(__name__)

CORS(app)

app.secret_key = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/verano_cientifico2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

app.register_blueprint(analisis)
app.register_blueprint(tolerancia)
