from flask_restful import Resource
from app.models.db import get_db_connection
from psycopg2.extras import RealDictCursor
from app.controllers.load_data import get_vault_token, get_encryption_key
from app.utils.security import decode_if_memoryview
from app.decorators.auth import require_auth
print("✅ marketing_controller.py cargado correctamente")


class MarketingController(Resource):
    @require_auth(roles=["marketing"])  # Solo permite acceso a rol 'marketing'
    def get(self, user_name):

        #print("📥 [Marketing] Ingreso al endpoint con usuario:", user_name)
        try:
            # 🔐 Obtener clave para desencriptar datos del auto
            vault_token = get_vault_token()
            encryption_key = get_encryption_key(vault_token)

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            query = """
                SELECT
                    u.user_name,
                    u.color_favorito,
                    u.avatar,
                    dp.cantidad_compras_realizadas,
                    pgp_sym_decrypt(a.auto::bytea, %s) AS auto,
                    pgp_sym_decrypt(a.auto_modelo::bytea, %s) AS auto_modelo,
                    pgp_sym_decrypt(a.auto_tipo::bytea, %s) AS auto_tipo,
                    pgp_sym_decrypt(a.auto_color::bytea, %s) AS auto_color
                FROM usuarios u
                JOIN autos a ON u.id = a.usuario_id
                JOIN datos_pago dp ON u.id = dp.usuario_id
                WHERE u.user_name = %s
            """

            cursor.execute(query, (
                encryption_key,
                encryption_key,
                encryption_key,
                encryption_key,
                user_name
            ))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if not result:
                return {"message": "Usuario no encontrado o sin datos de auto"}, 404

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
