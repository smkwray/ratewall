from __future__ import annotations

from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtam.levy_scenarios import (
    build_levy_scenarios,
    write_levy_scenario_outputs,
)
from ratewall.rwtam.reissuance_policy import build_reissuance_policy_scenarios
from ratewall.rwtam.v1 import build_v1


PACK_DIR = Path("configs/rwtam/packs")


def test_levy_l1_bills_only_converges_and_is_measured_above_bill_heavy() -> None:
    reissuance = build_reissuance_policy_scenarios(PACK_DIR)

    convergence = reissuance["bills_only"].rows("out_reissuance_composition_path")
    assert Decimal(convergence[0]["bill_share_start"]) < Decimal(convergence[-1]["bill_share_end"])
    assert Decimal(convergence[-1]["bill_share_end"]) < Decimal("1")
    assert Decimal(convergence[-1]["stock_coupons_end_bil"]) > Decimal("0")

    divergence = reissuance["base"].rows("out_reissuance_divergence_vs_base")
    year10 = {
        row["scenario"]: Decimal(row["RW_ratio"])
        for row in divergence
        if row["horizon"] == "year_10"
        and row["scenario"] in {"coupon_heavy", "bill_heavy", "bills_only"}
    }
    base = next(
        row
        for row in reissuance["base"].rows("out_ratewall_rollup")
        if row["period_type"] == "annual"
        and row["period"] == "2035"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    )
    assert year10["bills_only"] > year10["bill_heavy"] > Decimal(base["RW_ratio"]) > year10["coupon_heavy"]


def test_levy_l2_l3_l4_invariants_and_outputs(tmp_path: Path) -> None:
    result = build_levy_scenarios(PACK_DIR)
    checks = {row["check_id"]: row["status"] for row in result.rows("out_levy_invariant_check")}
    assert checks == {
        "L1_base_headline_byte_stable": "pass",
        "L1_bills_only_above_bill_heavy_y10": "pass",
        "L2_guardrail_N_minus_D_negative": "pass",
        "L3_remittance_loop_reconciles": "pass",
        "L4_distribution_ties_to_cashflow_rollup": "pass",
    }

    cycle_summary = [
        row
        for row in result.rows("out_cycle_2022_24_readout")
        if row["row_type"] in {"annual_summary", "cycle_total_2022_24"}
    ]
    assert cycle_summary
    assert all(Decimal(row["model_net_N_minus_D_bil"]) < 0 for row in cycle_summary)

    paths = write_levy_scenario_outputs(result, tmp_path)
    assert paths["out_cycle_2022_24_readout"].exists()
    assert paths["out_distributional_incidence_per_100bp"].exists()


def test_levy_corridor_reconciles_from_admin_legs() -> None:
    result = build_levy_scenarios(PACK_DIR)

    with localcontext() as context:
        context.prec = 200

        for row in result.rows("out_corridor_floor_comparison"):
            corridor_n = (
                Decimal(row["floor_N_bil"])
                + Decimal(row["issuance_loop_delta_N_bil"])
                - Decimal(row["admin_rate_N_removed_bil"])
            )
            corridor_d = (
                Decimal(row["floor_D_bil"])
                + Decimal(row["issuance_loop_delta_D_bil"])
                - Decimal(row["admin_rate_D_removed_bil"])
                + Decimal(row["remittance_loop_D_clawback_bil"])
            )
            assert abs(corridor_n - Decimal(row["corridor_N_bil"])) <= Decimal("0.000001")
            assert abs(corridor_d - Decimal(row["corridor_D_bil"])) <= Decimal("0.000001")
            assert Decimal(row["remittance_loop_D_clawback_bil"]) == Decimal("0")
            assert row["label"] == "scenario_only;operating_regime_comparative_static"
            assert "no_reserve_scarcity_credit_dynamics" in row["caveat"]

        year1 = {
            row["variant_id"]: row
            for row in result.rows("out_corridor_floor_comparison")
            if row["horizon"] == "year_1"
        }
        no_loop = year1["corridor_no_loop_p1_private_counterpart_only"]
        loop = year1["corridor_with_issuance_loop"]
        assert Decimal(loop["corridor_RW_ratio"]) == Decimal("0.04400782876718727187329989384")
        assert Decimal(loop["corridor_delta_share_of_floor_RW"]) == Decimal("0.1212933423845991801121081158")
        assert Decimal(loop["issuance_loop_extra_public_net_bil"]) == -Decimal(loop["fed_net_income_increase_bil"])
        assert Decimal(loop["issuance_loop_delta_N_bil"]) < 0
        assert Decimal(loop["corridor_N_bil"]) < Decimal(no_loop["corridor_N_bil"])
        assert loop["admin_rate_N_removed_bil"] == no_loop["admin_rate_N_removed_bil"]
        assert Decimal(no_loop["corridor_delta_share_of_floor_RW"]) < Decimal(loop["corridor_delta_share_of_floor_RW"]) < Decimal("0.1409")
        assert loop["government_revenue_doctrine"] == (
            "private_counterpart_plus_financing_closure; "
            "intra_government_transfers_zero_direct_demand_weight; "
            "deficit_effects_via_issuance_loop"
        )

        cumulative = next(
            row
            for row in result.rows("out_corridor_floor_comparison")
            if row["horizon"] == "cumulative_120_month"
            and row["variant_id"] == "corridor_with_issuance_loop"
        )
        assert Decimal(cumulative["corridor_RW_ratio"]) == Decimal("0.05292002733310368221450632329")
        assert Decimal(cumulative["corridor_delta_share_of_floor_RW"]) == Decimal("0.1070568947830331904394014999")


def test_levy_distributional_rows_tie_to_default_cashflow_rollup() -> None:
    result = build_levy_scenarios(PACK_DIR)
    default = build_v1(PACK_DIR)
    incidence = [
        row
        for row in result.rows("out_distributional_incidence_per_100bp")
        if row["row_type"] == "incidence"
    ]
    n_total = sum(Decimal(row["demand_conversion_N_bil"]) for row in incidence)
    d_total = sum(Decimal(row["demand_conversion_D_bil"]) for row in incidence)
    rollup = next(
        row
        for row in default.rows("out_cashflow_core_rollup")
        if row["period"] == "2026" and row["band"] == "base" and row["ricardian_offset"] == "0"
    )
    assert n_total == Decimal(rollup["N_bil"])
    assert d_total == Decimal(rollup["D_bil"])
    assert all(abs(Decimal(row["pre_display_plug_N_gap_bil"])) <= Decimal("0.000000000001") for row in incidence)
    assert all(abs(Decimal(row["pre_display_plug_D_gap_bil"])) <= Decimal("0.000000000001") for row in incidence)
    assert all(abs(Decimal(row["distribution_display_plug_N_bil"])) <= Decimal("0.000000000001") for row in incidence)
    assert all(abs(Decimal(row["distribution_display_plug_D_bil"])) <= Decimal("0.000000000001") for row in incidence)
    assert {row["cell_or_sector"] for row in incidence} >= {
        "hh_constrained_net_borrower",
        "hh_middle_owner_illiquid",
        "hh_retiree_fixed_income_saver",
        "hh_unconstrained_saver",
        "firm_bank_dependent_small",
        "firm_market_funded_large",
        "government",
        "banks",
        "foreign",
    }
