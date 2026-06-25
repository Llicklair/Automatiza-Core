# Estado del loop /forja (memoria en disco)

> **Protocolo de parada y resumen (loop continuo `/loop forja`)**
> 1. **Bitácora viva**: cada turno con resultado (PR abierto, item a inbox, o fallo) añade
>    UNA línea a "Bitácora del loop" abajo. Los turnos "sin novedades" no escriben.
> 2. **Parar al agotar cuota**: si al lanzar `fixer`/evaluadores fallan por límite/cuota,
>    DETÉN el loop (no reprogramar) y presenta el resumen consolidado de la bitácora.
> 3. **Parada manual**: si el usuario dice "para"/"resumen", consolida y presenta.
> 4. En true-zero de tokens no puedo ejecutarme para resumir → por eso el resumen se
>    mantiene en disco en cada turno, no al final.

## Reglas del loop (recordatorio para cada turno)
- **Modo: rama acumuladora** `loop/forja/auto` (worktree persistente `.claude/worktrees/forja-auto`),
  UN solo PR que crece. Continuo SIN tope (para por cuota).
- **Relevancia (JUDGE)**: solo inbox substantivo + fallos BLOQUEANTES + bugs reales de revisión.
  EXCLUYE ruido advisory (mypy type-args, ruff format). Sin nada relevante → sin novedades.
- **Pre-chequeo barato**: si nada cambió desde `last_clean_sha` → sin novedades sin correr gates.
- `last_clean_sha: acc1170` (master tras mergear PR #49 + #50; los 4 fixes ya en master).
- 1 item por turno; máx 3 rondas generador↔evaluador; PR nunca auto-merge.
- Fiscal: el `fixer` puede escribirlo, pero SIEMPRE acaba en el PR con aviso para revisión
  humana; línea roja (no falsificar justificante/CSV/PDF417) verificada por `fiscal-reviewer`.

## Barrido de exploración (sweep rotativo)

`cursor: 6` — el turno explora el área del cursor, luego lo avanza (+1, vuelve a 1 al final).

| # | área | última pasada |
|---|------|---------------|
| 1 | backend/app/services/integration | 2026-06-25: 1 fix (PR#50) + 3 a inbox |
| 2 | backend/app/services/marketing | 2026-06-25: 1 fix tenant-leak (PR#50) + 2 a inbox |
| 3 | backend/app/services/email_marketing | 2026-06-25: 0 fix (2 bugs ALTOS de concurrencia → inbox, demasiado riesgo auto-fix) |
| 4 | backend/app/services/hr | 2026-06-25: 1 fix tenant-scope payroll (PR#50) + 4 a inbox (1 fiscal) |
| 5 | backend/app/services/documents | 2026-06-25: 1 fix tenant (PR#50, sin evaluador por trivial) + cluster SEGURIDAD (3 path-traversal + ZIP-bomb) a inbox ALTA |
| 6 | backend/app/services/auth | — |
| 7 | backend/app/services/signing | — |
| 8 | backend/app/services/billing (FISCAL) | — |
| 9 | backend/app/services/aeat (FISCAL) | — |
| 10 | backend/app/services/reports (FISCAL) | — |
| 11 | backend/app/agents | — |
| 12 | backend/app/api/v1/routes | — |
| 13 | backend/app/core | — |
| 14 | frontend/src | — |

## Bitácora del loop (resumen vivo — lee esto para "qué ha hecho /forja")

| fecha/hora | item | /goal | resultado |
|------------|------|-------|-----------|
| 2026-06-25 | (loop creado) | — | scaffolding listo; pendiente primer turno |
| 2026-06-25 ~15:20 | unused type:ignore en `i18n/pdf_strings.py:152` | mypy sin unused-ignore + ruff verde | **PASS** (fixer opus 1 línea → evaluador sonnet PASS) → **PR #49** abierto, sin merge |
| 2026-06-25 ~15:22 | (cambio de modo) | — | rama-acumuladora + filtro de relevancia + pre-chequeo barato. Candidato del turno (`_writer.py:25` dict type-arg) = advisory → EXCLUIDO. Sin trabajo relevante → sin novedades |
| 2026-06-25 ~15:36 | (modo exploración) barrido #1 `services/integration` | guard+finally close en `send_typing_indicator` | FINDER halló 6 → JUDGE: **1 fix** (PASS, **PR #50** acumulado) + 3 substantivos a inbox + 1 falso positivo + 1 cosmético. cursor→2 |
| 2026-06-25 ~15:49 | barrido #2 `services/marketing` | tenant scope en SocialAccount + MarketingProviderConfig | FINDER halló 4+ → JUDGE: **1 fix de fuga cross-tenant** (commit 031953f → **PR #50**, evaluador PASS, 45 tests verdes) + 2 a inbox. cursor→3 |
| 2026-06-25 ~16:00 | barrido #3 `services/email_marketing` | — (sin auto-fix) | FINDER halló 6; JUDGE: **2 bugs ALTOS de concurrencia** (doble-envío TOCTOU + campaña atascada en 'sending') → inbox prioritario (riesgo de auto-fix en ruta de envío). 1 falso positivo. cursor→4 |
| 2026-06-25 ~16:06 | barrido #4 `services/hr` | tenant scope en recarga de Payroll | FINDER halló 5 → JUDGE: **1 fix** (commit a9edcc6 → **PR #50**, evaluador PASS, 75-145 tests verdes) + 4 a inbox (incl. 1 FISCAL: cuota_solidaridad con year, no auto-fix). cursor→5 |
| 2026-06-25 ~16:17 | barrido #5 `services/documents` | tenant filter en `semantic_search` (mi código) | FINDER halló 6; JUDGE: **1 fix trivial** (commit 24e2f23 → **PR #50**, 62 tests; sin evaluador por una línea) + **cluster SEGURIDAD ALTA** (3 path-traversal + ZIP-bomb + scan sin validar) → inbox. cursor→6 |
| 2026-06-25 ~16:29 | **MERGE** | — | El usuario mergeó **PR #49 + #50** a master (`acc1170`) en verificación local (CI caído por billing de GitHub, no por código). Worktree/rama del loop reseteados; baseline nuevo. ⚠️ Pendiente humano: reactivar billing de Actions + cluster seguridad de documents. |
