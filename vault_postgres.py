import os
import psycopg2
import requests
from dotenv import load_dotenv

# Cargar entorno desde .env
load_dotenv(override=True)

# Variables de configuración
VAULT_ADDR = os.getenv("VAULT_ADDR1", "http://localhost:8200")  # Local
VAULT_ROLE_ID = os.getenv("VAULT_ROLE_ID")
VAULT_SECRET_ID = os.getenv("VAULT_SECRET_ID")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mi_base_datos")
POSTGRES_HOST = os.getenv("POSTGRES_HOST1", "localhost")
POSTGRES_PORT = "5432"

def get_vault_token():
    """Obtener token temporal desde Vault usando AppRole"""
    resp = requests.post(
        f"{VAULT_ADDR}/v1/auth/approle/login",
        json={"role_id": VAULT_ROLE_ID, "secret_id": VAULT_SECRET_ID},
        headers={"Content-Type": "application/json"}
    )
    if resp.status_code == 200:
        print("🔐 Token de Vault obtenido.")
        return resp.json()["auth"]["client_token"]
    raise Exception(f"❌ Error autenticando en Vault: {resp.text}")

def get_jit_credentials(token):
    """Obtener credenciales JIT generadas por Vault"""
    headers = {"X-Vault-Token": token}
    resp = requests.get(f"{VAULT_ADDR}/v1/database/creds/app-role", headers=headers)
    if resp.status_code == 200:
        data = resp.json()["data"]
        lease = resp.json().get("lease_duration", "?")
        print(f"🔑 Usuario JIT: {data['username']} (lease: {lease}s)")
        return data["username"], data["password"]
    raise Exception(f"❌ Error obteniendo credenciales JIT: {resp.text}")

def test_connection():
    """Probar conexión a PostgreSQL usando las credenciales JIT"""
    token = get_vault_token()
    user, password = get_jit_credentials(token)

    conn = psycopg2.connect(
        dbname=POSTGRES_DB,
        user=user,
        password=password,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        sslmode="require"
    )
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    result = cur.fetchone()
    cur.close()
    conn.close()

    print(f"✅ Conexión JIT funcionando. Resultado de SELECT 1: {result[0]}")

if __name__ == "__main__":
    test_connection()
