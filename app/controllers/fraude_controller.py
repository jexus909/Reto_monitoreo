from flask_restful import Resource
from app.models.db import get_db_connection
from psycopg2.extras import RealDictCursor
from app.controllers.load_data import get_vault_token, get_encryption_key
from app.utils.security import enmascarar_tarjeta, enmascarar_cuenta, decode_if_memoryview
from app.decorators.auth import require_auth
import os
from flasgger import swag_from
from app.utils.logger import get_logger

logger = get_logger("fraude")

class FraudeController(Resource):
    @swag_from(os.path.join(os.path.dirname(__file__), '../../swagger_docs/fraude_controller.yml'))
    @require_auth(roles=["fraude"])
    def get(self, user_name):
        logger.info(f"Solicitud de datos de fraude para: {user_name}")

        try:
            vault_token = get_vault_token()
            encryption_key = get_encryption_key(vault_token)

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                "SELECT * FROM obtener_datos_fraude_por_username(%s, %s);", 
                (encryption_key, user_name)
            )

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if not result:
                logger.warning(f"No se encontraron datos de fraude para: {user_name}")
                return {"message": "Usuario no encontrado o sin datos de pago"}, 404

            logger.info(f"Datos de fraude obtenidos exitosamente para: {user_name}")

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
            logger.error(f"Error al consultar datos de fraude para {user_name}: {e}")
            return {"error": "Error interno del servidor"}, 500
