"""
Dispatcher de informes mensuales (report).
"""

import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _extract_month_year

logger = logging.getLogger(__name__)


async def _dispatch_report(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Genera el informe mensual de empresa y lo guarda como documento PDF."""
    intent = subtask.get("params", {}).get("intent", state.get("user_intent", ""))

    # Extraer mes del intent con lógica robusta de lenguaje natural
    _month, _year = _extract_month_year(intent)
    month_str = f"{_year}-{_month:02d}"

    try:
        # Llamada interna al endpoint de generación de informes

        # Obtener token del estado para autenticar la petición interna
        # Si no hay token en estado, usamos la BD directamente
        from calendar import monthrange as _mr
        from datetime import UTC as _UTC
        from datetime import date as _date
        from datetime import datetime as _dt

        from app.db.base import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            from sqlalchemy import and_, func
            from sqlalchemy import select as _select

            from app.db.models.models import (
                BankTransaction,
                Client,
                Employee,
                Invoice,
                Payroll,
                Tenant,
                TenantDocument,
            )
            from app.services.pdf_service import generate_snapshot_pdf

            tenant_id = state["tenant_id"]
            user_id = state["user_id"]

            year, mon = map(int, month_str.split("-"))
            start = _date(year, mon, 1)
            last_day = _mr(year, mon)[1]
            end = _date(year, mon, last_day)

            # Obtener nombre de empresa
            t_q = await db.execute(_select(Tenant).where(Tenant.id == tenant_id))
            tenant = t_q.scalar_one_or_none()
            company_name = tenant.name if tenant and tenant.name else "Tu empresa"

            # Facturas
            inv_q = await db.execute(
                _select(Invoice).where(
                    and_(
                        Invoice.tenant_id == tenant_id,
                        func.date(Invoice.date) >= start,
                        func.date(Invoice.date) <= end,
                    )
                )
            )
            invoices = inv_q.scalars().all()
            issued = [i for i in invoices if i.invoice_type == "issued"]
            received = [i for i in invoices if i.invoice_type == "received"]
            pending_issued = [i for i in issued if i.status in ("draft", "pending")]
            ingresos = sum(float(i.amount_total or 0) for i in issued)
            gastos = sum(float(i.amount_total or 0) for i in received)
            margen = ingresos - gastos
            margen_pct = round((margen / ingresos) * 100, 1) if ingresos > 0 else 0.0
            imp_pendiente = sum(float(i.amount_total or 0) for i in pending_issued)

            # Banca
            tx_q = await db.execute(
                _select(BankTransaction).where(
                    and_(
                        BankTransaction.tenant_id == tenant_id,
                        BankTransaction.date >= start,
                        BankTransaction.date <= end,
                    )
                )
            )
            txs = tx_q.scalars().all()
            bank_in = sum(float(t.amount) for t in txs if float(t.amount) > 0)
            bank_out = abs(sum(float(t.amount) for t in txs if float(t.amount) < 0))
            reconciled = sum(1 for t in txs if t.status == "reconciled")

            # RRHH
            emp_q = await db.execute(
                _select(Employee).where(
                    and_(Employee.tenant_id == tenant_id, Employee.status == "active")
                )
            )
            employees = emp_q.scalars().all()
            payroll_q = await db.execute(
                _select(Payroll).where(
                    and_(
                        Payroll.tenant_id == tenant_id,
                        func.date(Payroll.period_start) >= start,
                        func.date(Payroll.period_end) <= end,
                    )
                )
            )
            payrolls = payroll_q.scalars().all()
            coste_nominas = sum(float(p.net_salary or 0) for p in payrolls)
            paid_payrolls = [p for p in payrolls if p.status == "paid"]

            # Clientes
            total_clients_q = await db.execute(
                _select(func.count()).select_from(Client).where(Client.tenant_id == tenant_id)
            )
            total_clients = total_clients_q.scalar() or 0
            new_clients_q = await db.execute(
                _select(func.count())
                .select_from(Client)
                .where(
                    and_(
                        Client.tenant_id == tenant_id,
                        func.date(Client.created_at) >= start,
                        func.date(Client.created_at) <= end,
                    )
                )
            )
            new_clients = new_clients_q.scalar() or 0

            # Top client
            client_totals: dict = {}
            for inv in issued:
                cid = str(inv.client_id) if inv.client_id else None
                if cid:
                    client_totals[cid] = client_totals.get(cid, 0) + float(inv.amount_total or 0)
            top_client_name = None
            top_amount = 0.0
            if client_totals:
                top_cid = max(client_totals, key=client_totals.get)
                top_amount = client_totals[top_cid]
                cl_q = await db.execute(_select(Client).where(Client.id == top_cid))
                cl = cl_q.scalar_one_or_none()
                if cl:
                    top_client_name = cl.name

            # Resumen ejecutivo
            tendencia = "positiva" if margen > 0 else "negativa"
            resumen = (
                f"El mes {month_str} presenta una tendencia {tendencia}. "
                f"La empresa facturó {ingresos:,.2f} € con un margen bruto del {margen_pct:.1f}%. "
            )
            if pending_issued:
                resumen += f"Quedan {len(pending_issued)} facturas pendientes de cobro ({imp_pendiente:,.2f} €). "
            if employees:
                resumen += f"Plantilla activa: {len(employees)} empleados, coste nóminas {coste_nominas:,.2f} €. "
            if txs:
                resumen += f"Se registraron {len(txs)} movimientos bancarios."

            # Construir dict estructurado para PDF con gráficas
            snap_dict = {
                "facturas": {
                    "ingresos_total": ingresos,
                    "gastos_total": gastos,
                    "margen_bruto": margen,
                    "margen_pct": margen_pct,
                    "facturas_emitidas": len(issued),
                    "facturas_recibidas": len(received),
                    "facturas_pendientes_cobro": len(pending_issued),
                    "importe_pendiente_cobro": imp_pendiente,
                },
                "banca": {
                    "total_ingresos": bank_in,
                    "total_gastos": bank_out,
                    "saldo_neto": bank_in - bank_out,
                    "transacciones": len(txs),
                    "reconciliadas": reconciled,
                },
                "rrhh": {
                    "empleados_activos": len(employees),
                    "coste_nominas": coste_nominas,
                    "nominas_pagadas": len(paid_payrolls),
                    "nominas_pendientes": len(payrolls) - len(paid_payrolls),
                },
                "clientes": {
                    "total_clientes": total_clients,
                    "nuevos_periodo": new_clients,
                    "top_client_name": top_client_name,
                    "top_client_amount": top_amount,
                },
                "resumen_ejecutivo": resumen,
            }

            # Generar PDF con gráficas
            import os as _os
            import uuid as _uuid

            pdf_bytes = generate_snapshot_pdf(
                snap=snap_dict,
                company_name=company_name,
                month=month_str,
            )
            upload_dir = _os.path.abspath(
                _os.path.join(_os.path.dirname(__file__), "..", "..", "..", "..", "uploads")
            )
            _os.makedirs(upload_dir, exist_ok=True)
            file_name = f"informe_{month_str}_{_uuid.uuid4().hex[:8]}.pdf"
            file_path = _os.path.join(upload_dir, file_name)
            with open(file_path, "wb") as fh:
                fh.write(pdf_bytes)

            # Guardar en tenant_documents
            doc = TenantDocument(
                id=_uuid.uuid4(),
                tenant_id=tenant_id,
                uploaded_by=user_id,
                file_name=file_name,
                file_type="application/pdf",
                file_path=file_path,
                file_size=len(pdf_bytes),
                status="processed",
                parsed_content=resumen,
                category="informes",
                created_at=_dt.now(_UTC),
                processed_at=_dt.now(_UTC),
            )
            db.add(doc)
            await db.commit()

        return {
            "subtask_id": subtask.get("id", "report_1"),
            "agent": "report",
            "success": True,
            "output": {
                "message": f"Informe mensual de {month_str} generado correctamente para {company_name}.",
                "file_name": file_name,
                "period": month_str,
                "resumen": resumen,
                "kpis": {
                    "ingresos": ingresos,
                    "gastos": gastos,
                    "margen_pct": margen_pct,
                    "empleados_activos": len(employees),
                    "pendiente_cobro": imp_pendiente,
                },
            },
            "error": None,
        }
    except Exception as exc:
        return {
            "subtask_id": subtask.get("id", "report_1"),
            "agent": "report",
            "success": False,
            "output": {},
            "error": f"Error generando informe mensual: {exc}",
        }
