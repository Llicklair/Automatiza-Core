"""Smoke end-to-end del Coordinador (agents/orchestrator).

Invoca `orchestrator.ainvoke()` directamente para una bateria de prompts en
lenguaje natural (mono y multi-dominio). El objetivo es ver de que es capaz
el LLM HOY: que dominio clasifica, que plan genera, que dispatchers ejecuta
y con que resultado.

Caracteristicas:
- Sin Task en DB (estado se construye a mano). Mas rapido y aislado.
- Side-effects en DB son REALES (crea clientes, facturas, candidatos, etc.)
  en el tenant indicado por TENANT_ID. Limpieza manual al final si lo deseas.
- SMTP outbound MOCKEADO: ningun email se envia de verdad. Los emails
  interceptados se listan en el reporte.
- Genera reporte en tasks/smoke_orchestrator_<fecha>.md con resumen + detalle.

Uso:
  py -3.11 backend/scripts/smoke_orchestrator.py
  py -3.11 backend/scripts/smoke_orchestrator.py --only crm_simple
  py -3.11 backend/scripts/smoke_orchestrator.py --skip impossible,complex_chain
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT.parent / ".env")

# Mismo patron que test_agents.py: forzar fuera env contaminada
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("DEFAULT_LLM_PROVIDER", None)


# Tenant AutomatizaPyme + user demo (mismos que test_agents.py)
TENANT_ID = "9cd49fbb-355b-4b75-ad57-45ebe1c85749"
USER_ID = "0d7e5ea1-5a91-4372-8de1-8e72a2e0085b"

# Casos negativos: el Coordinador NO debe "completar" estos con tools alucinadas.
# Se espera que pida aclaración, falle elegante o no marque la task como done.
NEGATIVE_IDS = {"ambiguous", "impossible"}

# Estados que consideramos "completado con éxito".
_DONE_STATES = {"done", "DONE", "TaskStatus.DONE"}


# (id, prompt, comentario corto sobre que valida)
PROMPTS: list[tuple[str, str, str]] = [
    (
        "crm_simple",
        "Crea un cliente llamado Acme Smoke con email contacto@acme-smoke.test y telefono 600111222",
        "Mono-dominio CRM: clasificar -> dispatch CRM -> crear contacto",
    ),
    (
        "billing_simple",
        "Emite una factura de 500 euros + IVA al cliente Acme Smoke por servicios de consultoria",
        "Mono-dominio billing: requiere que CRM ya tenga el cliente del prompt anterior",
    ),
    (
        "hr_simple",
        "Da de alta un candidato llamado Juan Smoke Perez con email juan.smoke@test.com para puesto de desarrollador backend",
        "Mono-dominio recruitment: crear candidato",
    ),
    (
        "reports_month",
        "Dame el resumen contable del mes pasado",
        "Reports: clasificar como report y resolver mes/year",
    ),
    (
        "multi_billing_email",
        "Factura los servicios prestados a Acme Smoke este mes por 800 euros y mandale email avisando de que ya tiene la factura disponible",
        "Multi-dominio billing + email (SMTP mockeado)",
    ),
    (
        "ambiguous",
        "Haz lo de siempre con Acme",
        "Ambiguedad: el orchestrator debe pedir aclaracion o fallar elegante",
    ),
    (
        "impossible",
        "Lanza un cohete a Marte y compra Twitter",
        "Imposible: debe rechazar limpiamente sin alucinar tools",
    ),
    (
        "complex_chain",
        "Revisa que facturas vencen esta semana, manda recordatorios por email a los clientes morosos y luego dame un resumen de lo enviado",
        "Cadena compleja billing -> email -> reports",
    ),
    # === Iter 1 email/A (consultora) - aislamiento agente email ===
    (
        "iter1_email_send",
        "Manda un email a juan.perez@acme.test agradeciendole la reunion de ayer y confirmando que le envio la propuesta esta semana",
        "Iter1/A: clasificar email -> dispatch email -> tool send (SMTP mockeado)",
    ),
    (
        "iter1_email_summarize",
        "Resume mis emails sin leer de hoy y dime cuales son urgentes",
        "Iter1/A: clasificar email -> dispatch email -> tool list/summarize bandeja",
    ),
    (
        "iter1_email_search",
        "Busca el ultimo email que envie a Lucia sobre el contrato de servicios",
        "Iter1/A: clasificar email -> dispatch email -> tool search en gmail",
    ),
    # === Iter 2 documents/C (asesoria) ===
    (
        "iter2_documents",
        "Analiza el ultimo contrato PDF que subi y extrae las clausulas de penalizacion por incumplimiento",
        "Iter2/C: clasificar documents -> tool analyze/extract sobre PDF",
    ),
    # === Iter 3 billing/B (retail) ===
    (
        "iter3_billing",
        "Crea una factura de 1250 euros mas IVA al cliente con NIF B12345678 por suministro de material de oficina y mandasela por email",
        "Iter3/B: clasificar billing -> create_invoice + send_invoice_by_email",
    ),
    # === Iter 4 hr/A (consultora) ===
    (
        "iter4_hr",
        "Calcula la nomina de mayo para Ana Garcia y dejala pendiente de aprobacion",
        "Iter4/A: clasificar hr -> calculate_and_create_payroll",
    ),
    # === Iter 5 recruitment/A ===
    (
        "iter5_recruitment",
        "Da de alta a la candidata Lucia Martinez con email lucia.martinez@test.com para la vacante Backend Senior y agenda una entrevista",
        "Iter5/A: clasificar recruitment -> create_candidate + schedule_interview",
    ),
    # === Iter 6 crm/B (retail) ===
    (
        "iter6_crm",
        "Crea una oportunidad de 8500 euros con el cliente Acme Smoke en etapa Negociacion",
        "Iter6/B: clasificar crm -> create_opportunity",
    ),
    # === Iter 7 banking/C ===
    (
        "iter7_banking",
        "Concilia los movimientos bancarios de abril con las facturas emitidas y dame el resumen",
        "Iter7/C: clasificar banking -> reconcile_transactions + financial_summary",
    ),
    # === Iter 8 compliance/C ===
    (
        "iter8_compliance",
        "Recuerdame que modelos de IVA tengo que presentar este trimestre y consulta el BOE de hoy",
        "Iter8/C: clasificar compliance -> check_fiscal_deadlines + check_boe_news",
    ),
    # === Iter 9 accounting/B ===
    (
        "iter9_accounting",
        "Cuadrame los asientos del libro diario del mes pasado",
        "Iter9/B: clasificar accounting -> tools de libro diario",
    ),
    # === Iter 10 marketing/A ===
    (
        "iter10_marketing",
        "Generame 3 propuestas de copy para la landing page del servicio Auditoria IT",
        "Iter10/A: clasificar marketing -> generate_copy",
    ),
    # === Iter 11 excel/B ===
    (
        "iter11_excel",
        "Convierte el ultimo excel de pedidos en un resumen agrupado por categoria",
        "Iter11/B: clasificar excel -> parse_excel + transform",
    ),
    # === Iter 12 rag/C ===
    (
        "iter12_rag",
        "Busca en nuestra base de conocimiento la politica de devoluciones y plazos de garantia",
        "Iter12/C: clasificar rag -> semantic_search en knowledge base",
    ),
    # === Iter 13 uploads/A ===
    (
        "iter13_uploads",
        "Procesa el lote de facturas que subi hoy y dame un resumen",
        "Iter13/A: clasificar uploads/documents -> ingest + dispatch a documents",
    ),
    # === Ronda 2 end-to-end multi-agente ===
    (
        "e2e1_recruit_email_calendar",
        "Recibi el CV de Lucia Martinez para Backend SR, evaluala, agenda entrevista el viernes a las 10 y mandale email de confirmacion",
        "E2E1/A: recruitment -> calendar -> email en cadena",
    ),
    (
        "e2e2_invoice_accounting_bank",
        "Tengo una factura de proveedor de 500 euros, registra el asiento contable y concilia con el banco",
        "E2E2/B: documents -> accounting -> banking",
    ),
    (
        "e2e3_crm_contract_email",
        "Crea cliente Innova Smoke con email contacto@innova.test, genera un contrato de servicios estandar y mandaselo por email",
        "E2E3/A: crm -> documents -> email",
    ),
    (
        "e2e4_quarterly_close",
        "Cierre trimestral: dame los movimientos del trimestre, calcula el IVA, prepara modelo 303 y notificame para aprobacion",
        "E2E4/C: banking -> compliance (fiscal_approval) -> email",
    ),
    (
        "e2e5_lead_to_campaign",
        "Califica el lead de Mercados S.L., creame oportunidad si encaja y prepara campaña de nurture por email",
        "E2E5/B: crm.qualify_leads -> marketing -> email",
    ),
    (
        "e2e6_payroll_to_portal",
        "Genera todas las nominas de este mes, crea recibos PDF y publicalos en el portal de cada empleado",
        "E2E6/A: hr.generate_all_payrolls -> documents -> portal",
    ),
]


async def _create_task_row(prompt_text: str) -> str:
    """Inserta una Task real en DB para que los inserts dependientes
    (tenant_documents, audit_log, etc.) no violen FK al task_id."""
    from app.db.base import AsyncSessionLocal
    from app.db.models.tasks import Task

    task = Task(
        tenant_id=uuid.UUID(TENANT_ID),
        created_by=uuid.UUID(USER_ID) if USER_ID else None,
        status="pending",
        domain="coordinator",
        user_intent=prompt_text,
        additional_metadata={"source": "smoke_orchestrator"},
    )
    async with AsyncSessionLocal() as db:
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return str(task.id)


def _initial_state(prompt_text: str, task_id: str) -> dict:
    """Construye un OrchestratorState minimo, equivalente a _build_initial_state pero
    sin enriquecimiento por workflow_id."""
    from app.agents.orchestrator import TaskStatus

    return {
        "task_id": task_id,
        "tenant_id": TENANT_ID,
        "user_id": USER_ID,
        "user_intent": prompt_text,
        "current_intent": None,
        "classified_domain": None,
        "plan": None,
        "current_step": 0,
        "agent_results": [],
        "status": TaskStatus.PENDING,
        "requires_human_approval": False,
        "approval_id": None,
        "error_message": None,
        "iteration_count": 0,
        "tenant_knowledge": [],
        "additional_metadata": None,
    }


async def run_one(orchestrator, prompt_id: str, prompt_text: str, comment: str) -> dict:
    from app.core.tenant_context import set_current_tenant, set_current_task

    task_id = await _create_task_row(prompt_text)
    state = _initial_state(prompt_text, task_id)
    set_current_tenant(TENANT_ID)
    set_current_task(task_id)

    start = time.time()
    try:
        final = await orchestrator.ainvoke(state)
        elapsed = time.time() - start
        status_val = final.get("status")
        return {
            "id": prompt_id,
            "task_id": task_id,
            "comment": comment,
            "prompt": prompt_text,
            "ok": True,
            "elapsed_s": round(elapsed, 2),
            "status": status_val.value if hasattr(status_val, "value") else str(status_val),
            "classified_domain": final.get("classified_domain"),
            "plan_size": len(final.get("plan") or []),
            "plan": [
                {"agent": st.get("agent"), "action": st.get("action"), "status": st.get("status")}
                for st in (final.get("plan") or [])
            ],
            "agent_results": [
                {
                    "agent": r.get("agent"),
                    "success": r.get("success"),
                    "error": r.get("error"),
                    "output_preview": _preview(r.get("output")),
                }
                for r in final.get("agent_results", [])
            ],
            "error_message": final.get("error_message"),
            "iteration_count": final.get("iteration_count"),
            "requires_human_approval": final.get("requires_human_approval"),
        }
    except Exception as exc:
        return {
            "id": prompt_id,
            "task_id": task_id,
            "comment": comment,
            "prompt": prompt_text,
            "ok": False,
            "elapsed_s": round(time.time() - start, 2),
            "exception": f"{type(exc).__name__}: {exc}",
        }


def _preview(output) -> str:
    """Resume el output del agente a ~200 chars para el reporte."""
    if output is None:
        return ""
    if isinstance(output, (dict, list)):
        try:
            s = json.dumps(output, ensure_ascii=False)
        except Exception:
            s = str(output)
    else:
        s = str(output)
    return s[:200] + ("..." if len(s) > 200 else "")


def _verdict(r: dict) -> str:
    """Veredicto estricto PASS/FAIL para que el smoke sea un test, no un reporte.

    - Caso negativo (NEGATIVE_IDS): PASS si NO se completó como done (esperamos
      aclaración o fallo elegante), FAIL si se marcó done alucinando tools.
    - Caso positivo: FAIL si hubo excepción, si el status no es done, o si algún
      agente del plan devolvió success=False. PASS en otro caso.
    """
    is_negative = r["id"] in NEGATIVE_IDS
    status = r.get("status")
    reached_done = bool(r.get("ok")) and status in _DONE_STATES

    if is_negative:
        if not reached_done:
            return "PASS"  # pidió aclaración o falló elegante
        # Llegó a done: aceptable solo si declinó conversando (dominio chat),
        # NO si dispatchó un dominio real como si la tarea imposible fuera viable.
        return "PASS" if r.get("classified_domain") in ("chat", None) else "FAIL"

    if r.get("exception"):
        return "FAIL"
    if not reached_done:
        return "FAIL"
    failed_agents = [a for a in (r.get("agent_results") or []) if not a.get("success")]
    return "FAIL" if failed_agents else "PASS"


def _format_row(r: dict) -> str:
    status = r.get("status") or ("EXC" if r.get("exception") else "?")
    domain = r.get("classified_domain") or "-"
    steps = r.get("plan_size") if r.get("plan_size") is not None else "-"
    t = r.get("elapsed_s", "-")
    if r.get("exception"):
        errors = f"EXC: {r['exception'][:80]}"
    elif r.get("error_message"):
        errors = r["error_message"][:80]
    elif r.get("agent_results"):
        failed = [a for a in r["agent_results"] if not a.get("success")]
        if failed:
            errors = "; ".join(
                f"{a['agent']}: {(a.get('error') or '')[:40]}" for a in failed[:3]
            )
        else:
            errors = "ok"
    else:
        errors = "-"
    return f"| {r['id']} | {_verdict(r)} | {status} | {domain} | {steps} | {t} | {errors} |"


def _write_report(results: list[dict], sent_emails: list[dict]) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    out = ROOT.parent / "tasks" / f"smoke_orchestrator_{today}.md"
    out.parent.mkdir(exist_ok=True)

    lines = [
        f"# Smoke Orchestrator (Coordinador) - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Tenant: `{TENANT_ID}` (AutomatizaPyme)  ",
        f"User: `{USER_ID}`  ",
        f"SMTP: mockeado (no se envio ningun email real)  ",
        f"Prompts ejecutados: {len(results)}  ",
        f"Emails interceptados: {len(sent_emails)}  ",
        "",
        "## Resumen",
        "",
        "| ID | Veredicto | Status | Dominio | Steps | t(s) | Errores |",
        "|---|---|---|---|---|---|---|",
    ]
    lines += [_format_row(r) for r in results]
    passed = sum(1 for r in results if _verdict(r) == "PASS")
    failed = sum(1 for r in results if _verdict(r) == "FAIL")
    lines += ["", f"**Veredicto global: {passed} PASS / {failed} FAIL de {len(results)}**"]

    lines += ["", "## Detalle por prompt", ""]
    for r in results:
        lines.append(f"### {r['id']}")
        lines.append(f"_{r['comment']}_")
        lines.append("")
        lines.append(f"**Prompt**: {r['prompt']}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(r, indent=2, ensure_ascii=False))
        lines.append("```")
        lines.append("")

    lines += ["## Emails interceptados", "", "```json"]
    lines.append(json.dumps(sent_emails, indent=2, ensure_ascii=False))
    lines.append("```")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="CSV de ids de prompts a ejecutar")
    parser.add_argument("--skip", help="CSV de ids de prompts a saltar")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Devuelve exit code 1 si algún prompt obtiene veredicto FAIL (modo test).",
    )
    args = parser.parse_args()

    only = set((args.only or "").split(",")) if args.only else None
    skip = set((args.skip or "").split(",")) if args.skip else set()

    selected = [
        (pid, ptext, comment)
        for pid, ptext, comment in PROMPTS
        if (only is None or pid in only) and pid not in skip
    ]
    if not selected:
        print("Sin prompts seleccionados. Revisa --only/--skip.")
        return 1

    # Mock del envio SMTP. Atrapamos el facade send_email del email_sender.
    sent_emails: list[dict] = []

    async def fake_send_email(*args, **kwargs):
        # Firma real de send_email puede variar; capturamos to/subject best-effort.
        to = kwargs.get("to") or kwargs.get("recipient") or (args[0] if args else None)
        subject = kwargs.get("subject") or (args[1] if len(args) > 1 else None)
        sent_emails.append(
            {
                "to": str(to) if to else None,
                "subject": str(subject) if subject else None,
                "ts": datetime.now(timezone.utc).isoformat(),
                "kwargs_keys": sorted(kwargs.keys()),
            }
        )
        return {"success": True, "message_id": "smoke-fake", "to": str(to) if to else None}

    print(f"== Smoke Orchestrator: {len(selected)} prompts ==")
    print(f"Tenant: {TENANT_ID}\n")

    with patch("app.services.email_sender.send_email", side_effect=fake_send_email):
        # Import diferido para que el patch este activo cuando los modulos lo resuelvan
        from app.agents.orchestrator import orchestrator

        results: list[dict] = []
        for pid, ptext, comment in selected:
            print(f"[{pid}] ejecutando ({len(ptext)} chars)...", flush=True)
            r = await run_one(orchestrator, pid, ptext, comment)
            results.append(r)
            verdict = _verdict(r)
            print(
                f"  -> {verdict} status={r.get('status')} domain={r.get('classified_domain')} "
                f"steps={r.get('plan_size')} t={r.get('elapsed_s')}s",
                flush=True,
            )

    report = _write_report(results, sent_emails)
    passed = sum(1 for r in results if _verdict(r) == "PASS")
    failed = sum(1 for r in results if _verdict(r) == "FAIL")
    print(f"\nReporte: {report}")
    print(f"Emails interceptados: {len(sent_emails)}")
    print(f"Veredicto global: {passed} PASS / {failed} FAIL de {len(results)}")

    if args.strict and failed > 0:
        print(f"STRICT: {failed} prompt(s) con veredicto FAIL -> exit 1", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
