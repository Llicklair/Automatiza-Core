# Diagnóstico salud estática del backend

Fecha: 2026-06-22 · Entorno: Windows, Poetry 2.3.4, Python 3.11.9, ruff 0.7.4, mypy 1.20.2, pytest 9.0.3
Réplica del job `backend-lint` de `.github/workflows/ci.yml`.

## 1. Ruff lint (BLOQUEANTE) — PASA

Comando: `ruff check app/ --select E,W,F,I --ignore E501,E402,E701,E702,E731,W293`

- Exit code: 0 — **All checks passed!**
- Violaciones: 0
- El gate bloqueante de CI está verde.

## 2. Ruff format --check (advisory) — DIVERGE

Comando: `ruff format app/ --check`

- Exit code: 1
- 365 ficheros se reformatearían / 291 ya formateados (total 656).
- Advisory: no bloquea CI, pero >55% del árbol diverge del estilo de formato.

## 3. Mypy --strict (advisory) en app/agents + app/services — 1587 errores

Comando: `mypy app/agents app/services --strict --ignore-missing-imports --no-error-summary`

- Exit code: 1
- Total errores: **1587** (+ 27 notes)

Top categorías (código + conteo):
| Código | Conteo | Significado |
|--------|--------|-------------|
| type-arg | 737 | Falta argumento de tipo en genérico (p.ej. `dict` sin `[K,V]`) |
| no-untyped-def | 489 | Función sin anotación de tipo |
| no-untyped-call | 242 | Llamada a función sin tipar desde contexto tipado |
| no-any-return | 90 | Retorno declarado tipado devuelve Any |
| name-defined | 13 | **Nombre no definido — posible bug real** |
| unused-ignore | 11 | `# type: ignore` innecesario |
| untyped-decorator | 5 | Decorador sin tipar |

Top 5 ficheros por nº de errores:
1. app\services\pdf_reports\_snapshot_monthly.py — 41
2. app\services\pdf_reports\_fiscal_modelos.py — 37
3. app\services\pdf\pdf_base.py — 34
4. app\services\pdf_reports\_fiscal_report.py — 33
5. app\services\hr\queries.py — 32 (empatan: hr\commands.py, ai\employee_crud.py)

### Nota: name-defined (13) — los únicos que huelen a bug, no a deuda de tipos
Todos en 2 ficheros del módulo workflow:
- app\services\workflow\_execution.py
- app\services\workflow\service.py

Patrón: `Name "models.Workflow" / "models.Task" / "models.WorkflowExecution" is not defined`.
Probablemente `models` se importa solo bajo `TYPE_CHECKING` o falta el import del símbolo; mypy no resuelve esos nombres. Conviene revisarlo (no es solo ruido de --strict).

### unused-ignore (11) ficheros:
i18n\tenant_locale.py (4), workers\celery_tasks.py (2), execution_context.py, billing\verifactu_mode.py, autonomy.py, ai\stream_tokens.py, i18n\pdf_strings.py.

## 4. Pytest --collect-only (sin BD) — OK

Comando: `pytest tests/ --collect-only -q`

- Exit code: 0
- **2239 / 2280 tests recogidos** (41 deselected por marcadores/config).
- Errores de colección/import: **0**. Ningún módulo falla al importar.
- Módulos con más tests: test_prompt_e2e.py (68), test_billing_validators.py (64), test_core_exceptions.py (37).
