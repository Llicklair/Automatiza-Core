"""send_email.attachment_ids must accept either a list[str] or a single
string ID. The LLM frequently passes a single document UUID as a bare
string ("8df72dbc-...") instead of wrapping it in a list, and a strict
list-only Pydantic schema rejected it with:

  attachment_ids: Input should be a valid list

The function already coerces string -> [string] internally, but the
StructuredTool args_schema validates BEFORE the function runs. The fix
is to widen the type annotation so the schema accepts both shapes.
"""
from __future__ import annotations

from app.agents.email.tools import send_email


class TestSendEmailAttachmentIdsAcceptsBothShapes:
    def test_args_schema_accepts_list(self):
        fields = send_email.args_schema.model_fields
        assert "attachment_ids" in fields

        # Validate with a list[str] — should pass
        validated = send_email.args_schema.model_validate(
            {
                "tenant_id": "00000000-0000-0000-0000-000000000001",
                "to": "x@y.com",
                "subject": "s",
                "body": "b",
                "attachment_ids": ["a", "b"],
            }
        )
        assert validated.attachment_ids == ["a", "b"]

    def test_args_schema_accepts_single_string(self):
        # Validate with a bare string (the case the LLM kept hitting)
        # — should pass after the type widening, would have raised before.
        validated = send_email.args_schema.model_validate(
            {
                "tenant_id": "00000000-0000-0000-0000-000000000001",
                "to": "x@y.com",
                "subject": "s",
                "body": "b",
                "attachment_ids": "single-doc-uuid",
            }
        )
        # Pydantic preserves the string at validation time; the function
        # itself coerces it to a list later via isinstance check.
        assert validated.attachment_ids == "single-doc-uuid"

    def test_args_schema_accepts_none(self):
        validated = send_email.args_schema.model_validate(
            {
                "tenant_id": "00000000-0000-0000-0000-000000000001",
                "to": "x@y.com",
                "subject": "s",
                "body": "b",
                "attachment_ids": None,
            }
        )
        assert validated.attachment_ids is None
