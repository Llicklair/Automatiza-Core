# Migración: marketing social propio → Zernio (BYO)

**Decisión del usuario:** quitar toda la fontanería social propia (OAuth/publicación
de IG/FB/LinkedIn/X) y sustituirla por **Zernio** en modalidad **BYO** (cada usuario
configura su propia API key siguiendo una guía). **Google nativo (Gmail/Drive) e
email-marketing → INTACTOS** (Zernio no hace email).

## API de Zernio (verificada en docs)
- Base `https://zernio.com/api/v1` · Auth `Authorization: Bearer sk_...`
- Modelo: **Profile → Account(s) → Posts**
- Conectar: `GET /v1/connect/{platform}?profileId=X&redirect_url=...` → `authUrl`; vuelta con `?connected=...&accountId=Y&username=Z`
- Publicar: `POST /v1/posts` `{content, platforms:[{platform,accountId}], publishNow|isDraft|scheduledAt, mediaUrls}`
- Cuentas: `GET /v1/accounts` · Perfiles: `GET /v1/profiles` · Analítica: `GET /v1/analytics`
- Webhooks: HMAC-SHA256, idempotente por `X-Zernio-Event-Id`, ack <5s

## Etapas (additivo → recablear → demoler; verificar en cada una)

- [x] **E1 — Capa Zernio additiva (SAFE, nada se borra)** ✅
  - `services/marketing/zernio_client.py` (REST fino async, recibe api_key) ✅
  - `services/marketing/publisher_base.py` (`MarketingPublisher` Protocol + `PublishResult`) ✅
  - `core/config.py`: `ZERNIO_API_BASE` ✅
  - `tests/test_zernio_client.py` (httpx MockTransport, 6 tests) ✅
- [~] **E2 — Infra del módulo (SAFE, nada se borra)**
  - Modelo `MarketingProviderConfig(tenant_id único, api_key cifrada, default_profile_id)` ✅
  - Migración `0062_marketing_provider_config` (0061→0062, cadena verificada) ✅
  - `services/marketing/provider_config.py` (get/set key cifrada + `get_zernio_client`) ✅
  - `services/marketing/zernio_publisher.py` (`ZernioPublisher`, drop-in, 4 tests) ✅
  - [ ] Ruta connect vía Zernio (`GET authUrl` + callback que guarda accountId) — va con E3/E5
  - [ ] Repurpose `SocialAccount`: `account_id` = accountId de Zernio (campos de token se retiran en E4)
- [~] **E3 — Recablear consumidores a la interfaz**
  - [x] **E3a Publicación** ✅ — seam `services/marketing/publishing.py:get_publisher()`;
    los 3 puntos (`tasks_scheduler._publish_scheduled_posts`, ruta `/posts/{id}/publish`,
    ruta `/posts/publish-batch`) pasan a `ZernioPublisher`. IMPORTS OK + 10 tests verdes.
  - [x] **E3b Conexión** ✅ — ruta `connect` → resuelve profile + `client.connect_url()`;
    callback nuevo `/zernio/callback/{state}` (state cifrado en el path) hace upsert de
    `SocialAccount` con el accountId de Zernio. IMPORTS OK + test del state. ⚠️ Redirect
    real pendiente de smoke con la API key.
  - [x] **E3c Multi-cuenta + config** ✅ — `MarketingProviderConfig` pasa a **varias por
    tenant** (cada una = un email/key, free tier 2 cuentas c/u) + `SocialAccount.provider_config_id`.
    `provider_config.py` reescrito (multi). Endpoints `GET/POST/DELETE /marketing/zernio-config`
    (POST valida la key contra la API + cachea profile). `connect` elige cuenta; el callback
    vincula la red a su cuenta de Zernio; `ZernioPublisher` usa la key correcta por cuenta.
    IMPORTS OK + 12 tests verdes.
  - [x] **E3d** ✅ Tools del agente ya **agnósticas** (crean draft/scheduled + leen cuentas; no
    importan oauth/publisher). Analítica (`metrics.py`) → pendiente al cablear Zernio Analytics.

## ✅ SMOKE en vivo con la API key real (verificado 2026-06-16)
Contra la API real: **auth OK · `/profiles` (1 "Default", id `6a310c0c…`) · `/accounts` (0) ·
`/connect/instagram` → authUrl válido**. El contrato del `ZernioClient` cuadra con la API real.
Pendiente e2e: `POST /posts` (requiere cuenta conectada + intención de publicar).
(Script read-only: `c:\tmp\zernio_smoke.py`. La API key del usuario debe ROTARSE — se compartió en claro.)
- [x] **E4 — Demolición de lo viejo** ✅ (no queda NADA del OAuth viejo)
  - [x] Borrados `publisher.py` (viejo) + `oauth.py`; ruta vieja `oauth_callback` + import +
    `_log_oauth_error` + imports muertos (`traceback`/`app_data_dir`) eliminados. IMPORTS OK + 17 tests.
  - [x] `test_marketing_publish.py` reescrito (conserva la política de reintentos del scheduler).
  - [x] Borrados 3 tests OAuth obsoletos (`test_oauth_proxy`, `test_marketing_facebook`,
    `test_marketing_oauth_callback`) que importaban el `oauth.py` borrado y **rompían el suite**.
    Tras limpiar: **49 tests marketing+zernio verdes**.
  - [x] Borrado `oauth_tokens.py` (+ test); `metrics.py` reducido a lectura local
    (`get_campaign_metrics` + `_upsert_metrics`, sirve para Zernio Analytics); job
    `sync_marketing_metrics` retirado del scheduler. (Forzado al quitar los secretos OAuth.)
  - [x] Cosmético: secretos OAuth (Twitter/FB/IG/LinkedIn) + ruta `config_status` +
    `configStatus`/`MarketingConfigStatus` del frontend **eliminados**. `OAUTH_PROXY_URL`
    (imágenes) y `OAUTH_REDIRECT_URI` (base del connect) se quedan.
  - [x] **Enlaces a Zernio** en `TabCuentas` ("Crear cuenta gratis" → signup · "Conseguir
    API key" → dashboard/api-keys, vía `openExternal`). `tsc` limpio.
  - [x] Retiradas las columnas de token de `SocialAccount` (`access_token`/`refresh_token`/
    `token_expires_at`) — modelo + schema + interfaz TS + tests + migración `0063` (aplicada).
- [x] **E5 — Frontend** ✅ — `lib/api/marketing.ts`: interfaz `ZernioConfig` + API
  `zernioConfig` (list/add/delete) + `connect(platform, providerConfigId?)`.
  `TabCuentas.tsx` reescrito: sección **Cuentas de Zernio** (añadir/listar/borrar varios
  emails, "2 redes por email", validación de key) + selector de cuenta al conectar.
  `tsc --noEmit` sin errores. (Mantener TabCrear/Programados/Analitica/PlanIA tal cual.)
- [~] **E6 — Verificación**
  - 12 tests Zernio verdes + `tsc --noEmit` limpio + smoke en vivo contra la API real ✅
  - **Migración `0062` aplicada en BD local** ✅ (`alembic current` = `0062 (head)`)
  - Guía de usuario: `docs/marketing-zernio-setup.md` ✅
  - [ ] e2e final: conectar una red real + publicar (`POST /posts`) — en la app, lo haces tú.

## NO se toca
- `services/email_marketing/*` + rutas/modelos/UI de email.
- Integración Google nativa (Gmail/Drive) en `integraciones`.
- Dominio "marketing" del orquestador (el agente sigue; cambia solo la fontanería de publicación).
