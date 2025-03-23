import os
from dotenv import load_dotenv, dotenv_values

# Ruta al archivo .env
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../.env'))

def reload_env():
    """Forzar la recarga de las variables de entorno desde el archivo .env."""
    load_dotenv(dotenv_path=ENV_PATH, override=True)  # Cargar el .env y sobreescribir valores

def get_env_variable(key, default=None):
    """Leer desde el .env actualizado cada vez."""
    reload_env()  # Forzar la recarga al leer la variable
    env_vars = dotenv_values(ENV_PATH)
    return env_vars.get(key, default)
