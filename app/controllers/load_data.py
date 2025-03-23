import requests
import os
import psycopg2
from dotenv import load_dotenv
from app.models.db import get_db_connection
from datetime import datetime

# Cargar variables de entorno desde .env
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path, override=True)

# Detectar entorno de ejecución
IS_LOCAL = os.getenv("RUN_ENV", "docker") == "local"
VAULT_ADDR = os.getenv("VAULT_ADDR1" if IS_LOCAL else "VAULT_ADDR", "http://localhost:8200")
VAULT_ROLE_ID = os.getenv("VAULT_ROLE_ID")
VAULT_SECRET_ID = os.getenv("VAULT_SECRET_ID")

# Variable global para evitar carga duplicada
data_loaded = False

def get_vault_token():
    """Obtener el token de Vault usando AppRole."""
    headers = {"Content-Type": "application/json"}
    auth_url = f"{VAULT_ADDR}/v1/auth/approle/login"
    response = requests.post(auth_url, json={"role_id": VAULT_ROLE_ID, "secret_id": VAULT_SECRET_ID}, headers=headers)

    if response.status_code == 200:
        return response.json()["auth"]["client_token"]
    else:
        raise Exception(f"❌ Error autenticando con Vault: {response.text}")

def get_encryption_key(vault_token):
    """Obtener la clave de cifrado desde Vault."""
    headers = {"X-Vault-Token": vault_token}
    response = requests.get(f"{VAULT_ADDR}/v1/secret/data/postgres_key", headers=headers)

    if response.status_code == 200:
        return response.json()["data"]["data"]["value"]
    else:
        raise Exception(f"❌ Error obteniendo la clave de cifrado desde Vault: {response.text}")


def fix_date_format(date_str):
    """Corrige el formato de fecha para PostgreSQL o asigna una fecha por defecto si es inválida."""
    try:
        date_obj = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
        return date_obj.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        print(f"⚠️ Fecha inválida detectada: {date_str}. Se usará la fecha por defecto '2000-01-01 00:00:00'.")
        return "2000-01-01 00:00:00"  # Fecha por defecto

def load_data():
    """Cargar todos los datos desde la API externa y almacenarlos en PostgreSQL con cifrado."""
    global data_loaded

    if data_loaded:
        print("⚠️ Los datos ya han sido cargados previamente. No se volverán a insertar.")
        return

    print("🔄 Iniciando carga de datos...")

    # Obtener datos desde la API externa
    external_api_url = "https://62433a7fd126926d0c5d296b.mockapi.io/api/v1/usuarios"
    response = requests.get(external_api_url)

    if response.status_code != 200:
        print(f"❌ Error al obtener datos de la API externa: {response.status_code}")
        return

    users_data = response.json()  # Procesar todos los usuarios

    # Obtener la clave de cifrado desde Vault
    vault_token = get_vault_token()
    encryption_key = get_encryption_key(vault_token)

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        for user in users_data:
            print(f"🔹 Procesando usuario: {user}")

            # Verificar si el usuario ya existe para evitar duplicados
            cursor.execute("SELECT id FROM usuarios WHERE user_name = %s", (user["user_name"],))
            existing_user = cursor.fetchone()

            if existing_user:
                print(f"⚠️ El usuario {user['user_name']} ya existe en la base de datos. No se insertará nuevamente.")
                continue

            # Corregir formato de fechas antes de insertar
            fec_alta = fix_date_format(user["fec_alta"])
            fec_birthday = fix_date_format(user["fec_birthday"])

            # Estructurar la consulta SQL con cifrado
            query = """
                INSERT INTO usuarios (
                    fec_alta, user_name, codigo_zip, direccion, geo_latitud, geo_longitud, 
                    color_favorito, foto_dni, ip, avatar, fec_birthday
                ) VALUES (
                    %s, 
                    %s, 
                    %s, 
                    pgp_sym_encrypt(%s, %s), 
                    pgp_sym_encrypt(%s, %s), 
                    pgp_sym_encrypt(%s, %s), 
                    %s, 
                    pgp_sym_encrypt(%s, %s), 
                    pgp_sym_encrypt(%s, %s), 
                    %s, 
                    %s
                )
                RETURNING id;
            """

            # Parámetros de la consulta
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

            # Ejecutar la consulta
            cursor.execute(query, params)

            # Obtener el ID del usuario insertado
            user_id = cursor.fetchone()[0]
            print(f"✅ Usuario insertado con ID: {user_id}")

            # 🔹 Insertar datos de pago si existen
            if "credit_card_num" in user and "cuenta_numero" in user and "cantidad_compras_realizadas" in user:
                print(f"💳 Insertando datos de pago para el usuario {user['user_name']} (ID: {user_id})")

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
                print(f"✅ Datos de pago insertados para usuario {user_id}")
            else:
                print(f"⚠️ No hay datos de pago para el usuario {user['user_name']}.")

            # 🔹 Insertar datos de autos cifrados si existen
            if "auto" in user and "auto_modelo" in user and "auto_tipo" in user and "auto_color" in user:
                print(f"🚗 Insertando auto cifrado para el usuario {user['user_name']} (ID: {user_id})")

                query_auto = """
                    INSERT INTO autos (usuario_id, auto, auto_modelo, auto_tipo, auto_color)
                    VALUES (%s, pgp_sym_encrypt(%s, %s), pgp_sym_encrypt(%s, %s), pgp_sym_encrypt(%s, %s), pgp_sym_encrypt(%s, %s));
                """

                params_auto = (
                    user_id,
                    user["auto"], encryption_key,
                    user["auto_modelo"], encryption_key,
                    user["auto_tipo"], encryption_key,
                    user["auto_color"], encryption_key
                )

                cursor.execute(query_auto, params_auto)
                print(f"✅ Auto cifrado insertado para usuario {user_id}")
            else:
                print(f"⚠️ No hay datos de auto para el usuario {user['user_name']}.")

        conn.commit()
        print("✅ Todos los datos se insertaron correctamente.")

        # Marcar como cargado
        data_loaded = True

    except psycopg2.Error as e:
        print(f"❌ Error en la base de datos: {e}")
        conn.rollback()
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("🔒 Conexión cerrada con éxito.")
