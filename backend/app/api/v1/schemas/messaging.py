"""Pydantic schemas for messaging routes."""

from pydantic import BaseModel


class TelegramConnectResponse(BaseModel):
    link_url: str
    link_token: str
    bot_username: str | None = None
