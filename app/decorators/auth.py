import firebase_admin
from firebase_admin import auth, credentials
from functools import wraps
from flask import request
import requests
import os
from app.utils.logger import get_logger

logger = get_logger("auth")

IS_LOCAL = os.getenv("RUN_ENV", "docker") == "local"
VAULT_ADDR = os.getenv("VAULT_ADDR1" if IS_LOCAL else "VAULT_ADDR", "http://localhost:8200")
VAULT_ROLE_ID = os.getenv("VAULT_ROLE_ID")
VAULT_SECRET_ID = os.getenv("VAULT_SECRET_ID")
VAULT_FIREBASE_PATH = "secret/data/firebase"

def obtener_vault_token():
    """
    Obtener un Vault token utilizando AppRole (role_id y secret_id).
    """
    vault_url = f"{VAULT_ADDR}/v1/auth/approle/login"
    data = {
        "role_id": VAULT_ROLE_ID,
        "secret_id": VAULT_SECRET_ID
    }

    response = requests.post(vault_url, json=data)
    if response.status_code == 200:
        client_token = response.json()["auth"]["client_token"]
        logger.info("Token de Vault obtenido exitosamente.")
        return client_token
    else:
        logger.error(f"Error autenticando con Vault: {response.text}")
        raise Exception("Error autenticando con Vault")

def cargar_credenciales_firebase():
    """
    Recupera las credenciales de Firebase desde Vault y las inicializa en Firebase Admin SDK.
    """
    if firebase_admin._apps:
        logger.warning("Firebase ya había sido inicializado. Se omite reinicialización.")
        return True

    vault_token = obtener_vault_token()
    headers = {
        "X-Vault-Token": vault_token
    }

    logger.info("Solicitando credenciales de Firebase desde Vault...")
    response = requests.get(f"{VAULT_ADDR}/v1/{VAULT_FIREBASE_PATH}", headers=headers)

    if response.status_code == 200:
        firebase_service_account = response.json()['data']['data']
        cred = credentials.Certificate(firebase_service_account)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK inicializado correctamente.")
        return True
    else:
        logger.error(f"Error al obtener las credenciales de Firebase: {response.status_code}")
        return False

# Cargar credenciales automáticamente al importar si aún no está hecho
if cargar_credenciales_firebase():
    logger.info("Firebase Admin SDK listo.")
else:
    logger.critical("No se pudo inicializar Firebase desde Vault.")

def require_auth(roles=None):
    """
    Decorador para validar el JWT y verificar el rol del usuario.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            token = request.headers.get("Authorization")
            if not token:
                logger.warning("Token no proporcionado en el encabezado.")
                return {"message": "Token no proporcionado"}, 401

            token = token.replace("Bearer ", "")
            try:
                logger.info("Verificando token JWT...")
                decoded_token = auth.verify_id_token(token)

                rol = decoded_token.get("rol")
                if not rol:
                    logger.warning("Rol no especificado en el token.")
                    return {"message": "Acceso denegado. Rol no especificado."}, 403

                rol = rol.strip().lower()
                normalized_roles = [r.strip().lower() for r in roles]

                logger.info(f"Rol detectado: {rol}")
                logger.info(f"Roles autorizados: {normalized_roles}")

                if rol not in normalized_roles:
                    logger.warning(f"Acceso denegado: rol '{rol}' no autorizado.")
                    return {"message": "Rol no autorizado"}, 403

                logger.info("Acceso autorizado al recurso protegido.")

            except Exception as e:
                logger.error(f"Error al verificar el token: {e}")
                return {
                    "message": "Token inválido o error en la verificación",
                    "error": "Autenticación fallida"
                }, 401

            return func(*args, **kwargs)
        return wrapper
    return decorator
