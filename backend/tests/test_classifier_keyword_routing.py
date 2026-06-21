"""
Routing determinista por keywords (sin LLM).

El clasificador de producción resuelve la mayoría de intents con la capa de
keywords ANTES de llamar al LLM (cache → custom → keywords → LLM → chat). Esa
capa es determinista y DEBE testearse sin el LLM: vía `claude -p` es flaky —el
mismo input puede dar dominios distintos entre corridas, con "compliance" como
atractor erróneo frecuente—, así que `test_prompt_e2e.py` (prompt crudo) no es
una guardia fiable para el routing real.

Estos tests bloquean `_keyword_classify` para intents reales, incluidas dos
regresiones encontradas evaluando salidas el 2026-06-20:

  - Bug A: "da de alta … contrato indefinido" caía a `unknown` → LLM flaky →
    misrouteado a compliance. Los tipos de contrato son ahora señal HR fuerte.
  - Bug B (fiscal): "¿qué dice la AEAT sobre el modelo 303?" se ruteaba a `rag`
    porque el genérico "qué dice" ganaba al específico "modelo 303" con la regla
    first-match. Ahora gana el keyword más largo (maximal-munch).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.orchestrator.classifier import _keyword_classify  # noqa: E402

# (intent, dominio esperado). Solo intents que la capa keyword DEBE resolver de
# forma determinista. Los ambiguos legítimos caen a 'unknown' (→ LLM) y NO se
# fijan aquí a propósito.
CASES = [
    # — dominios base —
    ("crea una factura para garcía s.l. por 1500€ de consultoría", "billing"),
    ("¿cuánto hemos facturado este mes?", "billing"),
    ("cada lunes envíame un resumen de facturas pendientes", "workflow"),
    ("muéstrame el embudo de ventas", "crm"),
    ("sube este contrato pdf y extrae la fecha de vencimiento", "documents"),
    ("¿cuál es el saldo de la cuenta bancaria?", "banking"),
    ("haz la nómina de este mes", "hr"),
    # — Bug B (fiscal): el término específico vence al genérico —
    ("¿qué dice la aeat sobre el modelo 303?", "compliance"),
    # — Bug A: tipo de contrato como señal HR fuerte —
    ("da de alta a maría garcía, contrato indefinido, 2200€/mes", "hr"),
    # — guardas de desambiguación maximal-munch —
    ("según el documento de hacienda, ¿qué plazo hay?", "rag"),
    ("crea cliente nuevo y emítele una factura", "crm"),
    ("sube el contrato de maría en pdf", "documents"),
    # — workflow: stem "automatiza" cubre verbo/plural/acento (campaña 2026-06-21) —
    ("lista mis automatizaciones activas", "workflow"),
    ("automatiza que cada fin de mes se generen las nóminas", "workflow"),
    ("muéstrame mis automatizaciones", "workflow"),
    # guarda: consulta mensual NO es automatización
    ("¿cuánto facturamos cada mes?", "billing"),
]


@pytest.mark.parametrize("intent,expected", CASES)
def test_keyword_routing(intent, expected):
    got = _keyword_classify(intent.lower())
    assert got == expected, (
        f"\nIntent:    {intent!r}\n"
        f"Esperado:  {expected!r}\n"
        f"Obtenido:  {got!r}\n"
        "→ Revisar _KEYWORD_MAP / _STRONG_KEYWORDS en classifier_data.py"
    )
