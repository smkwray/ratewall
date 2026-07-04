from __future__ import annotations

from pathlib import Path


TABLE_PLATE = Path("outputs/reports/ratewall_table_plate.md")


def test_release_table_plate_uses_live_runtime_denominator_language() -> None:
    text = TABLE_PLATE.read_text(encoding="utf-8")
    assert "default literature-backed annual-flow runtime family" in text
    assert "legacy sensitivity-only annual-flow anchors" in text
    assert "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv" in text
    assert "literature annual-flow bridge candidate" not in text
    assert (
        "Scenario-facing denominator stack showing runtime anchors, review-only "
        "literature annual-flow comparison rows, and bounded h8 overlay rows side by side"
        not in text
    )
    assert (
        "review-only literature annual-flow comparison rows tied to the "
        "runtime-primary literature family"
    ) in text
    assert "proxy-IV h8 gate" not in text


def test_release_table_plate_limits_reopen_paths_to_live_choices() -> None:
    text = TABLE_PLATE.read_text(encoding="utf-8")
    assert (
        "future reopen should be limited to h8 translation, h8-compatible numerator work, "
        "or genuinely new scale evidence"
    ) in text
