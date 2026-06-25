# Estado del loop /forja (memoria en disco)

> **Protocolo de parada y resumen (loop continuo `/loop forja`)**
> 1. **Bitácora viva**: cada turno con resultado (PR abierto, item a inbox, o fallo) añade
>    UNA línea a "Bitácora del loop" abajo. Los turnos "sin novedades" no escriben.
> 2. **Parar al agotar cuota**: si al lanzar `fixer`/evaluadores fallan por límite/cuota,
>    DETÉN el loop (no reprogramar) y presenta el resumen consolidado de la bitácora.
> 3. **Parada manual**: si el usuario dice "para"/"resumen", consolida y presenta.
> 4. En true-zero de tokens no puedo ejecutarme para resumir → por eso el resumen se
>    mantiene en disco en cada turno, no al final.
> 5. **AUTÓNOMO SIN CONFIRMACIONES** (instrucción del usuario, 2026-06-25): NO preguntar
>    "¿sigo?/¿continúo?" ni ofrecer opciones al final de cada turno. El loop continúa solo;
>    solo se detiene con un "para" explícito. Narración por turno MÍNIMA (qué se arregló o
>    sin novedades + nº de PR); reservar texto para hallazgos importantes o decisiones reales.

## Reglas del loop (recordatorio para cada turno)
- **Modo: rama acumuladora** `loop/forja/auto` (worktree persistente `.claude/worktrees/forja-auto`),
  UN solo PR que crece. Continuo SIN tope (para por cuota).
- **Relevancia (JUDGE)**: solo inbox substantivo + fallos BLOQUEANTES + bugs reales de revisión.
  EXCLUYE ruido advisory (mypy type-args, ruff format). Sin nada relevante → sin novedades.
- **Pre-chequeo barato**: si nada cambió desde `last_clean_sha` → sin novedades sin correr gates.
- `last_clean_sha: acc1170` (master tras mergear PR #49 + #50; los 4 fixes ya en master).
- **2ª pasada en adelante**: el primer barrido drenó lo obvio; re-escanear áreas SIN cambios
  solo re-encuentra lo ya en inbox. Prioridad ahora: (1) código NUEVO (commits/working-tree desde
  el último estado), (2) **drenar items LIMPIOS marcados "candidato a auto-fix" en inbox**, (3)
  re-exploración profunda solo si (1)(2) vacíos. Marca el item de inbox como RESUELTO al arreglarlo.
- 1 item por turno; máx 3 rondas generador↔evaluador; PR nunca auto-merge.
- Fiscal: el `fixer` puede escribirlo, pero SIEMPRE acaba en el PR con aviso para revisión
  humana; línea roja (no falsificar justificante/CSV/PDF417) verificada por `fiscal-reviewer`.

## Barrido de exploración (sweep rotativo)

`cursor: 1` — el turno explora el área del cursor, luego lo avanza (+1, vuelve a 1 al final).
**Primer barrido COMPLETO (14/14) el 2026-06-25.** Cursor vuelve a 1 → pasadas más profundas
(re-explorar puede encontrar lo que la primera pasada no vio, o nuevo código). NOTA: el frontend
(área 14) el loop NO lo auto-verifica (worktree sin node_modules) → sus fixes van a inbox para humano.

| # | área | última pasada |
|---|------|---------------|
| 1 | backend/app/services/integration | 2026-06-25: 1 fix (PR#50) + 3 a inbox |
| 2 | backend/app/services/marketing | 2026-06-25: 1 fix tenant-leak (PR#50) + 2 a inbox |
| 3 | backend/app/services/email_marketing | 2026-06-25: 0 fix (2 bugs ALTOS de concurrencia → inbox, demasiado riesgo auto-fix) |
| 4 | backend/app/services/hr | 2026-06-25: 1 fix tenant-scope payroll (PR#50) + 4 a inbox (1 fiscal) |
| 5 | backend/app/services/documents | 2026-06-25: 1 fix tenant (PR#50, sin evaluador por trivial) + cluster SEGURIDAD (3 path-traversal + ZIP-bomb) a inbox ALTA |
| 6 | backend/app/services/auth | 2026-06-25: 1 fix seguridad (reset is_active → PR#51, evaluador PASS, 111 tests) + 4 a inbox (timing login, token en logs, enum) |
| 7 | backend/app/services/signing | 2026-06-25: 0 fix (firma legal, no se gamblea); 5 a inbox, incl. ⚠️ firma marcada por string-search sin verificación cripto |
| 8 | backend/app/services/billing (FISCAL) | 2026-06-25: 1 fix numeración correlativa recurrentes en AMBAS rutas (commands cf5d814 + scheduler e2903a8 → PR#51; evaluador fiscal REJECT→round2→PASS, 259 tests) + 3 a inbox (⚠️ backfill VeriFactu excluye rectificativas) |
| 9 | backend/app/services/aeat (FISCAL) | 2026-06-25: 1 fix crash `_round2(None)` en 303 (35b7b91 → PR#51, evaluador fiscal PASS, 130 tests, sin cambiar cálculos) + 2 a inbox (⚠️ c27 incluye recargo; doble redondeo 390) |
| 10 | backend/app/services/reports (FISCAL) | 2026-06-25: 1 fix Modelo 200 resta retenciones soportadas (82310c8 → PR#51, evaluador fiscal PASS, 166 tests, alinea con docstring) + 2 a inbox (filtro nóminas snapshot vs 111; CSV float) |
| 11 | backend/app/agents | 2026-06-25: 0 fix (judgment/fiscal/ya-evaluado); 4 a inbox (billing tool_session vs RLS-sound, recursion_limit, timeout mismatch, enforce_tenant log) |
| 12 | backend/app/api/v1/routes | 2026-06-25: 1 fix microsoft_callback usa rls_bypass como google (c78221b → PR#51, evaluador PASS, 50 tests) + 4 a inbox (platform sin whitelist, html_body sin max_length, sender set_current_tenant, generate_plan refactor) |
| 13 | backend/app/core | 2026-06-25: 1 fix claims UUID malformados → 401 no 500 (1d33539 → PR#51, evaluador PASS, 118 tests) + 3 a inbox (⚠️ DB pass default vs check_secrets/riesgo desktop; JWTError granularidad; prefijo path employee) |
| 6 | backend/app/services/auth | — |
| 7 | backend/app/services/signing | — |
| 8 | backend/app/services/billing (FISCAL) | — |
| 9 | backend/app/services/aeat (FISCAL) | — |
| 10 | backend/app/services/reports (FISCAL) | — |
| 11 | backend/app/agents | — |
| 12 | backend/app/api/v1/routes | — |
| 13 | backend/app/core | — |
| 14 | frontend/src | 2026-06-25: 0 fix (loop no verifica frontend sin node_modules); 4 a inbox (⚠️ JWT en URL; JWT en localStorage web; fetch fuera de lib/api; portal sin refresh) |

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
| 2026-06-25 ~16:29 | **MERGE** | — | El usuario mergeó **PR #49 + #50** a master (`acc1170`/`9ccfdc9`) en verificación local (CI caído por billing de GitHub, no por código). Worktree/rama del loop reseteados; baseline nuevo. ⚠️ Pendiente humano: reactivar billing de Actions + cluster seguridad de documents. |
| 2026-06-25 ~16:39 | barrido #6 `services/auth` | reset_password rechaza is_active=False | FINDER halló 5 → JUDGE: **1 fix seguridad** (commit f838275 → **PR #51** nuevo acumulador, evaluador PASS, 111 tests) + 4 a inbox (timing oracle login, token en logs, enum mensajes). cursor→7 |
| 2026-06-25 ~16:44 | barrido #7 `services/signing` | — (0 fix, firma legal) | FINDER halló 5; JUDGE: nada auto-fixeable (by-design o cambios de protocolo/cripto). Todo a inbox; ⚠️ destacado: firma marcada por string-search sin verificación criptográfica. cursor→8 |
| 2026-06-25 ~16:50 | barrido #8 `services/billing` (FISCAL) | numeración correlativa recurrentes (commands + scheduler) | FINDER fiscal halló 4 → JUDGE: **1 fix en 2 rondas** (evaluador fiscal REJECT por incompleto → fix scheduler → PASS; commits cf5d814+e2903a8 → **PR #51**, 259 tests) + 3 a inbox (⚠️ backfill VeriFactu sin rectificativas). cursor→9 |
| 2026-06-25 ~17:17 | barrido #9 `services/aeat` (FISCAL) | crash `_round2(None)` en 303 | FINDER fiscal halló 3 (verificación numérica) → JUDGE: **1 fix** del crash (35b7b91 → **PR #51**, evaluador fiscal PASS, 130 tests, mirror de hermanas, sin cambiar cálculos) + 2 a inbox que SÍ cambian resultado (⚠️ c27 con recargo; doble redondeo 390). cursor→10 |
| 2026-06-25 ~17:30 | barrido #10 `services/reports` (FISCAL) | Modelo 200 resta retenciones soportadas | FINDER fiscal halló 3 → JUDGE: **1 fix** (82310c8 → **PR #51**, evaluador fiscal PASS, 166 tests; el código estaba desincronizado de su propio docstring) + 2 a inbox (filtro nóminas snapshot↔111 con caveat; CSV float). cursor→11 |
| 2026-06-25 ~17:45 | barrido #11 `app/agents` | — (0 fix) | FINDER halló 4; JUDGE: nada auto-fixeable limpio (billing tool_session ya cubierto por RLS-sound; recursion_limit marginal; timeout mismatch = decisión; enforce_tenant log = candidato futuro). Todo a inbox. cursor→12 |
| 2026-06-25 ~17:52 | barrido #12 `api/v1/routes` | microsoft_callback usa rls_bypass | FINDER halló 5 → JUDGE: **1 fix** (c78221b → **PR #51**, evaluador PASS, 50 tests; bypass simétrico a google) + 4 a inbox (platform whitelist, html_body max_length, sender tenant, generate_plan refactor). cursor→13 |
| 2026-06-25 ~18:02 | barrido #13 `app/core` | claims UUID malformados → 401 no 500 | FINDER halló 4 → JUDGE: **1 fix** (1d33539 → **PR #51**, evaluador PASS, 118 tests; defensivo, camino válido intacto) + 3 a inbox (⚠️ DB pass default/riesgo desktop; JWTError; prefijo path). cursor→14 |
| 2026-06-25 ~18:14 | barrido #14 `frontend/src` | — (0 fix) | FINDER halló 5; JUDGE: 0 auto-fix (loop NO verifica frontend sin node_modules → no se gamblea); todo a inbox (⚠️ JWT en URL + JWT en localStorage web = alta seguridad). **PRIMER BARRIDO COMPLETO 14/14.** cursor→1 (pasadas profundas) |
| 2026-06-25 ~18:20 | **drenaje inbox** (2ª pasada) | cap max_length email-marketing | Cambio de modo: drenar items LIMPIOS de inbox en vez de re-escanear. **1 fix** (cf4e0f0 → **PR #51**, 26 tests; sin evaluador por cap trivial verificado). Inbox routes #4 RESUELTO. |
| 2026-06-25 ~18:28 | drenaje inbox | scan_single valida con validate_upload | **1 fix** seguridad (527cc48 → **PR #51**, 64 tests; matiz de tipos verificado ⊆ ALLOWED_EXTENSIONS). Inbox documents-SEGURIDAD #5 RESUELTO. /scan rechaza .exe/.sh/>50MB. |
| 2026-06-25 ~18:35 | drenaje inbox | whitelist platform zernio | **1 fix** (8e316cf → **PR #51**, 51 tests). Inbox routes #3 RESUELTO. |
| 2026-06-25 ~18:38 | **LOOP DETENIDO** (usuario: "para") | — | Total sesión: **15 fixes verificados** (5 mergeados PR#49/#50 + 10 en PR#51 abierto) + ~25 hallazgos en inbox para humano (varios ALTOS seguridad/fiscal). Worktree `.claude/worktrees/forja-auto` queda (rama de PR#51). Pendiente humano: billing CI, mergear PR#51, triar inbox. |
