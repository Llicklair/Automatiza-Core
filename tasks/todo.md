# Tareas activas — AutomatizaCore

Última actualización: 2026-06-12

> Solo trabajo **PENDIENTE**. Lo completado se ha retirado (queda en el historial
> git). Vista global priorizada y verificada contra el código:
> [roadmap_global_2026-06-11.md](./roadmap_global_2026-06-11.md).

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
- [~] **F2.9b Calcar el resto de modelos AEAT** — patrón sobre `_aeat_layout.py` +
  `aeat/casillas_NNN.py` (con `aeat/_casilla.py` compartido). Investigación de
  casillas hecha por workflow (16 agentes, verificación adversarial).
  - [x] **111** ✅ casillas 01-09 (trabajo/act. económicas) + 28/29/30 liquidación.
  - [x] **115** ✅ casillas 01-05 (resultado = 03 − 04).
  - [x] **390** ✅ casillas clave IVA anual (01-06 devengado, 33/34/47, 48/49/64, 65/84/86).
  - [ ] **190 / 347 / 349** (informativas-listado) — resumen con casillas + listado registro.
  - [ ] **200 / 100** (resumen_grande) — casillas clave de liquidación (preview).
  - [ ] Migrar el **303** al módulo compartido (cubierto por su batería de tests; al
    migrar, pasar `pct_codes=_PCT_CASILLAS` en cada `_casillas_table` — sus 02/05/17… son %).

## Gestoría / Firma

- [~] **F3.11 Firma AutoFirma** ✅ implementado (2026-06-12) — backend
  (`autofirma.py` + init/callback) + **endpoint de estado** `GET /signing/
  autofirma/status/{token}` (3 tests) + **botón "Firmar"** en `DocumentCard`
  (aprobados): obtiene el PDF → base64 → `init` → lanza `afirma://` → polling de
  estado → toast. **Pendiente de verificación e2e**: requiere AutoFirma instalado
  para probar el handshake del certificado FNMT (no verificable en CI).

## AIEmployee — Contrato del custom

Para justificar existir frente a `default + system_prompt_addendum`, un custom
debe aportar ≥2 de 4 capacidades; si solo tono/expertise → degradar a "Perfil".

| Capacidad | Campo BD |
|---|---|
| Scope filter persistente | `scope` (JSONB) |
| Memoria persistente | `memory_enabled` + tabla `employee_memory` |
| Knowledge base privada | `knowledge_enabled` + filtro RAG por employee |
| Workflows predefinidos | `workflows` (JSONB) |

Migración `0029_aiemployee_contract` + modelo + `employee_memory` ✅. Pendiente:
- [ ] **UI split "Empleado IA" vs "Perfil"** — el alta de custom obliga a marcar
  ≥2 capacidades; si solo tono/expertise, redirige a alta de "Perfil".
  Pendiente de **diseño UX** (no bloqueante para backend).
- [ ] **Aplicar el contrato a customs existentes** — auditar `AIEmployees` con
  `is_builtin=False`: los que no cumplan → "Perfil" (migración data-only) o
  rellenar scope/workflows. Necesita **tu criterio** sobre cuáles son empleados
  reales. (Origen: bug Yolanda Sánchez — custom roto que intercepta routing.)

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
- [ ] Migración i18n real por módulos (proyecto grande, en curso por el usuario).

## Auto-update / Release (#5 — ops + decisión usuario)

Wiring de código OK + `desktop/package.json` `publish` corregido. Para distribuir:
- [ ] Rebuild del instalador (`frontend: npm run build` → `desktop: npm run dist`)
  — el `app-update.yml` se hornea en build-time (el `.exe` actual tiene owner placeholder).
- [ ] Repo de releases **público** (electron-updater no actualiza desde repo
  privado sin token embebido inseguro).
- [ ] Sanear secretos del `.env` horneado en `build.extraResources`
  (placeholders + Electron safeStorage).

## Acciones de usuario (no código)

- [ ] **F1.3 OAuth Google → Production mode** — Cloud Console → "PUBLISH APP"
  (~30 s). Sin esto, los refresh tokens caducan a 7 días.
- [ ] OAuth verification + CASA assessment Tier 1 para `gmail.send` — cuando
  haya 5+ clientes confirmados.
- [ ] Roadmap M1-M2 (memorias): numeración correlativa, JWT safeStorage, AEAT FNMT.

---

## Notas / gotchas (referencia)

- **Cambios backend exigen cerrar y reabrir `AutomatizaCore.exe`** (backend
  Python embebido por Electron — no recoge cambios en caliente).
- **OAuth Google en Testing mode**: refresh tokens expiran a 7 días; 100 test
  users máx de por vida. Producción exige publicar (ver F1.3).
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
