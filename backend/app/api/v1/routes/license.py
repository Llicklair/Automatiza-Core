"""Endpoints de licencia: estado y activación."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.license import activate_license, get_stored_key

router = APIRouter(prefix="/license", tags=["license"])


class ActivateRequest(BaseModel):
    key: str


@router.get("/status")
async def license_status(request: Request):
    """Estado actual de la licencia."""
    valid = getattr(request.app.state, "license_valid", False)
    plan = getattr(request.app.state, "license_plan", "")
    return {
        "valid": valid,
        "plan": plan,
        "key": get_stored_key(),
    }


@router.post("/activate")
async def license_activate(body: ActivateRequest, request: Request):
    """Activa una clave de licencia en esta máquina."""
    result = await activate_license(body.key)
    if result.valid:
        request.app.state.license_valid = True
        request.app.state.license_plan = result.plan
        return {"ok": True, "plan": result.plan}
    return {"ok": False, "reason": result.reason}
