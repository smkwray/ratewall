from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.reissuance_policy import (
    REISSUANCE_POLICY_SCENARIOS,
    build_reissuance_policy_scenarios,
    write_reissuance_policy_outputs,
)
from ratewall.rwtam.v1 import build_v1


PACK_DIR = Path("configs/rwtam/packs")


def test_reissuance_policy_base_byte_reproduces_current_default_headline() -> None:
    results = build_reissuance_policy_scenarios(PACK_DIR)
    default = build_v1(PACK_DIR)

    assert results["base"].rows("out_ratewall_rollup") == default.rows("out_ratewall_rollup")
    gate = {
        row["check_id"]: row["status"]
        for row in results["base"].rows("out_reissuance_invariant_check")
    }
    assert gate["RP3_base_headline_byte_regression"] == "pass"


def test_reissuance_policy_composition_conserves_stock_and_pair_policy() -> None:
    results = build_reissuance_policy_scenarios(PACK_DIR)

    assert set(results) == set(REISSUANCE_POLICY_SCENARIOS)
    for scenario_id, result in results.items():
        checks = {
            row["check_id"]: row["status"]
            for row in result.rows("out_reissuance_invariant_check")
        }
        assert checks["RP1_composition_conservation"] == "pass", scenario_id
        assert checks["RP2_same_policy_within_pair"] == "pass", scenario_id
        assert checks["RP4_scenario_isolation"] == "pass", scenario_id

        composition = result.rows("out_reissuance_composition_path")
        assert len(composition) == 10
        assert all(abs(Decimal(row["conservation_gap_bil"])) <= Decimal("0.000001") for row in composition)
        assert all("active_bill_runoff_share" in row for row in composition)
        if scenario_id != "base":
            assert {row["policy_bill_share"] for row in composition} == {
                result.rows("out_reissuance_policy_config")[0]["policy_bill_share"]
            }


def test_reissuance_policy_scenarios_move_stock_composition_and_interest_response(tmp_path: Path) -> None:
    results = build_reissuance_policy_scenarios(PACK_DIR)
    bill_heavy = results["bill_heavy"].rows("out_reissuance_composition_path")
    coupon_heavy = results["coupon_heavy"].rows("out_reissuance_composition_path")

    bill_y10 = next(row for row in bill_heavy if row["year"] == "2035")
    coupon_y10 = next(row for row in coupon_heavy if row["year"] == "2035")
    base_y10 = next(row for row in results["base"].rows("out_reissuance_composition_path") if row["year"] == "2035")
    base_y1 = next(row for row in results["base"].rows("out_reissuance_composition_path") if row["year"] == "2026")
    assert abs(Decimal(base_y10["bill_share_end"]) - Decimal(base_y1["bill_share_start"])) < Decimal("0.02")
    assert Decimal(bill_y10["policy_bill_share"]) == Decimal("0.45")
    assert Decimal(bill_y10["bill_share_end"]) > Decimal(base_y10["bill_share_end"])
    assert Decimal(coupon_y10["bill_share_end"]) < Decimal(base_y10["bill_share_end"])

    divergence = results["base"].rows("out_reissuance_divergence_vs_base")
    year10_bill = next(
        row for row in divergence if row["scenario"] == "bill_heavy" and row["horizon"] == "year_10"
    )
    year10_coupon = next(
        row for row in divergence if row["scenario"] == "coupon_heavy" and row["horizon"] == "year_10"
    )
    assert Decimal(year10_bill["delta_government_interest_bil_vs_base"]) > 0
    assert Decimal(year10_coupon["delta_government_interest_bil_vs_base"]) < 0

    paths = write_reissuance_policy_outputs(results, tmp_path)
    assert Path(paths["out_reissuance_divergence_vs_base"]).exists()
    assert Path(paths["bill_heavy"]["out_reissuance_composition_path"]).exists()
