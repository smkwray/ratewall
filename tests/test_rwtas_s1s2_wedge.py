from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ratewall.rwtas.scenarios import (
    HOLDER_COMPOSITION_SCENARIOS,
    ISSUANCE_MIX_SCENARIOS,
    RSTAR_STRESS_SWEEP_SHOCKS,
    build_financialization_grid,
    build_holder_composition_scenarios,
    build_issuance_mix_scenarios,
    build_rstar_wedge_rows,
    write_holder_composition_outputs,
    write_issuance_mix_outputs,
    write_rstar_wedge,
)


PACK_DIR = Path("configs/rwtas/packs")


def test_s1_issuance_mix_scenarios_emit_headline_path_and_comparison(tmp_path: Path) -> None:
    results = build_issuance_mix_scenarios(PACK_DIR)

    assert set(results) == {"base", *ISSUANCE_MIX_SCENARIOS}
    comparison = results["base"].rows("out_s1_comparison_vs_base")
    assert {row["scenario"] for row in comparison} == set(ISSUANCE_MIX_SCENARIOS)
    assert {row["horizon"] for row in comparison} == {
        "year_1",
        "year_5",
        "cumulative_120_month",
    }
    assert results["S1_bills_heavy"].rows("out_government_interest_delta_path")
    assert results["S1_termed_out"].rows("out_government_interest_delta_path")

    year1 = [
        row
        for row in comparison
        if row["scenario"] == "S1_bills_heavy" and row["horizon"] == "year_1"
    ][0]
    assert year1["direction_check"] == "as_expected"

    paths = write_issuance_mix_outputs(results, tmp_path)
    assert Path(paths["out_s1_comparison_vs_base"]).exists()
    assert Path(paths["S1_bills_heavy"]["out_ratewall_rollup"]).exists()


def test_s2_holder_composition_scenarios_emit_disposition_and_closed_counterparts(tmp_path: Path) -> None:
    results = build_holder_composition_scenarios(PACK_DIR)

    assert set(results) == {"base", *HOLDER_COMPOSITION_SCENARIOS}
    shifts = results["base"].rows("out_s2_disposition_shifts_vs_base")
    assert {row["scenario"] for row in shifts} == set(HOLDER_COMPOSITION_SCENARIOS)
    assert Decimal(
        [row for row in shifts if row["scenario"] == "S2_banks_absorb"][0][
            "delta_leak_share_vs_base"
        ]
    ) < 0
    assert Decimal(
        [row for row in shifts if row["scenario"] == "S2_row_returns"][0][
            "delta_leak_share_vs_base"
        ]
    ) > 0

    for scenario_id in HOLDER_COMPOSITION_SCENARIOS:
        closure = results[scenario_id].rows("out_s2_balance_sheet_closure")
        assert closure
        assert {row["status"] for row in closure} == {"pass"}
        assert all(row["funding_note"] for row in closure)

    paths = write_holder_composition_outputs(results, tmp_path)
    assert Path(paths["out_s2_disposition_shifts_vs_base"]).exists()
    assert Path(paths["S2_banks_absorb"]["out_treasury_interest_disposition"]).exists()


def test_rstar_wedge_rows_cover_built_families_and_base_check_against(tmp_path: Path) -> None:
    issuance = build_issuance_mix_scenarios(PACK_DIR)
    holders = build_holder_composition_scenarios(PACK_DIR)
    financialization = build_financialization_grid(PACK_DIR)
    rows = build_rstar_wedge_rows(
        base_result=issuance["base"],
        financialization_results=financialization,
        issuance_results=issuance,
        holder_results=holders,
    )

    year1 = [row for row in rows if row["year_index"] == "1"]
    assert any(row["scenario_family"] == "base" and row["scenario_id"] == "base" for row in year1)
    assert set(ISSUANCE_MIX_SCENARIOS) <= {row["scenario_id"] for row in year1}
    assert set(HOLDER_COMPOSITION_SCENARIOS) <= {row["scenario_id"] for row in year1}
    assert {f"distress_static_{shock}bp" for shock in RSTAR_STRESS_SWEEP_SHOCKS} <= {
        row["scenario_id"] for row in year1
    }

    base = [
        row
        for row in year1
        if row["scenario_family"] == "base" and row["scenario_id"] == "base"
    ][0]
    assert (
                abs(
                    Decimal(base["wedge_per_100bp_stance_bp"])
                    - Decimal("5.053007485881559214151797833")
                )
            < Decimal("0.0001")
        )
    assert Decimal(base["wedge_bp_year"]) == Decimal(base["wedge_per_100bp_stance_bp"])

    path = write_rstar_wedge(rows, tmp_path)
    assert path.exists()
