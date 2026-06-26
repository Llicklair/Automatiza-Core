"""
Regresión: la búsqueda global (GET /api/v1/search) debe escapar los
metacaracteres LIKE (%, _, \\) para que el input del usuario se trate como
LITERAL y no como comodín. Antes del fix, q="%%" devolvía TODAS las filas.

Mismo patrón ya corregido en services/sales/queries.py (productos).
"""
import pytest

from app.db.models.crm import Client


@pytest.mark.asyncio
async def test_global_search_escapes_like_wildcard(auth_client, seed_tenant_and_user, db):
    """q de solo comodines NO debe devolver clientes (se trata como literal)."""
    tenant, _, _ = seed_tenant_and_user

    # Cliente con nombre literal SIN metacaracteres LIKE.
    db.add(Client(tenant_id=tenant.id, name="Acme", nif="B12345678"))
    await db.commit()

    # q="%%" (len 2, pasa min_length). Pre-fix se interpretaría como comodín y
    # devolvería "Acme"; con el escape NO hay ningún '%%' literal en "Acme".
    resp = await auth_client.get("/api/v1/search", params={"q": "%%"})
    assert resp.status_code == 200
    clients = [r for r in resp.json() if r["type"] == "client"]
    assert clients == [], f"esperaba 0 clientes, comodín no escapado: {clients}"


@pytest.mark.asyncio
async def test_global_search_still_matches_literal(auth_client, seed_tenant_and_user, db):
    """Control no-tautológico: una subcadena real SÍ encuentra el cliente."""
    tenant, _, _ = seed_tenant_and_user

    db.add(Client(tenant_id=tenant.id, name="Acme", nif="B12345678"))
    await db.commit()

    resp = await auth_client.get("/api/v1/search", params={"q": "Acm"})
    assert resp.status_code == 200
    labels = [r["label"] for r in resp.json() if r["type"] == "client"]
    assert "Acme" in labels, f"la búsqueda literal dejó de funcionar: {labels}"
