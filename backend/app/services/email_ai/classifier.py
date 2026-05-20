"""Clasificación de bandeja Gmail/Outlook y redacción de borradores con Anthropic.

Una llamada IA por operación. No usamos LangChain porque son round-trips puntuales.

Categorías:
  - urgente: cliente cabreado, plazo inminente, problema bloqueante
  - factura: cobros, presupuestos, recordatorios de pago
  - consulta: pregunta de cliente que requiere respuesta humana
  - proveedor: comunicaciones de proveedores (no urgentes)
  - rrhh: candidatos, empleados, gestiones internas
  - marketing: newsletters, ofertas, automáticos
  - spam: phishing, promociones no deseadas
  - otro: lo demás
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from app.core.config import settings

_log = logging.getLogger(__name__)

ALLOWED_CATEGORIES = {
    "urgente", "factura", "consulta", "proveedor",
    "rrhh", "marketing", "spam", "otro",
}

_CLASSIFY_PROMPT = """Eres un asistente que clasifica mensajes de email de una PYME española.

Para cada mensaje recibido, devuelve un objeto con:
- "id": el id original del mensaje (string)
- "category": una de: "urgente","factura","consulta","proveedor","rrhh","marketing","spam","otro"
- "urgency": entero 1-5 (1=ignorable, 5=responder hoy mismo)
- "requires_reply": true si el remitente espera respuesta humana
- "suggested_action": frase corta (<=80 chars) en español describiendo qué hacer

Devuelve EXCLUSIVAMENTE un objeto JSON con la forma:
{"items": [{...}, {...}, ...]}

Sin texto fuera del JSON, sin markdown. Si un mensaje es claramente spam o marketing devuelve requires_reply=false y urgency=1.
"""


_DRAFT_PROMPT = """Eres un asistente que redacta borradores de respuesta a emails para una PYME española.

Reglas:
- Tono profesional, cercano, claro. Sin "Estimado Sr.", usa "Hola {nombre}," o "Buenos días,".
- En español neutro de España (tú/aquí), nunca voseo.
- Máximo 6 párrafos cortos.
- Si la pregunta requiere datos que no tienes (importes, fechas, números de factura), pon entre corchetes [DATO POR CONFIRMAR] en vez de inventar.
- Termina con un saludo y la firma "{firma_placeholder}" exactamente así (la app la sustituye luego).
- NO inventes acuerdos, precios ni compromisos.

Devuelve EXCLUSIVAMENTE este JSON sin texto adicional ni markdown:
{
  "subject": "Asunto de la respuesta (Re: ...)",
  "body": "Texto completo de la respuesta con saltos de línea \\n",
  "confidence": 0.0 a 1.0,
  "warnings": ["aviso 1", "aviso 2"]  // datos a confirmar, ambigüedades
}
"""


@dataclass
class EmailClassification:
    id: str
    category: str
    urgency: int
    requires_reply: bool
    suggested_action: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "urgency": self.urgency,
            "requires_reply": self.requires_reply,
            "suggested_action": self.suggested_action,
        }


@dataclass
class EmailDraft:
    subject: str
    body: str
    confidence: float
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "body": self.body,
            "confidence": self.confidence,
            "warnings": self.warnings,
        }


class EmailAIError(RuntimeError):
    pass


def _parse_json_loose(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise EmailAIError("La IA no devolvió un objeto JSON parseable")
    return json.loads(match.group(0))


def _get_client():
    api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
    if not api_key:
        raise EmailAIError("Falta ANTHROPIC_API_KEY en configuración.")
    try:
        from anthropic import AsyncAnthropic
    except ImportError as e:
        raise EmailAIError("SDK anthropic no instalado.") from e
    return AsyncAnthropic(api_key=api_key)


def _model() -> str:
    return getattr(settings, "ANTHROPIC_MODEL", None) or "claude-haiku-4-5-20251001"


async def classify_messages(messages: list[dict]) -> list[EmailClassification]:
    """Clasifica una lista de emails. Espera ítems con id/from/subject/snippet."""
    if not messages:
        return []
    if len(messages) > 30:
        # Procesar en lotes; el LLM se vuelve flojo si le metes 100 a la vez.
        out = []
        for i in range(0, len(messages), 30):
            out.extend(await classify_messages(messages[i:i + 30]))
        return out

    client = _get_client()
    items_payload = [
        {
            "id": str(m.get("id", "")),
            "from": str(m.get("from", ""))[:120],
            "subject": str(m.get("subject", ""))[:160],
            "snippet": str(m.get("snippet", ""))[:400],
        }
        for m in messages
    ]

    resp = await client.messages.create(
        model=_model(),
        max_tokens=2000,
        system=_CLASSIFY_PROMPT,
        messages=[{
            "role": "user",
            "content": "Clasifica estos mensajes:\n" + json.dumps(items_payload, ensure_ascii=False, indent=2),
        }],
    )
    text_blocks = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    if not text_blocks:
        raise EmailAIError("La IA no devolvió contenido")

    payload = _parse_json_loose(text_blocks[0])
    items = payload.get("items", payload if isinstance(payload, list) else [])

    results: list[EmailClassification] = []
    for raw in items:
        cat = str(raw.get("category", "otro")).lower()
        if cat not in ALLOWED_CATEGORIES:
            cat = "otro"
        try:
            urgency = int(raw.get("urgency", 2))
        except (TypeError, ValueError):
            urgency = 2
        urgency = max(1, min(5, urgency))
        results.append(EmailClassification(
            id=str(raw.get("id", "")),
            category=cat,
            urgency=urgency,
            requires_reply=bool(raw.get("requires_reply", False)),
            suggested_action=str(raw.get("suggested_action", ""))[:120],
        ))
    return results


async def draft_reply(
    message: dict,
    context: str = "",
    user_full_name: str | None = None,
) -> EmailDraft:
    """Redacta un borrador de respuesta para un email entrante.

    `message` debe incluir from, subject, body (o snippet) y date.
    `context` opcional: contexto adicional sobre el cliente/proyecto.
    """
    client = _get_client()

    firma = "[Tu nombre]" if not user_full_name else user_full_name

    user_msg = {
        "remitente": str(message.get("from", "")),
        "asunto": str(message.get("subject", "")),
        "fecha": str(message.get("date", "")),
        "cuerpo": str(message.get("body") or message.get("snippet") or "")[:4000],
    }
    if context:
        user_msg["contexto_adicional"] = context

    resp = await client.messages.create(
        model=_model(),
        max_tokens=1500,
        system=_DRAFT_PROMPT.replace("{firma_placeholder}", firma),
        messages=[{
            "role": "user",
            "content": "Redacta una respuesta para este mensaje:\n" + json.dumps(user_msg, ensure_ascii=False, indent=2),
        }],
    )

    text_blocks = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    if not text_blocks:
        raise EmailAIError("La IA no devolvió contenido")

    payload = _parse_json_loose(text_blocks[0])
    return EmailDraft(
        subject=str(payload.get("subject", ""))[:200],
        body=str(payload.get("body", "")),
        confidence=float(payload.get("confidence", 0.5)),
        warnings=[str(w)[:200] for w in payload.get("warnings", [])][:5],
    )
