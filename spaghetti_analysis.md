# 🍝 Análisis de Código Espagueti — AutomatizaPyme

> **Scope:** 565 archivos · ~74.053 líneas de código fuente (frontend + backend, excluye `node_modules`, `dist`, `.next`)

---

## Resumen Ejecutivo

| Severidad | Problemas encontrados |
|-----------|----------------------|
| 🔴 Crítico | Funciones de 200–416 líneas · Páginas God-Component con 40+ hooks |
| 🟠 Alto | 58 `except Exception` genéricos · Lógica PDF triplicada |
| 🟡 Medio | Acoplamiento alto en 2 services · 80 bloques de código comentado |
| 🟢 Bajo | 0 `console.log` sin comentar · 0 `print()` de debug en producción |

**Conclusión:** El proyecto tiene buena disciplina de limpieza (sin logs de debug, sin TODOs abandonados), pero sufre de un patrón claro de **monolitos verticales** — módulos que crecieron sin ser particionados.

---

## 🔴 Crítico: Funciones / Métodos Gigantes (Backend)

Las siguientes funciones superan las **100 líneas** — el umbral donde el cerebro humano pierde el hilo de ejecución:

| Archivo | Líneas | Inicio |
|---------|--------|--------|
| `services/pdf_reports/_fiscal.py` | **416** | L371 |
| `services/pdf/invoices.py` | **402** | L39 |
| `services/pdf/hr.py` | **373** | L86 |
| `services/pdf_reports/_fiscal.py` | **288** | L41 |
| `services/pdf/invoices.py` | **273** | L457 |
| `agents/email/agent.py` | **244** | L255 |
| `services/pdf/albaranes.py` | **240** | L30 |
| `agents/orchestrator/node_handlers.py` | **226** | L575 |
| `agents/orchestrator/dispatchers/reports.py` | **218** | L30 |
| `services/pdf/invoices.py` | **212** | L731 |
| `services/pdf_reports/_operational.py` | **211** | L230 |
| `services/pdf/hr.py` | 188 / 170 / 147 | múltiples |
| `services/reports/aggregation.py` | **161** | L163 |
| `agents/workflow/agent.py` | **161** | L38 |
| `services/integration/heartbeat.py` | **155** | L80 |
| `agents/tool_registry.py` | **153** | L21 |

> [!CAUTION]
> `invoices.py` tiene **3 funciones de +200 líneas cada una** — es el archivo más urgente a refactorizar.

---

## 🔴 Crítico: God Components (Frontend)

Páginas que mezclan **estado, lógica de negocio, efectos secundarios y presentación** en un solo componente:

| Página | Líneas | Hooks (useState/useEffect/etc.) |
|--------|--------|---------------------------------|
| `automatizaciones/page.tsx` | 650 | **42** |
| `page.tsx` (dashboard raíz) | 670 | 25 |
| `plantillas/page.tsx` | **1.029** | 24 |
| `banca/page.tsx` | 731 | 23 |
| `rrhh/nominas/page.tsx` | 535 | 23 |
| `documentos/page.tsx` | 356 | 21 |
| `compras/facturas/page.tsx` | 405 | 20 |
| `informes/page.tsx` | 608 | 20 |
| `clientes/page.tsx` | 641 | 19 |
| `inventario/stock/page.tsx` | 684 | 19 |

> [!CAUTION]
> `automatizaciones/page.tsx` con **42 hooks** es el God Component más grave. Un componente normal no debería tener más de 6–8.

**Síntoma típico:** lógica de filtrado, llamadas a API, validación de formularios, y renderizado de tabla conviviendo en el mismo `page.tsx` de 600+ líneas.

---

## 🟠 Alto: `except Exception` Genérico (58 ocurrencias)

El manejador de errores más peligroso — silencia cualquier excepción, incluyendo bugs reales:

| Archivo | Ocurrencias | Riesgo |
|---------|-------------|--------|
| `llm_factory.py` | **10** | Falla de LLM puede silenciarse |
| `tasks_scheduler.py` | **9** | Tareas cron pueden fallar sin aviso |
| `tasks_orchestrator.py` | **8** | El orquestador puede perder jobs |
| `observability.py` | **6** | El sistema de monitoreo falla en silencio |
| Resto (tenant, workers, etc.) | ~25 | Distribuido |

> [!WARNING]
> `observability.py` tiene 6 `except Exception` silentes — el sistema que debería detectar errores, falla sin reportarlos.

---

## 🟠 Alto: Lógica PDF Duplicada / Triplicada

Hay **dos capas paralelas** de generación de PDF sin unificación:

```
backend/app/services/pdf/
├── invoices.py     943 líneas  ← generación directa
├── hr.py           987 líneas  ← generación directa
└── albaranes.py    270 líneas

backend/app/services/pdf_reports/
├── _fiscal.py      787 líneas  ← capa de reportes
├── _operational.py 658 líneas
└── _snapshot.py    619 líneas
```

**Problema:** Las dos carpetas hacen trabajo similar (construir PDFs con datos del ERP) pero con implementaciones distintas. `invoices.py` solo tiene 4 funciones que suman ~900 líneas, vs `_fiscal.py` con 4 funciones de ~700 líneas. Probable duplicación lógica.

---

## 🟠 Alto: Archivos Monolíticos (Top 10 por líneas)

| Archivo | Líneas | Funciones | Líneas/función |
|---------|--------|-----------|----------------|
| `scripts/full_system_test.py` | 1.396 | 28 | ~50 |
| `services/pdf/hr.py` | 987 | 11 | **~90** |
| `services/pdf/invoices.py` | 943 | 4 | **~235** |
| `agents/billing/tools.py` | 920 | 17 | ~54 |
| `agents/orchestrator/node_handlers.py` | 871 | 13 | **~67** |
| `services/documents/service.py` | 807 | 28 | ~29 |
| `agents/excel/tools.py` | 805 | 25 | ~32 |
| `services/pdf_reports/_fiscal.py` | 787 | 4 | **~197** |
| `services/workflow/service.py` | 785 | 24 | ~33 |
| `agents/hr/tools.py` | 715 | 15 | ~48 |

> [!NOTE]
> Los archivos con ratio líneas/función alto (>60) son los más críticos: pocas funciones enormes, no muchos archivos.

---

## 🟡 Medio: Acoplamiento Alto

Solo **2 archivos** con >6 imports internos de `from app.`:

| Archivo | Imports internos |
|---------|-----------------|
| `services/workflow/service.py` (785L) | 7 |
| `services/documents/service.py` (807L) | 7 |

Esto es relativamente bueno — el resto del codebase está bien desacoplado.

---

## 🟡 Medio: Código Comentado (80 bloques)

Hay **80 líneas** con código Python comentado (patrones `# def`, `# return`, `# if`, etc.). Indican dead code o experimentos no eliminados. No es crítico pero añade ruido.

---

## ✅ Lo que está Bien

| Cosa | Resultado |
|------|-----------|
| `print()` de debug en producción | **0** |
| `console.log` sin comentar (frontend) | **0** |
| TODO/FIXME/HACK abandonados | **0** |
| `as any` en TypeScript | Muy bajo (< 15 en todo el proyecto) |
| Imports circulares evidentes | Ninguno detectado |

---

## 📋 Plan de Acción Priorizado

### Sprint 1 — Alta urgencia (backend crítico)
1. **Partir `invoices.py`** en 3 módulos: `invoice_builder.py`, `invoice_sections.py`, `invoice_pdf.py`
2. **Partir `_fiscal.py`** — extraer función de 416L en 4–5 funciones con nombres descriptivos
3. **Refactorizar `llm_factory.py`** — añadir manejo específico de errores en los 10 `except Exception`

### Sprint 2 — Frontend god components
4. **`automatizaciones/page.tsx`** (42 hooks) → extraer: `useAutomatizaciones()` hook, `AutomatizacionForm`, `AutomatizacionList`
5. **`plantillas/page.tsx`** (1.029L) → el más grande del frontend, dividir en componentes
6. **`banca/page.tsx`** y **`nominas/page.tsx`** → custom hooks para agrupar estado relacionado

### Sprint 3 — Limpieza media
7. Unificar las dos capas PDF (`services/pdf/` + `services/pdf_reports/`) si hay lógica duplicada
8. Reemplazar `except Exception` silentes en `observability.py` por manejo específico
9. Eliminar los 80 bloques de código comentado

---

## Estimación de Esfuerzo

| Área | Archivos afectados | Esfuerzo estimado |
|------|--------------------|-------------------|
| Backend funciones gigantes | 8 archivos | 3–4 días |
| Frontend god components | 5 páginas | 2–3 días |
| Manejo de errores | 6 archivos | 1 día |
| Código comentado / limpieza | Todo el proyecto | 2–3 horas |
| **Total** | | **~7–9 días de trabajo** |
