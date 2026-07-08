from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.rwtam.ai_boom_twin import (
    FISCAL_BRANCHES,
    build_ai_boom_twin,
    export_ai_boom_state_pack,
    run_ai_boom_records,
    write_ai_boom_outputs,
)
from ratewall.rwtam.v1 import _opening_by_family, _read_csv_rows, build_v1


PACK_DIR = Path("configs/rwtam/packs")
DEFAULT_GOLDEN_ROLLUP = Path("tests/fixtures/rwtam/golden_wave8/out_ratewall_rollup.csv")


@pytest.fixture(scope="module")
def ai_boom_result(tmp_path_factory: pytest.TempPathFactory):
    return build_ai_boom_twin(
        PACK_DIR,
        output_root=tmp_path_factory.mktemp("rwtam_ai_boom_twin"),
    )


def test_ai_boom_default_build_stays_byte_stable() -> None:
    expected = _read_csv_rows(DEFAULT_GOLDEN_ROLLUP)
    actual = build_v1(PACK_DIR, include_impulse_beta_comparator=False).rows("out_ratewall_rollup")

    assert actual == expected


def test_ai_boom_growth_and_fiscal_dials_mutate_exported_opening_pack(tmp_path: Path) -> None:
    run = run_ai_boom_records(
        PACK_DIR,
        run_id="probe_full_F_minus",
        rate_environment_bp=Decimal("150"),
        growth_differential_annual=Decimal("0.01"),
        deficit_multiplier=FISCAL_BRANCHES["F_minus"],
    )
    exported = export_ai_boom_state_pack(run, 120, tmp_path / "pack")
    original = _opening_by_family({"opening_stocks": _read_csv_rows(PACK_DIR / "opening_stocks.csv")})
    shifted = _opening_by_family({"opening_stocks": _read_csv_rows(exported / "opening_stocks.csv")})

    assert shifted["treasury_bills"] > original["treasury_bills"]
    assert shifted["treasury_notes_bonds_tips"] > original["treasury_notes_bonds_tips"]
    assert shifted["deposits_savings_mmda"] > original["deposits_savings_mmda"]
    assert shifted["credit_card_revolving"] > original["credit_card_revolving"]


def test_ai_boom_twin_emits_branch_table_and_true_residual(ai_boom_result, tmp_path: Path) -> None:
    golden_before = _sha256(DEFAULT_GOLDEN_ROLLUP)
    rows = ai_boom_result.rows("out_ai_boom_twin")
    checks = {
        row["check_id"]: row["status"]
        for row in ai_boom_result.rows("out_ai_boom_invariant_check")
    }

    assert len(rows) == 2 * 2 * 2
    assert {row["branch_id"] for row in rows} == {"F_plus", "F_minus"}
    assert {row["rate_environment_bp"] for row in rows} == {"150", "250"}
    assert {row["remeasure_month_index"] for row in rows} == {"60", "120"}
    assert all(row["ablation_additivity_assumed"] == "false" for row in rows)
    for row in rows:
        assert Decimal(row["delta_RW_vs_control"]) == (
            Decimal(row["rate_environment_only_delta_RW"])
            + Decimal(row["growth_only_delta_RW"])
            + Decimal(row["fiscal_path_only_delta_RW"])
            + Decimal(row["ablation_residual_delta_RW"])
        )
        if row["branch_id"] == "F_plus":
            assert Decimal(row["fiscal_path_only_delta_RW"]) < 0
        else:
            assert Decimal(row["fiscal_path_only_delta_RW"]) > 0
    assert any(Decimal(row["ablation_residual_delta_RW"]) != 0 for row in rows)
    rate_150 = [row for row in rows if row["rate_environment_bp"] == "150"]
    rate_250 = [row for row in rows if row["rate_environment_bp"] == "250"]
    assert all(row["rate_route_activation_month"] == "" for row in rate_150)
    assert all(row["rate_route_activation_month"] for row in rate_250)
    assert all(Decimal(row["rate_route_peak_migration_flow_bil"]) > 0 for row in rate_250)
    assert any(Decimal(row["rate_environment_only_delta_RW"]) != 0 for row in rate_250)
    assert set(checks.values()) == {"pass"}
    assert "AI1_default_rollup_matches_golden_after_scenario_build" in checks

    paths = write_ai_boom_outputs(ai_boom_result, tmp_path)
    assert paths["out_ai_boom_twin"].exists()
    assert paths["out_ai_boom_state_path"].exists()
    assert paths["out_ai_boom_notes"].exists()
    assert _sha256(DEFAULT_GOLDEN_ROLLUP) == golden_before


def test_ai_boom_branch_dial_probe_only_fiscal_route_changes(ai_boom_result) -> None:
    rows = ai_boom_result.rows("out_ai_boom_twin")
    for rate_bp in {"150", "250"}:
        for month in {"60", "120"}:
            plus = next(row for row in rows if row["branch_id"] == "F_plus" and row["rate_environment_bp"] == rate_bp and row["remeasure_month_index"] == month)
            minus = next(row for row in rows if row["branch_id"] == "F_minus" and row["rate_environment_bp"] == rate_bp and row["remeasure_month_index"] == month)

            assert plus["rate_environment_only_delta_RW"] == minus["rate_environment_only_delta_RW"]
            assert plus["growth_only_delta_RW"] == minus["growth_only_delta_RW"]
            assert plus["fiscal_path_only_delta_RW"] != minus["fiscal_path_only_delta_RW"]


def test_ai_boom_threshold_note_emitted(ai_boom_result) -> None:
    notes = ai_boom_result.rows("out_ai_boom_notes")

    assert any(row["note_id"] == "migration_threshold_dead_zone" for row in notes)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
