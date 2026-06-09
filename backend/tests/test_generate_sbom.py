"""Tests del generador SBOM (DIS.SBOM)."""
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent.parent
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import generate_sbom  # noqa: E402


class TestBuildSbom:
    def test_estructura_cyclonedx(self):
        sbom = generate_sbom.build_sbom("1.0.0")
        assert sbom["bomFormat"] == "CycloneDX"
        assert sbom["specVersion"] == "1.5"
        assert sbom["serialNumber"].startswith("urn:uuid:")
        assert "metadata" in sbom
        assert "components" in sbom

    def test_metadata_incluye_version_y_supplier(self):
        sbom = generate_sbom.build_sbom("2.5.0")
        comp = sbom["metadata"]["component"]
        assert comp["version"] == "2.5.0"
        assert comp["name"] == "automatizacore"
        assert comp["supplier"]["name"] == "AutomatizaCore S.L."

    def test_incluye_componentes_de_distintas_fuentes(self):
        sbom = generate_sbom.build_sbom("1.0.0")
        sources = {
            p["value"]
            for c in sbom["components"]
            for p in c.get("properties", [])
            if p["name"] == "automatizacore:source"
        }
        # Esperamos al menos embedded + al menos una fuente JS (frontend/desktop).
        # `backend` puede no aparecer si requirements.txt no existe (Poetry).
        assert "embedded" in sources
        assert sources & {"frontend", "desktop"}

    def test_componentes_tienen_purl_o_hash(self):
        sbom = generate_sbom.build_sbom("1.0.0")
        for c in sbom["components"]:
            has_id = "purl" in c or "hashes" in c
            assert has_id, f"Componente sin identificador único: {c.get('name')}"

    def test_components_no_vacio(self):
        sbom = generate_sbom.build_sbom("1.0.0")
        # Como mínimo los embedded_binaries del manifest
        assert len(sbom["components"]) > 0


class TestParsers:
    def test_parse_requirements_strip_comments(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text(
            "# comment\n"
            "fastapi==0.110.0\n"
            "pydantic==2.7.0  # inline comment\n"
            "-e .\n"
            "git+https://example.com/foo\n",
            encoding="utf-8",
        )
        out = generate_sbom._parse_requirements(req)
        names = [c["name"] for c in out]
        assert "fastapi" in names
        assert "pydantic" in names
        # Líneas con -e o git+ se ignoran.
        assert len(out) == 2

    def test_parse_package_json(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({
            "dependencies": {"react": "^18.3.1", "next": "14.2"},
            "devDependencies": {"vitest": "^1.0.0"},
        }), encoding="utf-8")
        out = generate_sbom._parse_package_json(pkg, scope="test")
        names = [c["name"] for c in out]
        assert "react" in names
        assert "next" in names
        assert "vitest" in names
        # Strip de "^" en versión.
        react = next(c for c in out if c["name"] == "react")
        assert react["version"] == "18.3.1"

    def test_parse_package_json_marca_devdep_como_optional(self, tmp_path):
        pkg = tmp_path / "package.json"
        pkg.write_text(json.dumps({
            "dependencies": {"react": "18.3.1"},
            "devDependencies": {"vitest": "1.0.0"},
        }), encoding="utf-8")
        out = generate_sbom._parse_package_json(pkg, scope="test")
        react = next(c for c in out if c["name"] == "react")
        vitest = next(c for c in out if c["name"] == "vitest")
        assert react["scope"] == "required"
        assert vitest["scope"] == "optional"

    def test_parse_embedded(self, tmp_path):
        manifest = tmp_path / "embedded.json"
        manifest.write_text(json.dumps({
            "binaries": [
                {
                    "name": "postgresql",
                    "version": "17.0",
                    "sha256": "abc123",
                    "license": "PostgreSQL License",
                    "download_url": "https://example.com/pg.zip",
                },
            ],
        }), encoding="utf-8")
        out = generate_sbom._parse_embedded(manifest)
        assert len(out) == 1
        comp = out[0]
        assert comp["name"] == "postgresql"
        assert comp["hashes"][0]["alg"] == "SHA-256"
        assert comp["hashes"][0]["content"] == "abc123"
        assert comp["externalReferences"][0]["url"] == "https://example.com/pg.zip"

    def test_parse_embedded_sin_hash_omite_hashes(self, tmp_path):
        manifest = tmp_path / "embedded.json"
        manifest.write_text(json.dumps({
            "binaries": [{"name": "x", "version": "1.0", "sha256": ""}],
        }), encoding="utf-8")
        out = generate_sbom._parse_embedded(manifest)
        # sha256="" → no se añade bloque hashes
        assert "hashes" not in out[0] or not out[0].get("hashes")

    def test_parse_archivos_inexistentes_devuelven_lista_vacia(self, tmp_path):
        nope = tmp_path / "nope.json"
        assert generate_sbom._parse_requirements(nope) == []
        assert generate_sbom._parse_package_json(nope, scope="x") == []
        assert generate_sbom._parse_embedded(nope) == []


class TestEmbeddedManifest:
    """El manifest de binarios embebidos debe estar versionado y válido."""

    def test_manifest_existe(self):
        assert generate_sbom._EMBEDDED_MANIFEST.exists(), (
            "Falta dependencies/embedded_binaries.json — "
            "DIS.SBOM exige declarar los binarios embebidos del instalador."
        )

    def test_manifest_es_json_valido(self):
        data = json.loads(
            generate_sbom._EMBEDDED_MANIFEST.read_text(encoding="utf-8")
        )
        assert "binaries" in data
        assert isinstance(data["binaries"], list)

    def test_cada_binario_tiene_campos_minimos(self):
        data = json.loads(
            generate_sbom._EMBEDDED_MANIFEST.read_text(encoding="utf-8")
        )
        for b in data["binaries"]:
            for key in ("name", "version", "sha256", "license"):
                assert key in b, f"Binario {b.get('name')} sin campo `{key}`"
