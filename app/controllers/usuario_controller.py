from flask_restful import Resource
from app.models.db import get_db_connection
from psycopg2.extras import RealDictCursor
from app.controllers.load_data import get_vault_token, get_encryption_key
from app.utils.security import decode_if_memoryview
from app.decorators.auth import require_auth

class UsuarioController(Resource):
    @require_auth(roles=["soporte"])
    def get(self, user_name):
        try:
            vault_token = get_vault_token()
            encryption_key = get_encryption_key(vault_token)

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT
                    user_name,
                    codigo_zip,
                    pgp_sym_decrypt(direccion::bytea, %s) AS direccion,
                    color_favorito,
                    pgp_sym_decrypt(ip::bytea, %s) AS ip,
                    avatar
                FROM usuarios
                WHERE user_name = %s
            """
            cursor.execute(query, (encryption_key, encryption_key, user_name))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if not user:
                return {"message": "Usuario no encontrado"}, 404

            user['direccion'] = decode_if_memoryview(user['direccion'])
            user['ip'] = decode_if_memoryview(user['ip'])

            return user, 200  # ✅ Devuelve un dict simple que Flask-RESTful puede serializar

        except Exception as e:
            return {"error": str(e)}, 500
