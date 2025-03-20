CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Tabla de Usuarios
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    fec_alta TIMESTAMP NOT NULL,
    user_name TEXT NOT NULL,
    codigo_zip TEXT NOT NULL,
    direccion BYTEA NOT NULL,
    geo_latitud BYTEA NOT NULL,
    geo_longitud BYTEA NOT NULL,
    color_favorito TEXT NOT NULL,
    foto_dni BYTEA NOT NULL,
    ip BYTEA NOT NULL,
    avatar TEXT NOT NULL,
    fec_birthday TIMESTAMP NOT NULL
);

-- Tabla de Datos de Pago (SIN almacenar CVV para cumplir PCI DSS)
CREATE TABLE datos_pago (
    id SERIAL PRIMARY KEY,
    usuario_id INT REFERENCES usuarios(id) ON DELETE CASCADE,
    credit_card_num BYTEA NOT NULL, -- Cifrado en reposo
    cuenta_numero BYTEA NOT NULL,   -- Cifrado en reposo
    cantidad_compras_realizadas INT NOT NULL
);

-- Tabla de Autos del Usuario
CREATE TABLE autos (
    id SERIAL PRIMARY KEY,
    usuario_id INT REFERENCES usuarios(id) ON DELETE CASCADE,
    auto BYTEA NOT NULL,  -- Cifrado en reposo
    auto_modelo BYTEA NOT NULL,  -- Cifrado en reposo
    auto_tipo BYTEA NOT NULL,  -- Cifrado en reposo
    auto_color BYTEA NOT NULL  -- Cifrado en reposo
);

