import os
import requests
import psycopg2
import string
import random
import time
import json
from dotenv import load_dotenv

# Cargar variables de entorno
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path, override=True)

# Configuración
VAULT_ADDR = os.getenv("VAULT_ADDR", "http://vault:8200")
VAULT_DEV_ROOT_TOKEN_ID = os.getenv("VAULT_DEV_ROOT_TOKEN_ID", "root")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "mi_postgres")
POSTGRES_PORT = "5432"
POSTGRES_DB = os.getenv("POSTGRES_DB", "mi_base_datos")
POSTGRES_USER = "default_user"

# Esperar a que Vault esté listo
def wait_for_vault_ready(timeout=30):
    print("⏳ Esperando que Vault esté listo...")
    for _ in range(timeout):
        try:
            r = requests.get(f"{VAULT_ADDR}/v1/sys/health")
            if r.status_code in [200, 429, 472, 473, 501]:
                print("✅ Vault está listo.")
                return
        except:
            pass
        time.sleep(1)
    raise Exception("❌ Timeout: Vault no respondió a tiempo.")

# Crear política
def create_policy(vault_token):
    headers = {"X-Vault-Token": vault_token}
    policy = """
path "secret/data/db_credentials" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/metadata/db_credentials" {
  capabilities = ["read", "list", "delete"]
}
path "secret/data/postgres_key" {
  capabilities = ["create", "read", "update", "delete", "list"]
}
path "secret/metadata/postgres_key" {
  capabilities = ["read", "list", "delete"]
}
path "secret/data/firebase" {
  capabilities = ["read"]
}
path "secret/metadata/firebase" {
  capabilities = ["read", "list"]
}
# Permiso para obtener credenciales JIT
path "database/creds/app-role" {
  capabilities = ["read"]
}
"""
    r = requests.put(f"{VAULT_ADDR}/v1/sys/policies/acl/app_policy", headers=headers, json={"policy": policy})
    if r.status_code != 204:
        raise Exception(f"❌ Error creando app_policy: {r.text}")
    print("✅ Política app_policy creada.")

# Habilitar auth/approle
def enable_approle_auth_method(vault_token):
    headers = {"X-Vault-Token": vault_token}
    r = requests.post(f"{VAULT_ADDR}/v1/sys/auth/approle", headers=headers, json={"type": "approle"})
    if r.status_code not in [200, 204]:
        if "path is already in use" in r.text:
            print("⚠️ auth/approle ya estaba habilitado.")
        else:
            raise Exception(f"❌ Error habilitando auth/approle: {r.text}")
    else:
        print("✅ Método de autenticación AppRole habilitado.")

# Crear AppRole
def create_approle(vault_token, role_name="mi_app"):
    headers = {"X-Vault-Token": vault_token}
    payload = {"policies": ["app_policy"], "token_ttl": "1h", "token_max_ttl": "4h"}
    r = requests.post(f"{VAULT_ADDR}/v1/auth/approle/role/{role_name}", headers=headers, json=payload)
    if r.status_code not in [200, 204]:
        raise Exception(f"❌ Error creando AppRole: {r.text}")
    print("✅ AppRole creado.")

# Obtener role_id y secret_id
def get_approle_credentials(vault_token, role_name="mi_app"):
    headers = {"X-Vault-Token": vault_token}
    role_id = requests.get(f"{VAULT_ADDR}/v1/auth/approle/role/{role_name}/role-id", headers=headers).json()["data"]["role_id"]
    secret_id = requests.post(f"{VAULT_ADDR}/v1/auth/approle/role/{role_name}/secret-id", headers=headers).json()["data"]["secret_id"]
    print("✅ Credenciales AppRole obtenidas.")
    return role_id, secret_id

# Actualizar .env sin duplicados
def update_env_file(role_id, secret_id):
    path = ".env"
    if os.path.exists(path):
        with open(path, "r") as f:
            lines = [line for line in f if not line.startswith("VAULT_ROLE_ID=") and not line.startswith("VAULT_SECRET_ID=")]
    else:
        lines = []
    lines.append(f"VAULT_ROLE_ID={role_id}\n")
    lines.append(f"VAULT_SECRET_ID={secret_id}\n")
    with open(path, "w") as f:
        f.writelines(lines)
    print("✅ .env actualizado sin duplicados.")

# Borrar secretos anteriores
def delete_old_secrets(vault_token):
    headers = {"X-Vault-Token": vault_token}
    requests.delete(f"{VAULT_ADDR}/v1/secret/metadata/db_credentials", headers=headers)
    print("✅ Secretos anteriores eliminados.")

# Guardar secreto en Vault
def store_in_vault(vault_token, path, data):
    headers = {"X-Vault-Token": vault_token}
    r = requests.post(f"{VAULT_ADDR}/v1/secret/data/{path}", headers=headers, json={"data": data})
    if r.status_code != 200:
        raise Exception(f"❌ Error guardando {path}: {r.text}")
    print(f"✅ Secreto {path} guardado.")

# Cargar archivo monitoreo-api.json como secreto firebase
def load_firebase_secret(vault_token, file_path="monitoreo-api.json"):
    if not os.path.exists(file_path):
        print(f"⚠️ Archivo {file_path} no encontrado. Se omite carga de Firebase.")
        return
    with open(file_path, "r") as f:
        firebase_data = json.load(f)
    store_in_vault(vault_token, "firebase", firebase_data)
    os.remove(file_path)
    print(f"✅ Secreto firebase guardado. 🗑️ Archivo {file_path} eliminado.")

# Cambiar contraseña en PostgreSQL
def update_postgres_password(password):
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=POSTGRES_USER,
            password="default_pass",
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            sslmode="require"
        )
        conn.autocommit = True
        cursor = conn.cursor()
        cursor.execute(f"ALTER USER {POSTGRES_USER} WITH PASSWORD '{password}';")
        cursor.close()
        conn.close()
        print("✅ Contraseña de PostgreSQL actualizada.")
    except Exception as e:
        print(f"❌ Error cambiando contraseña en PostgreSQL: {e}")

# Habilitar engine database
def enable_database_engine(vault_token):
    headers = {"X-Vault-Token": vault_token}
    r = requests.post(f"{VAULT_ADDR}/v1/sys/mounts/database", headers=headers, json={"type": "database"})
    if r.status_code not in [200, 204]:
        if "path is already in use" in r.text:
            print("⚠️ El engine database ya estaba habilitado.")
        else:
            raise Exception(f"❌ Error habilitando el engine database: {r.text}")
    else:
        print("✅ Vault Database Secrets Engine habilitado.")

# Configurar engine postgres_jit
def configure_postgres_engine(vault_token, db_user, db_pass):
    headers = {"X-Vault-Token": vault_token}
    payload = {
        "plugin_name": "postgresql-database-plugin",
        "allowed_roles": "app-role",
        "connection_url": f"postgresql://{{{{username}}}}:{{{{password}}}}@mi_postgres:5432/{POSTGRES_DB}?sslmode=require",
        "username": db_user,
        "password": db_pass
    }
    r = requests.post(f"{VAULT_ADDR}/v1/database/config/postgres_jit", headers=headers, json=payload)
    if r.status_code not in [200, 204]:
        raise Exception(f"❌ Error configurando postgres_jit: {r.text}")
    print("✅ Configuración postgres_jit creada.")

# Crear rol JIT
def create_jit_role(vault_token):
    headers = {"X-Vault-Token": vault_token}
    payload = {
        "db_name": "postgres_jit",
        "creation_statements": (
            "CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '{{password}}' VALID UNTIL '{{expiration}}';"
            "GRANT CONNECT ON DATABASE mi_base_datos TO \"{{name}}\";"
            "GRANT USAGE ON SCHEMA public TO \"{{name}}\";"
            "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";"
            "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO \"{{name}}\";"
        ),
        "default_ttl": "1h",
        "max_ttl": "4h"
    }
    response = requests.post(f"{VAULT_ADDR}/v1/database/roles/app-role", headers=headers, json=payload)
    if response.status_code not in [200, 204]:
        raise Exception(f"❌ Error creando rol JIT: {response.text}")
    print("✅ Rol dinámico app-role creado con permisos ampliados.")


# Main
def main():
    print("🚀 Iniciando setup completo de Vault y PostgreSQL...")

    vault_token = VAULT_DEV_ROOT_TOKEN_ID

    wait_for_vault_ready()
    create_policy(vault_token)
    enable_approle_auth_method(vault_token)
    create_approle(vault_token)
    role_id, secret_id = get_approle_credentials(vault_token)
    update_env_file(role_id, secret_id)

    db_password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*()", k=16))
    encryption_key = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%^&*()", k=32))

    delete_old_secrets(vault_token)
    store_in_vault(vault_token, "db_credentials", {"user": POSTGRES_USER, "password": db_password})
    store_in_vault(vault_token, "postgres_key", {"value": encryption_key})

    load_firebase_secret(vault_token)  # <<< carga json de Firebase

    update_postgres_password(db_password)
    enable_database_engine(vault_token)
    configure_postgres_engine(vault_token, POSTGRES_USER, db_password)
    create_jit_role(vault_token)

    print("🎉 Setup completo y exitoso.")

if __name__ == "__main__":
    main()
