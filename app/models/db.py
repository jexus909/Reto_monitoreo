import psycopg2
import os
from dotenv import load_dotenv
import requests

# Cargar las variables de entorno
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path, override=True)

# Función para obtener el token de Vault utilizando AppRole
def get_vault_token():
    VAULT_ADDR = os.getenv("VAULT_ADDR")
    VAULT_ROLE_ID = os.getenv("VAULT_ROLE_ID")
    VAULT_SECRET_ID = os.getenv("VAULT_SECRET_ID")
    
    # URL para la autenticación con AppRole
    auth_url = f"{VAULT_ADDR}/v1/auth/approle/login"
    
    # Datos de autenticación (usando role_id y secret_id)
    response = requests.post(auth_url, json={"role_id": VAULT_ROLE_ID, "secret_id": VAULT_SECRET_ID})

    if response.status_code == 200:
        # Extraer el token del cuerpo de la respuesta
        vault_token = response.json()["auth"]["client_token"]
        return vault_token
    else:
        raise Exception(f"❌ Error autenticando con Vault: {response.text}")

# Función para obtener las credenciales de PostgreSQL desde Vault
def get_postgres_credentials(vault_token):
    VAULT_ADDR = os.getenv("VAULT_ADDR")
    headers = {"X-Vault-Token": vault_token}
    
    # Obtener las credenciales de la base de datos desde Vault
    response = requests.get(f"{VAULT_ADDR}/v1/secret/data/db_credentials", headers=headers)
    
    if response.status_code == 200:
        data = response.json()["data"]["data"]
        postgres_user = data["user"]
        postgres_password = data["password"]
        return postgres_user, postgres_password
    else:
        raise Exception(f"❌ Error obteniendo las credenciales de PostgreSQL desde Vault: {response.text}")

# Función para obtener la conexión a PostgreSQL
def get_db_connection():
    # Obtener el token de Vault
    vault_token = get_vault_token()

    # Obtener las credenciales de PostgreSQL desde Vault
    postgres_user, postgres_password = get_postgres_credentials(vault_token)

    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
    
    # Establecer la conexión a PostgreSQL con las credenciales obtenidas de Vault
    conn = psycopg2.connect(
        dbname=POSTGRES_DB,
        user=postgres_user,
        password=postgres_password,
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        sslmode='require'
    )
    return conn
