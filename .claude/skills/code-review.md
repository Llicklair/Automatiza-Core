---
name: code-review
description: "Dispatch after completing a non-trivial implementation (3+ steps or architectural changes) to review before commit. NOT for simple fixes, typos, or small changes."
---

# Lightweight Code Review

## When to Use

- After completing a non-trivial task (3+ steps or architectural changes)
- When the user explicitly requests a review
- After the implementation passes verification

## When to Skip

- Trivial tasks (1-2 steps, obvious fix, config-only)
- Purely additive changes with no existing code modified
- User explicitly says to skip

## Process

1. Gather context for the reviewer subagent:
   - Original task description or plan from tasks/todo.md
   - Git diff of all changes
   - Blast radius analysis (see below)

2. **Blast Radius Detection** (choose based on available tooling):
   - **If GitNexus is available and responsive:** use `gitnexus_detect_changes()` to map changed symbols and affected execution flows
   - **If GitNexus is unavailable or unhelpful:** fall back to manual analysis:
     - `git diff --stat` to identify all changed files
     - Grep for imports/usages of modified functions/classes across the codebase
     - Trace callers of changed functions via code search
     - Check for broken references or missing imports
   - Either way, the goal is the same: identify what else in the project is affected by these changes

3. Dispatch ONE reviewer subagent with this prompt:

   > Review these changes against 3 criteria:
   > 1. **Spec Alignment** — Do changes match the plan/request? Anything missing or extra?
   > 2. **Code Quality** — Obvious bugs, edge cases, or convention violations?
   > 3. **Blast Radius** — Based on the impact analysis provided, are there unexpected affected areas?
   >
   > Return ONLY:
   > ```
   > REVIEW: [PASS | CONCERNS]
   > - [1-3 bullet findings, or "No issues found"]
   > ```

4. Critically evaluate findings — don't auto-apply everything
5. Report to user: one line if PASS, specific items if CONCERNS

## Integration Point

Fits in the workflow after verification, before commit:
```
Build -> Verify -> Review (this skill) -> Evaluate -> Commit
```
