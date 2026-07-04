"""Small normalization helpers for source records."""

from __future__ import annotations

from decimal import Decimal


def parse_decimal_text(value: str | None) -> Decimal | None:
    if value is None:
        return None
    stripped = value.strip()
    if stripped in {"", "."}:
        return None
    return Decimal(stripped)

