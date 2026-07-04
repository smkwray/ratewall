from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ratewall.rwtas.scenarios import (
    FINANCIALIZATION_SCENARIO_IDS,
    build_financialization_grid,
    write_financialization_grid_outputs,
)


PACK_DIR = Path("configs/rwtas/packs")


def test_financialization_grid_emits_required_scenarios_and_summary(tmp_path: Path) -> None:
    results = build_financialization_grid(PACK_DIR)
    summary = results["base"].rows("out_financialization_grid")

    assert [row["scenario"] for row in summary] == list(FINANCIALIZATION_SCENARIO_IDS)
    assert all(row["floating_gap_statistic_bil"] for row in summary)
    assert all(row["N_bil"] for row in summary)
    assert all(row["D_full_bil"] for row in summary)
    assert all(row["RW_full"] for row in summary)

    paths = write_financialization_grid_outputs(results, tmp_path)
    assert Path(paths["out_financialization_grid"]).exists()
    assert Path(paths["F-asset-50"]["out_ratewall_rollup"]).exists()


def test_t49_financialization_delta_sets_close_by_sector() -> None:
    results = build_financialization_grid(PACK_DIR)

    for scenario_id, result in results.items():
        scenario_rows = [
            row
            for row in result.rows("out_scenario_delta_balance")
            if row["delta_set_id"].startswith("F-")
        ]
        if scenario_id == "base":
            assert not scenario_rows
            continue
        assert scenario_rows, scenario_id
        assert {row["status"] for row in scenario_rows} == {"pass"}


def test_financialization_scenario_diagnostics_are_isolated_from_headline() -> None:
    results = build_financialization_grid(PACK_DIR)

    for scenario_id, result in results.items():
        diagnostic = result.rows("out_financialization_credit_supply_diagnostic")[0]
        assert diagnostic["headline_entry_flag"] == "false"
        assert diagnostic["include_flag"] == "0"
        assert diagnostic["value_status"] == "diagnostic_only_non_additive"
        if scenario_id.startswith("F-asset"):
            assert Decimal(diagnostic["deposit_shift_bil"]) > 0
            assert Decimal(diagnostic["mmf_like_gross_income_bil"]) > 0


def test_financialization_grid_keeps_monotonicity_as_finding_not_assertion() -> None:
    results = build_financialization_grid(PACK_DIR)
    summary = {row["scenario"]: row for row in results["base"].rows("out_financialization_grid")}

    assert Decimal(summary["F-asset-50"]["RW_full"]) > Decimal(summary["base"]["RW_full"])
    assert Decimal(summary["F-liability-60"]["RW_full"]) < Decimal(summary["base"]["RW_full"])
    assert summary["F-both"]["net_sign_vs_base"] in {"positive", "negative", "zero"}
    assert Decimal(summary["F-wrapper"]["floating_gap_statistic_bil"]) == Decimal(
        summary["base"]["floating_gap_statistic_bil"]
    )
