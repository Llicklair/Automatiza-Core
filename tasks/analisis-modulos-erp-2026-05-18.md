# Análisis funcional de módulos ERP — 2026-05-18

**Versión 2** — auditoría profunda de los 38 módulos del dashboard, cruzando frontend (LoC, llamadas API, subpáginas) con backend (endpoints por route file).

---

## TL;DR

- El ERP está **mucho más completo de lo que parece a primera vista**. La sensación de "incompleto" viene de **3-4 módulos visibles** que son cara pública: Correos, Marketing, Calendario, TPV.
- Los **3 stubs de 5 LoC** (`actividades`, `aprobaciones`, `tareas`) **NO están incompletos**: son redirects intencionados a `/bandeja` y `/mi-equipo`. Considera quitarlos del sidebar para reducir ruido.
- Hueco mayor real único: **Email marketing** (0% implementado). Lo demás son huecos puntuales subsanables en 1-3 días cada uno.
- **Sandbox** → retirar (5 ficheros, ~45 min).
- **Plugin system** → descartar confirmado.

---

## 1. Matriz de madurez por módulo

Estado: ✅ completo · 🟡 hueco puntual · 🔴 hueco grande · ⚪ redirect · ❌ retirar

### ERP core (operaciones)

| Módulo | Estado | Hueco detectado | Esfuerzo fix |
|---|---|---|---|
| **ventas** (facturas, pedidos, presupuestos, facturación electrónica) | ✅ | — | — |
| **compras** (facturas recibidas, pedidos, proveedores) | ✅ | — | — |
| **inventario** (stock, scanner, valuación) | ✅ | — | — |
| **albaranes** | ✅ | — | — |
| **catalogo** (productos) | ✅ | — | — |
| **clientes** + ficha `[id]` | ✅ | Cambios sin commitear en `clientes/portal/page.tsx` — revisar antes | — |
| **crm** (actividades, calendario, embudo, reservas, reuniones) | ✅ | — | — |
| **proyectos** (kanban, tareas, mis-tareas) | ✅ | — | — |
| **tpv** | 🟡 | Sin **devoluciones**, sin **cierre Z/X**, sin **descuento por línea**, sin **factura nominativa** (siempre simplificada), sin gestión multi-caja | 3-5 días |

### Finanzas y fiscal

| Módulo | Estado | Hueco | Esfuerzo |
|---|---|---|---|
| **contabilidad** (activos, asesorías, balance, cuadro, libro diario, P&G) | ✅ | — | — |
| **banca** (resumen, conciliación, transacciones, saldos) | ✅ | — | — |
| **tesoreria** (cashflow, pagos-y-cobros, remesas SEPA) | ✅ | — | — |
| **impuestos** (asistida, modelos AEAT, calendario, libro registro) | ✅ | — | — |
| **compliance** (BOE, calendario, consulta IA) | ✅ | — | — |
| **informes** (fiscal + gestión + snapshot) | ✅ | — | — |
| **modelos_aeat** (backend) | ✅ | — | — |
| **presentacion_asistida** | ✅ | — | — |

### Personas

| Módulo | Estado | Hueco | Esfuerzo |
|---|---|---|---|
| **rrhh** (empleados, fichajes, gastos, horarios, nóminas, docs, análisis-CV) | ✅ | — | — |
| **mi-equipo** (empleados IA + chat coordinador) | ✅ | — | — |
| **portal (empleado)** | 🟡 | Falta: ver **contratos propios**, ver **horario propio**, **mensajes con admin**, **firma recibos**. Hoy: clock-in/out, vacaciones, gastos, nóminas | 2-3 días |
| **clientes/portal** (cliente externo) | 🟡 | Hoy solo lista/descarga facturas. Falta: **ver presupuestos**, **aceptar/rechazar online**, **pagar online**, **mensajería** | 3-5 días |
| **bienvenida** (wizard 4 pasos) | ✅ | Duplica intencionalmente algo de `/primeros-pasos`. Aclarar en sidebar cuál es cuál o fusionar | 0.5 día UX |
| **primeros-pasos** (checklist largo) | ✅ | Ver arriba | — |

### Comunicación y contenidos

| Módulo | Estado | Hueco | Esfuerzo |
|---|---|---|---|
| **correos** | 🟡 | Drive picker SÍ está implementado en código. Si el usuario no lo ve, es por OAuth Gmail no conectado (devuelve 400) → mejorar mensaje de error y CTA "Conectar Gmail". También falta **búsqueda en bandeja**, **etiquetas**, **threading visual** | 1-2 días |
| **marketing** | 🔴 | Solo genera plan de redes (Instagram/Facebook/LinkedIn). Sin **publicación real**, sin **calendario editorial persistido**, sin **email marketing**, sin métricas | 1-2 semanas |
| **plantillas** (de documentos: factura, nómina, contrato) | ✅ | Editor visual completo + ContratosTab. Verificar manualmente que el preview PDF funciona end-to-end | smoke test |
| **documentos** | ✅ | Funcional. Posible mejora: **vista previa inline** de PDFs sin descargar | nice-to-have |
| **escaner** (OCR + clasificación IA) | ✅ | Sin histórico persistente en la vista (los resultados se pierden al recargar) | 1 día |
| **excel** | 🟡 | **Nombre engañoso**: solo importa hojas como "documentos categoría excel". No edita, no visualiza datos extraídos como tabla, no exporta. Renombrar a "Importar Excel" o ampliar con visor de hojas | 0.5 día rename ó 1 semana visor |
| **calendario** | 🟡 | **Bug**: backend `/calendar/unified` agrega Events + Reservas + (probable) vencimientos. Frontend solo llama `api.crm.events` → se pierden vencimientos AEAT, facturas, nóminas. Cambiar a `api.calendar.unified` | 0.5 día |

### Plataforma

| Módulo | Estado | Hueco | Esfuerzo |
|---|---|---|---|
| **configuracion** (empresa, idioma, autonomía, backups, firma, integraciones, api-keys, regap, actualizaciones, mantenimiento) | ✅ | 26 archivos, todo presente | — |
| **integraciones** (PSD2, Gmail, Outlook, Drive, OneDrive, Telegram) | ✅ | — | — |
| **automatizaciones** (workflows con scheduler) | ✅ | — | — |
| **bandeja** (aprobaciones + actividad + inbox unificado) | ✅ | — | — |
| **alertas** | 🟡 | Solo visor + botón "check ahora". Sin **CRUD de reglas custom** (todo hard-coded en backend). Decisión: ¿basta con reglas predefinidas? | 1 semana si se quiere custom |
| **auditoria** | ✅ | Visor pasivo está bien. Falta **export CSV** y **filtros por fecha/agente/status** | 1 día |
| **analitica** | ✅ | 811 LoC frontend, 1 endpoint backend agregador → correcto. Verificar drill-down a sub-páginas | smoke test |

### Stubs / a retirar

| Módulo | Estado | Acción |
|---|---|---|
| **actividades** | ⚪ | Redirect → `/bandeja?tab=actividad`. Quitar del sidebar (ya está en bandeja) |
| **aprobaciones** | ⚪ | Redirect → `/bandeja?tab=aprobaciones`. Quitar del sidebar |
| **tareas** | ⚪ | Redirect → `/mi-equipo?tab=tareas`. Quitar del sidebar |
| **sandbox** | ❌ | Retirar. 5 ficheros + 2 referencias + ruta `generative_ui.py` |

### Búsqueda global

| Módulo | Estado | Hueco | Esfuerzo |
|---|---|---|---|
| `/search` (backend) | 🟡 | Endpoint existe (empleados/clientes/facturas), pero **no hay UI de búsqueda global** en el sidebar/topbar. Implementar `Cmd+K` palette | 1-2 días |

---

## 2. Huecos transversales (no de un módulo concreto)

### A. Acciones de exportar/imprimir
Muchas tablas no tienen botón **Exportar CSV** (auditoría, transacciones banca, gastos, nóminas históricas). Patrón: añadir un helper `exportToCSV(data, filename)` reutilizable.

### B. Mutaciones HTTP en cliente
El grep `method: ["POST/PUT/PATCH/DELETE"]` devolvió 0 en todos los módulos. Es **correcto**: las mutaciones van por `request(url, { method })` envuelto en `lib/api/client.ts`. No es un bug, solo aclaración para el audit.

### C. Bandeja unificada
Bandeja ya absorbió actividad + aprobaciones + inbox. Verificar que el sidebar no muestre duplicados.

### D. Calendario unificado roto
Backend lo sirve, frontend no lo consume. Fix de 30 min — alto impacto UX.

---

## 3. Plan de acción priorizado

### Sprint 1 — quick wins (3 días)
1. **Quitar del sidebar**: `actividades`, `aprobaciones`, `tareas`, `sandbox`
2. **Fix calendario**: cambiar `api.crm.events` → `api.calendar.unified` (incluir vencimientos AEAT/facturas/nóminas en la vista)
3. **Mejorar mensaje "Drive no conectado"** en correos: CTA directo a conectar Gmail
4. **Renombrar Excel → "Importar Excel"** o decidir si se amplía
5. **Retirar sandbox completo** (frontend + backend + nav-config)
6. **Aclarar Bienvenida vs Primeros-pasos** en sidebar (o fusionar)

### Sprint 2 — TPV completo (3-5 días)
7. Devoluciones (refund) en TPV
8. Cierre Z / reporte X de caja
9. Descuentos por línea y por ticket
10. Asociar cliente al ticket → factura nominativa

### Sprint 3 — Email marketing MVP (1-2 semanas) — LA PIEZA GRANDE
11. Modelos: `EmailCampaign`, `EmailAudience`, `EmailSend`
12. Endpoints: `/email/campaigns` CRUD + `/send` + `/stats`
13. Worker batch con throttling por proveedor (Gmail límite ~500/día)
14. Tracking pixel + redirector clicks + unsubscribe (RGPD)
15. UI: nueva pestaña en `/correos` o nuevo submenú en `/marketing`

### Sprint 4 — Portales (5-7 días)
16. Portal empleado: contratos propios, horario, mensajería, firma recibos
17. Portal cliente: aceptar presupuestos online + pagar online + mensajería

### Sprint 5 — pulido (variable)
18. Búsqueda global Cmd+K
19. Exportar CSV en tablas clave
20. Histórico escáner persistido
21. Filtros + export en auditoría

---

## 4. Sobre el plugin system (decisión confirmada)

Descartarlo es correcto. Tu motor `services/workflow/` (parse-NL → workflow + scheduler) cubre el 90% de los casos de extensión sin la complejidad de:

- Sandbox de ejecución multi-tenant (Firecracker/gVisor — infra cara)
- Política RLS y scopes OAuth por plugin
- Backwards-compat eterna de la API interna

Si un usuario quiere "extender", diseña un workflow. Si quiere integrar un SaaS X, se añade conector revisado en `backend/app/integrations/`.

---

## 5. Preguntas pendientes para desbloquear sprint 3

1. **Email marketing — proveedor de envío**: ¿SMTP propio (relay) o usar Gmail/Outlook del usuario? Lo segundo: rápido pero techo ~500/día; lo primero: 1-2 semanas extra de infra.
2. **Tracking opens/clicks**: ¿aceptable bajo RGPD con consentimiento explícito en footer? Si no, métricas se limitan a entregado/rebotado.
3. **Marketing + Email**: ¿unificar en `/marketing` con tabs (Redes / Email / Calendario editorial) o dejar Email en `/correos` con tab "Campañas"?
4. **Stubs en sidebar**: ¿confirmas que quito `actividades`, `aprobaciones`, `tareas` del menú (siguen accesibles vía bandeja/mi-equipo)?
5. **Bienvenida vs primeros-pasos**: ¿fusionamos en uno o aclaramos copy?
