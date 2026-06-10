"""_next_due_run: catch-up de ticks retrasados sin doble disparo."""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.workers.tasks_scheduler import _GRACE_MINUTES, _next_due_run

TZ = ZoneInfo("Europe/Madrid")


def _at(h, m, s=0):
    return datetime(2026, 6, 10, h, m, s, tzinfo=TZ)


def test_minuto_exacto_dispara():
    due = _next_due_run({"cron": "0 9 * * *"}, _at(9, 0, 30))
    assert due == _at(9, 0)


def test_tick_retrasado_dentro_de_gracia_recupera():
    # Portátil suspendido a las 8:59, despierta 9:03 → recupera la de 9:00.
    due = _next_due_run({"cron": "0 9 * * *"}, _at(9, 3))
    assert due == _at(9, 0)


def test_fuera_de_ventana_no_dispara():
    due = _next_due_run({"cron": "0 9 * * *"}, _at(9, _GRACE_MINUTES + 1))
    assert due is None


def test_cron_cada_minuto_devuelve_el_ultimo_vencido():
    # No ráfaga: aunque haya 10 vencidos en la ventana, devuelve solo el último.
    due = _next_due_run({"cron": "* * * * *"}, _at(9, 5, 30))
    assert due == _at(9, 5)


def test_sin_cron_o_invalido():
    assert _next_due_run({}, _at(9, 0)) is None
    assert _next_due_run({"cron": "no es un cron"}, _at(9, 0)) is None


# ── _infer_domain_from_text: default ──────────────────────────────────────────


def test_infer_domain_sin_keywords_va_al_coordinador():
    """Texto sin keywords → "chat" (el coordinador clasifica con LLM).
    Antes el default era "billing" y un workflow genérico acababa en facturación."""
    from app.workers.tasks_scheduler import _infer_domain_from_text

    assert _infer_domain_from_text("enviar resumen semanal del negocio") == "chat"
    assert _infer_domain_from_text("factura vencida del cliente") == "billing"
