"""Tests del hardening de tool_session() (RLS — defensa en profundidad).

`tool_session()` ahora EXIGE un tenant_id explícito: el fallback silencioso a
None (que heredaba el ContextVar ambiente y podía dejar una sesión sin tenant)
se eliminó para que un olvido de contexto falle RUIDOSAMENTE.
"""

from uuid import uuid4

import pytest

from app.agents.shared.db import tool_session


async def test_tool_session_rejects_none():
    """tenant_id=None debe levantar ValueError, no abrir una sesión sin tenant."""
    with pytest.raises(ValueError):
        async with tool_session(None):  # type: ignore[arg-type]
            pass


async def test_tool_session_yields_session_with_tenant():
    """Con un tenant_id válido, cede una AsyncSession utilizable."""
    async with tool_session(uuid4()) as db:
        assert db is not None
