"""Heartbeat Service — Ciclo vital de los AIEmployee.

Cada empleado activo tiene un cron job que:
1. Comprueba presupuesto mensual (budget_guard); si se agota, pausa y cancela heartbeat.
2. Revisa tareas `pending` del mismo dominio y tenant.
3. Reclama cada tarea con UPDATE atómico (pending → executing) y despacha al orquestador.
4. Actualiza estado visual (idle → working → idle) y escribe activity_feed.

El despacho usa el mismo `dispatch_orchestrator` que POST /tasks; TaskRunner evita
duplicados si la tarea ya está en vuelo. La reclamación en BD evita dos empleados
del mismo dominio ejecutando la misma tarea.

Registro dinámico: los jobs se crean/cancelan cuando el usuario
crea o pausa empleados en tiempo de ejecución.
"""

import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update

from app.db.base import AsyncSessionLocal
from app.services.agent_budget import get_budget_status
from app.db.models.ai_employees import ActivityEntry, AIEmployee
from app.db.models.tasks import Task

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 300  # 5 minutos
HEARTBEAT_MAX_DISPATCH_PER_CYCLE = 5  # evita inundar el TaskRunner en un solo tick

# Dedupe en memoria del aviso blando de presupuesto (80%): el heartbeat corre
# cada 5 min, así que sin esto el toast saltaría en cada tick. Se resetea al
# pausar/reactivar el empleado (el set se limpia en (un)register).
_budget_warned: set[str] = set()


async def _ws_notify_budget(tenant_id: str, employee_id: str, event_type: str, budget: dict) -> None:
    """Empuja un evento de presupuesto al canal WS del tenant (best-effort)."""
    try:
        from app.api.ws.notifications import manager

        await manager.broadcast_to_tenant(
            str(tenant_id),
            {
                "type": event_type,
                "employee_id": str(employee_id),
                "employee_name": budget.get("name"),
                "spend_usd": round(budget.get("spend_usd") or 0, 2),
                "limit_usd": budget.get("limit_usd"),
                "ratio": round(budget.get("ratio") or 0, 2),
            },
        )
    except Exception as exc:
        logger.debug("WS budget notify falló (silenciado): %s", exc)


def get_scheduler():
    from app.services.scheduler import scheduler

    return scheduler


# ─── Registro / Cancelación de Jobs ──────────────────────────────────────────


def register_employee_heartbeat(employee_id: str, tenant_id: str) -> None:
    """Registra o reemplaza el cron job de heartbeat para un empleado.
    Idempotente: elimina el job previo si existía.
    """
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler = get_scheduler()
    job_id = f"heartbeat_{employee_id}"

    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        func=run_employee_heartbeat,
        trigger=IntervalTrigger(seconds=HEARTBEAT_INTERVAL_SECONDS),
        id=job_id,
        kwargs={"employee_id": employee_id, "tenant_id": tenant_id},
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )
    _budget_warned.discard(employee_id)
    logger.debug("Heartbeat registrado para empleado %s", employee_id)


def unregister_employee_heartbeat(employee_id: str) -> None:
    """Cancela el cron job de heartbeat de un empleado."""
    scheduler = get_scheduler()
    job_id = f"heartbeat_{employee_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.debug("Heartbeat cancelado para empleado %s", employee_id)


# ─── Lógica del Heartbeat ────────────────────────────────────────────────────


async def run_employee_heartbeat(employee_id: str, tenant_id: str) -> None:
    """Ejecuta un ciclo de heartbeat para un empleado.

    Usa su propia sesión DB (corre fuera del contexto de request).
    Falla silenciosamente — nunca debe romper el scheduler.
    """
    tenant_uuid = UUID(tenant_id)
    emp_uuid = UUID(employee_id)
    domain: str | None = None
    employee_name = ""

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AIEmployee).where(
                    AIEmployee.id == emp_uuid,
                    AIEmployee.tenant_id == tenant_uuid,
                )
            )
            employee = result.scalar_one_or_none()
            if not employee or employee.status == "paused":
                unregister_employee_heartbeat(employee_id)
                return

            budget = await get_budget_status(employee_id, db)
            if budget and budget["state"] == "exhausted":
                await db.execute(
                    update(AIEmployee).where(AIEmployee.id == emp_uuid).values(status="paused")
                )
                await db.commit()
                await _ws_notify_budget(tenant_id, employee_id, "budget_exhausted", budget)
                _budget_warned.discard(employee_id)
                unregister_employee_heartbeat(employee_id)
                logger.info("Heartbeat cancelado: presupuesto agotado para %s", employee_id)
                return
            if budget and budget["state"] == "warning" and employee_id not in _budget_warned:
                _budget_warned.add(employee_id)
                await _ws_notify_budget(tenant_id, employee_id, "budget_warning", budget)

            domain = employee.domain
            employee_name = employee.name

            pending_count_result = await db.execute(
                select(func.count()).where(
                    Task.tenant_id == tenant_uuid,
                    Task.domain == domain,
                    Task.status == "pending",
                )
            )
            pending_before = int(pending_count_result.scalar() or 0)

            await db.execute(
                update(AIEmployee).where(AIEmployee.id == emp_uuid).values(status="working")
            )
            await db.commit()

        from app.services.workflow.task_dispatch import dispatch_orchestrator

        dispatched = 0
        for _ in range(HEARTBEAT_MAX_DISPATCH_PER_CYCLE):
            async with AsyncSessionLocal() as db:
                one = await db.execute(
                    select(Task.id)
                    .where(
                        Task.tenant_id == tenant_uuid,
                        Task.domain == domain,
                        Task.status == "pending",
                    )
                    .order_by(Task.created_at.asc())
                    .limit(1)
                )
                row = one.first()
                if not row:
                    break
                tid = row[0]
                upd = await db.execute(
                    update(Task)
                    .where(
                        Task.id == tid,
                        Task.tenant_id == tenant_uuid,
                        Task.domain == domain,
                        Task.status == "pending",
                    )
                    .values(status="executing", started_at=datetime.now(UTC))
                    .returning(Task.id)
                )
                claimed = upd.fetchone()
                if not claimed:
                    await db.rollback()
                    continue
                await db.commit()

            try:
                # Fase 3 (RLS): tenant_uuid es la tenancy de la task reclamada.
                await dispatch_orchestrator(str(tid), tenant_id=str(tenant_uuid))
                dispatched += 1
            except Exception as exc:
                logger.exception("Heartbeat: error despachando tarea %s: %s", tid, exc)
                try:
                    async with AsyncSessionLocal() as dbx:
                        await dbx.execute(
                            update(Task)
                            .where(Task.id == tid)
                            .values(status="pending", started_at=None)
                        )
                        await dbx.commit()
                except Exception:
                    logger.error("No se pudo revertir tarea %s a pending", tid)

        async with AsyncSessionLocal() as db:
            if dispatched > 0:
                message = (
                    f"He puesto en marcha {dispatched} tarea{'s' if dispatched != 1 else ''} "
                    f"pendiente{'s' if dispatched != 1 else ''} en {domain}."
                )
                icon = "🚀"
            elif pending_before > 0:
                message = (
                    f"He revisado mi bandeja: {pending_before} tarea(s) pendiente(s) en {domain} "
                    f"(otras instancias las están procesando o están en cola)."
                )
                icon = "🔍"
            else:
                message = f"He revisado mi bandeja de entrada. Todo al día en {domain}."
                icon = "✅"

            entry = ActivityEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                employee_id=employee_id,
                category=domain or "system",
                icon=icon,
                message=message,
                metadata_json={
                    "pending_tasks_seen": pending_before,
                    "dispatched": dispatched,
                    "heartbeat": True,
                },
            )
            db.add(entry)

            await db.execute(
                update(AIEmployee).where(AIEmployee.id == emp_uuid).values(status="idle")
            )
            await db.commit()
            logger.debug(
                "Heartbeat completado para %s (%s), dispatched=%d",
                employee_name,
                employee_id,
                dispatched,
            )

    except Exception as e:
        logger.error("Heartbeat falló para empleado %s: %s", employee_id, e)
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(AIEmployee).where(AIEmployee.id == emp_uuid).values(status="idle")
                )
                await db.commit()
        except Exception as recovery_err:
            # Recovery del status del empleado falló — quedará en "working" colgado.
            # Health-check pre-dispatch lo bloqueará en próximas invocaciones.
            logger.warning(
                "No se pudo restaurar status='idle' del empleado %s tras fallo de "
                "heartbeat: %s: %s",
                employee_id, type(recovery_err).__name__, recovery_err,
            )


# ─── Bootstrap en Startup ─────────────────────────────────────────────────────


async def bootstrap_employee_heartbeats() -> None:
    """Restaura los heartbeat jobs para todos los empleados activos.

    Se llama una vez en el startup de FastAPI, después de que el
    scheduler ya esté corriendo. Falla silenciosamente por empleado.
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AIEmployee.id, AIEmployee.tenant_id).where(AIEmployee.status != "paused")
            )
            employees = result.all()

        registered = 0
        for emp_id, tenant_id in employees:
            try:
                register_employee_heartbeat(str(emp_id), str(tenant_id))
                registered += 1
            except Exception as e:
                logger.warning("No se pudo registrar heartbeat para %s: %s", emp_id, e)

        logger.info("Bootstrap heartbeats: %d empleados registrados", registered)

    except Exception as e:
        logger.error("Bootstrap heartbeats falló (no es fatal): %s", e)
