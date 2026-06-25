# Inbox /forja — hallazgos en services/marketing (2026-06-25, barrido #2)

El loop arregló la fuga de tenant (#1+#2, en PR #50). Estos quedan para tu criterio:

## Para revisar
1. **`api/v1/routes/marketing.py:278` callback OAuth público sin expiración de state** [alta].
   `GET /marketing/zernio/callback/{state}` no lleva `get_current_user`; la única barrera es
   el `state` cifrado con `TENANT_ENCRYPTION_KEY`. No hay expiración ni nonce de un solo uso.
   Un state comprometido/replayado permite upsert de `SocialAccount`. Fix recomendado: añadir
   timestamp de expiración al payload cifrado y validarlo en `_zernio_unstate`, o registrar el
   state como nonce de un solo uso. Es cambio de diseño (como el callback de firma) → decisión humana.

2. **`publishing.py:82` `db.rollback()` sin try/except en el handler del batch** [media].
   Si la sesión PG está rota, el `rollback()` lanza y burbujea, rompiendo la respuesta del
   batch. Fix objetivo y pequeño (envolver en try/except + log). *Candidato a auto-fix en un
   próximo turno si quieres; lo dejé por el tope de 1 item/turno.*

## Nota
- `zernio_client.py:70` abre `httpx.AsyncClient` por llamada (sin pooling): ineficiente con
  lotes grandes, pero NO es bug (se cierra bien). Mejora opcional, no defecto.
