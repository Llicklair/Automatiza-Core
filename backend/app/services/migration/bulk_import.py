"""Bulk CSV import for employees / clients / products.

Capa de servicio para los endpoints `POST /import/{employees,clients,products}`.
La ruta solo recibe filas, valida transporte y delega aquí. Toda la lógica
(coerción de tipos, instanciación de modelos ORM, persistencia, agregación
de errores) vive en este módulo para que pueda reutilizarse desde un wizard
de onboarding, un workflow batch o tests sin pasar por HTTP.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.crm import Client
from app.db.models.hr import Employee, Payroll
from app.db.models.inventory import Product


@dataclass
class BulkImportResult:
    """Resultado de un import bulk fila a fila.

    - `created`: filas insertadas con éxito.
    - `errors`: lista de errores estructurados con `row` (1-based, +1 por
      la cabecera) y `reason`.
    - `skipped`: filas saltadas por validación previa (e.g. campo
      obligatorio vacío). NOTA: cada skip también queda registrado en
      `errors` para compatibilidad con la API histórica.
    """

    created: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    skipped: int = 0


def _coerce(value: str | None, typ: type):
    """Convierte `value` al tipo `typ`; devuelve `None` ante error o vacío."""
    if value == "" or value is None:
        return None
    try:
        return typ(value)
    except (ValueError, TypeError):
        return None


async def import_employees_rows(
    rows: list[dict[str, str]],
    tenant_id: UUID,
    db: AsyncSession,
) -> BulkImportResult:
    """Persiste filas de empleados. Hace `commit` al final."""
    result = BulkImportResult()
    for i, row in enumerate(rows):
        name = row.get("nombre") or row.get("name") or ""
        if not name.strip():
            result.errors.append({"row": i + 2, "reason": "El campo 'nombre' es obligatorio"})
            result.skipped += 1
            continue
        try:
            emp = Employee(
                tenant_id=tenant_id,
                name=name.strip(),
                nif=row.get("nif") or None,
                email=row.get("email") or None,
                department=row.get("departamento") or row.get("department") or None,
                role=row.get("rol") or row.get("role") or None,
                base_salary=_coerce(row.get("salario_base") or row.get("base_salary") or "", float),
                irpf_rate=_coerce(row.get("irpf") or row.get("irpf_rate") or "", float),
                status=row.get("estado") or row.get("status") or "active",
            )
            db.add(emp)
            await db.flush()
            result.created += 1
        except Exception as e:  # noqa: BLE001 — agregamos al reporte por fila
            result.errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return result


async def import_clients_rows(
    rows: list[dict[str, str]],
    tenant_id: UUID,
    db: AsyncSession,
) -> BulkImportResult:
    """Persiste filas de clientes. Hace `commit` al final."""
    result = BulkImportResult()
    for i, row in enumerate(rows):
        name = row.get("nombre") or row.get("name") or ""
        if not name.strip():
            result.errors.append({"row": i + 2, "reason": "El campo 'nombre' es obligatorio"})
            result.skipped += 1
            continue
        try:
            client = Client(
                tenant_id=tenant_id,
                name=name.strip(),
                nif=row.get("nif") or None,
                email=row.get("email") or None,
                phone=row.get("telefono") or row.get("phone") or None,
                address=row.get("direccion") or row.get("address") or None,
                city=row.get("ciudad") or row.get("city") or None,
                postal_code=row.get("codigo_postal") or row.get("postal_code") or None,
                client_type=row.get("tipo") or row.get("client_type") or "customer",
            )
            db.add(client)
            await db.flush()
            result.created += 1
        except Exception as e:  # noqa: BLE001
            result.errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return result


async def import_products_rows(
    rows: list[dict[str, str]],
    tenant_id: UUID,
    db: AsyncSession,
) -> BulkImportResult:
    """Persiste filas de productos. Hace `commit` al final."""
    result = BulkImportResult()
    for i, row in enumerate(rows):
        name = row.get("nombre") or row.get("name") or ""
        if not name.strip():
            result.errors.append({"row": i + 2, "reason": "El campo 'nombre' es obligatorio"})
            result.skipped += 1
            continue
        try:
            product = Product(
                tenant_id=tenant_id,
                name=name.strip(),
                sku=row.get("sku") or None,
                description=row.get("descripcion") or row.get("description") or None,
                price=_coerce(row.get("precio") or row.get("price") or "0", float) or 0,
                tax_percentage=_coerce(row.get("iva") or row.get("tax_percentage") or "21", float) or 21.0,
                stock_quantity=_coerce(row.get("stock") or row.get("stock_quantity") or "0", int) or 0,
            )
            db.add(product)
            await db.flush()
            result.created += 1
        except Exception as e:  # noqa: BLE001
            result.errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return result


def _parse_dt(s: str | None) -> datetime | None:
    """Parsea una fecha de migración (ISO o dd/mm/aaaa) a datetime UTC."""
    if not s:
        return None
    s = str(s).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


async def _resolve_employee(db, tenant_id, row):
    """Localiza el empleado por NIF o por nombre exacto. No lo crea."""
    nif = (row.get("nif") or "").strip() or None
    name = (row.get("empleado") or row.get("nombre") or row.get("name") or "").strip() or None
    emp = None
    if nif:
        r = await db.execute(select(Employee).where(Employee.tenant_id == tenant_id, Employee.nif == nif))
        emp = r.scalars().first()
    if emp is None and name:
        r = await db.execute(
            select(Employee).where(Employee.tenant_id == tenant_id, func.lower(Employee.name) == name.lower())
        )
        emp = r.scalars().first()
    return emp


async def import_payrolls_rows(
    rows: list[dict[str, str]],
    tenant_id: UUID,
    db: AsyncSession,
) -> BulkImportResult:
    """Importa nóminas HISTÓRICAS al migrar desde otro programa.

    Migración ≠ generación: se PRESERVAN los importes del programa de origen
    (no se recalcula nada). El empleado debe existir previamente (importa la
    plantilla antes). Idempotente por (empleado, período): no duplica una
    nómina ya migrada, de modo que reejecutar la migración es seguro.

    Columnas aceptadas (es/en): nif|empleado|nombre, periodo (YYYY-MM) o
    periodo_inicio/periodo_fin, fecha_emision, salario_base, bruto, irpf,
    deducciones, liquido|neto, estado.
    """
    result = BulkImportResult()
    for i, row in enumerate(rows):
        emp = await _resolve_employee(db, tenant_id, row)
        if emp is None:
            result.errors.append(
                {"row": i + 2, "reason": "Empleado no encontrado (impórtalo antes; usa nif o nombre exacto)"}
            )
            result.skipped += 1
            continue

        p_start = _parse_dt(row.get("periodo_inicio") or row.get("period_start"))
        p_end = _parse_dt(row.get("periodo_fin") or row.get("period_end"))
        # Atajo de migración: "periodo" = "YYYY-MM" → deriva inicio/fin del mes.
        if (p_start is None or p_end is None) and (row.get("periodo") or row.get("mes")):
            try:
                ym = str(row.get("periodo") or row.get("mes")).strip()
                y, m = int(ym[:4]), int(ym[5:7])
                p_start = datetime(y, m, 1, tzinfo=UTC)
                p_end = datetime(y, m, monthrange(y, m)[1], tzinfo=UTC)
            except (ValueError, IndexError):
                pass
        if p_start is None or p_end is None:
            result.errors.append(
                {"row": i + 2, "reason": "Falta el período (periodo_inicio/periodo_fin o periodo YYYY-MM)"}
            )
            result.skipped += 1
            continue

        issue = _parse_dt(row.get("fecha_emision") or row.get("issue_date")) or p_end
        base = _coerce(row.get("salario_base") or row.get("base_salary") or "", float)
        net = _coerce(row.get("liquido") or row.get("neto") or row.get("net_salary") or "", float)
        if base is None or net is None:
            result.errors.append({"row": i + 2, "reason": "Faltan importes obligatorios (salario_base y liquido/neto)"})
            result.skipped += 1
            continue

        # Idempotencia: una nómina por (empleado, período).
        dup = await db.execute(
            select(Payroll.id)
            .where(
                Payroll.tenant_id == tenant_id,
                Payroll.employee_id == emp.id,
                Payroll.period_start == p_start,
                Payroll.period_end == p_end,
            )
            .limit(1)
        )
        if dup.scalar_one_or_none() is not None:
            result.skipped += 1
            continue

        try:
            pay = Payroll(
                tenant_id=tenant_id,
                employee_id=emp.id,
                period_start=p_start,
                period_end=p_end,
                issue_date=issue,
                base_salary=base,
                gross_salary=_coerce(row.get("bruto") or row.get("gross_salary") or "", float),
                irpf=_coerce(row.get("irpf") or "", float) or 0,
                deductions=_coerce(row.get("deducciones") or row.get("deductions") or "", float) or 0,
                net_salary=net,
                # Históricas: por defecto "paid" (ya procesadas en el sistema previo).
                status=row.get("estado") or row.get("status") or "paid",
            )
            db.add(pay)
            await db.flush()
            result.created += 1
        except Exception as e:  # noqa: BLE001
            result.errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return result


async def _resolve_client(db, tenant_id, nif, name):
    """Localiza un Client (cliente o proveedor) por NIF o nombre exacto."""
    client = None
    if nif:
        r = await db.execute(select(Client).where(Client.tenant_id == tenant_id, Client.nif == nif))
        client = r.scalars().first()
    if client is None and name:
        r = await db.execute(
            select(Client).where(Client.tenant_id == tenant_id, func.lower(Client.name) == name.lower())
        )
        client = r.scalars().first()
    return client


async def import_invoices_rows(
    rows: list[dict[str, str]],
    tenant_id: UUID,
    db: AsyncSession,
) -> BulkImportResult:
    """Importa facturas HISTÓRICAS al migrar desde otro programa.

    Migración fiel:
      - PRESERVA el número y los importes de origen (no recalcula, no re-numera).
      - NO encadena Verifactu (son facturas previas al sistema; encadenarlas
        falsearía la cadena) ni genera asientos (el libro diario se migra aparte).
      - Por lo anterior, con VeriFactu ACTIVO (voluntary) las emitidas se
        RECHAZAN: importarlas sería un bypass de la cadena. La migración se
        hace antes de activar el modo.
      - El cliente/proveedor debe existir (impórtalos antes).
      - Idempotente: para emitidas por (tipo, número); para recibidas por
        (tipo, número, proveedor) —el número de la recibida lo pone el proveedor.

    Columnas (es/en): numero|invoice_number, tipo (issued|received), nif|cliente|
    proveedor|nombre, fecha|issue_date, base|base_imponible, iva|cuota_iva,
    total, estado.
    """
    from app.db.models.billing import Invoice
    from app.services.billing.constants import EMITTED_INVOICE_TYPES
    from app.services.billing.verifactu_mode import should_remit

    verifactu_activo = await should_remit(db, tenant_id=tenant_id)

    result = BulkImportResult()
    for i, row in enumerate(rows):
        number = (row.get("numero") or row.get("número") or row.get("invoice_number") or "").strip() or None
        if not number:
            result.errors.append({"row": i + 2, "reason": "Falta el número de factura"})
            result.skipped += 1
            continue

        itype = (row.get("tipo") or row.get("invoice_type") or "issued").strip().lower()
        if itype not in ("issued", "received"):
            itype = "issued"

        nif = (row.get("nif") or row.get("nif_cliente") or row.get("nif_proveedor") or "").strip() or None
        name = (
            row.get("cliente") or row.get("proveedor") or row.get("nombre") or row.get("name") or ""
        ).strip() or None
        party = await _resolve_client(db, tenant_id, nif, name)
        if party is None:
            result.errors.append(
                {
                    "row": i + 2,
                    "reason": f"Cliente/proveedor no encontrado para '{name or nif or '?'}' (impórtalo antes)",
                }
            )
            result.skipped += 1
            continue

        d = _parse_dt(row.get("fecha") or row.get("date") or row.get("issue_date"))
        if d is None:
            result.errors.append({"row": i + 2, "reason": "Falta la fecha de la factura"})
            result.skipped += 1
            continue

        base = _coerce(row.get("base") or row.get("base_imponible") or row.get("amount_base") or "", float)
        tax = _coerce(row.get("iva") or row.get("cuota_iva") or row.get("tax_amount") or "", float)
        total = _coerce(row.get("total") or row.get("amount_total") or "", float)
        if total is None and base is not None:
            total = (base or 0) + (tax or 0)
        if total is None:
            result.errors.append({"row": i + 2, "reason": "Falta el importe total"})
            result.skipped += 1
            continue

        # Idempotencia con la clave de negocio correcta por tipo.
        conds = [
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_number == number,
            Invoice.invoice_type == itype,
        ]
        if itype == "received":
            conds.append(Invoice.client_id == party.id)
        dup = await db.execute(select(Invoice.id).where(*conds).limit(1))
        if dup.scalar_one_or_none() is not None:
            result.skipped += 1
            continue

        # Verifactu activo → una "emitida importada" sería un bypass de la
        # cadena (doble uso, art. 201 bis LGT): cualquier venta real podría
        # colarse como "migración" sin registro. La migración de históricas se
        # hace ANTES de activar VeriFactu (las previas no las expidió este SIF
        # y por eso no se encadenan — ver docstring).
        if verifactu_activo and itype in EMITTED_INVOICE_TYPES:
            result.errors.append(
                {
                    "row": i + 2,
                    "reason": "VeriFactu activo: las facturas emitidas no se importan "
                    "(sería un bypass de la cadena). Migra antes de activar VeriFactu "
                    "o emite la factura desde el sistema.",
                }
            )
            result.skipped += 1
            continue

        try:
            inv = Invoice(
                tenant_id=tenant_id,
                client_id=party.id,
                invoice_number=number,
                date=d,
                status=row.get("estado") or row.get("status") or "paid",
                invoice_type=itype,
                amount_base=base if base is not None else (total - (tax or 0)),
                tax_amount=tax if tax is not None else 0,
                amount_total=total,
                notes="Migrada del sistema anterior",
            )
            db.add(inv)
            await db.flush()
            result.created += 1
        except Exception as e:  # noqa: BLE001
            result.errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return result


async def import_bank_transactions_rows(
    rows: list[dict[str, str]],
    tenant_id: UUID,
    db: AsyncSession,
) -> BulkImportResult:
    """Importa movimientos bancarios HISTÓRICOS (carga de extracto en migración).

    El importe va CON SIGNO (+ ingreso / − cargo). Quedan sin conciliar
    (`status='unreconciled'`) para que el usuario los case con facturas después.

    Idempotente por (fecha, importe, concepto[, saldo]): recargar el mismo
    extracto no duplica movimientos. Nota: dos cargos legítimamente idénticos el
    mismo día (igual importe, concepto y saldo) se tratarían como uno — es el
    precio de no tener referencia bancaria única en el modelo; aceptable para
    una carga de migración.

    Columnas (es/en): fecha|date, concepto|descripcion|description,
    importe|amount, saldo|balance.
    """
    from app.db.models.accounting import BankTransaction

    result = BulkImportResult()
    for i, row in enumerate(rows):
        d = _parse_dt(row.get("fecha") or row.get("date"))
        desc = (
            row.get("concepto") or row.get("descripcion") or row.get("descripción") or row.get("description") or ""
        ).strip()
        amount = _coerce(row.get("importe") or row.get("amount") or "", float)
        if d is None or not desc or amount is None:
            result.errors.append({"row": i + 2, "reason": "Faltan campos obligatorios (fecha, concepto, importe)"})
            result.skipped += 1
            continue

        desc = desc[:255]
        balance = _coerce(row.get("saldo") or row.get("balance") or "", float)
        d_date = d.date()

        conds = [
            BankTransaction.tenant_id == tenant_id,
            BankTransaction.date == d_date,
            BankTransaction.amount == amount,
            BankTransaction.description == desc,
        ]
        if balance is not None:
            conds.append(BankTransaction.balance == balance)
        dup = await db.execute(select(BankTransaction.id).where(*conds).limit(1))
        if dup.scalar_one_or_none() is not None:
            result.skipped += 1
            continue

        try:
            tx = BankTransaction(
                tenant_id=tenant_id,
                date=d_date,
                description=desc,
                amount=amount,
                balance=balance,
                status="unreconciled",
            )
            db.add(tx)
            await db.flush()
            result.created += 1
        except Exception as e:  # noqa: BLE001
            result.errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return result
