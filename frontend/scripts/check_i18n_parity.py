"""Gate de paridad i18n: es.json y en.json deben tener EXACTAMENTE las mismas claves.

Uso: python frontend/scripts/check_i18n_parity.py  (exit 1 si hay divergencia)
"""

import json
import sys
from pathlib import Path

MESSAGES = Path(__file__).resolve().parent.parent / "src" / "messages"


def flat(d: dict, prefix: str = "") -> set[str]:
    out: set[str] = set()
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out |= flat(v, key)
        else:
            out.add(key)
    return out


def main() -> int:
    es = flat(json.loads((MESSAGES / "es.json").read_text(encoding="utf-8")))
    en = flat(json.loads((MESSAGES / "en.json").read_text(encoding="utf-8")))
    only_es = sorted(es - en)
    only_en = sorted(en - es)
    if only_es or only_en:
        print(f"i18n parity ROTA: es={len(es)} en={len(en)}")
        for k in only_es[:20]:
            print(f"  solo-es: {k}")
        for k in only_en[:20]:
            print(f"  solo-en: {k}")
        return 1
    print(f"i18n parity OK: {len(es)} claves en ambos idiomas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
