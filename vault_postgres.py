import os
import requests
import psycopg2
from dotenv import load_dotenv

# 🔥 Cargar explícitamente el archivo .env 🔥
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path, override=True)

# 🔥 DEBUG: Verificar que las variables de entorno se están cargando correctamente 🔥
print(f"🔎 VAULT_ADDR: {os.getenv('VAULT_ADDR')}")
print(f"🔎 VAULT_ROLE_ID: {os.getenv('VAULT_ROLE_ID')}")
print(f"🔎 VAULT_SECRET_ID: {os.getenv('VAULT_SECRET_ID')}")
print(f"🔎 POSTGRES_DB: {os.getenv('POSTGRES_DB')}")

# Configuración de Vault
VAULT_ADDR = os.getenv("VAULT_ADDR")
VAULT_ROLE_ID = os.getenv("VAULT_ROLE_ID")
VAULT_SECRET_ID = os.getenv("VAULT_SECRET_ID")

# 🔹 Obtener el token dinámicamente desde `AppRole` 🔹
def get_vault_token():
    response = requests.post(f"{VAULT_ADDR}/v1/auth/approle/login", json={"role_id": VAULT_ROLE_ID, "secret_id": VAULT_SECRET_ID})
    if response.status_code == 200:
        client_token = response.json()["auth"]["client_token"]
        print(f"✅ Token obtenido con éxito: {client_token[:8]}******")  # 🔥 Solo mostramos los primeros 8 caracteres por seguridad
        return client_token
    else:
        raise Exception(f"❌ Error autenticando con Vault: {response.text}")

# 🔹 Obtener credenciales desde Vault 🔹
def get_db_credentials():
    vault_token = get_vault_token()  # 🔥 Obtenemos el token dinámicamente
    headers = {"X-Vault-Token": vault_token}
    
    response = requests.get(f"{VAULT_ADDR}/v1/secret/data/db_credentials", headers=headers)
    if response.status_code == 200:
        creds = response.json()["data"]["data"]
        print(f"✅ Credenciales obtenidas de Vault con éxito. Usuario: {creds['user']}")
        return creds["user"], creds["password"]
    else:
        raise Exception(f"❌ Error obteniendo credenciales de Vault: {response.text}")

# 🔹 Conectar a PostgreSQL 🔹
def connect_db():
    user, password = get_db_credentials()  # 🔥 Obtenemos credenciales desde Vault
    db_name = os.getenv("POSTGRES_DB")  # 🔥 Tomamos el nombre de la base de datos desde .env
    
    try:
        conn = psycopg2.connect(
            dbname=db_name,
            user=user,  # 🔥 Usamos `default_user` o el usuario de Vault
            password=password,  # 🔥 Tomamos la contraseña desde Vault
            host="localhost",  # Ajusta si PostgreSQL está en otro servidor
            port="5432"
        )
        print("✅ Conexión exitosa a PostgreSQL con credenciales seguras de Vault.")
        return conn
    except Exception as e:
        print(f"❌ Error conectando a PostgreSQL: {e}")

# 🔹 Prueba de conexión 🔹
if __name__ == "__main__":
    connect_db()
