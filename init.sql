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

-- 🔑 obtener_usuario_por_username(...)
CREATE OR REPLACE FUNCTION obtener_usuario_por_username(key TEXT, uname TEXT)
RETURNS TABLE (
    user_name TEXT,
    codigo_zip TEXT,
    direccion TEXT,
    color_favorito TEXT,
    ip TEXT,
    avatar TEXT
)
AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.user_name, u.codigo_zip,
        pgp_sym_decrypt(u.direccion::bytea, key),
        u.color_favorito, pgp_sym_decrypt(u.ip::bytea, key), u.avatar
    FROM usuarios u WHERE u.user_name = uname;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 📊 obtener_datos_marketing_por_username(...)
CREATE OR REPLACE FUNCTION obtener_datos_marketing_por_username(key TEXT, uname TEXT)
RETURNS TABLE (
    user_name TEXT, color_favorito TEXT, avatar TEXT,
    cantidad_compras_realizadas INT, auto TEXT,
    auto_modelo TEXT, auto_tipo TEXT, auto_color TEXT
)
AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.user_name, u.color_favorito, u.avatar,
        dp.cantidad_compras_realizadas,
        pgp_sym_decrypt(a.auto::bytea, key),
        pgp_sym_decrypt(a.auto_modelo::bytea, key),
        pgp_sym_decrypt(a.auto_tipo::bytea, key),
        pgp_sym_decrypt(a.auto_color::bytea, key)
    FROM usuarios u
    JOIN autos a ON u.id = a.usuario_id
    JOIN datos_pago dp ON u.id = dp.usuario_id
    WHERE u.user_name = uname;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 🚨 obtener_datos_fraude_por_username(...)
CREATE OR REPLACE FUNCTION obtener_datos_fraude_por_username(key TEXT, uname TEXT)
RETURNS TABLE (
    user_name TEXT,
    geo_latitud TEXT,
    geo_longitud TEXT,
    ip TEXT,
    cantidad_compras_realizadas INT,
    credit_card_num TEXT,
    cuenta_numero TEXT
)
AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.user_name,
        pgp_sym_decrypt(u.geo_latitud::bytea, key),
        pgp_sym_decrypt(u.geo_longitud::bytea, key),
        pgp_sym_decrypt(u.ip::bytea, key),
        dp.cantidad_compras_realizadas,
        pgp_sym_decrypt(dp.credit_card_num::bytea, key),
        pgp_sym_decrypt(dp.cuenta_numero::bytea, key)
    FROM usuarios u
    JOIN datos_pago dp ON u.id = dp.usuario_id
    WHERE u.user_name = uname;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;