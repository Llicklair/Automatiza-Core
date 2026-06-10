"""
Email agent package.
"""

from .agent import run_email_agent
from .tools import build_tools_list, check_inbox, check_unread, send_email

__all__ = [
    "run_email_agent",
    "check_inbox",
    "check_unread",
    "send_email",
    "build_tools_list",
]
