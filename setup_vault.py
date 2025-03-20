import os
import requests
import psycopg2
import time
import string
import random
from dotenv import load_dotenv

# 🔥 Cargar .env 🔥
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path, override=True)

# Variables de entorno
VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_ROLE_ID = os.getenv("VAULT_ROLE_ID")
VAULT_SECRET_ID = os.getenv("VAULT_SECRET_ID")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = "default_user"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"

# 🔥 Obtener un Token Temporal desde AppRole 🔥
def get_vault_token():
    response = requests.post(f"{VAULT_ADDR}/v1/auth/approle/login", json={"role_id": VAULT_ROLE_ID, "secret_id": VAULT_SECRET_ID})
    if response.status_code == 200:
        client_token = response.json()["auth"]["client_token"]
        print(f"✅ Token obtenido con éxito: {client_token[:8]}******")
        return client_token
    else:
        raise Exception(f"❌ Error autenticando con Vault: {response.text}")

# 🔥 Borrar secretos antiguos en Vault (KV v2 requiere `metadata/`) 🔥
def delete_old_secrets(vault_token):
    headers = {"X-Vault-Token": vault_token}
    print("🛑 Eliminando secretos anteriores...")
    requests.delete(f"{VAULT_ADDR}/v1/secret/metadata/db_credentials", headers=headers)
    print("✅ Secretos eliminados correctamente.")

# 🔥 Guardar credenciales en Vault (KV v2 usa `secret/data/...`) 🔥
def store_in_vault(vault_token, path, data):
    headers = {"X-Vault-Token": vault_token}
    
    # 🔥 Para KV v2, la ruta correcta es `secret/data/...`
    response = requests.post(f"{VAULT_ADDR}/v1/secret/data/{path}", headers=headers, json={"data": data})
    
    if response.status_code != 200:
        raise Exception(f"Error almacenando {path} en Vault: {response.text}")
    
    print(f"✅ {path} almacenado en Vault.")

# 🔥 Cambiar la contraseña de `default_user` en PostgreSQL 🔥
def update_postgres_password(password):
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="default_user",
            password="default_pass",  # 🔥 La contraseña inicial de docker-compose.yml
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # 🔥 Actualizar la contraseña de `default_user` en PostgreSQL 🔥
        cursor.execute(f"ALTER USER {POSTGRES_USER} WITH PASSWORD '{password}';")
        print(f"✅ Contraseña de PostgreSQL para el usuario '{POSTGRES_USER}' actualizada correctamente.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error actualizando la contraseña en PostgreSQL: {e}")

# 🔥 Función principal 🔥
def main():
    print("🚀 Iniciando configuración de Vault y PostgreSQL...")

    # 🔥 Obtener Token de Vault desde `AppRole` 🔥
    vault_token = get_vault_token()

    # 🔥 Borrar secretos incorrectos antes de guardar los nuevos 🔥
    delete_old_secrets(vault_token)

    db_password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*()", k=16))
    encryption_key = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*()", k=32))

    # 🔥 Guardar credenciales en Vault con `default_user` 🔥
    store_in_vault(vault_token, "db_credentials", {"user": "default_user", "password": db_password})
    store_in_vault(vault_token, "postgres_key", {"value": encryption_key})

    # 🔥 Cambiar la contraseña del usuario en PostgreSQL 🔥
    update_postgres_password(db_password)

    print("🎉 Aprovisionamiento de Vault y PostgreSQL completado.")

if __name__ == "__main__":
    main()
