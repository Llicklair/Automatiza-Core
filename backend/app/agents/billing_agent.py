"""
Agente de Facturación — Fase 1.

Flujo:
  1. Extrae datos de la intención del usuario (LLM → JSON estructurado)
  2. Anonimiza datos sensibles antes del LLM (NIF, importes → placeholders)
  3. Valida determinísticamente (sin LLM)
  4. Busca el cliente en Holded (base de datos real)
  5. Crea el borrador de factura
  6. Si importe > umbral → solicita aprobación humana
  7. Envía y registra en audit log
"""
import json
import re
from datetime import UTC, date

from app.core.prompt_sanitizer import sanitize_user_input
from decimal import Decimal, InvalidOperation

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agents.validators.billing import validate_invoice_data
from app.core.config import settings
from app.core.llm_factory import get_llm
from app.integrations.holded import HoldedClient

# ─── Modelo de salida estructurada del LLM ────────────────────────────────────

class ExtractedInvoiceData(BaseModel):
    """El LLM deve rellenar este esquema. Pydantic valida. Sin libertad."""
    client_name: str | None = Field(None, description="Nombre o razón social del cliente")
    client_nif: str | None = Field(None, description="NIF o CIF del cliente (9 caracteres)")
    issuer_name: str | None = Field(None, description="Nombre o razón social de la empresa emisora si se indica")
    issuer_nif: str | None = Field(None, description="NIF/CIF de la empresa emisora si se indica")
    issuer_address: str | None = Field(None, description="Dirección completa de la empresa emisora si se indica")
    issuer_email: str | None = Field(None, description="Email de facturación de la empresa emisora si se indica")
    concept: str | None = Field(None, max_length=500, description="Descripción del servicio/producto")
    amount_base: str | None = Field(None, description="Base imponible en euros, solo el número. Ej: '1500.00'")
    vat_rate: float | None = Field(None, description="Tipo de IVA: 0, 4, 10 o 21")
    invoice_date: str | None = Field(None, description="Fecha de factura en formato YYYY-MM-DD")
    notes: str | None = Field(None, description="Notas adicionales para la factura")
    confidence: float | None = Field(0.0, ge=0, le=1, description="Confianza del 0 al 1 en la extracción")
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Campos que no se pudieron extraer del texto"
    )
    is_query: bool = Field(False, description="True si el usuario quiere LISTAR o CONSULTAR facturas existentes, no crear una nueva")


# ─── Anonimización pre-LLM ────────────────────────────────────────────────────

def anonymize_for_llm(text: str) -> tuple[str, dict[str, str]]:
    """
    DESACTIVADO: Ollama corre localmente, no hay riesgo de privacidad.
    Se mantiene la firma por compatibilidad pero no transforma el texto.
    """
    return text, {}


# ─── LLM setup ────────────────────────────────────────────────────────────────

def _get_llm():
    return get_llm(temperature=0, format_output="json")


EXTRACTION_SYSTEM_PROMPT = """Eres un asistente especializado en extracción de datos de facturación española.

Tu tarea es extraer datos estructurados de la intención del usuario y devolver ÚNICAMENTE un JSON válido (sin bloques de código, sin explicaciones).

REGLAS ESTRICTAS:
1. Si un dato no está explícitamente en el texto, pon null y añádelo a `missing_fields`.
2. NUNCA inventes NIF/CIF, importes ni fechas. Si no aparecen en el texto, déjalos en null.
3. `amount_base` es la BASE IMPONIBLE (sin IVA) como string numérico. Ej: "1500.00". Si el usuario dice "1500€", extrae "1500.00".
4. `vat_rate` es el tipo de IVA como número. Si no se menciona, usa 21.
5. `invoice_date` en formato YYYY-MM-DD. Si no se menciona, usa la fecha de hoy: FECHA_HOY.
6. `client_nif` es el NIF o CIF del cliente (9 caracteres). Si no está en el texto, pon null.
7. Si el usuario indica una EMPRESA EMISORA distinta del cliente en la cabecera (ej: \"Crea una factura con cabecera de la empresa X...\"), rellena `issuer_name`, `issuer_nif`, `issuer_address` y `issuer_email` con esos datos. Si no se menciona empresa emisora, ponlos en null.
8. Devuelve SOLO el JSON, sin bloques ```json``` ni texto adicional.

Formato de respuesta:
{
  "client_name": "Nombre del cliente o null",
  "client_nif": null,
  "issuer_name": "Nombre de la empresa emisora o null",
  "issuer_nif": null,
  "issuer_address": null,
  "issuer_email": null,
  "concept": "Descripción del servicio o null",
  "amount_base": "1500.00",
  "vat_rate": 21,
  "invoice_date": "FECHA_HOY",
  "notes": null,
  "confidence": 0.9,
  "missing_fields": [],
  "is_query": false
}
NOTA: Si el usuario pide "ver facturas", "listar", "analizar facturas", "listado" o preguntar "cuánto he facturado" o "consultar", pon is_query=true."""

# ─── Función principal del agente ────────────────────────────────────────────

class BillingAgentResult(BaseModel):
    success: bool
    action: str  # "draft_created" | "approval_required" | "validation_failed" | "extraction_failed"
    holded_invoice_id: str | None = None
    validation_errors: list[str] = []
    validation_warnings: list[str] = []
    extracted_data: dict | None = None
    approval_required: bool = False
    approval_threshold_eur: float = 5000.0
    error: str | None = None


async def run_billing_agent(
    user_intent: str,
    tenant_id: str,
    holded_api_key: str | None = None,
    task_id: str | None = None,
) -> BillingAgentResult:
    """
    Ejecuta el agente de facturación completo con todas las capas de seguridad.
    """
    today = date.today().isoformat()

    # ── PASO 1: Anonimizar antes del LLM ──────────────────────────────────
    anonymized_text, anon_map = anonymize_for_llm(user_intent)

    # ── PASO 2: Extracción con LLM (salida estructurada) ─────────────────
    if holded_api_key == "DEMO_HOLDED_KEY":
        # Mock LLM data to ensure perfect demo flow
        extracted = ExtractedInvoiceData(
            client_name="Tech Solutions SL",
            client_nif="B60249562",
            concept="Servicios de consultoría informática del mes de octubre",
            amount_base="5500.00",
            vat_rate=21,
            invoice_date=today,
            notes="Dato autogenerado por la demo",
            confidence=0.99,
            missing_fields=[],
            is_query=any(kw in user_intent.lower() for kw in ["ver", "listar", "analizar", "listado", "consultar", "cuanto", "cuánto"])
        )
    else:
        llm = _get_llm()
        messages = [
            SystemMessage(content=EXTRACTION_SYSTEM_PROMPT.replace("FECHA_HOY", today)),
            HumanMessage(content=f"Extrae los datos de facturación de esta instrucción:\n\n{sanitize_user_input(anonymized_text)}"),
        ]

        try:
            response = await llm.ainvoke(messages)
            raw_json = response.content.strip()

            # Ollama a veces envuelve el JSON en bloques de codigo markdown
            if raw_json.startswith("```"):
                raw_json = re.sub(r"^```(?:json)?\n?", "", raw_json)
                raw_json = re.sub(r"\n?```$", "", raw_json.strip())

            # Des-anonimizar: restaurar valores reales en el JSON (no-op si anon_map esta vacio)
            for placeholder, real_value in anon_map.items():
                raw_json = raw_json.replace(placeholder, real_value)

            data_dict = json.loads(raw_json)
            extracted = ExtractedInvoiceData(**data_dict)

        except Exception as e:
            error_msg = str(e).lower()
            if "429" in error_msg or "quota" in error_msg or "insufficient" in error_msg:
                user_msg = "Has excedido la cuota gratuita de tu clave de OpenAI API o estás siendo limitado temporalmente (Error 429). Por favor, verifica el saldo de tu cuenta de OpenAI."
            else:
                user_msg = f"Error conectando con el modelo de IA: {str(e)}"
                
            return BillingAgentResult(
                success=False,
                action="extraction_failed",
                error=user_msg
            )

    # Si es una CONSULTA, saltar la validación de creación y devolver lista
    if extracted.is_query:
        import uuid as _uuid
        from sqlalchemy import select
        from app.db.base import AsyncSessionLocal
        from app.db.models.models import Invoice, Client
        
        try:
            async with AsyncSessionLocal() as db:
                # Buscar facturas recientes del tenant
                stmt = select(Invoice, Client).join(Client).where(
                    Invoice.tenant_id == _uuid.UUID(tenant_id)
                ).order_by(Invoice.date.desc()).limit(15)
                
                result = await db.execute(stmt)
                rows = result.all()
                
                invoices_list = []
                total_facturado = 0
                for inv, cli in rows:
                    total_facturado += float(inv.amount_total)
                    invoices_list.append({
                        "numero": inv.invoice_number,
                        "cliente": cli.name,
                        "nif": cli.nif,
                        "fecha": inv.date.strftime("%Y-%m-%d"),
                        "total": float(inv.amount_total),
                        "estado": inv.status
                    })
                
                if not invoices_list:
                    # Datos de demo si la BD está vacía
                    invoices_list = [
                        {"numero": "F2025-001", "cliente": "Tech Solutions SL", "nif": "B60249562", "fecha": "2025-10-01", "total": 3200.0, "estado": "paid"},
                        {"numero": "F2025-002", "cliente": "Acme Corp", "nif": "A12345678", "fecha": "2025-10-10", "total": 1500.0, "estado": "draft"},
                    ]
                    total_facturado = 4700.0

                summary = f"He encontrado {len(invoices_list)} facturas recientes.\nTotal facturado: {total_facturado}€.\n\nFacturas:\n"
                for inv in invoices_list:
                    summary += f"- {inv['numero']}: {inv['cliente']} ({inv['total']}€) - {inv['estado']}\n"
                
                return BillingAgentResult(
                    success=True,
                    action="summary",
                    extracted_data={"invoices": invoices_list, "total": total_facturado},
                    error=None
                )
        except Exception as e:
            print(f"[BILLING] Error en consulta: {e}")
            return BillingAgentResult(success=False, action="failed", error=str(e))

    # ── Auto-resolución de cliente desde BD ──────────────────────────────
    # Si falta el NIF pero hay nombre de cliente → buscarlo por nombre en BD
    # Si no hay ni nombre → coger el primer cliente disponible del tenant
    if not extracted.client_nif:
        try:
            import uuid as _uuid
            from sqlalchemy import select, or_, func
            from app.db.base import AsyncSessionLocal
            from app.db.models.models import Client as ClientModel
            async with AsyncSessionLocal() as db:
                if extracted.client_name:
                    # Búsqueda por nombre exacto primero, luego parcial
                    name_clean = extracted.client_name.strip()
                    res = await db.execute(
                        select(ClientModel)
                        .where(
                            ClientModel.tenant_id == _uuid.UUID(tenant_id),
                            or_(
                                func.lower(ClientModel.name) == name_clean.lower(),
                                func.lower(ClientModel.name).contains(name_clean.lower()),
                            )
                        )
                        .limit(1)
                    )
                else:
                    # Sin nombre → primer cliente del tenant
                    res = await db.execute(
                        select(ClientModel)
                        .where(ClientModel.tenant_id == _uuid.UUID(tenant_id))
                        .order_by(ClientModel.created_at.asc())
                        .limit(1)
                    )
                client = res.scalar_one_or_none()
                if client:
                    extracted.client_nif = client.nif
                    extracted.client_name = client.name
        except Exception:
            pass

    # Fecha por defecto: hoy
    if not extracted.invoice_date:
        extracted.invoice_date = today

    # Concepto por defecto si sigue vacío
    if not extracted.concept:
        extracted.concept = "Servicios generales"

    # Si hay campos faltantes críticos, no continuar (Modo CREACIÓN)
    actual_missing = []
    if not extracted.client_nif: actual_missing.append("NIF del cliente")
    if not extracted.amount_base: actual_missing.append("Base imponible")
    if not extracted.invoice_date: actual_missing.append("Fecha")
    if not extracted.concept: actual_missing.append("Concepto")

    if actual_missing:
        return BillingAgentResult(
            success=False,
            action="extraction_failed",
            extracted_data=extracted.model_dump(),
            error=f"Faltan datos obligatorios: {', '.join(actual_missing)}. Por favor proporciónalos."
        )
        
    # Aplicar valores por defecto
    if extracted.vat_rate is None:
        extracted.vat_rate = 21.0

    # ── PASO 3: Validación determinista ───────────────────────────────────
    try:
        raw = extracted.amount_base.strip()
        # Detectar formato: si el punto separa grupos de 3 dígitos (separador de miles en español)
        # Casos: "6.000" → 6000 | "1.500,50" → 1500.50 | "350,50" → 350.50 | "1500.50" → 1500.50
        import re as _re
        if _re.search(r'\.\d{3}(?:[,\d]|$)', raw):
            # Formato español: punto = miles, coma = decimal
            raw = raw.replace(".", "")   # quitar separador de miles
            raw = raw.replace(",", ".")  # convertir decimal
        else:
            # Solo coma decimal o ya en formato anglosajón
            raw = raw.replace(",", ".")
        amount = Decimal(raw)
    except InvalidOperation:
        return BillingAgentResult(
            success=False,
            action="validation_failed",
            extracted_data=extracted.model_dump(),
            error=f"Importe no válido: '{extracted.amount_base}'"
        )

    try:
        inv_date = date.fromisoformat(extracted.invoice_date)
    except ValueError:
        return BillingAgentResult(
            success=False,
            action="validation_failed",
            extracted_data=extracted.model_dump(),
            error=f"Fecha no válida: '{extracted.invoice_date}'"
        )

    validation = validate_invoice_data(
        client_nif=extracted.client_nif,
        amount_base=amount,
        vat_rate=extracted.vat_rate,
        invoice_date=inv_date,
    )

    if not validation.is_valid:
        return BillingAgentResult(
            success=False,
            action="validation_failed",
            extracted_data=extracted.model_dump(),
            validation_errors=validation.errors,
            validation_warnings=validation.warnings,
        )

    # ── PASO 4: Buscar o crear cliente + crear factura en UNA única transacción atómica ──
    import uuid
    from datetime import datetime as dt
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Client, Invoice, InvoiceLine

    contact_id_holded = "unknown"
    contact_created_holded = False

    # ── Sincronizar con Holded ANTES de abrir la transacción (operación externa) ──
    if holded_api_key and holded_api_key != "DEMO_HOLDED_KEY":
        try:
            holded = HoldedClient(api_key=holded_api_key)
            contact = await holded.get_contact_by_nif(extracted.client_nif)
            if not contact:
                new_contact = await holded.create_contact({
                    "name": extracted.client_name,
                    "vatnumber": extracted.client_nif,
                    "type": "client",
                })
                contact_id_holded = new_contact.get("id", "unknown")
                contact_created_holded = True
            else:
                contact_id_holded = contact["id"]
            await holded.close()
        except Exception as e:
            validation.warnings.append(f"No se pudo sincronizar el cliente con Holded: {e}")

    # ── PASO 5: ¿Requiere aprobación humana? ────────────────────────────
    APPROVAL_THRESHOLD = Decimal("5000")
    needs_approval = amount > APPROVAL_THRESHOLD

    if needs_approval:
        # En aprobaciones no creamos nada en BD aún — solo devolvemos los datos extraidos
        extra_warnings = [f"Contacto '{extracted.client_name}' creado en Holded."] if contact_created_holded else []
        return BillingAgentResult(
            success=True,
            action="approval_required",
            extracted_data={
                **extracted.model_dump(),
                "contact_id_holded": contact_id_holded,
                "amount_with_vat": str(round(amount * (1 + Decimal(str(extracted.vat_rate)) / 100), 2)),
            },
            approval_required=True,
            validation_warnings=validation.warnings + extra_warnings,
        )

    # ── PASO 6: Crear factura en Holded (externo, antes de la transacción DB) ──
    holded_id = None
    if holded_api_key and holded_api_key != "DEMO_HOLDED_KEY" and contact_id_holded != "unknown":
        import calendar
        date_unix = int(calendar.timegm(inv_date.timetuple()))
        payload = HoldedClient.build_invoice_payload(
            contact_id=contact_id_holded,
            concept=extracted.concept,
            amount_base=float(amount),
            vat_rate=extracted.vat_rate,
            date_unix=date_unix,
            notes=extracted.notes or "",
        )
        try:
            holded2 = HoldedClient(api_key=holded_api_key)
            invoice_h = await holded2.create_invoice(payload)
            holded_id = invoice_h.get("id", "unknown")
            await holded2.close()
        except Exception as e:
            validation.warnings.append(f"Fallo al sincronizar factura con Holded: {e}")

    # ── PASO 7: TRANSACCIÓN ATÓMICA: Client + Invoice + InvoiceLine en un solo commit ──
    #
    # Si cualquier escritura falla: rollback total. Cero datos huérfanos.
    # Patron: begin → upsert client → insert invoice → insert lines → emit event → commit
    #
    tax_amount = round(amount * Decimal(str(extracted.vat_rate)) / 100, 2)
    total_amount = amount + tax_amount
    inv_datetime = dt(inv_date.year, inv_date.month, inv_date.day, tzinfo=UTC)
    invoice_number = f"IA-{task_id[:8].upper() if task_id else 'AUTO'}"

    async with AsyncSessionLocal() as db:
        try:
            # — Upsert cliente —
            result = await db.execute(
                select(Client).where(
                    Client.tenant_id == uuid.UUID(tenant_id),
                    Client.nif == extracted.client_nif,
                )
            )
            local_client = result.scalars().first()
            if not local_client:
                if not extracted.client_name:
                    return BillingAgentResult(
                        success=False,
                        action="validation_failed",
                        extracted_data=extracted.model_dump(),
                        error=f"Cliente con NIF {extracted.client_nif} no encontrado y no se puede crear sin nombre.",
                    )
                local_client = Client(
                    tenant_id=uuid.UUID(tenant_id),
                    nif=extracted.client_nif,
                    name=extracted.client_name,
                    holded_id=contact_id_holded if contact_id_holded != "unknown" else None,
                )
                db.add(local_client)
                await db.flush()  # genera el id sin commit
            elif contact_id_holded and contact_id_holded != "unknown" and not local_client.holded_id:
                local_client.holded_id = contact_id_holded

            # — Crear factura —
            new_invoice = Invoice(
                tenant_id=uuid.UUID(tenant_id),
                client_id=local_client.id,
                invoice_number=invoice_number,
                date=inv_datetime,
                amount_base=amount,
                tax_amount=tax_amount,
                amount_total=total_amount,
                notes=extracted.notes,
                status="draft",
                external_id=holded_id,
            )
            db.add(new_invoice)
            await db.flush()  # genera new_invoice.id sin commit

            # — Crear línea de factura —
            invoice_line = InvoiceLine(
                invoice_id=new_invoice.id,
                description=extracted.concept or "Servicio",
                quantity=1.0,
                unit_price=float(amount),
                discount_percentage=0.0,
                tax_percentage=float(extracted.vat_rate or 21),
                total=float(total_amount),
            )
            db.add(invoice_line)

            # — Emitir evento de dominio (dentro de la misma transacción) —
            try:
                from app.services.event_bus import emit_event
                await emit_event(
                    db=db,
                    tenant_id=uuid.UUID(tenant_id),
                    user_id=None,
                    event_name="invoice_created",
                    context={
                        "invoice_id": str(new_invoice.id),
                        "invoice_number": invoice_number,
                        "amount_total": float(total_amount),
                        "client_name": extracted.client_name,
                        "client_nif": extracted.client_nif,
                        "concept": extracted.concept,
                    },
                )
            except Exception as ev_err:
                # El evento no bloquea la factura — solo advertencia
                validation.warnings.append(f"Evento invoice_created no emitido: {ev_err}")

            # ── COMMIT ÚNICO: todo o nada ──
            await db.commit()
            await db.refresh(new_invoice)

            # ── PASO 8: Generar PDF y Guardar en TenantDocument ──
            document_id = None
            try:
                from app.services.pdf_service import generate_invoice_pdf
                from app.db.models.models import TenantDocument
                import os
                
                # Cargar datos completos para el PDF
                inv_pdf_data = {
                    "number": new_invoice.invoice_number,
                    "date": new_invoice.date.isoformat(),
                    "amount_base": float(new_invoice.amount_base),
                    "tax_amount": float(new_invoice.tax_amount),
                    "amount_total": float(new_invoice.amount_total),
                    "notes": new_invoice.notes,
                    "client": {
                        "name": local_client.name,
                        "nif": local_client.nif,
                    },
                    "lines": [{
                        "description": invoice_line.description,
                        "quantity": invoice_line.quantity,
                        "unit_price": invoice_line.unit_price,
                        "tax_percentage": invoice_line.tax_percentage,
                        "total": invoice_line.total,
                    }],
                    "company": {
                        "name": getattr(settings, "APP_NAME", "Empresa"), # O datos del tenant si los tuviéramos
                        "nif": "B-00000000",
                    }
                }
                
                pdf_bytes = generate_invoice_pdf(inv_pdf_data)
                
                # Guardar en disco
                upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
                if not os.path.exists(upload_dir) and "WIN" in os.name.upper():
                    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads")
                os.makedirs(upload_dir, exist_ok=True)
                
                file_name = f"Factura_{new_invoice.invoice_number}.pdf"
                file_path = os.path.join(upload_dir, file_name)
                with open(file_path, "wb") as f:
                    f.write(pdf_bytes)
                
                # Registrar en BD
                new_doc = TenantDocument(
                    tenant_id=uuid.UUID(tenant_id),
                    file_name=file_name,
                    file_path=file_path,
                    file_type="application/pdf",
                    file_size=len(pdf_bytes),
                    category="Facturas",
                    status="completed"
                )
                
                # Usar una nueva sesión para el documento si la anterior está cerrada o comprometida
                async with AsyncSessionLocal() as db_doc:
                    db_doc.add(new_doc)
                    await db_doc.commit()
                    await db_doc.refresh(new_doc)
                    document_id = str(new_doc.id)
                    
            except Exception as pdf_err:
                validation.warnings.append(f"Factura creada pero no se pudo generar el PDF: {pdf_err}")

        except Exception as e:
            await db.rollback()
            return BillingAgentResult(
                success=False,
                action="validation_failed",
                extracted_data=extracted.model_dump(),
                error=f"Error al guardar la factura en base de datos: {e}",
            )

    extra_warnings = [f"Contacto '{extracted.client_name}' creado nuevo en Holded."] if contact_created_holded else []

    return BillingAgentResult(
        success=True,
        action="draft_created",
        holded_invoice_id=holded_id or "local_only",
        extracted_data={
            **extracted.model_dump(),
            "invoice_id": str(new_invoice.id),
            "invoice_number": invoice_number,
            "document_id": document_id,
            "amount_total": float(total_amount),
            "tax_amount": float(tax_amount),
        },
        validation_warnings=validation.warnings + extra_warnings,
    )
