# Seguridad de dependencias — DIS.DEP

> Política de gestión de dependencias para minimizar superficie de ataque vía supply chain (incidentes tipo Log4Shell, event-stream, ua-parser-js, etc.).

## §1 Escaneo automático — Dependabot

Configurado en `.github/dependabot.yml`. Cubre:

| Ecosistema | Path | Frecuencia | PRs máx |
|---|---|---|---|
| `pip` | `/backend` | semanal (lunes 06:00 CET) | 5 |
| `npm` | `/frontend` | semanal (lunes 06:00 CET) | 5 |
| `npm` | `/desktop` | semanal (lunes 06:00 CET) | 3 |
| `github-actions` | `/` | mensual | sin límite |

PRs agrupados por `minor` y `patch` para reducir ruido. Actualizaciones `major` se proponen individualmente para revisión humana.

## §2 SCA en CI — OSV-Scanner

**TODO Sprint 8**: añadir step a `ci.yml` que ejecute `osv-scanner` sobre `requirements.txt`, `package-lock.json` (frontend), `package-lock.json` (desktop). PR bloqueado si hay vulnerabilidad **HIGH** o **CRITICAL** sin excepción documentada.

Ejemplo de step:

```yaml
- name: OSV-Scanner
  uses: google/osv-scanner-action/osv-scanner-action@v1.9.0
  with:
    scan-args: |-
      --recursive
      ./backend
      ./frontend
      ./desktop
```

## §3 Política de versiones

### Pinning

* **`backend/requirements.txt`** usa `>=` actualmente — admite minor/patch flotantes. **TODO Sprint 8**: migrar a `requirements.lock` con `pip-compile` para reproducibilidad bit-a-bit en CI y en el instalador Electron.
* **`frontend/package-lock.json`** y **`desktop/package-lock.json`** ya tienen lockfile generado por npm. Pinning estricto efectivo.

### Excepciones

* Una excepción a una vulnerabilidad detectada por OSV-Scanner debe documentarse en `docs/dependency_exceptions.md` (futuro) con:
  - CVE
  - Razón por la que se acepta (no-explotable, falsa positiva, etc.)
  - Fecha de revisión próxima

## §4 SBOM por release

**TODO Sprint 9 (post-MVP)**: generar SBOM CycloneDX por cada build de release. Permite a clientes B2B (especialmente gestorías que requieran due diligence) consultar inventario completo.

```bash
# Backend
pip install cyclonedx-bom
cyclonedx-py -r -i backend/requirements.txt -o sbom-backend.json

# Frontend
npx @cyclonedx/cyclonedx-npm --output-file sbom-frontend.json
```

SBOM se publica como release artifact junto al instalador firmado.

## §5 Verificación de binarios embebidos

El instalador Electron embebe binarios de:

| Binario | Fuente | Verificación actual | Verificación deseada |
|---|---|---|---|
| Python 3.11.9 | python.org embed zip | hash SHA-256 del zip oficial | + firma GPG de python.org |
| PostgreSQL portable | Postgres-X64-portable | (sin verificación) | hash SHA-256 + página oficial |
| JRE | OpenJDK | (sin verificación) | hash SHA-256 + página oficial |

**TODO Sprint 9**: añadir verificación de hash a `postgres-manager.js`, `python-manager.js`, `jre-manager.js`. El download falla si el hash no coincide con la lista publicada en `docs/binary_hashes.txt`.

## §6 Periodicidad de revisión

Esta política se revisa **trimestralmente** o cuando se publique una vulnerabilidad de alto impacto que requiera ajustes (tipo log4shell). Revisión registrada en `git log` de este archivo.
