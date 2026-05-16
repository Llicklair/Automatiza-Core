"""Bulk CSV import endpoints for employees, clients and products."""
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.crm import Client
from app.db.models.hr import Employee
from app.db.models.inventory import Product

router = APIRouter(prefix="/import", tags=["import"])


class ImportResult(BaseModel):
    imported: int
    errors: list[dict[str, Any]]


def _coerce(value: str, typ: type):
    if value == "" or value is None:
        return None
    try:
        return typ(value)
    except (ValueError, TypeError):
        return None


# ── Employees ─────────────────────────────────────────────────────────────────

@router.post("/employees", response_model=ImportResult)
async def import_employees(
    body: dict[str, list[dict[str, str]]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    rows: list[dict[str, str]] = body.get("rows", [])
    ok = 0
    errors: list[dict] = []

    for i, row in enumerate(rows):
        name = row.get("nombre") or row.get("name") or ""
        if not name.strip():
            errors.append({"row": i + 2, "reason": "El campo 'nombre' es obligatorio"})
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
            ok += 1
        except Exception as e:
            errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return ImportResult(imported=ok, errors=errors)


# ── Clients ───────────────────────────────────────────────────────────────────

@router.post("/clients", response_model=ImportResult)
async def import_clients(
    body: dict[str, list[dict[str, str]]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    rows: list[dict[str, str]] = body.get("rows", [])
    ok = 0
    errors: list[dict] = []

    for i, row in enumerate(rows):
        name = row.get("nombre") or row.get("name") or ""
        if not name.strip():
            errors.append({"row": i + 2, "reason": "El campo 'nombre' es obligatorio"})
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
            ok += 1
        except Exception as e:
            errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return ImportResult(imported=ok, errors=errors)


# ── Products ──────────────────────────────────────────────────────────────────

@router.post("/products", response_model=ImportResult)
async def import_products(
    body: dict[str, list[dict[str, str]]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    rows: list[dict[str, str]] = body.get("rows", [])
    ok = 0
    errors: list[dict] = []

    for i, row in enumerate(rows):
        name = row.get("nombre") or row.get("name") or ""
        if not name.strip():
            errors.append({"row": i + 2, "reason": "El campo 'nombre' es obligatorio"})
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
            ok += 1
        except Exception as e:
            errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return ImportResult(imported=ok, errors=errors)
