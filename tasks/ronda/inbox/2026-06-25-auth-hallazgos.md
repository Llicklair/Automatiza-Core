# Inbox /forja — hallazgos en services/auth (2026-06-25, barrido #6) ⚠️ área sensible

El loop arregló #4 (reset_password sin check is_active → PR #51). El resto NO se auto-arregló
(tocan el flujo de login o son decisiones de producto). Para tu criterio:

## Para revisar
1. **`service.py:132` timing oracle en login** [alta]. Cuando el email NO existe, `verify_password`
   no se llama → respuesta en µs; si existe pero la pass es mala → ~100ms (bcrypt). Un atacante
   distingue emails registrados midiendo tiempos (el rate-limit no lo mitiga: 1 petición/email).
   Fix propuesto: comparar contra un hash bcrypt dummy cuando `user is None` para igualar tiempos.
   ⚠️ Toca el flujo de LOGIN (radio de daño máximo) → revisión humana antes de tocar.

2. **`email_reset.py:78` token de reset crudo en logs (dev)** [alta/media]. La `reset_url` (con token)
   se loguea a INFO en entornos no-producción sin SMTP. En el escritorio Electron los logs van a
   disco sin cifrar (`%APPDATA%/AutomatizaPyme/`). Ya marcado como "intencional + hay test que lo
   verifica" en la revisión previa → es decisión de producto: ¿quitamos el log del enlace? Si sí,
   hay que actualizar el test que lo asierta.

3. **`service.py:208-213` mensajes de error distintos (enumeración de tokens)** [media]. "Enlace
   inválido" vs "ya utilizado" vs "expirado" se propagan al cliente → un atacante con un token
   distingue su estado. Mitigado por tokens de 32 bytes. Fix: mensaje genérico único al cliente
   (tradeoff seguridad-vs-UX, decisión humana).

4. **`service.py:189` retorno de `send_password_reset_email` ignorado** [baja]. Si el envío SMTP
   falla en producción, el token queda emitido, el usuario no recibe email y se devuelve 200. Fix:
   loguear/actuar si retorna False en producción.

## Follow-up del fix #4 (PR #51)
- Añadir test de regresión: usuario inactivo con token válido → ValueError sin mutar
  `hashed_password`/`used_at`; usuario activo → flujo completo. (Sugerido por evaluador, no bloqueante.)
