# Inbox /forja (run-2, híbrido) — collections / reclamación de impagos (2026-06-26, lente correctitud)

Flujo: `services/collections/risk.py` (scoring de riesgo) + `reminders.py` (recordatorios vencidos). FIX #1
(`draft` fuera de `_UNPAID_STATUSES`) ya hecho → PR #56. Quedan tres (tocan semántica del scoring / legal):

## Media — `updated_at` como proxy de fecha de cobro infla `days_avg_to_pay`
3. **`risk.py:101` `pay_proxy = inv.updated_at or inv.created_at or inv.date`** — `updated_at` cambia en
   CUALQUIER edición (corrección de línea, nota). Una factura cobrada hace 60 días pero editada hoy da
   `updated_at = hoy` → `delta` inflado → `days_avg_to_pay` sube → +15 pts de riesgo (guard `days_avg > 45`).
   Caso: emitida hace 30d, cobrada hace 25d, editada hoy → delta 30 en vez de 5. El propio comentario lo
   reconoce ("proxy"). Fix: si existe un campo `payment_date`/`paid_at` en el modelo, usarlo primero; si no,
   crearlo y setearlo al marcar pagada. Toca semántica del scoring → revisión humana.

## Baja — ranking "a quién perseguir" incluye clientes sin nada vencido
4. **`risk.py:213` `scores = [s for s in scores if s.unpaid_count > 0]`** — `unpaid_count` incluye facturas
   `sent`/`pending` aún EN PLAZO. El propósito del filtro es "a quién perseguir", pero devuelve clientes con
   5 facturas dentro de plazo y 0 vencidas (score 0, low), diluyendo la señal. Fix objetivo: usar
   `s.overdue_count > 0` (o exponer ambos filtros). Cambia qué clientes salen en el ranking → tu criterio.

## Baja (legal) — interés sobre 30 días fijos si el cron se retrasa
2. **`reminders.py:156` `days_overdue` del `ReminderStep` = días hasta la `fire_date` PLANIFICADA, no hasta
   `today`** — para `formal_d30` el interés se calcula sobre 30 días fijos. Si el job no corre el día D+30
   exacto (festivo, reintento) sino D+45, el template dice "lleva 30 días vencida" cuando son más → interés
   comunicado subestimado. Internamente consistente, impreciso solo con retraso del cron. Área legal →
   revisión humana (decidir si el interés se calcula sobre `today` real en el momento del envío).
