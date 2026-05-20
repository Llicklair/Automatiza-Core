"""Servicios IA para email: clasificación de bandeja + redacción de borradores."""

from app.services.email_ai.classifier import EmailAIError, classify_messages, draft_reply

__all__ = ["classify_messages", "draft_reply", "EmailAIError"]
