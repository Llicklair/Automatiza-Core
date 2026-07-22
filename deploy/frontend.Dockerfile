# Frontend Next.js — imagen de producción.
# Contexto de build: la RAÍZ del repo (ver docker-compose.yml).
FROM node:20-alpine

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
