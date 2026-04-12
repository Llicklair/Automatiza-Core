"""Prompt loader — reads .txt files from the prompts/ folder."""

import functools
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


@functools.cache
def load_prompt(name: str) -> str:
    """Load a prompt by name (without extension).

    Usage: load_prompt("generative_ui") → reads prompts/generative_ui.txt
    Cached after first load (prompts don't change at runtime).
    """
    path = _PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()
