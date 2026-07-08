from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.slr_conditions import (
    QUARANTINE_LABEL,
    SLR_CAPTION_NOTE,
    build_slr_conditions_experiment,
    cleanup_stale_hysteresis_redo_artifacts,
    write_slr_conditions_outputs,
)


PACK_DIR = Path("configs/rwtam/packs")


def test_slr_conditions_reduced_grid_emits_lineage_and_quarantine(tmp_path: Path) -> None:
    result = build_slr_conditions_experiment(PACK_DIR, full_grid=False, output_root=tmp_path)
    grid = result.rows("out_slr_conditions_grid")
    stimulus = result.rows("out_slr_stimulus_leg")
    fiat = result.rows("out_slr_fiat_response_curve")
    spectrum = result.rows("out_slr_spectrum")

    assert len(grid) == 2
    assert {row["absorption_regime"] for row in grid} == {"normal_0342"}
    assert {row["baseline_mode_B_share"] for row in grid} == {"0.342"}
    assert {row["horizon_years"] for row in grid} == {"1", "5"}
    assert all(row["claim_grade_label"] == "scenario_only_owner_flagged" for row in grid)
    assert all(Decimal(row["current_stimulus_bil"]) != 0 for row in grid)
    assert all("treated_rollup_path" in row for row in grid)
    assert stimulus[0]["tp_10y_bp"] == "-15"
    assert stimulus[0]["tp_30y_bp"] == "-20"

    assert any(QUARANTINE_LABEL in row["claim_grade_label"] for row in fiat)
    assert any(row["shock_bp"] == "s_star" for row in fiat)
    assert {row["state_id"] for row in spectrum} == {
        "textbook_limit_fiat_state",
        "calibrated_US_2026_default",
        "hypothetical_ratio_one_illustration",
    }
    assert {
        row["caption_note"]
        for rows in result.tables.values()
        for row in rows
    } == {SLR_CAPTION_NOTE}

    paths = write_slr_conditions_outputs(result, tmp_path / "written")
    assert paths["out_slr_conditions_grid"].exists()
    with paths["out_slr_conditions_grid"].open(encoding="utf-8", newline="") as handle:
        written = list(csv.DictReader(handle))
    assert len(written) == len(grid)


def test_hysteresis_redo_cleanup_only_removes_top_level_stale_csvs(tmp_path: Path) -> None:
    root = tmp_path / "hysteresis_redo"
    nested = root / "measurements"
    nested.mkdir(parents=True)
    stale = root / "out_response_curve.csv"
    keep = nested / "out_response_curve.csv"
    stale.write_text("a\n1\n", encoding="utf-8")
    keep.write_text("a\n1\n", encoding="utf-8")

    removed = cleanup_stale_hysteresis_redo_artifacts(root)

    assert removed == [stale]
    assert not stale.exists()
    assert keep.exists()
