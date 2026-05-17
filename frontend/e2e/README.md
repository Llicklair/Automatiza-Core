# E2E Tests — Playwright (QA.E2E)

Suite Playwright para flujos end-to-end del frontend. Diseñada para
ejecutar localmente y en CI.

## Estructura

| Archivo | Propósito | Estado |
|---|---|---|
| `playwright.config.ts` (`frontend/`) | Config global: webServer, baseURL, projects, retries | Listo |
| `smoke.spec.ts` | Smoke tests sin backend (home, login render, navegación auth) | 3 tests activos |
| `happy-path.spec.ts` | Flow real signup → factura → 303 | `test.skip()` (placeholder hasta seed + storage state) |
| `.results/` | Output (gitignored) | — |

## Cómo correrlo

### Primera vez (descargar Chromium ~170MB)

```pwsh
cd frontend
npm install
npx playwright install chromium
```

### Ejecutar tests

```pwsh
cd frontend
npm run test:e2e            # headless, todos los specs
npm run test:e2e:ui         # UI interactiva (recomendado en dev)
npm run test:e2e:debug      # debug con inspector
npx playwright test smoke   # solo smoke
```

El `webServer` del config arranca `npm run dev` automáticamente y espera
al puerto 3000. Si ya tienes el dev server corriendo, lo reusa (en local;
en CI siempre arranca uno nuevo).

### Pre-requisitos para `happy-path.spec.ts` (cuando se active)

1. Postgres local corriendo en `:5433` (gestionado por `postgres-manager.js`).
2. Backend FastAPI en `:8000` (`cd backend && py -3.11 -m uvicorn app.main:app --reload --port 8000`).
3. Variable `E2E_BASE_URL` opcional para apuntar a otro entorno (default `http://localhost:3000`).

## CI

Para añadir a `.github/workflows/ci.yml` (próximo paso, no incluido aún):

```yaml
- name: Install Playwright browsers
  run: cd frontend && npx playwright install --with-deps chromium
- name: E2E tests
  run: cd frontend && npm run test:e2e
```

Reporter `github` ya configurado — produce anotaciones inline en PRs.

## Próximos pasos (TODO)

1. **`auth.setup.ts`** — proyecto Playwright que hace login una vez y guarda
   storage state. Resto de tests lo cargan via `storageState`.
2. **Fixture de seed** — usuario + tenant deterministas creados por API o
   `pytest --fixtures`. Evita pollution entre runs.
3. **Activar `happy-path.spec.ts`** — quitar `.skip` cuando los puntos 1-2
   estén listos.
4. **Test PRES.303** contra mock AEAT — una vez `PRES.303` se integre.
5. **Snapshot visual** opcional — con `page.screenshot()` + comparación
   pixel-by-pixel para detectar regresiones de UI.
