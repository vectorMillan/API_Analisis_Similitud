from flask import Flask
from routes.Ajuste_Tolerancia import tolerancia
from routes.Analisis_Similitud import analisis
from config.config import db
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

CORS(app)

db_host = os.getenv('DB_HOST')
db_user = os.getenv('DB_USER')
db_password = os.getenv('DB_PASSWORD')
db_name = os.getenv('DB_NAME')

app.secret_key = 'secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql://{db_user}:{db_password}@{db_host}/{db_name}'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/verano_cientifico2'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

app.register_blueprint(analisis)
app.register_blueprint(tolerancia)
