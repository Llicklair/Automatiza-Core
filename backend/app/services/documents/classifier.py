"""
Clasificador de documentos por reglas — 0 tokens LLM.

Detecta tipo de documento usando keywords y patrones regex.
Solo recurre al LLM cuando no puede clasificar con confianza.
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RuleClassification:
    """Resultado de clasificación por reglas."""

    document_type: str  # factura_recibida, contrato, extracto_bancario, nomina, otro
    confidence: float  # 0.0 - 1.0
    matched_rules: list[str] = field(default_factory=list)
    key_entities: dict = field(default_factory=dict)
    needs_llm: bool = False  # True si la clasificación no es fiable


# Patrones para extracción de entidades
NIF_PATTERN = re.compile(r"\b([A-Z][- ]?\d{7}[- ]?[A-Z0-9]|\d{8}[- ]?[A-Z]|[XYZ][- ]?\d{7}[- ]?[A-Z])\b")
IMPORTE_PATTERN = re.compile(r"(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€")
FECHA_PATTERN = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b")
IBAN_PATTERN = re.compile(r"\b(ES\d{2}\s?\d{4}\s?\d{4}\s?\d{2}\s?\d{10})\b")

# Reglas de clasificación: (keywords, tipo, peso)
RULES = [
    # Facturas
    {
        "type": "factura_recibida",
        "keywords": [
            "factura",
            "invoice",
            "nº factura",
            "num factura",
            "base imponible",
            "iva",
            "irpf",
            "total factura",
            "importe total",
        ],
        "strong_keywords": ["base imponible", "iva", "total factura"],
        "requires": ["importe"],  # debe tener al menos un importe
    },
    # Nóminas
    {
        "type": "nomina",
        "keywords": [
            "nómina",
            "nomina",
            "salario bruto",
            "salario neto",
            "seguridad social",
            "retención irpf",
            "devengos",
            "deducciones",
            "trabajador",
            "categoría profesional",
        ],
        "strong_keywords": ["salario bruto", "devengos", "deducciones", "seguridad social"],
        "requires": [],
    },
    # Extractos bancarios
    {
        "type": "extracto_bancario",
        "keywords": [
            "extracto",
            "saldo",
            "movimientos",
            "cuenta corriente",
            "debe",
            "haber",
            "saldo anterior",
            "saldo final",
            "fecha valor",
            "concepto",
        ],
        "strong_keywords": ["saldo anterior", "saldo final", "fecha valor"],
        "requires": ["iban"],
    },
    # Contratos
    {
        "type": "contrato",
        "keywords": [
            "contrato",
            "cláusula",
            "clausula",
            "estipulaciones",
            "partes contratantes",
            "objeto del contrato",
            "duración",
            "rescisión",
            "firma",
            "comparecen",
        ],
        "strong_keywords": ["cláusula", "partes contratantes", "estipulaciones", "comparecen"],
        "requires": [],
    },
]


def classify_by_rules(text: str) -> RuleClassification:
    """
    Clasifica un documento usando reglas de keywords y patrones.

    Args:
        text: Texto extraído del documento.

    Returns:
        RuleClassification con tipo, confianza y entidades.
        Si needs_llm=True, se recomienda usar el LLM para confirmar.
    """
    text_lower = text.lower()
    text_upper = text.upper()

    # Extraer entidades
    entities = {}
    nifs = NIF_PATTERN.findall(text_upper)
    if nifs:
        entities["nifs"] = list(dict.fromkeys([n.replace("-", "").replace(" ", "") for n in nifs]))

    importes = IMPORTE_PATTERN.findall(text)
    if importes:
        entities["importes"] = importes

    fechas = FECHA_PATTERN.findall(text)
    if fechas:
        entities["fechas"] = fechas[:5]  # max 5

    ibans = IBAN_PATTERN.findall(text_upper)
    if ibans:
        entities["ibans"] = [i.replace(" ", "") for i in ibans]

    # Puntuar cada tipo
    scores = []
    for rule in RULES:
        score = 0
        matched = []

        # Keywords normales: +1 punto c/u
        for kw in rule["keywords"]:
            if kw in text_lower:
                score += 1
                matched.append(kw)

        # Keywords fuertes: +3 puntos c/u
        for kw in rule["strong_keywords"]:
            if kw in text_lower:
                score += 3
                matched.append(f"*{kw}")

        # Requisitos: si no se cumplen, penalizar
        for req in rule["requires"]:
            if req == "importe" and not importes:
                score -= 2
            if req == "iban" and not ibans:
                score -= 2

        scores.append((rule["type"], score, matched))

    # Ordenar por puntuación
    scores.sort(key=lambda x: x[1], reverse=True)
    best_type, best_score, best_matched = scores[0]

    # Determinar confianza
    if best_score >= 8:
        confidence = 0.95
    elif best_score >= 5:
        confidence = 0.85
    elif best_score >= 3:
        confidence = 0.70
    else:
        confidence = 0.40

    # ¿Necesita LLM?
    needs_llm = confidence < 0.70

    # Si la confianza es muy baja, clasificar como "otro"
    if best_score < 2:
        best_type = "otro"
        confidence = 0.30
        needs_llm = True

    # Construir key_entities en formato compatible con ClassifiedDocument
    key_entities = {}
    if entities.get("nifs"):
        key_entities["nif"] = entities["nifs"][0]
    if entities.get("importes"):
        key_entities["importe"] = f"{entities['importes'][0]}€"
    if entities.get("fechas"):
        key_entities["fecha"] = entities["fechas"][0]
    if entities.get("ibans"):
        key_entities["iban"] = entities["ibans"][0]

    return RuleClassification(
        document_type=best_type,
        confidence=confidence,
        matched_rules=best_matched,
        key_entities=key_entities,
        needs_llm=needs_llm,
    )
