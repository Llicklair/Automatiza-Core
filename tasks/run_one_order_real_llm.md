# Run ONE order E2E with the REAL Claude Code LLM (Windows, no API key)

Proven 2026-06-23. Uses the desktop app's bundled Python + local `claude` CLI.
No API key needed — the `claude_code` provider shells out to the local Claude
Code CLI (subscription session).

## Interpreter (has all backend deps)
`C:\Users\Marcos\AppData\Roaming\AutomatizaPyme\python\python.exe`
(has langchain_core, langgraph, fastapi, sqlalchemy, asyncpg, anthropic, etc.
NOTE: the umbrella `langchain` package is NOT installed — backend only needs
`langchain_core` / `langgraph`, so that's fine.)

## Safe tenant in THIS DB (PG :5433) — use Demo Masivo, never the real fiscal tenant
- TENANT_ID = c505879e-953a-45af-b3f9-7688e67d4a35  (name: "Demo Masivo")
- USER_ID   = fc029d3e-4ef4-49ed-b04a-fc9837a4c726  (demo.masivo@automatizacore.com)
(The smoke script's hardcoded TENANT_ID 9cd49fbb-... does NOT exist in this DB —
it FK-violates. Always override with a tenant that exists here.)

## TWO blockers the raw smoke script hits (and the fixes baked in below)
1. RLS fail-closed: must call `set_current_tenant(TENANT_ID)` BEFORE the first
   DB write (`_create_task_row`). The stock script sets it too late -> RLS
   InsufficientPrivilege on INSERT into tasks.
2. Tenant must EXIST in this DB -> use the Demo Masivo ids above.

## Recipe — change only PROMPT to run any single order

```bash
DESKPY="/c/Users/Marcos/AppData/Roaming/AutomatizaPyme/python/python.exe"
"$DESKPY" - <<'PY'
import sys, os, asyncio, warnings, time, json
warnings.filterwarnings("ignore")
ROOT = r"C:\Users\Marcos\Desktop\automatizacion de empresas\Automatiza-pyme-main\backend"
sys.path.insert(0, ROOT)
os.environ.pop("ENVIRONMENT", None)          # NOT 'testing' -> real claude_code (NOT MockChatModel)
from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "..", ".env"))
from unittest.mock import patch
from app.core.tenant_context import set_current_tenant, set_current_task

TENANT_ID = "c505879e-953a-45af-b3f9-7688e67d4a35"   # Demo Masivo (safe)
USER_ID   = "fc029d3e-4ef4-49ed-b04a-fc9837a4c726"
PROMPT    = "Dame el resumen contable del mes pasado"  # <-- EDIT THIS

async def main():
    set_current_tenant(TENANT_ID)            # FIX 1: tenant BEFORE any write
    with patch("app.services.email.sender.send_email", side_effect=lambda *a,**k:{"success":True}):
        import scripts.smoke_orchestrator as S
        S.TENANT_ID, S.USER_ID = TENANT_ID, USER_ID
        from app.agents.orchestrator import orchestrator
        from app.core.llm_factory import get_llm
        print("LLM:", type(get_llm()).__name__)     # -> ClaudeCodeChatModel
        tid = await S._create_task_row(PROMPT)
        st = S._initial_state(PROMPT, tid); set_current_task(tid)
        t0 = time.time(); final = await orchestrator.ainvoke(st)
        print("elapsed", round(time.time()-t0,1), "status", final.get("status"),
              "domain", final.get("classified_domain"))
        for r in final.get("agent_results") or []:
            print(json.dumps(r if isinstance(r,dict) else r.__dict__, ensure_ascii=False, default=str)[:600])
asyncio.run(main())
PY
```

## Verified result (read-only "Dame el resumen contable del mes pasado")
- LLM: ClaudeCodeChatModel (real `claude -p`, ~9s, real token usage)
- status DONE, domain `report`, 2 agent_results both success
- report agent read real data: facturado 267,417.99 €, 16 empleados, 72 mov. banco;
  generated benign PDF informe_2026-05_*.pdf. No fiscal series consumed, no invoice created.
