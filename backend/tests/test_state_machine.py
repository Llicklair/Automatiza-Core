"""Tests para app.services.state_machine."""
import pytest
from app.services.state_machine import (
    InvalidTransitionError,
    allowed_next_states,
    can_transition,
    is_terminal,
    validate_transition,
)


class TestInvoiceTransitions:
    def test_draft_to_issued(self):
        validate_transition("Invoice", "draft", "issued")  # no lanza

    def test_draft_to_cancelled(self):
        validate_transition("Invoice", "draft", "cancelled")

    def test_issued_to_paid(self):
        validate_transition("Invoice", "issued", "paid")

    def test_issued_to_cancelled(self):
        validate_transition("Invoice", "issued", "cancelled")

    def test_paid_is_terminal(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("Invoice", "paid", "draft")

    def test_cancelled_is_terminal(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("Invoice", "cancelled", "draft")

    def test_draft_to_paid_not_allowed(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("Invoice", "draft", "paid")


class TestPayrollTransitions:
    def test_draft_to_approved(self):
        validate_transition("Payroll", "draft", "approved")

    def test_approved_to_paid(self):
        validate_transition("Payroll", "approved", "paid")

    def test_draft_to_rejected(self):
        validate_transition("Payroll", "draft", "rejected")

    def test_paid_is_terminal(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("Payroll", "paid", "draft")


class TestTaskTransitions:
    def test_pending_to_planning(self):
        validate_transition("Task", "pending", "planning")

    def test_executing_to_done(self):
        validate_transition("Task", "executing", "done")

    def test_executing_to_failed(self):
        validate_transition("Task", "executing", "failed")

    def test_done_is_terminal(self):
        with pytest.raises(InvalidTransitionError):
            validate_transition("Task", "done", "pending")


class TestCanTransition:
    def test_valid_returns_true(self):
        assert can_transition("Invoice", "draft", "issued") is True

    def test_invalid_returns_false(self):
        assert can_transition("Invoice", "paid", "draft") is False


class TestAllowedNextStates:
    def test_draft_invoice(self):
        states = allowed_next_states("Invoice", "draft")
        assert "issued" in states
        assert "cancelled" in states

    def test_terminal_returns_empty(self):
        states = allowed_next_states("Invoice", "paid")
        assert states == []


class TestIsTerminal:
    def test_paid_is_terminal(self):
        assert is_terminal("Invoice", "paid") is True

    def test_draft_is_not_terminal(self):
        assert is_terminal("Invoice", "draft") is False


class TestInvalidTransitionError:
    def test_error_message_contains_info(self):
        with pytest.raises(InvalidTransitionError) as exc_info:
            validate_transition("Invoice", "paid", "draft")
        err = exc_info.value
        assert err.entity == "Invoice"
        assert err.current == "paid"
        assert err.target == "draft"
        assert "Invoice" in str(err)
