# Auto-update con electron-updater (DIS.UPD)

> **Versión 1.0 — 2026-05-15**.

AutomatizaCore se actualiza automáticamente con
[`electron-updater`](https://www.electron.build/auto-update) leyendo
releases publicados en GitHub Releases. Soporta dos **canales**
(stable / beta) y **delta updates** (diferencial — el cliente descarga
solo los bloques cambiados, no el .exe entero).

## §1 Lifecycle

```
arranque app:
  ├─► setupAutoUpdater() — aplica el canal persistido
  └─► autoUpdater.checkForUpdates()    [silencioso si no hay update]

update disponible:
  ├─► autoUpdater emite "update-available" → renderer recibe IPC
  ├─► autoUpdater empieza a descargar (autoDownload=true)
  ├─► emite "download-progress" durante la descarga
  └─► emite "update-downloaded" cuando termina

renderer muestra modal "Actualización lista, ¿reiniciar?":
  ├─► usuario acepta → ipcRenderer.invoke("install-update")
  ├─► main: isQuitting=true, stopAll(), autoUpdater.quitAndInstall()
  └─► NSIS reemplaza binarios, relanza app actualizada

usuario cambia canal en Settings:
  ├─► ipcRenderer.invoke("set-update-channel", "beta")
  ├─► main: store.set, autoUpdater.channel="beta", allowPrerelease=true
  └─► dispara un re-check inmediato con el nuevo canal
```

## §2 Canales

| Canal | autoUpdater.channel | allowPrerelease | Cuándo usar |
|---|---|---|---|
| `stable` (default) | `latest` | `false` | Producción, uso diario |
| `beta` | `beta` | `true` | Early adopters, QA en cliente |

Persistencia en `electron-store` (archivo `update-prefs.json` dentro de
`userData/`). El módulo está en
[`desktop/lib/update-channel.js`](../desktop/lib/update-channel.js).

### Cómo publicar en cada canal

- **Stable**: tag GitHub `v1.0.0` (sin sufijo). `electron-builder
  --publish always` genera `latest.yml`.
- **Beta**: tag `v1.0.0-beta.1`. Se publica como pre-release en GitHub.
  electron-updater genera `beta.yml` automáticamente.

Workflow CI (sketch):

```yaml
- name: Build and publish
  env:
    GH_TOKEN: ${{ secrets.GH_TOKEN }}
  run: |
    cd desktop
    npm ci
    npm run dist -- --publish always
```

## §3 Delta updates

electron-builder con target `nsis` habilita por defecto
`differentialPackage`. Los archivos `*.exe.blockmap` se publican junto
al instalador y permiten que el cliente descargue solo los bloques
distintos respecto a la versión instalada.

Tamaño típico: 200-300 MB instalador completo → 20-50 MB delta para un
patch menor.

Sin configuración extra. Verificable inspeccionando los assets del
release: deben aparecer `latest.yml`, `<setup>.exe`, `<setup>.exe.blockmap`.

## §4 Publish (estado 2026-06-12)

[`desktop/package.json`](../desktop/package.json) → `build.publish` apunta al
repo real:

```json
"publish": {
  "provider": "github",
  "owner": "Llicklair",
  "repo": "Automatiza-Core"
}
```

⚠️ **El repo es PRIVADO.** electron-updater **no puede** actualizar a clientes
desde un repo privado sin un token embebido en el binario (inseguro: cualquiera
con el .exe lo extrae). Opciones antes de distribuir:

1. **(Recomendado)** Repo de releases **público** dedicado (p. ej.
   `Llicklair/automatizacore-releases`) — solo binarios, sin código. Apuntar
   `publish.repo` ahí. El código sigue privado.
2. Hacer público el repo actual (expone el código — desaconsejado).
3. Embeber un PAT de solo-lectura (inseguro; descartado).

Para el workflow de release: `GH_TOKEN` con scope `repo` (solo en CI, nunca en
el binario) + `npm run dist -- --publish always`.

## §5 Code signing (cross-ref DIS.SIG)

Sin **certificado de firma de código EV** (DEC.04 ~480€/año), Windows
SmartScreen mostrará advertencias al usuario cuando autoUpdater
intente reemplazar binarios. Los usuarios pueden saltarse la advertencia,
pero el proceso pierde la promesa de "transparente".

Hasta que el cert esté firmado:
- Indicar a los beta-testers que ignoren la primera advertencia de
  SmartScreen tras un update.
- Documentar en el changelog que la firma vendrá en v1.0.x.

`forceCodeSigning: false` en el config actual permite buildear sin
cert local — útil para CI sin secretos.

### Cómo firmar cuando haya certificado

electron-builder firma automáticamente si encuentra estas variables de entorno
(no requieren cambios en `package.json`):

```bash
# .pfx en base64 o ruta al fichero
set CSC_LINK=base64-del-certificado-o-ruta.pfx
set CSC_KEY_PASSWORD=contraseña-del-pfx
cd desktop && npm run dist -- --publish always
```

En CI: guardar `CSC_LINK`/`CSC_KEY_PASSWORD` como secrets. Para forzar que un
build de release NO salga sin firmar, poner `forceCodeSigning: true` solo en el
pipeline de release (dejarlo `false` para builds de dev).

## §6 IPC bridge expuesto al renderer

[`desktop/preload.js`](../desktop/preload.js):

| Método | Direction | Uso |
|---|---|---|
| `checkForUpdates()` | renderer→main | Fuerza un check (botón "Buscar actualizaciones") |
| `installUpdate()` | renderer→main | Modal "Reiniciar para instalar?" |
| `getUpdateChannel()` | renderer→main | Lee canal persistido |
| `setUpdateChannel(channel)` | renderer→main | Cambia canal + persiste + re-check |
| `onUpdateAvailable(cb)` | main→renderer | Listener evento |
| `onUpdateDownloadProgress(cb)` | main→renderer | Progress events |
| `onUpdateDownloaded(cb)` | main→renderer | Listo para reiniciar |
| `onUpdateError(cb)` | main→renderer | Error de check/download |
| `removeUpdateListeners()` | renderer | Cleanup en unmount |

## §7 Componentes UI

- [`components/settings/UpdateChannelSelector.tsx`](../frontend/src/components/settings/UpdateChannelSelector.tsx)
  — radio group stable/beta. Se oculta automáticamente fuera de
  Electron (browser dev).
- Integración con `/configuracion/actualizaciones` (página existente)
  queda como follow-up mecánico — basta importar y renderizar.

## §8 Tests

[`frontend/src/__tests__/update-channel.test.ts`](../frontend/src/__tests__/update-channel.test.ts) (13 tests):
- Normalización de inputs (case, whitespace, inválidos).
- Defaults y constantes exportadas.
- Persistencia bidireccional via store mock.
- `apply()` setea `channel` + `allowPrerelease` en autoUpdater.
- Stable resetea allowPrerelease=false.
- Inputs raros → stable.
- Logger callback invocado.
- `supported()` devuelve copia inmutable.

## §9 Troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| Cliente no se actualiza | `app.isPackaged===false` (dev) | autoUpdater no aplica en dev. Test con build empaquetado. |
| Update se descarga pero no instala | Backend tiene handle abierto sobre python.exe | Resolved en DIS.SVC: `install-update` llama `stopAll()` antes. |
| Beta no aparece tras switch | El último beta release no incluye `beta.yml` | Verificar que electron-builder publicó con `--publish always` Y que el tag es pre-release. |
| Windows SmartScreen alerta | Falta cert EV firmado (DIS.SIG) | Cliente acepta el warning; planear DIS.SIG. |

## §10 Saneado de secretos en el instalador (2026-06-12)

Antes, `extraResources` horneaba el `.env` real → **filtraba secretos del
desarrollador a cada cliente**. Ahora `predist` ejecuta
[`desktop/sanitize-env.js`](../desktop/sanitize-env.js), que genera
`desktop/.env.dist` (gitignorado) eliminando claves que NO deben distribuirse:

- `SECRET_KEY`, `TENANT_ENCRYPTION_KEY` → se generan por-instalación vía
  Electron safeStorage (`service-manager.js::getOrCreateSecrets`).
- `POSTGRES_*`, `DATABASE_URL` → la BD es per-install (`getDatabaseURL`).
- `LANGFUSE_*`, `LLM_TRACE_*` → observabilidad del desarrollador.

> Nota: `AP_DEVMODE` se eliminó por completo del código (ya no existe bypass de
> licencia por entorno), así que no hay nada que filtrar por ese lado.

`extraResources` ahora copia `.env.dist` (no `../.env`).

### ⚠️ Decisión pendiente — credenciales OAuth de la app

`.env.dist` **todavía incluye** los secretos OAuth de la app (`GOOGLE_CLIENT_SECRET`,
y los de Twitter/Facebook/Instagram) porque el login depende de ellos hoy.
Embeber secretos OAuth en un binario distribuido es un riesgo conocido
(cualquiera con el .exe los extrae → puede suplantar la app). Opciones:

1. **Proxy backend de OAuth**: el secreto vive en un servidor tuyo; el desktop
   solo recibe el resultado. Es lo correcto, pero requiere infra.
2. **OAuth por-tenant (BYOK social)**: cada cliente registra su propia app OAuth.
3. Aceptar el riesgo por ahora (rotar los secretos si se filtran).

Hasta decidir, los secretos OAuth siguen viajando. **Recomendado**: al menos
rotar `LANGFUSE_*` si alguna build previa con el `.env` completo llegó a
distribuirse (esos sí eran fuga pura).
