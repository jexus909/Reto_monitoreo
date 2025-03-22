from flask import request
from flask_restful import Resource
from app.models.db import get_db_connection
from psycopg2.extras import RealDictCursor
from app.controllers.load_data import get_vault_token, get_encryption_key

class UsuarioController(Resource):
    def get(self, user_name):
        rol = request.headers.get("X-Rol", "soporte").lower()

        if rol != "soporte":
            return {"message": "Rol no autorizado"}, 403

        try:
            # 🔐 Obtener clave de cifrado desde Vault
            vault_token = get_vault_token()
            encryption_key = get_encryption_key(vault_token)

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 🎯 Consulta con desencriptado solo de los campos que el rol puede ver
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

            return user, 200

        except Exception as e:
            return {"error": str(e)}, 500
