import psycopg2

# Datos de prueba (simulando la respuesta de la API)
usuario = {
    "fec_alta": "2021-07-31T00:11:06.741Z",
    "user_name": "Junior39",
    "codigo_zip": "22139",
    "direccion": "Amelia Forks",
    "geo_latitud": "-40.0728",
    "geo_longitud": "-39.5073",
    "color_favorito": "white",
    "foto_dni": "http://placeimg.com/640/480",
    "ip": "224.140.175.223",
    "avatar": "https://cdn.fakercloud.com/avatars/franciscoamk_128.jpg",
    "fec_birthday": "2022-03-29T03:28:16.364Z"
}

# Clave de cifrado obtenida desde Vault
encryption_key = "ClaveSegura12345"

# Conexión a PostgreSQL
conn = psycopg2.connect(
    dbname="mi_base_datos",
    user="default_user",
    password=")wCnkEajB8w5!T7t",
    host="localhost",
    port="5432",
    sslmode="require"
)
cursor = conn.cursor()

# Consulta de inserción con cifrado
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
    usuario["fec_alta"],
    usuario["user_name"],
    usuario["codigo_zip"],
    usuario["direccion"], encryption_key,
    usuario["geo_latitud"], encryption_key,
    usuario["geo_longitud"], encryption_key,
    usuario["color_favorito"],
    usuario["foto_dni"], encryption_key,
    usuario["ip"], encryption_key,
    usuario["avatar"],
    usuario["fec_birthday"]
)

# Ejecutar la consulta
cursor.execute(query, params)

# Obtener el ID del usuario insertado
user_id = cursor.fetchone()[0]
print(f"✅ Usuario insertado con ID: {user_id}")

# Confirmar la transacción
conn.commit()

# Cerrar conexión
cursor.close()
conn.close()
print("🔒 Conexión cerrada con éxito.")
