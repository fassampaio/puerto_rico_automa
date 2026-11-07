"""Text utilities."""

from __future__ import annotations

import unicodedata

_SYMBOLS = str.maketrans(
    {"·": "|", "←": "<-", "→": "->", "—": "-", "–": "-"}
)


def to_ascii(text: str) -> str:
    """Strip accents and symbols (e.g. "café" -> "cafe") for output and log files."""
    normalized = unicodedata.normalize("NFKD", text.translate(_SYMBOLS))
    return normalized.encode("ascii", "ignore").decode("ascii")
