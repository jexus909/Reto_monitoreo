import os
import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv()
#  Detección del entorno
IS_LOCAL = os.getenv("RUN_ENV", "docker") == "local"

VAULT_ADDR = os.getenv("VAULT_ADDR1" if IS_LOCAL else "VAULT_ADDR", "http://localhost:8200")
VAULT_ROLE_ID = os.getenv("VAULT_ROLE_ID")
VAULT_SECRET_ID = os.getenv("VAULT_SECRET_ID")
POSTGRES_HOST = os.getenv("POSTGRES_HOST1" if IS_LOCAL else "POSTGRES_HOST", "localhost")
POSTGRES_PORT = "5432"
POSTGRES_DB = os.getenv("POSTGRES_DB", "mi_base_datos")

def get_vault_token():
    """Autenticarse en Vault usando AppRole"""
    auth_url = f"{VAULT_ADDR}/v1/auth/approle/login"
    headers = {"Content-Type": "application/json"}
    payload = {"role_id": VAULT_ROLE_ID, "secret_id": VAULT_SECRET_ID}

    response = requests.post(auth_url, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["auth"]["client_token"]
    else:
        raise Exception(f"❌ Error autenticando en Vault: {response.text}")

def get_jit_db_credentials(vault_token):
    """Obtener usuario y contraseña JIT desde Vault"""
    headers = {"X-Vault-Token": vault_token}
    creds_url = f"{VAULT_ADDR}/v1/database/creds/app-role"

    response = requests.get(creds_url, headers=headers)
    if response.status_code == 200:
        data = response.json()["data"]
        return data["username"], data["password"]
    else:
        raise Exception(f"❌ Error obteniendo credenciales JIT: {response.text}")

def get_db_connection():
    """Obtener conexión segura a PostgreSQL usando credenciales JIT"""
    try:
        vault_token = get_vault_token()
        db_user, db_pass = get_jit_db_credentials(vault_token)

        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=db_user,
            password=db_pass,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            sslmode="require"
        )
        return conn
    except Exception as e:
        print(f"❌ Error en get_db_connection: {e}")
        raise
