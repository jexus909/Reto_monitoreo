import firebase_admin
from firebase_admin import auth, credentials
from functools import wraps
from flask import request
import requests
import os

IS_LOCAL = os.getenv("RUN_ENV", "docker") == "local"

# Variables de entorno para Vault (compatibles con local y Docker)
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
        print(f"✅ Token de Vault obtenido con éxito: {client_token[:8]}******")
        return client_token
    else:
        raise Exception(f"❌ Error autenticando con Vault: {response.text}")

def cargar_credenciales_firebase():
    """
    Recupera las credenciales de Firebase desde Vault y las inicializa en Firebase Admin SDK.
    """
    if firebase_admin._apps:
        print("⚠️ Firebase ya estaba inicializado. Se omite reinicialización.")
        return True

    vault_token = obtener_vault_token()
    headers = {
        "X-Vault-Token": vault_token
    }

    print("🔥 Intentando obtener credenciales de Firebase desde Vault...")
    response = requests.get(f"{VAULT_ADDR}/v1/{VAULT_FIREBASE_PATH}", headers=headers)

    if response.status_code == 200:
        print("🔥 Credenciales de Firebase recuperadas con éxito desde Vault.")
        firebase_service_account = response.json()['data']['data']
        cred = credentials.Certificate(firebase_service_account)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase Admin SDK inicializado correctamente.")
        return True
    else:
        print(f"❌ Error al obtener las credenciales de Firebase desde Vault: {response.status_code}")
        return False

# Cargar las credenciales de Firebase una vez al iniciar
if cargar_credenciales_firebase():
    print("✅ Firebase Admin SDK inicializado correctamente.")
else:
    print("❌ No se pudo inicializar Firebase Admin SDK desde Vault.")

def require_auth(roles=None):
    """
    Decorador para validar el JWT y verificar el rol del usuario.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print("🛡️ Ejecutando decorador require_auth...")

            token = request.headers.get("Authorization")
            if not token:
                print("🚫 No se proporcionó token")
                return {"message": "Token no proporcionado"}, 401

            token = token.replace("Bearer ", "")
            try:
                print(f"🔥 Verificando token JWT: {token[:20]}...")  # Truncado para no exponerlo completo
                decoded_token = auth.verify_id_token(token)

                print("🧾 Claims del token:", decoded_token)

                rol = decoded_token.get("rol")
                if not rol:
                    print("⚠️ Rol no presente en el token.")
                    return {"message": "Acceso denegado. Rol no especificado."}, 403

                # Normalizar el rol y los roles permitidos
                rol = rol.strip().lower()
                normalized_roles = [r.strip().lower() for r in roles]

                print(f"🔐 Rol detectado: [{rol}]")
                print(f"✅ Roles permitidos: {normalized_roles}")

                if rol not in normalized_roles:
                    print("🚫 Acceso denegado por rol no autorizado.")
                    return {"message": "Rol no autorizado"}, 403

                print("✅ Acceso autorizado. Ejecutando función protegida...")

            except Exception as e:
                print(f"❌ Error al verificar el token: {e}")
                return {
                    "message": "Token inválido o error en la verificación",
                    "error": str(e)
                }, 401

            return func(*args, **kwargs)
        return wrapper
    return decorator
