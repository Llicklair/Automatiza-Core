"""
Endpoint para consultar el uso de LLM por tenant (llamadas, tokens, coste estimado).
"""

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.services import llm_usage_tracker

router = APIRouter(prefix="/llm-usage", tags=["llm-usage"])


@router.get("/stats")
async def get_llm_usage_stats(
    months: int = Query(default=3, ge=1, le=12),
    current_user=Depends(get_current_user),
):
    """
    Devuelve estadísticas de uso LLM del tenant para los últimos N meses.

    Incluye: total de llamadas, tokens de entrada/salida y coste estimado en USD,
    desglosado por agente y proveedor.
    """
    tenant_id = str(current_user.tenant_id)
    stats = llm_usage_tracker.get_monthly_stats(tenant_id, months=months)
    return {"months": stats}
