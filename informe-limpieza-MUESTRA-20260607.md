# Informe de limpieza de código — MUESTRA

**Proyecto:** AutomatizaPyme · **Fecha:** 2026-06-07
**Alcance:** backend Python (`backend/app`) + frontend TS (`frontend/src`)
**Naturaleza:** solo análisis (lectura). No se ha modificado ningún archivo.

> Este es un ejemplo de lo que recibirías cada día. Cada punto es una *propuesta*: tú decides qué aplicar.

---

## 1. Código muerto (alta confianza) — backend

Detectado con `vulture` a confianza ≥90 %. Son los hallazgos más fiables y de menor riesgo.

| Archivo | Línea | Hallazgo |
|---|---|---|
| `core/llm/claude_code.py` | 563 | variable sin usar `tool_choice` (100 %) |
| `core/llm/claude_code.py` | 573 | variable sin usar `include_raw` (100 %) |
| `services/pdf_reports/agent_report.py` | 992 | variable sin usar `rel` (100 %) |
| `workers/celery_tasks.py` | 30 | variable sin usar `einfo` (100 %) |
| `services/accounting/libros_pdf.py` | 28 | import sin usar `landscape` (90 %) |
| `services/aeat/certificate_storage.py` | 62 | import sin usar `load_der_x509_certificate` (90 %) |

**Propuesta:** eliminar estos 6. Bajo riesgo. (A confianza ≥60 % hay 701 candidatos más, pero con muchos falsos positivos: requieren revisión manual y por eso no se tocan.)

---

## 2. Archivos potencialmente huérfanos

### Backend — ⚠️ revisar con cuidado
La heurística marca **91** módulos sin imports estáticos, pero **casi todos los de `agents/*` (`agent.py`, `tools.py`, `prompts.py`) probablemente se cargan dinámicamente** vía un registro (`tool_registry`). **No son huérfanos reales.** Esto ilustra por qué la rutina propone y no borra: un borrado automático aquí rompería los agentes.

**Propuesta:** confirmar cómo se registran los agentes y, una vez claro, filtrar ese patrón para que el informe solo señale huérfanos verdaderos.

### Frontend — candidatos más limpios (10)
```
src/__probe.ts                              ← parece archivo de prueba temporal
src/components/Workflows/NodeStatusBadge.tsx
src/components/ai/AIGenerationFooter.tsx
src/components/ui/sheet.tsx                  ← componente UI sin usar
src/components/ui/tooltip.tsx               ← componente UI sin usar
src/lib/utils/error.ts
src/i18n/request.ts                         ← posible carga por convención (revisar)
src/test-utils/*, src/test/a11y/setup.ts    ← infra de tests (NO borrar)
```
**Propuesta:** `__probe.ts` y los componentes UI sin usar son candidatos claros a eliminar; el resto, revisar.

---

## 3. Acoplamiento y modularización

### Módulos más dependidos (núcleo — tocar con cuidado)
```
in=124  app.db.base
in=109  app.db.models.models      ← un solo archivo importado por 109 sitios
in= 57  app.core.dependencies
in= 42  app.core.config
```
`db.models.models` con 109 dependientes es un punto único de acoplamiento. **Propuesta:** evaluar dividir `models.models` en módulos por dominio (billing, hr, auth…) — alto impacto, hacer de forma incremental y con tests.

### Archivos grandes / con muchas dependencias (candidatos a dividir)
```
1010 líneas  services/pdf_reports/agent_report.py
 822 líneas  services/sales/commands.py
 784 líneas  services/reports/modelos_aeat.py
 770 líneas  api/v1/routes/hr.py
out=20       agents/tool_registry
out=17       agents/documents/tools
```
**Propuesta:** los archivos >700 líneas son candidatos a trocear por responsabilidad. Empezar por `agent_report.py` (el mayor).

---

## Resumen y prioridades

| Prioridad | Acción | Riesgo |
|---|---|---|
| 🟢 Ya | Eliminar los 6 hallazgos de código muerto (sección 1) | Bajo |
| 🟢 Ya | Eliminar `__probe.ts` + UI sin usar | Bajo |
| 🟡 Revisar | Confirmar carga dinámica de agentes para afinar huérfanos | — |
| 🟠 Planificar | Dividir `models.models` por dominio | Alto |
| 🟠 Planificar | Trocear archivos >700 líneas | Medio |

**Nada de esto se ha aplicado.** Dime qué puntos quieres que ejecute (con los cambios revisables, y pasando tests antes de cerrar).
