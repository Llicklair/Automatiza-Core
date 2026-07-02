"""Parser del Cuaderno 43 de la AEB (Norma 43) — extractos bancarios españoles.

Formato de registros de 80 caracteres (posiciones 1-based del estándar):

- ``11`` cabecera de cuenta: entidad, oficina, cuenta, fechas, saldo inicial.
- ``22`` movimiento: fecha operación/valor, concepto común, debe/haber, importe.
- ``23`` conceptos complementarios del movimiento anterior (hasta 5 líneas).
- ``33`` final de cuenta: nº apuntes y totales debe/haber, saldo final
  (se valida que cuadren con los movimientos leídos).
- ``88`` fin de fichero.

Los importes van en céntimos (14 dígitos, 2 decimales implícitos). El signo
lo da la clave debe/haber: 1 = debe (cargo, negativo), 2 = haber (abono,
positivo).

Salida pensada para `import_bank_transactions_rows` (idempotente): lista de
dicts ``{"fecha", "concepto", "importe", "saldo"}`` con saldo corrido
calculado a partir del saldo inicial de la cuenta.
"""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime


class Norma43Error(ValueError):
    """Fichero N43 malformado o que no cuadra con sus registros de control."""


@dataclass
class Norma43Movement:
    fecha_operacion: date
    fecha_valor: date | None
    concepto: str
    importe: float  # con signo: + abono, − cargo
    documento: str = ""
    referencia: str = ""
    saldo: float | None = None  # saldo corrido tras el movimiento


@dataclass
class Norma43Account:
    entidad: str
    oficina: str
    cuenta: str
    fecha_inicio: date | None
    fecha_fin: date | None
    saldo_inicial: float
    divisa: str
    nombre: str
    movimientos: list[Norma43Movement] = field(default_factory=list)
    saldo_final: float | None = None


def _amount(digits: str, debe_haber: str) -> float:
    """Importe de 14 dígitos con 2 decimales implícitos; 1=debe(−), 2=haber(+)."""
    cents = int(digits)
    value = round(cents / 100, 2)
    return -value if debe_haber == "1" else value


def _date(s: str) -> date | None:
    """Fecha AAMMDD (siglo 2000; el formato AEB usa año de 2 dígitos)."""
    s = s.strip()
    if not s or s == "000000":
        return None
    try:
        return datetime.strptime(s, "%y%m%d").replace(tzinfo=UTC).date()
    except ValueError as e:
        raise Norma43Error(f"Fecha inválida en N43: {s!r}") from e


def _decode(content: bytes | str) -> str:
    if isinstance(content, str):
        return content
    for enc in ("utf-8", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    raise Norma43Error("No se pudo decodificar el fichero (ni UTF-8 ni Latin-1)")


def parse_norma43(content: bytes | str) -> list[Norma43Account]:
    """Parsea un fichero Norma 43 completo. Lanza ``Norma43Error`` si está
    malformado o si los totales del registro 33 no cuadran con los movimientos."""
    text = _decode(content)
    lines = [ln.rstrip("\r\n") for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise Norma43Error("Fichero vacío")

    accounts: list[Norma43Account] = []
    account: Norma43Account | None = None
    last_mov: Norma43Movement | None = None

    for n, line in enumerate(lines, start=1):
        code = line[:2]

        if code == "11":
            if len(line) < 51:
                raise Norma43Error(f"Línea {n}: registro 11 demasiado corto")
            account = Norma43Account(
                entidad=line[2:6],
                oficina=line[6:10],
                cuenta=line[10:20],
                fecha_inicio=_date(line[20:26]),
                fecha_fin=_date(line[26:32]),
                saldo_inicial=_amount(line[33:47], line[32]),
                divisa=line[47:50],
                nombre=line[51:77].strip() if len(line) > 51 else "",
            )
            accounts.append(account)
            last_mov = None

        elif code == "22":
            if account is None:
                raise Norma43Error(f"Línea {n}: registro 22 sin cabecera 11 previa")
            if len(line) < 42:
                raise Norma43Error(f"Línea {n}: registro 22 demasiado corto")
            fecha_op = _date(line[10:16])
            if fecha_op is None:
                raise Norma43Error(f"Línea {n}: movimiento sin fecha de operación")
            last_mov = Norma43Movement(
                fecha_operacion=fecha_op,
                fecha_valor=_date(line[16:22]),
                concepto="",
                importe=_amount(line[28:42], line[27]),
                documento=line[42:52].strip() if len(line) > 42 else "",
                referencia=(line[52:80].strip() if len(line) > 52 else ""),
            )
            account.movimientos.append(last_mov)

        elif code == "23":
            if last_mov is None:
                raise Norma43Error(f"Línea {n}: registro 23 sin movimiento 22 previo")
            extra = line[4:80].strip()
            if extra:
                last_mov.concepto = f"{last_mov.concepto} {extra}".strip()

        elif code == "33":
            if account is None:
                raise Norma43Error(f"Línea {n}: registro 33 sin cabecera 11 previa")
            if len(line) < 59:
                raise Norma43Error(f"Línea {n}: registro 33 demasiado corto")
            num_debe = int(line[20:25])
            total_debe = round(int(line[25:39]) / 100, 2)
            num_haber = int(line[39:44])
            total_haber = round(int(line[44:58]) / 100, 2)
            account.saldo_final = _amount(line[59:73], line[58])

            cargos = [m for m in account.movimientos if m.importe < 0]
            abonos = [m for m in account.movimientos if m.importe >= 0]
            if len(cargos) != num_debe or len(abonos) != num_haber:
                raise Norma43Error(
                    f"Registro 33 no cuadra: declara {num_debe} cargos y "
                    f"{num_haber} abonos, leídos {len(cargos)} y {len(abonos)}"
                )
            suma_debe = round(-sum(m.importe for m in cargos), 2)
            suma_haber = round(sum(m.importe for m in abonos), 2)
            if abs(suma_debe - total_debe) > 0.005 or abs(suma_haber - total_haber) > 0.005:
                raise Norma43Error(
                    f"Registro 33 no cuadra: totales declarados D={total_debe} "
                    f"H={total_haber}, calculados D={suma_debe} H={suma_haber}"
                )
            # Saldo corrido por movimiento
            saldo = account.saldo_inicial
            for m in account.movimientos:
                saldo = round(saldo + m.importe, 2)
                m.saldo = saldo
            if abs(saldo - account.saldo_final) > 0.005:
                raise Norma43Error(
                    f"Saldo final declarado {account.saldo_final} no cuadra con " f"el calculado {saldo}"
                )
            last_mov = None

        elif code == "88":
            break

        else:
            raise Norma43Error(f"Línea {n}: código de registro desconocido {code!r}")

    if account is None:
        raise Norma43Error("El fichero no contiene ningún registro 11 (cabecera)")
    return accounts


def norma43_to_rows(accounts: list[Norma43Account]) -> list[dict[str, str]]:
    """Convierte las cuentas parseadas al formato de filas que consume
    `import_bank_transactions_rows` (fecha ISO, concepto, importe con signo, saldo)."""
    rows: list[dict[str, str]] = []
    for acc in accounts:
        for m in acc.movimientos:
            concepto = m.concepto or m.referencia or m.documento or "Movimiento N43"
            rows.append(
                {
                    "fecha": m.fecha_operacion.isoformat(),
                    "concepto": concepto,
                    "importe": f"{m.importe:.2f}",
                    "saldo": "" if m.saldo is None else f"{m.saldo:.2f}",
                }
            )
    return rows
