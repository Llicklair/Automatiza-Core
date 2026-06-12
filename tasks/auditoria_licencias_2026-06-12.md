# Auditoría de integridad — Validación de licencias (2026-06-12)

> Contexto: prerrequisito para habilitar auto-update. Revisión de
> `core/license.py`, `middleware/license_check.py`, `routes/license.py`,
> `main.py` (lifespan).

## Arquitectura actual

App desktop: backend Python embebido en Electron. Al arrancar (`main.py`
lifespan) se llama a `validate_license()` y se fija `app.state.license_valid`.
Un middleware bloquea con **402** toda ruta no incluida en `_ALLOWED_PREFIXES`
si `license_valid` es falso.

Validación (`core/license.py`):
1. `AP_DEVMODE=1` → bypass (valid, plan=dev).
2. Lee caché `%APPDATA%/AutomatizaCore/license.json`.
3. Verifica HMAC(machine_id) + machine_id de la caché.
4. Caché < 24 h → válida sin llamar al servidor.
5. Si no → POST `/licenses/validate` con `nonce`; verifica **firma Ed25519**
   del servidor sobre `{nonce}:{plan}` (clave pública hardcodeada).
6. Gracia offline 7 días desde la última validación correcta.

## Fortalezas (bien hechas)

- **Firma Ed25519 del servidor** con clave pública hardcodeada + **nonce** →
  impide servidor falso y replay de respuestas. Sólido.
- HMAC de caché + comprobación de `machine_id` → frena edición naïf y copiar
  el `license.json` a otra máquina.
- Gracia offline acotada a 7 días.

## Debilidades (por severidad)

### 🔴 CRÍTICA

- **L1 — El backend se distribuye como fuente Python editable.** En
  `desktop/dist/win-unpacked/resources/project/backend/app/core/license.py` el
  código va en claro. Un usuario puede editar `validate_license()` →
  `return LicenseResult(valid=True)` (o el middleware) y saltarse TODO. Ninguna
  criptografía corrige esto: si el código de enforcement es editable en el
  cliente, la validación client-side es, por diseño, eludible.
  - **Mitigación real**: compilar/ofuscar el backend (PyInstaller `--onefile`,
    Nuitka, o al menos distribuir `.pyc` + arrancar desde el compilado), o
    asumir un modelo "honor system + barrera anti-casual".

### 🟠 ALTA

- **L2 — Middleware fail-open.** `license_check.py` usa
  `getattr(request.app.state, "license_valid", True)`: si el flag no llega a
  fijarse (excepción en el lifespan ANTES de `main.py:56` — p.ej.
  `recover_stale_executions()` en la línea 51 lanza), el atributo no existe →
  **todo pasa**. Debe ser `False` (fail-closed), como ya hace
  `routes/license.py:18`. **Fix de 1 línea, alto valor.**

- **L3 — La "firma" de caché es forjable localmente.** `_sign` usa
  `hmac(key=machine_id, …)`, pero `machine_id` (MachineGuid/MAC) es **legible
  en la propia máquina** → un usuario local puede recomputar el HMAC y forjar
  `license.json` con `last_validated` futuro y cualquier `plan`. Como la caché
  < 24 h no llama al servidor, **el servidor (con su Ed25519 infalsificable)
  nunca se consulta** → bypass permanente offline. La firma del servidor solo
  protege si se fuerza la consulta online.

- **L4 — Bypass DEVMODE en el binario distribuido.** `AP_DEVMODE=1` desactiva
  la validación. El usuario controla su entorno → puede activarlo. Debe quedar
  **fuera de los builds de release** (rama compilada solo en dev, o atada a un
  flag de build).

### 🟡 MEDIA

- **L5 — Validación solo en el arranque.** No hay revalidación periódica;
  sesiones largas no recomprueban. Para desktop es menor (reinicia), pero
  combinado con L3 deja el enforcement laxo. Recomendable revalidar cada 24 h
  desde el scheduler y refrescar `app.state.license_valid`.

- **L6 — `except (InvalidSignature, Exception)`** en `_verify_server_sig`: el
  `Exception` hace redundante a `InvalidSignature` y traga cualquier error
  (aquí fail-closed → devuelve False, aceptable) pero oculta bugs. Menor.

## Relación con auto-update

Antes de distribuir auto-updates:
1. **Firmar instalador + updates** (electron-updater + code signing / firma del
   `latest.yml`) para que nadie inyecte un build malicioso por el canal de update.
2. **Decidir el modelo de licencia** (L1): si el backend va como fuente, la
   licencia es barrera anti-casual, no enforcement fuerte. Para enforcement
   serio → compilar el backend.
3. El canal de update **no debe** poder degradar la validación (no publicar
   builds con `AP_DEVMODE` ni con la rama de bypass activa).

## Recomendaciones priorizadas

| # | Acción | Coste | Efecto | Estado |
|---|---|---|---|---|
| 1 | **L2**: middleware fail-closed (`default=False`) | 1 línea | Cierra fail-open inmediato | ✅ HECHO 2026-06-12 (+ default defensivo en `main.py` lifespan + try/except) |
| 2 | **L4**: excluir `AP_DEVMODE` de release | bajo | Cierra bypass por entorno | ✅ HECHO 2026-06-12 (gateado por `AUTOMATIZA_RELEASE`; el launcher empaquetado lo fija en `python-manager.js`) |
| 3 | **L5**: revalidación periódica (24 h) en scheduler | bajo | Reduce ventana de caché forjada | pendiente |
| 4 | **L1**: compilar/ofuscar backend | alto (estratégico) | Única defensa real client-side | pendiente (decisión de producto) |
| 5 | **L3**: reducir TTL de caché / forzar online más a menudo | bajo | Mitigación parcial (el fix real es L1) | pendiente |

**Veredicto:** la criptografía servidor↔cliente (Ed25519 + nonce) está bien,
pero el enforcement **client-side es eludible** mientras el backend se distribuya
como fuente y exista el fail-open (L2) y el DEVMODE (L4). Los puntos 1-3 son
rápidos y seguros de aplicar ya; el 4 es una decisión de producto.
