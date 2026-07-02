import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.dependencies import get_current_user
from app.integrations.advisory_guides import get_guides
from app.integrations.boe_scraper import BOEScraper, get_proximos_vencimientos
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advisory", tags=["advisory"])


@router.get("/boe", response_model=list[dict])
@limiter.limit("30/minute")
async def get_boe_news(
    request: Request,
    section: Literal["fiscal", "laboral", "mercantil"] = Query(
        "fiscal", description="Sección del BOE a scrapear (fiscal, laboral, mercantil)"
    ),
    limit: int = Query(10, description="Número máximo de noticias a obtener"),
    current_user=Depends(get_current_user),
):
    """
    Obtiene las últimas novedades publicadas en el RSS del BOE, filtrando
    por palabras clave relevantes para PYMEs y autónomos.
    """
    scraper = BOEScraper()
    try:
        news = await scraper.get_novedades(seccion=section, max_items=limit)
        return news
    except Exception as exc:
        logger.exception("Error obteniendo BOE")
        raise HTTPException(status_code=500, detail="Error interno obteniendo el BOE") from exc
    finally:
        await scraper.close()


@router.get("/calendar", response_model=list[dict])
@limiter.limit("30/minute")
async def get_fiscal_calendar(
    request: Request,
    days_ahead: int = Query(90, ge=1, le=365, description="Días hacia adelante a buscar vencimientos"),
    current_user=Depends(get_current_user),
):
    """
    Devuelve los próximos vencimientos de impuestos basados en
    el calendario fiscal de la AEAT para autónomos y pymes.
    """
    try:
        events = get_proximos_vencimientos(days_ahead=days_ahead)
        return events
    except Exception as exc:
        logger.exception("Error obteniendo calendario fiscal")
        raise HTTPException(status_code=500, detail="Error interno obteniendo el calendario fiscal") from exc


@router.get("/guides", response_model=list[dict])
@limiter.limit("30/minute")
async def get_advisory_guides(
    request: Request,
    section: Literal["fiscal", "laboral", "mercantil"] = Query(
        "fiscal", description="Sección normativa (fiscal, laboral, mercantil)"
    ),
    current_user=Depends(get_current_user),
):
    """
    Devuelve guías normativas estáticas con referencias legales y
    consejos prácticos para PYMEs, organizadas por sección.
    """
    return get_guides(section=section)
