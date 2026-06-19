"""Descarga/actualiza los XSD oficiales de AEAT VeriFactu.

Los esquemas se publican en la Sede AEAT y se actualizan por orden ministerial;
este script los baja a `app/services/aeat/xsd/` para validar el XML localmente
(ver `services/billing/registro_facturacion.validate_verifactu_xml`).

Uso:
    python scripts/update_aeat_xsd.py

Requiere red. Namespaces verificados en `tasks/verifactu_xsd_reference.md`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

_BASE = (
    "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/"
    "aplicaciones/es/aeat/tikeV1.0/cont/ws/"  # OJO: el PATH lleva V1.0; el NS no.
)

# Ficheros oficiales VeriFactu (Suministro de Registros de Facturación).
_FILES = [
    "SuministroLR.xsd",
    "SuministroInformacion.xsd",
    "RespuestaSuministro.xsd",
    "ConsultaLR.xsd",
    "RespuestaConsultaLR.xsd",
    "EventosSIF.xsd",
    "RespuestaValRegistNoVeriFactu.xsd",
]

# xmldsig: `SuministroInformacion.xsd` lo importa por URL absoluta. Lo guardamos
# en local para que la validación XSD funcione SIN red (ver el resolver en
# registro_facturacion.validate_verifactu_xml).
_XMLDSIG = (
    "xmldsig-core-schema.xsd",
    "https://www.w3.org/TR/2002/REC-xmldsig-core-20020212/xmldsig-core-schema.xsd",
)

_DEST = Path(__file__).resolve().parents[1] / "app" / "services" / "aeat" / "xsd"


def _download(client: httpx.Client, url: str, dest: Path) -> bool:
    try:
        r = client.get(url)
        r.raise_for_status()
    except httpx.HTTPError as e:
        print(f"  [x] {dest.name}: {e}")
        return False
    dest.write_bytes(r.content)
    print(f"  [ok] {dest.name} ({len(r.content):,} bytes)")
    return True


def main() -> int:
    _DEST.mkdir(parents=True, exist_ok=True)
    print(f"Descargando XSD VeriFactu en {_DEST}")
    ok = 0
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for name in _FILES:
            ok += _download(client, _BASE + name, _DEST / name)
        name, url = _XMLDSIG
        # No abortar si falla xmldsig: la validación cae a online si falta.
        _download(client, url, _DEST / name)

    total = len(_FILES)
    print(f"\n{ok}/{total} esquemas VeriFactu descargados.")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
