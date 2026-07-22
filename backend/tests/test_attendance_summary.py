"""attendance_summary: horas fichadas por empleado en un rango de fechas.

Solo suman los tramos cerrados; los abiertos se cuentan aparte (un fichaje
olvidado no infla las horas). Base del registro de jornada (RD-ley 8/2019).
"""

from datetime import UTC, date, datetime

import pytest

from app.db.models.hr import Attendance, Employee
from app.services.hr.queries import attendance_summary


async def _emp(db, tenant_id, name):
    e = Employee(tenant_id=tenant_id, name=name)
    db.add(e)
    await db.flush()
    return e


def _att(tenant_id, emp_id, d, h_in, h_out):
    return Attendance(
        tenant_id=tenant_id,
        employee_id=emp_id,
        date=d,
        clock_in=datetime(d.year, d.month, d.day, h_in, 0, tzinfo=UTC),
        clock_out=datetime(d.year, d.month, d.day, h_out, 0, tzinfo=UTC) if h_out else None,
    )


@pytest.mark.asyncio
async def test_summary_suma_cerrados_cuenta_abiertos_y_filtra_rango(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    ana = await _emp(db, tenant.id, "Ana")
    luis = await _emp(db, tenant.id, "Luis")
    db.add_all(
        [
            _att(tenant.id, ana.id, date(2026, 7, 20), 9, 17),  # 8h
            _att(tenant.id, ana.id, date(2026, 7, 21), 9, 13),  # 4h
            _att(tenant.id, ana.id, date(2026, 7, 22), 9, None),  # abierto
            _att(tenant.id, luis.id, date(2026, 7, 21), 10, 12),  # 2h
            _att(tenant.id, luis.id, date(2026, 6, 1), 9, 17),  # fuera de rango
        ]
    )
    await db.commit()

    filas = await attendance_summary(db, tenant.id, date(2026, 7, 1), date(2026, 7, 31))

    por_id = {f["employee_id"]: f for f in filas}
    a = por_id[str(ana.id)]
    assert a["horas"] == 12.0
    assert a["dias"] == 2
    assert a["tramos"] == 2
    assert a["abiertos"] == 1
    lu = por_id[str(luis.id)]
    assert lu["horas"] == 2.0  # la de junio queda fuera del rango
    assert lu["dias"] == 1
    assert lu["abiertos"] == 0
    # Orden: más horas primero.
    assert filas[0]["employee_id"] == str(ana.id)


@pytest.mark.asyncio
async def test_summary_rango_vacio(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    assert await attendance_summary(db, tenant.id, date(2026, 1, 1), date(2026, 1, 31)) == []
