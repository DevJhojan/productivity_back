# 1. Imagen base oficial de Python (ligera y optimizada)
FROM python:3.12-slim

# 2. Establecer variables de entorno cruciales para Python en Docker
# Previerte que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE=1
# Asegura que los logs de Python se muestren en consola en tiempo real sin retrasos
ENV PYTHONUNBUFFERED=1

# 3. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 4. Instalar dependencias del sistema necesarias para compilar ciertas librerías (como psycopg2 para PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. Copiar primero el archivo de dependencias para aprovechar la caché de Docker
COPY requirements.txt /app/

# 6. Actualizar pip e instalar las dependencias del proyecto
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# 7. Copiar el resto del código del proyecto al directorio de trabajo
COPY . /app/

# 8. Expone el puerto en el que correrá la aplicación (coincidiendo con tu docker-compose.prod.yml)
EXPOSE 8000

# 9. Comando por defecto para arrancar la aplicación con Gunicorn en producción
# NOTA: Reemplaza 'core' por el nombre real de la carpeta que contiene tu archivo wsgi.py
CMD ["gunicorn", "productivity_back.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120"]
