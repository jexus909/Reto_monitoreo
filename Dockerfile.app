FROM python:3.9-slim

# Crear directorio
WORKDIR /app

# Copiar requisitos e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install flask flask-restful requests psycopg2-binary python-dotenv flasgger firebase-admin

# Copiar el resto del proyecto
COPY . .

# Puerto expuesto
EXPOSE 9090

# El comando real se define desde docker-compose
