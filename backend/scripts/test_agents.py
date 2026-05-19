"""[DEPRECATED] Harness de testeo de agentes individuales (sin orchestrator).

⚠️  DEPRECATED — duplica cobertura de la suite pytest oficial y puede
divergir. Equivalentes en `backend/tests/`:

  - test_accounting_agent.py
  - test_agent_execution_trace.py
  - test_agent_metrics.py
  - test_e2e_agent_flows.py
  - test_api_recruitment.py (recruitment)
  - test_api_email.py (email)
  - test_compliance_tools_signatures.py (compliance)

Ejecutar suite pytest equivalente:
    cd backend && pytest tests/test_e2e_agent_flows.py -v

Este harness queda como utilidad de exploración manual rápida; **no añadir
nuevos asserts aquí** — escribirlos en `backend/tests/` con fixtures reales.

---

Invoca el grafo LangGraph compilado de cada agente directamente con prompts
acción + edge cases. Útil para detectar fallos de tools, prompts o respuestas
degradadas en agentes específicos.

Uso:
  python backend/scripts/test_agents.py                # todos
  python backend/scripts/test_agents.py --agent billing
  python backend/scripts/test_agents.py --save out.json
"""

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import os  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT.parent / ".env")

# Forzar fuera la env contaminada de Gemini si sigue presente
os.environ.pop("GEMINI_API_KEY", None)
os.environ.pop("DEFAULT_LLM_PROVIDER", None)


TENANT_ID = "9cd49fbb-355b-4b75-ad57-45ebe1c85749"
USER_ID = "0d7e5ea1-5a91-4372-8de1-8e72a2e0085b"

# (agent_name, import_path, [(label, prompt, expectation)])
AGENTS: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "billing": (
        "app.agents.billing",
        [
            ("happy_list", "Lista todas las facturas pendientes", "tool_call_listed"),
            ("happy_create", "Crea una factura de 100 EUR para el cliente Tech Solutions", "tool_call_or_explained"),
            ("edge_unknown_client", "Crea una factura para el cliente XYZ-NO-EXISTE-12345", "graceful_error"),
        ],
    ),
    "hr": (
        "app.agents.hr",
        [
            ("happy_list", "Lista todos los empleados", "tool_call_listed"),
            ("happy_payroll", "Calcula la nómina de marzo para Juan Pérez", "tool_call_or_explained"),
            ("edge_no_employee", "Calcula nómina del empleado Inexistente Apellido Falso", "graceful_error"),
        ],
    ),
    "crm": (
        "app.agents.crm",
        [
            ("happy_list", "Lista las oportunidades del trimestre", "tool_call_listed"),
            ("happy_qualify", "Califica los leads pendientes", "tool_call_or_explained"),
            ("edge_empty", "qualify", "graceful_or_clarify"),
        ],
    ),
    "banking": (
        "app.agents.banking",
        [
            ("happy_list", "Lista las transacciones del último mes", "tool_call_listed"),
            ("happy_summary", "Dame un resumen financiero", "tool_call_or_explained"),
            ("edge_concile", "Concilia con datos vacíos", "graceful_error"),
        ],
    ),
    "compliance": (
        "app.agents.compliance",
        [
            ("happy_deadlines", "¿Qué plazos fiscales hay este mes?", "tool_call_or_explained"),
            ("happy_query", "¿Cuándo se presenta el modelo 303?", "tool_call_or_explained"),
            ("edge_unknown_model", "¿Cuándo se presenta el modelo 9999?", "graceful_clarify"),
        ],
    ),
    "documents": (
        "app.agents.documents",
        [
            ("happy_search", "Busca documentos sobre garantías", "tool_call_or_explained"),
            ("happy_classify", "Clasifica los documentos pendientes en su carpeta correspondiente", "tool_call_or_explained"),
            ("edge_empty", "", "graceful_clarify"),
        ],
    ),
}


def _initial_state(prompt: str) -> dict:
    # IMPORTANTE: messages debe venir VACÍO para que el agente inyecte su
    # SystemMessage (con tenant_id, fecha, etc.) en el primer paso. Si pasamos
    # messages con HumanMessage ya, el agente salta la init y el LLM no recibe
    # contexto del tenant — terminará pidiéndolo al usuario.
    return {
        "tenant_id": TENANT_ID,
        "task_id": str(uuid.uuid4()),
        "user_id": USER_ID,
        "user_intent": prompt,
        "current_intent": prompt,
        "messages": [],
        "agent_results": [],
        "status": "running",
    }


def _extract_tools_called(messages: list) -> list[str]:
    tools = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
                if name:
                    tools.append(name)
    return tools


def _extract_final_response(messages: list) -> str:
    for msg in reversed(messages):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content.strip()
    return ""


async def _run_one(agent_name: str, label: str, prompt: str, graph, timeout: float) -> dict:
    state = _initial_state(prompt)
    started = time.perf_counter()
    error = None
    final_state: dict = {}
    try:
        final_state = await asyncio.wait_for(graph.ainvoke(state), timeout=timeout)
    except TimeoutError:
        error = f"TIMEOUT >{timeout}s"
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
    elapsed = time.perf_counter() - started

    messages = final_state.get("messages") or []
    tools_called = _extract_tools_called(messages)
    response = _extract_final_response(messages)

    return {
        "agent": agent_name,
        "label": label,
        "prompt": prompt[:80] + ("..." if len(prompt) > 80 else ""),
        "elapsed_s": round(elapsed, 2),
        "error": error,
        "tools_called": tools_called,
        "response_preview": response[:160],
        "n_messages": len(messages),
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", help="Filtra un agente concreto")
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--save", help="Path JSON de salida")
    args = parser.parse_args()

    targets = AGENTS
    if args.agent:
        targets = {args.agent: AGENTS[args.agent]} if args.agent in AGENTS else {}
    if not targets:
        print("Sin agente que coincida.")
        return

    results: list[dict] = []
    total = sum(len(cases) for _, cases in targets.values())
    counter = 0
    for agent_name, (import_path, cases) in targets.items():
        try:
            mod = __import__(import_path, fromlist=["graph"])
            graph = getattr(mod, "graph")
        except Exception as e:
            print(f"[{agent_name}] FAIL al importar: {e}")
            for label, prompt, _ in cases:
                results.append({
                    "agent": agent_name, "label": label, "prompt": prompt[:80],
                    "elapsed_s": 0, "error": f"IMPORT_FAIL: {e}",
                    "tools_called": [], "response_preview": "", "n_messages": 0,
                })
            continue

        for label, prompt, _expect in cases:
            counter += 1
            print(f"[{counter}/{total}] {agent_name} :: {label} :: {prompt[:60]}")
            r = await _run_one(agent_name, label, prompt, graph, args.timeout)
            results.append(r)
            flag = "FAIL" if r["error"] else "OK  "
            print(
                f"  [{flag}] {r['elapsed_s']:>5}s  tools={r['tools_called']}  "
                f"err={(r['error'] or '')[:50]}"
            )
            if r["response_preview"]:
                print(f"        → {r['response_preview']}")
            print()

    # Resumen por agente
    print("=" * 90)
    print("RESUMEN POR AGENTE")
    print("=" * 90)
    by_agent: dict[str, list[dict]] = {}
    for r in results:
        by_agent.setdefault(r["agent"], []).append(r)
    for agent, rs in by_agent.items():
        ok = sum(1 for r in rs if not r["error"] and (r["tools_called"] or r["response_preview"]))
        print(f"  {agent:<14} {ok}/{len(rs)}  tools_used_avg={sum(len(r['tools_called']) for r in rs) / len(rs):.1f}")
        for r in rs:
            if r["error"]:
                print(f"      └─ FAIL [{r['label']}]: {r['error'][:80]}")
            elif not r["tools_called"] and not r["response_preview"]:
                print(f"      └─ EMPTY [{r['label']}]: sin tools ni respuesta")

    if args.save:
        Path(args.save).write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        print(f"\nGuardado en {args.save}")


if __name__ == "__main__":
    asyncio.run(main())
