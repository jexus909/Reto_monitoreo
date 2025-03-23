from flask_restful import Resource
from app.models.db import get_db_connection
from psycopg2.extras import RealDictCursor
from app.controllers.load_data import get_vault_token, get_encryption_key
from app.utils.security import enmascarar_tarjeta, enmascarar_cuenta, decode_if_memoryview
from app.decorators.auth import require_auth

class FraudeController(Resource):
    @require_auth(roles=["fraude"])  # Solo permite acceso al rol 'fraude'
    def get(self, user_name):
        print(f"📥 [Fraude] Ingreso al endpoint con usuario: {user_name}")

        try:
            # 🔐 Obtener clave para desencriptar campos sensibles
            vault_token = get_vault_token()
            encryption_key = get_encryption_key(vault_token)

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 🔑 Llamada a la función almacenada
            cursor.execute(
                "SELECT * FROM obtener_datos_fraude_por_username(%s, %s);", 
                (encryption_key, user_name)
            )

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if not result:
                print("⚠️ Usuario no encontrado o sin datos de pago.")
                return {"message": "Usuario no encontrado o sin datos de pago"}, 404

            print("✅ Datos recuperados con éxito.")

            #  imprimir resultados.
            return {
                "user_name": result["user_name"],
                "geo_latitud": decode_if_memoryview(result["geo_latitud"]),
                "geo_longitud": decode_if_memoryview(result["geo_longitud"]),
                "ip": decode_if_memoryview(result["ip"]),
                "credit_card": enmascarar_tarjeta(decode_if_memoryview(result["credit_card_num"])),
                "cuenta_numero": enmascarar_cuenta(decode_if_memoryview(result["cuenta_numero"])),
                "cantidad_compras_realizadas": result["cantidad_compras_realizadas"]
            }, 200

        except Exception as e:
            print(f"❌ Error en el endpoint de fraude: {e}")
            return {"error": str(e)}, 500
