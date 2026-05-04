# Plan de split de commits — WIP 2026-05-04

89 ficheros, +4332/−1148. Propuesta: **15 commits temáticos**, ordenados por dependencia (modelos → servicios → rutas → frontend).

> No ejecutado todavía. Confirmar uno a uno antes de aplicar.

## Hallazgo bloqueante: JWT portal sin uso

`create_client_portal_access_token` ([core/security.py](../backend/app/core/security.py)) y `get_current_client_portal` ([core/dependencies.py](../backend/app/core/dependencies.py)) están **definidos pero no se llaman en ningún sitio**. El portal hoy autentica con `ClientPortalToken` (raw token + hash en BD, default 90 días). El JWT corto es WIP a medio cablear.

**Decisión previa al commit**: o se completa el flujo (endpoint que intercambie raw_token → JWT y endpoints públicos del portal usando `get_current_client_portal`), o se revierte para no dejar dead code.

## Orden propuesto

| # | Tipo y ámbito | Ficheros | Notas |
|---|---|---|---|
| 1 | `chore: tooling y notas` | `.claude/settings.local.json`, `tasks/lessons.md`, `tasks/todo.md`, `backend/requirements.txt` | Independiente |
| 2 | `feat(db): modelos auth, hr, billing` | `db/models/__init__.py`, `auth.py`, `hr.py`, `billing.py` | Base para 3-7 |
| 3 | `feat(auth): JWT corto para portal cliente` | `core/security.py`, `core/dependencies.py` | **Bloqueado** hasta resolver el WIP |
| 4 | `refactor(hr): split cqrs queries+commands` | `services/hr/{commands,queries,service,_employee_docs,_payroll}.py` | Decidir si `service.py` queda o se elimina |
| 5 | `refactor(services): commands cleanup billing/crm/sales` | `services/{billing,crm,sales}/commands.py` | Continuación de e43b157 |
| 6 | `feat(api): endpoints HR (+372 líneas)` | `routes/hr.py`, `schemas/hr.py` | Depende de 2 y 4 |
| 7 | `feat(api): endpoints messaging y banking` | `routes/{messaging,banking,invoices,tenant}.py`, `services/banking/service.py` | Depende de 2 |
| 8 | `feat(api): registrar nuevos routers` | `api/v1/router.py` | Cierra 6 y 7 |
| 9 | `refactor(documents): contracts y snapshot` | `services/documents/{_contracts,service,snapshot}.py` | Independiente |
| 10 | `feat(workflow): scheduler y service` | `services/workflow/service.py`, `services/scheduler.py` | Independiente |
| 11 | `feat(agents): workflow agent + AI services` | `agents/workflow/agent.py`, `services/ai/{employee_crud,generative_ui}.py` | Depende de 4 si referencia HR commands |
| 12 | `feat(integrations): google drive client` | `integrations/google_drive_client.py` | Independiente |
| 13 | `chore(seed): seed_advanced_workflow` | `scripts/seed_advanced_workflow.py` | Tras 10-11 |
| 14 | `feat(frontend-api): módulos lib/api` | `lib/api/{banking,erp,hr,messaging,tenant,index}.ts`, `lib/api.ts` | Depende de 6, 7, 8 |
| 15 | `feat(frontend): páginas dashboard` | 33 páginas + 3 hooks + components compartidos (DataTable, GlobalSearch, nav-config, PageHeader, layout, EmpleadoFormModal) | Subdividir si rompe `tsc --noEmit` |

## Subdivisión sugerida del commit 15 (si es muy grande)

- 15a `feat(frontend/contabilidad)`: 5 páginas contabilidad + impuestos
- 15b `feat(frontend/ventas)`: 6 páginas ventas (facturas, pedidos, presupuestos, recurrentes, servicios)
- 15c `feat(frontend/tesoreria)`: 3 páginas tesoreria
- 15d `feat(frontend/rrhh)`: 5 páginas rrhh + 3 hooks + EmpleadoFormModal
- 15e `feat(frontend/crm-compras)`: 5 páginas crm + 2 compras
- 15f `feat(frontend/shared)`: data-table, layout, nav-config, GlobalSearch, PageHeader, layout, page.tsx raíz, _hooks/useDashboard

## Verificación entre commits

Tras cada commit, ejecutar:
- Backend (commits 2-13): `cd backend; python -m pytest tests/ -x` (al menos los tests del dominio tocado)
- Frontend (commits 14-15): `cd frontend; npx tsc --noEmit`
- Tras el último: `gitnexus_detect_changes({scope: "all"})`

## Riesgos

- **Commit 3 (auth portal)**: si se confirma JWT sin uso, mejor moverlo al final cuando esté el flujo completo, o revertir.
- **Commit 4**: el `service.py` residual en HR genera ambigüedad. Sugerencia: en este mismo commit decidir y eliminar `service.py` delegando a commands+queries.
- **Commit 15**: 33 páginas + componentes compartidos cambiados. Imprescindible `tsc --noEmit` antes de mergear; subdividir si falla.
