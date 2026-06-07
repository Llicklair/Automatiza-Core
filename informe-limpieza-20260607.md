# Informe de limpieza de código

**Proyecto:** AutomatizaPyme · **Fecha:** 2026-06-07
**Alcance:** backend Python (`backend/app`) + frontend TS (`frontend/src`)
**Modo configurado:** informe + arreglos seguros.

## ⚠️ No se han aplicado arreglos automáticos en esta pasada

El árbol de trabajo tiene **49 archivos modificados sin commitear** (+1 sin trackear)
que no son de esta rutina. Aplicar arreglos automáticos ahora los mezclaría con tu
trabajo en curso y, si los tests fallaran, el revert podría pisarlos. Por seguridad,
esta ejecución es **solo análisis**. Cuando tengas el árbol limpio (commit o stash de
lo pendiente), vuelve a lanzarla y aplicaré los arreglos de bajo riesgo.

Todo lo de abajo es solo lectura: **no se ha modificado ningún archivo.**

---

## 1. Código muerto de alta confianza (vulture ≥90 %)

Los más fiables y de menor riesgo. 6 hallazgos:

| Archivo | Línea | Hallazgo |
|---|---|---|
| `core/llm/claude_code.py` | 563 | variable sin usar `tool_choice` (100 %) |
| `core/llm/claude_code.py` | 573 | variable sin usar `include_raw` (100 %) |
| `services/pdf_reports/agent_report.py` | 992 | variable sin usar `rel` (100 %) |
| `workers/celery_tasks.py` | 30 | variable sin usar `einfo` (100 %) |
| `services/accounting/libros_pdf.py` | 28 | import sin usar `landscape` (90 %) |
| `services/aeat/certificate_storage.py` | 62 | import sin usar `load_der_x509_certificate` (90 %) |

**Propuesta:** eliminar los 6. (A confianza ≥60 % hay cientos más, con muchos falsos
positivos: requieren revisión manual, no se tocan automáticamente.)

---

## 2. Ruff — imports sin usar y desordenados (auto-corregibles)

`ruff check` detecta **25 incidencias, 20 auto-corregibles** con `--fix`:

- **14 × I001** (bloques de imports desordenados) — reordenado, 100 % seguro.
- **11 × F401** (imports sin usar). De estos, ~6 son auto-seguros y ~5 conviene
  mirarlos a mano (ver nota).

F401 destacados:

```
agents/orchestrator/dispatchers/misc.py   get_registry
services/aeat/expediente_303.py           Casilla303
services/aeat/preventive_check.py         Client
services/collections/reminders.py         field
services/treasury/projection.py           Decimal
services/aeat/certificate_storage.py      base64
--- revisar a mano (posible "import de disponibilidad") ---
services/accounting/libros_pdf.py         TA_CENTER, TA_RIGHT, landscape, PageBreak
services/aeat/certificate_storage.py      load_der_x509_certificate
```

> Nota: ruff marca los de `reportlab`/`cryptography` como NO auto-corregibles porque
> a veces se importan solo para comprobar que la librería está disponible. Antes de
> borrarlos hay que confirmar que no cumplen esa función.

**Propuesta:** aplicar `ruff check --fix` (I001 + F401 seguros) y `ruff format` cuando
el árbol esté limpio. Revisar a mano los 5 de reportlab/cryptography.

---

## 3. Archivos potencialmente huérfanos

### Frontend (`frontend/src`) — candidatos limpios (10 de 477)
```
src/__probe.ts                  ← parece archivo de prueba temporal (candidato a borrar)
src/components/ui/sheet.tsx      ← componente UI sin usar
src/components/ui/tooltip.tsx    ← componente UI sin usar
src/components/Workflows/NodeStatusBadge.tsx
src/components/ai/AIGenerationFooter.tsx
src/lib/utils/error.ts
src/i18n/request.ts              ← posible carga por convención (revisar)
src/test-utils/*, src/test/a11y/setup.ts   ← infra de tests (NO borrar)
```
**Propuesta:** `__probe.ts` y los componentes UI sin usar son candidatos claros;
el resto, revisar antes de tocar.

### Backend — ⚠️ alta tasa de falsos positivos
La heurística marca **41** módulos sin imports estáticos, pero muchos son `__init__.py`
o se cargan de forma dinámica/condicional (dispatchers, servicios usados solo por
agentes o por tests). Ejemplos a revisar **con cuidado**, no borrar a ciegas:
```
services/billing/invoice.py, services/billing/recurring.py, services/billing/metering.py
services/crm/service.py, services/hr/documents.py, services/hr/recruitment.py
services/ai/node_engine_nodes.py, services/ai/stream_tokens.py
```
**Propuesta:** revisar uno a uno con búsqueda de uso real (incl. tests y dispatch
dinámico) antes de considerar eliminarlos.

---

## 4. Acoplamiento y archivos grandes

### Módulos más dependidos (núcleo — tocar con cuidado)
```
in=124  app.db.base
in=109  app.db.models.models     ← un solo módulo importado por 109 sitios
in= 57  app.core.dependencies
in= 42  app.core.config
```
`db.models.models` con 109 dependientes es un punto único de acoplamiento.
**Propuesta:** evaluar dividirlo por dominio de forma incremental y con tests.

### Archivos > 700 líneas (candidatos a trocear por responsabilidad)
```
1010  services/pdf_reports/agent_report.py
 822  services/sales/commands.py
 784  services/reports/modelos_aeat.py
 770  api/v1/routes/hr.py
 718  services/analytics/dashboard.py
 700  agents/orchestrator/classifier.py
```
**Propuesta:** empezar por `agent_report.py` (el mayor).

---

## 5. Frontend lint

`eslint src` se ejecutó **sin incidencias reportadas**.

---

## Resumen y prioridades

| Prioridad | Acción | Riesgo | Estado |
|---|---|---|---|
| 🟢 | `ruff --fix` (14 I001 + ~6 F401 seguros) + 6 muertos de vulture | Bajo | Pendiente (árbol sucio) |
| 🟡 | Revisar 5 F401 de reportlab/cryptography | — | Manual |
| 🟡 | Borrar `__probe.ts` + 2 componentes UI sin usar (frontend) | Bajo | Manual/revisar |
| 🟡 | Revisar huérfanos backend (carga dinámica) | — | Manual |
| 🟠 | Dividir `db.models.models` por dominio | Alto | Planificar |
| 🟠 | Trocear archivos > 700 líneas | Medio | Planificar |

**Nada de esto se ha aplicado.** Para que aplique los arreglos de bajo riesgo
automáticamente: deja el árbol limpio (commit/stash de los 49 cambios pendientes) y
relanza la limpieza.
