"""
Tareas Celery del orquestador LangGraph.
"""
import uuid
from datetime import UTC

from app.workers.celery_app import celery_app, run_async


@celery_app.task(name="run_orchestrator", bind=True, max_retries=3, time_limit=600, soft_time_limit=540)
def run_orchestrator(self, task_id: str):
    """Ejecuta el orquestador LangGraph para una tarea dada."""
    from app.services.idempotency import SyncIdempotencyGuard
    guard = SyncIdempotencyGuard()

    # ── Idempotencia: si ya se ejecutó esta tarea, skip ──
    if guard.already_executed("run_orchestrator", task_id):
        print(f"[IDEMPOTENCY] run_orchestrator:{task_id} ya ejecutado. Skip.")
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = run_async(_execute_orchestrator(task_id))
        guard.mark_executed("run_orchestrator", task_id, {"status": "done"})
        return result
    except Exception as exc:
        import traceback
        traceback.print_exc()
        err_str = str(exc).lower()
        # Reintentar en errores transitorios: red, Redis, timeout LLM, rate limit
        is_transient = (
            isinstance(exc, (ConnectionError, OSError, TimeoutError))
            or "429" in err_str
            or "rate limit" in err_str
            or "timeout" in err_str
            or "service unavailable" in err_str
            or "overloaded" in err_str
            or "connection" in err_str
        )
        retry_num = self.request.retries
        if is_transient and retry_num < 3:
            guard.release("run_orchestrator", task_id)
            # Backoff exponencial: 30s, 60s, 120s
            countdown = 30 * (2 ** retry_num)
            print(f"[RETRY] run_orchestrator:{task_id} reintento {retry_num + 1}/3 en {countdown}s — {exc}")
            raise self.retry(exc=exc, countdown=countdown)
        # Error de lógica o reintentos agotados → marcar fallida
        run_async(_mark_task_failed(task_id, str(exc)))
        raise exc


@celery_app.task(name="resume_orchestrator", bind=True, max_retries=3, time_limit=600, soft_time_limit=540)
def resume_orchestrator(self, task_id: str):
    """Reanuda el orquestador tras una aprobación humana."""
    from app.services.idempotency import SyncIdempotencyGuard
    guard = SyncIdempotencyGuard()

    # ── Idempotencia: evitar crear la factura dos veces tras doble aprobación ──
    if guard.already_executed("resume_orchestrator", task_id):
        print(f"[IDEMPOTENCY] resume_orchestrator:{task_id} ya ejecutado. Skip.")
        return {"skipped": True, "reason": "already_executed"}

    try:
        result = run_async(_resume_orchestrator(task_id))
        guard.mark_executed("resume_orchestrator", task_id, {"status": "done"})
        return result
    except Exception as exc:
        guard.release("resume_orchestrator", task_id)
        raise self.retry(exc=exc, countdown=10)


async def _mark_task_failed(task_id: str, error_msg: str):
    """Marca una tarea como fallida en BD directamente (sin pasar por el orquestador)."""
    from datetime import datetime

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Task
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status = "failed"
                task.error_message = f"Error interno del agente: {error_msg[:500]}"
                task.completed_at = datetime.now(UTC)
                await db.commit()
    except Exception:
        pass  # Si falla esto, al menos ya logueamos en stderr


def _plan_to_ui_graph(plan: list, trigger_type: str) -> tuple[list, list]:
    """
    Convierte el plan del orquestador (lista de SubTask) en nodos y aristas ReactFlow.
    Genera un grafo DAG con layout automático de capas.
    """
    AGENT_TYPES = {
        "billing": "skill", "hr": "skill", "crm": "skill",
        "advisory": "skill", "banking": "skill", "documents": "skill",
        "compliance": "skill", "rag": "skill", "excel": "skill",
        "email": "skill", "coordinator": "action", "workflow": "action",
        "orchestrator": "action", "skill": "skill",
    }
    AGENT_LABELS = {
        "billing": "Facturación", "hr": "RRHH", "crm": "CRM",
        "advisory": "Asesoría Fiscal", "banking": "Banca",
        "documents": "Documentos", "compliance": "Cumplimiento",
        "rag": "Búsqueda RAG", "excel": "Excel", "email": "Email",
        "coordinator": "Coordinador", "orchestrator": "Orquestador",
        "workflow": "Workflow",
    }
    TRIGGER_LABELS = {
        "event_based": "Evento ERP", "schedule_based": "Programación", "manual": "Inicio Manual",
    }

    nodes = []
    edges = []

    # 1. Nodo trigger
    nodes.append({
        "id": "trigger",
        "type": "trigger",
        "position": {"x": 250, "y": 0},
        "data": {"label": TRIGGER_LABELS.get(trigger_type, "Trigger"), "trigger_type": trigger_type},
    })

    # 2. Construir índice id → position en el plan
    step_id_to_index: dict[str, int] = {}
    for i, step in enumerate(plan):
        step_id = step.get("id", f"step_{i}")
        step_id_to_index[step_id] = i

    # 3. Calcular capas (topological layers para layout)
    layers: dict[str, int] = {}  # step_id → layer
    for i, step in enumerate(plan):
        step_id = step.get("id", f"step_{i}")
        deps = step.get("depends_on", [])
        if not deps:
            layers[step_id] = 0
        else:
            max_dep_layer = 0
            for dep in deps:
                max_dep_layer = max(max_dep_layer, layers.get(dep, 0))
            layers[step_id] = max_dep_layer + 1

    # 4. Agrupar por capa y posicionar
    from collections import defaultdict
    layer_groups: dict[int, list] = defaultdict(list)
    for i, step in enumerate(plan):
        step_id = step.get("id", f"step_{i}")
        layer_groups[layers.get(step_id, i)].append((i, step_id, step))

    COL_W = 220
    ROW_H = 130

    for layer_idx in sorted(layer_groups.keys()):
        items = layer_groups[layer_idx]
        total_w = len(items) * COL_W
        start_x = 250 - total_w // 2 + COL_W // 2
        for col_idx, (original_idx, step_id, step) in enumerate(items):
            agent = step.get("agent", step.get("domain", "skill"))
            x = start_x + col_idx * COL_W
            y = 150 + layer_idx * ROW_H
            nodes.append({
                "id": step_id,
                "type": AGENT_TYPES.get(agent, "skill"),
                "position": {"x": x, "y": y},
                "data": {
                    "label": AGENT_LABELS.get(agent, agent.title()),
                    "domain": agent,
                    "description": step.get("action", step.get("instruction", ""))[:120],
                },
            })
            # Edges
            deps = step.get("depends_on", [])
            if deps:
                for dep_id in deps:
                    edges.append({
                        "id": f"e-{dep_id}-{step_id}",
                        "source": dep_id,
                        "target": step_id,
                    })
            else:
                # Sin dependencia explícita → conectar desde trigger
                edges.append({
                    "id": f"e-trigger-{step_id}",
                    "source": "trigger",
                    "target": step_id,
                })

    return nodes, edges


async def _build_tenant_context(tenant_id: str, db) -> str:
    """
    Carga contexto del tenant desde BD y lo devuelve como string para inyectar en el intent.
    Incluye: nombre empresa, NIF, fecha actual, primeros clientes disponibles.
    """
    from datetime import date
    from sqlalchemy import select
    from app.db.models.auth import Tenant
    from app.db.models.models import Client
    import uuid as _uuid

    lines = [f"Fecha actual: {date.today().strftime('%d/%m/%Y')}. Moneda: EUR (€). País: España."]

    try:
        tenant_res = await db.execute(select(Tenant).where(Tenant.id == _uuid.UUID(tenant_id)))
        tenant = tenant_res.scalar_one_or_none()
        if tenant:
            lines.append(f"Empresa emisora: {tenant.name} (NIF: {tenant.nif}).")
    except Exception:
        pass

    try:
        clients_res = await db.execute(
            select(Client)
            .where(Client.tenant_id == _uuid.UUID(tenant_id))
            .order_by(Client.created_at.asc())
            .limit(5)
        )
        clients = clients_res.scalars().all()
        if clients:
            client_list = ", ".join(f"{c.name} (NIF: {c.nif})" for c in clients)
            lines.append(f"Clientes disponibles: {client_list}.")
    except Exception:
        pass

    return " ".join(lines)


async def _execute_orchestrator(task_id: str):
    from datetime import datetime

    from sqlalchemy import select

    from app.agents.orchestrator import OrchestratorState, TaskStatus, orchestrator
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Task

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return

        if task.status == "cancelled":
            print(f"[CELERY] Tarea {task_id} fue cancelada antes de iniciar. Abortando.")
            return

        task.status = "executing"
        task.started_at = datetime.now(UTC)
        await db.commit()

        # ── Enrichment: inyectar contexto del tenant en el intent ─────────
        base_intent = task.user_intent or ""
        is_automation = bool((task.additional_metadata or {}).get("workflow_id"))
        if is_automation:
            try:
                ctx = await _build_tenant_context(str(task.tenant_id), db)
                enriched_intent = f"{base_intent}\n\n[Contexto del sistema: {ctx}]"
            except Exception:
                enriched_intent = base_intent
        else:
            enriched_intent = base_intent

        initial_state: OrchestratorState = {
            "task_id": task_id,
            "tenant_id": str(task.tenant_id),
            "user_id": str(task.created_by) if task.created_by else "",
            "user_intent": enriched_intent,
            # Pasar el domain guardado en BD directamente para no reclasificar
            "classified_domain": task.domain if task.domain else None,
            "plan": None,
            "current_step": 0,
            "agent_results": [],
            "status": TaskStatus.PENDING,
            "requires_human_approval": False,
            "approval_id": None,
            "error_message": None,
            "iteration_count": 0,
            "additional_metadata": task.additional_metadata or {},
        }

        # ── Streaming con logs en Redis ───────────────────────────────────
        import redis.asyncio as _aioredis
        from app.core.config import settings as _settings

        redis_key = f"exec_logs:{task_id}"
        try:
            _redis = await _aioredis.from_url(_settings.REDIS_URL, decode_responses=True)
            await _redis.delete(redis_key)  # limpiar logs anteriores
        except Exception:
            _redis = None

        async def _push_log(line: str):
            if _redis:
                try:
                    await _redis.rpush(redis_key, line)
                    await _redis.expire(redis_key, 7200)  # 2h TTL
                except Exception:
                    pass

        final_state = None
        seen_results: set = set()

        await _push_log("🚀 Iniciando automatización…")

        async for chunk in orchestrator.astream(initial_state, config={"recursion_limit": 50}):
            for node_name, state_update in chunk.items():
                if node_name == "__end__":
                    final_state = state_update
                    continue

                results: list = state_update.get("agent_results") or []
                for r in results:
                    rid = r.get("subtask_id") or r.get("agent", "") + str(len(seen_results))
                    if rid not in seen_results:
                        seen_results.add(rid)
                        agent = r.get("agent", "?")
                        summary = r.get("summary") or r.get("output", "")
                        if isinstance(summary, dict):
                            summary = summary.get("action") or str(summary)[:120]
                        ok = "✅" if r.get("success") else "❌"
                        await _push_log(f"{ok} [{agent}] {str(summary)[:200]}")

                err = state_update.get("error_message")
                if err and err not in seen_results:
                    seen_results.add(err)
                    await _push_log(f"⚠️ {err[:200]}")

                if state_update.get("status") in ("done", "failed", "awaiting_approval"):
                    final_state = state_update

        # Si astream no devolvió __end__, usar el último estado
        if final_state is None:
            final_state = initial_state

        if _redis:
            status_val = final_state.get("status")
            if hasattr(status_val, "value"):
                status_val = status_val.value
            icon = "✅" if status_val == "done" else "❌"
            await _push_log(f"{icon} Ejecución finalizada ({status_val})")
            await _redis.aclose()

        print("FINAL STATE RETURNED BY LANGGRAPH:", final_state)

        task.status = final_state["status"].value if hasattr(final_state["status"], "value") else final_state["status"]
        task.plan = final_state.get("plan")
        task.agent_results = final_state.get("agent_results", [])
        task.current_step = final_state.get("current_step", 0)
        task.requires_human_approval = final_state.get("requires_human_approval", False)
        task.error_message = final_state.get("error_message")
        task.additional_metadata = final_state.get("additional_metadata")

        if task.status in ("done", "failed"):
            task.completed_at = datetime.now(UTC)

        # ── Auto-guardar topología visual del plan en el Workflow ───────────
        wf_id = (task.additional_metadata or {}).get("workflow_id")
        plan_list = final_state.get("plan")
        if wf_id and plan_list:
            from app.db.models.models import Workflow as WFModel
            wf_res = await db.execute(select(WFModel).where(WFModel.id == uuid.UUID(wf_id)))
            wf_record = wf_res.scalar_one_or_none()
            if wf_record and not wf_record.ui_nodes:
                ui_nodes, ui_edges = _plan_to_ui_graph(plan_list, wf_record.trigger_type or "manual")
                wf_record.ui_nodes = ui_nodes
                wf_record.ui_edges = ui_edges

        # ── Actualizar el WorkflowExecution vinculado (si hay) ──────────────
        wf_exec_id = (task.additional_metadata or {}).get("execution_id")
        if wf_exec_id:
            from app.db.models.models import WorkflowExecution as WFExec
            exec_res = await db.execute(
                select(WFExec).where(WFExec.id == uuid.UUID(wf_exec_id))
            )
            wf_exec = exec_res.scalar_one_or_none()
            if wf_exec and wf_exec.status == "running":
                task_to_exec_status = {
                    "done": "success",
                    "failed": "failed",
                    "awaiting_approval": "paused",
                }
                wf_exec.status = task_to_exec_status.get(task.status, "running")
                if task.status in ("done", "failed"):
                    wf_exec.completed_at = datetime.now(UTC)
                wf_exec.result_log = (
                    task.error_message
                    or (str(task.agent_results[-1].get("output", "")) if task.agent_results else None)
                    or wf_exec.result_log
                )

        # ── Actualizar el documento vinculado (si hay) ──────────────────────
        from app.db.models.models import TenantDocument
        doc_result = await db.execute(
            select(TenantDocument).where(TenantDocument.task_id == task.id)
        )
        linked_doc = doc_result.scalars().first()
        if linked_doc:
            if task.status == "done":
                linked_doc.status = "processed"
                linked_doc.processed_at = datetime.now(UTC)
                # Guardar el resumen del agente como contenido parseado
                results = final_state.get("agent_results", [])
                if results:
                    last = results[-1]
                    output = last.get("output", {})
                    if isinstance(output, dict):
                        classified = output.get("classified") or {}
                        summary = (
                            classified.get("summary")
                            or output.get("summary")
                            or output.get("respuesta_consulta")
                            or output.get("alertas_redactadas", [""])[0]
                        )
                        linked_doc.parsed_content = summary or str(output)
                    else:
                        linked_doc.parsed_content = str(output)
            else:
                linked_doc.status = "failed"

        await db.commit()



async def _resume_orchestrator(task_id: str):
    """
    Reanuda la ejecución después de una aprobación humana.
    Coge el payload guardado en PendingApproval y crea la factura en BD local y Holded.
    """
    import calendar
    import uuid
    from datetime import datetime
    from decimal import Decimal

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Client, Invoice, PendingApproval, Task, TenantIntegration
    from app.integrations.holded import HoldedClient
    from app.services.encryption import decrypt_credentials

    async with AsyncSessionLocal() as db:
        try:
            # 1. Cargar la tarea
            print(f"[RESUME] Cargando tarea {task_id}")
            task_res = await db.execute(select(Task).where(Task.id == task_id))
            task = task_res.scalar_one_or_none()
            if not task:
                print(f"[RESUME] Error: Tarea {task_id} no encontrada")
                return

            # 2. Buscar la PendingApproval aprobada para esta tarea
            print(f"[RESUME] Buscando approval aprobado para {task_id}")
            approval_res = await db.execute(
                select(PendingApproval).where(
                    PendingApproval.task_id == uuid.UUID(task_id),
                    PendingApproval.status == "approved",
                ).order_by(PendingApproval.approved_at.desc()).limit(1)
            )
            approval = approval_res.scalars().first()

            if not approval or not approval.action_payload:
                print("[RESUME] Error: Approval no encontrado o sin payload")
                task.status = "failed"
                task.error_message = "No se encontró la aprobación asociada para continuar o el payload está vacío."
                await db.commit()
                return

            payload_data = approval.action_payload  # dict
            print(f"[RESUME] Payload cargado: keys={list(payload_data.keys())}")

            # 3. Intentar obtener API key de Holded
            int_res = await db.execute(
                select(TenantIntegration).where(
                    TenantIntegration.tenant_id == task.tenant_id,
                    TenantIntegration.integration_type == "holded",
                    TenantIntegration.is_active.is_(True),
                )
            )
            integration = int_res.scalars().first()
            holded_api_key = None
            if integration:
                try:
                    creds = decrypt_credentials(integration.encrypted_credentials)
                    holded_api_key = creds.get("api_key")
                except Exception as e:
                    print(f"[RESUME] Error descifrando holded key: {e}")
        except Exception as _e:
            print(f"[RESUME] Critical error early: {_e}")
            import traceback; traceback.print_exc()
            return

        # 4. Recuperar Cliente Local (NIF o ID)
        client_nif = payload_data.get("client_nif")
        amount_base = Decimal(str(payload_data.get("amount_base", "0")).replace(",", "."))
        vat_rate = Decimal(str(payload_data.get("vat_rate", 21)))
        concept = payload_data.get("concept", "Concepto por aprobación manual")
        invoice_date_str = payload_data.get("invoice_date", datetime.now(UTC).strftime("%Y-%m-%d"))

        from datetime import date
        inv_date = date.fromisoformat(invoice_date_str)

        cliente_local = None
        # Si venía el ID ya pre-guardado de la fase anterior
        if "contact_id_local" in payload_data:
            client_res = await db.execute(select(Client).where(Client.id == uuid.UUID(payload_data["contact_id_local"])))
            cliente_local = client_res.scalars().first()

        if not cliente_local and client_nif:
            client_res = await db.execute(select(Client).where(Client.tenant_id == task.tenant_id, Client.nif == client_nif))
            cliente_local = client_res.scalars().first()

        # FALLBACK: Si todavía no existe (por rollbacks asincrónos en el origen), crearlo aquí.
        if not cliente_local and client_nif:
            print(f"[RESUME] Cliente {client_nif} no estaba en DB. Re-creándolo como fallback.")
            cliente_local = Client(
                tenant_id=task.tenant_id,
                nif=client_nif,
                name=payload_data.get("client_name", "Cliente Generado Auto")
            )
            db.add(cliente_local)
            await db.commit()
            await db.refresh(cliente_local)

        if not cliente_local:
            task.status = "failed"
            task.error_message = "No se encontró ni se pudo crear el cliente local vinculado durante la reanudación."
            await db.commit()
            return

        # 5. Crear la factura en Holded (Opcional)
        holded_id = None
        if holded_api_key and cliente_local.holded_id and holded_api_key != "DEMO_HOLDED_KEY":
            date_unix = int(calendar.timegm(inv_date.timetuple()))
            holded_payload = HoldedClient.build_invoice_payload(
                contact_id=cliente_local.holded_id,
                concept=concept,
                amount_base=float(amount_base),
                vat_rate=float(vat_rate),
                date_unix=date_unix,
                notes=payload_data.get("notes") or "",
            )
            try:
                holded_client = HoldedClient(api_key=holded_api_key)
                invoice_holded_resp = await holded_client.create_invoice(holded_payload)
                holded_id = invoice_holded_resp.get("id", "unknown")
                await holded_client.close()
            except Exception:
                holded_id = "failed_sync"

        # 6. Guardar en Base de Datos Local
        tax_amount = round(amount_base * (vat_rate / Decimal("100")), 2)
        total_amount = amount_base + tax_amount

        # Generar número de factura secuencial
        from sqlalchemy import func
        count_res = await db.execute(
            select(func.count(Invoice.id)).where(Invoice.tenant_id == task.tenant_id)
        )
        invoice_count = (count_res.scalar() or 0) + 1
        invoice_number = f"FAC-{inv_date.year}-{invoice_count:04d}"

        new_invoice = Invoice(
            tenant_id=task.tenant_id,
            client_id=cliente_local.id,
            invoice_number=invoice_number,
            date=inv_date,
            amount_base=amount_base,
            tax_amount=tax_amount,
            amount_total=total_amount,
            status="draft",
            invoice_type="issued",
            external_id=holded_id
        )
        db.add(new_invoice)
        await db.flush()

        # 6b. Crear la línea de detalle de la factura
        from app.db.models.models import InvoiceLine
        invoice_line = InvoiceLine(
            invoice_id=new_invoice.id,
            description=concept,
            quantity=Decimal("1"),
            unit_price=amount_base,
            tax_percentage=vat_rate,
            total=total_amount,
        )
        db.add(invoice_line)
        await db.flush()

        # 7. Actualizar la Tarea principal
        existing_results = list(task.agent_results or [])
        existing_results.append({
            "agent": "billing",
            "success": True,
            "output": {
                "action": "draft_created",
                "holded_invoice_id": holded_id or "local_only",
                "local_invoice_id": str(new_invoice.id),
                "note": "Factura creada tras aprobación manual.",
            },
        })
        task.agent_results = existing_results

        # En vez de "done", incrementamos paso y relanzamos el grafo
        current_step = task.current_step + 1
        task.current_step = current_step
        task.status = "executing"
        task.requires_human_approval = False

        await db.commit()

        # Re-construir el estado y pasarle de vuelta a LangGraph
        from app.agents.orchestrator import OrchestratorState, TaskStatus, orchestrator
        initial_state: OrchestratorState = {
            "task_id": task_id,
            "tenant_id": str(task.tenant_id),
            "user_id": str(task.created_by) if task.created_by else "",
            "user_intent": task.user_intent or "",
            "classified_domain": task.domain if task.domain else None,
            "plan": task.plan,
            "current_step": current_step,
            "agent_results": existing_results,
            "status": TaskStatus.EXECUTING,
            "requires_human_approval": False,
            "approval_id": None,
            "error_message": task.error_message,
            "iteration_count": 0,
            "additional_metadata": task.additional_metadata or {},
        }

        final_state = await orchestrator.ainvoke(initial_state, config={"recursion_limit": 50})

        task.status = final_state["status"].value if hasattr(final_state["status"], "value") else final_state["status"]
        task.plan = final_state.get("plan")
        task.agent_results = final_state.get("agent_results", [])
        task.current_step = final_state.get("current_step", 0)
        task.requires_human_approval = final_state.get("requires_human_approval", False)
        task.error_message = final_state.get("error_message")

        if task.status in ("done", "failed"):
            task.completed_at = datetime.now(UTC)

        await db.commit()
