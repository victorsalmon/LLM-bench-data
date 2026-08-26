"""Shared experiment helpers."""

import re


def word_count(text: str) -> int:
    """Count words in *text* using a simple regex."""
    return len(re.findall(r"\b\w+\b", text or ""))
