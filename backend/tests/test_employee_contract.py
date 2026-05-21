"""Tests del validador del contrato AIEmployee (≥2 de 4 capacidades)."""

import pytest

from app.services.ai.employee_contract import (
    MIN_CAPABILITIES,
    count_capabilities,
    validate_employee_contract,
)


@pytest.mark.parametrize(
    "kwargs, expected_count",
    [
        (dict(scope=None, memory_enabled=False, knowledge_enabled=False, workflows=None), 0),
        (dict(scope={"clients": [1]}, memory_enabled=False, knowledge_enabled=False, workflows=None), 1),
        (dict(scope={"clients": [1]}, memory_enabled=True, knowledge_enabled=False, workflows=None), 2),
        (dict(scope=None, memory_enabled=True, knowledge_enabled=True, workflows=[{"n": "x"}]), 3),
        (dict(scope={"a": ["x"]}, memory_enabled=True, knowledge_enabled=True, workflows=[{"n": "y"}]), 4),
    ],
)
def test_count_capabilities(kwargs, expected_count):
    assert count_capabilities(**kwargs) == expected_count


def test_empty_containers_count_as_absent():
    # dict vacío y listas vacías no son capacidad presente
    assert count_capabilities(
        scope={}, memory_enabled=False, knowledge_enabled=False, workflows=[]
    ) == 0


def test_scope_only_with_falsy_values_does_not_count():
    # scope con todas sus claves vacías/None tampoco cuenta
    assert count_capabilities(
        scope={"clients": [], "categories": None},
        memory_enabled=False,
        knowledge_enabled=False,
        workflows=None,
    ) == 0


def test_contract_fails_below_minimum():
    ok, msg = validate_employee_contract(
        scope=None, memory_enabled=False, knowledge_enabled=False, workflows=None
    )
    assert ok is False
    assert "0" in msg
    assert "Perfil" in msg


def test_contract_passes_at_minimum():
    ok, msg = validate_employee_contract(
        scope={"clients": [1]},
        memory_enabled=True,
        knowledge_enabled=False,
        workflows=None,
    )
    assert ok is True
    assert "2/4" in msg


def test_minimum_constant_is_two():
    assert MIN_CAPABILITIES == 2
