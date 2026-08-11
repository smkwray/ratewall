"""Shared provenance ordering for claim state, events, and headline atoms."""

from __future__ import annotations


MEASUREMENT_CLASSES = frozenset(
    {
        "measured_security",
        "measured_contract",
        "measured_bucket",
        "measured_aggregate",
        "inferred_cohort",
        "calibrated_assumption_ladder",
        "structural_zero",
        "unavailable",
    }
)


def weakest_measurement_class(*classes: str) -> str:
    """Return the weakest provenance required to construct a derived object."""

    if not classes or any(value not in MEASUREMENT_CLASSES for value in classes):
        raise ValueError(f"cannot combine measurement classes {classes!r}")
    unique = set(classes)
    if len(unique) == 1:
        return classes[0]
    for weakest in (
        "unavailable",
        "calibrated_assumption_ladder",
        "inferred_cohort",
    ):
        if weakest in unique:
            return weakest
    unique.discard("structural_zero")
    if len(unique) == 1:
        return next(iter(unique))
    if not unique:
        return "structural_zero"
    return "measured_aggregate"
