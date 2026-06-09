"""DIS.SBOM — generador de SBOM CycloneDX unificado.

Produce un documento CycloneDX 1.5 JSON con tres bloques:

  1. Dependencias Python (backend) leídas de `backend/requirements.txt`.
  2. Dependencias npm (frontend + desktop) leídas de los `package.json`.
  3. Binarios embebidos en el instalador Electron (Postgres, Python
     portable, JRE si aplica) — listados desde
     `dependencies/embedded_binaries.json` con SHA-256 + procedencia
     oficial verificable.

Uso típico en release:
    python scripts/generate_sbom.py \
        --version 1.0.0 \
        --output dist/sbom-cyclonedx-1.0.0.json

El archivo se incluye en cada release publicado en GitHub Releases —
permite auditoría de supply chain por clientes B2B/gestorías que
piden SBOM (cada vez más habitual en RFPs).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).parent.parent

# Localización de los manifests de dependencias.
_BACKEND_REQUIREMENTS = _ROOT / "backend" / "requirements.txt"
_FRONTEND_PKG = _ROOT / "frontend" / "package.json"
_DESKTOP_PKG = _ROOT / "desktop" / "package.json"
_EMBEDDED_MANIFEST = _ROOT / "dependencies" / "embedded_binaries.json"


def _parse_requirements(path: Path) -> list[dict]:
    """Parser sencillo de requirements.txt → componentes CycloneDX."""
    if not path.exists():
        return []
    components: list[dict] = []
    line_re = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([^\s;#]+)")
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-") or line.startswith("git+"):
            continue
        m = line_re.match(line)
        if not m:
            continue
        name, version = m.group(1).lower(), m.group(2)
        components.append({
            "type": "library",
            "bom-ref": f"pkg:pypi/{name}@{version}",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name}@{version}",
            "scope": "required",
            "properties": [{"name": "automatizacore:source", "value": "backend"}],
        })
    return components


def _parse_package_json(path: Path, scope: str) -> list[dict]:
    """Lee dependencies + devDependencies → componentes CycloneDX."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict] = []
    for section in ("dependencies", "devDependencies"):
        for name, raw_version in (data.get(section) or {}).items():
            # Strip prefijos ^/~/>= y rangos.
            version = re.sub(r"^[~^>=<]+", "", raw_version)
            version = re.split(r"[\s|]", version)[0] if version else "unknown"
            scope_value = "required" if section == "dependencies" else "optional"
            # CycloneDX no usa "dev" como scope, pero podemos taggearlo.
            out.append({
                "type": "library",
                "bom-ref": f"pkg:npm/{name}@{version}#{scope}",
                "name": name,
                "version": version,
                "purl": f"pkg:npm/{name}@{version}",
                "scope": scope_value,
                "properties": [
                    {"name": "automatizacore:source", "value": scope},
                    {"name": "automatizacore:section", "value": section},
                ],
            })
    return out


def _parse_embedded(path: Path) -> list[dict]:
    """Binarios embebidos (Postgres, Python portable, JRE) con hash."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict] = []
    for entry in data.get("binaries", []):
        comp = {
            "type": "application",
            "bom-ref": f"binary:{entry['name']}@{entry['version']}",
            "name": entry["name"],
            "version": entry["version"],
            "scope": "required",
            "properties": [
                {"name": "automatizacore:source", "value": "embedded"},
                {"name": "automatizacore:license", "value": entry.get("license", "unknown")},
            ],
        }
        if entry.get("sha256"):
            comp["hashes"] = [{"alg": "SHA-256", "content": entry["sha256"]}]
        if entry.get("download_url"):
            comp["externalReferences"] = [
                {"type": "distribution", "url": entry["download_url"]},
            ]
        out.append(comp)
    return out


def build_sbom(version: str) -> dict:
    """Construye el documento CycloneDX 1.5."""
    components: list[dict] = []
    components.extend(_parse_requirements(_BACKEND_REQUIREMENTS))
    components.extend(_parse_package_json(_FRONTEND_PKG, "frontend"))
    components.extend(_parse_package_json(_DESKTOP_PKG, "desktop"))
    components.extend(_parse_embedded(_EMBEDDED_MANIFEST))

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{uuid.uuid4()}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "tools": [{
                "vendor": "AutomatizaCore",
                "name": "generate_sbom.py",
                "version": "1.0.0",
            }],
            "component": {
                "type": "application",
                "bom-ref": f"automatizacore@{version}",
                "name": "automatizacore",
                "version": version,
                "supplier": {"name": "AutomatizaCore S.L."},
            },
        },
        "components": components,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DIS.SBOM — generador SBOM CycloneDX")
    parser.add_argument("--version", required=True, help="Versión del release (ej. 1.0.0)")
    parser.add_argument("--output", required=True, type=Path, help="Ruta del JSON output")
    args = parser.parse_args()

    sbom = build_sbom(args.version)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(sbom, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"SBOM generado: {args.output}\n"
        f"  components total: {len(sbom['components'])}\n"
        f"  hash sha256:    {hashlib.sha256(args.output.read_bytes()).hexdigest()}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
