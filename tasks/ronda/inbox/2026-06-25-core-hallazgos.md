# Inbox /forja — hallazgos en app/core (2026-06-25, barrido #13)

El loop arregló #2 (claims UUID malformados → 401 no 500 → PR #51). Quedan:

## ⚠️ Verificar antes de tocar (riesgo escritorio)
3. **`config.py:54,57` passwords de BD por defecto (`pyme_pass`) no validadas en `check_secrets`** [media
   prod]. A diferencia de SECRET_KEY/TENANT_ENCRYPTION_KEY, arrancar con la password de BD por defecto
   NO se rechaza. Fix propuesto: añadir `pyme_pass` a `check_secrets`. ⚠️ PERO el escritorio usa PG
   embebida en :5433 — si usa esas credenciales, el check ROMPERÍA su arranque. Verifica qué credenciales
   usa el desktop (y en qué ENVIRONMENT corre) antes de añadir el check; quizá solo en production.

## Baja / diseño
1. **`security.py:91` `decode_token` captura `JWTError` genérico** [baja]. Comportamiento correcto hoy
   (expirado y firma-inválida → ambos None → 401), sin bypass. Mejora de auditoría: distinguir/loggear
   `ExpiredSignatureError` vs firma inválida. Diferible.
4. **`dependencies.py:33` filtro de rol `employee` por `startswith("/api/v1/portal/")`** [baja]. Frágil:
   una futura ruta `/api/v1/portal-admin/` haría match por prefijo. No explotable hoy (no existe esa ruta).
   Revisar antes de añadir rutas con ese prefijo; considerar match exacto por segmento.

## Follow-up del fix #2 (PR #51)
- Test sugerido (evaluador): JWT firmado con `sub="INVALID"` → `get_current_user` debe dar 401, no 500.
