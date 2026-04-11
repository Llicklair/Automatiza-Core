# Diagnóstico del Proyecto — 2026-04-10

## Resumen Ejecutivo

Se analizaron backend (33 rutas, 17 agentes, 48 migraciones), frontend (25+ páginas, 25 API modules) y capa de integración (Electron + Desktop). El proyecto tiene una estructura sólida pero hay **3 issues críticos**, **5 altos** y varios medianos que explican los bugs que estás viendo.

---

## CRITICAL — Crashean o rompen funcionalidad core

### 1. Modelos no exportados en `__init__.py`
- **Archivo**: `backend/app/db/models/__init__.py`
- **Problema**: `AIEmployee`, `AgentSkill`, `ActivityEntry`, `TokenLedger` NO están exportados
- **Impacto**: Alembic no descubre estas tablas → no se crean en BD → queries fallan en runtime

### 2. Agente de contabilidad no existe
- **Archivo esperado**: `backend/app/agents/accounting_agent.py` (NO EXISTE)
- **Referenciado en**: `backend/app/api/v1/routes/accounting.py`
- **Impacto**: Cualquier endpoint de contabilidad crashea al invocar el agente

### 3. `datetime.UTC` requiere Python 3.12+
- **Archivo**: `backend/app/api/v1/routes/hr_documents.py` línea 6
- **Problema**: `from datetime import UTC` solo funciona en Python 3.12+, el proyecto usa 3.11
- **Impacto**: Import error al cargar el módulo de documentos HR

---

## HIGH — Features rotas o degradadas

### 4. 13 páginas no accesibles desde la navegación
- **Archivo**: `frontend/src/components/layout/nav-config.ts`
- **Páginas ocultas**: `/compliance`, `/configuracion/actualizaciones`, `/configuracion/api-keys`, `/configuracion/empresa`, `/configuracion/perfil`, `/proyectos/mis-tareas`, `/proyectos/proyectos`, `/clientes/[id]`, `/ventas/facturas/[id]`, `/ventas/facturas/nueva`, y 3 redirects (`/actividades`, `/aprobaciones`, `/tareas`)
- **Impacto**: Usuarios no pueden llegar a estas páginas desde el sidebar

### 5. Puerto de BD desalineado en `.env.example`
- **Archivo**: `backend/.env.example` (dice `5432`)
- **Real**: `config.py` y `postgres-manager.js` usan `5433`
- **Impacto**: Nuevas instalaciones o resets de `.env` conectan al puerto equivocado

### 6. Uso masivo de `any` en TypeScript
- **Archivos afectados**: `albaranes/page.tsx`, `analitica/page.tsx`, `automatizaciones/page.tsx` (8+ usos cada uno)
- **Impacto**: Sin type-safety → bugs silenciosos en runtime, errores difíciles de rastrear

### 7. Tool Registry no maneja accounting agent
- **Archivo**: `backend/app/agents/tool_registry.py` líneas 20-80
- **Impacto**: `call_tool()` crashea si se invocan herramientas de contabilidad

### 8. Dual registry system (tools vs skills)
- **Archivos**: `backend/app/agents/tool_registry.py` vs `backend/app/skills/registry.py`
- **Impacto**: Dos sistemas de registro paralelos que pueden divergir → comportamiento inconsistente

---

## MEDIUM — Incompleto o riesgo latente

### 9. React hooks con dependencias faltantes (5 archivos)
| Archivo | Dependencias faltantes |
|---------|----------------------|
| `compras/facturas/page.tsx` | `handleDeleteInvoice`, `handleStatusChange` |
| `clientes/page.tsx` | Múltiples hooks |
| `automatizaciones/page.tsx` | `setGuard` |
| `ventas/facturas/[id]/page.tsx` | `t` (i18n) |
| `rrhh/empleados/EmployeeDocsModal.tsx` | useCallback deps |

**Impacto**: Stale closures → datos desactualizados en handlers, re-renders innecesarios

### 10. Página de actualizaciones sin implementar
- **Archivo**: `frontend/src/app/(dashboard)/configuracion/actualizaciones/page.tsx`
- **TODO**: `// TODO: Conectar con VPS de actualizaciones cuando esté disponible`

### 11. Configuración sub-páginas dispersas
- 5 sub-páginas en `/configuracion/` pero solo `/configuracion/integraciones` está en el nav
- **Fix**: Agregar parent item `/configuracion` con todas las sub-rutas

### 12. `TenantLlmConfig` no re-exportado
- **Archivo**: `backend/app/db/models/models.py` línea 33
- **Impacto**: Imports desde `models.py` pueden fallar para este modelo

---

## LOW — Calidad de código

- Import styles inconsistentes en rutas (some `from models import models`, others specific imports)
- `backend/app/services/__init__.py` vacío (services no descubribles)
- Windows CRLF/LF warnings en 6 archivos modificados
- `erp.py` route es solo re-export sin documentación

---

## VERIFICADO OK

- **Electron/Desktop**: main.js, managers, preload — todo correcto
- **Contrato API backend-frontend**: Endpoints alineados (invoices, clients, employees, HR docs)
- **Migraciones Alembic**: 48 migraciones encadenadas correctamente
- **Auth**: JWT + RBAC implementado
- **Middleware**: CORS, rate limiting, security headers
- **Zustand stores**: 4 stores correctamente implementados
- **API clients frontend**: 25 módulos con barrel export funcional

---

## Plan de acción recomendado (por prioridad)

| # | Acción | Severidad | Esfuerzo |
|---|--------|-----------|----------|
| 1 | Exportar modelos faltantes en `models/__init__.py` | CRITICAL | 5 min |
| 2 | Fix `datetime.UTC` → `timezone.utc` en `hr_documents.py` | CRITICAL | 2 min |
| 3 | Crear `accounting_agent.py` o stub + registrar en tool_registry | CRITICAL | 30 min |
| 4 | Agregar páginas faltantes a `nav-config.ts` | HIGH | 15 min |
| 5 | Corregir puerto en `.env.example` (5432→5433) | HIGH | 1 min |
| 6 | Agregar dependencias faltantes en useEffect/useCallback (5 archivos) | MEDIUM | 20 min |
| 7 | Reemplazar `any` por tipos propios en páginas afectadas | HIGH | 45 min |
| 8 | Unificar tool_registry y skill_registry | MEDIUM | 1-2 hrs |
| 9 | Re-exportar `TenantLlmConfig` en models.py | MEDIUM | 2 min |
