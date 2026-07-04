from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.rwtas.fiscal_tilt import (
    build_fiscal_tilt_experiment,
    export_fiscal_tilt_state_pack,
    run_fiscal_tilt_records,
    write_fiscal_tilt_outputs,
)
from ratewall.rwtas.v1 import _opening_by_family, _read_csv_rows, build_v1


PACK_DIR = Path("configs/rwtas/packs")


@pytest.fixture(scope="module")
def fiscal_tilt_result(tmp_path_factory: pytest.TempPathFactory):
    return build_fiscal_tilt_experiment(
        PACK_DIR,
        output_root=tmp_path_factory.mktemp("rwtas_fiscal_tilt"),
    )


def test_fiscal_tilt_default_off_reproduces_default_rollup_byte_exact() -> None:
    expected = build_v1(PACK_DIR, include_impulse_beta_comparator=False).rows("out_ratewall_rollup")
    actual = build_v1(
        PACK_DIR,
        include_impulse_beta_comparator=False,
        fiscal_tilt_config={"enabled": False},
    ).rows("out_ratewall_rollup")

    assert actual == expected


def test_fiscal_tilt_on_moves_existing_migrated_stock_state(tmp_path: Path) -> None:
    run = run_fiscal_tilt_records(
        PACK_DIR,
        deficit_path="cbo_plus_50pct",
        deficit_multiplier=Decimal("1.5"),
        tilt_enabled=True,
        enabled_mechanisms=frozenset({"migration", "beta"}),
    )
    state_120 = next(row for row in run.state_rows if row["month_index"] == "120")

    assert Decimal(state_120["migrated_stock_bil"]) > 0
    assert Decimal(state_120["tilt_flow_cumulative_bil"]) == Decimal(state_120["migrated_stock_bil"])

    exported = export_fiscal_tilt_state_pack(run, 120, tmp_path / "pack")
    original = _opening_by_family({"opening_stocks": _read_csv_rows(PACK_DIR / "opening_stocks.csv")})
    shifted = _opening_by_family({"opening_stocks": _read_csv_rows(exported / "opening_stocks.csv")})

    assert shifted["deposits_checkable"] < original["deposits_checkable"]
    assert shifted["mmf_shares"] > original["mmf_shares"]


def test_fiscal_tilt_grid_emits_2x2_and_ablation_residual(fiscal_tilt_result, tmp_path: Path) -> None:
    rows = fiscal_tilt_result.rows("out_fiscal_tilt_grid")
    ablations = fiscal_tilt_result.rows("out_fiscal_tilt_ablation")
    checks = {
        row["check_id"]: row["status"]
        for row in fiscal_tilt_result.rows("out_fiscal_tilt_invariant_check")
    }

    assert len(rows) == 2 * 2 * 2
    assert {row["deficit_path"] for row in rows} == {"cbo_base", "cbo_plus_50pct"}
    assert {row["fiscal_tilt"] for row in rows} == {"off", "on"}
    assert {row["remeasure_month_index"] for row in rows} == {"60", "120"}
    assert len(ablations) == 2 * 2
    assert all(row["ablation_additivity_assumed"] == "false" for row in ablations)
    for row in ablations:
        assert Decimal(row["tilt_on_delta_RW_vs_tilt_off"]) == (
            Decimal(row["direct_migration_yield_delta_RW"])
            + Decimal(row["competition_beta_uplift_delta_RW"])
            + Decimal(row["interaction_residual_delta_RW"])
        )
        assert Decimal(row["direct_migration_yield_delta_RW"]) < 0
        assert Decimal(row["competition_beta_uplift_delta_RW"]) > 0
    assert any(Decimal(row["interaction_residual_delta_RW"]) != 0 for row in ablations)
    assert set(checks.values()) == {"pass"}

    paths = write_fiscal_tilt_outputs(fiscal_tilt_result, tmp_path)
    assert paths["out_fiscal_tilt_grid"].exists()
    assert paths["out_fiscal_tilt_state_path"].exists()
