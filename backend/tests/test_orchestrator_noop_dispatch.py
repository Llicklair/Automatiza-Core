"""Un agente sin dispatcher NO debe reportarse como éxito.

Antes, si el plan/blueprint nombraba un agente inexistente, el dispatcher
devolvía success=True con "[PENDIENTE] no implementado" y la tarea (programada o
no) se marcaba COMPLETADA sin ejecutar nada. Éxito falso clase Switch Pro en el
motor que ejecuta todos los workflows.
"""

import pytest

from app.agents.orchestrator._dispatch_handlers import _invoke_dispatcher_impl

pytestmark = pytest.mark.asyncio


async def test_agente_inexistente_es_fallo_no_exito():
    # Sin tenant_id no se intenta el empleado dinámico → cae directo al fallback.
    res = await _invoke_dispatcher_impl({}, {"id": "s1"}, "agente_que_no_existe")

    assert res["success"] is False, "un agente sin dispatcher no debe contar como éxito"
    assert res["error"], "debe explicar que el paso no se ejecutó"
    assert res["output"].get("action") == "failed"
