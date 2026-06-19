# AutomatizaCore — Project Rules

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

### Naming: "orchestrator" vs "coordinator"
The README uses two conceptual layers — **Orquestador** (top, persistent
workflows + scheduler) and **Coordinador** (middle, one-shot instruction
decomposition). In the code, the **Orquestador layer lives in
`services/workflow/`** (parse-nl, scheduler, executions) and the
**Coordinador layer lives in `agents/orchestrator/`**. Yes, the directory
name `orchestrator` matches the *other* concept — it predates the README's
naming and a 200+ occurrence rename was deemed not worth the risk. When
reading code, treat `agents/orchestrator/` as "Coordinador" and
`services/workflow/` as "Orquestador".

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

This project is indexed by GitNexus as **Automatiza-pyme-main** (11042 symbols, 30405 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

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
3. `READ gitnexus://repo/Automatiza-pyme-main/process/{processName}` — trace the full execution flow step by step
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
| `gitnexus://repo/Automatiza-pyme-main/context` | Codebase overview, check index freshness |
| `gitnexus://repo/Automatiza-pyme-main/clusters` | All functional areas |
| `gitnexus://repo/Automatiza-pyme-main/processes` | All execution flows |
| `gitnexus://repo/Automatiza-pyme-main/process/{name}` | Step-by-step execution trace |

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

# context-mode — MANDATORY routing rules

You have context-mode MCP tools available. These rules are NOT optional — they protect your context window from flooding. A single unrouted command can dump 56 KB into context and waste the entire session.

## BLOCKED commands — do NOT attempt these

### curl / wget — BLOCKED
Any Bash command containing `curl` or `wget` is intercepted and replaced with an error message. Do NOT retry.
Instead use:
- `ctx_fetch_and_index(url, source)` to fetch and index web pages
- `ctx_execute(language: "javascript", code: "const r = await fetch(...)")` to run HTTP calls in sandbox

### Inline HTTP — BLOCKED
Any Bash command containing `fetch('http`, `requests.get(`, `requests.post(`, `http.get(`, or `http.request(` is intercepted and replaced with an error message. Do NOT retry with Bash.
Instead use:
- `ctx_execute(language, code)` to run HTTP calls in sandbox — only stdout enters context

### WebFetch — BLOCKED
WebFetch calls are denied entirely. The URL is extracted and you are told to use `ctx_fetch_and_index` instead.
Instead use:
- `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` to query the indexed content

## REDIRECTED tools — use sandbox equivalents

### Bash (>20 lines output)
Bash is ONLY for: `git`, `mkdir`, `rm`, `mv`, `cd`, `ls`, `npm install`, `pip install`, and other short-output commands.
For everything else, use:
- `ctx_batch_execute(commands, queries)` — run multiple commands + search in ONE call
- `ctx_execute(language: "shell", code: "...")` — run in sandbox, only stdout enters context

### Read (for analysis)
If you are reading a file to **Edit** it → Read is correct (Edit needs content in context).
If you are reading to **analyze, explore, or summarize** → use `ctx_execute_file(path, language, code)` instead. Only your printed summary enters context. The raw file content stays in the sandbox.

### Grep (large results)
Grep results can flood context. Use `ctx_execute(language: "shell", code: "grep ...")` to run searches in sandbox. Only your printed summary enters context.

## Tool selection hierarchy

1. **GATHER**: `ctx_batch_execute(commands, queries)` — Primary tool. Runs all commands, auto-indexes output, returns search results. ONE call replaces 30+ individual calls.
2. **FOLLOW-UP**: `ctx_search(queries: ["q1", "q2", ...])` — Query indexed content. Pass ALL questions as array in ONE call.
3. **PROCESSING**: `ctx_execute(language, code)` | `ctx_execute_file(path, language, code)` — Sandbox execution. Only stdout enters context.
4. **WEB**: `ctx_fetch_and_index(url, source)` then `ctx_search(queries)` — Fetch, chunk, index, query. Raw HTML never enters context.
5. **INDEX**: `ctx_index(content, source)` — Store content in FTS5 knowledge base for later search.

## Subagent routing

When spawning subagents (Agent/Task tool), the routing block is automatically injected into their prompt. Bash-type subagents are upgraded to general-purpose so they have access to MCP tools. You do NOT need to manually instruct subagents about context-mode.

## Output constraints

- Keep responses under 500 words.
- Write artifacts (code, configs, PRDs) to FILES — never return them as inline text. Return only: file path + 1-line description.
- When indexing content, use descriptive source labels so others can `ctx_search(source: "label")` later.

## ctx commands

| Command | Action |
|---------|--------|
| `ctx stats` | Call the `ctx_stats` MCP tool and display the full output verbatim |
| `ctx doctor` | Call the `ctx_doctor` MCP tool, run the returned shell command, display as checklist |
| `ctx upgrade` | Call the `ctx_upgrade` MCP tool, run the returned shell command, display as checklist |
