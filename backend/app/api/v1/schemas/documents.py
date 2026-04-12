"""Schemas Pydantic para gestión documental."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    file_name: str
    file_type: str | None
    file_size: int
    status: str
    parsed_content: str | None
    category: str | None
    created_at: datetime
    processed_at: datetime | None
    task_id: uuid.UUID | None


class ScanResultOut(BaseModel):
    document: DocumentOut
    auto_category: str
    message: str


class ImportDBOut(BaseModel):
    document_id: uuid.UUID
    file_name: str
    rows_detected: int
    columns: list[str]
    category: str
    task_id: uuid.UUID | None
    message: str


class ContractTemplateOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    file_name: str
    file_size: int
    file_path: str
    created_at: datetime


class ContractPreviewHtmlOut(BaseModel):
    html: str
    html_editable: str
    variables_detected: list[str]
    warnings: list[str]


class ContractBodyHtmlIn(BaseModel):
    html: str
