"""Endpoints de licencia: estado y activación."""

from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel

from app.core.license import activate_license, get_stored_key, warm_up_server

router = APIRouter(prefix="/license", tags=["license"])


class ActivateRequest(BaseModel):
    key: str


def _mask_key(key: str | None) -> str | None:
    """Enmascara la clave de licencia dejando solo los últimos 4 caracteres.

    Este endpoint es público (allowlist del middleware de licencia), así que no
    debe exponer la clave completa a un visitante anónimo. Devolvemos el campo
    como string enmascarado para no romper a quien lea `key` del status.
    """
    if not key:
        return key
    if len(key) <= 4:
        return "…" + key
    return "…" + key[-4:]


@router.get("/status")
async def license_status(request: Request):
    """Estado actual de la licencia."""
    valid = getattr(request.app.state, "license_valid", False)
    plan = getattr(request.app.state, "license_plan", "")
    return {
        "valid": valid,
        "plan": plan,
        "key": _mask_key(get_stored_key()),
    }


@router.post("/activate")
async def license_activate(body: ActivateRequest, request: Request):
    """Activa una clave de licencia en esta máquina."""
    result = await activate_license(body.key)
    if result.valid:
        request.app.state.license_valid = True
        request.app.state.license_plan = result.plan
        return {"ok": True, "plan": result.plan}
    return {"ok": False, "reason": result.reason, "retriable": result.retriable}


@router.post("/warmup")
async def license_warmup(background: BackgroundTasks):
    """Despierta el servidor de licencias en background (mitiga el cold start de Render).

    Se llama al abrir el modal de activación para que un usuario nuevo no tope con
    una espera larga al pulsar Activar.
    """
    background.add_task(warm_up_server)
    return {"warming": True}
