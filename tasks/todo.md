# Tareas activas — AutomatizaCore

Última actualización: 2026-06-19 (reconciliado contra el código)

> Solo trabajo **PENDIENTE**. Lo completado se ha retirado (queda en el historial
> git). Vista global priorizada y verificada contra el código:
> [roadmap_global_2026-06-11.md](./roadmap_global_2026-06-11.md).
>
> **Reconciliación 2026-06-19** (auditoría de 4 clusters contra el código): se
> confirmó como **obsoleto** el bug "IG impressions → 400" (el marketing migró a
> Zernio, ya no llama a la Graph API de Meta) y se detectó que la **cobertura E2E**
> no estaba reflejada aquí (ver sección al final). El resto de "Deuda técnica
> diferida" (A1-A7) se verificó vivo en código.

---

## Fiscal

- [x] **F2.6 Conciliación bancaria explicable** ✅ (2026-06-12) — backend ya
  tenía `_explain_match` (score + reasons: importe/fecha/cliente/Nº factura),
  endpoints suggestions/reconcile/reject (con aprendizaje vía mig `0034`) y
  auto-match. **Cerrado el gap de UI** en `ConciliacionTab`: muestra los motivos
  ("Coincide por: …") por sugerencia + botón "Rechazar" que llama al endpoint de
  aprendizaje (el par no vuelve a sugerirse).
- [ ] **F2.8 Presentación telemática AEAT (200/100)** — Modelo 200 (datos +
  endpoint + PDF) ✅ y **Modelo 100** (IRPF Renta preview: datos + escala IRPF
  progresiva + `GET /100` + PDF `GET /100/pdf`) ✅ (2026-06-12). **Falta**: la
  presentación telemática real (requiere certificado AEAT — bloqueada).
- [x] **F2.9 Modelo 130 "calcado" oficial AEAT (borrador)** ✅ (2026-06-16) —
  el PDF del 130 usaba `_kv_table` genérico (sin casillas). Ahora replica el
  formulario oficial: casillas numeradas + estilo AEAT, manteniendo BORRADOR.
  **Hecho:** nuevo `aeat/casillas_130.py` (`build_casillas_130`) + nuevo
  `pdf_reports/_aeat_layout.py` (helpers compartidos) + reescrito
  `generate_modelo_130_pdf` + `tests/test_casillas_130.py` (8 tests). **303 NO
  tocado.** 50 tests verdes (130 + smoke modelos + 303 + datos AEAT).
  Mapeo verificado (Verifácturamos + Infoautónomos):
  - **Apartado I:** 01 Ingresos · 02 Gastos · 03 Rdto. neto [01−02] · 04 20%·03(≥0)
    · 05 Pagos fracc. anteriores (0, editable) · 06 Retenciones (0, editable) · 07 [04−05−06].
  - **Apartado III:** 12 [07+11] · 13 Deducción rentas bajas (0, editable) · 14 [12−13]
    · 15 Result. neg. trim. ant. (0, editable) · 16 Préstamo vivienda (0, editable)
    · 17 [14−15−16] · 18 A deducir compl. (0, editable) · 19 Resultado [17−18].
  - Apartado II (agrícola 08–11) se omite por defecto. Editables a 0 con nota (NO inventar).
  - **Cambios:** nuevo `aeat/casillas_130.py` (`build_casillas_130`) + reescribir
    `generate_modelo_130_pdf` (layout AEAT) + (recomendado) extraer helpers a
    `_aeat_layout.py` compartido 303/130 + `test_casillas_130.py`.
  - **Línea roja:** mantener disclaimer; NO falsificar nº justificante / CSV / PDF417.
- [x] **F2.9b Calcar el resto de modelos AEAT** ✅ (2026-06-18) — patrón sobre
  `_aeat_layout.py` + `aeat/casillas_NNN.py` (con `aeat/_casilla.py` compartido).
  Números de casilla verificados contra ≥2 fuentes (línea roja: no inventar). 57
  tests verdes (casillas + smoke PDFs + batería 303).
  - [x] **111** ✅ casillas 01-09 (trabajo/act. económicas) + 28/29/30 liquidación.
  - [x] **115** ✅ casillas 01-05 (resultado = 03 − 04).
  - [x] **390** ✅ casillas clave IVA anual (01-06 devengado, 33/34/47, 48/49/64, 65/84/86).
  - [x] **190 / 347 / 349** ✅ (informativas) — `casillas_190.py` (01 nº perceptores,
    02 Σ percepciones, 03 Σ retenciones; BOE EHA/3127/2009) y `casillas_347.py`
    (01/02 operaciones >3.005,06€, 03/04 arrendamientos local negocio). El **349**
    no numera el resumen → rótulos por etiqueta (nº operadores + importe), no casillas
    inventadas. Los tres en estilo calcado: identificación + resumen + listado de registros.
  - [x] **200 / 100** ✅ (preview liquidación) — `casillas_200.py` (00500/00552/00558%/
    00562/00592/00601/00621; Manual Sociedades 2024) y `casillas_100.py` (0224/0500/
    0519/0595/0596/0604/0670; Renta 2024/2025). Conceptos sin casilla-resumen única
    (ajustes 00355–00414, retenciones 01785–01799) NO se inventan: se explican en nota.
  - [x] Migrar el **303** al módulo compartido ✅ — eliminados los helpers duplicados
    de `_fiscal_modelo303.py`; ahora usa `_aeat_layout` con `pct_codes=_PCT_CASILLAS`
    en cada `_casillas_table`. Batería de tests del 303 verde sin cambios.
- [ ] **Modelos no cubiertos (futuro, P2)** — **131** (IRPF módulos / estimación
  objetiva) y **TicketBAI** (País Vasco/Navarra): cero código hoy. Diferidos a
  demanda real de cliente.

## Gestoría / Firma

- [~] **F3.11 Firma AutoFirma** ✅ implementado (2026-06-12) — backend
  (`autofirma.py` + init/callback) + **endpoint de estado** `GET /signing/
  autofirma/status/{token}` (3 tests) + **botón "Firmar"** en `DocumentCard`
  (aprobados): obtiene el PDF → base64 → `init` → lanza `afirma://` → polling de
  estado → toast. **Pendiente de verificación e2e**: requiere AutoFirma instalado
  para probar el handshake del certificado FNMT (no verificable en CI).

## AIEmployee — Contrato del custom (RETIRADO 2026-06-18)

Históricamente un custom debía aportar ≥2 de 4 capacidades o se degradaba a
"Perfil". **Ese contrato se retiró** (ver abajo): un custom "fino" (solo persona/
`system_prompt`) es válido. Las 4 capacidades quedan como add-ons opcionales:

| Capacidad | Campo BD |
|---|---|
| Scope filter persistente | `scope` (JSONB) |
| Memoria persistente | `memory_enabled` + tabla `employee_memory` |
| Knowledge base privada | `knowledge_enabled` + filtro RAG por employee |
| Workflows predefinidos | `workflows` (JSONB) |

Migración `0029_aiemployee_contract` + modelo + `employee_memory` ✅.

- [x] **Contrato del custom retirado** ✅ (2026-06-18) — un workflow multi-agente
  (10 agentes, verificación adversarial) demostró que las 4 capacidades son casi
  inertes en runtime (el comportamiento sale solo de `system_prompt` + skills;
  scope/workflows no se leen, knowledge sin cablear, memory solo con skill) y que el
  contrato `≥2 capacidades` penalizaba el uso REAL (tono/ángulo al redactar informes/
  estrategias). **Decisión del usuario: quitar la traba**, no construir el split UI.
  Hecho: eliminado el gate 422 en `create_employee` + `POST /ai-employees` (y
  `EmployeeContractError`); frontend deja de hardcodear capacidades; docstrings
  actualizados. `employee_contract.py` se conserva como utilidad de **auditoría**.
  **Seguridad de routing intacta**: el guard que frena el bug Yolanda
  (`classifier._meets_employee_contract`) es independiente del 422 y NO se tocó; los
  customs rotos (prompt vacío) los frena el health-check del classifier, no el alta.
  Por eso "aplicar el contrato a customs existentes" queda **obsoleto** (un custom
  fino ya es válido; no hay nada que degradar). 131 tests verdes + tsc limpio.
- [ ] **(Opcional, no urgente) Gancho de informes** — el `system_prompt` del custom
  solo llega vía dispatch (instruct / `addressed_employee_id`); `/informes` genera por
  periodo SIN selector de empleado y de forma determinista (no pasa por la IA), así que
  el "ángulo" del custom NO se aplica hoy a los informes PDF automáticos. Para "informes
  con enfoque del empleado" haría falta un selector de empleado en `/informes` (cambio
  mayor) — pendiente de decisión del usuario.

## Arquitectura

- [x] **F1.1 Audit de dominios** ✅ (2026-06-12) — `audit_domain_completeness.py`
  ejecutado: **sync limpio** (EXIT=0) entre `VALID_DOMAINS`/`DISPATCHER_MAP`/
  `_KEYWORD_MAP`/`_STRONG_KEYWORDS`. Sin asimetrías (coordinator/custom/skill son
  dominios especiales esperados).
- [x] **#3 `AgentResult` end-to-end** ✅ RESUELTO POR DISEÑO (verificado 2026-06-12)
  — el objetivo (contrato `AgentResult` uniforme en todo el dispatch) **ya se
  cumple**: los 17 dispatchers están tipados `-> AgentResult` y los graph-based
  pasan por el adaptador único `_run_graph_agent(graph, …) -> AgentResult`
  (`dispatchers/misc.py`). La tarea original (añadir `run_agent()` a cada
  `agent.py`) describía otro enfoque, superado por ese adaptador; el refactor
  literal sería reescribir 14 agentes para cero ganancia funcional. Los nodos de
  agente devuelven dicts de estado (convención LangGraph) — no es inconsistencia.

## Deuda técnica diferida (no aprobada aún)

- [ ] Migración incremental del resto de agentes a `tool_session()` (RLS en tools).
- [ ] Extraer lógica de negocio de routes con muchos commits.
- [ ] `run_recurring` numera `REC-<timestamp>` fuera de la serie correlativa.
- [ ] Marketing: doble carga de `accounts()` entre `TabCuentas`/`TabCrear`.
- [x] **i18n / app en inglés — barrido de UI + activación** ✅ (2026-06-19) — toda
  la UI del dashboard migrada a next-intl con parity es/en al 100% (4806=4806
  claves, 0 residual salvo 2 etiquetas de color en mi-equipo dejadas a propósito).
  **Inglés ACTIVADO** en runtime (`i18n/request.ts` `SUPPORTED_LOCALES=["es","en"]`
  + selector en `/configuracion/idioma`). Commits `f207154`..`09180f2`.
- [ ] **i18n — IA en inglés** (pendiente) — la **IA sigue fijada en español**
  (prompts "Responde siempre en español" en `agents/email`, `dispatchers/chat`,
  `prompts/*.txt`). Para respuestas de la IA en el idioma de la UI: pasar `locale`
  a los agentes y parametrizar esos prompts. Cambio de **backend**.
- [ ] **i18n — repaso humano del `en`** (recomendado antes de exponer a clientes) —
  la traducción inglesa la generaron agentes (verificada como fiel al es, pero sin
  revisión humana); conviene una pasada sobre todo en términos fiscales (AEAT,
  modelos, casillas). Reactivar **ca/eu/gl** sigue pendiente (son stubs incompletos).

## Auto-update / Release (#5 — ops + decisión usuario)

Wiring de código OK + `desktop/package.json` `publish` corregido. Para distribuir:
- [ ] Rebuild del instalador (`frontend: npm run build` → `desktop: npm run dist`)
  — el `app-update.yml` se hornea en build-time (el `.exe` actual tiene owner placeholder).
- [ ] Repo de releases **público** (electron-updater no actualiza desde repo
  privado sin token embebido inseguro).
- [ ] Sanear secretos del `.env` horneado en `build.extraResources`
  (placeholders + Electron safeStorage).

## Acciones de usuario (no código)

- [x] **F1.3 OAuth Google → Production mode** ✅ (2026-06-18) — app publicada en
  Cloud Console; los refresh tokens ya no caducan a 7 días.
- [ ] OAuth verification + CASA assessment Tier 1 para `gmail.send` — **NO hace
  falta aún**: en Producción los scopes restringidos admiten hasta ~100 usuarios
  sin verificación. Solo necesario al acercarse a ese tope (100 clientes).
- [~] Roadmap M1-M2 (memorias) — contrastado con código (2026-06-18):
  - [x] **Numeración correlativa** ✅ `services/billing/numbering.py` (`next_invoice_number`
    → `A2026-0001`); HR docs `DOC-2026-0001`. (Único fuera de serie: `run_recurring`
    `REC-<timestamp>`, ya listado en Deuda técnica diferida.)
  - [x] **JWT safeStorage** ✅ `frontend/src/lib/secureStore.ts` → Electron
    `safeStorage.encryptString` (DPAPI/Keychain); fallback localStorage solo dev/web.
  - [ ] **AEAT FNMT** — solo AutoFirma (firma docs) hecho; la **presentación telemática
    real a AEAT con cert FNMT** sigue pendiente (REGAP mockeado en `onboarding/regap.py`,
    Verifactu simulado en `billing/facturae.py`). **Bloqueada por certificado** (= F2.8).
  - [~] **Envío VeriFactu code-complete** ✅ (2026-06-19) — `services/billing/verifactu_submit.py`:
    `voluntary`+`confirmed` → carga cert del tenant (`certificate_storage`, modelo BYO) → firma
    (`xades_signer`) → POST mTLS (`HttpxVerifactuTransport`) → `parse_acuse` del acuse oficial.
    Gated y seguro: sin `confirmed` no hay POST; sin cert o firma stub **aborta sin fingir** (nunca
    CSV ficticio). 14 tests (sin cert/red/BD) + spec en `tasks/verifactu_envio_spec.md`. Cero
    cambios en el flujo vivo (nada lo llama aún). **Falta:** (a) verificar contra **preproducción
    con un cert real** (endpoint/sobre SOAP/perfil XAdES POR CONFIRMAR), (b) decidir régimen con
    gestor, (c) conectar el hook en `commands.py:131`. La elección de régimen ya está en la UI
    (`ModoVerifactuPanel`); el XML ya valida contra XSD oficial.

## Marketing

- [x] **"Publicar ahora" publicaba en falso** ✅ (2026-06-19) — `TabCrear.submit()`
  solo llamaba a `posts.create()` (deja el post en `draft`) y mostraba "¡Publicado!".
  Ahora, si `publishNow`, llama a `posts.publish(post.id)` y solo da éxito si vuelve
  `status: published` (el backend ya devolvía 502 con `error_message` al fallar).
  +clave i18n `marketing.crear.publishFail` (es/en). `tsc` limpio.
- [ ] **Fallback de host Render hardcodeado** — `image_generation.py:44` e
  `image_search.py:41` usan `settings.OAUTH_PROXY_URL or "https://…onrender.com"`;
  si Render cae y no hay key local → 503. Mover el default a config/env (sin host fijo).
- ~~IG `impressions` deprecado → 400~~ **OBSOLETO** (2026-06-19) — el marketing migró a
  Zernio, que abstrae la Graph API de Meta; `get_analytics` solo pasa `platform`+fechas,
  no pide `impressions`. No hay nada que arreglar.

## Tests E2E (cobertura) — riesgo nº1 de la evaluación

Auditado contra `backend/tests` (2026-06-19). Fixtures listas en `conftest.py`
(`auth_client`, `db`, `seed_tenant_and_user`) → añadir un E2E es trivial.

- [x] **Con E2E:** Facturación (`test_e2e_happy_path.py`), VeriFactu (emitir→huella→
  `/verify`, `test_e2e_verifactu.py`, activo), RRHH-nóminas (`test_e2e_happy_path.py`).
- [x] **Contabilidad** ✅ (2026-06-19) — `tests/test_e2e_accounting.py` (2 tests): flujo
  asiento → libro diario → cuentas anuales (Balance+P&G PDF); aserta Σdebe==Σhaber por
  asiento y global, y que un asiento descuadrado se **rechaza (400)** y no se registra.
- [x] **Banca** ✅ (2026-06-19) — `tests/test_e2e_banking.py`: importar N43 → listar
  movimientos + resumen → conciliar abono ↔ factura emitida (movimiento `reconciled` +
  factura `paid`). **Destapó y arregló un bug real**: `_explain_match` (sugerencias de
  conciliación, F2.6) reventaba con `TypeError` al restar `tx.date` (`date`, del N43) e
  `inv.date` (`datetime`, de factura) — fix `_as_date()` en `services/banking/service.py`.
  Los tests previos no lo pillaban (usaban fechas del mismo tipo).
- [x] **Tesorería + SEPA** ✅ (2026-06-19) — `tests/test_e2e_treasury_sepa.py`: proyección
  de cashflow → remesa de adeudos SEPA (pain.008) + transferencias (pain.001) → registro,
  descarga del XML y avance de estado (generated → sent). Aserta namespace SEPA y suma de
  control (no hay validación XSD en el repo).
- [x] **CRM** ✅ (2026-06-19) — `tests/test_e2e_crm.py`: cliente → oportunidad → avance de
  etapa (new→qualified→won) → actividad ligada; aserta embudo y filtrado de actividad por oportunidad.
- [x] **Inventario** ✅ (2026-06-19) — `tests/test_e2e_inventory.py`: producto con mínimo →
  entrada por lote (caducidad/FEFO) → salida bajo mínimo → aparece en reposición. **Destapó
  y arregló un 2º bug real**: alta de lote (`lot_service.create_lot`) y movimiento por escáner
  (`documents/scanner.py`) creaban un `StockMovement` **sin `tenant_id`** (NOT NULL) → reventaban
  con IntegrityError. Fix: pasar `tenant_id` en ambos sitios.
- [x] **Onboarding** ✅ (2026-06-19) — `tests/test_e2e_onboarding.py`: completar wizard (5 pasos)
  → simulación Modelo 303 (resultado = devengado − deducible) → REGAP mock (start→grant→verify).
- [x] **Marketing** happy-path ✅ (2026-06-19) — `tests/test_e2e_marketing_happy.py`: crear post
  → publicar OK → queda `published` con `platform_post_id` (publisher stubeado, sin red Zernio).
  Complementa `test_e2e_marketing_publish.py` (ruta de error).

> **Estado (2026-06-19):** los 6 módulos sin E2E quedan cubiertos, **incluido el happy-path de
> Marketing**. Sumados a los 3 previos (Facturación, VeriFactu, RRHH-nóminas), los **9 módulos
> core tienen E2E**. El proceso destapó 2 bugs reales de producción (conciliación por fecha;
> `StockMovement` sin `tenant_id` en alta de lote y escáner), ya arreglados.

---

## Notas / gotchas (referencia)

- **Cambios backend exigen cerrar y reabrir `AutomatizaCore.exe`** (backend
  Python embebido por Electron — no recoge cambios en caliente).
- **OAuth Google en Producción** (publicada 2026-06-18): refresh tokens ya NO
  caducan a 7 días. Scopes restringidos (`gmail.send`) admiten ~100 usuarios sin
  verificación CASA; verificar solo al acercarse a ese tope.
- **El orchestrator requiere un `Task` real en DB** para `ainvoke` directo (FK
  desde `tenant_documents` y `audit_log`); `smoke_orchestrator.py` tiene
  `_create_task_row()`.
- **Classifier cachea 24 h** (`_CACHE_TTL_CLASSIFY`); invalidar con
  `c:\tmp\clear_classify_cache.py` al iterar keywords/strong.
- **`VALID_DOMAINS` + `DISPATCHER_MAP` + keywords del classifier** deben ir en
  sync o el routing falla en silencio.
- **Rutas absolutas `/foo` no funcionan en Electron** (`file://` → 404); usar
  componentes inline (p.ej. `<LogoSvg />`) para assets críticos.
- **Smoke standalone no usa email/encryption real**: la `TENANT_ENCRYPTION_KEY`
  viene de Electron safeStorage, no del `.env` (decrypt FAIL → email DEMO; es esperado).


---

> **Nota:** lo que sigue es un plan tecnico independiente (port a Linux self-hosted, sin Docker), NO parte del roadmap de producto de arriba. Estado: planificado, sin iniciar.

# Port a Linux self-hosted (sin Docker) — Plan de trabajo

## 1. Objetivo

Permitir que una empresa despliegue Automatiza-pyme en **su propio servidor Linux**, autocontenido y **sin Docker**, replicando la filosofia del `.exe` de Windows: descargar en el primer arranque runtimes portables (PostgreSQL, Python, JRE) bajo un directorio de datos propio y orquestarlos de forma headless. El backend (uvicorn :8080) y el frontend (Next.js :3000) corren como un servicio gestionado por systemd, sin GUI Electron.

## 2. Estrategia: bootstrapper headless

La capa GUI de Electron se **descarta por completo**. El nucleo reutilizable es `service-manager.js` (~80-90% logica pura de orquestacion sobre `http`/`child_process`/`fs`, con acoplamiento Electron solo en `try/catch` con fallback). El plan:

- Crear un nuevo `desktop/bootstrap.js` (entrypoint plano de node) que haga `require('./service-manager')` y llame `startAll(onProgress=console.log)`, con manejo de senales (`SIGTERM`/`SIGINT` -> `stopAll()` -> `process.exit`). **Hoy no existe ni self-start ni signal handling** en service-manager (no hay `require.main === module`): systemd mataria el proceso node sin llamar a `stopAll()`, dejando Postgres/uvicorn/next huerfanos. Esto es la adicion mas importante.

**Reutilizado (con cambios):**
- `desktop/service-manager.js` — orquestador, nucleo del bootstrapper.
- `desktop/postgres-manager.js`, `desktop/python-manager.js`, `desktop/jre-manager.js` — managers de runtime (portar download/extract/paths a Linux).
- `desktop/network-utils.js` — sin Windows-isms (`os.networkInterfaces()`), se usa tal cual.

**Descartado en el path servidor:**
- `desktop/main.js` — boot atado al ciclo GUI de Electron (splash, BrowserWindow, tray, safeStorage, IPC, auto-updater).
- `desktop/launch.js` — lanzador de Electron (`spawn(electron, ['.'])`). Se sustituye por `node bootstrap.js` / unidad systemd.
- `desktop/sync.js` — hot-copy dev hacia un arbol `.exe` instalado en Windows (LOCALAPPDATA\Programs). Irrelevante en servidor.
- `package.json` build block (`build.win.target: nsis`) — solo Windows; no se usa electron-builder en servidor.

## 3. Tabla de runtimes portables Linux

| Runtime | Fuente recomendada | Naming del artefacto (x86_64) | Version | Relocalizable | Caveat principal |
|---------|--------------------|-------------------------------|---------|:-------------:|------------------|
| **PostgreSQL** | zonky.io embedded-postgres-binaries (Maven Central `io.zonky.test.postgres`); alt: theseus-rs/postgresql-binaries (tarball directo) | JAR `embedded-postgres-binaries-linux-amd64-<ver>.jar` -> dentro `postgres-linux-x86_64.txz` (tar+xz). theseus: `postgresql-<ver>-x86_64-unknown-linux-gnu.tar.gz` | 15.x (mirror del EDB 15 de Windows) | **Si** (preservar layout bin/lib/share) | Build glibc; en Alpine/musl usar `-alpine`. NO viene data dir preinicializado: hay que `initdb -D` en primer arranque. No correr como root. |
| **Python** | astral-sh/python-build-standalone (flavor `install_only`) | `cpython-3.11.x+YYYYMMDD-x86_64-unknown-linux-gnu-install_only.tar.gz` (o `install_only_stripped`) | 3.11.14 (igualar patch del embeddable Windows) | **Si** | **NO existe embeddable Linux oficial** (ver 4). gnu necesita glibc>=2.17. musl no carga wheels C-extension. pip/venv ya vienen incluidos (sin `._pth`). |
| **JRE** (opcional) | Eclipse Temurin (Adoptium) v3 redirect | `OpenJDK21U-jre_x64_linux_hotspot_21.0.x_y.tar.gz` (~50 MB) + `.sha256.txt` | 21 LTS (mirror Windows) | **Si** | tar.gz no zip. Extrae a `jdk-21.0.x+y-jre/`, launcher `bin/java` (sin .exe). `chmod +x bin/java`. Solo lo usa OpenDataLoader (PDF); **opcional**, hay fallback a pypdf. En Alpine usar `os=alpine-linux`. |

URLs de descarga sugeridas:
- Postgres (zonky): `https://repo1.maven.org/maven2/io/zonky/test/postgres/embedded-postgres-binaries-linux-amd64/<ver>/embedded-postgres-binaries-linux-amd64-<ver>.jar`
- Python: release dateado de python-build-standalone (metadata en `https://raw.githubusercontent.com/astral-sh/python-build-standalone/latest-release/latest-release.json`)
- JRE: `https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jre/hotspot/normal/eclipse?project=jdk`

## 4. Cambios por fichero

> **DECISION DE DISENO #1 (la mas importante):** el `python-3.11.9-embed-amd64.zip` (Windows embeddable) **NO tiene equivalente Linux**. python.org publica embeddable SOLO para Windows. La estrategia "descomprimir un interprete autocontenido" NO se porta 1:1. En Linux se usa **python-build-standalone (install_only)** que ya trae stdlib + pip + venv: desaparece el hack de `._pth` y el truco de `pip --target`. Esto reordena buena parte de `python-manager.js`.

### Capa transversal (a anadir antes de tocar los managers)
- Helper de sufijo de ejecutable: `const EXE = process.platform === 'win32' ? '.exe' : '';`
- Helper de base de datos de la app (XDG): `process.platform === 'win32' ? (process.env.APPDATA || ~/AppData/Roaming) : (process.env.XDG_DATA_HOME || ~/.local/share)`, con override `APP_DATA_DIR`/`DATA_DIR` (default servidor `/var/lib/automatizapyme`).
- Centralizar separador `PYTHONPATH` via `path.delimiter`.

### `desktop/postgres-manager.js`
- **[block]** lineas 47, 104, 148, 172, 252 — todos los binarios con `.exe` hardcodeado (`pg_ctl.exe`, `initdb.exe`, `psql.exe`). `isPostgresInstalled()` (47) siempre false y todo spawn da ENOENT. Fix: `path.join(PG_BIN, 'pg_ctl'+EXE)`, etc.
- **[block]** lineas 64-65 — `zipUrl` = ZIP Windows x64 EDB (PE executables, no corren en Linux). Fix: descargar JAR zonky linux-amd64 -> extraer `postgres-linux-x86_64.txz`, o tarball theseus-rs. Ramificar URL+extractor por `process.platform`.
- **[block]** linea 76 — extraccion via `C:\Windows\System32\tar.exe`. Fix: `const tarCmd = process.platform==='win32' ? winTar : 'tar';` con `tar -xJf` (.txz/xz) o `tar -xzf` (.tar.gz) segun formato.
- **[block]** lineas 108, 119-126 — `--auth=trust` + regex de `pg_hba.conf`. En servidor es riesgo de seguridad y la regex `host all all 127.0.0.1/32 md5` probablemente **no matchea** los defaults Linux (scram-sha-256, peer/local, `::1`) -> el rewrite se vuelve no-op silencioso. Fix: password real para `pyme_user` (`initdb --pwfile` o `ALTER ROLE`), `scram-sha-256`, escribir `pg_hba.conf` explicito, `bind 127.0.0.1`. Anadir `--locale=C.UTF-8` (o `--no-locale`) para evitar fallo por locale ausente en imagenes minimas.
- **[easy]** lineas 9-12, 24-27 — `%APPDATA%` y fallback `AppData\Roaming`. Fix: base XDG (capa transversal).
- **[easy]** lineas 81, 109, 156 — `windowsHide:true` no-op en Linux (sin cambio).
- **[easy]** linea 174 — `stopPostgres` execSync solo depende del path `pgCtl` (resuelto por el fix `.exe`); flags/quoting ya cross-platform.
- **[easy]** linea 28 / 297-307 — `PG_PORT=5433`, URLs `localhost`/`asyncpg` ya cross-platform; opcional hacer puerto configurable por env.

> **Recomendacion alternativa servidor:** la via mas limpia puede ser NO portar el download-and-bundle de Postgres: instalar via apt/dnf (`postgresql-15`) o apuntar el backend a un Postgres del sistema via `DATABASE_URL`, reduciendo postgres-manager a un modulo guard/no-op en Linux. El plan abajo asume portar el manager para mantener la filosofia del .exe; evaluar el trade-off en fase 2.

### `desktop/python-manager.js`
- **[block]** linea 18 — `PYTHON_EXE = .../python.exe`. Fix: `process.platform==='win32' ? PYTHON_DIR/python.exe : VENV_DIR/bin/python3`.
- **[block]** linea 19 — `SITE_PACKAGES = PYTHON_DIR/Lib/site-packages`. Linux venv usa `lib/python3.11/site-packages`. Mejor: instalar en el venv normal (sin `--target`) y NO computar el path.
- **[block]** lineas 85-88 — `powershell -NoProfile Expand-Archive`. No existe en Linux y el embeddable no tiene contraparte. Fix: descargar python-build-standalone `install_only.tar.gz`, extraer con `tar -xzf`, y crear venv con `python3 -m venv`.
- **[block]** lineas 90-101 — edicion de `._pth` (`Lib\\site-packages`). Hack exclusivo del embeddable Windows. Fix: **eliminar el bloque** en Linux (el venv ya tiene site configurado).
- **[block]** lineas 169-172 — `pip install --target SITE_PACKAGES` + PYTHONPATH. Fix: en venv, `python3 -m pip install -r requirements.txt` sin `--target`. Asegurar `build-essential`/`libpq-dev` en el host si algun sdist (asyncpg, pydantic-core, numpy) debe compilar.
- **[easy]** linea 138 — `Scripts\pip.exe`. Fix: invocar pip como modulo: `spawn(PYTHON_EXE, ['-m','pip','install',...])`.
- **[easy]** lineas 239, 354 — `PYTHONPATH` usa `;` (separador Windows). En Linux colapsa ambas rutas. Fix: `[BACKEND_DIR, SITE_PACKAGES].join(path.delimiter)`.
- **[easy]** lineas 337-341 — `stopBackend`: `taskkill` YA guardado por `process.platform==='win32'`, else `SIGTERM` (correcto).
- **[easy]** lineas 259-264 + 253 — inyeccion `sys.path` por "embedded ignora PYTHONPATH": innecesaria en venv pero inofensiva.
- **[easy]** lineas 263, 256, 312 — puerto 8080 y host `0.0.0.0` hardcodeados. Fix: leer `PORT`/`HOST` de env.
- **[easy]** lineas 320-323 — `process.execPath + ELECTRON_RUN_AS_NODE`: bajo node plano es no-op y funciona.
- **[easy]** linea 10 — `PYTHON_LOG_FILE` en `~/Desktop`. Fix: `APP_DATA_DIR/backend.log` o stdout (journald).

### `desktop/jre-manager.js` (opcional — solo OpenDataLoader; hay fallback a pypdf)
- **[block]** linea 29 — `JAVA_EXE = JRE_DIR/bin/java.exe`. Fix: `path.join(JRE_DIR,'bin', process.platform==='win32' ? 'java.exe' : 'java')`.
- **[block]** lineas 67-68 — URL `windows/x64`. Fix: construir os/arch desde `process.platform`/`process.arch` (`linux`, `aarch64`).
- **[block]** lineas 78, 85 — `C:\Windows\System32\tar.exe -xf` sobre un .zip. Fix: `spawn('tar', ['-xzf', tarball, '-C', tempExtract])`.
- **[block]** `backend/app/services/pdf/parser.py:48` — consumidor hardcodea `java.exe`. Fix: `'java.exe' if os.name=='nt' else 'java'`; o preferir `JAVA_HOME` (ya se chequea primero en parser.py:43) / temurin-21-jre-headless del sistema.
- **[easy]** lineas 12-15 — APPDATA (XDG, capa transversal).
- **[easy]** linea 69/97 — nombrar `jre.tar.gz` en Linux; la deteccion de carpeta `jdk-*-jre` (99-108) es portable.
- **[easy]** linea 86 — `windowsHide` no-op.
- **[easy]** `service-manager.js:268-270` — probe de `java.exe` para `JAVA_HOME`. Fix: reusar `getJavaPath()` de jre-manager (ya importado, linea 53).
- Recomendacion servidor: **no auto-descargar**; instalar `temurin-21-jre-headless` y exportar `JAVA_HOME`, o aceptar el fallback pypdf. Anadir verificacion SHA256 (TODO en `desktop/docs/dependency_security.md:76`).

### `desktop/service-manager.js`
- **[block]** lineas 121-144 `killOrphanProcesses` — `netstat -ano | findstr | taskkill` (Windows-only, sin rama posix). Se llama en cada boot (525) y shutdown (620). Fix: rastrear PIDs de hijos propios y `child.kill()`; o rama posix con `ss -lptn 'sport = :PORT'` / `lsof -ti tcp:PORT` + `kill -TERM`/`-KILL`.
- **[block]** lineas 278-303 `runSpawn` + 290 — timeout-kill via `taskkill` sin guard. Fix: rama `win32` taskkill / posix `SIGTERM` luego `SIGKILL`; preferir `spawn` con array de args.
- **[block]** lineas 268-270 `getBackendEnv` JAVA_HOME — probe `java.exe`. Fix: `javaBin = win32?'java.exe':'java'` o reusar `getJavaPath()`.
- **[block]** lineas 59-67, 162-169, 199-219 — Electron `app.isPackaged`/`safeStorage`. En headless cae a secrets.json **plaintext** (regresion de seguridad). Fix: leer `SECRET_KEY`/`TENANT_ENCRYPTION_KEY` de env (systemd `EnvironmentFile=`) o fichero 0600; `mode:0o600` al escribir. Opcional `PROJECT_ROOT`/`APP_ROOT` por env.
- **[easy]** linea 12 — APPDATA (XDG, default `/var/lib/automatizapyme`).
- **[easy]** linea 16 — `BOOT_LOG` en `~/Desktop`. Fix: stdout (journald) o `APP_DATA_DIR/boot.log`.
- **[easy]** lineas 311-312 — `npmCmd` ya correcto (`win32?'npm.cmd':'npm'`); asegurar `npm`/`node` en PATH del servicio.
- **[easy]** lineas 424-433 — frontend `spawn('node', [nextBin,'start','-H','0.0.0.0','-p','3000'])` funciona; opcional `detached:true` o `KillMode=control-group`.
- **[easy]** lineas 457-467 `stopFrontend` — ya tiene rama posix `SIGTERM`.
- **[easy]** lineas 472-514 `waitForHTTP` — `127.0.0.1` portable; opcional pegar a `/health`.
- **[easy]** `startAll` exige `onProgress`: pasar logger de consola / hacerlo no-op.

### `desktop/main.js`, `launch.js`, `sync.js`, `package.json`
- **[block]** Descartar `main.js` (GUI lifecycle), `launch.js` (lanzador Electron), `sync.js` (hot-copy a .exe Windows) y el bloque `build.win` de `package.json` en el path servidor. Sustituir por `bootstrap.js` + unidad systemd. El codigo fuente (backend/frontend) se despliega via git/CI/rsync, no como extraResources de electron-builder. La red ya es 0.0.0.0-friendly (`next start -H 0.0.0.0`; `_BACKEND_HOST` configurable).

## 5. Plan de implementacion ordenado

1. **Capa abstracta de path/plataforma** (sin deps). Helpers `EXE`, base XDG/`APP_DATA_DIR`, join de `PYTHONPATH`. *Bloquea a todo lo demas.*
2. **Port postgres-manager.js** (dep: fase 1). `.exe`-suffix, URL zonky/theseus + extractor `tar`, `initdb --locale`, password scram + `pg_hba` explicito. **Verificar: initdb + start + createDatabase en una VM/host Linux real.**
3. **Port python-manager.js** (dep: fase 1; independiente de fase 2). Sustituir embeddable por python-build-standalone + venv, borrar `._pth`, quitar `--target`, separador `PYTHONPATH`, log dir. **Verificar: venv + pip install + uvicorn + migraciones Alembic.**
4. **Port jre-manager.js + parser.py** (dep: fase 1; opcional, baja prioridad). O saltar y usar JAVA_HOME del sistema / fallback pypdf.
5. **Port service-manager.js** (dep: fases 2-3). `killOrphanProcesses` posix, `runSpawn` timeout, JAVA_HOME, secrets por env, logs a stdout, `startAll` con logger.
6. **Extraer bootstrapper headless** `desktop/bootstrap.js` (dep: fase 5). `require.main===module`, `startAll`, signal handlers -> `stopAll`.
7. **Unidad systemd + .env** (dep: fase 6). Ver seccion 6.
8. **First-run init + backups** (dep: fases 6-7). Idempotencia (no re-descargar si ya instalado), `pg_dump` programado, persistencia de PGDATA entre updates.
9. **Test end-to-end** (dep: todo). Primer arranque limpio en host glibc, reinicio, shutdown limpio (sin huerfanos), restore de backup.

## 6. systemd / arranque

Enfoque recomendado: **una unica unidad `Type=simple`** que ejecuta `bootstrap.js`, dejando que systemd reape el arbol de hijos (Postgres/uvicorn/next) via `KillMode=control-group`. Esto reduce la dependencia del hack de orphan-cleanup.

```ini
# /etc/systemd/system/automatizapyme.service
[Unit]
Description=Automatiza-pyme (headless self-hosted)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=automatizapyme
Group=automatizapyme
Environment=APP_DATA_DIR=/var/lib/automatizapyme
Environment=PORT=8080
Environment=HOST=127.0.0.1
EnvironmentFile=/etc/automatizapyme/secrets.env   # SECRET_KEY, TENANT_ENCRYPTION_KEY, DB password
WorkingDirectory=/opt/automatizapyme/desktop
ExecStart=/usr/bin/node /opt/automatizapyme/desktop/bootstrap.js
KillMode=control-group
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=on-failure
# Postgres/initdb NO corren como root: User no-root es obligatorio

[Install]
WantedBy=multi-user.target
```

- **Directorio de datos**: `APP_DATA_DIR` (default servidor `/var/lib/automatizapyme`, fallback usuario `$XDG_DATA_HOME`/`~/.local/share/AutomatizaPyme`). Contiene `pgsql/`, `pgdata/`, `python/`/`venv/`, `jre/`, `backend.log`. Debe ser propiedad del usuario del servicio y persistir entre updates.
- **Secretos**: `EnvironmentFile` 0600 (no `safeStorage`).
- Alternativa (una unidad por proceso: postgres / backend / frontend con dependencias `After=`) si se quiere reinicio granular; mas complejo, no recomendado para v1.

## 7. Riesgos y datos

- **Persistencia de PGDATA entre updates**: `pgdata/` vive en `APP_DATA_DIR`, separado del codigo en `/opt`. Un `git pull`/redeploy NO debe tocarlo. Riesgo: borrar APP_DATA_DIR reinicializa la DB. Marcar el dir como volumen de estado y documentarlo.
- **Compatibilidad glibc**: builds gnu (Postgres zonky, Python PBS) requieren glibc>=2.17. En Alpine/musl fallan -> usar variantes `-alpine`/`-musl` (Python musl no carga wheels C-extension). Validar `ldd --version` en first-run y abortar con mensaje claro.
- **Backups (pg_dump)**: programar `pg_dump`/`pg_dumpall` (cron o timer systemd) hacia `APP_DATA_DIR/backups`, usando el `pg_dump` del arbol portable. Probar restore. Sin esto, una corrupcion de PGDATA = perdida total.
- **Puertos/firewall**: backend 8080 y frontend 3000; `bind 127.0.0.1` para Postgres (5433). Para acceso externo, reverse proxy (nginx/Caddy) delante de :3000, no exponer uvicorn/Postgres directos. Abrir solo el puerto del proxy en el firewall.
- **Verificacion de integridad**: hoy NO hay verificacion de hash/firma de descargas (TODO en `desktop/docs/dependency_security.md:76`), ni en Windows. Anadir SHA256 (JRE trae `.sha256.txt`; Postgres/Python publican checksums) antes de produccion.
- **No correr como root**: initdb y el server Postgres se niegan a arrancar como root; la unidad debe usar `User=` no-root.
- **Tree-kill / huerfanos**: sin `KillMode=control-group` y sin signal handling en bootstrap, un stop dejaria Postgres/uvicorn/next vivos.

## 8. Estimacion de esfuerzo

| Fase | Esfuerzo |
|------|----------|
| 1. Capa path/plataforma | 0.5 dia |
| 2. postgres-manager (download zonky/theseus, initdb, pg_hba scram) | 2-3 dias (el mas arriesgado) |
| 3. python-manager (PBS + venv, borrar embeddable hacks) | 1.5-2 dias |
| 4. jre-manager + parser.py (opcional) | 0.5-1 dia (o 0 si se usa JRE del sistema) |
| 5. service-manager (posix kill, secrets, logs) | 1.5 dias |
| 6. bootstrap.js + signal handling | 0.5 dia |
| 7. systemd + .env | 0.5 dia |
| 8. first-run init + backups | 1 dia |
| 9. test e2e en host Linux real | 1-1.5 dias |
| **Total** | **~9-12 dias** (1 ingeniero), ~2 semanas con margen |