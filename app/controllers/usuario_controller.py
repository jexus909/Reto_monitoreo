from flask_restful import Resource
from app.models.db import get_db_connection
from psycopg2.extras import RealDictCursor
from app.controllers.load_data import get_vault_token, get_encryption_key
from app.utils.security import decode_if_memoryview
from app.decorators.auth import require_auth
import os
from flasgger import swag_from

class UsuarioController(Resource):
    @swag_from(os.path.join(os.path.dirname(__file__), '../../swagger_docs/usuario_get.yml'))
    @require_auth(roles=["soporte"])
    def get(self, user_name):
        try:
            vault_token = get_vault_token()
            encryption_key = get_encryption_key(vault_token)

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 🔑 Llamada a la función almacenada en PostgreSQL
            cursor.execute(
                "SELECT * FROM obtener_usuario_por_username(%s, %s);",
                (encryption_key, user_name)
            )

            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if not user:
                return {"message": "Usuario no encontrado"}, 404

            user['direccion'] = decode_if_memoryview(user['direccion'])
            user['ip'] = decode_if_memoryview(user['ip'])

            return user, 200  # ✅ Resultado desencriptado y listo para retornar

        except Exception as e:
            return {"error": str(e)}, 500
