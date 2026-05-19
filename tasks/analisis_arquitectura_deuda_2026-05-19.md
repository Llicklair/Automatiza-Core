# Análisis consolidado: arquitectura + deuda técnica — 2026-05-19

> Síntesis ejecutiva de dos auditorías paralelas. Detalle completo en:
> - [auditoria_arquitectura_2026-05-19.md](auditoria_arquitectura_2026-05-19.md)
> - [deuda_tecnica_2026-05-19.md](deuda_tecnica_2026-05-19.md)
>
> No duplica lo ya cubierto en [analisis-proyecto-2026-05-17.md](analisis-proyecto-2026-05-17.md) ni [analisis-modulos-erp-2026-05-18.md](analisis-modulos-erp-2026-05-18.md).

---

## El cuadro real

El proyecto **no es un desastre**. Es un sistema grande (67K LoC Python, 13 agentes, 25 servicios) con disciplina arquitectónica medible: ningún componente frontend salta `lib/api/`, ningún agente importa otro agente, los modelos DB no tienen lógica, las migraciones Alembic son lineales. Eso ya es más higiene que el 80% de las pymes-tech.

Lo que duele es **otra cosa**: deuda visible, no enterrada. Hay un puñado de incumplimientos puntuales del propio `ARCHITECTURE.md`, un bloque de multi-tenancy a medio rematar, y una red de tests muy fina para el tamaño del backend. Y un par de bugs documentados en `lessons.md` que siguen vivos en el código.

**Tres grandes ejes de dolor**, en orden de gravedad:
1. **Multi-tenant a medias** — 6 TODOs `Fase 3 RLS` en workers + interceptación de AIEmployees custom sin gate.
2. **Red de tests ausente** — 8 de 13 agentes sin `test_<agent>.py`, 21 de 25 servicios sin tests directos. Coverage backend ≈ 0.17%.
3. **Rutas con lógica de negocio** — 3 ofensores concretos (`import_bulk.py`, `client_portal.py`, `tenant.py`) que escriben modelos ORM y hacen `db.commit()` en la capa de transporte.

---

## Top hallazgos (cruzando ambas auditorías)

### Críticos (bloquean producción o riesgo de bug grave)

| # | Hallazgo | Origen | Esfuerzo |
|---|---|---|---|
| 1 | **Bug timeout empleados custom no se propaga** — vive desde lessons 2026-05-08 | `_dispatch_handlers.py::_invoke_dynamic_employee` | M |
| 2 | **Reverso de stock no se aplica al borrar albarán** — lessons 2026-05-15 | `services/sales/commands.py` (822 LoC) | M |
| 3 | **6 TODOs Fase 3 RLS en workers** — riesgo cross-tenant | `workers/tasks_node_engine.py:91,123` + `tasks_orchestrator.py:174,256` + `tasks_scheduler.py:188,244,301` | L |
| 4 | **ETL completo en ruta** — el peor ofensor arquitectónico | `api/v1/routes/import_bulk.py:42-145` | M |
| 5 | **Tokens criptográficos generados en ruta** — `secrets.token_urlsafe` + `_hash_token` sin service | `api/v1/routes/client_portal.py:78-92` | S |
| 6 | **Certificado .p12 validado + persistido en ruta** | `api/v1/routes/tenant.py:170-225` | S |
| 7 | **8 agentes sin tests directos** | banking, billing, compliance, crm, documents, excel, marketing, rag, recruitment | L |
| 8 | **~12 `except Exception` que tragan errores sin loggear** — lessons 2026-05-09 abierto | `agent_tools/documents.py:286`, `agent_tools/semantic_search.py:94`, `banking/_account_tools.py:62` | M |

### Altos (fricción real)

- **7 de 12 agentes sin `prompts.py`** — incumple patrón `CLAUDE.md`: banking, compliance, crm, documents, marketing, rag, recruitment.
- **8 módulos en `lib/api/` llaman `fetch()` directo** sin pasar por `client.ts` — admin, client_portal, presentacion, scanner, system, taskStream.
- **Servicios sin tests** — 21/25. Incluye billing/Verifactu, hr/IRPF, auth, workflow.
- **ExecutionContext pierde texto markdown entre steps** — workaround `response_preview` 800 chars frágil (lessons 2026-05-18).
- **Classifier cachea 24h sin TTL configurable** (lessons 2026-05-18).
- **AIEmployees custom interceptan dispatch antes que builtin** — cliente puede nombrar "facturación" y romper builtin (lessons 2026-05-18).
- **194 `: any` en TypeScript** frontend.
- **Sandbox experimental** sigue ahí pese a decisión de retirarlo (~45 min de limpieza).

### Medios (estructurales)

- **`agents/uploads/` con PDFs reales** dentro del paquete Python — anomalía estructural.
- **`agents/validators/`** mal nombrado — no es un agente, son utilidades transversales.
- **Recruitment + Marketing dispatchers** mezclados en `dispatchers/misc.py` mientras los demás tienen archivo propio.
- **`ARCHITECTURE.md` no distingue domain-service de infra-service** — `cache`, `scheduler`, `ws_relay`, `idempotency` parecen violar la regla "service recibe `db`" pero son infra de proceso. Vacío doctrinal.
- **Scripts `backend/scripts/test_*.py`** (4 ficheros, ~1.2K LoC combinados) duplican fixtures de pytest y `full_system_test.py` (1394 LoC) solapa con la suite real.
- **6 archivos >700 LoC** con responsabilidades mezcladas: `agent_report.py` (1010), `sales/commands.py` (822), `portal/page.tsx` (751), `hr.py route` (744), `analitica/page.tsx` (711), `classifier.py` (679).

---

## Plan de ataque unificado

### Sprint 1 (1 semana) — desbloquear pre-producción
**Objetivo: cerrar los dos bugs vivos y limpiar superficie inútil.**
- C1. Fix timeout empleados custom (M)
- C2. Reverso de stock en albaranes (M)
- A7. Retirar Sandbox experimental (XS)
- M1+M2. Decidir destino de `scripts/test_*.py` y `full_system_test.py` (S)
- i5. Mover `agents/uploads/` fuera del paquete Python (XS)

### Sprint 2 (1 semana) — multi-tenant
**Objetivo: cerrar Fase 3 RLS antes de que entre el primer cliente real.**
- C3. Resolver los 6 TODOs Fase 3 RLS en `workers/*` como un cambio coherente (L)
- A5. Gate o documentar la interceptación de AIEmployees custom (S)

### Sprint 3 (1-2 semanas) — red de seguridad
**Objetivo: poder refactorizar sin miedo.**
- C5. `test_<agent>.py` para los 8 agentes sin tests (L) — priorizar billing, hr, recruitment
- A1. Tests de servicios críticos: Verifactu, IRPF, AEAT, auth, workflow (L)

### Sprint 4 (1 semana) — saneamiento arquitectónico
**Objetivo: cerrar los incumplimientos del propio `ARCHITECTURE.md`.**
- Extraer `services/migration/bulk_import.py` y vaciar `import_bulk.py` (S)
- Extraer `services/client_portal/tokens.py` con `issue_token()` (S)
- Extraer `services/tenant/certificates.py` con `install_certificate()` (S)
- Añadir `prompts.py` a los 7 agentes que carecen (S)
- Enrutar `lib/api/*` por `client.ts`; añadir `requestBlob()` para descargas (S)
- Mover dispatchers `recruitment` y `marketing` a archivo propio (XS)
- Renombrar `agents/validators/` → `agents/shared/validators/` o `services/billing/validators.py` (S)
- Actualizar `ARCHITECTURE.md` con distinción domain-service vs infra-service (XS)

### Continuo / oportunista
- C8. Auditar y limpiar swallowers de `except Exception` (M)
- A3. Replantear `ExecutionContext` sin `response_preview` truncado (S)
- A4. TTL configurable en classifier (XS)
- A6. Reducir 194 `: any` TS por dominio (M)
- A9. Partir archivos >700 LoC por dominio (M cada uno)
- M3-M8. TODOs documentados (XS-S cada uno)
- B1-B6. Cosmético en PRs de oportunidad

---

## Lo que NO es deuda (pero podría parecerlo)

Esto sale en métricas pero no debería preocupar:
- **355 `except Exception`** — el 90% loggea + retorna `AgentResult(success=False)` correctamente. Solo ~12 son swallowers reales.
- **25 migraciones Alembic lineales** — head único, sano.
- **Frontend `package.json`** — `next 16.2`, `react 18.3`, `vitest 4`, `dompurify 3.3`. Stack al día.
- **Backend Poetry** — `fastapi ^0.115`, `sqlalchemy ^2.0.36`, `pydantic ^2.9`. Solo `langfuse 2.x → 3.x` pendiente, sin urgencia.
- **3 routes sin auth detectadas** — `__init__.py`, `erp.py` (agrupador), `verify.py` (público por diseño). No es vulnerabilidad.
- **9 ficheros con skip/xfail** — solo 1 `xfail` real (`test_api_projects.py:66`), el resto son `skipif` por dependencias opcionales.

---

## Conclusión

No es desastre — es un proyecto en pre-producción con **disciplina arquitectónica real** y **deuda visible y acotada**. Cuatro sprints cortos enfocados (5 semanas) cierran el 80% del dolor estructural. El resto es saneamiento continuo.

El proyecto está más cerca de producción de lo que se siente cuando lo miras de cerca.
