from flask import Blueprint
from flask_restful import Api, Resource

# Definir Blueprint para organizar las rutas de la API
api_bp = Blueprint('api', __name__)

# Inicializar Flask-RESTful API
api = Api(api_bp)

# Crear un recurso de ejemplo para el endpoint
class HelloWorld(Resource):
    def get(self):
        return {'message': 'Hello, World!'}

# Agregar el recurso a la API
api.add_resource(HelloWorld, '/hello')  # Ruta: /api/hello
