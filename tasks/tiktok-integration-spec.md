# Integración TikTok — guía de implementación

> Fuente: deep-research sobre docs oficiales de TikTok (2026) + patrón de plataformas
> ya existente en el código. Complementa [`restructuracion-modulos.md`](restructuracion-modulos.md)
> y la metodología de [`iteraciones-cliente-real.md`](iteraciones-cliente-real.md).

## 0. Decisión (recap)
TikTok **sustituye a Facebook** mejor que Meta porque su auditoría **no pide documentos
de empresa** (solo política de privacidad + vídeo demo + descripción de datos, ~1-2 sem).
Dos modos:
- **Upload-to-Inbox** (`video.upload`): la API sube el vídeo a los borradores del usuario
  y **él lo publica desde la app de TikTok** → público **sin auditoría**. ← **empezar por aquí.**
- **Direct Post** (`video.publish`): la API publica directa. Sin auditar → contenido
  forzado a **privado (`SELF_ONLY`)** + máx 5 usuarios. Público → requiere **auditar tu app central**.

## 1. ⚠️ La diferencia grande: TikTok es VÍDEO/FOTO, no texto
Twitter/LinkedIn/FB publican texto. **TikTok exige media** (vídeo, o foto-carrusel). El
`content` (texto) del post pasa a ser el **caption/título**. Implica:
- `ScheduledPost` necesita un **`video_url`** (o `media_url`) → **migración Alembic** nueva.
- El flujo de "Crear post" en marketing debe pedir un vídeo cuando la red es TikTok.
- Subida en **2 pasos**: `init` (devuelve `upload_url` o acepta `PULL_FROM_URL`) → subir el binario (`FILE_UPLOAD`) **o** dar una URL (`PULL_FROM_URL`, que exige **dominio verificado** en el portal de TikTok).

## 2. Prerrequisitos (portal TikTok for Developers) — lo que TÚ configuras
1. Crear app en developers.tiktok.com; añadir **Login Kit** + **Content Posting API**.
2. Scopes: `user.info.basic`, `video.upload` (inbox) y/o `video.publish` (direct).
3. **Redirect URI** = el proxy: `https://automatizapyme-license-server.onrender.com/oauth/cb`.
4. (Solo si usas `PULL_FROM_URL`) **verificar el dominio** desde el que se sirve el vídeo.
5. `TIKTOK_CLIENT_ID` (= client_key) en el `.env` del cliente; `TIKTOK_CLIENT_SECRET` en **Render** (no en el binario).

## 3. Cambios de código (ficheros exactos)

### a) `backend/app/services/marketing/oauth.py`
- `connect_account` supported set (en `routes/marketing.py:224`): añadir `"tiktok"`.
- `_oauth_url`: rama tiktok →
  `https://www.tiktok.com/v2/auth/authorize/?client_key=…&scope=user.info.basic,video.upload&response_type=code&redirect_uri=…&state=…&code_challenge=…&code_challenge_method=S256` (usa el PKCE que ya tienes para Twitter).
- `_fetch_profile`: rama tiktok →
  `GET https://open.tiktokapis.com/v2/user/info/?fields=open_id,union_id,display_name` (Bearer); id = `data.user.open_id`, name = `display_name`. **Comprueba `status_code`** (como acabamos de hacer en Twitter).

### b) license-server `main.py` (Render)
- `_oauth_creds`: que devuelva `TIKTOK_CLIENT_ID/SECRET`.
- `/oauth/exchange`: rama tiktok →
  `POST https://open.tiktokapis.com/v2/oauth/token/` form: `client_key, client_secret, code, grant_type=authorization_code, redirect_uri, code_verifier`.

### c) `backend/app/services/marketing/oauth_tokens.py`
- `_refresh`: añadir `if account.platform == "tiktok": return await _refresh_tiktok(account)`.
- `_refresh_tiktok`: `POST …/v2/oauth/token/` con `grant_type=refresh_token`. **TikTok ROTA el refresh_token** (como Twitter) → persiste el nuevo (ya hay lógica para eso, oauth_tokens:58-60). Access 24h / refresh 365d.

### d) `backend/app/services/marketing/publisher.py`
- `_dispatch`: `elif platform == "tiktok": return await _publish_tiktok(token, content, video_url, mode)`.
- `_publish_tiktok` (modo **inbox**, sin auditoría):
  `POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/`
  body: `{"source_info": {"source":"PULL_FROM_URL","video_url": <url>}}` → devuelve `publish_id`.
  Para `FILE_UPLOAD`: init devuelve `upload_url`, haces `PUT` del binario por chunks.
- Modo **direct** (tras auditar): `…/v2/post/publish/video/init/` con `post_info` (`title`, `privacy_level`, etc.).
- Foto-carrusel: `…/v2/post/publish/content/init/` con `media_type=PHOTO`.

### e) `frontend/.../marketing/_components/constants.ts`
- Añadir a `PLATFORMS`: `{ id:"tiktok", name:"TikTok", limit:2200, colorClass:…, iconBg:… }`.
- Asegúrate de que el icono existe en `components/ui/social-icons.tsx`.

### f) DB
- Migración Alembic: `scheduled_posts.video_url TEXT NULL` (o `media_url`).

## 4. Camino mínimo recomendado (iterativo)
1. **Iteración A — OAuth TikTok**: 3a + 3b + 3c → conectar cuenta (test E2E del callback como `test_marketing_oauth_callback.py`).
2. **Iteración B — Upload-to-Inbox**: 3d (modo inbox) + 1 (video_url) + 3e → el usuario sube vídeo, se manda a su TikTok, él publica. **Sin auditoría, público.**
3. **Iteración C — Direct Post**: tras pasar la auditoría de TikTok, añadir el modo direct (público automático).

Cada iteración: red→green con un test que la replique (regla de oro del doc de iteraciones).

## 5. Por-cliente (qué configura cada negocio)
- Con **tu app central** (recomendado): el cliente **solo conecta su cuenta** (OAuth). El secret vive en Render. Igual que IG/X hoy.
- (Opcional BYO-app sandbox): un cliente avanzado podría meter su `TIKTOK_CLIENT_ID` propio, pero en sandbox el contenido sale **privado** → no recomendado para marketing.

## 6. Gotchas
- Contenido **privado** si tu app no está auditada (Direct Post). Inbox lo evita (publica el usuario).
- `PULL_FROM_URL` exige dominio verificado; si el vídeo es local del cliente, usa `FILE_UPLOAD`.
- Caps sin auditar: 5 usuarios/24h; con auditar: ~15 posts/día por creador.
- Tokens cortos (24h) → asegúrate de que `ensure_valid_token` refresca antes de publicar (ya lo hace).
