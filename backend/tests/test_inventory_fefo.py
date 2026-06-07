"""Tests de la lógica pura FEFO (sin base de datos)."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.services.inventory._fefo import LotAllocation, plan_fefo_deduction


@dataclass
class FakeLot:
    id: str
    quantity: int
    expiry_date: date | None
    received_at: datetime | None = None


def _dt(y, m, d):
    return datetime(y, m, d, tzinfo=timezone.utc)


def test_deducts_from_earliest_expiry_first():
    lots = [
        FakeLot("tarde", 10, date(2026, 12, 1)),
        FakeLot("pronto", 10, date(2026, 6, 1)),
    ]
    plan, shortage = plan_fefo_deduction(lots, 5)
    assert shortage == 0
    assert plan == [LotAllocation("pronto", 5)]


def test_spans_multiple_lots_in_fefo_order():
    lots = [
        FakeLot("a", 3, date(2026, 6, 1)),
        FakeLot("b", 4, date(2026, 7, 1)),
        FakeLot("c", 10, date(2026, 8, 1)),
    ]
    plan, shortage = plan_fefo_deduction(lots, 8)
    assert shortage == 0
    assert plan == [
        LotAllocation("a", 3),
        LotAllocation("b", 4),
        LotAllocation("c", 1),
    ]


def test_lots_without_expiry_go_last():
    lots = [
        FakeLot("sin_caducidad", 10, None),
        FakeLot("con_caducidad", 4, date(2026, 6, 1)),
    ]
    plan, shortage = plan_fefo_deduction(lots, 6)
    assert shortage == 0
    assert plan == [
        LotAllocation("con_caducidad", 4),
        LotAllocation("sin_caducidad", 2),
    ]


def test_tie_on_expiry_uses_earliest_received():
    same = date(2026, 6, 1)
    lots = [
        FakeLot("nuevo", 5, same, _dt(2026, 5, 10)),
        FakeLot("viejo", 5, same, _dt(2026, 1, 10)),
    ]
    plan, shortage = plan_fefo_deduction(lots, 3)
    assert shortage == 0
    assert plan == [LotAllocation("viejo", 3)]


def test_reports_shortage_when_insufficient():
    lots = [FakeLot("a", 2, date(2026, 6, 1))]
    plan, shortage = plan_fefo_deduction(lots, 5)
    assert plan == [LotAllocation("a", 2)]
    assert shortage == 3


def test_skips_empty_lots():
    lots = [
        FakeLot("vacio", 0, date(2026, 1, 1)),
        FakeLot("ok", 5, date(2026, 6, 1)),
    ]
    plan, shortage = plan_fefo_deduction(lots, 4)
    assert shortage == 0
    assert plan == [LotAllocation("ok", 4)]


def test_non_positive_quantity_is_noop():
    lots = [FakeLot("a", 5, date(2026, 6, 1))]
    assert plan_fefo_deduction(lots, 0) == ([], 0)
    assert plan_fefo_deduction(lots, -3) == ([], 0)
