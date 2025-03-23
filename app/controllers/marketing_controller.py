from flask_restful import Resource
from app.models.db import get_db_connection
from psycopg2.extras import RealDictCursor
from app.controllers.load_data import get_vault_token, get_encryption_key
from app.utils.security import decode_if_memoryview
from app.decorators.auth import require_auth
import os
from flasgger import swag_from
from app.utils.logger import get_logger

logger = get_logger("marketing")

class MarketingController(Resource):
    @swag_from(os.path.join(os.path.dirname(__file__), '../../swagger_docs/marketing_controller.yml'))
    @require_auth(roles=["marketing"])
    def get(self, user_name):
        logger.info(f"Consulta de datos de marketing para: {user_name}")
        try:
            vault_token = get_vault_token()
            encryption_key = get_encryption_key(vault_token)

            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute(
                "SELECT * FROM obtener_datos_marketing_por_username(%s, %s);",
                (encryption_key, user_name)
            )

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if not result:
                logger.warning(f"No se encontraron datos de marketing para: {user_name}")
                return {"message": "Usuario no encontrado o sin datos de auto"}, 404

            logger.info(f"Datos de marketing entregados para: {user_name}")
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
            logger.error(f"Error en consulta de marketing para {user_name}: {e}")
            return {"error": "Error interno del servidor"}, 500
