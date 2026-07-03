"""Gate de plan (solo < pro < gestoría) — candado AUTORITATIVO de tiers.

El plan viene del grant firmado por el servidor de licencias (`app.state.
license_plan`), infalsificable. Sin este gate, el candado del frontend era
cosmético: un cliente 'solo' podía usar features 'pro' tecleando la URL o
llamando a la API directamente.

Uso (a nivel de router, en api/v1/router.py):
    api_router.include_router(crm.router, dependencies=[Depends(require_plan("pro"))])
"""

from fastapi import HTTPException, Request

# Jerarquía de planes. Un plan cubre todos los de rango inferior o igual.
_PLAN_RANK = {"solo": 0, "pro": 1, "gestoria": 2}


def _rank(plan: str) -> int:
    # Desconocido/vacío → rango 0 (solo). El grant solo emite solo/pro/gestoría,
    # así que esto solo afecta a etiquetas inesperadas, que se tratan como el
    # mínimo (nunca conceden acceso pro/gestoría por error).
    return _PLAN_RANK.get((plan or "").strip().lower(), 0)


def require_plan(minimum: str):
    """Dependencia FastAPI que exige un plan mínimo. 402 si no llega.

    Se apoya en que LicenseCheckMiddleware ya garantizó licencia válida para las
    rutas gateadas; aquí solo se compara el tier.
    """
    needed = _PLAN_RANK[minimum]

    async def _dep(request: Request) -> None:
        plan = getattr(request.app.state, "license_plan", "")
        if _rank(plan) < needed:
            raise HTTPException(
                status_code=402,
                detail={
                    "detail": f"Esta función requiere el plan {minimum.capitalize()}. "
                    "Mejora tu plan en Configuración → Licencia.",
                    "type": "plan_upgrade_required",
                    "required_plan": minimum,
                    "current_plan": (plan or "").strip().lower() or "solo",
                },
            )

    return _dep
