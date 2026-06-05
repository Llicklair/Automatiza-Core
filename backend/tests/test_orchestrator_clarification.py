"""Tests de la guarda de ambigüedad del Coordinador.

`needs_clarification` evita que el Coordinador se invente y ejecute un plan ante
instrucciones referenciales sin contenido concreto («haz lo de siempre con
Acme»). Es determinista y conservador: NO debe bloquear instrucciones válidas
que mencionan un dominio o cifras.
"""

from app.agents.orchestrator._validate_handlers import needs_clarification


def test_ambigua_lo_de_siempre():
    ambiguous, q = needs_clarification("Haz lo de siempre con Acme")
    assert ambiguous
    assert "ambigua" in q.lower()


def test_ambigua_vacia():
    ambiguous, q = needs_clarification("")
    assert ambiguous
    assert q


def test_ambigua_lo_tipico():
    ambiguous, _ = needs_clarification("haz lo típico")
    assert ambiguous


def test_ambigua_lo_de_costumbre():
    ambiguous, _ = needs_clarification("prepárame lo de costumbre")
    assert ambiguous


def test_no_ambigua_con_dominio_y_cifra():
    # «como siempre» pero con factura + importe concretos → ejecutable.
    ambiguous, _ = needs_clarification("Crea la factura de 500€ a Acme como siempre")
    assert not ambiguous


def test_no_ambigua_con_dominio():
    ambiguous, _ = needs_clarification("Genera la nómina de Juan como siempre")
    assert not ambiguous


def test_no_ambigua_instruccion_concreta():
    ambiguous, _ = needs_clarification("Concilia el banco de abril")
    assert not ambiguous


def test_no_ambigua_sin_frase_vaga():
    ambiguous, _ = needs_clarification("Envía un recordatorio a los clientes con facturas vencidas")
    assert not ambiguous
