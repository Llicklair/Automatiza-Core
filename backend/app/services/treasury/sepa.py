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
_NS_008 = "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02"
_IBAN_RE = re.compile(r"^[A-Z]{2}[0-9A-Z]{2,32}$")
_SEQ_TYPES = ("FRST", "RCUR", "OOFF", "FNAL")


class Pain001Error(ValueError):
    """Error de validación al construir el pain.001."""


class Pain008Error(ValueError):
    """Error de validación al construir el pain.008."""


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
        raise Pain001Error(f"La fecha de ejecución {execution_date} es anterior a hoy {today}.")

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
        SubElement(SubElement(cdtr_agt, "FinInstnId"), "Othr").append(_element("Id", "NOTPROVIDED"))
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


# ── pain.008 — adeudos directos SEPA Core (cobros a clientes) ─────────────────


@dataclass
class DirectDebitOrder:
    """Un adeudo individual dentro de una remesa pain.008 (SEPA Core)."""

    debtor_name: str
    debtor_iban: str
    amount_eur: Decimal | float
    concept: str
    mandate_id: str
    mandate_date: date
    sequence_type: str = "RCUR"  # FRST | RCUR | OOFF | FNAL
    end_to_end_id: str | None = None


@dataclass
class CreditorParty:
    """Acreedor de los adeudos: la pyme, con su identificador SEPA (AT-02)."""

    name: str
    iban: str
    creditor_id: str  # identificador de acreedor SEPA (p.ej. ES12000B12345678)
    bic: str | None = None


def build_pain008(
    creditor: CreditorParty,
    collection_date: date,
    orders: list[DirectDebitOrder],
    *,
    message_id: str | None = None,
    now: datetime | None = None,
) -> tuple[str, dict]:
    """Construye el XML pain.008.001.02 (Customer Direct Debit Initiation,
    esquema CORE) y devuelve ``(xml_str, summary)``.

    Cada adeudo requiere mandato (MndtId + fecha de firma) y tipo de
    secuencia. Los adeudos se agrupan en un ``PmtInf`` por tipo de secuencia
    (el SeqTp es un atributo del bloque de pago, no de la transacción).
    """
    if not orders:
        raise Pain008Error("La remesa requiere al menos 1 adeudo.")

    today = (now or datetime.now(timezone.utc)).date()
    if collection_date < today:
        raise Pain008Error(f"La fecha de cobro {collection_date} es anterior a hoy {today}.")

    creditor_iban = _validate_iban(creditor.iban)
    creditor_name = _sanitize_txt(creditor.name, 70)
    if not creditor_name:
        raise Pain008Error("El nombre del acreedor es obligatorio.")
    creditor_id = _sanitize_txt(creditor.creditor_id, 35)
    if not creditor_id:
        raise Pain008Error("El identificador de acreedor SEPA es obligatorio.")

    validated: list[tuple[DirectDebitOrder, Decimal, str]] = []
    control_sum = Decimal("0")
    for ord_ in orders:
        seq = (ord_.sequence_type or "RCUR").upper()
        if seq not in _SEQ_TYPES:
            raise Pain008Error(f"Tipo de secuencia inválido: {ord_.sequence_type!r}")
        if not (ord_.mandate_id or "").strip():
            raise Pain008Error(f"Adeudo a '{ord_.debtor_name}' sin mandato (MndtId).")
        if ord_.mandate_date is None:
            raise Pain008Error(f"Adeudo a '{ord_.debtor_name}' sin fecha de mandato.")
        try:
            amt = _validate_amount(ord_.amount_eur)
            iban_ok = _validate_iban(ord_.debtor_iban)
        except Pain001Error as e:
            raise Pain008Error(str(e)) from e
        control_sum += amt
        validated.append((ord_, amt, iban_ok))

    creation_ts = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%S")
    msg_id = (message_id or f"ADE-{_uuid.uuid4().hex[:16]}").upper()

    doc = Element("Document", attrib={"xmlns": _NS_008})
    cst = SubElement(doc, "CstmrDrctDbtInitn")

    grp = SubElement(cst, "GrpHdr")
    SubElement(grp, "MsgId").text = msg_id
    SubElement(grp, "CreDtTm").text = creation_ts
    SubElement(grp, "NbOfTxs").text = str(len(validated))
    SubElement(grp, "CtrlSum").text = format(control_sum, "f")
    SubElement(SubElement(grp, "InitgPty"), "Nm").text = creditor_name

    # Un PmtInf por tipo de secuencia, en orden estable
    by_seq: dict[str, list[tuple[DirectDebitOrder, Decimal, str]]] = {}
    for item in validated:
        by_seq.setdefault(item[0].sequence_type.upper(), []).append(item)

    for i, (seq, items) in enumerate(sorted(by_seq.items()), start=1):
        seq_sum = sum(amt for _, amt, _ in items)
        pmt = SubElement(cst, "PmtInf")
        SubElement(pmt, "PmtInfId").text = f"{msg_id}-{i:03d}"
        SubElement(pmt, "PmtMtd").text = "DD"
        SubElement(pmt, "NbOfTxs").text = str(len(items))
        SubElement(pmt, "CtrlSum").text = format(seq_sum, "f")
        pmt_tp = SubElement(pmt, "PmtTpInf")
        SubElement(SubElement(pmt_tp, "SvcLvl"), "Cd").text = "SEPA"
        SubElement(SubElement(pmt_tp, "LclInstrm"), "Cd").text = "CORE"
        SubElement(pmt_tp, "SeqTp").text = seq
        SubElement(pmt, "ReqdColltnDt").text = collection_date.isoformat()
        SubElement(SubElement(pmt, "Cdtr"), "Nm").text = creditor_name
        SubElement(SubElement(SubElement(pmt, "CdtrAcct"), "Id"), "IBAN").text = creditor_iban
        cdtr_agt = SubElement(pmt, "CdtrAgt")
        fin_inst = SubElement(cdtr_agt, "FinInstnId")
        if creditor.bic:
            SubElement(fin_inst, "BIC").text = creditor.bic.upper()
        else:
            SubElement(fin_inst, "Othr").append(_element("Id", "NOTPROVIDED"))
        schme = SubElement(pmt, "CdtrSchmeId")
        othr = SubElement(SubElement(SubElement(schme, "Id"), "PrvtId"), "Othr")
        SubElement(othr, "Id").text = creditor_id
        SubElement(SubElement(othr, "SchmeNm"), "Prtry").text = "SEPA"

        for ord_, amt, iban_ok in items:
            tx = SubElement(pmt, "DrctDbtTxInf")
            e2e = ord_.end_to_end_id or f"E2E-{_uuid.uuid4().hex[:20].upper()}"
            SubElement(SubElement(tx, "PmtId"), "EndToEndId").text = _sanitize_txt(e2e, 35)
            SubElement(tx, "InstdAmt", attrib={"Ccy": "EUR"}).text = format(amt, "f")
            mndt = SubElement(SubElement(tx, "DrctDbtTx"), "MndtRltdInf")
            SubElement(mndt, "MndtId").text = _sanitize_txt(ord_.mandate_id, 35)
            SubElement(mndt, "DtOfSgntr").text = ord_.mandate_date.isoformat()
            dbtr_agt = SubElement(tx, "DbtrAgt")
            SubElement(SubElement(dbtr_agt, "FinInstnId"), "Othr").append(_element("Id", "NOTPROVIDED"))
            SubElement(SubElement(tx, "Dbtr"), "Nm").text = _sanitize_txt(ord_.debtor_name, 70)
            SubElement(SubElement(SubElement(tx, "DbtrAcct"), "Id"), "IBAN").text = iban_ok
            if ord_.concept:
                SubElement(SubElement(tx, "RmtInf"), "Ustrd").text = _sanitize_txt(ord_.concept, 140)

    xml_bytes = tostring(doc, encoding="utf-8", xml_declaration=True)
    xml_str = xml_bytes.decode("utf-8")

    import hashlib

    summary = {
        "msg_id": msg_id,
        "nb_of_txs": len(validated),
        "control_sum_eur": float(control_sum),
        "creditor_iban": creditor_iban,
        "collection_date": collection_date.isoformat(),
        "sha256": hashlib.sha256(xml_bytes).hexdigest(),
    }
    return xml_str, summary
