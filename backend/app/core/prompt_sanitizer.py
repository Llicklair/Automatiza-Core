"""
Sanitizador de inputs de usuario antes de enviarlos al LLM.
Previene prompt injection eliminando patrones peligrosos.
"""

import re

# Patrones que pueden indicar prompt injection
_INJECTION_PATTERNS = [
    r"\[SYSTEM\]",
    r"\[INST\]",
    r"<<SYS>>",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"ignore (?:all )?previous (?:instructions|rules|prompts)",
    r"you are now",
    r"new instructions:",
    r"override (?:system|previous)",
    r"jailbreak",
    r"DAN mode",
]

_COMPILED = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def sanitize_user_input(text: str, max_length: int = 4000) -> str:
    """
    Sanitiza texto de usuario antes de inyectarlo en un prompt LLM.
    - Trunca a max_length caracteres
    - Elimina patrones de prompt injection conocidos
    - Escapa delimitadores de prompt
    """
    if not text:
        return ""
    text = text[:max_length]
    text = _COMPILED.sub("[FILTERED]", text)
    return text.strip()
