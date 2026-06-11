# Roadmap GLOBAL unificado — AutomatizaCore (2026-06-11)

> **Fuente única de verdad.** Consolida todos los docs de `tasks/` (backlog, todo,
> roadmap, auditorías, specs, pilot-readiness, go-to-market) **contrastados contra
> el código real** (agentes de scoping + verificación directa). Reemplaza a
> `diagnostico_real_2026-06-11.md` y `roadmap_implementacion_2026-06-11.md`.
>
> Estado por ítem: **PENDIENTE** (no existe) · **PARCIAL** (existe pero sin cablear/incompleto) ·
> **USER** (acción manual del usuario, no código). Esfuerzos orientativos 1 dev.

## Método y advertencia

Verificado el 2026-06-11. **Lección recurrente**: los diagnósticos previos (y los
greps estrechos) sobre-reportan huecos. Antes de planificar trabajo, confirmamos
que NO eran huecos: VeriFactu (cadena), modelos 111/130/190/347/390, numeración de
facturas, cliente PSD2 Nordigen, worker de marketing + OAuth, scheduler de email,
aprobación humana (`autonomy_gate`), tabla `employee_memory`, RAG semántico,
UI de fichajes/CRM/marketing — **todo existe**. El trabajo real es **cablear
integraciones finales y añadir contenido especializado**, no construir de cero.

---

# FASE 1 — Desbloquear venta legal + piloto (P0)

Sin esto no se puede vender/distribuir legalmente. Es la prioridad absoluta.

| # | Ítem | Estado | Archivos clave | Fuente |
|---|---|---|---|---|
| 1.1 | **VeriFactu: RegistroAlta/Anulación XML** (hoy solo `payload_canonico`) | PENDIENTE | crear `services/billing/registro_facturacion.py` | roadmap_impl, depth-audit |
| 1.2 | **VeriFactu: QR en factura** | PENDIENTE | `services/billing/qr_generator.py` + PDF; dep `qrcode` | roadmap_impl |
| 1.3 | **VeriFactu/AEAT: envío real mTLS** (hoy `dry_run=True`, sin cert cliente) | PARCIAL | `services/aeat/sede_client.py`, `certificate_storage.py`; dep `xmlsec`/`signxml` | depth-audit, pilot |
| 1.4 | **XSD oficiales AEAT** (carpeta `xsd/` no existe → validación no-op) | PENDIENTE | `services/aeat/xsd/` + `xsd_validation.py` + `scripts/update_aeat_xsd.py` | roadmap_impl |
| 1.5 | **Firma del instalador** (`forceCodeSigning: false` → SmartScreen) | PENDIENTE / USER | `desktop/electron-builder.yml`; requiere comprar certificado | auditoria_06-10, pilot |
| 1.6 | **Auto-update: config publish real** (owner/repo) | PENDIENTE | `desktop/package.json` | plan-gtm, pilot |
| 1.7 | **System tray invisible en runtime** (código existe, no aparece) | PENDIENTE (bug) | `desktop/tray-manager.js` | auditoria_06-10 |
| 1.8 | **BYOK: paso de API key en onboarding** (wizard no pide LLM key) | PENDIENTE | `services/onboarding/wizard.py` (+ paso `llm_config`) | plan-gtm |
| 1.9 | **Auditar simetría de dominios** (ejecutar `audit_domain_completeness.py` y cerrar `VALID_DOMAINS`×`DISPATCHER_MAP`×`_KEYWORD_MAP`) | PARCIAL | script ya existe, falta ejecutarlo y cerrar residuales | todo F1.1 |
| 1.10 | **OAuth Google → modo Production** (Cloud Console) | USER | acción manual ~30s, no código | todo F1.3 |

---

# FASE 2 — Completar producto para go-to-market (P1)

Features a medias que restan valor/UX una vez hay usuarios.

### Fiscal
| # | Ítem | Estado | Archivos | Fuente |
|---|---|---|---|---|
| 2.1 | XML oficial para 111/347/349/390 (hoy solo 303/130 tienen XML; resto solo datos+PDF) | PARCIAL | `services/reports/modelos_aeat.py`, patrón `modelo_303_xml.py` | scoping fiscal |
| 2.2 | ~~Modelo 190 clave G (profesionales)~~ **HECHO** (2026-06-11): `build_modelo_190_data` incluye clave G desde facturas con retención IRPF; `retencion_irpf_amount` ya existía (sin migración); +2 tests. Clave K (premios) fuera de alcance (sin modelo de datos). | HECHO | `services/reports/modelos_aeat.py` | backlog, scoping |
| 2.3 | Asistente fiscal preventivo (widget `/impuestos` + notificación) — reusa `services/aeat/` | PENDIENTE | nuevo widget + `preventive_check.py` existente | todo F1.4 |

### Facturación / Contabilidad
| 2.4 | ~~billing→accounting: asiento automático al emitir factura~~ **HECHO** (ya cableado): `create_invoice_journal_entry` se invoca en creación (agente) e importación de facturas | HECHO | `services/billing/auto_accounting.py` | depth-audit |
| 2.5 | VeriFactu: auditoría de envíos (`verifactu_submissions`) | PENDIENTE | nueva tabla + logs | roadmap_impl |

### Documentos / Gestoría
| 2.6 | Servicio de generación de documentos (template + LLM + ReportLab) | PENDIENTE | `services/documents/generate.py` | scoping docs |
| 2.7 | Plantillas reales de gestoría (contrato, despido, nómina formal, poder) | PENDIENTE | catálogo + prompts; hoy `template_service.py` solo presets de color | scoping docs |
| 2.8 | Numeración + pie legal de docs de gestoría (extender `numbering.py`) | PENDIENTE | `services/billing/numbering.py` (extender) | scoping docs |
| 2.9 | Cablear firma (`signed_documents`/AutoFirma) a la generación | PENDIENTE | `routes/signing.py` (existe, desacoplado) | scoping docs |

### Onboarding
| 2.10 | Agente de onboarding (Fase 2 spec): `agents/onboarding/` (wrapper de wizard/regap/simulate_303) | PENDIENTE | crear agente | onboarding-spec |
| 2.11 | Frontend wizard UI (hoy solo `lib/api/onboarding.ts`, sin componentes) | PENDIENTE | `components/onboarding/` + página | scoping onboarding |
| 2.12 | Cablear onboarding al Coordinador (intent "configura mi empresa") | PENDIENTE | `agents/orchestrator/` dispatcher | onboarding-spec |

### Banca
| 2.13 | PSD2: consumir cliente Nordigen en `sync_transactions` + flujo requisition (cliente ya completo) | PENDIENTE | `services/banking/service.py`, `TenantIntegration` (campos) | scoping banca, backlog INT.PSD2 |
| 2.14 | Parser N43 multibanco + fixtures de 5 bancos (INT.FIX/INT.PAR) | PENDIENTE | `services/banking/parsers/`, `tests/fixtures/n43/` | backlog |
| 2.15 | Reconciliador bidireccional (`reconciliation_attempts`) (INT.REC) | PENDIENTE | bloqueado por 2.14 | backlog |
| 2.16 | UX demo-vs-live de credenciales (banca/email no señalizan modo) | PARCIAL | banking/email service + frontend | depth-audit |

### Inventario
| 2.17 | Venta/POS → decremento de stock (inventario no enlazado a ventas) | PENDIENTE | integración ventas↔inventario | depth-audit |

### BYOK / IA / Pricing
| 2.18 | Token ledger persistente a BD (hoy `agent_budget` en memoria) | PARCIAL | `services/agent_budget*` | plan-gtm |
| 2.19 | LLM usage dashboard UI (`UsageWidget` vacío; endpoint `/llm-usage/stats` existe) | PARCIAL | `frontend/.../_components/UsageWidget.tsx` | plan-gtm |

### Frontend / i18n
| 2.20 | i18n: completar traducción o ocultar idiomas no traducidos (≈80% hardcoded, 53 "Cargando…") — **migración next-intl en curso** | PARCIAL (en progreso) | `frontend/src/messages/`, dominios pendientes | auditoria_frontend, git WIP |

### Arquitectura / Backend
| 2.21 | Módulo neutral para dispatch (`_resolve_upload_dir`/`_invoke_dispatcher` importados privados desde 3 módulos) | PENDIENTE | refactor servicios documents | auditoria_backend |

### Operaciones / GTM
| 2.22 | `tasks/contingency.md` (6 riesgos) antes de lanzar | PENDIENTE | doc | backlog CONT.1 |
| 2.23 | Knowledge base público (30-40 artículos, Docusaurus) | PENDIENTE | `docs/kb/` | backlog OPS.KB |
| 2.24 | Widget Crisp en frontend (SLA) | PARCIAL | `docs/sla_tiers.md` existe; falta widget | backlog OPS.SLA |

---

# FASE 3 — Mejoras y mercado ampliado (P2)

| # | Ítem | Estado | Fuente |
|---|---|---|---|
| 3.1 | Analytics de marketing (modelo métricas + fetch por red + job diario; publisher ya guarda `platform_post_id`) | PENDIENTE | roadmap_impl |
| 3.2 | Normativa fiscal → RAG (hoy hardcoded en `compliance/tools.py`; reusa BOEScraper + `cosine_topk`) | PENDIENTE | roadmap_impl |
| 3.3 | Modelo 131 (IRPF módulos) y Modelo 200 (Sociedades) | PENDIENTE | backlog |
| 3.4 | Multi-currency banca (`requires_manual_review`) (INT.CUR) | PENDIENTE | backlog |
| 3.5 | Búsqueda semántica: ~~endpoint REST dedicado~~ **HECHO** (2026-06-11): `GET /documents/search` (coseno en Python, scoped por tenant, +4 tests); **falta UI** frontend | PARCIAL (backend hecho) | `api/v1/routes/documents.py` | depth-audit |
| 3.6 | REGAP: consulta real a AEAT (hoy mockeado) | PARCIAL | plan-gtm, scoping |
| 3.7 | ~~Scheduler: dominio por defecto "billing" → "chat"~~ **HECHO**: `_infer_domain_from_text` ya devuelve "chat" por defecto | HECHO | auditoria_backend |
| 3.8 | ~~Quitar datos DEMO aleatorios en producción~~ **HECHO**: gated tras `BANKING_DEMO_SYNC` + `BankSyncNotAvailableError` si off + `[DEMO]` excluido de analíticas | HECHO | auditoria_backend |
| 3.9 | README: añadir N43/retenciones/tesorería al estado de módulos | PENDIENTE | auditoria_06-10 |
| 3.10 | **TicketBAI** (País Vasco/Navarra) — reusa 80-90% (XAdES/cert/cadena) | PENDIENTE | scoping fiscal |

---

# Secuencia recomendada

1. **Fase 1 completa** — bloquea venta/distribución. Crítico: 1.1-1.4 (VeriFactu+XSD) y 1.5-1.7 (desktop). 1.10 es acción tuya.
2. **Fase 2 por dominios** — priorizar fiscal (2.1-2.3) + docs gestoría (2.6-2.9) + onboarding (2.10-2.12), que dan más valor percibido. Banca/inventario después.
3. **Fase 3** — cuando el core esté sólido; TicketBAI solo si entras en mercado foral.

# Bloqueantes que dependen de ti (no código)
- **1.5** Comprar certificado de firma de código (Windows).
- **1.10** Pasar OAuth de Google a Production en Cloud Console.
- **1.3/2.13/3.6** Credenciales reales (cert AEAT, Nordigen, REGAP) para salir de dry-run/demo.

# Docs que este roadmap reemplaza/consolida
- `diagnostico_real_2026-06-11.md` y `roadmap_implementacion_2026-06-11.md` → subsumidos aquí.
- `backlog.md`, `todo.md`, `roadmap.md` → siguen como trackers vivos; este doc es la vista global priorizada y verificada contra código.
