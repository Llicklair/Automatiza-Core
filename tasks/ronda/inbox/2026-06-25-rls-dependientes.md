# Inbox /ronda — hallazgos que dependen de confirmar RLS (2026-06-25)

> **ESTADO: RESUELTO — NO es trabajo pendiente.** (1) sender y (2) dependencies: filtro de
> tenant explícito añadido y commiteado (f6fb297). (3) sessions: falso positivo (callback
> externo con `rls_bypass()` deliberado). El discovery de /forja debe SALTAR este fichero.

Estos 3 hallazgos los marcaron los jueces como [alta] por **falta de filtro de tenant
explícito** en la consulta. Pero su gravedad real depende de si el listener RLS global
(fail-closed) está activo en ESE contexto de sesión. El bucle no puede decidirlo solo —
es juicio humano. Confirmar para cada uno si la sesión pasa por `set_current_tenant`:

1. **`services/email_marketing/sender.py:37`** — worker en background lee `EmailCampaign`
   por `campaign_id` sin `tenant_id`. ¿La sesión del BackgroundTask fija el tenant? Si NO
   → o bien RLS lo bloquea (fail-closed, denegado) o hay fuga real. La ruta sí valida
   tenant antes de encolar; el worker no re-valida. **Fix barato y correcto igualmente:**
   añadir `EmailCampaign.tenant_id == UUID(tenant_id)` al WHERE (el tenant_id ya llega).

2. **`core/dependencies.py:134`** — `ClientPortalToken` se busca por `client_id`+`is_active`
   sin `tenant_id`. ¿El modelo lleva `tenant_id` y el RLS lo filtra aquí? Fix explícito:
   añadir `ClientPortalToken.tenant_id == UUID(tenant_id)`.

3. **`services/signing/sessions.py:97`** — `process_signed_callback` filtra solo por
   `session_token` (128 bits, difícil de adivinar) sin tenant. El callback puede no pasar
   por `get_current_user` → ¿se fija el tenant? `get_signing_status` (línea 156) SÍ filtra
   por tenant: el patrón correcto ya existe en el mismo archivo.

> Regla del proyecto (memoria): el aislamiento RLS es sólido (listener global + fail-closed).
> Si lo confirmas, estos 3 son **defensa en profundidad** (recomendable, no P0). Si en alguno
> la sesión NO fija tenant y RLS no aplica → es P0 de fuga entre clientes.
