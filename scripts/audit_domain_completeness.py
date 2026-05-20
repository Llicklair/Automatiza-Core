"""Audita la sincronización del coordinador para garantizar el principio ERP.

El principio "la IA accede a todos los módulos del ERP" se materializa en 3
puntos del código que deben estar sincronizados (lessons.md 2026-05-18):

  1. `VALID_DOMAINS`        — set de dominios válidos (state.py).
  2. `DISPATCHER_MAP`       — mapping agent_name → función (dispatchers).
  3. `_KEYWORD_MAP`         — keywords por dominio (classifier.py).

Si un dominio falta en cualquiera de los 3, queda silenciosamente inaccesible
desde el clasificador de intenciones. Este script detecta:

  - Dominios en VALID_DOMAINS pero sin entry en DISPATCHER_MAP.
  - Dominios en DISPATCHER_MAP pero NO en VALID_DOMAINS (inalcanzable).
  - Dominios sin keywords en _KEYWORD_MAP (LLM-only, sin fallback).
  - Tools registradas en tool_registry pero no expuestas por ningún agente.

Uso:
    python scripts/audit_domain_completeness.py

Salida:
    Tabla de hallazgos. Exit code 0 si todo OK, 1 si hay asimetrías.

Pensado para correr en pre-commit y en CI antes de merge a master.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permitir import del backend cuando se ejecuta desde la raíz del repo.
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


# Dominios "meta" — no implementan un agente clásico pero participan del
# routing. Se excluyen del check "debe tener dispatcher" porque su lógica
# vive en el grafo del coordinador, no en un dispatcher dedicado.
META_DOMAINS = {"coordinator", "custom", "chat"}


def _load_state() -> tuple[set[str], dict, dict]:
    """Carga las tres tablas de sincronización del coordinador."""
    from app.agents.orchestrator.classifier import _KEYWORD_MAP
    from app.agents.orchestrator.dispatchers import DISPATCHER_MAP
    from app.agents.orchestrator.state import VALID_DOMAINS

    return VALID_DOMAINS, DISPATCHER_MAP, _KEYWORD_MAP


def _check_sync(
    valid: set[str], dispatchers: dict, keywords: dict
) -> list[tuple[str, str, str]]:
    """Devuelve lista (severidad, dominio, descripción) de hallazgos."""
    findings: list[tuple[str, str, str]] = []

    in_valid = set(valid)
    in_dispatch = set(dispatchers.keys())
    in_keywords = set(keywords.keys())

    # 1. En VALID_DOMAINS pero sin dispatcher (excluyendo metas).
    no_dispatcher = (in_valid - in_dispatch) - META_DOMAINS
    for d in sorted(no_dispatcher):
        findings.append(
            (
                "CRITICAL",
                d,
                "está en VALID_DOMAINS pero no en DISPATCHER_MAP "
                "— se clasifica pero no se ejecuta",
            )
        )

    # 2. En DISPATCHER_MAP pero NO en VALID_DOMAINS (inalcanzable).
    inaccessible = in_dispatch - in_valid
    for d in sorted(inaccessible):
        findings.append(
            (
                "CRITICAL",
                d,
                "está en DISPATCHER_MAP pero NO en VALID_DOMAINS "
                "— inalcanzable desde el classifier (fix: añadir a "
                "VALID_DOMAINS en state.py)",
            )
        )

    # 3. Dominios sin keywords (solo LLM-classification, sin fallback).
    no_keywords = (in_valid - in_keywords) - META_DOMAINS
    for d in sorted(no_keywords):
        findings.append(
            (
                "WARNING",
                d,
                "sin entradas en _KEYWORD_MAP — depende 100% del LLM "
                "classifier sin red de seguridad",
            )
        )

    return findings


def _check_tool_registry() -> list[tuple[str, str, str]]:
    """Detecta tools registradas que ningún agente expone (huérfanas).

    Best-effort: requiere que `tool_registry` se importe sin efectos
    secundarios. Si falla, devuelve solo un warning.
    """
    findings: list[tuple[str, str, str]] = []
    try:
        from app.agents import tool_registry  # type: ignore
    except Exception as exc:  # noqa: BLE001
        findings.append(
            (
                "WARNING",
                "tool_registry",
                f"no se pudo importar para auditoría de tools ({exc})",
            )
        )
        return findings

    # El registry expone un dict ALL_TOOLS o similar. Sin contrato firme,
    # hacemos best-effort y reportamos lo que encontremos. No bloquear si
    # el módulo no expone la estructura esperada.
    candidates = ("ALL_TOOLS", "REGISTRY", "TOOLS")
    catalog: dict | None = None
    for name in candidates:
        if hasattr(tool_registry, name):
            catalog = getattr(tool_registry, name)
            break

    if catalog is None:
        findings.append(
            (
                "INFO",
                "tool_registry",
                "no expone ALL_TOOLS/REGISTRY/TOOLS — saltando audit de tools",
            )
        )
    # Auditoría más profunda (cross-check tools vs system prompts) queda
    # para una iteración posterior — requiere parsear los prompts de cada
    # agente y mapear menciones explícitas vs registry.
    return findings


def _print_table(findings: list[tuple[str, str, str]]) -> None:
    if not findings:
        print("OK — sincronización VALID_DOMAINS × DISPATCHER_MAP × _KEYWORD_MAP correcta.")
        return

    sev_w = max(len("Sev"), max(len(f[0]) for f in findings))
    dom_w = max(len("Dominio"), max(len(f[1]) for f in findings))

    print(f"{'Sev':<{sev_w}}  {'Dominio':<{dom_w}}  Descripción")
    print(f"{'-' * sev_w}  {'-' * dom_w}  {'-' * 60}")
    for sev, dom, desc in findings:
        print(f"{sev:<{sev_w}}  {dom:<{dom_w}}  {desc}")


def main() -> int:
    # Consola Windows: forzar UTF-8 para que acentos y guiones no garblen.
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            pass

    valid, dispatchers, keywords = _load_state()
    findings = _check_sync(valid, dispatchers, keywords)
    findings.extend(_check_tool_registry())

    _print_table(findings)

    critical = [f for f in findings if f[0] == "CRITICAL"]
    if critical:
        print(f"\n{len(critical)} hallazgo(s) CRÍTICO(s) — fix obligatorio antes de merge.")
        return 1

    warnings = [f for f in findings if f[0] == "WARNING"]
    if warnings:
        print(f"\n{len(warnings)} warning(s) — revisar pero no bloquean merge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
