"""Pydantic schemas for document template endpoints."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TemplateCreate(BaseModel):
    name: str
    template_type: str = "invoice"  # invoice | payroll | excel
    layout_style: str = "modern"
    accent_color: str = "#6366f1"
    font_family: str = "helvetica"
    logo_position: str = "left"
    header_style: str = "color_band"
    table_style: str = "striped"
    footer_text: str | None = None
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: str | None = None
    layout_style: str | None = None
    accent_color: str | None = None
    font_family: str | None = None
    logo_position: str | None = None
    header_style: str | None = None
    table_style: str | None = None
    footer_text: str | None = None
    is_default: bool | None = None


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    template_type: str
    layout_style: str
    accent_color: str
    font_family: str
    logo_position: str
    header_style: str
    table_style: str
    footer_text: str | None
    is_default: bool

    model_config = ConfigDict(from_attributes=True)


class PreviewRequest(BaseModel):
    template_type: str = "invoice"
    layout_style: str = "modern"
    accent_color: str = "#6366f1"
    font_family: str = "helvetica"
    logo_position: str = "left"
    header_style: str = "color_band"
    table_style: str = "striped"
    footer_text: str | None = None
