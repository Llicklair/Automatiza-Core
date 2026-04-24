"""Pydantic schemas for HR Documents endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GenerateRequest(BaseModel):
    doc_type: str  # contract, nda, termination, settlement, addendum, other
    instructions: str = ""  # Free-text description of what to generate
    employee_name: str | None = None  # Optional: auto-fill employee data
    employee_id: str | None = None  # Optional: pull data from HR module


class HRDocumentOut(BaseModel):
    id: str
    doc_type: str
    title: str
    employee_name: str | None
    content_html: str
    status: str
    instructions: str | None
    created_at: datetime
    approved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
