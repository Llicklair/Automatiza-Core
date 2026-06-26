# Inbox /forja v2 — auth / JWT / sesiones (2026-06-26, lente seguridad+correctitud)

Flujo: login/JWT/refresh/reset. FIX #1 (refresh revalida `is_active`) + FIX #2 (rate-limit `/refresh`) ya
hechos → PR #52, 144 tests verde + 3 regresión. El finder confirmó que el RESTO está SÓLIDO: firma+exp+`alg`
fijo HS256 (sin `alg:none` ni confusión HS/RS), `type` claim chequeado, `get_current_user` hace DB-lookup +
is_active por request, reset SHA-256 single-use TTL 1h, bcrypt tiempo constante, `forgot_password` sin
enumeración, tenant del token firmado. Quedan dos DELICADOS (decisión humana):

## Delicado (arquitectónico) — sin revocación real de refresh tokens
3. **`core/config.py:27` `REFRESH_TOKEN_EXPIRE_DAYS=30` + sin blacklist** — los refresh tokens son stateless;
   no hay tabla de sesiones ni blacklist, y no hay endpoint de logout que invalide el refresh token → "cerrar
   sesión" en el frontend es cosmético (el refresh token sigue válido hasta su expiración natural). Tras el
   FIX #1, un usuario DESACTIVADO ya no puede renovar (mitiga el caso peor), pero un token robado de un
   usuario ACTIVO sigue siendo válido 30 días sin posibilidad de revocar. Fix (decisión de producto):
   tabla de refresh tokens / blacklist con jti + endpoint logout que revoque, o bajar el TTL. Requiere
   esquema + diseño → revisión humana.

## Delicado (producto) — enumeración de cuentas en login
4. **`services/auth/service.py:51-55` login: 403 "Cuenta desactivada" vs 401 "credenciales incorrectas"** —
   la diferencia de código/mensaje permite a un atacante confirmar que un email existe (y está desactivado).
   No es bypass de acceso, pero facilita reconocimiento. Unificar en 401 genérico mejora la postura pero
   puede confundir a usuarios legítimos desactivados que no entienden por qué no entran → decisión de
   producto/UX. (Menor que la enumeración de `forgot_password`, que SÍ está bien resuelta.)
