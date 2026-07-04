from __future__ import annotations

import csv
import zipfile
from decimal import Decimal
from pathlib import Path

from ratewall.databook.historical_provisional_estimate import (
    HISTORICAL_DENOMINATOR_CONVENTION_FIELDS,
    HISTORICAL_OVERLAP_GATE_FIELDS,
    HISTORICAL_PUBLIC_INTEREST_NET_BLOCK_FIELDS,
    HISTORICAL_PROVISIONAL_AUDIT_FIELDS,
    HISTORICAL_PROVISIONAL_DENOMINATOR_FIELDS,
    HISTORICAL_PROVISIONAL_GATE_FIELDS,
    HISTORICAL_PROVISIONAL_NUMERATOR_FIELDS,
    HISTORICAL_PROVISIONAL_RW_FIELDS,
    HISTORICAL_ROOT_PUBLIC_INTEREST_RW_FIELDS,
    historical_denominator_convention_rows,
    historical_overlap_gate_rows,
    historical_public_interest_net_block_rows,
    historical_provisional_audit_rows,
    historical_provisional_denominator_rows,
    historical_provisional_gate_rows,
    historical_provisional_numerator_rows,
    historical_provisional_rw_rows,
    historical_root_public_interest_rw_rows,
    write_historical_provisional_estimate_outputs,
)


def test_historical_provisional_estimate_builds_nonfinal_panel(
    tmp_path: Path,
) -> None:
    historical_dir = _write_historical_fixture(tmp_path)
    cbo_zip = _write_cbo_zip(tmp_path)
    fred_dir = _write_fred_fixture(tmp_path)
    cbo_revenue = _write_cbo_revenue_fixture(tmp_path)

    denominator_rows = historical_provisional_denominator_rows(
        historical_comparable_dir=historical_dir,
        cbo_historical_economic_zip=cbo_zip,
    )
    public_interest_rows = historical_public_interest_net_block_rows(
        historical_comparable_dir=historical_dir,
        denominator_rows=denominator_rows,
        fred_source_dir=fred_dir,
        cbo_revenue_path=cbo_revenue,
    )
    root_public_interest_rows = historical_root_public_interest_rw_rows(
        cbo_historical_economic_zip=cbo_zip,
        fred_source_dir=fred_dir,
        historical_public_interest_rows=public_interest_rows,
    )
    denominator_convention_rows = historical_denominator_convention_rows(
        denominator_rows=denominator_rows,
    )
    numerator_rows = historical_provisional_numerator_rows(
        historical_comparable_dir=historical_dir,
        historical_public_interest_rows=public_interest_rows,
    )
    overlap_gate_rows = historical_overlap_gate_rows(
        public_interest_rows=public_interest_rows,
        numerator_rows=numerator_rows,
    )
    rw_rows = historical_provisional_rw_rows(
        denominator_rows=denominator_rows,
        numerator_rows=numerator_rows,
    )
    gate_rows = historical_provisional_gate_rows(
        denominator_rows=denominator_rows,
        numerator_rows=numerator_rows,
        public_interest_rows=public_interest_rows,
        denominator_convention_rows=denominator_convention_rows,
        overlap_gate_rows=overlap_gate_rows,
    )
    audit_rows = historical_provisional_audit_rows(
        denominator_rows=denominator_rows,
        numerator_rows=numerator_rows,
        rw_rows=rw_rows,
        gate_rows=gate_rows,
        public_interest_rows=public_interest_rows,
        denominator_convention_rows=denominator_convention_rows,
        overlap_gate_rows=overlap_gate_rows,
    )

    assert {field for row in denominator_rows for field in row} == set(
        HISTORICAL_PROVISIONAL_DENOMINATOR_FIELDS
    )
    assert {field for row in numerator_rows for field in row} == set(
        HISTORICAL_PROVISIONAL_NUMERATOR_FIELDS
    )
    assert {field for row in public_interest_rows for field in row} == set(
        HISTORICAL_PUBLIC_INTEREST_NET_BLOCK_FIELDS
    )
    assert {field for row in root_public_interest_rows for field in row} == set(
        HISTORICAL_ROOT_PUBLIC_INTEREST_RW_FIELDS
    )
    assert {field for row in denominator_convention_rows for field in row} == set(
        HISTORICAL_DENOMINATOR_CONVENTION_FIELDS
    )
    assert {field for row in overlap_gate_rows for field in row} == set(
        HISTORICAL_OVERLAP_GATE_FIELDS
    )
    assert {field for row in rw_rows for field in row} == set(
        HISTORICAL_PROVISIONAL_RW_FIELDS
    )
    assert {field for row in gate_rows for field in row} == set(
        HISTORICAL_PROVISIONAL_GATE_FIELDS
    )
    assert {field for row in audit_rows for field in row} == set(
        HISTORICAL_PROVISIONAL_AUDIT_FIELDS
    )
    assert denominator_rows[0]["historical_path_D_bil"] == "97"
    assert denominator_rows[0]["fixed_D_comparison_bil"] == "194"
    assert numerator_rows[0]["forecast_backfill_used"] == "false"
    assert public_interest_rows[0]["forecast_backfill_used"] == "false"
    assert public_interest_rows[0]["on_rrp_source_status"] == (
        "source_backed_fred_quarter_average"
    )
    assert public_interest_rows[0]["reserve_balance_stock_source_status"] == (
        "source_backed_fred_quarter_average"
    )
    assert public_interest_rows[0]["iorb_source_status"] == (
        "source_backed_rate_and_reserve_stock_quarter_average"
    )
    assert public_interest_rows[0]["bank_treasury_route_source_status"] == (
        "source_backed_z1_bank_treasury_split"
    )
    assert public_interest_rows[0]["source_direct_treasury_interest_support_bil"] == "5"
    assert public_interest_rows[0]["historical_current_remittance_state_bil"] == "-100"
    assert (
        public_interest_rows[0]["historical_current_remittance_demand_offset_bil"]
        == "0"
    )
    assert public_interest_rows[0]["remittance_source_status"] == (
        "source_backed_h41_deferred_asset_context_zero_support"
    )
    assert (
        Decimal(public_interest_rows[0]["direct_treasury_interest_support_bil"])
        + Decimal(public_interest_rows[0]["bank_treasury_interest_support_bil"])
        == Decimal("5")
    )
    root_base = next(
        row for row in root_public_interest_rows if row["assumption_case"] == "base"
    )
    assert root_base["series_role"] == "historical_root_public_interest_context"
    assert root_base["selected_historical_n_includes_tdc"] == "false"
    assert root_base["final_classifier_allowed"] == "false"
    assert root_base["source_direct_treasury_interest_basis_bil"] == "5"
    assert root_base["direct_treasury_interest_support_bil"] == "5"
    assert (
        Decimal(root_base["bank_treasury_interest_support_bil"])
        + Decimal(root_base["nonbank_treasury_interest_support_bil"])
        == Decimal(root_base["direct_treasury_interest_support_bil"])
    )
    assert Decimal(root_base["root_public_interest_n_bil"]) < Decimal("10")
    assert "tdc_ex_overlap_support_bil" not in root_base
    assert denominator_convention_rows[0]["forecast_moving_D_reused"] == "false"
    assert Decimal(numerator_rows[0]["provisional_observed_component_sum_bil"]) > Decimal(
        "10"
    )
    assert Decimal(rw_rows[0]["provisional_historical_ratewall_ratio"]) == (
        Decimal(numerator_rows[0]["provisional_observed_component_sum_bil"])
        / Decimal("97")
    )
    assert {row["final_classifier_allowed"] for row in rw_rows} == {"false"}
    assert {
        row["gate_status"]
        for row in gate_rows
        if row["check_id"]
        in {
            "final_classifier",
            "iorb_reserve_stock",
            "bank_treasury_route",
            "remittance_on_rrp",
            "overlap",
        }
    } == {"closed_nonclassifier", "pass"}
    final_gate = next(row for row in gate_rows if row["check_id"] == "final_classifier")
    assert final_gate["evidence_summary"].startswith("R37 resolved")
    by_overlap = {row["check_id"]: row for row in overlap_gate_rows}
    assert by_overlap["bank_route_nonadditive_split"]["gate_status"] == "pass"
    assert by_overlap["fed_liability_interest_sources"]["gate_status"] == "pass"
    assert by_overlap["remittance_timing_overlap"]["gate_status"] == "pass"
    assert by_overlap["remittance_timing_overlap"]["final_classifier_effect"] == (
        "no_final_blocker"
    )
    assert {row["check_status"] for row in audit_rows} == {"pass"}

    outputs = write_historical_provisional_estimate_outputs(
        tmp_path / "out",
        denominator_rows=denominator_rows,
        public_interest_rows=public_interest_rows,
        root_public_interest_rw_rows=root_public_interest_rows,
        denominator_convention_rows=denominator_convention_rows,
        overlap_gate_rows=overlap_gate_rows,
        numerator_rows=numerator_rows,
        rw_rows=rw_rows,
        gate_rows=gate_rows,
        audit_rows=audit_rows,
    )
    assert outputs["rw_csv"].read_text(encoding="utf-8").startswith(
        "historical_provisional_rw_row_id,"
    )
    assert outputs["public_interest_csv"].read_text(encoding="utf-8").startswith(
        "historical_public_interest_net_block_row_id,"
    )
    assert outputs["root_public_interest_rw_csv"].read_text(
        encoding="utf-8"
    ).startswith("historical_root_public_interest_rw_row_id,")
    assert outputs["denominator_convention_csv"].read_text(encoding="utf-8").startswith(
        "historical_denominator_convention_row_id,"
    )
    assert outputs["overlap_gate_csv"].read_text(encoding="utf-8").startswith(
        "historical_overlap_gate_row_id,"
    )


def test_historical_remittance_uses_h41_not_positive_cbo_forecast(
    tmp_path: Path,
) -> None:
    historical_dir = _write_historical_fixture(tmp_path)
    cbo_zip = _write_cbo_zip(tmp_path)
    fred_dir = _write_fred_fixture(tmp_path)
    cbo_revenue = _write_cbo_revenue_fixture(tmp_path, value="9999")

    denominator_rows = historical_provisional_denominator_rows(
        historical_comparable_dir=historical_dir,
        cbo_historical_economic_zip=cbo_zip,
    )
    public_interest_rows = historical_public_interest_net_block_rows(
        historical_comparable_dir=historical_dir,
        denominator_rows=denominator_rows,
        fred_source_dir=fred_dir,
        cbo_revenue_path=cbo_revenue,
    )

    row = public_interest_rows[0]
    assert row["historical_current_remittance_state_bil"] == "-100"
    assert row["historical_current_remittance_demand_offset_bil"] == "0"
    assert row["remittance_source_status"] == (
        "source_backed_h41_deferred_asset_context_zero_support"
    )


def test_positive_h41_remittance_is_context_not_numerator_support(
    tmp_path: Path,
) -> None:
    historical_dir = _write_historical_fixture(tmp_path)
    cbo_zip = _write_cbo_zip(tmp_path)
    fred_dir = _write_fred_fixture(tmp_path, h41_remittance="100000")
    cbo_revenue = _write_cbo_revenue_fixture(tmp_path)

    denominator_rows = historical_provisional_denominator_rows(
        historical_comparable_dir=historical_dir,
        cbo_historical_economic_zip=cbo_zip,
    )
    public_interest_rows = historical_public_interest_net_block_rows(
        historical_comparable_dir=historical_dir,
        denominator_rows=denominator_rows,
        fred_source_dir=fred_dir,
        cbo_revenue_path=cbo_revenue,
    )

    row = public_interest_rows[0]
    assert row["historical_current_remittance_state_bil"] == "100"
    assert row["historical_current_remittance_demand_offset_bil"] == "0"
    assert row["remittance_source_status"] == (
        "source_backed_h41_positive_weekly_remittance_due_context_not_support"
    )


def test_missing_h41_remittance_source_blocks_remittance_gate(
    tmp_path: Path,
) -> None:
    historical_dir = _write_historical_fixture(tmp_path)
    cbo_zip = _write_cbo_zip(tmp_path)
    fred_dir = _write_fred_fixture(tmp_path, include_h41=False)
    cbo_revenue = _write_cbo_revenue_fixture(tmp_path)

    denominator_rows = historical_provisional_denominator_rows(
        historical_comparable_dir=historical_dir,
        cbo_historical_economic_zip=cbo_zip,
    )
    public_interest_rows = historical_public_interest_net_block_rows(
        historical_comparable_dir=historical_dir,
        denominator_rows=denominator_rows,
        fred_source_dir=fred_dir,
        cbo_revenue_path=cbo_revenue,
    )
    numerator_rows = historical_provisional_numerator_rows(
        historical_comparable_dir=historical_dir,
        historical_public_interest_rows=public_interest_rows,
    )
    overlap_rows = historical_overlap_gate_rows(
        public_interest_rows=public_interest_rows,
        numerator_rows=numerator_rows,
    )
    gate_rows = historical_provisional_gate_rows(
        denominator_rows=denominator_rows,
        numerator_rows=numerator_rows,
        public_interest_rows=public_interest_rows,
        denominator_convention_rows=historical_denominator_convention_rows(
            denominator_rows=denominator_rows
        ),
        overlap_gate_rows=overlap_rows,
    )

    assert public_interest_rows[0]["remittance_source_status"] == (
        "missing_h41_remittance_state_source"
    )
    by_gate = {row["check_id"]: row for row in gate_rows}
    assert by_gate["remittance_on_rrp"]["gate_status"] == "blocked_unproven"
    assert by_gate["overlap"]["gate_status"] == "blocked_unproven"


def _write_historical_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "historical"
    root.mkdir()
    _write_csv(
        root / "ratewall_historical_comparable_surface.csv",
        [
            _historical_component(
                "tdc_ex_overlap_current_demand_support",
                "tdc_ex_overlap_support",
                "10",
            ),
            _historical_component(
                "direct_treasury_interest_support",
                "public_interest_net_block",
                "5",
            ),
        ],
    )
    return root


def _historical_component(
    channel_id: str, family: str, value: str
) -> dict[str, str]:
    return {
        "historical_comparable_surface_row_id": (
            f"historical_comparable_surface::2024Q1::base::{channel_id}"
        ),
        "historical_period_id": "2024Q1",
        "period": "2024Q1",
        "quarter": "2024Q1",
        "assumption_case": "base",
        "ratio_object_id": "rw_historical_wall_ratio_path",
        "channel_id": channel_id,
        "shared_channel_family": family,
        "historical_numerator_value_bil": value,
        "historical_denominator_variant": "historical_path_denominator_v1_required",
        "historical_path_D_bil": "",
        "fixed_D_comparison_bil": "",
        "historical_rate_gap_pct_points": "",
        "historical_ratio": "",
        "historical_ratio_not_classifier": "true",
        "source_status": "source_backed_fixture",
        "adapter_status": "source_backed_component_context_not_classifier",
        "source_historical_row_id": "fixture",
        "allowed_use": "historical_component_comparison_context_only",
        "blocked_use": "historical_classifier",
        "claim_boundary": "fixture",
    }


def _write_cbo_zip(tmp_path: Path) -> Path:
    path = tmp_path / "cbo.zip"
    rows = [
        {
            "date": "2024q1",
            "gdp": "25000",
            "treasury_bill_rate_3mo": "4.8",
            "fed_funds_rate": "0.5",
            "treasury_note_rate_10yr": "4.1",
        }
    ]
    csv_text = _csv_text(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Quarterly_February2026.csv", csv_text)
    return path


def _write_fred_fixture(
    tmp_path: Path,
    *,
    h41_remittance: str = "-100000",
    include_h41: bool = True,
) -> Path:
    root = tmp_path / "fred"
    root.mkdir()
    _write_csv(
        root / "IORB.csv",
        [
            {"observation_date": "2024-01-02", "IORB": "5"},
            {"observation_date": "2024-03-29", "IORB": "5"},
        ],
    )
    _write_csv(
        root / "RRPONTSYD.csv",
        [
            {"observation_date": "2024-01-02", "RRPONTSYD": "1000"},
            {"observation_date": "2024-03-29", "RRPONTSYD": "3000"},
        ],
    )
    _write_csv(
        root / "WRBWFRBL.csv",
        [
            {"observation_date": "2024-01-02", "WRBWFRBL": "1000000"},
            {"observation_date": "2024-03-29", "WRBWFRBL": "1000000"},
        ],
    )
    _write_csv(
        root / "WRESBAL.csv",
        [
            {"observation_date": "2024-01-02", "WRESBAL": "1000000"},
            {"observation_date": "2024-03-29", "WRESBAL": "1000000"},
        ],
    )
    _write_csv(
        root / "NA000309Q.csv",
        [
            {
                "observation_date": "2024-01-01",
                "NA000309Q": "41666.66666666666666666666667",
            },
        ],
    )
    _write_csv(
        root / "RRPONTSYAWARD.csv",
        [
            {"observation_date": "2024-01-02", "RRPONTSYAWARD": "4"},
            {"observation_date": "2024-03-29", "RRPONTSYAWARD": "4"},
        ],
    )
    _write_csv(
        root / "BOGZ1FL763061100Q.csv",
        [
            {"observation_date": "2024-01-01", "BOGZ1FL763061100Q": "1000000"},
        ],
    )
    _write_csv(
        root / "FDHBPIN.csv",
        [
            {"observation_date": "2024-01-01", "FDHBPIN": "10000"},
        ],
    )
    if include_h41:
        _write_csv(
            root / "RESPPLLOPNWW.csv",
            [
                {"observation_date": "2024-01-03", "RESPPLLOPNWW": h41_remittance},
            ],
        )
    return root


def _write_cbo_revenue_fixture(tmp_path: Path, *, value: str = "8") -> Path:
    path = tmp_path / "cbo_revenue.csv"
    _write_csv(
        path,
        [
            {
                "date": "FY2024",
                "variable": "rev_fed_reserve",
                "value": value,
                "estimate_type": "actual",
            }
        ],
    )
    return path


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text(_csv_text(rows), encoding="utf-8")


def _csv_text(rows: list[dict[str, str]]) -> str:
    fields = list(rows[0])
    from io import StringIO

    handle = StringIO()
    writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()
