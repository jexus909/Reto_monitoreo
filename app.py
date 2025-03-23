from flask import Flask
from app.controllers.load_data import load_data  # Llamar al módulo que realiza la carga
from app.routes.api_routes import api_bp  # Importar rutas de la API
from app.decorators.auth import cargar_credenciales_firebase  # Importamos la función desde auth.py
import threading
import time  # Importamos time para hacer la pausa
from app.utils.env_utils import get_env_variable


app = Flask(__name__)

# Registrar las rutas de la API
app.register_blueprint(api_bp, url_prefix='/api')

# Usamos una bandera global para asegurarnos de que los datos solo se carguen una vez
data_loaded = False

# Función para cargar los datos en un hilo
def load_data_in_background():
    """
    Cargar los datos en un hilo en segundo plano al inicio del servidor
    """
    global data_loaded
    if not data_loaded:
        print("Iniciando la carga de datos desde la API externa...")
        load_data()  # Llamar a la función que realiza la carga de datos
        data_loaded = True  # Marcar como cargado para evitar futuras cargas
        print("Datos cargados con éxito.")
    else:
        print("Los datos ya han sido cargados previamente.")

# Ejecutar la carga de datos en un hilo en segundo plano al iniciar el servidor
def start_load_data():
    print("Arrancando el servidor Flask...")
    thread = threading.Thread(target=load_data_in_background)
    thread.start()

if __name__ == "__main__":
    # **Cargar las credenciales de Firebase** al iniciar la aplicación
    if cargar_credenciales_firebase():
        print("✅ Firebase Admin SDK inicializado correctamente.")
    else:
        print("❌ No se pudo inicializar Firebase Admin SDK desde Vault.")
    
    # Pausar 30 segundos antes de iniciar la carga de datos
    print("⏳ Pausando 5 segundos para verificar la carga de Firebase...")
    time.sleep(5)  # Pausa de 30 segundos

    # Iniciar la carga de datos
    start_load_data()
    print("📡 Rutas activas en Flask:")
    #print(app.url_map)

    # Ejecutar el servidor de Flask
    app.run(
        ssl_context=('certs/ssl.crt', 'certs/ssl.key'),  # Usar los certificados SSL generados
        debug=False,
        host='0.0.0.0',  # Aceptar conexiones de cualquier IP
        port=9090  # Puerto para HTTPS
    )