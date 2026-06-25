---
name: cuadre
description: "Bucle de verificación fiscal. Descubre los cambios que tocan código fiscal/contable (VeriFactu, AEAT, facturación) desde la última pasada, los manda al revisor adversarial fiscal-reviewer, persiste los veredictos y SE DETIENE en una puerta humana — nunca auto-arregla ni auto-mergea código fiscal. Úsalo como /cuadre (una pasada) o /loop cuadre (en bucle)."
---

# /cuadre — el bucle que dice "no" antes de descuadrar a un cliente

Implementa los 5 movimientos de Loop Engineering (descubrir → delegar → **verificar** →
persistir → agendar) aplicados solo a lo fiscal. La regla de oro: **este bucle juzga,
no arregla**. El generador eres tú o el agente que escribió el código; el evaluador es
`fiscal-reviewer`. Nunca los mezcles en el mismo agente — un autor se aprueba solo.

## Rutas fiscales que vigila (el "radio de visión")
- `backend/app/services/aeat/` — `casillas_*.py`, `_casilla.py`, `preventive_check.py`
- `backend/app/services/billing/` — `registro_facturacion.py`, `verifactu_submit.py`,
  `backfill_verifactu.py`, `auto_accounting.py`, `commands.py`
- `backend/app/services/reports/fiscal.py`, `backend/app/services/reports/modelos_aeat.py`
- `backend/app/services/pdf_reports/_aeat_layout.py`, `_fiscal_modelo*.py`, `_fiscal_modelos.py`
- `backend/app/agents/billing/_invoice_write_tools.py`

## Movimientos (lo que haces en cada turno)

### 1. DISCOVERY — encuentra el trabajo tú mismo
- Lee el estado previo: `tasks/cuadre/state.md` (qué se revisó y hasta qué commit).
- Calcula qué cambió en las rutas fiscales **desde la última pasada**:
  ```
  git diff --name-only <last_sha>..HEAD -- backend/app/services/aeat backend/app/services/billing \
    backend/app/services/reports/fiscal.py backend/app/services/reports/modelos_aeat.py \
    backend/app/services/pdf_reports backend/app/agents/billing/_invoice_write_tools.py
  ```
  (si `state.md` no trae sha, usa el diff de trabajo: `git status --porcelain` sobre esas rutas).
- Si **no hay cambios fiscales nuevos** → escribe "sin novedades" en el estado y **TERMINA**.
  No inventes trabajo. Discovery pone el techo de calidad del bucle.

### 2. HANDOFF — delega aislado
- Agrupa los archivos cambiados por área (aeat / billing / reports / pdf / agents).
- Por cada área con cambios, lanza **un** subagente `fiscal-reviewer` (Agent tool,
  `subagent_type: "fiscal-reviewer"`). Pásale los archivos y el diff de su área.
- **Tope (circuit breaker): máximo 4 revisores por turno.** Si hay más áreas, prioriza
  VeriFactu/series y deja el resto en `./inbox/` para el siguiente turno. Registra qué dejaste.

### 3. VERIFICATION — el que dice "no"
- El subagente corre los tests fiscales reales y devuelve PASS / REJECT / BLOCKER.
- Tú NO sobreescribes su veredicto. Si dudas de un PASS, lanza un segundo revisor sobre
  esa misma área (modelo distinto) y quédate con el más estricto.
- Modelo distinto a propósito: el revisor corre en `sonnet` (ver su frontmatter) para no
  heredar los puntos ciegos del agente que generó.

### 4. PERSISTENCE — la memoria fuera del chat
- Anexa a `tasks/cuadre/state.md` una fila por área revisada:
  `| fecha | área | sha/diff | veredicto | fallos | acción |`
- El agente olvida; el repo no. Si no escribes aquí, mañana revisas lo mismo.

### 5. SCHEDULING / la puerta humana (lo que NO automatizas)
- **NUNCA** auto-arregles ni auto-mergees código fiscal. Tu salida son veredictos + un
  resumen para Marcos, no commits.
- REJECT y `RIESGO-LEGAL` → resúmelos arriba del todo, en claro, para revisión humana.
- Lo dudoso va a `./inbox/`, no a un PR.
- En `/loop cuadre`, cada turno solo mira lo nuevo desde el último estado; si no hay nada,
  no consume turnos en vano.

## Topes (ponlos siempre, asume que algo girará en vano de noche)
- Máx. 4 revisores/turno. Máx. 1 re-revisión por área. Sin reintentos infinitos de tests.
- Si en bucle local (`/loop`), recuerda: gasta tu suscripción Claude (compartida con el
  escritorio). No lo dejes corriendo toda la noche sin un intervalo razonable.

## Salida final al usuario (cada pasada)
1. **Veredicto global**: ¿hay algún REJECT/RIESGO-LEGAL? (lo primero, sin rodeos).
2. Tabla de áreas revisadas con su dictamen.
3. Qué quedó en `./inbox/` para el siguiente turno.
4. Ruta del estado actualizado: `tasks/cuadre/state.md`.

> La parte fácil es montar el bucle. La difícil — y la única que importa aquí — es que
> tenga dentro algo capaz de decir "no". Eso es `fiscal-reviewer`. Si alguna vez este
> bucle lleva muchas pasadas sin rechazar nada, sospecha del revisor, no lo celebres.
