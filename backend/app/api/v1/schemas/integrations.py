"""Schemas Pydantic para integraciones."""

from pydantic import BaseModel


class IntegrationStatusOut(BaseModel):
    integration_type: str
    is_active: bool
    last_sync_at: str | None = None


class Psd2ConnectRequest(BaseModel):
    secret_id: str
    secret_key: str


class EmailConnectRequest(BaseModel):
    email_address: str
    password: str
    provider: str = "gmail"
    imap_host: str | None = None
    imap_port: int | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None
