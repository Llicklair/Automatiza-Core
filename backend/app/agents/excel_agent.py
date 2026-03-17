import os
import uuid
import logging
import re
from datetime import datetime, timezone
from pydantic import BaseModel
from sqlalchemy.future import select

from app.db.base import AsyncSessionLocal
from app.db.models.tenant import TenantDocument
from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.hr import Employee, Payroll
from app.db.models.inventory import Product
from app.db.models.accounting import BankTransaction

from langchain_core.messages import SystemMessage, HumanMessage
from app.core.llm_factory import get_llm
import pandas as pd

logger = logging.getLogger(__name__)

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")


class ExcelAgentResult(BaseModel):
    success: bool
    action: str
    output_message: str
    error: str | None = None


def _get_llm():
    return get_llm(temperature=0)


# ─── Keywords to detect which dataset to query ───────────────────────────────
_INTENT_MAP = [
    (["factura", "invoice", "venta", "cobro", "ingreso"], "invoices"),
    (["empleado", "empleada", "trabajador", "plantilla", "rrhh", "personal"], "employees"),
    (["nómina", "nomina", "salario", "sueldo", "pago de empleado"], "payrolls"),
    (["cliente", "client", "cuenta", "crm"], "clients"),
    (["producto", "catalogo", "catálogo", "inventario", "stock", "artículo", "articulo"], "products"),
    (["banco", "bank", "movimiento", "transaccion", "transacción"], "bank"),
]


def _detect_datasets(intent: str) -> list[str]:
    """Return list of dataset keys that match the intent. Falls back to invoices."""
    intent_lower = intent.lower()
    matched = []
    for keywords, key in _INTENT_MAP:
        if any(kw in intent_lower for kw in keywords):
            if key not in matched:
                matched.append(key)
    return matched or ["invoices"]


# ─── DB Fetchers ──────────────────────────────────────────────────────────────

async def _fetch_invoices(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Invoice, Client.name.label("client_name"))
            .join(Client, Invoice.client_id == Client.id)
            .where(Invoice.tenant_id == uuid.UUID(tenant_id))
            .order_by(Invoice.date.desc())
            .limit(500)
        )
        rows = result.all()
    if not rows:
        return pd.DataFrame(columns=["Número", "Cliente", "Fecha", "Vencimiento",
                                      "Base (€)", "IVA (€)", "Total (€)", "Estado"])
    data = []
    for inv, client_name in rows:
        data.append({
            "Número": inv.invoice_number or "",
            "Cliente": client_name or "",
            "Fecha": inv.date.strftime("%d/%m/%Y") if inv.date else "",
            "Vencimiento": inv.due_date.strftime("%d/%m/%Y") if inv.due_date else "",
            "Base (€)": float(inv.amount_base or 0),
            "IVA (€)": float(inv.tax_amount or 0),
            "Total (€)": float(inv.amount_total or 0),
            "Estado": inv.status or "",
        })
    return pd.DataFrame(data)


async def _fetch_clients(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Client)
            .where(Client.tenant_id == uuid.UUID(tenant_id))
            .order_by(Client.name)
            .limit(500)
        )
        clients = result.scalars().all()
    if not clients:
        return pd.DataFrame(columns=["Nombre", "NIF/CIF", "Email", "Ciudad", "Código Postal", "Tipo"])
    data = [{
        "Nombre": c.name or "",
        "NIF/CIF": c.nif or "",
        "Email": c.email or "",
        "Ciudad": c.city or "",
        "Código Postal": c.postal_code or "",
        "Tipo": c.client_type or "",
    } for c in clients]
    return pd.DataFrame(data)


async def _fetch_employees(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Employee)
            .where(Employee.tenant_id == uuid.UUID(tenant_id))
            .order_by(Employee.name)
        )
        employees = result.scalars().all()
    if not employees:
        return pd.DataFrame(columns=["Nombre", "NIF", "Departamento", "Puesto",
                                      "Salario Base (€)", "IRPF (%)", "Estado"])
    data = [{
        "Nombre": e.name or "",
        "NIF": e.nif or "",
        "Departamento": e.department or "",
        "Puesto": e.role or "",
        "Salario Base (€)": float(e.base_salary or 0),
        "IRPF (%)": float(e.irpf_rate or 0),
        "Estado": e.status or "",
    } for e in employees]
    return pd.DataFrame(data)


async def _fetch_payrolls(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Payroll, Employee.name.label("emp_name"))
            .join(Employee, Payroll.employee_id == Employee.id)
            .where(Payroll.tenant_id == uuid.UUID(tenant_id))
            .order_by(Payroll.issue_date.desc())
            .limit(500)
        )
        rows = result.all()
    if not rows:
        return pd.DataFrame(columns=["Empleado", "Período inicio", "Período fin",
                                      "Salario Base (€)", "SS (€)", "IRPF (€)",
                                      "Deducciones (€)", "Neto (€)", "Estado"])
    data = []
    for p, emp_name in rows:
        ss_total = float((p.ss_contingencias_comunes or 0) + (p.ss_desempleo or 0) +
                         (p.ss_formacion_profesional or 0) + (p.ss_mei or 0))
        data.append({
            "Empleado": emp_name or "",
            "Período inicio": p.period_start.strftime("%d/%m/%Y") if p.period_start else "",
            "Período fin": p.period_end.strftime("%d/%m/%Y") if p.period_end else "",
            "Salario Base (€)": float(p.base_salary or 0),
            "SS (€)": ss_total,
            "IRPF (€)": float(p.irpf or 0),
            "Deducciones (€)": float(p.deductions or 0),
            "Neto (€)": float(p.net_salary or 0),
            "Estado": p.status or "",
        })
    return pd.DataFrame(data)


async def _fetch_products(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product)
            .where(Product.tenant_id == uuid.UUID(tenant_id))
            .order_by(Product.name)
            .limit(500)
        )
        products = result.scalars().all()
    if not products:
        return pd.DataFrame(columns=["Nombre", "SKU", "Tipo", "Precio (€)",
                                      "IVA (%)", "Stock", "Descripción"])
    data = [{
        "Nombre": p.name or "",
        "SKU": p.sku or "",
        "Tipo": p.item_type or "",
        "Precio (€)": float(p.price or 0),
        "IVA (%)": float(p.tax_percentage or 0),
        "Stock": int(p.stock_quantity or 0),
        "Descripción": p.description or "",
    } for p in products]
    return pd.DataFrame(data)


async def _fetch_bank(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BankTransaction)
            .where(BankTransaction.tenant_id == uuid.UUID(tenant_id))
            .order_by(BankTransaction.date.desc())
            .limit(500)
        )
        txs = result.scalars().all()
    if not txs:
        return pd.DataFrame(columns=["Fecha", "Concepto", "Importe (€)", "Saldo (€)", "Estado"])
    data = [{
        "Fecha": t.date.strftime("%d/%m/%Y") if t.date else "",
        "Concepto": t.description or "",
        "Importe (€)": float(t.amount or 0),
        "Saldo (€)": float(t.balance or 0),
        "Estado": t.status or "",
    } for t in txs]
    return pd.DataFrame(data)


_FETCHER_MAP = {
    "invoices": _fetch_invoices,
    "clients": _fetch_clients,
    "employees": _fetch_employees,
    "payrolls": _fetch_payrolls,
    "products": _fetch_products,
    "bank": _fetch_bank,
}

_SHEET_NAMES = {
    "invoices": "Facturas",
    "clients": "Clientes",
    "employees": "Empleados",
    "payrolls": "Nóminas",
    "products": "Catálogo",
    "bank": "Movimientos banco",
}


# ─── Excel writer with basic formatting ──────────────────────────────────────

def _write_excel(sheets: dict[str, pd.DataFrame], output_path: str) -> None:
    """Write multiple DataFrames to a formatted .xlsx file."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default empty sheet

    header_font = Font(bold=True, color="FFFFFF", size=10)
    header_fill = PatternFill(fill_type="solid", fgColor="1F4E79")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_side = Side(style="thin", color="D9D9D9")
    cell_border = Border(left=thin_side, right=thin_side, bottom=thin_side)

    alt_fill = PatternFill(fill_type="solid", fgColor="EBF3FB")

    for sheet_name, df in sheets.items():
        ws = wb.create_sheet(title=sheet_name[:31])  # Excel 31-char limit
        if df.empty:
            ws.append(["Sin datos"])
            continue

        # Header row
        for col_idx, col_name in enumerate(df.columns, start=1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = cell_border

        # Data rows
        for row_idx, row in enumerate(df.itertuples(index=False), start=2):
            fill = alt_fill if row_idx % 2 == 0 else None
            for col_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.border = cell_border
                cell.alignment = Alignment(horizontal="left", vertical="center")
                if fill:
                    cell.fill = fill

        # Auto-fit columns (approximate)
        for col_idx, col_name in enumerate(df.columns, start=1):
            max_len = max(
                len(str(col_name)),
                df.iloc[:, col_idx - 1].astype(str).str.len().max() if not df.empty else 0,
            )
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 3, 50)

        # Freeze header row
        ws.freeze_panes = "A2"

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    wb.save(output_path)


# ─── LLM-based fallback for custom transformations on uploaded files ──────────

SYSTEM_PROMPT = """Eres un experto en Pandas y automatización de datos.
Tu tarea es escribir un bloque de código Python que procese archivos Excel/CSV y genere un nuevo archivo de resultado.
Solo puedes usar la librería `pandas` y la librería estándar de Python.
Dispones de las siguientes variables globales en tu entorno de ejecución:
- `INPUT_FILES`: diccionario {nombre_archivo: ruta_absoluta}
- `OUTPUT_PATH`: ruta absoluta donde guardar el resultado con `df.to_excel(OUTPUT_PATH, index=False)`.

INSTRUCCIONES CRÍTICAS:
1. Devuelve ÚNICAMENTE código Python, sin bloques markdown.
2. No uses print(). Guarda el resultado en OUTPUT_PATH.
3. No importes librerías ajenas a `pandas`.
4. El código debe ser tolerante a errores y directo a la solución.
"""


async def _run_llm_transform(
    user_intent: str, input_files: dict[str, str], output_path: str
) -> ExcelAgentResult:
    llm = _get_llm()
    prompt = (
        f"Archivos disponibles en INPUT_FILES: {list(input_files.keys())}\n"
        f"OUTPUT_PATH: {output_path}\n\n"
        f"Petición: {user_intent}\n\n"
        "Genera el código Python (solo texto plano, sin markdown):"
    )
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=prompt)]
    response = await llm.ainvoke(messages)
    code = response.content.strip()
    if code.startswith("```"):
        code = re.sub(r"^```(?:python)?\n?", "", code)
        code = re.sub(r"\n?```$", "", code)
    logger.info("[EXCEL_AGENT] Código LLM:\n%s", code)
    exec_globals = {"INPUT_FILES": input_files, "OUTPUT_PATH": output_path, "pd": pd}
    exec(code, exec_globals)  # noqa: S102 — prototype sandbox
    if not os.path.exists(output_path):
        return ExcelAgentResult(
            success=False,
            action="failed",
            output_message="El código se ejecutó pero no generó ningún archivo.",
            error="Archivo no generado",
        )
    return ExcelAgentResult(
        success=True,
        action="excel_generated",
        output_message=f"Archivo generado con transformación personalizada: {os.path.basename(output_path)}",
    )


# ─── Main entry point ────────────────────────────────────────────────────────

async def run_excel_agent(
    user_intent: str, tenant_id: str, task_id: str
) -> ExcelAgentResult:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_filename = f"informe_{ts}_{task_id[:8]}.xlsx"
    output_path = os.path.join(UPLOADS_DIR, output_filename)

    try:
        # ── Check for uploaded Excel/CSV files ──────────────────────────────
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TenantDocument).where(TenantDocument.tenant_id == uuid.UUID(tenant_id))
            )
            docs = result.scalars().all()

        input_files = {
            doc.file_name.lower(): doc.file_path
            for doc in docs
            if doc.file_path
            and os.path.exists(doc.file_path)
            and doc.file_name.lower().endswith((".xlsx", ".csv", ".xls"))
        }

        # ── Strategy A: uploaded files → LLM transform ──────────────────────
        if input_files:
            try:
                res = await _run_llm_transform(user_intent, input_files, output_path)
                if res.success:
                    await _register_document(tenant_id, task_id, output_filename, output_path, user_intent)
                    return res
                # LLM failed → fall through to DB strategy
                logger.warning("[EXCEL_AGENT] LLM transform failed, falling back to DB export")
            except Exception as llm_err:
                logger.warning("[EXCEL_AGENT] LLM error: %s — falling back to DB export", llm_err)

        # ── Strategy B: query DB directly based on intent ───────────────────
        datasets = _detect_datasets(user_intent)
        logger.info("[EXCEL_AGENT] Datasets detectados: %s", datasets)

        sheets: dict[str, pd.DataFrame] = {}
        for key in datasets:
            fetcher = _FETCHER_MAP.get(key)
            if fetcher:
                df = await fetcher(tenant_id)
                sheets[_SHEET_NAMES[key]] = df

        if not sheets:
            return ExcelAgentResult(
                success=False,
                action="failed",
                output_message="No se pudieron identificar datos relevantes para la petición.",
                error="Sin datos",
            )

        _write_excel(sheets, output_path)

        total_rows = sum(len(df) for df in sheets.values())
        sheet_summary = ", ".join(
            f"{name} ({len(df)} registros)" for name, df in sheets.items()
        )
        await _register_document(tenant_id, task_id, output_filename, output_path, user_intent)

        return ExcelAgentResult(
            success=True,
            action="excel_generated",
            output_message=(
                f"Excel generado con {total_rows} registros en {len(sheets)} hoja(s): "
                f"{sheet_summary}. Archivo: {output_filename}"
            ),
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return ExcelAgentResult(
            success=False,
            action="failed",
            output_message=f"Error generando Excel: {e}",
            error=str(e),
        )


async def _register_document(
    tenant_id: str, task_id: str, filename: str, file_path: str, intent: str
) -> None:
    async with AsyncSessionLocal() as db:
        doc = TenantDocument(
            tenant_id=uuid.UUID(tenant_id),
            task_id=uuid.UUID(task_id),
            file_name=filename,
            file_path=file_path,
            file_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size=os.path.getsize(file_path),
            category="informes",
            status="completed",
            parsed_content=f"Generado por IA: {intent}",
        )
        db.add(doc)
        await db.commit()
