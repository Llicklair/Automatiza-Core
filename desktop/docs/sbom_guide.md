# SBOM CycloneDX — guía operacional (DIS.SBOM)

> **Versión 1.0 — 2026-05-15**.

Un **SBOM** (Software Bill of Materials) es el inventario de todas las
dependencias que componen una versión publicada del software. Clientes
B2B sofisticados (gestorías corporate, asesorías grandes) lo piden cada
vez más en RFPs. El gobierno federal de EE.UU. lo exige desde 2024 a
sus proveedores; en UE viene en marcha con la Cyber Resilience Act.

AutomatizaCore emite un SBOM CycloneDX 1.5 por cada release publicado.

## §1 Generar el SBOM

```bash
python scripts/generate_sbom.py \
    --version 1.0.0 \
    --output dist/sbom-cyclonedx-1.0.0.json
```

El script combina tres fuentes:

| Fuente | Origen | Componentes |
|---|---|---|
| Backend Python | `backend/requirements.txt` (si existe) | librerías `pkg:pypi/...` |
| Frontend | `frontend/package.json` (dependencies + devDependencies) | `pkg:npm/...` con tag `frontend` |
| Desktop | `desktop/package.json` | `pkg:npm/...` con tag `desktop` |
| Binarios embebidos | `dependencies/embedded_binaries.json` | applications con SHA-256 oficial |

El output incluye `serialNumber` único (UUID urn) por SBOM y `timestamp`
ISO-8601 en `metadata.timestamp` — auditable a posteriori.

## §2 Manifest de binarios embebidos

[`dependencies/embedded_binaries.json`](../dependencies/embedded_binaries.json)
es la fuente de verdad para los binarios de terceros que el instalador
Electron empaqueta:

- **PostgreSQL 17.0** (portable) — distribución oficial EnterpriseDB.
- **Python 3.11 embeddable** (windows-amd64) — distribución oficial python.org.
- **Electron 33** — empaquetado por electron-builder.

Cada entrada lleva:
- `name`, `version`, `platform`
- `sha256` (de la página oficial de checksums)
- `license` SPDX
- `download_url` oficial verificable

### Verificación pre-release

Antes de publicar una release, ejecutar el script de verificación
(pendiente — DIS.SIG / DIS.SBOM follow-up):

```bash
python scripts/verify_embedded_binaries.py
```

Computa SHA-256 sobre los binarios locales del build y los compara
con el manifest. Si discrepa, **bloquear el release** — significa que
un binario fue sustituido (posible compromiso de supply chain).

## §3 Integración con releases GitHub

En el workflow de release (pendiente DIS.UPD), añadir:

```yaml
- name: Generate SBOM
  run: |
    python scripts/generate_sbom.py \
      --version ${{ github.ref_name }} \
      --output dist/sbom-cyclonedx-${{ github.ref_name }}.json

- name: Attach SBOM to release
  uses: softprops/action-gh-release@v2
  with:
    files: dist/sbom-cyclonedx-*.json
```

El cliente descarga el SBOM de la sección Assets del release.

## §4 Consumo externo

Herramientas que aceptan CycloneDX 1.5 JSON:

- **Dependency-Track** (auto-host) — dashboard con CVE matching automático.
- **OSV-Scanner** (Google) — escanea contra OSV vulnerability DB.
- **GitHub Advanced Security** — importa SBOM directamente.

Para auditoría manual rápida, `jq` extrae el listado de componentes:

```bash
jq '.components[] | {name, version, scope}' sbom-cyclonedx-1.0.0.json
```

## §5 Actualización del manifest embebido

Cuando se bumpea Postgres, Python embeddable o Electron:

1. Descargar el binario nuevo de la fuente oficial.
2. Computar `sha256sum` del archivo (verificar contra la página de
   checksums oficial **del proveedor**, no del mirror).
3. Actualizar `dependencies/embedded_binaries.json` con la nueva versión + hash.
4. PR con el cambio. El test `test_generate_sbom.py::TestEmbeddedManifest`
   asegura que el manifest sigue siendo JSON válido y completo.

## §6 Política de divulgación

El SBOM se hace **público** (subido como asset del release). No revela
nada que no sea evidente al inspeccionar el binario. La transparencia
beneficia a clientes auditores; ocultar el SBOM no añade seguridad real
("security by obscurity" es un antipatrón conocido).

## §7 Tests

[`backend/tests/test_generate_sbom.py`](../backend/tests/test_generate_sbom.py) (14 tests):
- Estructura CycloneDX 1.5 conformante.
- Metadata con versión y supplier.
- Parsers de requirements.txt / package.json / embedded_binaries.json.
- Manifest de binarios versionado y completo (cada binario con sha256+license).
