---
name: ronda
description: "Bucle de verificación de TODO el proyecto (Loop Engineering). Descubre los cambios desde la última pasada, enruta cada uno a su juez adversarial — fiscal-reviewer para código fiscal, code-reviewer para el resto de backend y frontend — corre las puertas reales de CI, persiste veredictos y SE DETIENE en una puerta humana. Nunca auto-arregla ni auto-mergea. Úsalo como /ronda (una pasada) o /loop ronda (en bucle)."
---

# /ronda — el bucle que patrulla todo el proyecto y dice "no"

Implementa los 5 movimientos de Loop Engineering (descubrir → delegar → **verificar** →
persistir → agendar) sobre TODO el repo, no solo lo fiscal. Regla de oro: **este bucle
juzga, no arregla**. El generador es quien escribió el código; el evaluador es un agente
**separado** (modelo distinto, `sonnet`) que asume que está roto. Nunca los fusiones: un
autor se aprueba solo.

`/cuadre` es la rebanada solo-fiscal de esto; `/ronda` cubre todo y reutiliza el mismo
juez fiscal cuando toca.

## Movimientos

### 1. DISCOVERY — encuentra el trabajo tú mismo
- Lee el estado previo: `tasks/ronda/state.md` (qué se revisó, hasta qué sha).
- Calcula qué cambió desde la última pasada:
  ```
  git diff --name-only <last_sha>..HEAD                      # si state.md trae sha
  git status --porcelain                                     # si no, los cambios sin commitear
  ```
- Filtra ruido: ignora `node_modules/`, `*.lock`, `dist/`, `.next/`, datos generados.
- Si **no hay cambios de código nuevos** → anota "sin novedades" y **TERMINA**. No inventes trabajo.

### 2. ROUTING + HANDOFF — el juez correcto por área, aislado
Clasifica cada archivo y agrúpalos por área:

| Si el path cae en… | Juez (subagent_type) |
|---|---|
| `services/aeat/`, `services/billing/`, `services/reports/fiscal.py`, `reports/modelos_aeat.py`, `pdf_reports/_aeat*`/`_fiscal*`, `agents/billing/_invoice_write_tools.py` | **fiscal-reviewer** |
| Resto de `backend/app/**` | **code-reviewer** |
| `frontend/src/**` | **code-reviewer** |

- Lanza **un** subagente por área-con-cambios (Agent tool, `subagent_type` según la tabla).
  Pásale los archivos y su diff.
- **Tope (circuit breaker): máx. 5 revisores por turno.** Prioriza fiscal > seguridad/auth >
  backend > frontend. Lo que no entre, déjalo en `./inbox/` y regístralo. No subas el tope
  hasta que confíes en que los jueces atrapan errores de verdad.

### 3. VERIFICATION — el que dice "no"
- Cada subagente corre las puertas reales de su área y devuelve PASS / REJECT / BLOCKER.
- Tú NO sobreescribes su veredicto. Si dudas de un PASS en algo sensible (auth, pagos, RLS),
  lanza un segundo revisor y quédate con el más estricto.
- Jueces en `sonnet` a propósito: no heredan los puntos ciegos del agente que generó.

### 4. PERSISTENCE — memoria fuera del chat
- Anexa a `tasks/ronda/state.md` una fila por área:
  `| fecha | área | capa | sha/diff | veredicto | fallos | acción |`
- El agente olvida; el repo no. Si no escribes aquí, mañana revisas lo mismo.

### 5. SCHEDULING / puerta humana — lo que NO automatizas
- **NUNCA** auto-arregles ni auto-mergees. Tu salida son veredictos + resumen para Marcos.
- REJECT y `RIESGO-LEGAL` → primero del todo, en claro.
- Lo dudoso → `./inbox/`, no a un PR.
- En `/loop ronda`, cada turno solo mira lo nuevo desde el último estado.

## Topes (asume que algo girará en vano de noche)
- Máx. 5 revisores/turno. Máx. 1 re-revisión por área. Sin reintentos infinitos de tests.
- En bucle local consume tu suscripción Claude (compartida con el escritorio): dale
  intervalo (`/loop 30m ronda`), no lo dejes corriendo toda la noche.

## Las cuatro deudas silenciosas (vigílalas tú, que el bucle no las ve)
- **Deuda de verificación**: si una puerta no cubre algo, dilo; no marques PASS por omisión.
- **Erosión de comprensión**: lee tú mismo una muestra de lo que aprobó, no todo en automático.
- **Rendición cognitiva**: el bucle ejecuta, **tú decides**. Mantente capaz de decir "esto está mal".
- **Token blowout**: respeta los topes de arriba.

## Salida final al usuario (cada pasada)
1. **Veredicto global**: ¿algún REJECT/RIESGO-LEGAL? (lo primero, sin rodeos).
2. Tabla de áreas revisadas con capa y dictamen.
3. Qué quedó en `./inbox/` para el siguiente turno.
4. Ruta del estado: `tasks/ronda/state.md`.

> Lo fácil es montar el bucle; lo difícil es que tenga dentro algo capaz de decir "no".
> Si `/ronda` lleva muchas pasadas sin rechazar nada, sospecha del revisor — no lo celebres.
