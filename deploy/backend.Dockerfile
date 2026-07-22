# Backend FastAPI — imagen de producción.
# Contexto de build: la RAÍZ del repo (ver docker-compose.yml).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Dependencias del sistema mínimas (lxml/pillow/reportlab traen wheels en 3.11).
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Migraciones (rol admin) y arranque del API (rol de aplicación).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 2"]
