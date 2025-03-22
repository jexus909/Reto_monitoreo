from flask import request
from flask_restful import Resource
from app.models.db import get_db_connection
from psycopg2.extras import RealDictCursor
from app.controllers.load_data import get_vault_token, get_encryption_key
from app.utils.security import enmascarar_tarjeta, enmascarar_cuenta, decode_if_memoryview

# ✅ Convertir cualquier memoryview a string
def decode_if_memoryview(value):
    return value.tobytes().decode("utf-8") if isinstance(value, memoryview) else value

class FraudeController(Resource):
    def get(self, user_name):
        rol = request.headers.get("X-Rol", "fraude").lower()

        if rol != "fraude":
            return {"message": "Rol no autorizado"}, 403

        try:
            # 🔐 Obtener clave de cifrado desde Vault
            vault_token = get_vault_token()
            encryption_key = get_encryption_key(vault_token)

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 🎯 Consulta segura y desencriptada
            query = """
                SELECT
                    u.user_name,
                    pgp_sym_decrypt(u.geo_latitud::bytea, %s) AS geo_latitud,
                    pgp_sym_decrypt(u.geo_longitud::bytea, %s) AS geo_longitud,
                    pgp_sym_decrypt(u.ip::bytea, %s) AS ip,
                    dp.cantidad_compras_realizadas,
                    pgp_sym_decrypt(dp.credit_card_num::bytea, %s) AS credit_card_num,
                    pgp_sym_decrypt(dp.cuenta_numero::bytea, %s) AS cuenta_numero
                FROM usuarios u
                JOIN datos_pago dp ON u.id = dp.usuario_id
                WHERE u.user_name = %s
            """

            cursor.execute(query, (
                encryption_key, encryption_key, encryption_key,
                encryption_key, encryption_key, user_name
            ))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if not result:
                return {"message": "Usuario no encontrado o sin datos de pago"}, 404

            # 🔐 Enmascarar y convertir
            tarjeta_enmascarada = enmascarar_tarjeta(decode_if_memoryview(result["credit_card_num"]))

            return {
             "user_name": result["user_name"],
             "geo_latitud": decode_if_memoryview(result["geo_latitud"]),
             "geo_longitud": decode_if_memoryview(result["geo_longitud"]),
             "ip": decode_if_memoryview(result["ip"]),
             "credit_card": tarjeta_enmascarada,
             "cuenta_numero": enmascarar_cuenta(decode_if_memoryview(result["cuenta_numero"])),
             "cantidad_compras_realizadas": result["cantidad_compras_realizadas"]
            }, 200


        except Exception as e:
            return {"error": str(e)}, 500
