from __future__ import annotations

from pathlib import Path

import pytest

from ratewall.rwtam.slr_conditions import (
    SLR_TDC_BETA_SELECTOR_SUSPENSION,
    build_slr_conditions_experiment,
    cleanup_stale_hysteresis_redo_artifacts,
)


PACK_DIR = Path("configs/rwtam/packs")


def test_slr_conditions_grid_fails_closed_before_tdc_beta_selector(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="unrepaired state-conditioned TDC beta selector"):
        build_slr_conditions_experiment(PACK_DIR, full_grid=False, output_root=tmp_path)

    assert SLR_TDC_BETA_SELECTOR_SUSPENSION.startswith("slr_conditions is suspended")
    assert not list(tmp_path.iterdir())


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
