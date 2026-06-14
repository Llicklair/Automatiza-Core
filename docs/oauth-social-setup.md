# Configuración OAuth — Redes Sociales

El módulo de Marketing usa OAuth 2.0 para conectar cuentas de redes sociales.
El flujo es **completamente local**: la app Electron abre un popup → el usuario autoriza
en la red social → el callback llega al backend local (`localhost:8000`) → el token
se guarda en la BD local. Render/el servidor de licencias no interviene.

---

## Variables de entorno necesarias (`.env` del backend)

> **Dos modos de redirect.** Las redes sociales rechazan `http://localhost` (exigen HTTPS).
> - **Local/dev**: deja `OAUTH_PROXY_URL` vacío y registra el callback `localhost` de abajo.
>   Solo funciona con plataformas que aceptan localhost en modo desarrollo.
> - **Con proxy (recomendado para la app de escritorio)**: define `OAUTH_PROXY_URL`
>   (Render). El intercambio code→token ocurre en el servidor y debes registrar
>   `{OAUTH_PROXY_URL}/oauth/cb` como redirect en cada portal de desarrolladores.

```env
# URL de callback — debe coincidir exactamente con lo registrado en cada plataforma
OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/marketing/oauth/callback

# Proxy OAuth/imágenes (opcional). Si se define, registra {OAUTH_PROXY_URL}/oauth/cb
# como redirect en lugar del callback local.
OAUTH_PROXY_URL=

# Instagram / Facebook (una sola app Meta cubre ambas)
FACEBOOK_CLIENT_ID=tu_app_id
FACEBOOK_CLIENT_SECRET=tu_app_secret

INSTAGRAM_CLIENT_ID=tu_app_id        # mismo que Facebook si es una Meta app
INSTAGRAM_CLIENT_SECRET=tu_app_secret

# LinkedIn
LINKEDIN_CLIENT_ID=tu_client_id
LINKEDIN_CLIENT_SECRET=tu_client_secret

# Twitter / X
TWITTER_CLIENT_ID=tu_client_id
TWITTER_CLIENT_SECRET=tu_client_secret
```

---

## 1. Meta (Instagram + Facebook)

1. Ve a [developers.facebook.com](https://developers.facebook.com) → **Crear app** → tipo "Business"
2. Añade los productos: **Facebook Login** e **Instagram Basic Display**
3. En Configuración → Básica: copia `App ID` y `App Secret`
4. En Facebook Login → Configuración → URIs de redireccionamiento válidos:
   ```
   http://localhost:8000/api/v1/marketing/oauth/callback
   ```
5. Permisos necesarios: `pages_manage_posts`, `pages_read_engagement`, `user_profile`, `user_media`

> Durante desarrollo la app está en modo sandbox — solo usuarios añadidos como testers pueden conectar.

---

## 2. LinkedIn

1. Ve a [linkedin.com/developers](https://www.linkedin.com/developers) → **Create app**
2. En "Auth" → Authorized redirect URLs:
   ```
   http://localhost:8000/api/v1/marketing/oauth/callback
   ```
3. Permisos (Products): solicita **Share on LinkedIn** y **Sign In with LinkedIn using OpenID Connect**
4. Copia `Client ID` y `Client Secret`

---

## 3. Twitter / X

1. Ve a [developer.twitter.com](https://developer.twitter.com) → **Create Project** → **Create App**
2. En "User authentication settings":
   - Type of App: **Web App**
   - Callback URI:
     ```
     http://localhost:8000/api/v1/marketing/oauth/callback
     ```
   - Habilita OAuth 2.0
3. Permisos: `tweet.write`, `users.read`, `offline.access`
4. Copia `Client ID` y `Client Secret`

> Twitter usa PKCE. El backend envía `code_challenge=challenge` (método `plain`).
> El intercambio de token usa `code_verifier=challenge`.

---

## Flujo técnico

```
Frontend (Electron)
  └─ POST /api/v1/marketing/accounts/connect/{platform}
       └─ Backend genera state = base64("{platform}|{tenant_id}")
       └─ Devuelve auth_url con state
  └─ window.open(auth_url)  ← abre popup en el navegador del sistema

Usuario autoriza en la red social
  └─ Plataforma redirige a OAUTH_REDIRECT_URI?code=xxx&state=yyy

Backend (localhost:8000)
  └─ GET /api/v1/marketing/oauth/callback
       └─ Decodifica state → platform + tenant_id
       └─ Intercambia code por access_token (POST a la API de la plataforma)
       └─ Obtiene account_id y account_name del perfil
       └─ Guarda/actualiza SocialAccount en BD local
       └─ Devuelve HTML que cierra el popup y lanza evento "oauth-complete"

Frontend
  └─ Escucha evento "oauth-complete" → recarga lista de cuentas
```

---

## Notas de seguridad

- Los `access_token` se guardan **cifrados** en la BD (Fernet, AES-128 + HMAC) usando
  `TENANT_ENCRYPTION_KEY`. Ver `app/services/encryption.py` y `app/services/marketing/oauth_tokens.py`.
  Si la clave falta, el arranque del backend falla con instrucciones para generarla.
- Los tokens de Meta expiran en 60 días (long-lived token). LinkedIn en 60 días.
  Twitter puede emitir refresh tokens si se solicita `offline.access`.
- La `redirect_uri` debe ser exactamente igual en el `.env` y en el portal de desarrolladores.
