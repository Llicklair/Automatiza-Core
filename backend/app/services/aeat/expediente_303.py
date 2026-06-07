"""Expediente del Modelo 303 — bundle completo listo para presentar.

Genera, dado un trimestre/año del tenant:
  - casillas oficiales rellenadas
  - XML auxiliar con todas las casillas
  - checklist de pasos a seguir en la SEDE AEAT
  - referencia al PDF (que se descarga vía endpoint existente)

NO firma ni presenta. Ese paso lo hace el usuario en la SEDE con su
certificado digital o cl@ve. La Fase C implementará la presentación real.
"""

from __future__ import annotations

import base64
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.aeat.casillas_303 import build_casillas_303
from app.services.aeat.modelo_303_xml import build_modelo_303_xml

_log = logging.getLogger(__name__)


class ExpedienteError(RuntimeError):
    pass


def _checklist_for(quarter: int, year: int, resultado: float) -> list[dict]:
    """Genera el checklist personalizado de pasos para presentar el 303.

    El paso 4 cambia según el resultado:
      - Positivo → ingresar.
      - Negativo → solicitar compensación o devolución.
      - Cero → marcar 'sin actividad'.
    """
    a_ingresar = resultado > 0
    a_compensar = resultado < 0

    pasos = [
        {
            "n": 1,
            "titulo": "Descargar el PDF y revisar todas las casillas",
            "detalle": "Comprueba especialmente las casillas editables marcadas — pueden requerir ajuste por compensaciones de trimestres anteriores o bienes de inversión.",
            "completado": False,
        },
        {
            "n": 2,
            "titulo": "Acceder a la SEDE AEAT",
            "detalle": "https://sede.agenciatributaria.gob.es → Modelo 303 → Presentación.",
            "completado": False,
        },
        {
            "n": 3,
            "titulo": "Identificarse con certificado digital o Cl@ve",
            "detalle": "Si presentas en nombre de tu empresa, usa el certificado de representante. Si lo hace tu asesor por ti, debe estar dado de alta en el censo de colaboradores sociales.",
            "completado": False,
        },
        {
            "n": 4,
            "titulo": (
                f"Marcar 'a ingresar' por {resultado:.2f} € y aportar IBAN"
                if a_ingresar
                else f"Solicitar compensación por {abs(resultado):.2f} €"
                if a_compensar
                else "Marcar 'sin actividad' o resultado cero"
            ),
            "detalle": (
                "Cuenta bancaria de cargo. La AEAT realizará el cobro en la fecha indicada."
                if a_ingresar
                else "Se acumula al saldo a compensar del próximo trimestre. Solo se solicita devolución en el 4T."
                if a_compensar
                else "Sin importe a ingresar ni a compensar."
            ),
            "completado": False,
        },
        {
            "n": 5,
            "titulo": "Rellenar las casillas (puedes copiarlas del XML/PDF de este expediente)",
            "detalle": "La SEDE permite cargar un fichero o introducir manualmente. Usa este expediente como referencia.",
            "completado": False,
        },
        {
            "n": 6,
            "titulo": "Firmar y enviar",
            "detalle": "Guarda el CSV (Código Seguro de Verificación) que devuelve la SEDE — es el justificante oficial.",
            "completado": False,
        },
    ]
    return pasos


async def build_expediente_303(
    db: AsyncSession,
    tenant_id: UUID,
    quarter: int,
    year: int,
) -> dict:
    """Construye el expediente completo del 303.

    Devuelve un dict con:
      - tenant: {name, nif}
      - quarter, year, periodo (str "1T 2026")
      - casillas: list[{codigo, descripcion, valor, editable, nota}]
      - resumen: {total_devengado, total_deducible, resultado, signo}
      - xml: string con el XML auxiliar
      - xml_filename: sugerencia de nombre de archivo
      - pdf_url: endpoint del backend que devuelve el PDF
      - checklist: pasos para presentar en SEDE AEAT
    """
    # Reutilizamos el cálculo existente en reports/fiscal.py
    from app.services.reports.fiscal import build_modelo_303_data

    data = await build_modelo_303_data(db, tenant_id, quarter, year)

    casillas = build_casillas_303(data)
    cas_by_code = {c.codigo: c for c in casillas}

    total_devengado = float(cas_by_code["27"].valor) if "27" in cas_by_code else 0.0
    total_deducible = float(cas_by_code["45"].valor) if "45" in cas_by_code else 0.0
    resultado = float(cas_by_code["71"].valor) if "71" in cas_by_code else (total_devengado - total_deducible)

    if resultado > 0:
        signo = "ingresar"
    elif resultado < 0:
        signo = "compensar"
    else:
        signo = "cero"

    xml_str = build_modelo_303_xml(
        tenant_name=data["tenant"]["name"],
        tenant_nif=data["tenant"]["nif"],
        year=year,
        quarter=quarter,
        casillas=casillas,
    )

    pdf_url = f"/api/v1/reports/fiscal/modelo-303?quarter={quarter}&year={year}"

    return {
        "tenant": data["tenant"],
        "quarter": quarter,
        "year": year,
        "periodo": f"{quarter}T {year}",
        "casillas": [c.to_dict() for c in casillas],
        "resumen": {
            "total_devengado": round(total_devengado, 2),
            "total_deducible": round(total_deducible, 2),
            "resultado": round(resultado, 2),
            "signo": signo,
        },
        "xml": xml_str,
        "xml_filename": f"Modelo303_{quarter}T_{year}.xml",
        "xml_base64": base64.b64encode(xml_str.encode("utf-8")).decode("ascii"),
        "pdf_url": pdf_url,
        "checklist": _checklist_for(quarter, year, resultado),
    }
