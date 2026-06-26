# Inbox /forja v2 — notificaciones / email / messaging (2026-06-26, lente errores+seguridad)

Flujo: envío de email (SMTP/Outlook) + handler de Telegram. FIX #2 (task de fondo sin ref → GC) y FIX #4
(smtplib bloqueante → `to_thread`) ya hechos → PR #52, 48 tests verde. Quedan dos de menor prioridad:

## Media/baja — saneado de cabecera de email (hardening; Python moderno mitiga)
1. **`services/email/service.py:253-254` y `281-283`** — `msg["Subject"] = subject` con `subject` venido
   del agente/LLM o payload sin sanear; y `Content-Disposition: attachment; filename={filename}` sin comillas
   ni escape. En Python 3.x moderno la asignación pasa por `Header` (folding) y serializar con `\r\n` crudo
   suele lanzar `HeaderParseError`, así que el riesgo de inyección real es BAJO/incierto — pero es hardening
   barato y correcto: `subject = subject.replace("\r", "").replace("\n", "")` antes de asignar; y filename
   entre comillas con `"` escapado (o `email.utils.encode_rfc2231`). Verificar primero que no rompe asuntos
   legítimos con acentos/emoji (el `Header` ya los codifica).

## Baja — inyección en el DSL de Google Drive (intra-tenant)
3. **`api/v1/routes/messaging.py:327`** — `query_filter = f"name contains '{q}'"` interpola el query param
   `q` (str sin validar) en la query de la Drive API. `q = "' or '1'='1"` → condición siempre-cierta. NO es
   fuga cross-tenant (el token OAuth es del propio tenant), por eso baja; pero un usuario del tenant puede
   listar más de lo previsto. Fix objetivo: escapar comillas simples → `q_safe = q.replace("'", "\\'")` y usar
   `f"name contains '{q_safe}'"`. (Drive API DSL, no SQL.)
