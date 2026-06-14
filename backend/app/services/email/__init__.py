"""Email domain services."""

from app.services.email.credentials import get_email_credentials, get_oauth_token
from app.services.email.sender import send_email
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
    "get_email_credentials",
    "get_oauth_token",
    "send_email",
    "PROVIDER_PRESETS",
    "EmailCredentials",
    "EmailMessage",
    "credentials_from_dict",
    "read_inbox",
    "read_unread",
    "send_email_smtp",
    "test_imap_connection",
]
