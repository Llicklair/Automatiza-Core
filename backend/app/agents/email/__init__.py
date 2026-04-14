"""
Email agent package.
"""

from .agent import run_email_agent, send_email_direct
from .tools import build_tools_list, check_inbox, check_unread, send_email

__all__ = [
    "run_email_agent",
    "send_email_direct",
    "check_inbox",
    "check_unread",
    "send_email",
    "build_tools_list",
]
