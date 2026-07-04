from __future__ import annotations

import math
from pathlib import Path

from ratewall.databook.denominator_response_diagnostic import (
    DENOMINATOR_RESPONSE_DIAGNOSTIC_FIELDS,
    denominator_response_diagnostic_rows,
)
from ratewall.sources.base import RetrievalMetadata, SourceSnapshot


def test_denominator_response_diagnostic_rows_are_nonpromotional() -> None:
    rows = denominator_response_diagnostic_rows(
        macro_rows=_macro_rows(),
        control_snapshots=_control_snapshots(),
        shock_rows=_shock_rows(),
        source_paths=[Path("data/raw/example.csv")],
    )

    assert {field for row in rows for field in row} == set(
        DENOMINATOR_RESPONSE_DIAGNOSTIC_FIELDS
    )
    assert {row["horizon_q"] for row in rows} == {"4", "8"}
    assert {row["coefficient_admission_status"] for row in rows} == {
        "diagnostic_only_not_admitted_to_D"
    }
    assert {row["admitted_curve_response_coefficient"] for row in rows} == {""}
    assert {row["policy_path_100bp_year_normalization_status"] for row in rows} == {
        "blocked_scalar_surprise_not_admitted_100bp_year_policy_path"
    }
    assert {row["source_snapshot_status"] for row in rows} == {
        "pass_local_sources_available_for_diagnostic_estimate"
    }
    assert {row["canonical_ratio_entry"] for row in rows} == {"false"}
    assert {row["enters_main_ratio"] for row in rows} == {"false"}
    assert {row["evidence_mode_enabled"] for row in rows} == {"false"}
    assert {row["denominator_prior_update_allowed"] for row in rows} == {"false"}
    assert all("empirical_denominator_response_claim" in row["blocked_use"] for row in rows)
    assert all("not_curve_sensitive_D" in row["claim_boundary"] for row in rows)
    assert all(int(row["n_obs"]) > 40 for row in rows)


def test_denominator_response_diagnostic_requires_identifiable_design() -> None:
    rows = denominator_response_diagnostic_rows(
        macro_rows=_macro_rows(quarter_count=12),
        control_snapshots=_control_snapshots(quarter_count=12),
        shock_rows=_shock_rows(quarter_count=12),
    )

    assert rows == []


def _macro_rows(quarter_count: int = 96) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index in range(quarter_count):
        quarter = _quarter_label(2000, index)
        shock = _shock_value(index)
        real_fspdp = 1000.0 * math.exp(
            0.006 * index + 0.03 * shock + 0.01 * _noise(index, 1)
        )
        nominal_fspdp = real_fspdp * (1.1 + 0.002 * index + 0.01 * _noise(index, 2))
        nominal_gdp = nominal_fspdp / (0.82 + 0.02 * _noise(index, 3))
        real_pce = 800.0 * math.exp(0.004 * index + 0.01 * _noise(index, 4))
        nominal_pce = real_pce * (1.2 + 0.001 * index + 0.01 * _noise(index, 5))
        rows.append(
            {
                "quarter": quarter,
                "real_fspdp": str(real_fspdp),
                "nominal_fspdp": str(nominal_fspdp),
                "nominal_gdp": str(nominal_gdp),
                "real_pce": str(real_pce),
                "nominal_pce": str(nominal_pce),
                "fspdp_share_of_gdp": str(nominal_fspdp / nominal_gdp),
            }
        )
    return rows


def _control_snapshots(quarter_count: int = 96) -> dict[str, SourceSnapshot]:
    return {
        "UNRATE": _snapshot(
            "UNRATE",
            [
                {
                    "date": _quarter_start_date(2000, index),
                    "value": str(4.0 + _noise(index, 6)),
                }
                for index in range(quarter_count)
            ],
        ),
        "FEDFUNDS": _snapshot(
            "FEDFUNDS",
            [
                {
                    "date": _quarter_start_date(2000, index),
                    "value": str(2.0 + _noise(index, 7)),
                }
                for index in range(quarter_count)
            ],
        ),
    }


def _shock_rows(quarter_count: int = 96) -> list[dict[str, str]]:
    return [
        {
            "quarter": _quarter_label(2000, index),
            "monetary_event_sum": str(_shock_value(index)),
        }
        for index in range(quarter_count)
    ]


def _snapshot(series_id: str, records: list[dict[str, str]]) -> SourceSnapshot:
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id="fixture",
            series_id=series_id,
            source_url="fixture://local",
            units="level",
            frequency="quarterly",
            transform="level",
            retrieved_at="2026-06-26T00:00:00Z",
        ),
        records=records,
    )


def _shock_value(index: int) -> float:
    return _noise(index, 8) - 0.5 + 0.015 * math.sin(index)


def _noise(index: int, salt: int) -> float:
    return (((index + 1) * (salt * 7919 + 104729)) % 1009) / 1009.0


def _quarter_label(start_year: int, index: int) -> str:
    year = start_year + index // 4
    quarter = index % 4 + 1
    return f"{year}Q{quarter}"


def _quarter_start_date(start_year: int, index: int) -> str:
    year = start_year + index // 4
    month = (index % 4) * 3 + 1
    return f"{year:04d}-{month:02d}-01"
