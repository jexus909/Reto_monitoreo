import requests
import os
import psycopg2
from dotenv import load_dotenv
from app.models.db import get_db_connection
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger("load_data")

# Cargar variables de entorno
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path, override=True)

IS_LOCAL = os.getenv("RUN_ENV", "docker") == "local"
VAULT_ADDR = os.getenv("VAULT_ADDR1" if IS_LOCAL else "VAULT_ADDR", "http://localhost:8200")
VAULT_ROLE_ID = os.getenv("VAULT_ROLE_ID")
VAULT_SECRET_ID = os.getenv("VAULT_SECRET_ID")

data_loaded = False

def get_vault_token():
    headers = {"Content-Type": "application/json"}
    auth_url = f"{VAULT_ADDR}/v1/auth/approle/login"
    response = requests.post(auth_url, json={"role_id": VAULT_ROLE_ID, "secret_id": VAULT_SECRET_ID}, headers=headers)

    if response.status_code == 200:
        return response.json()["auth"]["client_token"]
    else:
        logger.error(f"Error autenticando con Vault: {response.text}")
        raise Exception("Error autenticando con Vault")

def get_encryption_key(vault_token):
    headers = {"X-Vault-Token": vault_token}
    response = requests.get(f"{VAULT_ADDR}/v1/secret/data/postgres_key", headers=headers)

    if response.status_code == 200:
        return response.json()["data"]["data"]["value"]
    else:
        logger.error(f"Error obteniendo clave de cifrado desde Vault: {response.text}")
        raise Exception("Error obteniendo clave de cifrado")

def fix_date_format(date_str):
    try:
        date_obj = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
        return date_obj.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return "2000-01-01 00:00:00"

def load_data():
    global data_loaded

    if data_loaded:
        logger.info("Carga de datos ya realizada previamente. Proceso omitido.")
        return

    logger.info("Inicio de carga de datos desde API externa")

    external_api_url = "https://62433a7fd126926d0c5d296b.mockapi.io/api/v1/usuarios"
    response = requests.get(external_api_url)

    if response.status_code != 200:
        logger.error(f"Error al obtener datos de la API externa: {response.status_code}")
        return

    users_data = response.json()

    vault_token = get_vault_token()
    encryption_key = get_encryption_key(vault_token)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for user in users_data:
            cursor.execute("SELECT id FROM usuarios WHERE user_name = %s", (user["user_name"],))
            if cursor.fetchone():
                continue

            fec_alta = fix_date_format(user["fec_alta"])
            fec_birthday = fix_date_format(user["fec_birthday"])

            query = """
                INSERT INTO usuarios (
                    fec_alta, user_name, codigo_zip, direccion, geo_latitud, geo_longitud, 
                    color_favorito, foto_dni, ip, avatar, fec_birthday
                ) VALUES (
                    %s, %s, %s,
                    pgp_sym_encrypt(%s, %s),
                    pgp_sym_encrypt(%s, %s),
                    pgp_sym_encrypt(%s, %s),
                    %s,
                    pgp_sym_encrypt(%s, %s),
                    pgp_sym_encrypt(%s, %s),
                    %s, %s
                )
                RETURNING id;
            """
            params = (
                fec_alta,
                user["user_name"],
                user["codigo_zip"],
                user["direccion"], encryption_key,
                user["geo_latitud"], encryption_key,
                user["geo_longitud"], encryption_key,
                user["color_favorito"],
                user["foto_dni"], encryption_key,
                user["ip"], encryption_key,
                user["avatar"],
                fec_birthday
            )
            cursor.execute(query, params)
            user_id = cursor.fetchone()[0]

            if all(k in user for k in ["credit_card_num", "cuenta_numero", "cantidad_compras_realizadas"]):
                query_pago = """
                    INSERT INTO datos_pago (usuario_id, credit_card_num, cuenta_numero, cantidad_compras_realizadas)
                    VALUES (%s, pgp_sym_encrypt(%s, %s), pgp_sym_encrypt(%s, %s), %s);
                """
                params_pago = (
                    user_id,
                    user["credit_card_num"], encryption_key,
                    user["cuenta_numero"], encryption_key,
                    user["cantidad_compras_realizadas"]
                )
                cursor.execute(query_pago, params_pago)

            if all(k in user for k in ["auto", "auto_modelo", "auto_tipo", "auto_color"]):
                query_auto = """
                    INSERT INTO autos (usuario_id, auto, auto_modelo, auto_tipo, auto_color)
                    VALUES (
                        %s,
                        pgp_sym_encrypt(%s, %s),
                        pgp_sym_encrypt(%s, %s),
                        pgp_sym_encrypt(%s, %s),
                        pgp_sym_encrypt(%s, %s)
                    );
                """
                params_auto = (
                    user_id,
                    user["auto"], encryption_key,
                    user["auto_modelo"], encryption_key,
                    user["auto_tipo"], encryption_key,
                    user["auto_color"], encryption_key
                )
                cursor.execute(query_auto, params_auto)

        conn.commit()
        data_loaded = True
        logger.info("Carga de datos completada exitosamente.")

    except psycopg2.Error as e:
        logger.error(f"Error en la base de datos: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("Conexión cerrada correctamente.")
