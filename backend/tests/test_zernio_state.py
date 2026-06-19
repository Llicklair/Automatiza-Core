"""Test del state cifrado URL-safe del flujo de conexión vía Zernio.

El state viaja en el PATH del redirect y lleva (tenant, cuenta de Zernio). Debe ser
tamper-proof y sin caracteres conflictivos ('/', '=', '+'). Round-trip + rechazo
de un state manipulado.
"""
from uuid import uuid4

import pytest

from app.api.v1.routes.marketing import _zernio_state, _zernio_unstate


def test_state_roundtrip_y_url_safe():
    tenant_id, config_id = uuid4(), uuid4()
    s = _zernio_state(tenant_id, config_id)
    assert "/" not in s and "=" not in s and "+" not in s  # apto para path
    assert _zernio_unstate(s) == (tenant_id, config_id)


def test_state_manipulado_falla():
    with pytest.raises(Exception):
        _zernio_unstate("esto-no-es-un-state-valido!!")
