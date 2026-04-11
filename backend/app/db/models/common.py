"""Imports y utilidades compartidas por todos los modelos de dominio."""

from datetime import UTC, datetime


def utcnow():
    return datetime.now(UTC)
