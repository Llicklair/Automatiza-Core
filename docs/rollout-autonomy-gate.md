# Rollout del autonomy gate a las acciones consecuentes

**Objetivo:** que "preguntar antes de actuar" funcione igual en **tareas
interactivas** y en **automatizaciones** (sin nadie delante). El mecanismo ya
existe: la política de autonomía por dominio (`services/autonomy.py`) + la cola
`PendingApproval` con ejecutores registrados (`services/workflow/approval_actions.py`).

En **CONFIRM**, la acción se encola y se ejecuta al aprobarla — por eso vale para
ambos contextos. En **AUTO** se ejecuta directa (automatización pre-autorizada).
En **MANUAL** solo se sugiere.

## Patrón de referencia (ya aplicado: agente de stock)

1. **Ejecutor registrado** en `approval_actions.py` (la capa de servicios NO
   importa agentes; importa el *service* correspondiente):

   ```python
   @register_action("inventory_batch_adjust")
   async def _exec_inventory_batch_adjust(params, db, tenant_id):
       from app.services.inventory import batch_service
       res = await batch_service.batch_adjust_stock(db, uuid.UUID(tenant_id),
               params["items"], op=params["op"], reason=params.get("reason",""), dry_run=False)
       return True, f"...{res['applied']} aplicados."
   ```

2. **Gate en la tool** (consulta la política, encola en CONFIRM):

   ```python
   mode = await check_autonomy(db, tenant_id=tid, domain="inventory")
   # MANUAL → sugerir ; CONFIRM → create_action_approval(kind=..., params=..., summary=preview)
   # AUTO   → ejecutar la escritura real
   ```

   `create_action_approval` toma el `task_id` del ContextVar, así que en una
   automatización la aprobación queda enlazada sin trabajo extra.

Defaults ya fijados en `services/autonomy.py` (CONFIRM): `email`, `documents`,
`inventory` (+ los previos: `accounting`, `marketing`, `recruitment`,
`banking_write`=MANUAL).

---

## Pendiente de aplicar (mismo patrón)

### 1. email.send_email (dominio `email`) — PRIORIDAD ALTA
Acción irreversible. Hoy `send_email` (demo) y `send_email_real`
(`agents/email/_provider_tools.py`) envían sin consultar el gate.
- **Ejecutor**: `@register_action("send_email")` → re-resolver proveedores
  (`get_oauth_token` / `get_email_credentials`, como en `agents/email/agent.py`)
  y enviar. Conviene extraer un `resolve_email_providers(tenant_id)` y un
  `perform_email_send(...)` reutilizables por la tool y el ejecutor.
- **Gate**: al inicio del envío, `check_autonomy(domain="email")`; en CONFIRM,
  `create_action_approval(kind="send_email", params={to,subject,body,attachment_ids})`
  y devolver "correo en la bandeja de aprobaciones".
- **Test**: CONFIRM encola y no envía; AUTO envía; payload del borrador correcto.

### 2. documents.import_invoice_document (dominio `documents`) — PRIORIDAD ALTA
Cierra el flujo factura-de-compra→stock que falta.
- Quitar el `draft["apply_stock"] = False` fijo; pasar a un parámetro
  `apply_stock: bool` de la tool.
- **Gate**: `check_autonomy(domain="documents")`. En CONFIRM, previsualizar los
  datos OCR (proveedor, nº, fecha, base/IVA/total, líneas) y encolar
  `kind="import_received_invoice"` con `params={document_id, apply_stock}`.
- **Ejecutor**: `@register_action("import_received_invoice")` → `extract_invoice_data`
  + `import_received_invoices(..., draft con apply_stock elegido)`.
- **Conversacional**: cuando la confianza del OCR sea baja o falten campos clave
  (NIF, total), el resumen del CONFIRM es el sitio para listar lo dudoso y pedir
  corrección antes de persistir.

### 3. hr.generate_all_payrolls (dominio `hr`) — MEDIA
Escritura masiva. `hr` tiene default AUTO; la nómina individual ya usa approval.
- Gatear `generate_all_payrolls` con `check_autonomy(domain="hr")` y, en CONFIRM,
  encolar `kind="generate_all_payrolls"` con `params={month, year}` mostrando nº
  de nóminas y total estimado en el `summary`.
- **Ejecutor**: `@register_action("generate_all_payrolls")`.
- Nota: el gate es por dominio; si no se quiere gatear TODO hr, mantener el gate
  a nivel de esta tool concreta (consultar el modo pero solo encolar aquí).

### 4. excel.import_excel / modify_excel — MEDIA
No hay dominio `excel` en `KNOWN_DOMAINS`. Opciones: (a) añadir dominio `excel`,
o (b) gatear contra el dominio del dato que escribe (p. ej. `billing`/`crm`).
Recomendado (a) por claridad. Previsualizar qué se crea/actualiza en el ERP antes
de aplicar.

### 5. billing.send_invoice_by_email / update_invoice_status(anular) — MEDIA
`billing` ya usa approval por umbral de importe; extender el mismo `create_action_approval`
a estas dos acciones (envío y anulación) con sus ejecutores.

---

## Checklist por acción
- [ ] Dominio correcto en `KNOWN_DOMAINS` (+ default en `DEFAULTS` si procede).
- [ ] Ejecutor `@register_action("<kind>")` en `approval_actions.py` (importa el service, no el agente).
- [ ] Gate en la tool: `check_autonomy` → MANUAL/CONFIRM/AUTO.
- [ ] `summary` legible (es lo que el humano ve en la bandeja).
- [ ] Tests: CONFIRM encola sin ejecutar · AUTO ejecuta · MANUAL sugiere.
- [ ] `params` JSON-serializable (el ejecutor los relee tal cual).
