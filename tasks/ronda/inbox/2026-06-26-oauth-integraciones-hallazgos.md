# Inbox /forja (run-2, híbrido) — OAuth Google/Microsoft (2026-06-26, lente seguridad)

Marco global: `generate_auth_url`→`set_oauth_state` (state EN MEMORIA)→`handle_oauth_callback`. FIX #2
(PKCE obligatorio en `exchange_code` de Google) ya hecho → PR #56, 32 tests verde.

## ✅ Verificado SÓLIDO (no defecto)
- **CSRF**: `handle_oauth_callback` devuelve `None` si el state no está en memoria (no hay fallback que
  extraiga tenant del string del state ni del token) → 400. El brief temía un fallback que continuara; NO
  existe. Sólido.
- **Tokens cifrados**: `encrypt_credentials({access_token, refresh_token})` antes de persistir (mismo
  mecanismo que PSD2/email). Sin tokens en claro en BD. Sólido.

## ⚠️ Media (operativo) — state en memoria rompe OAuth con multi-worker
4. **`services/integration/service.py:20` `_oauth_states` es un dict de proceso** — con Gunicorn/uvicorn
   **>1 worker**, el callback puede caer en un worker distinto al del authorize → `pop_oauth_state` da `None`
   → la integración falla con **400 aleatorio**. NO es agujero de seguridad (rechaza correctamente), es
   **disponibilidad/correctitud**: el OAuth fallaría de forma intermitente en producción escalada. Hoy
   probablemente corre 1 worker (no se nota), pero es un landmine al escalar. Fix: mover el store de state a
   **Redis/BD con TTL** (igual que el resto de estado compartido). Decisión de infra → revisión humana.

## Baja — grace period reutilizable
3. **`services/integration/service.py:31-32,235-236` `_completed_oauth` (120s)** retiene el state consumido
   para tolerar callbacks duplicados (Electron). Un `GET /callback?code=<cualquiera>&state=<completado>` en
   esos 120s devuelve 200 (éxito) **ignorando el `code` entrante**. No emite tokens nuevos ni los sobrescribe
   → no hay fuga de credenciales; el único "daño" es que un atacante confirma que el tenant tiene la
   integración activa (fuga menor de info). Fix opcional: validar/ignorar más estrictamente o acortar el TTL.
