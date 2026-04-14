"""Email domain services."""

from app.services.email.service import (
    PROVIDER_PRESETS,
    EmailCredentials,
    EmailMessage,
    credentials_from_dict,
    read_inbox,
    read_unread,
    send_email_smtp,
    test_imap_connection,
)

__all__ = [
    "PROVIDER_PRESETS",
    "EmailCredentials",
    "EmailMessage",
    "credentials_from_dict",
    "read_inbox",
    "read_unread",
    "send_email_smtp",
    "test_imap_connection",
]
