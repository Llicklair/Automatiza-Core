"""Tests for workflow condition evaluator."""
from app.services.workflow.conditions import evaluate_conditions


class TestLeafOperators:
    def test_eq_true(self):
        assert evaluate_conditions({"field": "status", "op": "eq", "value": "pending"}, {"status": "pending"})

    def test_eq_false(self):
        assert not evaluate_conditions({"field": "status", "op": "eq", "value": "paid"}, {"status": "pending"})

    def test_ne(self):
        assert evaluate_conditions({"field": "status", "op": "ne", "value": "paid"}, {"status": "pending"})

    def test_gt(self):
        assert evaluate_conditions({"field": "amount", "op": "gt", "value": 1000}, {"amount": 1500})

    def test_gt_false(self):
        assert not evaluate_conditions({"field": "amount", "op": "gt", "value": 1000}, {"amount": 500})

    def test_gte_equal(self):
        assert evaluate_conditions({"field": "amount", "op": "gte", "value": 1000}, {"amount": 1000})

    def test_lt(self):
        assert evaluate_conditions({"field": "amount", "op": "lt", "value": 1000}, {"amount": 500})

    def test_lte(self):
        assert evaluate_conditions({"field": "amount", "op": "lte", "value": 1000}, {"amount": 1000})

    def test_contains(self):
        assert evaluate_conditions({"field": "name", "op": "contains", "value": "García"}, {"name": "María García"})

    def test_in(self):
        assert evaluate_conditions({"field": "status", "op": "in", "value": ["pending", "overdue"]}, {"status": "pending"})

    def test_in_false(self):
        assert not evaluate_conditions({"field": "status", "op": "in", "value": ["pending", "overdue"]}, {"status": "paid"})

    def test_exists(self):
        assert evaluate_conditions({"field": "email", "op": "exists"}, {"email": "test@example.com"})

    def test_not_exists(self):
        assert evaluate_conditions({"field": "email", "op": "not_exists"}, {"name": "John"})


class TestCompoundOperators:
    def test_and_all_true(self):
        cond = {
            "operator": "AND",
            "conditions": [
                {"field": "amount", "op": "gt", "value": 1000},
                {"field": "status", "op": "eq", "value": "pending"},
            ],
        }
        assert evaluate_conditions(cond, {"amount": 1500, "status": "pending"})

    def test_and_one_false(self):
        cond = {
            "operator": "AND",
            "conditions": [
                {"field": "amount", "op": "gt", "value": 1000},
                {"field": "status", "op": "eq", "value": "paid"},
            ],
        }
        assert not evaluate_conditions(cond, {"amount": 1500, "status": "pending"})

    def test_or_one_true(self):
        cond = {
            "operator": "OR",
            "conditions": [
                {"field": "amount", "op": "gt", "value": 9000},
                {"field": "status", "op": "eq", "value": "pending"},
            ],
        }
        assert evaluate_conditions(cond, {"amount": 500, "status": "pending"})

    def test_or_all_false(self):
        cond = {
            "operator": "OR",
            "conditions": [
                {"field": "amount", "op": "gt", "value": 9000},
                {"field": "status", "op": "eq", "value": "paid"},
            ],
        }
        assert not evaluate_conditions(cond, {"amount": 500, "status": "pending"})

    def test_not(self):
        cond = {"operator": "NOT", "condition": {"field": "status", "op": "eq", "value": "paid"}}
        assert evaluate_conditions(cond, {"status": "pending"})

    def test_nested(self):
        cond = {
            "operator": "AND",
            "conditions": [
                {"field": "amount", "op": "gte", "value": 500},
                {
                    "operator": "OR",
                    "conditions": [
                        {"field": "status", "op": "eq", "value": "overdue"},
                        {"field": "priority", "op": "gte", "value": 5},
                    ],
                },
            ],
        }
        assert evaluate_conditions(cond, {"amount": 1000, "status": "overdue", "priority": 3})
        assert evaluate_conditions(cond, {"amount": 1000, "status": "pending", "priority": 7})
        assert not evaluate_conditions(cond, {"amount": 1000, "status": "pending", "priority": 2})


class TestEdgeCases:
    def test_none_condition_always_true(self):
        assert evaluate_conditions(None, {"amount": 0})

    def test_empty_condition_always_true(self):
        assert evaluate_conditions({}, {"amount": 0})

    def test_missing_field_eq_false(self):
        assert not evaluate_conditions({"field": "missing", "op": "eq", "value": "x"}, {})

    def test_dot_notation(self):
        assert evaluate_conditions(
            {"field": "invoice.amount", "op": "gt", "value": 100},
            {"invoice": {"amount": 200}},
        )

    def test_temporal_context_weekday(self):
        cond = {"field": "now_weekday", "op": "eq", "value": 0}  # lunes
        assert evaluate_conditions(cond, {"now_weekday": 0})
        assert not evaluate_conditions(cond, {"now_weekday": 2})
