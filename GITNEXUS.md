# GitNexus — Full Reference

Indexed as **atomatizacion de empresas** (2464 symbols, 6270 relationships, 193 execution flows).

> If any tool warns the index is stale, run `npx gitnexus analyze` first.

## Tools

| Tool | Use | Example |
|------|-----|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360° view of a symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers | MUST update |
| d=2 | LIKELY AFFECTED — indirect | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Workflows

**Debugging**: query → context → read process resource → detect_changes (for regressions)

**Refactoring**: context + impact → make changes → detect_changes to verify scope

**Renaming**: gitnexus_rename with dry_run:true first, review, then dry_run:false

## Resources

- `gitnexus://repo/atomatizacion de empresas/context` — overview + freshness
- `gitnexus://repo/atomatizacion de empresas/clusters` — functional areas
- `gitnexus://repo/atomatizacion de empresas/processes` — execution flows
- `gitnexus://repo/atomatizacion de empresas/process/{name}` — step-by-step trace

## CLI

- `npx gitnexus analyze` — re-index
- `npx gitnexus status` — check freshness
- `npx gitnexus wiki` — generate docs
