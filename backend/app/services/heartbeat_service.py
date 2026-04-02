"""Heartbeat Service — Ciclo vital de los AIEmployee.

Cada empleado activo tiene un cron job que:
1. Revisa su bandeja de entrada (tareas pendientes en su dominio)
2. Actualiza su estado visualmente (idle → working → idle)
3. Escribe una entrada en activity_feed

IMPORTANTE: Este servicio NO ejecuta tareas — eso sigue siendo
responsabilidad del orquestador existente. El heartbeat solo
añade presencia visual y logging de actividad.

Registro dinámico: los jobs se crean/cancelan cuando el usuario
crea o pausa empleados en tiempo de ejecución.
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update

from app.db.base import AsyncSessionLocal
from app.db.models.ai_employees import AIEmployee, ActivityEntry
from app.db.models.tasks import Task

logger = logging.getLogger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 300  # 5 minutos


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
    try:
        async with AsyncSessionLocal() as db:
            # 1. Verificar que el empleado sigue activo
            result = await db.execute(
                select(AIEmployee).where(
                    AIEmployee.id == employee_id,
                    AIEmployee.tenant_id == tenant_id,
                )
            )
            employee = result.scalar_one_or_none()
            if not employee or employee.status == "paused":
                unregister_employee_heartbeat(employee_id)
                return

            # 2. Contar tareas pendientes en su dominio
            pending_count_result = await db.execute(
                select(func.count()).where(
                    Task.tenant_id == tenant_id,
                    Task.domain == employee.domain,
                    Task.status == "pending",
                )
            )
            pending_count = pending_count_result.scalar() or 0

            # 3. Marcar como "working" durante la revisión
            await db.execute(
                update(AIEmployee)
                .where(AIEmployee.id == employee_id)
                .values(status="working")
            )
            await db.commit()

            # 4. Escribir entrada de actividad
            if pending_count > 0:
                message = (
                    f"He revisado mi bandeja de entrada. "
                    f"Tengo {pending_count} tarea{'s' if pending_count != 1 else ''} pendiente{'s' if pending_count != 1 else ''} "
                    f"en el área de {employee.domain}."
                )
                icon = "🔍"
            else:
                message = f"He revisado mi bandeja de entrada. Todo al día en {employee.domain}."
                icon = "✅"

            entry = ActivityEntry(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                employee_id=employee_id,
                category=employee.domain,
                icon=icon,
                message=message,
                metadata_json={"pending_tasks": pending_count, "heartbeat": True},
            )
            db.add(entry)

            # 5. Volver a "idle"
            await db.execute(
                update(AIEmployee)
                .where(AIEmployee.id == employee_id)
                .values(status="idle")
            )
            await db.commit()
            logger.debug("Heartbeat completado para %s (%s)", employee.name, employee_id)

    except Exception as e:
        # Fallo silencioso — nunca debe romper el scheduler ni otros jobs
        logger.error("Heartbeat falló para empleado %s: %s", employee_id, e)
        # Intentar restaurar status a idle en caso de error
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(AIEmployee)
                    .where(AIEmployee.id == employee_id)
                    .values(status="idle")
                )
                await db.commit()
        except Exception:
            pass


# ─── Bootstrap en Startup ─────────────────────────────────────────────────────

async def bootstrap_employee_heartbeats() -> None:
    """Restaura los heartbeat jobs para todos los empleados activos.

    Se llama una vez en el startup de FastAPI, después de que el
    scheduler ya esté corriendo. Falla silenciosamente por empleado.
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(AIEmployee.id, AIEmployee.tenant_id).where(
                    AIEmployee.status != "paused"
                )
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
