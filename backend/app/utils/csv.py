from __future__ import annotations

from typing import Any

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n")


def sanitize_csv_text(value: Any) -> str:
    """Keep spreadsheet text cells from being interpreted as formulas."""
    text = "" if value is None else str(value)
    return f"'{text}" if text.startswith(FORMULA_PREFIXES) else text
