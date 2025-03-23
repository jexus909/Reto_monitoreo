from flask_restful import Resource
from app.models.db import get_db_connection
from psycopg2.extras import RealDictCursor
from app.controllers.load_data import get_vault_token, get_encryption_key
from app.utils.security import decode_if_memoryview
from app.decorators.auth import require_auth
import os
from flasgger import swag_from
from app.utils.logger import get_logger

logger = get_logger("usuario")

class UsuarioController(Resource):
    @swag_from(os.path.join(os.path.dirname(__file__), '../../swagger_docs/usuario_get.yml'))
    @require_auth(roles=["soporte"])
    def get(self, user_name):
        logger.info(f"Consulta de usuario iniciada: {user_name}")
        try:
            vault_token = get_vault_token()
            encryption_key = get_encryption_key(vault_token)

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                "SELECT * FROM obtener_usuario_por_username(%s, %s);",
                (encryption_key, user_name)
            )

            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if not user:
                logger.warning(f"Usuario no encontrado: {user_name}")
                return {"message": "Usuario no encontrado"}, 404

            user['direccion'] = decode_if_memoryview(user['direccion'])
            user['ip'] = decode_if_memoryview(user['ip'])

            logger.info(f"Datos obtenidos correctamente para usuario: {user_name}")
            return user, 200

        except Exception as e:
            logger.error(f"Error consultando usuario {user_name}: {e}")
            return {"error": "Error interno del servidor"}, 500
