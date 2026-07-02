"""Orquestador de presentación electrónica a SEDE AEAT.

Encadena: cargar certificado → firmar XML → enviar → procesar respuesta →
persistir AeatPresentation. Cada paso actualiza el status del registro
para que el frontend muestre progreso real.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounting import AeatPresentation
from app.services.aeat.certificate_storage import (
    CertificateError,
    get_active_certificate,
    load_decrypted,
)
from app.services.aeat.sede_client import SedeError, submit_signed_xml
from app.services.aeat.xades_signer import SigningError, sign_xades_bes
from app.services.aeat.xsd_validation import validate_xml_pre_signature

_log = logging.getLogger(__name__)


class PresentationError(RuntimeError):
    pass


async def create_presentation(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID | None,
    *,
    model_code: str,
    year: int,
    period: str,
    xml_unsigned: str,
    environment: str = "preproduccion",
) -> AeatPresentation:
    """Crea el registro de presentación en estado `pending`. No firma todavía."""
    if model_code not in {"303", "130", "111", "115", "347", "390", "190", "349"}:
        raise PresentationError(f"Modelo {model_code} no soportado.")
    if environment not in {"preproduccion", "produccion"}:
        raise PresentationError(f"Entorno inválido: {environment}")

    p = AeatPresentation(
        tenant_id=tenant_id,
        model_code=model_code,
        year=year,
        period=period,
        environment=environment,
        status="pending",
        xml_unsigned=xml_unsigned,
        created_by_id=user_id,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def submit_presentation(
    db: AsyncSession,
    tenant_id: UUID,
    presentation_id: UUID,
    *,
    dry_run: bool = True,
    confirmed_by_user_id: UUID | None = None,
) -> AeatPresentation:
    """Firma, envía y captura respuesta. Actualiza el AeatPresentation paso a paso.

    Blindaje fiscal: el envío REAL (`dry_run=False`) exige `confirmed_by_user_id`
    — el ID del humano que pulsó el botón. Ningún agente/automatización puede
    presentar ante la AEAT sin esa confirmación explícita. Queda en AuditLog.
    """
    if not dry_run and confirmed_by_user_id is None:
        raise PresentationError(
            "Presentación real bloqueada: falta la confirmación humana explícita "
            "(confirmed_by_user_id). Las presentaciones AEAT nunca se auto-envían."
        )
    if not dry_run:
        from app.services.audit import log_action

        await log_action(
            db,
            tenant_id=tenant_id,
            agent_name="aeat",
            action_type="aeat_presentation_confirmed",
            status="success",
            input_data={
                "presentation_id": str(presentation_id),
                "confirmed_by_user_id": str(confirmed_by_user_id),
            },
        )
    res = await db.execute(
        select(AeatPresentation)
        .where(AeatPresentation.id == presentation_id)
        .where(AeatPresentation.tenant_id == tenant_id)
    )
    p = res.scalar_one_or_none()
    if p is None:
        raise LookupError("Presentación no encontrada")
    if p.status in {"accepted", "submitted"}:
        raise PresentationError(f"La presentación ya fue enviada (status={p.status}).")
    if not p.xml_unsigned:
        raise PresentationError("No hay XML sin firmar para presentar.")

    # 1. Cargar certificado
    try:
        cert = await get_active_certificate(db, tenant_id)
        if cert is None:
            raise CertificateError("No hay certificado activo configurado.")
        if cert.valid_until and cert.valid_until.replace(tzinfo=None) < datetime.now(UTC).replace(tzinfo=None):
            raise CertificateError("El certificado activo está caducado.")
        pfx_bytes, password = await load_decrypted(db, tenant_id)
    except CertificateError as e:
        p.status = "error"
        p.error_code = "CERT"
        p.error_message = str(e)
        await db.commit()
        await db.refresh(p)
        return p

    # 2. Validar XML antes de firmar (well-formed + XSD si está disponible)
    validation_errors = validate_xml_pre_signature(p.xml_unsigned, p.model_code)
    if validation_errors:
        p.status = "error"
        p.error_code = "XSD"
        p.error_message = "; ".join(validation_errors)[:2000]
        await db.commit()
        await db.refresh(p)
        return p

    # 3. Firmar
    try:
        sign_result = sign_xades_bes(p.xml_unsigned, pfx_bytes, password)
    except SigningError as e:
        p.status = "error"
        p.error_code = "SIGN"
        p.error_message = str(e)
        await db.commit()
        await db.refresh(p)
        return p

    p.xml_signed = sign_result.signed_xml
    p.status = "signed"
    await db.commit()

    if not sign_result.signed and not dry_run:
        p.status = "error"
        p.error_code = "SIGN_STUB"
        p.error_message = "Firma stub no aceptable en producción. Instala signxml + xmlsec en el backend."
        await db.commit()
        await db.refresh(p)
        return p

    # 4. Enviar
    try:
        result = await submit_signed_xml(
            p.model_code,
            sign_result.signed_xml,
            environment=p.environment,
            dry_run=dry_run,
            confirmed=confirmed_by_user_id is not None,
        )
    except SedeError as e:
        p.status = "error"
        p.error_code = "SEDE_HTTP"
        p.error_message = str(e)
        await db.commit()
        await db.refresh(p)
        return p

    p.submitted_at = datetime.now(UTC)
    p.response_raw = result.response_body
    if result.accepted and result.dry_run:
        # Ensayo (dry_run): NO es una presentación real ante la AEAT. LÍNEA ROJA:
        # nunca debe quedar como 'accepted' ni con un CSV que parezca un
        # justificante válido. Estado propio 'simulado' y csv_justificante=None
        # (esto último hace que download_acuse devuelva 422 automáticamente).
        p.status = "simulado"
        p.csv_justificante = None
    elif result.accepted:
        p.status = "accepted"
        p.csv_justificante = result.csv
        p.accepted_at = datetime.now(UTC)
    else:
        p.status = "rejected"
        p.error_code = result.error_code
        p.error_message = result.error_message

    await db.commit()
    await db.refresh(p)
    return p


async def get_presentation(db: AsyncSession, tenant_id: UUID, presentation_id: UUID) -> AeatPresentation | None:
    res = await db.execute(
        select(AeatPresentation)
        .where(AeatPresentation.id == presentation_id)
        .where(AeatPresentation.tenant_id == tenant_id)
    )
    return res.scalar_one_or_none()


def build_acuse_text(p: AeatPresentation) -> str:
    """Acuse de recibo en texto plano con el CSV justificante de la AEAT.

    Si la presentación NO está realmente aceptada por la AEAT (ensayo dry_run =
    status 'simulado', o sin CSV real), el documento se marca de forma inequívoca
    como SIN VALIDEZ y se omite la línea de verificación en sede — nunca debe
    parecer un justificante real.
    """
    es_real = p.status == "accepted" and bool(p.csv_justificante)
    lines = [
        "ACUSE DE RECIBO — PRESENTACIÓN ELECTRÓNICA AEAT",
        "=" * 48,
    ]
    if not es_real:
        lines += [
            "*** ENSAYO — JUSTIFICANTE SIMULADO, SIN VALIDEZ ANTE LA AEAT ***",
            "=" * 48,
        ]
    lines += [
        f"Modelo:        {p.model_code}",
        f"Ejercicio:     {p.year}",
        f"Periodo:       {p.period}",
        f"Entorno:       {p.environment}",
        f"Estado:        {p.status}",
        f"CSV (justificante): {p.csv_justificante or '—'}",
        f"Presentado:    {p.submitted_at.isoformat() if p.submitted_at else '—'}",
        f"Aceptado:      {p.accepted_at.isoformat() if p.accepted_at else '—'}",
        "",
    ]
    lines.append(
        "Verificable en https://sede.agenciatributaria.gob.es con el CSV."
        if es_real
        else "Documento de ensayo interno. NO presentado realmente ante la AEAT."
    )
    return "\n".join(lines)


async def list_presentations(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    limit: int = 50,
) -> list[AeatPresentation]:
    res = await db.execute(
        select(AeatPresentation)
        .where(AeatPresentation.tenant_id == tenant_id)
        .order_by(AeatPresentation.created_at.desc())
        .limit(limit)
    )
    return list(res.scalars().all())


def presentation_to_dict(p: AeatPresentation) -> dict:
    return {
        "id": str(p.id),
        "model_code": p.model_code,
        "year": p.year,
        "period": p.period,
        "environment": p.environment,
        "status": p.status,
        "csv_justificante": p.csv_justificante,
        "error_code": p.error_code,
        "error_message": p.error_message,
        "submitted_at": p.submitted_at.isoformat() if p.submitted_at else None,
        "accepted_at": p.accepted_at.isoformat() if p.accepted_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
