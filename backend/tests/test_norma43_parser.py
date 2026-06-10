"""Tests del parser Norma 43 (Cuaderno 43 AEB) — fixture sintética anonimizada."""

import pytest

from app.services.banking.parsers.norma43 import (
    Norma43Error,
    norma43_to_rows,
    parse_norma43,
)


def _line(code: str, body: str) -> str:
    return (code + body).ljust(80)


def _mov22(fecha: str, dh: str, cents: int, doc: str = "0000000000") -> str:
    # 22 + entidad(4) + oficina(4) + f.op(6) + f.valor(6) + común(2) + propio(3)
    #    + D/H(1) + importe(14) + documento(10) + referencias
    return _line(
        "22",
        "00810001" + fecha + fecha + "02" + "000" + dh + f"{cents:014d}" + doc,
    )


def _build_file(movs: list[tuple[str, str, int]], saldo_inicial_cents: int = 100000) -> str:
    """Genera un N43 mínimo válido con registro 33 que cuadra."""
    lines = [
        _line(
            "11",
            "00810001" + "0123456789" + "260601" + "260630" + "2"
            + f"{saldo_inicial_cents:014d}" + "978" + "1" + "EMPRESA DEMO SL",
        )
    ]
    for fecha, dh, cents in movs:
        lines.append(_mov22(fecha, dh, cents))
        lines.append(_line("23", "01TRANSFERENCIA DE PRUEBA"))
    cargos = [(c) for _, dh, c in movs if dh == "1"]
    abonos = [(c) for _, dh, c in movs if dh == "2"]
    saldo_final = saldo_inicial_cents - sum(cargos) + sum(abonos)
    lines.append(
        _line(
            "33",
            "00810001" + "0123456789"
            + f"{len(cargos):05d}" + f"{sum(cargos):014d}"
            + f"{len(abonos):05d}" + f"{sum(abonos):014d}"
            + ("2" if saldo_final >= 0 else "1") + f"{abs(saldo_final):014d}" + "978",
        )
    )
    lines.append(_line("88", "9" * 18 + f"{len(lines) + 1:06d}"))
    return "\n".join(lines)


def test_parse_fichero_valido():
    content = _build_file([("260605", "2", 150000), ("260610", "1", 25050)])
    accounts = parse_norma43(content)
    assert len(accounts) == 1
    acc = accounts[0]
    assert acc.cuenta == "0123456789"
    assert acc.saldo_inicial == 1000.0
    assert len(acc.movimientos) == 2

    abono, cargo = acc.movimientos
    assert abono.importe == 1500.0
    assert abono.fecha_operacion.isoformat() == "2026-06-05"
    assert "TRANSFERENCIA DE PRUEBA" in abono.concepto
    assert cargo.importe == -250.50
    # Saldo corrido: 1000 + 1500 − 250.50
    assert abono.saldo == 2500.0
    assert cargo.saldo == 2249.50
    assert acc.saldo_final == 2249.50


def test_to_rows_formato_import():
    content = _build_file([("260605", "2", 150000)])
    rows = norma43_to_rows(parse_norma43(content))
    assert rows == [
        {
            "fecha": "2026-06-05",
            "concepto": "TRANSFERENCIA DE PRUEBA",
            "importe": "1500.00",
            "saldo": "2500.00",
        }
    ]


def test_registro_33_totales_no_cuadran():
    content = _build_file([("260605", "2", 150000)])
    # Corromper el total haber del registro 33
    bad = content.replace(f"{150000:014d}", f"{999900:014d}")
    with pytest.raises(Norma43Error, match="no cuadra"):
        parse_norma43(bad)


def test_registro_33_numero_apuntes_no_cuadra():
    lines = _build_file([("260605", "2", 150000)]).splitlines()
    # Eliminar el movimiento (22) y su concepto (23): el 33 declara 1 abono
    lines = [ln for ln in lines if not ln.startswith(("22", "23"))]
    with pytest.raises(Norma43Error, match="declara"):
        parse_norma43("\n".join(lines))


def test_fichero_vacio_y_sin_cabecera():
    with pytest.raises(Norma43Error):
        parse_norma43("")
    with pytest.raises(Norma43Error):
        parse_norma43(_line("22", "x" * 60))


def test_codigo_desconocido():
    with pytest.raises(Norma43Error, match="desconocido"):
        parse_norma43(_line("99", ""))


def test_decode_latin1():
    content = _build_file([("260605", "2", 150000)])
    content = content.replace("TRANSFERENCIA DE PRUEBA", "NÓMINA SEÑOR PÉREZ    ")
    accounts = parse_norma43(content.encode("latin-1"))
    assert "NÓMINA SEÑOR PÉREZ" in accounts[0].movimientos[0].concepto


# ── Integración con el import idempotente ─────────────────────────────────────


@pytest.mark.asyncio
async def test_import_n43_idempotente(db):
    from uuid import uuid4

    from sqlalchemy import func, select

    from app.db.models.accounting import BankTransaction
    from app.db.models.models import Tenant
    from app.services.migration.bulk_import import import_bank_transactions_rows

    tenant = Tenant(id=uuid4(), name="N43 S.L.", nif="B43434343", plan="starter")
    db.add(tenant)
    await db.flush()

    rows = norma43_to_rows(
        parse_norma43(_build_file([("260605", "2", 150000), ("260610", "1", 25050)]))
    )
    res1 = await import_bank_transactions_rows(rows, tenant.id, db)
    assert res1.created == 2

    # Recargar el mismo extracto no duplica
    res2 = await import_bank_transactions_rows(rows, tenant.id, db)
    assert res2.created == 0
    assert res2.skipped == 2

    count = await db.execute(
        select(func.count(BankTransaction.id)).where(BankTransaction.tenant_id == tenant.id)
    )
    assert int(count.scalar() or 0) == 2
