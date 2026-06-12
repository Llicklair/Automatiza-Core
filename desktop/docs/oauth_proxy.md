# Proxy OAuth en el servidor (Render) — contrato

> Para no embeber `client_secret` de Meta en el binario. El backend local llama
> a estos endpoints; el **servidor de Render guarda los secrets** y hace las
> llamadas que los requieren. Si `OAUTH_PROXY_URL` está vacío, el backend usa el
> secret local (comportamiento actual) — el cliente ya está listo y con fallback.

## Activación

1. Implementar los endpoints de abajo en el servidor de Render (mismo despliegue
   que el license-server: `https://automatizapyme-license-server.onrender.com`).
2. Mover los secrets `FACEBOOK_CLIENT_SECRET`, `INSTAGRAM_*`, `TWITTER_CLIENT_SECRET`,
   `LINKEDIN_CLIENT_SECRET` a las env vars del servidor de Render (NO en el cliente).
3. Fijar en el cliente `OAUTH_PROXY_URL=https://…onrender.com` (vía
   `service-manager.js::getBackendEnv` o `.env`).
4. Añadir esos `*_CLIENT_SECRET` a la denylist de `desktop/sanitize-env.js` para
   que dejen de viajar en `.env.dist`.

## Endpoints que debe exponer Render

### `POST /oauth/exchange`
Intercambia el authorization code por token (requiere el secret).

Request: `{ "platform": "facebook|instagram|twitter|linkedin", "code": "...", "redirect_uri": "..." }`

El servidor replica la lógica de `_exchange_token` (ver
`backend/app/services/marketing/oauth.py`) con su `client_id`+`client_secret`:
- facebook/instagram → `POST graph.facebook.com/v22.0/oauth/access_token`
- linkedin → `POST linkedin.com/oauth/v2/accessToken`
- twitter → `POST api.twitter.com/2/oauth2/token` (Basic auth client_id:secret)

Response: **el JSON del proveedor tal cual** (debe incluir `access_token`).

### `POST /oauth/fb-longtoken`
Convierte el user token de Facebook en uno de larga duración (`fb_exchange_token`,
requiere el secret).

Request: `{ "user_token": "..." }`
Response: `{ "access_token": "<long_lived_token>" }`

> El listado de páginas (`/me/accounts`) y los perfiles NO requieren secret →
> siguen ejecutándose en el cliente; no hay endpoint proxy para ellos.

### `GET /oauth/cb` — rebote HTTPS → callback local

Facebook/X/LinkedIn **no admiten `http://localhost`** como `redirect_uri` (error
"el dominio de esta URL no está incluido en los dominios de la aplicación"; además
el toggle "Aplicar HTTPS" está bloqueado en las apps nuevas). Solución: el redirect
registrado en cada red es esta URL **HTTPS** de Render, que hace `302` al callback
local:

```
GET /oauth/cb?code=…&state=…  →  302  http://localhost:8080/api/v1/marketing/oauth/callback?code=…&state=…
```

La red social solo ve una URL HTTPS válida; el navegador sí puede saltar a
`localhost`. Es *stateless* (no toca BD ni secrets).

## Flujo completo de conexión (redes sociales)

```
1. App → backend local POST /accounts/connect/{platform}  → devuelve auth_url
2. auth_url se abre en el navegador.
   redirect_uri = https://…onrender.com/oauth/cb  (lo fija _redirect_uri() cuando
   OAUTH_PROXY_URL está activo)
3. El usuario autoriza en la red social
4. Red social → 302 a https://…onrender.com/oauth/cb?code&state
5. Render /oauth/cb → 302 a http://localhost:8080/api/v1/marketing/oauth/callback?code&state
6. Backend local: decode state → POST {proxy}/oauth/exchange {code, redirect_uri=/oauth/cb, …}
7. Render /oauth/exchange usa el client_secret → token → lo devuelve al backend
8. Backend resuelve la Página/IG (sin secret) y guarda la cuenta cifrada
```

**Clave:** el `redirect_uri` de los pasos 2 y 6 **debe ser idéntico** (`/oauth/cb`)
o la red social rechaza el intercambio. Lo garantiza `_redirect_uri()`. Diagnóstico:
los fallos del callback se vuelcan a `%APPDATA%/AutomatizaPyme/oauth_debug.log`.

## Alta en el panel de cada red (checklist)

### Facebook / Instagram (developers.facebook.com)
1. **Casos de uso**: añade **"Administra todo en tu página"** (permisos `pages_*`)
   y, para IG, **"Administrar mensajes y contenido en Instagram"** por **Facebook
   Login** (NO la "Instagram API with Instagram Login", que usa scopes
   `instagram_business_*` distintos a los del código).
2. **Facebook Login → Configuración → URIs de redirección de OAuth válidos**:
   `https://automatizapyme-license-server.onrender.com/oauth/cb`
3. **Configuración → Básica → Dominios de la aplicación**:
   `automatizapyme-license-server.onrender.com`
4. **Roles**: tu cuenta como Admin/Tester (y **aceptar** la invitación). Para IG,
   además **Instagram Tester** aceptado desde la app de Instagram.
5. **Env vars en Render**: `FACEBOOK_CLIENT_ID`, `FACEBOOK_CLIENT_SECRET`
   (Instagram reusa los de Facebook). La cuenta IG debe ser Business/Creator
   vinculada a una Página.
6. **Producción** (que conecten clientes reales): exige **App Review** + verificación
   de negocio + política de privacidad + vídeo demo. En modo desarrollo solo
   funcionan las cuentas con rol aceptado.

### X (Twitter) y LinkedIn
- Mismo `redirect_uri` de rebote (`/oauth/cb`) en su panel + secrets `TWITTER_*` /
  `LINKEDIN_*` en Render.
- X usa **PKCE** (lo gestiona el cliente). LinkedIn está **aparcado** (su alta exige
  una Company Page, que pide un mínimo de conexiones).

## Seguridad del proxy

- HTTPS obligatorio. Validar `state`/origen si se amplía.
- **Stateless**: no almacenar tokens de usuario; solo intercambiar y devolver.
- El proxy ve los tokens del usuario momentáneamente (inevitable en el
  intercambio). Por eso **Google NO usa el proxy** (ver sección siguiente): su
  token de Gmail no debe transitar el servidor.

## Google (Gmail + Drive) — NO usa proxy, usa PKCE

A diferencia de las redes sociales, Google se queda **100% local** porque su token
da acceso al correo del usuario y no debe pasar por Render. El flujo
(`backend/app/integrations/google_oauth.py`) usa **PKCE S256** (RFC 7636):

- `generate_auth_url()` genera un `code_verifier` por flujo y envía
  `code_challenge=base64url(sha256(verifier))` + `code_challenge_method=S256`.
- El `verifier` se guarda junto al `state` (in-memory, TTL 600 s) y se reenvía en
  `exchange_code()` en el callback. El `redirect_uri` ya es local (el backend
  corre en `localhost`), así que es efectivamente un flujo loopback.

**El `GOOGLE_CLIENT_SECRET` se sigue embebiendo** (`sanitize-env.js` lo conserva):
Google exige el secret en el intercambio incluso con PKCE. Para que ese secret
deje de ser sensible, cambia el cliente OAuth en Google Cloud Console a tipo
**"Aplicación de escritorio" (Desktop app)**: Google trata su secret como **no
confidencial** por diseño, y PKCE aporta la protección real contra robo del code.
Mientras siga siendo un cliente *Web*, el secret es sensible pero PKCE igualmente
protege el intercambio. Cambiar de tipo de cliente no requiere tocar código (solo
`GOOGLE_CLIENT_ID`/`SECRET` nuevos en el `.env`).

## Cold start (Render free)

El primer intercambio tras inactividad puede tardar ~30-60 s (el dyno despierta).
Aceptable para una acción interactiva puntual (conectar cuenta). Si molesta, subir
de plan o un ping de keep-alive.
