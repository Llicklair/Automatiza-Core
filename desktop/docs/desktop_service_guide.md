# Backend como servicio + tray persistente (DIS.SVC)

> **Versión 1.0 — 2026-05-15**.

AutomatizaPyme corre como aplicación Electron de escritorio, pero su
backend (uvicorn) DEBE estar disponible mientras el equipo del usuario
esté encendido para que cron jobs, scheduled workflows y notificaciones
funcionen. Esta guía describe cómo se logra **sin** instalarlo como
servicio nativo de Windows (Service Control Manager).

## §1 Decisión de diseño: Electron host, no SCM

Considerada y descartada la instalación como servicio Windows con
`nssm` o `node-windows` por:

- Complica el instalador (requiere permisos admin elevados).
- Hace difícil para el usuario "quitarlo del medio" cuando quiera.
- Auto-update con servicios SCM requiere parar/reiniciar el servicio
  fuera de Electron, complicando el flujo.

En su lugar, **Electron actúa como service host**:

- La ventana se oculta al pulsar X (close→hide), Electron sigue vivo.
- Tray icon permanente con menú contextual (`tray-manager.js`).
- Backend supervisor reinicia el backend si crashea
  (`lib/backend-supervisor.js`).
- Auto-update lanza `quitAndInstall()` que para el supervisor de forma
  ordenada antes de reemplazar binarios.

El usuario percibe: "AutomatizaPyme está siempre disponible mientras
mi PC está encendido, no me molesta cuando no lo uso".

## §2 Lifecycle

```
arranque PC
  └─► Electron arranca (autostart via electron-builder option)
      ├─► service-manager.startAll(): Postgres → backend → frontend
      ├─► backendSupervisor.start(uvicorn)   ← auto-restart si crashea
      ├─► createTray(...)                    ← icono persistente
      └─► createWindow()                     ← BrowserWindow visible

usuario pulsa X:
  └─► window.close → preventDefault → window.hide
      (Tray sigue activo, backend sigue corriendo)

usuario click derecho tray → "Abrir Dashboard":
  └─► onShow callback → mainWindow.show()

usuario click derecho tray → "Parar servicios":
  └─► stopAll() → supervisor.stop({clean: true})
      Backend para. Tray sigue activo para arrancar de nuevo.

autoUpdater notifica "update-downloaded":
  └─► UI muestra modal "Reiniciar para instalar?"
      Usuario acepta → ipcRenderer "install-update"
      → isQuitting=true, stopAll(), autoUpdater.quitAndInstall()
      Instalador NSIS reemplaza binarios, relanza app.

usuario click derecho tray → "Salir":
  └─► isQuitting=true, app.quit() → 'before-quit' → stopAll()
```

## §3 Supervisor de backend

[`desktop/lib/backend-supervisor.js`](../desktop/lib/backend-supervisor.js)
es un wrapper Node sin dependencias de Electron que envuelve un
`ChildProcess` y lo reinicia con backoff exponencial si crashea.

### Backoff defaults

| Intento | Delay |
|---|---|
| 1 | 1 s |
| 2 | 2 s |
| 3 | 4 s |
| 4 | 8 s |
| 5 | 16 s |
| 6+ | 32 s |

Tras **6 intentos** consecutivos sin éxito → `onGiveUp` callback. La
UI muestra modal de error y pide al usuario revisar logs (los logs
están en `%APPDATA%/AutomatizaPyme/logs/`, CONT.LOG).

### Stop limpio vs crash

- `supervisor.stop({ clean: true })` → mata el child + marca
  `cleanExitMode=true` → la emisión subsiguiente de `exit` NO dispara
  restart.
- Si el child emite `exit(code!=0)` SIN stop previo → supervisor
  considera crash → restart con backoff.

### Integración con install-update

El handler IPC `install-update` (en `main.js`) hace:

1. `isQuitting = true` — evita que `window.close` intercepte ocultando.
2. `stopAll()` — supervisor.stop + para frontend + para Postgres.
3. `autoUpdater.quitAndInstall()` — Electron sale, NSIS instala.

Sin paso 2, NSIS puede fallar al reemplazar `python.exe` o
`postgres.exe` si están abiertos.

## §4 Tray contextual

[`desktop/tray-manager.js`](../desktop/tray-manager.js) define el menú:

- **Abrir Dashboard** — muestra ventana.
- **IP Local** + **Copiar URL LAN/API** — comparte la URL para que
  otros equipos del despacho accedan (modo "servidor compartido"
  rudimentario; el switch MULTI.1 mejora esto en v1.2).
- **Usuarios conectados...** — instrucciones de firewall.
- **Parar servicios** — para todo, deja Electron + tray activos.
- **Salir** — para todo y cierra Electron.

Double-click sobre el icono = "Abrir Dashboard".

## §5 Diagnóstico

Si el backend supervisor está en `give-up`, el `inspect()` reporta
`shouldRun: false`. El diagnostic-bundle (CONT.LOG) incluye este
estado en `info.json` para que el soporte pueda diagnosticar a partir
del log.

Para forzar un reset desde tray (follow-up): añadir "Reintentar
backend" que llame `supervisor.resetAttempts()` + `supervisor.start()`.
No está en MVP — el atajo es "Salir + abrir de nuevo".

## §6 Tests

[`frontend/src/__tests__/backend-supervisor.test.ts`](../frontend/src/__tests__/backend-supervisor.test.ts) (10 tests):

- Start invoca spawn (idempotente).
- Inspect refleja estado tras start.
- Restart tras crash con backoff exponencial.
- Backoff sigue la secuencia configurada.
- Give-up tras maxAttempts.
- Stop limpio cancela timer y mata child.
- ResetAttempts limpia contador.
- Validación de `spawn` parámetro.

## §7 macOS / Linux

El supervisor es portable (Node puro). El tray-manager usa
`electron.Tray` que soporta macOS y Linux. Lo que cambia:

- macOS: `BrowserWindow.hide()` mantiene la app en el Dock (no en
  tray); el patrón sería usar el menú contextual del Dock.
- Linux: depende del entorno gráfico (GNOME esconde trays por defecto,
  KDE los muestra).

DIS.MAC (v1.0.x posterior) y soporte Linux quedan post-MVP.
