"""Servicio del wizard REGAP (PRES.REG) — apoderamiento AEAT.

REGAP = Registro de Apoderamientos de la Agencia Tributaria. Para que
AutomatizaPyme S.L. pueda presentar declaraciones telemáticas en nombre
de un cliente, el cliente debe haber otorgado el apoderamiento en sede
electrónica AEAT con uno de tres métodos de autenticación:

  1. `clave_pin`     — Cl@ve PIN (envío SMS)
  2. `clave_permanente` — Cl@ve Permanente (usuario + contraseña + SMS)
  3. `cert_fnmt`     — Certificado FNMT instalado en el navegador del cliente

Este servicio gestiona la FSM por tenant. La verificación contra el
endpoint real REGAP queda **mocked** hasta DEC.14 (alta colaborador social).
Cuando la consulta real esté disponible, sustituir `_call_regap_consulta`
por el cliente HTTPS oficial.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import TenantRegapStatus

logger = logging.getLogger("onboarding.regap")

AuthMethod = Literal["clave_pin", "clave_permanente", "cert_fnmt"]
RegapStatus = Literal[
    "not_started",
    "identifying",
    "cert_pending",
    "power_granted",
    "verified",
    "rejected",
]

# NIF de AutomatizaPyme S.L. (DEC.02 — entidad facturadora oficial).
# Se carga del settings si está configurado, por defecto placeholder.
APODERADO_NIF_DEFAULT = "B00000000"
APODERADO_NOMBRE_DEFAULT = "AutomatizaPyme S.L."


def _settings_apoderado() -> tuple[str, str]:
    try:
        from app.core.config import settings

        nif = getattr(settings, "APODERADO_NIF", "") or APODERADO_NIF_DEFAULT
        nombre = (
            getattr(settings, "APODERADO_NOMBRE", "") or APODERADO_NOMBRE_DEFAULT
        )
        return nif, nombre
    except Exception:
        return APODERADO_NIF_DEFAULT, APODERADO_NOMBRE_DEFAULT


async def get_regap_status(db: AsyncSession, *, tenant_id: UUID) -> TenantRegapStatus:
    """Devuelve el registro REGAP del tenant; lo crea con defaults si no existe."""
    result = await db.execute(
        select(TenantRegapStatus).where(TenantRegapStatus.tenant_id == tenant_id)
    )
    record = result.scalar_one_or_none()
    if record is not None:
        return record

    nif, nombre = _settings_apoderado()
    record = TenantRegapStatus(
        tenant_id=tenant_id,
        status="not_started",
        apoderado_nif=nif,
        apoderado_nombre=nombre,
    )
    db.add(record)
    await db.flush()
    return record


async def start_identification(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    auth_method: AuthMethod,
) -> TenantRegapStatus:
    """Step 1 → 2: el cliente eligió método de autenticación.

    `clave_pin` / `clave_permanente` saltan a `power_granted` directamente
    cuando completen sus pasos en Sede AEAT. `cert_fnmt` pasa por
    `cert_pending` mientras solicita el certificado FNMT (proceso de 5-10 d).
    """
    record = await get_regap_status(db, tenant_id=tenant_id)

    record.auth_method = auth_method
    if auth_method == "cert_fnmt":
        record.status = "cert_pending"
    else:
        record.status = "identifying"
    record.updated_at = datetime.now(UTC)
    await db.flush()
    return record


async def mark_power_granted(
    db: AsyncSession, *, tenant_id: UUID
) -> TenantRegapStatus:
    """Step 2 → 3: el cliente declara haber completado el apoderamiento.

    Es una declaración del usuario — antes de marcar `verified` debe pasar
    por `verify_regap_consulta` (consulta real al endpoint AEAT).
    """
    record = await get_regap_status(db, tenant_id=tenant_id)
    if record.status not in ("identifying", "cert_pending"):
        raise ValueError(
            f"Transición ilegal: estado actual '{record.status}' no permite "
            f"avanzar a 'power_granted'"
        )
    record.status = "power_granted"
    record.updated_at = datetime.now(UTC)
    await db.flush()
    return record


async def _call_regap_consulta(nif_cliente: str, nif_apoderado: str) -> dict:
    """Consulta real REGAP — MOCK por ahora.

    Cuando DEC.14 (alta colaborador social) esté completo, sustituir por:
        cliente HTTPS contra Sede AEAT con cert representación. La respuesta
        real es un XML/JSON con la lista de apoderamientos vigentes para el
        NIF consultado.
    """
    return {
        "mock": True,
        "consulted_at": datetime.now(UTC).isoformat(),
        "nif_cliente": nif_cliente,
        "nif_apoderado": nif_apoderado,
        "apoderamientos": [
            {
                "tramite": "PRESENTACION_DECLARACIONES",
                "vigente_desde": "2026-01-01",
                "estado": "VIGENTE",
            }
        ],
    }


async def verify_regap_consulta(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    nif_cliente: str,
) -> TenantRegapStatus:
    """Step 3 → 4: consulta REGAP confirma que el apoderamiento existe."""
    record = await get_regap_status(db, tenant_id=tenant_id)
    if record.status != "power_granted":
        raise ValueError(
            f"Transición ilegal: solo se puede verificar desde 'power_granted', "
            f"actual '{record.status}'"
        )

    apoderado_nif = record.apoderado_nif or APODERADO_NIF_DEFAULT
    payload = await _call_regap_consulta(nif_cliente, apoderado_nif)
    vigente = any(
        ap.get("estado") == "VIGENTE" for ap in payload.get("apoderamientos", [])
    )

    record.verify_payload = json.dumps(payload)
    if vigente:
        record.status = "verified"
        record.verified_at = datetime.now(UTC)
        record.rejected_reason = None
    else:
        record.status = "rejected"
        record.rejected_reason = (
            "La consulta REGAP no devolvió apoderamientos vigentes. "
            "Confirma que has completado el trámite en Sede AEAT y vuelve a intentar."
        )
    record.updated_at = datetime.now(UTC)
    await db.flush()
    return record


async def reset_regap(db: AsyncSession, *, tenant_id: UUID) -> TenantRegapStatus:
    """Vuelve a `not_started` — útil si el cliente quiere cambiar de método."""
    record = await get_regap_status(db, tenant_id=tenant_id)
    nif, nombre = _settings_apoderado()
    record.status = "not_started"
    record.auth_method = None
    record.apoderado_nif = nif
    record.apoderado_nombre = nombre
    record.verify_payload = None
    record.verified_at = None
    record.rejected_reason = None
    record.updated_at = datetime.now(UTC)
    await db.flush()
    return record
