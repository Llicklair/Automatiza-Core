# Acceso remoto vía Cloudflare Tunnel — Fase 1

> Objetivo: que los empleados de **un** cliente accedan a AutomatizaCore **desde
> casa, sin instalar nada** (solo una URL en el navegador). El PC-servidor de la
> oficina (donde corre la app) publica un túnel saliente; nadie abre puertos.

## Topología

```
Empleado (casa, navegador)
        │  https://app.tudominio.com   (TLS de Cloudflare)
        ▼
Cloudflare Edge  ──►  Cloudflare Access (login de identidad)  ──►  Túnel
        ▼
cloudflared (corre en el PC-servidor de la oficina)
        ├─ /api/v1/*  +  /ws/*   →  http://localhost:8080  (backend FastAPI)
        └─ resto                 →  http://localhost:3000  (frontend Next.js)
```

Clave del diseño: **un solo hostname, ruteo por path**. El frontend resuelve la
URL del backend como **mismo origen** cuando se sirve tras un puerto estándar
(ver `frontend/src/lib/api/base.ts`), así que las llamadas van a `/api/v1/...`
sobre el mismo dominio → **no se dispara CORS** y el `:8080` **nunca** se expone
a internet.

## Lo que YA está preparado en el código (Fase 1)

- `base.ts` — resolver único de la base del backend/WS: absoluto a `:8080` en
  acceso directo (Electron/LAN), **mismo origen** tras el túnel. Lo usan el
  cliente HTTP, el reporter de errores y el WebSocket.
- `middleware/rate_limit.py` — el rate limit usa la **IP real** del visitante
  (`CF-Connecting-IP`) cuando el peer es loopback (el túnel local). Sin esto,
  todos los empleados compartirían un único cupo y se bloquearían entre sí.
- `core/net.py` + `routes/auth.py` — `/api/v1/auth/register` (crea tenant+admin)
  queda **bloqueado** salvo desde el equipo local. Ni la LAN ni el túnel pueden
  crear tenants en la BD del cliente.
- `main.py` — en producción (`DEBUG=False`) se ocultan `/docs`, `/redoc` **y**
  `/openapi.json`.

## Requisitos previos

1. Un dominio en Cloudflare (p. ej. `tudominio.com`) — plan gratuito vale.
2. `cloudflared` instalado en el PC-servidor.
3. La app corriendo: frontend en `0.0.0.0:3000` (ya por defecto), backend en
   `0.0.0.0:8080` (activa el toggle de red local en la app, o `_BACKEND_HOST=0.0.0.0`).
4. **`DEBUG=False`** en el backend (default). Verifícalo: con DEBUG=True se
   exponen los docs y el detalle de las excepciones.

## Paso a paso (túnel con nombre)

```powershell
cloudflared tunnel login                      # autoriza el dominio en el navegador
cloudflared tunnel create automatiza-<cliente># crea el túnel y su credencial .json
cloudflared tunnel route dns automatiza-<cliente> app-<cliente>.tudominio.com
```

Crea `config.yml` (junto a la credencial, normalmente `%USERPROFILE%\.cloudflared\`):

```yaml
tunnel: <TUNNEL_ID>
credentials-file: C:\Users\<usuario>\.cloudflared\<TUNNEL_ID>.json

ingress:
  # API REST del backend
  - hostname: app-<cliente>.tudominio.com
    path: ^/api/v1/.*
    service: http://localhost:8080
  # WebSocket de notificaciones (vive en raíz, NO bajo /api/v1)
  - hostname: app-<cliente>.tudominio.com
    path: ^/ws/.*
    service: http://localhost:8080
  # Todo lo demás → frontend. /docs, /metrics, /health, /lifecycle del backend
  # NO se enrutan aquí → quedan inalcanzables desde internet.
  - hostname: app-<cliente>.tudominio.com
    service: http://localhost:3000
  # Catch-all obligatorio
  - service: http_status:404
```

Arranca el túnel (y luego instálalo como servicio para que persista):

```powershell
cloudflared tunnel run automatiza-<cliente>
cloudflared service install            # opcional: arranque automático con Windows
```

## Cloudflare Access — el front-door de seguridad (OBLIGATORIO)

Pone una capa de identidad **delante del origen**: nadie llega ni a la pantalla
de login de la app sin pasar antes por Cloudflare. Neutraliza el brute-force de
internet y limita el acceso a los empleados del cliente.

1. Zero Trust → Access → Applications → **Add a self-hosted application**.
2. Domain: `app-<cliente>.tudominio.com`.
3. Policy: **Allow** → incluye los emails de los empleados (o el dominio de
   correo de la empresa), o Google/Microsoft SSO. Gratis hasta 50 usuarios.

Con Access activo, las cookies de identidad viajan en el mismo origen, así que
`fetch` a `/api/v1/*` y el WebSocket pasan sin fricción; la app valida además su
propio JWT por debajo (doble muro).

## Validación end-to-end (hazla TÚ antes de dar la URL al cliente)

1. Túnel + Access arriba; backend en `0.0.0.0:8080`, `DEBUG=False`.
2. Desde el móvil en **4G** (fuera de la WiFi de la oficina), abre la URL.
3. Pasa Access → login de la app → usa el ERP (lista facturas, abre el WS de
   notificaciones, descarga un PDF).
4. Comprueba que `https://app-<cliente>.tudominio.com/docs` y `/openapi.json`
   dan 404 (no se enrutan).

## Pendiente antes de dar de alta a los ~10 empleados (Fase 1.5)

Hallazgos de la revisión de seguridad aún abiertos (ver
`tasks/remote_access_fase1.md`). Aceptables para un piloto de 1 admin de
confianza; **a resolver antes de cuentas de empleado no-admin**:

- **RBAC (H2):** los bulk-import (`routes/import_bulk.py`) y los disconnect de
  integraciones (`routes/integrations.py`) los puede ejecutar cualquier usuario
  autenticado, no solo admin. Un empleado podría mutar datos en masa o
  desconectar el banco. Limitar a rol admin.
- **Lockout por cuenta (C2):** hoy solo hay límite por IP (`5/5min`). Añadir
  bloqueo por email tras N intentos. Cloudflare Access ya cubre el grueso del
  riesgo desde internet.
- **Token WS en la URL (H1):** `?token=` puede acabar en logs. Mover el token al
  primer mensaje del WS y acortar el TTL del access-token.
- **CORS en modo LAN (C3):** si algún cliente usa LAN directa (sin túnel),
  `FRONTEND_URL` debe incluir la IP LAN. En modo túnel (mismo origen) no aplica.

## Fase 2 (solo si llega un 2º cliente)

Productizar: empaquetar `cloudflared` en el instalador Electron, UI de
auto-provisión (crear túnel + hostname por cliente desde la app), y redirects
OAuth configurables (`PUBLIC_URL`) para integraciones desde remoto.
