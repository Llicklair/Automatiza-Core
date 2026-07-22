# Despliegue en servidor dedicado (self-hosted)

Un stack completo **por cliente**: sus datos viven en **su** servidor (un equipo
en el propio negocio o un VPS contratado por el cliente). Ideal para negocios
con **varios locales** (p. ej. varias tintorerías contra la misma base de
datos: stock unificado, facturación y cadena VeriFactu centralizadas).

> ⚠️ Estado: kit inicial. La composición está estructuralmente validada pero la
> **primera instalación real debe hacerse con calma en el servidor de destino**
> (no se ha ejecutado aún un despliegue completo end-to-end).

## Requisitos

- Servidor Linux (Ubuntu 22.04+ recomendado), 4 GB RAM mínimo.
- Docker + Docker Compose (`curl -fsSL https://get.docker.com | sh`).
- Un dominio (o subdominio) apuntando a la IP del servidor (registro A).
  El TLS lo emite Caddy solo (Let's Encrypt) — sin certificados manuales.

## Instalación

```bash
git clone <repo> automatizacore && cd automatizacore/deploy
cp .env.example .env
nano .env          # DOMAIN + SECRET_KEY (openssl rand -hex 32) + 2 contraseñas
docker compose up -d --build   # primera build: varios minutos
```

Al terminar: `https://TU-DOMINIO` → registro de la primera cuenta (tenant).

- Migraciones: se aplican solas en cada arranque del backend (`alembic upgrade head`).
- Rol de aplicación separado del owner (RLS efectivo): lo crea `init-db.sh`
  en el primer arranque del volumen de datos.

## Operación

| Tarea | Comando |
|---|---|
| Ver estado | `docker compose ps` |
| Logs | `docker compose logs -f backend` |
| **Actualizar** | `git pull && docker compose up -d --build` |
| Parar | `docker compose down` (los datos persisten en el volumen) |

## Backups (obligatorio antes de producción)

```bash
# Dump diario (añadir a cron del servidor):
docker compose exec -T db pg_dump -U pyme_user pyme_db | gzip > backup-$(date +%F).sql.gz
```

Conservar fuera del servidor (disco externo / otro equipo). La cadena VeriFactu
y el registro de jornada viven en esta BD: su conservación es obligación legal.

## Notas legales antes de vender esta modalidad

- **VeriFactu**: la declaración responsable describe la tipología e instalación
  del SIF — la modalidad "instalado en servidor del cliente" debe estar
  reflejada (consultar con el abogado antes de comercializarla).
- **RGPD**: si el servidor es un VPS contratado por el cliente, el encargado es
  el proveedor del VPS y el cliente sigue siendo responsable; si lo hosteas TÚ,
  pasas a ser encargado de tratamiento (contrato art. 28 RGPD).

## Qué NO incluye este modo

- Auto-update de Electron (aquí se actualiza con `git pull` + rebuild).
- El proxy HTTPS local de LAN y el certificado propio (aquí hay TLS real).
- El TPV, escáner móvil, portal de empleado, etc. funcionan igual: por
  navegador contra `https://TU-DOMINIO` desde cualquier local del negocio.
