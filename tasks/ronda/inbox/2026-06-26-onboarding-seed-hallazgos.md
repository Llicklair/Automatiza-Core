# Inbox /forja (run-2, híbrido) — onboarding seed demo (2026-06-26, lente correctitud+seguridad)

Marco global (GitNexus): `seed_demo_data` ← `post_seed` + 6 tests que codifican el contrato (demo
excluido de fiscal/visible en analítica/no consume serie/idempotente/clear borra solo demo). FIX #1
(advisory lock por tenant → idempotencia bajo concurrencia) ya hecho → PR #56. **Authz verificada como
sólida** (no es defecto). Queda uno:

## Baja — `clear_demo_data` sin rollback explícito ante error parcial
2. **`onboarding/seed.py:215-234`** — el borrado hace 3 operaciones (`db.delete` facturas en loop + flush,
   `delete(Product)`, `delete(Client)`) antes de un único `commit`, SIN `try/except` + `await db.rollback()`.
   Si salta una excepción a mitad (p.ej. FK externa no mapeada que referencie `Product`), la sesión queda
   en estado inconsistente y, si la ruta tampoco hace rollback, corrupta para el resto del request.
   Probabilidad baja (en condiciones normales no hay FK externa a Invoice fuera del cascade), pero correcto
   señalarlo. Fix: envolver en `try/except Exception: await db.rollback(); raise`. Verificar antes las FK
   reales a `Product`/`Invoice` demo. → revisión.

## Verificado — NO defecto
- ✅ Authz de `post_seed`/`clear`: `get_current_user` en todos los endpoints + `user.tenant_id` (no param
  manipulable) + RLS defensa en profundidad. Sólido.
- ✅ Contrato fiscal (is_demo en todo lo sembrado, no consume serie real, cascade ORM `Invoice.lines`):
  correcto en el código, como dice el marco global. (NO re-flaggear "demo en analítica".)
