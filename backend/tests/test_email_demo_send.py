"""El envío de email en modo DEMO (sin credenciales) NO debe afirmar 'enviado'.

Antes devolvía "[DEMO] Correo 'X' enviado a Y", que el usuario y el LLM daban
por enviado aunque no salía nada (éxito silencioso falso).
"""

from app.agents.email.tools import send_email


def test_demo_send_no_afirma_enviado():
    res = send_email.invoke({
        "tenant_id": "t",
        "to": "cliente@acme.com",
        "subject": "Presupuesto",
        "body": "Adjunto el presupuesto.",
        "confirm": True,
    })
    low = res.lower()
    assert "no se envió" in low or "no se envio" in low, res
    assert "credenciales" in low, res
    # No debe leerse como un envío exitoso.
    assert "enviado a" not in low, res
