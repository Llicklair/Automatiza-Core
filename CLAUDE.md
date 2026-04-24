# AutomatizaPyme — Project Rules

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.
- **Optimize Tokens Consumption and Context Window**: Reduce tokens consumption and context window cluttering as possible without losing accuracy and effectiveness.

---

## Workflow Orchestration

- **Plan first**: Enter plan mode for non-trivial tasks (3+ steps). If vague, ask 1-3 clarifying questions BEFORE planning. If something goes sideways, STOP and re-plan.
- **Subagents**: Use liberally to keep main context clean. One task per subagent.
- **Self-improvement**: After ANY correction → update `tasks/lessons.md` with the pattern and prevention rule.
- **Verify before done**: Prove it works — run tests, check logs, diff behavior. "Would a staff engineer approve this?"
- **Elegance (balanced)**: For non-trivial changes, pause and consider a more elegant way. Skip for simple fixes.
- **Autonomous bugs**: Just fix them. Don't ask for hand-holding. Zero context switching from user.
- **Critical evaluation**: Don't blindly accept suggestions. Understand the WHY before applying corrections.

---

## Task Management

Plan → `tasks/todo.md` | Lessons → `tasks/lessons.md` | Track progress as you go.

---

## Architecture Rules (enforced — see ARCHITECTURE.md for full details)

### Layer boundaries
- **Routes** (`api/v1/routes/`): validate input + return HTTP. ZERO business logic. Delegate to services or agents.
- **Services** (`services/`): reusable business logic that doesn't belong to an agent. Receive `db: AsyncSession` as param.
- **Agents** (`agents/<domain>/`): all AI lives here. Only public export is `run_agent()`.
- **DB Models** (`db/models/`): SQLAlchemy ORM only. No business logic in models.

### Agent structure (mandatory)
```
agents/<domain>/
├── __init__.py       ← exports only: run_agent()
├── agent.py          ← LangGraph graph + run_agent()
├── tools.py          ← @tool + docstring (declared to LLM)
├── prompts.py        ← system prompt strings, no logic
└── _*.py             ← private implementation (never import from outside)
```

### Frontend rules
- Components NEVER call `fetch()` directly — always use `lib/api/*.ts`
- `lib/api/client.ts` is the single HTTP base (handles JWT, 401 refresh, errors)
- Each domain has its API module: `billing.ts`, `hr.ts`, `documents.ts`, etc.
- For file uploads use `requestUpload()` from client.ts (not raw fetch)

### Agent communication
- Agents NEVER import other agents. Communication goes through the orchestrator or shared services.
- Agents return `AgentResult(success=False)` on errors, never throw exceptions to the orchestrator.

### Commit discipline
- Descriptive commit messages (no more "test N"). Format: `type: short description`
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- Run `tsc --noEmit` (frontend) before committing TS changes

---

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **atomatizacion de empresas** (4028 symbols, 10461 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/atomatizacion de empresas/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/atomatizacion de empresas/context` | Codebase overview, check index freshness |
| `gitnexus://repo/atomatizacion de empresas/clusters` | All functional areas |
| `gitnexus://repo/atomatizacion de empresas/processes` | All execution flows |
| `gitnexus://repo/atomatizacion de empresas/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## CLI

- Re-index: `npx gitnexus analyze`
- Check freshness: `npx gitnexus status`
- Generate docs: `npx gitnexus wiki`

<!-- gitnexus:end -->
