from flask import Blueprint
from flask_restful import Api, Resource
from app.controllers.usuario_controller import UsuarioController
from app.controllers.fraude_controller import FraudeController
from app.controllers.marketing_controller import MarketingController

# Definir Blueprint para organizar las rutas de la API
api_bp = Blueprint('api', __name__)
api = Api(api_bp)

# Endpoint de prueba
class HelloWorld(Resource):
    def get(self):
        return {'message': 'Hello, World!'}

# Agregar recursos a la API
api.add_resource(HelloWorld, '/hello')  # Ruta: /api/hello
api.add_resource(UsuarioController, '/usuarios/<string:user_name>')
api.add_resource(FraudeController, '/fraude/<string:user_name>')
api.add_resource(MarketingController, '/marketing/<string:user_name>')