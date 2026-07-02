"""Schemas Pydantic para gestión documental."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


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


class ContractChatMsg(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ContractInterviewIn(BaseModel):
    contract_type: str  # servicios | trabajo | nda | alquiler
    messages: list[ContractChatMsg] = []


class ContractInterviewOut(BaseModel):
    message: str
    done: bool
    contract: str | None = None


class ContractSaveIn(BaseModel):
    contract_type: str
    title: str
    content: str  # markdown del contrato redactado


class SemanticSearchHit(BaseModel):
    """Un fragmento (chunk) relevante de la búsqueda semántica RAG."""

    document_id: str
    file_name: str | None = None
    chunk_index: str | None = None
    text: str
    page_number: int | None = None
    element_type: str | None = None
    similarity: float


class DocumentContentUpdate(BaseModel):
    """Cuerpo de PATCH /{id}/content. `content` acotado para evitar payloads enormes."""

    content: str = Field(max_length=5_000_000)
    append: bool = False


class ErpImportRequest(BaseModel):
    """Cuerpo (opcional) de los endpoints erp-import. El `target` lo valida el servicio."""

    target: str | None = None
