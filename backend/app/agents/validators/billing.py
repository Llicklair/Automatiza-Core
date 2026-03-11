"""
Validadores deterministas para facturación española.
SIN LLM — lógica pura, 100% predecible.
Fuentes: BOE, AEAT, Reglamento de Facturación (RD 1619/2012).
"""
import re
from datetime import date, timedelta
from decimal import Decimal

# ─── NIF / CIF ────────────────────────────────────────────────────────────────

# Tabla de control DNI
_DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"

# Prefijos válidos para personas jurídicas (CIF)
_CIF_ORG_PREFIXES = set("ABCDEFGHJNPQRSUVW")


def validate_nif(nif: str) -> tuple[bool, str]:
    """
    Valida NIF (personas físicas) y CIF (personas jurídicas) españoles.
    Devuelve (válido: bool, motivo: str).
    """
    if not nif:
        return False, "NIF vacío"

    nif = nif.upper().strip().replace("-", "").replace(" ", "")

    if len(nif) != 9:
        return False, f"Longitud incorrecta: {len(nif)} caracteres (se esperan 9)"

    # DNI — 8 dígitos + letra de control
    if nif[0].isdigit():
        if not re.match(r"^\d{8}[A-Z]$", nif):
            return False, "Formato DNI inválido"
        expected = _DNI_LETTERS[int(nif[:8]) % 23]
        if nif[8] != expected:
            return False, f"Letra de control incorrecta (esperada: {expected})"
        return True, "DNI válido"

    # NIE — extranjeros (X, Y, Z)
    if nif[0] in "XYZ":
        prefix_map = {"X": "0", "Y": "1", "Z": "2"}
        numeric = prefix_map[nif[0]] + nif[1:8]
        if not re.match(r"^\d{8}$", numeric):
            return False, "Formato NIE inválido"
        expected = _DNI_LETTERS[int(numeric) % 23]
        if nif[8] != expected:
            return False, f"Letra de control NIE incorrecta (esperada: {expected})"
        return True, "NIE válido"

    # CIF — persona jurídica
    if nif[0] in _CIF_ORG_PREFIXES:
        if not re.match(r"^[A-Z]\d{7}[A-Z0-9]$", nif):
            return False, "Formato CIF inválido"
        digits = [int(c) for c in nif[1:8]]
        even_sum = sum(digits[1::2])
        odd_sum = sum(
            (d * 2 // 10) + (d * 2 % 10) for d in digits[::2]
        )
        total = even_sum + odd_sum
        control_digit = (10 - (total % 10)) % 10
        control_letter = "JABCDEFGHI"[control_digit]

        last = nif[8]
        if nif[0] in "PQSNWR":
            # Sólo letra
            if last != control_letter:
                return False, f"Letra de control CIF incorrecta (esperada: {control_letter})"
        elif nif[0] in "ABEH":
            # Sólo dígito
            if last != str(control_digit):
                return False, f"Dígito de control CIF incorrecto (esperado: {control_digit})"
        else:
            # Acepta letra o dígito
            if last not in (control_letter, str(control_digit)):
                return False, f"Control CIF incorrecto (esperado: {control_letter} o {control_digit})"
        return True, "CIF válido"

    return False, f"Prefijo desconocido: '{nif[0]}'"


# ─── IBAN ────────────────────────────────────────────────────────────────────

def validate_iban(iban: str) -> tuple[bool, str]:
    """Valida IBAN por módulo 97 (ISO 13616)."""
    iban = iban.upper().strip().replace(" ", "").replace("-", "")

    if len(iban) < 15 or len(iban) > 34:
        return False, "Longitud IBAN incorrecta"

    if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]+$", iban):
        return False, "Formato IBAN inválido"

    # Trasladar los 4 primeros al final y sustituir letras por números
    rearranged = iban[4:] + iban[:4]
    numeric = ""
    for ch in rearranged:
        numeric += str(ord(ch) - ord("A") + 10) if ch.isalpha() else ch

    if int(numeric) % 97 != 1:
        return False, "Dígitos de control IBAN incorrectos"

    return True, "IBAN válido"


# ─── IVA ────────────────────────────────────────────────────────────────────

VALID_VAT_RATES_ES = {0, 4, 10, 21}  # tipos vigentes en España
VALID_IRPF_RATES   = {7, 15, 19}     # retenciones IRPF habituales


def validate_vat_rate(rate: float) -> tuple[bool, str]:
    """Verifica que el tipo de IVA sea válido en España."""
    if rate not in VALID_VAT_RATES_ES:
        return False, f"Tipo de IVA inválido: {rate}%. Valores permitidos: {sorted(VALID_VAT_RATES_ES)}"
    return True, f"IVA {rate}% válido"


# ─── Importes ────────────────────────────────────────────────────────────────

MAX_INVOICE_AMOUNT_EUR = Decimal("1_000_000")  # Límite de alerta por factura
MIN_INVOICE_AMOUNT_EUR = Decimal("0.01")


def validate_amount(amount: Decimal) -> tuple[bool, str]:
    if amount < MIN_INVOICE_AMOUNT_EUR:
        return False, f"Importe demasiado bajo: {amount}€"
    if amount > MAX_INVOICE_AMOUNT_EUR:
        return False, f"Importe inusualmente alto: {amount}€ (requiere aprobación manual)"
    return True, f"Importe {amount}€ dentro de rango"


# ─── Fechas ──────────────────────────────────────────────────────────────────

def validate_invoice_date(invoice_date: date) -> tuple[bool, str]:
    today = date.today()
    too_old = today - timedelta(days=365)   # Más de 1 año en el pasado
    too_future = today + timedelta(days=365) # Más de 1 año en el futuro

    if invoice_date < too_old:
        return False, f"Fecha de factura demasiado antigua: {invoice_date}"
    if invoice_date > too_future:
        return False, f"Fecha de factura demasiado en el futuro: {invoice_date}"
    return True, f"Fecha {invoice_date} válida"


# ─── Validación completa de factura ─────────────────────────────────────────

class InvoiceValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict:
        return {
            "valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_invoice_data(
    client_nif: str,
    amount_base: Decimal,
    vat_rate: float,
    invoice_date: date,
    iban: str | None = None,
) -> InvoiceValidationResult:
    """
    Validación determinista completa de una factura.
    Se ejecuta ANTES de cualquier llamada a LLM o API externa.
    """
    result = InvoiceValidationResult()

    # NIF — se registra como advertencia, no como error bloqueante
    # (permite NIFs ficticios de prueba o ligeras variaciones en CIF)
    ok, msg = validate_nif(client_nif)
    if not ok:
        result.warnings.append(f"Aviso NIF: {msg}. Verifica que sea correcto.")

    # Importe
    ok, msg = validate_amount(amount_base)
    if not ok:
        result.errors.append(msg)
    if amount_base > Decimal("50_000"):
        result.warnings.append(f"Importe elevado ({amount_base}€): verifica antes de enviar")

    # IVA
    ok, msg = validate_vat_rate(vat_rate)
    if not ok:
        result.errors.append(msg)

    # Fecha
    ok, msg = validate_invoice_date(invoice_date)
    if not ok:
        result.errors.append(msg)

    # IBAN (opcional)
    if iban:
        ok, msg = validate_iban(iban)
        if not ok:
            result.errors.append(f"IBAN inválido: {msg}")

    return result
