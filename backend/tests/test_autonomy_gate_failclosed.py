"""El gate de autonomía debe FALLAR CERRADO.

Si `gated_tool` no puede resolver el tenant_id, no puede consultar la política
de autonomía del tenant — así que NO debe ejecutar una tool con efecto
secundario. Antes fallaba ABIERTO (ejecutaba sin gate), un bypass del único
mecanismo de seguridad.
"""

import pytest

from app.services.autonomy_gate import gated_tool

pytestmark = pytest.mark.asyncio

_ran = {"v": False}


@gated_tool(domain="email")
async def _danger(tenant_id: str = "", x: int = 0) -> str:
    _ran["v"] = True
    return "EJECUTADO"


async def test_sin_tenant_no_ejecuta():
    _ran["v"] = False
    res = await _danger(tenant_id="", x=1)
    assert _ran["v"] is False, "no debe ejecutar la tool sin tenant resoluble"
    assert "EJECUTADO" not in res


async def test_tenant_no_uuid_no_ejecuta():
    _ran["v"] = False
    res = await _danger(tenant_id="no-soy-uuid", x=1)
    assert _ran["v"] is False, "no debe ejecutar la tool con tenant_id inválido"
    assert "EJECUTADO" not in res
