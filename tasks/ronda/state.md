# Estado del bucle /ronda (memoria del proyecto en disco)

> **Protocolo de parada y resumen (bucle continuo `/loop ronda`)**
> 1. **Bitácora viva**: cada pasada con hallazgos añade UNA línea a la sección
>    "Bitácora del bucle" de abajo (fecha · qué revisó · veredicto · acción). Las
>    pasadas "sin novedades" NO escriben (evita bloat). Así el resumen está SIEMPRE
>    en disco aunque la sesión muera o se agoten los tokens.
> 2. **Parar al agotar cuota**: si al lanzar revisores fallan por límite/cuota
>    (errores de API repetidos), DETÉN el bucle (no reprogramar ScheduleWakeup) y
>    presenta el resumen consolidado leyendo la "Bitácora del bucle".
> 3. **Parada manual**: si el usuario dice "para"/"resumen", consolida la bitácora
>    y preséntala; deja de reprogramar.
> 4. Nota: en true-zero de tokens no puedo ejecutarme para resumir → por eso el
>    resumen se mantiene en disco en cada pasada, no al final.

El agente olvida; este archivo no. Cada pasada de `/ronda` añade una fila.
Última pasada revisada hasta: **2026-06-25 · working tree @ 08bf60c** (cambios sin commitear)

| fecha | área | capa | sha/diff | veredicto | fallos | acción |
|-------|------|------|----------|-----------|--------|--------|
| 2026-06-25 | fiscal (billing+reports+invoice tools) | service/agent | wt@08bf60c | **REJECT** | 347 suma rectificativas con signo dudoso (sin test); test_libro↔303 da falso "cuadre" (fixture de 1 solo trimestre); CSV duplica `_period_invoices_stmt` | revisar 347 + acotar/eliminar comentario "cuadran" |
| 2026-06-25 | seguridad/auth/core | core/service | wt@08bf60c | **REJECT** | `sessions.py:97` callback SELECT sin tenant; `dependencies.py:134` ClientPortalToken sin tenant; mypy gaps en security/config | añadir filtro tenant explícito (defensa en profundidad) → inbox para confirmar RLS |
| 2026-06-25 | email-marketing (nuevo) | service/route | wt@08bf60c | **REJECT** | `sender.py:37` worker en background lee campaña sin tenant_id; `delete_campaign` sin guarda de estado (TOCTOU); count vs insert TOCTOU; 22 símbolos sin tipo | añadir tenant_id al worker + guarda de estado → inbox para confirmar RLS |
| 2026-06-25 | marketing+integraciones | service/route | wt@08bf60c | **REJECT** | `publish_posts_batch` commit parcial sin try/except por ítem (listas published/failed mienten en fallo de red); `tenant_id` sin tipo; `frontend_origin()` vacío cuelga OAuth | envolver cada publish + anotar tipos |
| 2026-06-25 | hr+documents+admin | route/service | wt@08bf60c | **REJECT** | `search_documents` con lógica de negocio en la route (viola CLAUDE.md); `body: dict` crudo sin Pydantic (sin validación, DoS de tamaño); tests requieren DB (BLOCKER) | extraer a service + schemas Pydantic |

## Resolución (2026-06-25, misma sesión) — todos los REJECT atendidos

Verificado: `ruff check app/` ✓ · mypy sin errores nuevos en ficheros tocados ✓ · 17/17 tests ✓ (incl. nuevo `test_modelo_347_minora_rectificativas`) · imports ✓.

- **Fiscal**: el 347 NO tenía bug (rectificativas se guardan en negativo → ya neteaban). Era deuda de verificación → añadido test de regresión. Root-cause del descuadre libro↔303 resuelto: `build_libro_registro_csv` ahora reutiliza `_period_invoices_stmt` (mismo SELECT). Comentarios "cuadran" precisados (conjunto, no importe anual=trimestral).
- **Seguridad**: worker de email anclado a `tenant_id`; `ClientPortalToken` con filtro de tenant explícito (defensa en profundidad). `process_signed_callback` = **falso positivo** (callback externo sin auth, `rls_bypass()` deliberado y documentado en la route; el `session_token` de 128 bits es la capability) → sin cambio.
- **Correctitud**: `publish_posts_batch` commit por ítem + try/except; `delete_campaign` con guarda de estado ("sending"→409); TOCTOU count/list eliminado; `scheduled_at` pasado → 422; `frontend_origin()` con fallback+log.
- **Tipos**: módulos nuevos de email_marketing tipados (`tenant_id: UUID`, return types). `integrations.py`/`documents.py` pre-existentes fuera de scope (advisory en CI).

> Nota: estos cambios se commitearon y pushearon a `master` (f6fb297, fc6827e, 759864d).

## Bitácora del bucle (resumen vivo — lee esto para "qué ha hecho /ronda")

| fecha/hora | pasada | resultado |
|------------|--------|-----------|
| 2026-06-25 ~14:30 | review inicial (5 áreas) + fixes | 5 REJECT atendidos, verificado (ruff/mypy/17 tests), commiteado+pusheado a master |
| 2026-06-25 ~14:47 | iter. continua #1 | sin novedades de código (solo `.consejo/` + `.jsonl` generados, ignorados) |
