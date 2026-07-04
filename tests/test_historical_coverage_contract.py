from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path

import pytest

from ratewall.databook.historical_coverage_contract import (
    HISTORICAL_COVERAGE_CONTRACT_FIELDS,
    HISTORICAL_EXTENSION_FEASIBILITY_FIELDS,
    HISTORICAL_NUMERATOR_PANEL_FIELDS,
    HISTORICAL_TDC_MECHANISM_PANEL_FIELDS,
    HistoricalCoverageContractError,
    historical_coverage_contract_rows,
    historical_extension_feasibility_rows,
    historical_extension_readout_markdown,
    historical_numerator_panel_rows,
    historical_tdc_mechanism_panel_rows,
    validate_historical_coverage_contract,
    validate_historical_numerator_panel,
    validate_historical_tdc_mechanism_panel,
    write_historical_coverage_contract_outputs,
)
from ratewall.databook.historical_tdc_source_registry import (
    HISTORICAL_TDC_SOURCE_REGISTRY_FIELDS,
    historical_tdc_source_registry_rows,
)


def test_historical_source_registry_required_routes(tmp_path: Path) -> None:
    dirs = _write_fixture(tmp_path)

    rows = historical_tdc_source_registry_rows(
        sibling_calibration_dir=dirs["sibling"],
        historical_provisional_dir=dirs["historical"],
    )

    assert {field for row in rows for field in row} == set(
        HISTORICAL_TDC_SOURCE_REGISTRY_FIELDS
    )
    by_route = {row["route_id"]: row for row in rows}
    assert {
        "implemented_short_panel",
        "main_long_history_bank_scope",
        "strict_modern_bank_scope",
        "level_splice_1990_appendix",
    } == set(by_route)
    assert by_route["implemented_short_panel"]["route_status"].startswith("pass")
    assert by_route["strict_modern_bank_scope"]["route_status"].startswith("pass")
    assert by_route["main_long_history_bank_scope"]["fail_closed_label"] == (
        "fail_closed_selected_tdc_column_missing"
    )


def test_historical_coverage_contract_windows_and_nonclassifier(
    tmp_path: Path,
) -> None:
    dirs = _write_fixture(tmp_path)
    source_rows = historical_tdc_source_registry_rows(
        sibling_calibration_dir=dirs["sibling"],
        historical_provisional_dir=dirs["historical"],
    )
    rows = historical_coverage_contract_rows(
        source_registry_rows=source_rows,
        historical_provisional_dir=dirs["historical"],
    )

    assert {field for row in rows for field in row} == set(
        HISTORICAL_COVERAGE_CONTRACT_FIELDS
    )
    by_route = {row["route_id"]: row for row in rows}
    assert by_route["implemented_short_panel"]["coverage_window_start"] == "2021Q4"
    assert by_route["implemented_short_panel"]["coverage_window_end"] == "2026Q2"
    assert by_route["main_long_history_bank_scope"]["coverage_window_start"] == "2002Q1"
    assert by_route["strict_modern_bank_scope"]["coverage_window_start"] == "2022Q1"
    assert by_route["level_splice_1990_appendix"]["coverage_window_start"] == "1990Q1"
    assert all(row["selected_historical_n_includes_tdc"] == "false" for row in rows)
    assert all(row["classifier_allowed"] == "false" for row in rows)
    assert all(row["tdc_centrality"] == "diagnostic_context" for row in rows)
    assert all(row["final_classifier_status"] == "closed_nonclassifier" for row in rows)
    assert all(
        row["historical_n_formula"]
        == "tdc_ex_overlap_support_bil + public_interest_net_block_partial_bil"
        for row in rows
    )


def test_historical_numerator_and_tdc_panels_lock_formula(tmp_path: Path) -> None:
    dirs = _write_fixture(tmp_path)

    numerator = historical_numerator_panel_rows(
        historical_provisional_dir=dirs["historical"]
    )
    tdc = historical_tdc_mechanism_panel_rows(numerator_rows=numerator)

    assert {field for row in numerator for field in row} == set(
        HISTORICAL_NUMERATOR_PANEL_FIELDS
    )
    assert {field for row in tdc for field in row} == set(
        HISTORICAL_TDC_MECHANISM_PANEL_FIELDS
    )
    assert numerator[0]["historical_n_context_bil"] == "11"
    assert numerator[0]["direct_treasury_interest_decomposition_bil"] == "3"
    assert "direct_treasury" not in numerator[0]["historical_n_formula"]
    assert all(row["tdc_centrality"] == "diagnostic_context" for row in tdc)
    assert all(
        row["post_2025q4_tdc_source_update_status"].startswith("blocked")
        for row in tdc
        if row["period"] > "2025Q4"
    )


def test_historical_feasibility_readout_and_outputs(tmp_path: Path) -> None:
    dirs = _write_fixture(tmp_path)
    source_rows = historical_tdc_source_registry_rows(
        sibling_calibration_dir=dirs["sibling"],
        historical_provisional_dir=dirs["historical"],
    )
    coverage = historical_coverage_contract_rows(
        source_registry_rows=source_rows,
        historical_provisional_dir=dirs["historical"],
    )
    feasibility = historical_extension_feasibility_rows(
        coverage_rows=coverage,
        source_registry_rows=source_rows,
    )
    numerator = historical_numerator_panel_rows(
        historical_provisional_dir=dirs["historical"]
    )
    tdc = historical_tdc_mechanism_panel_rows(numerator_rows=numerator)
    readout = historical_extension_readout_markdown(
        coverage_rows=coverage,
        feasibility_rows=feasibility,
    )

    assert {field for row in feasibility for field in row} == set(
        HISTORICAL_EXTENSION_FEASIBILITY_FIELDS
    )
    assert "not a final wall-hit classifier" in readout
    outputs = write_historical_coverage_contract_outputs(
        tmp_path / "out",
        source_registry_rows=source_rows,
        coverage_rows=coverage,
        feasibility_rows=feasibility,
        numerator_panel_rows=numerator,
        tdc_mechanism_panel_rows=tdc,
        readout_markdown=readout,
    )
    assert outputs["coverage_contract_csv"].read_text(encoding="utf-8").startswith(
        "historical_coverage_contract_row_id,"
    )
    assert outputs["tdc_mechanism_panel_csv"].read_text(encoding="utf-8").startswith(
        "historical_tdc_mechanism_panel_row_id,"
    )


def test_bad_fixture_rejects_direct_treasury_double_count(tmp_path: Path) -> None:
    dirs = _write_fixture(tmp_path)
    source_rows = historical_tdc_source_registry_rows(
        sibling_calibration_dir=dirs["sibling"],
        historical_provisional_dir=dirs["historical"],
    )
    rows = historical_coverage_contract_rows(
        source_registry_rows=source_rows,
        historical_provisional_dir=dirs["historical"],
    )
    bad = deepcopy(rows)
    bad[0]["historical_n_formula"] = (
        "tdc_ex_overlap_support_bil + direct_treasury_interest_bil + "
        "public_interest_net_block_partial_bil"
    )

    with pytest.raises(HistoricalCoverageContractError, match="direct Treasury"):
        validate_historical_coverage_contract(bad)


def test_bad_fixture_rejects_classifier_and_selected_tdc(tmp_path: Path) -> None:
    rows = historical_numerator_panel_rows(
        historical_provisional_dir=_write_fixture(tmp_path)["historical"]
    )
    selected_bad = deepcopy(rows)
    selected_bad[0]["selected_historical_n_includes_tdc"] = "true"
    with pytest.raises(HistoricalCoverageContractError, match="selected TDC"):
        validate_historical_numerator_panel(selected_bad)

    classifier_bad = deepcopy(rows)
    classifier_bad[0]["classifier_allowed"] = "true"
    with pytest.raises(HistoricalCoverageContractError, match="classifier"):
        validate_historical_numerator_panel(classifier_bad)


def test_bad_fixture_rejects_post_2025q4_tdc_unbacked(tmp_path: Path) -> None:
    rows = historical_tdc_mechanism_panel_rows(
        numerator_rows=historical_numerator_panel_rows(
            historical_provisional_dir=_write_fixture(tmp_path)["historical"]
        )
    )
    bad = deepcopy(rows)
    row = next(row for row in bad if row["period"] == "2026Q1")
    row["post_2025q4_tdc_source_update_status"] = "pass_unbacked"

    with pytest.raises(HistoricalCoverageContractError, match="post-2025Q4"):
        validate_historical_tdc_mechanism_panel(bad)


def _write_fixture(tmp_path: Path) -> dict[str, Path]:
    sibling = tmp_path / "sibling"
    historical = tmp_path / "historical"
    sibling.mkdir()
    historical.mkdir()
    _write_csv(
        sibling / "tdcest_tdc_estimates.csv",
        [
            {
                "date": "1990-03-31",
                "tdc_tier2_mmf_rrp_prop_bank_only_ru_flow": "",
                "tdc_bank_only_extended_1990": "1",
            },
            {
                "date": "2002-03-31",
                "tdc_tier2_mmf_rrp_prop_bank_only_ru_flow": "1",
                "tdc_bank_only_extended_1990": "1",
            },
            {
                "date": "2022-03-31",
                "tdc_tier2_mmf_rrp_prop_bank_only_ru_flow": "1",
                "tdc_bank_only_extended_1990": "1",
            },
            {
                "date": "2025-12-31",
                "tdc_tier2_mmf_rrp_prop_bank_only_ru_flow": "1",
                "tdc_bank_only_extended_1990": "1",
            },
        ],
    )
    _write_csv(
        sibling / "tdcpass_quarterly_panel.csv",
        [
            {
                "quarter": "1990Q1",
                "tdc_tier2_mmf_rrp_prop_bank_only_qoq": "",
                "tdc_tier2_regression_mmf_rrp_prop_bank_only_qoq": "1",
                "tdc_bank_only_extended_1990_qoq": "1",
            },
            {
                "quarter": "2022Q1",
                "tdc_tier2_mmf_rrp_prop_bank_only_qoq": "1",
                "tdc_tier2_regression_mmf_rrp_prop_bank_only_qoq": "1",
                "tdc_bank_only_extended_1990_qoq": "1",
            },
            {
                "quarter": "2025Q4",
                "tdc_tier2_mmf_rrp_prop_bank_only_qoq": "1",
                "tdc_tier2_regression_mmf_rrp_prop_bank_only_qoq": "1",
                "tdc_bank_only_extended_1990_qoq": "1",
            },
        ],
    )
    _write_csv(
        historical / "ratewall_historical_provisional_numerator_ledger.csv",
        [
            _numerator_row("2021Q4", "10", "1", "3"),
            _numerator_row("2026Q1", "0", "4", "5"),
            _numerator_row("2026Q2", "0", "6", "7"),
        ],
    )
    _write_csv(
        historical / "ratewall_historical_provisional_denominator_panel.csv",
        [
            {"period": "2021Q4"},
            {"period": "2026Q1"},
            {"period": "2026Q2"},
        ],
    )
    return {"sibling": sibling, "historical": historical}


def _numerator_row(
    period: str, tdc: str, public_interest: str, direct_treasury: str
) -> dict[str, str]:
    return {
        "period": period,
        "quarter": period,
        "assumption_case": "base",
        "tdc_ex_overlap_support_bil": tdc,
        "public_interest_net_block_partial_bil": public_interest,
        "direct_treasury_interest_support_bil": direct_treasury,
        "numerator_source_status": "source_backed_fixture",
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
