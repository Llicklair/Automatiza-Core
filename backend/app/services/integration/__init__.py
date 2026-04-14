"""Integration domain services — re-exports for backwards compatibility."""

from app.services.integration.heartbeat import (
    bootstrap_employee_heartbeats,
    register_employee_heartbeat,
    run_employee_heartbeat,
    unregister_employee_heartbeat,
)
from app.services.integration.messaging import (
    connect_telegram,
    disconnect_telegram,
    find_integration_by_chat,
    get_telegram_status,
    handle_link_command,
    process_and_reply,
    send_reply,
    send_typing_indicator,
    setup_webhook,
    verify_webhook_secret,
)
from app.services.integration.service import (
    connect_email,
    connect_psd2,
    disconnect_integration,
    email_status,
    get_integration,
    get_oauth_access_token,
    get_recent_files,
    get_recent_messages,
    get_status,
    handle_oauth_callback,
    list_integrations,
    pop_oauth_state,
    set_oauth_state,
    upsert_integration,
)

__all__ = [
    # heartbeat
    "bootstrap_employee_heartbeats",
    "register_employee_heartbeat",
    "run_employee_heartbeat",
    "unregister_employee_heartbeat",
    # messaging
    "connect_telegram",
    "disconnect_telegram",
    "find_integration_by_chat",
    "get_telegram_status",
    "handle_link_command",
    "process_and_reply",
    "send_reply",
    "send_typing_indicator",
    "setup_webhook",
    "verify_webhook_secret",
    # service
    "connect_email",
    "connect_psd2",
    "disconnect_integration",
    "email_status",
    "get_integration",
    "get_oauth_access_token",
    "get_recent_files",
    "get_recent_messages",
    "get_status",
    "handle_oauth_callback",
    "list_integrations",
    "pop_oauth_state",
    "set_oauth_state",
    "upsert_integration",
]
