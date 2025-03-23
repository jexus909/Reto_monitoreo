from flask_restful import Resource
from app.models.db import get_db_connection
from psycopg2.extras import RealDictCursor
from app.controllers.load_data import get_vault_token, get_encryption_key
from app.utils.security import decode_if_memoryview
from app.decorators.auth import require_auth
print("✅ marketing_controller.py cargado correctamente")


class MarketingController(Resource):
    @require_auth(roles=["marketing"])  # Solo permite acceso al rol 'marketing'
    def get(self, user_name):

        try:
            # 🔐 Obtener clave para desencriptar datos del auto
            vault_token = get_vault_token()
            encryption_key = get_encryption_key(vault_token)

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 🔑 Llamada a función almacenada en PostgreSQL
            cursor.execute(
                "SELECT * FROM obtener_datos_marketing_por_username(%s, %s);",
                (encryption_key, user_name)
            )

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if not result:
                return {"message": "Usuario no encontrado o sin datos de auto"}, 404

            # ✨ Resultado desencriptado, decodificado y retornado al usuario final
            return {
                "user_name": result["user_name"],
                "color_favorito": result["color_favorito"],
                "avatar": result["avatar"],
                "cantidad_compras_realizadas": result["cantidad_compras_realizadas"],
                "auto": decode_if_memoryview(result["auto"]),
                "auto_modelo": decode_if_memoryview(result["auto_modelo"]),
                "auto_tipo": decode_if_memoryview(result["auto_tipo"]),
                "auto_color": decode_if_memoryview(result["auto_color"])
            }, 200

        except Exception as e:
            return {"error": str(e)}, 500
