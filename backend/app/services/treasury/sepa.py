"""Generación de fichero SEPA pain.001.001.03 para remesas de
transferencias salientes (pagos a proveedores) — F2.7.

Estándar ISO 20022 — Customer Credit Transfer Initiation v3. Las
entidades bancarias españolas aceptan este formato por canal banca
electrónica como remesa de cobros/pagos masivos.

Estructura simplificada generada:

  Document
    └── CstmrCdtTrfInitn
          ├── GrpHdr (MsgId, CreDtTm, NbOfTxs, CtrlSum, InitgPty)
          └── PmtInf (PmtMtd=TRF, ReqdExctnDt, Dbtr, DbtrAcct, DbtrAgt)
                └── CdtTrfTxInf × N
                      ├── PmtId.EndToEndId
                      ├── Amt.InstdAmt (currency=EUR)
                      ├── CdtrAgt.FinInstnId
                      ├── Cdtr.Nm
                      ├── CdtrAcct.Id.IBAN
                      └── RmtInf.Ustrd  (concepto)

No se firma ni se envía: el usuario descarga el .xml y lo sube al portal
de su banco. Validamos lo imprescindible para que la entidad lo acepte:
IBAN del beneficiario presente, importe > 0, fecha de ejecución >= hoy.
"""

from __future__ import annotations

import re
import uuid as _uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring

_NS = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"
_IBAN_RE = re.compile(r"^[A-Z]{2}[0-9A-Z]{2,32}$")


class Pain001Error(ValueError):
    """Error de validación al construir el pain.001."""


@dataclass
class TransferOrder:
    """Una transferencia individual dentro de una remesa pain.001."""

    creditor_name: str
    creditor_iban: str
    amount_eur: Decimal | float
    concept: str
    end_to_end_id: str | None = None  # se autogenera si None


@dataclass
class DebtorParty:
    name: str
    iban: str
    bic: str | None = None  # opcional para SEPA dentro de la UE


def _norm_iban(iban: str) -> str:
    return re.sub(r"\s+", "", (iban or "").upper())


def _validate_iban(iban: str) -> str:
    iban = _norm_iban(iban)
    if not _IBAN_RE.match(iban):
        raise Pain001Error(f"IBAN inválido: '{iban}'")
    return iban


def _validate_amount(amount: Decimal | float) -> Decimal:
    try:
        d = Decimal(str(amount)).quantize(Decimal("0.01"))
    except Exception as e:
        raise Pain001Error(f"Importe inválido: {amount}") from e
    if d <= 0:
        raise Pain001Error(f"El importe debe ser > 0: {amount}")
    return d


def _sanitize_txt(s: str, maxlen: int = 140) -> str:
    # ISO 20022 acepta texto razonable; recortamos a maxlen y eliminamos
    # caracteres de control. No re-codificamos a ASCII porque pain.001
    # admite Unicode en SEPA EU/EEA.
    cleaned = re.sub(r"[\x00-\x1f\x7f]", " ", s or "")
    return cleaned.strip()[:maxlen]


def build_pain001(
    debtor: DebtorParty,
    execution_date: date,
    orders: list[TransferOrder],
    *,
    message_id: str | None = None,
    initiating_party_name: str | None = None,
    now: datetime | None = None,
) -> tuple[str, dict]:
    """Construye el XML pain.001.001.03 y devuelve (xml_str, summary).

    Args:
        debtor: ordenante (la pyme propietaria del tenant).
        execution_date: fecha de ejecución (no anterior a hoy).
        orders: 1..n transferencias a incluir.
        message_id: opcional, identificador único de la remesa.
        initiating_party_name: opcional, distinta de `debtor.name` si la
            empresa firma desde otra entidad.

    Returns:
        (xml_string, summary_dict)
        summary_dict incluye nb_of_txs, control_sum (€), iban del deudor,
        msg_id y un hash SHA-256 del XML para auditoría.
    """
    if not orders:
        raise Pain001Error("La remesa requiere al menos 1 transferencia.")

    today = (now or datetime.now(timezone.utc)).date()
    if execution_date < today:
        raise Pain001Error(
            f"La fecha de ejecución {execution_date} es anterior a hoy {today}."
        )

    debtor_iban = _validate_iban(debtor.iban)
    initiator = _sanitize_txt(initiating_party_name or debtor.name, 70)
    if not initiator:
        raise Pain001Error("El nombre del ordenante es obligatorio.")

    creation_ts = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%S")
    msg_id = (message_id or f"REM-{_uuid.uuid4().hex[:16]}").upper()
    pmt_inf_id = f"{msg_id}-001"

    validated: list[tuple[TransferOrder, Decimal, str]] = []
    control_sum = Decimal("0")
    for ord_ in orders:
        amt = _validate_amount(ord_.amount_eur)
        iban_ok = _validate_iban(ord_.creditor_iban)
        control_sum += amt
        validated.append((ord_, amt, iban_ok))

    # Construcción XML
    doc = Element("Document", attrib={"xmlns": _NS})
    cst = SubElement(doc, "CstmrCdtTrfInitn")

    grp = SubElement(cst, "GrpHdr")
    SubElement(grp, "MsgId").text = msg_id
    SubElement(grp, "CreDtTm").text = creation_ts
    SubElement(grp, "NbOfTxs").text = str(len(validated))
    SubElement(grp, "CtrlSum").text = format(control_sum, "f")
    initg = SubElement(grp, "InitgPty")
    SubElement(initg, "Nm").text = initiator

    pmt = SubElement(cst, "PmtInf")
    SubElement(pmt, "PmtInfId").text = pmt_inf_id
    SubElement(pmt, "PmtMtd").text = "TRF"
    SubElement(pmt, "NbOfTxs").text = str(len(validated))
    SubElement(pmt, "CtrlSum").text = format(control_sum, "f")
    SubElement(pmt, "ReqdExctnDt").text = execution_date.isoformat()
    dbtr = SubElement(pmt, "Dbtr")
    SubElement(dbtr, "Nm").text = _sanitize_txt(debtor.name, 70)
    dbtr_acct = SubElement(pmt, "DbtrAcct")
    SubElement(SubElement(dbtr_acct, "Id"), "IBAN").text = debtor_iban
    dbtr_agt = SubElement(pmt, "DbtrAgt")
    fin_inst = SubElement(dbtr_agt, "FinInstnId")
    if debtor.bic:
        SubElement(fin_inst, "BIC").text = debtor.bic.upper()
    else:
        SubElement(fin_inst, "Othr").append(_element("Id", "NOTPROVIDED"))

    for ord_, amt, iban_ok in validated:
        tx = SubElement(pmt, "CdtTrfTxInf")
        pid = SubElement(tx, "PmtId")
        e2e = ord_.end_to_end_id or f"E2E-{_uuid.uuid4().hex[:20].upper()}"
        SubElement(pid, "EndToEndId").text = _sanitize_txt(e2e, 35)
        amt_el = SubElement(tx, "Amt")
        SubElement(amt_el, "InstdAmt", attrib={"Ccy": "EUR"}).text = format(amt, "f")
        cdtr_agt = SubElement(tx, "CdtrAgt")
        SubElement(SubElement(cdtr_agt, "FinInstnId"), "Othr").append(
            _element("Id", "NOTPROVIDED")
        )
        cdtr = SubElement(tx, "Cdtr")
        SubElement(cdtr, "Nm").text = _sanitize_txt(ord_.creditor_name, 70)
        cdtr_acct = SubElement(tx, "CdtrAcct")
        SubElement(SubElement(cdtr_acct, "Id"), "IBAN").text = iban_ok
        if ord_.concept:
            rmt = SubElement(tx, "RmtInf")
            SubElement(rmt, "Ustrd").text = _sanitize_txt(ord_.concept, 140)

    xml_bytes = tostring(doc, encoding="utf-8", xml_declaration=True)
    xml_str = xml_bytes.decode("utf-8")

    import hashlib
    summary = {
        "msg_id": msg_id,
        "nb_of_txs": len(validated),
        "control_sum_eur": float(control_sum),
        "debtor_iban": debtor_iban,
        "execution_date": execution_date.isoformat(),
        "sha256": hashlib.sha256(xml_bytes).hexdigest(),
    }
    return xml_str, summary


def _element(tag: str, text: str) -> Element:
    el = Element(tag)
    el.text = text
    return el
