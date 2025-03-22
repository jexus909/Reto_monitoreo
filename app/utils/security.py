def enmascarar_tarjeta(numero):
    """
    Enmascara un número de tarjeta (BIN + últimos 4): 676722XXXXXX5169
    """
    numero = numero.replace("-", "").replace(" ", "")
    if len(numero) < 10:
        return "XXXX"
    return numero[:6] + "X" * (len(numero) - 10) + numero[-4:]

def enmascarar_cuenta(numero):
    """
    Enmascara un número de cuenta (2 primeros + últimos 3): 50XXXX904
    """
    numero = numero.replace("-", "").replace(" ", "")
    if len(numero) < 5:
        return "XXX"
    return numero[:2] + "X" * (len(numero) - 5) + numero[-3:]

def decode_if_memoryview(value):
    """
    Convierte memoryview a string para serializar en JSON.
    """
    return value.tobytes().decode("utf-8") if isinstance(value, memoryview) else value
