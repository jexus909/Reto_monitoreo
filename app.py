from flask import Flask
from flasgger import Swagger
from app.controllers.load_data import load_data
from app.routes.api_routes import api_bp
from app.decorators.auth import cargar_credenciales_firebase
import threading
import time
from app.utils.logger import get_logger

# Logger principal para app.py
logger = get_logger("main")

app = Flask(__name__)

# Registrar rutas de la API
app.register_blueprint(api_bp, url_prefix='/api')

# Configuración Swagger
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "API Monitoreo",
        "version": "1.0",
        "description": "Documentación interactiva Swagger para la API Monitoreo"
    },
    "host": "localhost:9090",
    "basePath": "/api",
    "schemes": ["https"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT con el prefijo **Bearer**. Ejemplo: `Bearer {token}`"
        }
    },
    "security": [
        {
            "Bearer": []
        }
    ]
})

# Bandera para evitar múltiples cargas de datos
data_loaded = False

def load_data_in_background():
    global data_loaded
    if not data_loaded:
        logger.info(" Iniciando la carga de datos desde API externa...")
        try:
            load_data()
            data_loaded = True
            logger.info(" Datos cargados con éxito.")
        except Exception as e:
            logger.error(f" Error durante la carga de datos: {e}")
    else:
        logger.debug(" Los datos ya fueron cargados previamente.")

def start_load_data():
    logger.info(" Ejecutando hilo para carga de datos...")
    thread = threading.Thread(target=load_data_in_background)
    thread.start()

if __name__ == "__main__":
    if cargar_credenciales_firebase():
        logger.info(" Firebase Admin SDK inicializado correctamente.")
    else:
        logger.critical(" No se pudo inicializar Firebase Admin SDK desde Vault.")

    
    start_load_data()

    logger.info("Rutas registradas:")
    for rule in app.url_map.iter_rules():
        logger.debug(f" {rule}")

    logger.info("Servidor Flask ejecutándose en https://localhost:9090")
    app.run(
        ssl_context=('certs/ssl.crt', 'certs/ssl.key'),
        debug=False,
        host='0.0.0.0',
        port=9090
    )
