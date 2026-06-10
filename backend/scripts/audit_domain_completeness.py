"""Audit de exhaustividad del Coordinador.

Cruza los 4 puntos de sincronización del routing y falla con exit code 1
si hay asimetría no documentada como excepción legítima.

Puntos cruzados:
  - VALID_DOMAINS         (state.py)            — dominios reconocidos como destino
  - DISPATCHER_MAP        (dispatchers/__init__) — agente → función dispatcher
  - _KEYWORD_MAP          (classifier.py)        — keywords débiles por dominio
  - _STRONG_KEYWORDS      (classifier.py)        — keywords fuertes (clasif. directa)

Excepciones legítimas declaradas explícitamente:
  - VALID sin DISPATCHER:    {coordinator, custom}
        coordinator es el propio agente; custom se enruta en _dispatch_handlers.py
  - VALID sin _KEYWORD_MAP:  {custom, skill}
        meta-routings programáticos (no por palabras clave del usuario)
  - VALID sin _STRONG_KEYWORDS: {chat, coordinator, custom, skill}
        meta-dominios sin clasificación directa por keywords fuertes

Uso:
  python backend/scripts/audit_domain_completeness.py
  # exit 0 = sync limpio, exit 1 = asimetría no documentada
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "agents" / "orchestrator"

EXPECTED_VALID_WITHOUT_DISPATCHER = {"coordinator", "custom"}
EXPECTED_VALID_WITHOUT_KEYWORD = {"custom", "skill"}
EXPECTED_VALID_WITHOUT_STRONG = {"chat", "coordinator", "custom", "skill"}


def _extract_set_literal(src: str, name: str) -> set[str]:
    m = re.search(rf"{name}\s*=\s*\{{([^}}]+)\}}", src, re.DOTALL)
    if not m:
        return set()
    return set(re.findall(r'"(\w+)"', m.group(1)))


def _extract_dispatcher_keys(src: str) -> set[str]:
    m = re.search(r"DISPATCHER_MAP\s*=\s*\{(.+?)\n\}", src, re.DOTALL)
    if not m:
        return set()
    return set(re.findall(r'"(\w+)":\s*_dispatch_', m.group(1)))


def _extract_dict_keys(src: str, name: str) -> set[str]:
    m = re.search(rf"{name}[^=]*=\s*\{{([\s\S]+?)\n\}}", src)
    if not m:
        return set()
    return set(re.findall(r'^\s*"(\w+)":\s*\[', m.group(1), re.MULTILINE))


def main() -> int:
    state_src = (ROOT / "state.py").read_text(encoding="utf-8")
    disp_src = (ROOT / "dispatchers" / "__init__.py").read_text(encoding="utf-8")
    classif_src = (ROOT / "classifier_data.py").read_text(encoding="utf-8")

    valid = _extract_set_literal(state_src, "VALID_DOMAINS")
    dispatchers = _extract_dispatcher_keys(disp_src)
    keywords = _extract_dict_keys(classif_src, "_KEYWORD_MAP")
    strong = _extract_dict_keys(classif_src, "_STRONG_KEYWORDS")

    print(f"VALID_DOMAINS    ({len(valid):2}): {sorted(valid)}")
    print(f"DISPATCHER_MAP   ({len(dispatchers):2}): {sorted(dispatchers)}")
    print(f"_KEYWORD_MAP     ({len(keywords):2}): {sorted(keywords)}")
    print(f"_STRONG_KEYWORDS ({len(strong):2}): {sorted(strong)}")

    issues: list[str] = []

    unexpected = (valid - dispatchers) - EXPECTED_VALID_WITHOUT_DISPATCHER
    if unexpected:
        issues.append(f"VALID sin DISPATCHER (no esperado): {sorted(unexpected)}")

    bad_dispatcher = dispatchers - valid
    if bad_dispatcher:
        issues.append(f"DISPATCHER sin VALID (dominio inalcanzable): {sorted(bad_dispatcher)}")

    unexpected_kw = (valid - keywords) - EXPECTED_VALID_WITHOUT_KEYWORD
    if unexpected_kw:
        issues.append(f"VALID sin _KEYWORD_MAP (clasif. ciego): {sorted(unexpected_kw)}")

    unexpected_strong = (valid - strong) - EXPECTED_VALID_WITHOUT_STRONG
    if unexpected_strong:
        issues.append(f"VALID sin _STRONG_KEYWORDS (no esperado): {sorted(unexpected_strong)}")

    junk_kw = keywords - valid
    if junk_kw:
        issues.append(f"_KEYWORD_MAP sin VALID (basura): {sorted(junk_kw)}")

    junk_strong = strong - valid
    if junk_strong:
        issues.append(f"_STRONG_KEYWORDS sin VALID (basura): {sorted(junk_strong)}")

    print()
    if issues:
        print("ASIMETRIAS DETECTADAS:")
        for i in issues:
            print(f"  - {i}")
        return 1

    print("OK: sync limpio entre VALID_DOMAINS / DISPATCHER_MAP / _KEYWORD_MAP / _STRONG_KEYWORDS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
