# Proxy OAuth en el servidor (Render) — contrato

> Para no embeber `client_secret` de Meta en el binario. El backend local llama
> a estos endpoints; el **servidor de Render guarda los secrets** y hace las
> llamadas que los requieren. Si `OAUTH_PROXY_URL` está vacío, el backend usa el
> secret local (comportamiento actual) — el cliente ya está listo y con fallback.

## Activación

1. Implementar los endpoints de abajo en el servidor de Render (mismo despliegue
   que el license-server, p. ej. `https://automatizacore-license-server.onrender.com`).
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
- facebook/instagram → `POST graph.facebook.com/v18.0/oauth/access_token`
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

## Seguridad del proxy

- HTTPS obligatorio. Validar `state`/origen si se amplía.
- **Stateless**: no almacenar tokens de usuario; solo intercambiar y devolver.
- El proxy ve los tokens del usuario momentáneamente (inevitable en el
  intercambio). Para Google se recomienda PKCE-loopback (no proxy) y así su token
  no transita el servidor — ver nota en `auto_update_guide.md`.

## Cold start (Render free)

El primer intercambio tras inactividad puede tardar ~30-60 s (el dyno despierta).
Aceptable para una acción interactiva puntual (conectar cuenta). Si molesta, subir
de plan o un ping de keep-alive.
