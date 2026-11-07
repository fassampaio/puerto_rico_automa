"""Utilitários de texto."""

from __future__ import annotations

import unicodedata

_SYMBOLS = str.maketrans({"·": "|", "←": "<-", "→": "->", "—": "-", "–": "-", "º": "o", "ª": "a"})


def to_ascii(text: str) -> str:
    """Remove acentos e cedilha (ação -> acao), para saídas e arquivos de log."""
    normalized = unicodedata.normalize("NFKD", text.translate(_SYMBOLS))
    return normalized.encode("ascii", "ignore").decode("ascii")
