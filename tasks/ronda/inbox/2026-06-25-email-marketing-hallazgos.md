# Inbox /forja — hallazgos en services/email_marketing (2026-06-25, barrido #3)

El loop NO auto-arregló nada aquí: los defectos altos son de concurrencia en la ruta de
ENVÍO de emails a clientes → demasiado riesgo para auto-fix, necesitan tu diseño.

## ALTA prioridad (bugs reales, fix necesita decisión humana)
1. **`sender.py:36-44` doble-envío por TOCTOU** [alta]. `send_campaign` hace read-check-write
   sin lock: el botón /send y el scheduler APScheduler pueden disparar a la vez, ambos leen
   `status="draft"`, ambos pasan la guardia y envían → **cada cliente recibe el email dos veces**.
   Fix propuesto: claim atómico — `UPDATE email_campaigns SET status='sending' WHERE id=:id
   AND tenant_id=:t AND status IN ('draft','scheduled') RETURNING id`; solo envía quien obtiene fila.

2. **`sender.py:46-87` campaña atascada permanente en "sending"** [alta]. Los destinatarios se
   marcan en memoria y se commitea SOLO al final (línea ~87). Si el proceso cae a media tanda:
   los enviados por SMTP no quedan registrados, la campaña queda `"sending"` para siempre y la
   guardia de la línea 40 impide cualquier reintento. Fix propuesto: commit incremental por
   destinatario (o por lotes) + recuperación de campañas "sending" colgadas con heartbeat/TTL.

## Menores (opinables / semántica)
3. **`campaigns.py:54+68` inserción no paginada** [media]: `list_recipients` carga todos los
   `Client` en memoria y mete 1 fila por cliente en una transacción. Tenant con decenas de
   miles → OOM/timeout. Fix: `bulk_insert_mappings` o `INSERT ... SELECT`.
4. **`campaigns.py:95-97` no se puede desprogramar** [baja]: con `scheduled_at=None` la guardia
   lo ignora → no se puede volver de "scheduled" a "draft". Decisión de semántica de API.
5. **`delete_template` / `delete_campaign` cascade** [baja]: comprobar si el FK tiene cascade;
   si no, deja `template_id`/`EmailCampaignRecipient` huérfanos. Verificar el modelo.

## Descartado
- `update_template` "sin guards de None": la ruta usa `TemplateCreate` (campos requeridos) →
  None no es alcanzable vía API. No es bug real.
