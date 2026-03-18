# Estado del Proyecto ERP: Plan de Optimización y Continuación

Este documento resume el progreso de sesiones anteriores y el estado actual del proyecto.

## 📋 Contexto General
- **Proyecto**: ERP multiagente para PYMEs españolas (AutomatizaPyme).
- **Reglas establecidas**: El repositorio corre únicamente en local. NO comprobar el `.env` y POSPONER el sistema de validación de licencias hasta disponer de un VPS.

---

## ✅ Todo completado hasta la fecha

### Sprint 1 — Calidad de código y bugs críticos
- Outputs de agentes IA: `_format_summary()` → frases legibles en español (no JSON crudo)
- WebSocket URL dinámica (env var `NEXT_PUBLIC_WS_URL`)
- `ConfirmDialog` global con store Zustand (reemplaza `window.confirm()` en 22 archivos)
- `downloadBlob()` centralizado en `api.ts`
- `logger.ts` frontend + `logError()` reemplaza todos los `console.error` (26 archivos)
- Todos los `print()` del backend reemplazados por `logger.*`
- `asyncio.sleep()` en orquestador (no más `time.sleep()`)

### Sprint 2 — Solidez del sistema
- Prompt del coordinador reescrito con contexto legal español (PGC, AEAT, IVA, SS, ET)
- Validación de tipos de IVA legales (0/4/10/21%) en `create_invoice`
- Validaciones post-cálculo (importe negativo, factura en cero)
- Caché LLM en memoria ya integrada en `classify_node` y `plan_node`
- `llm_factory.py` — bug `fallback` undefined corregido en todos los providers
- Fallback chain Groq → OpenAI → Ollama → Mock

### Sprint 3 — Reglas de negocio españolas
- `InvoiceSeries`: numeración correlativa automática `F2026-0001` con `SELECT FOR UPDATE`
- Nóminas: `_calc_payroll()` con tasas SS 2025 reales; endpoints `/payrolls/auto` y `/employees/{id}/payroll/preview`
- Libro de registro AEAT exportable en CSV (`GET /api/v1/reports/libro-registro`)
- Health check `/health` con ping activo a PostgreSQL

### Sprint 4 — UX
- `/primeros-pasos`: 8 pasos guiados, progreso localStorage, prerequisitos, carousel IA

### Arquitectura
- `models.py` modularizado en dominios: `billing.py`, `hr.py`, `crm.py`, `auth.py`, etc.
- `orchestrator.py` → paquete `orchestrator/` con `_core.py`, `state.py`, `__init__.py`
- 67 tests de integración en `backend/tests/`

---

## 🚀 Próximos pasos posibles

### 🟡 Pendiente
- **10. Actualizar dependencias Frontend** — React/Next.js. Evaluación de riesgo necesaria antes de hacer.
- **Validación de licencias** — pospuesta hasta VPS disponible.
- **Tests nuevos** — cubrir los endpoints añadidos (series, nómina auto, libro registro).
- **Página de nóminas mejorada** — integrar el botón "Calcular automáticamente" usando `api.hr.payrolls.generateAuto()` y el modal preview con tasas SS desglosadas.
- **Exportar libro de registro desde el frontend** — añadir botón en `/impuestos` o `/contabilidad`.
