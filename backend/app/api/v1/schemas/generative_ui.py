"""Schemas Pydantic para Generative UI."""

from pydantic import BaseModel, ConfigDict, Field


class GenerateRequest(BaseModel):
    prompt: str = Field(max_length=8000)
    title: str | None = None


class GeneratedUIOut(BaseModel):
    id: str
    title: str
    description: str | None
    prompt: str
    content_html: str
    is_pinned: bool
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class UpdateUIRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    is_pinned: bool | None = None
