from __future__ import annotations

import csv
import shutil
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pytest

from ratewall.rwtam.derived_metrics import build_derived_metrics


SOURCE_DIR = Path("var/rwtam/v1")
pytestmark = pytest.mark.audit_fast


@lru_cache(maxsize=1)
def _metrics_result():
    return build_derived_metrics(SOURCE_DIR)


def _read(name: str) -> list[dict[str, str]]:
    with (SOURCE_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_derived_metrics_attenuation_is_exact_source_arithmetic() -> None:
    result = _metrics_result()
    rollup = _read("out_ratewall_rollup.csv")
    rows = result.rows("out_attenuation_multiplier")

    base_year = next(row for row in rows if row["horizon"] == "year_1" and row["band"] == "base")
    assert Decimal(base_year["attenuation_multiplier"]).quantize(Decimal("0.0001")) == Decimal("1.0527")
    for row in rows:
        source = next(
            item
            for item in rollup
            if item["period_type"] == row["source_period_type"]
            and item["period"] == row["source_period"]
            and item["band"] == row["band"]
            and item["ricardian_offset"] == "0"
            and item["dose_mode"] == "persistent_level"
        )
        assert row["source_RW_ratio"] == source["RW_ratio"]
        assert Decimal(row["attenuation_multiplier"]) == Decimal("1") / (
            Decimal("1") - Decimal(source["RW_ratio"])
        )


def test_wall_incidence_regroups_ledger_and_sums_to_rollup_n() -> None:
    result = _metrics_result()
    ledger = _read("out_cashflow_leg_gross.csv")
    rollup = _read("out_ratewall_rollup.csv")
    incidence = result.rows("out_wall_incidence_by_receiving_group")

    identity = next(
        row
        for row in incidence
        if row["row_role"] == "identity" and row["horizon"] == "year_1" and row["band"] == "base"
    )
    source_n = next(
        row
        for row in rollup
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
        and row["dose_mode"] == "persistent_level"
    )["N_bil"]
    positive_converted = sum(
        Decimal(row["converted_effect_bil"])
        for row in ledger
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
        and row["dose_mode"] == "persistent_level"
        and Decimal(row["converted_effect_bil"]) > 0
    )

    assert Decimal(identity["demand_converted_N_bil"]) == positive_converted
    assert Decimal(identity["demand_converted_N_bil"]) == Decimal(source_n)
    assert Decimal(identity["demand_converted_share_of_ledger_N"]) == Decimal("1")
    groups = {
        row["receiving_group"]
        for row in incidence
        if row["row_role"] == "group" and row["horizon"] == "year_1" and row["band"] == "base"
    }
    assert groups == {
        "constrained_borrowers",
        "middle",
        "retirees",
        "unconstrained_savers",
        "firms",
        "state_local",
        "RoW_leaked",
        "no_conversion",
    }


def test_fiscal_cost_ratio_uses_public_interest_rows_and_is_labeled() -> None:
    result = _metrics_result()
    public_rows = _read("out_government_interest_channel.csv")
    rollup = _read("out_ratewall_rollup.csv")
    fiscal = result.rows("out_fiscal_cost_per_unit_compression")

    for row in fiscal:
        if row["horizon"] == "year_1":
            years = {"2026"}
            rollup_key = ("annual", "2026")
        else:
            years = {str(year) for year in range(2026, 2036)}
            rollup_key = ("cumulative_120_month", "2026-2035")
        expense = sum(Decimal(item["cashflow_delta_bil"]) for item in public_rows if item["year"] in years)
        source = next(
            item
            for item in rollup
            if item["period_type"] == rollup_key[0]
            and item["period"] == rollup_key[1]
            and item["band"] == "base"
            and item["ricardian_offset"] == "0"
            and item["dose_mode"] == "persistent_level"
        )
        compression = Decimal(source["D_bil"]) - Decimal(source["N_bil"])
        assert Decimal(row["public_interest_expense_bil"]) == expense
        assert Decimal(row["net_demand_compression_bil"]) == compression
        assert Decimal(row["fiscal_cost_per_unit_compression"]) == expense / compression
        assert row["interpretation_label"] == "diagnostic_ratio_not_welfare_claim"


def test_timing_profile_surfaces_monthly_rows_without_rebuild() -> None:
    result = _metrics_result()
    monthly = _read("out_ratewall_monthly.csv")
    timing = result.rows("out_timing_profile")
    base_timing = [row for row in timing if row["band"] == "base"]
    source_base = [
        row
        for row in monthly
        if row["period_type"] == "monthly"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
        and row["dose_mode"] == "persistent_level"
    ]

    assert len(base_timing) == len(source_base)
    assert [row["RW_ratio"] for row in base_timing] == [row["RW_ratio"] for row in source_base]
    max_source = max(source_base, key=lambda row: Decimal(row["RW_ratio"]))
    assert {row["max_RW_month"] for row in base_timing} == {max_source["period"]}
    assert {row["rw_ratio_degenerate"] for row in base_timing} == {"source_column_absent"}


def test_derived_metrics_fail_closed_when_source_csv_missing(tmp_path: Path) -> None:
    source = tmp_path / "v1"
    shutil.copytree(SOURCE_DIR, source)
    (source / "out_ratewall_rollup.csv").unlink()

    result = build_derived_metrics(source)
    status = result.rows("out_metric_source_status")
    checks = result.rows("out_derived_metrics_invariant_check")

    assert status[0]["source_id"] == "metric_source_missing"
    assert status[0]["status"] == "fail"
    assert "no_recompute_attempted" in status[0]["message"]
    assert checks == [
        {
            "check_id": "DM0_required_sources_present",
            "status": "fail",
            "message": str(source / "out_ratewall_rollup.csv"),
        }
    ]
