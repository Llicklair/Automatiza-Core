import logging
import os
import uuid as uuid_mod
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)

from app.api.v1.schemas.erp import (
    ClientCreate,
    ClientResponse,
    ClientUpdate,
    InvoiceCreate,
    InvoiceResponse,
    InvoiceStatusUpdate,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    RecurringInvoiceCreate,
    RecurringInvoiceResponse,
    RecurringInvoiceUpdate,
    SalesOrderCreate,
    SalesOrderResponse,
    SalesOrderUpdate,
    StockMovementCreate,
    StockMovementResponse,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Client, Invoice, InvoiceLine, Product, PurchaseOrder, PurchaseOrderLine, RecurringInvoice, SalesOrder, SalesOrderLine, StockMovement, Tenant, TenantDocument, User
from app.services.event_bus import emit_event
from app.services.pdf_service import generate_invoice_pdf

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")


# ─── Clientes (CRM) ─────────────────────────────────────────────────────────

@router.get("/clients", response_model=list[ClientResponse], tags=["erp"])
async def list_clients(
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    client_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Client).where(Client.tenant_id == current_user.tenant_id)
    if client_type:
        query = query.where(Client.client_type == client_type)
    query = query.order_by(desc(Client.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/clients", response_model=ClientResponse, status_code=status.HTTP_201_CREATED, tags=["erp"])
async def create_client(
    payload: ClientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_client = Client(
        tenant_id=current_user.tenant_id,
        **payload.model_dump()
    )
    db.add(new_client)
    try:
        await db.commit()
        await db.refresh(new_client)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Ya existe un cliente con ese NIF o email")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error guardando cliente: %s", e)
        raise HTTPException(status_code=500, detail="Error al guardar el cliente")

    # Emitir evento para disparar automatizaciones (no crítico)
    try:
        await emit_event(
            db=db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            event_name="client_created",
            context={"client_id": str(new_client.id), "client_name": new_client.name, "nif": new_client.nif},
        )
    except Exception:
        logger.warning("emit_event client_created falló — no es crítico")

    return new_client


@router.patch("/clients/{client_id}", response_model=ClientResponse, tags=["erp"])
async def update_client(
    client_id: UUID,
    payload: ClientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == current_user.tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(client, key, value)
    try:
        await db.commit()
        await db.refresh(client)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error actualizando cliente %s: %s", client_id, e)
        raise HTTPException(status_code=500, detail="Error al actualizar el cliente")
    return client


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
async def delete_client(
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == current_user.tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    try:
        await db.delete(client)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error eliminando cliente %s: %s", client_id, e)
        raise HTTPException(status_code=500, detail="Error al eliminar el cliente")


@router.get("/clients/{client_id}/invoices", response_model=list[InvoiceResponse], tags=["erp"])
async def list_client_invoices(
    client_id: UUID,
    skip: int = 0,
    limit: int = Query(default=100, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve todas las facturas de un cliente específico dentro del tenant."""
    # Verificar que el cliente pertenece al tenant
    client_result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.tenant_id == current_user.tenant_id,
        )
    )
    client = client_result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    query = (
        select(Invoice)
        .options(
            joinedload(Invoice.client),
            joinedload(Invoice.lines),
        )
        .where(
            Invoice.client_id == client_id,
            Invoice.tenant_id == current_user.tenant_id,
        )
        .order_by(desc(Invoice.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    # joinedload(Invoice.lines) devuelve posibles filas duplicadas; unique() es obligatorio
    return result.unique().scalars().all()


# ─── Catálogo (Productos) ────────────────────────────────────────────────────

@router.get("/products", response_model=list[ProductResponse], tags=["erp"])
async def list_products(
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Product)
        .where(Product.tenant_id == current_user.tenant_id)
        .order_by(desc(Product.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/products/{product_id}", response_model=ProductResponse, tags=["erp"])
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == current_user.tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == current_user.tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    await db.delete(product)
    await db.commit()


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, tags=["erp"])
async def create_product(
    payload: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_product = Product(
        tenant_id=current_user.tenant_id,
        **payload.model_dump()
    )
    db.add(new_product)
    await db.commit()
    await db.refresh(new_product)
    return new_product


# ─── Facturas (Billing) ──────────────────────────────────────────────────────

@router.get("/invoices", response_model=list[InvoiceResponse], tags=["erp"])
async def list_invoices(
    skip: int = 0,
    limit: int = Query(default=50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Invoice)
        .options(
            joinedload(Invoice.client),
            joinedload(Invoice.lines),
        )
        .where(Invoice.tenant_id == current_user.tenant_id)
        .order_by(desc(Invoice.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.unique().scalars().all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse, tags=["erp"])
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el detalle de una factura (con cliente y líneas)."""
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id)
    )
    invoice = result.unique().scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    return invoice


@router.patch("/invoices/{invoice_id}/status", response_model=InvoiceResponse, tags=["erp"])
async def update_invoice_status(
    invoice_id: UUID,
    payload: InvoiceStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cambia el estado de una factura: draft → pending → paid | cancelled."""
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id)
    )
    invoice = result.unique().scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    allowed = {"draft", "pending", "paid", "cancelled"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail=f"Estado no válido. Opciones: {allowed}")
    invoice.status = payload.status
    await db.commit()
    await db.refresh(invoice)
    result2 = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id)
    )
    return result2.unique().scalar_one()


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
async def delete_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    await db.delete(invoice)
    await db.commit()


@router.post("/clients/{client_id}/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED, tags=["erp"])
async def create_invoice(
    client_id: UUID,
    payload: InvoiceCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Descomponemos el payload
    payload_dict = payload.model_dump()
    lines_data = payload_dict.pop("lines", [])
    
    # Ignorar posibles campos totalizadores de frontend
    payload_dict.pop("amount_base", None)
    payload_dict.pop("tax_amount", None)
    payload_dict.pop("amount_total", None)

    # 1. Crear el padre (Invoice) con bases en cero
    new_invoice = Invoice(
        tenant_id=current_user.tenant_id,
        client_id=client_id,
        amount_base=0.0,
        tax_amount=0.0,
        amount_total=0.0,
        **payload_dict
    )
    db.add(new_invoice)
    await db.commit()
    await db.refresh(new_invoice)

    # 2. Insertar las InvoiceLine y calcular sumatorios
    total_base = 0.0
    total_tax = 0.0

    for line_data in lines_data:
        # Recuperamos datos de base
        qty = float(line_data.get("quantity", 1))
        uprice = float(line_data.get("unit_price", 0))
        discount_perc = float(line_data.get("discount_percentage", 0))
        tax_perc = float(line_data.get("tax_percentage", 21))
        
        # Calcular línea individual
        line_base = qty * uprice
        if discount_perc > 0:
            line_base -= line_base * (discount_perc / 100)
            
        line_tax = line_base * (tax_perc / 100)
        line_total = line_base + line_tax
        
        # Acumular globales
        total_base += line_base
        total_tax += line_tax
        
        # Guardar línea
        inv_line = InvoiceLine(
            invoice_id=new_invoice.id,
            product_id=line_data.get("product_id"),
            description=line_data.get("description"),
            quantity=qty,
            unit_price=uprice,
            discount_percentage=discount_perc,
            tax_percentage=tax_perc,
            total=line_total
        )
        db.add(inv_line)

    # 3. Actualizar el padre con los cálculos sumados
    new_invoice.amount_base = total_base
    new_invoice.tax_amount = total_tax
    new_invoice.amount_total = total_base + total_tax
    
    await db.commit()

    # 4. Refrescar Invoice para devolver con joins
    result = await db.execute(
        select(Invoice)
        .options(
            joinedload(Invoice.client),
            joinedload(Invoice.lines)
        )
        .where(Invoice.id == new_invoice.id)
    )
    final_invoice = result.unique().scalar_one()

    # 5. Generar PDF y guardarlo en TenantDocument (en background)
    background_tasks.add_task(
        _generate_and_save_invoice_pdf,
        invoice=final_invoice,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )

    # 6. Emitir evento para disparar automatizaciones event_based
    await emit_event(
        db=db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        event_name="invoice_created",
        context={
            "invoice_id": str(final_invoice.id),
            "invoice_number": final_invoice.invoice_number,
            "amount_total": float(final_invoice.amount_total or 0),
            "client_name": final_invoice.client.name if final_invoice.client else None,
            "status": final_invoice.status,
        },
    )

    return final_invoice


async def _generate_and_save_invoice_pdf(invoice, tenant_id, user_id):
    """Genera el PDF de la factura y lo registra como TenantDocument."""
    from app.db.base import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as session:
            tenant_obj = await session.get(Tenant, tenant_id)

        company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
        company_nif = tenant_obj.nif if tenant_obj else "B00000000"

        invoice_data = {
            "number": invoice.invoice_number or f"F-{str(invoice.id)[:8].upper()}",
            "date": invoice.date.isoformat() if invoice.date else "",
            "amount_base": float(invoice.amount_base or 0),
            "tax_amount": float(invoice.tax_amount or 0),
            "amount_total": float(invoice.amount_total or 0),
            "client": {
                "name": invoice.client.name if invoice.client else "Cliente",
                "nif": invoice.client.nif if invoice.client else "",
                "email": invoice.client.email if invoice.client else "",
                "address": invoice.client.address if invoice.client else "",
            },
            "company": {
                "name": company_name,
                "nif": company_nif,
                "address": "Calle Principal, 1 · Madrid",
                "phone": "",
            },
            "lines": [
                {
                    "description": line.description or "",
                    "quantity": float(line.quantity or 1),
                    "unit_price": float(line.unit_price or 0),
                    "tax_percentage": float(line.tax_percentage or 21),
                    "total": float(line.total or 0),
                }
                for line in (invoice.lines or [])
            ],
            "notes": invoice.notes or "",
            "payment_terms": invoice.terms or "",
        }

        pdf_bytes = generate_invoice_pdf(invoice_data)
        file_name = f"Factura_{invoice_data['number']}.pdf"

        # Guardar en disco
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        unique_name = f"{uuid_mod.uuid4().hex}.pdf"
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        # Registrar en TenantDocument
        async with AsyncSessionLocal() as session:
            doc = TenantDocument(
                tenant_id=tenant_id,
                uploaded_by=user_id,
                file_name=file_name,
                file_type="application/pdf",
                file_path=file_path,
                file_size=len(pdf_bytes),
                category="Facturas",
                status="ready",
            )
            session.add(doc)
            await session.commit()
    except Exception as e:
        print(f"[PDF] Error generando PDF de factura: {e}")


@router.get("/invoices/{invoice_id}/pdf", tags=["erp"])
async def download_invoice_pdf(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga el PDF de una factura específica generándolo al vuelo."""
    # Cargar factura y tenant (empresa emisora)
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == current_user.tenant_id)
    )
    invoice = result.unique().scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    tenant_result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant_obj = tenant_result.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
    company_nif = tenant_obj.nif if tenant_obj else "B00000000"
    invoice_data = {
        "number": invoice.invoice_number or f"F-{str(invoice.id)[:8].upper()}",
        "date": invoice.date.isoformat() if invoice.date else "",
        "amount_base": float(invoice.amount_base or 0),
        "tax_amount": float(invoice.tax_amount or 0),
        "amount_total": float(invoice.amount_total or 0),
        "client": {
            "name": invoice.client.name if invoice.client else "Cliente",
            "nif": invoice.client.nif if invoice.client else "",
            "email": invoice.client.email if invoice.client else "",
            "address": invoice.client.address if invoice.client else "",
        },
        "company": {
            "name": company_name,
            "nif": company_nif,
            "address": "Calle Principal, 1 · Madrid",
            "phone": "",
        },
        "lines": [
            {
                "description": line.description or "",
                "quantity": float(line.quantity or 1),
                "unit_price": float(line.unit_price or 0),
                "tax_percentage": float(line.tax_percentage or 21),
                "total": float(line.total or 0),
            }
            for line in (invoice.lines or [])
        ],
        "notes": invoice.notes or "",
        "payment_terms": invoice.terms or "",
    }

    pdf_bytes = generate_invoice_pdf(invoice_data)
    file_name = f"Factura_{invoice_data['number']}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


# ─── Stock / Inventario ──────────────────────────────────────────────────────

@router.get("/products/{product_id}/stock-movements", response_model=list[StockMovementResponse], tags=["inventory"])
async def list_stock_movements(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(StockMovement)
        .where(StockMovement.product_id == product_id, StockMovement.tenant_id == current_user.tenant_id)
        .order_by(desc(StockMovement.created_at))
        .limit(100)
    )
    return result.scalars().all()


@router.post("/products/{product_id}/stock-movements", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED, tags=["inventory"])
async def create_stock_movement(
    product_id: UUID,
    payload: StockMovementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == current_user.tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Calcular nuevo stock según tipo de movimiento
    if payload.movement_type == "entrada":
        new_stock = int(product.stock_quantity) + abs(payload.quantity)
    elif payload.movement_type == "salida":
        new_stock = int(product.stock_quantity) - abs(payload.quantity)
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="Stock insuficiente")
    else:  # ajuste
        new_stock = payload.quantity

    product.stock_quantity = new_stock

    movement = StockMovement(
        tenant_id=current_user.tenant_id,
        product_id=product_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        stock_after=new_stock,
        reference=payload.reference,
        notes=payload.notes,
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    return movement


# ─── Pedidos de Venta ────────────────────────────────────────────────────────

@router.get("/orders", response_model=list[SalesOrderResponse], tags=["erp"])
async def list_sales_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.tenant_id == current_user.tenant_id)
        .options(
            joinedload(SalesOrder.client),
            joinedload(SalesOrder.lines),
        )
        .order_by(desc(SalesOrder.created_at))
    )
    return result.unique().scalars().all()


@router.post("/orders", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED, tags=["erp"])
async def create_sales_order(
    payload: SalesOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Generar número de pedido
    from datetime import datetime as dt
    order_number = payload.order_number or f"PED-{dt.now().strftime('%Y%m%d%H%M%S')}"

    # Calcular totales
    amount_base = 0.0
    tax_amount = 0.0
    for line in payload.lines:
        base = line.quantity * line.unit_price * (1 - line.discount_percentage / 100)
        tax = base * (line.tax_percentage / 100)
        amount_base += base
        tax_amount += tax

    order = SalesOrder(
        tenant_id=current_user.tenant_id,
        client_id=payload.client_id,
        order_number=order_number,
        date=payload.date or __import__('datetime').datetime.now(__import__('datetime').timezone.utc),
        expected_delivery=payload.expected_delivery,
        notes=payload.notes,
        quote_id=payload.quote_id,
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_base + tax_amount, 2),
    )
    db.add(order)
    await db.flush()

    for line_data in payload.lines:
        base = line_data.quantity * line_data.unit_price * (1 - line_data.discount_percentage / 100)
        tax = base * (line_data.tax_percentage / 100)
        line = SalesOrderLine(
            order_id=order.id,
            product_id=line_data.product_id,
            description=line_data.description,
            quantity=line_data.quantity,
            unit_price=line_data.unit_price,
            discount_percentage=line_data.discount_percentage,
            tax_percentage=line_data.tax_percentage,
            total=round(base + tax, 2),
        )
        db.add(line)

    await db.commit()
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == order.id)
        .options(joinedload(SalesOrder.client), joinedload(SalesOrder.lines))
    )
    return result.unique().scalar_one()


@router.patch("/orders/{order_id}", response_model=SalesOrderResponse, tags=["erp"])
async def update_sales_order(
    order_id: UUID,
    payload: SalesOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id, SalesOrder.tenant_id == current_user.tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    await db.commit()
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == order_id)
        .options(joinedload(SalesOrder.client), joinedload(SalesOrder.lines))
    )
    return result.unique().scalar_one()


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
async def delete_sales_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id, SalesOrder.tenant_id == current_user.tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    await db.delete(order)
    await db.commit()


# ─── Pedidos de Compra ───────────────────────────────────────────────────────

@router.get("/purchase-orders", response_model=list[PurchaseOrderResponse], tags=["erp"])
async def list_purchase_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.tenant_id == current_user.tenant_id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
        .order_by(desc(PurchaseOrder.created_at))
    )
    return result.unique().scalars().all()


@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED, tags=["erp"])
async def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime as dt
    order_number = payload.order_number or f"PC-{dt.now().strftime('%Y%m%d%H%M%S')}"

    amount_base = 0.0
    tax_amount = 0.0
    for line in payload.lines:
        base = float(line.quantity) * float(line.unit_price)
        tax = base * (float(line.tax_percentage) / 100)
        amount_base += base
        tax_amount += tax

    order = PurchaseOrder(
        tenant_id=current_user.tenant_id,
        supplier_id=payload.supplier_id,
        order_number=order_number,
        date=payload.date or dt.now(__import__('datetime').timezone.utc),
        expected_delivery=payload.expected_delivery,
        notes=payload.notes,
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_base + tax_amount, 2),
    )
    db.add(order)
    await db.flush()

    for line_data in payload.lines:
        base = float(line_data.quantity) * float(line_data.unit_price)
        tax = base * (float(line_data.tax_percentage) / 100)
        line = PurchaseOrderLine(
            order_id=order.id,
            product_id=line_data.product_id,
            description=line_data.description,
            quantity=line_data.quantity,
            unit_price=line_data.unit_price,
            tax_percentage=line_data.tax_percentage,
            total=round(base + tax, 2),
        )
        db.add(line)

    await db.commit()
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order.id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
    )
    return result.unique().scalar_one()


@router.patch("/purchase-orders/{order_id}", response_model=PurchaseOrderResponse, tags=["erp"])
async def update_purchase_order(
    order_id: UUID,
    payload: PurchaseOrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id, PurchaseOrder.tenant_id == current_user.tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido de compra no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(order, field, value)
    await db.commit()
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order_id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
    )
    return result.unique().scalar_one()


@router.delete("/purchase-orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
async def delete_purchase_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseOrder).where(PurchaseOrder.id == order_id, PurchaseOrder.tenant_id == current_user.tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido de compra no encontrado")
    await db.delete(order)
    await db.commit()


# ─── Facturación Recurrente ──────────────────────────────────────────────────

@router.get("/recurring-invoices", response_model=list[RecurringInvoiceResponse], tags=["erp"])
async def list_recurring_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.tenant_id == current_user.tenant_id)
        .options(joinedload(RecurringInvoice.client))
        .order_by(desc(RecurringInvoice.created_at))
    )
    return result.unique().scalars().all()


@router.post("/recurring-invoices", response_model=RecurringInvoiceResponse, status_code=status.HTTP_201_CREATED, tags=["erp"])
async def create_recurring_invoice(
    payload: RecurringInvoiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rec = RecurringInvoice(
        tenant_id=current_user.tenant_id,
        client_id=payload.client_id,
        name=payload.name,
        interval_type=payload.interval_type,
        next_run_date=payload.next_run_date,
        notes=payload.notes,
        terms=payload.terms,
        lines_json=[line.model_dump() for line in payload.lines],
    )
    db.add(rec)
    await db.commit()
    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec.id)
        .options(joinedload(RecurringInvoice.client))
    )
    return result.unique().scalar_one()


@router.patch("/recurring-invoices/{rec_id}", response_model=RecurringInvoiceResponse, tags=["erp"])
async def update_recurring_invoice(
    rec_id: UUID,
    payload: RecurringInvoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RecurringInvoice).where(RecurringInvoice.id == rec_id, RecurringInvoice.tenant_id == current_user.tenant_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Factura recurrente no encontrada")
    data = payload.model_dump(exclude_unset=True)
    if "lines" in data:
        data["lines_json"] = data.pop("lines")
    for field, value in data.items():
        setattr(rec, field, value)
    await db.commit()
    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec_id)
        .options(joinedload(RecurringInvoice.client))
    )
    return result.unique().scalar_one()


@router.delete("/recurring-invoices/{rec_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["erp"])
async def delete_recurring_invoice(
    rec_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(RecurringInvoice).where(RecurringInvoice.id == rec_id, RecurringInvoice.tenant_id == current_user.tenant_id)
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Factura recurrente no encontrada")
    await db.delete(rec)
    await db.commit()


@router.post("/recurring-invoices/{rec_id}/run", response_model=InvoiceResponse, tags=["erp"])
async def run_recurring_invoice(
    rec_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera manualmente una factura a partir de una plantilla recurrente."""
    import datetime as dt_module

    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.id == rec_id, RecurringInvoice.tenant_id == current_user.tenant_id)
        .options(joinedload(RecurringInvoice.client))
    )
    rec = result.unique().scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Factura recurrente no encontrada")

    now = dt_module.datetime.now(dt_module.timezone.utc)
    invoice_number = f"REC-{now.strftime('%Y%m%d%H%M%S')}"

    amount_base = 0.0
    tax_amount = 0.0
    for line in (rec.lines_json or []):
        base = float(line.get("quantity", 1)) * float(line.get("unit_price", 0))
        tax = base * (float(line.get("tax_percentage", 21)) / 100)
        amount_base += base
        tax_amount += tax

    invoice = Invoice(
        tenant_id=current_user.tenant_id,
        client_id=rec.client_id,
        invoice_number=invoice_number,
        date=now,
        status="draft",
        invoice_type="issued",
        notes=rec.notes,
        terms=rec.terms,
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_base + tax_amount, 2),
    )
    db.add(invoice)
    await db.flush()

    for line in (rec.lines_json or []):
        base = float(line.get("quantity", 1)) * float(line.get("unit_price", 0))
        tax = base * (float(line.get("tax_percentage", 21)) / 100)
        inv_line = InvoiceLine(
            invoice_id=invoice.id,
            description=line.get("description", ""),
            quantity=line.get("quantity", 1),
            unit_price=line.get("unit_price", 0),
            discount_percentage=0,
            tax_percentage=line.get("tax_percentage", 21),
            total=round(base + tax, 2),
        )
        db.add(inv_line)

    # Calcular próxima fecha según intervalo
    interval_map = {"weekly": 7, "monthly": 30, "quarterly": 90, "yearly": 365}
    days = interval_map.get(rec.interval_type, 30)
    rec.last_run_date = now.date()
    rec.next_run_date = (now + dt_module.timedelta(days=days)).date()

    await db.commit()

    res = await db.execute(
        select(Invoice)
        .where(Invoice.id == invoice.id)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
    )
    return res.unique().scalar_one()
