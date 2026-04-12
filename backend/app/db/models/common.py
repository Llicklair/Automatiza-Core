"""Imports y utilidades compartidas por todos los modelos de dominio."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


__all__ = [
    "JSONB",
    "UUID",
    "Base",
    "BigInteger",
    "Boolean",
    "Column",
    "Date",
    "DateTime",
    "ForeignKey",
    "Integer",
    "Numeric",
    "String",
    "Text",
    "relationship",
    "utcnow",
    "uuid",
]
