"""Numeric helpers for accounting calculations."""

from __future__ import annotations

from decimal import Decimal
from typing import Union

NumberLike = Union[int, float, str, Decimal]


def to_decimal(value: NumberLike, *, field: str) -> Decimal:
    if isinstance(value, bool):
        raise TypeError(f"{field} must be numeric, not boolean")
    try:
        parsed = Decimal(str(value))
    except Exception as exc:
        raise TypeError(f"{field} must be decimal-compatible") from exc
    if not parsed.is_finite():
        raise ValueError(f"{field} must be finite")
    return parsed


def require_nonnegative(value: Decimal, *, field: str) -> Decimal:
    if value < 0:
        raise ValueError(f"{field} must be nonnegative")
    return value


def require_positive(value: Decimal, *, field: str) -> Decimal:
    if value <= 0:
        raise ValueError(f"{field} must be positive")
    return value

