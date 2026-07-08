"""Marginal-only final readout for RateWall V1 closeout."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal
from pathlib import Path

from ratewall.databook.final_marginal_model import (
    DEFAULT_ADMITTED_RESIDUAL_PATH,
    DEFAULT_DENOMINATOR_PATH,
    DEFAULT_PI_DEBT_AUDIT_PATH,
    DEFAULT_SAFE_YIELD_PATH,
    DEFAULT_SELECTED_NUMERATOR_PATH,
    DEFAULT_TDC_SUPPORT_PATH,
    SELECTED_RW_M_CLAIM_BOUNDARY,
    SELECTED_RW_M_RWTAM_BLOCKED_USE,
)
from ratewall.databook.table_io import write_rows

DEFAULT_FINAL_RATIO_PATH = Path(
    "var/preliminary_scenario_results/final_marginal_model/"
    "ratewall_final_marginal_rw_ratio_snapshot.csv"
)
DEFAULT_READINESS_PATH = Path(
    "var/preliminary_scenario_results/final_marginal_model/"
    "ratewall_final_marginal_readiness_ledger.csv"
)
DEFAULT_CHANNEL_PARITY_PATH = Path(
    "var/preliminary_scenario_results/marginal_numerator/"
    "ratewall_channel_period_parity_matrix.csv"
)

FINAL_MARGINAL_READOUT_FIELDS = [
    "final_marginal_readout_row_id",
    "metric_id",
    "metric_value",
    "metric_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


def final_marginal_readout_rows(
    *,
    final_ratio_path: str | Path = DEFAULT_FINAL_RATIO_PATH,
    selected_numerator_path: str | Path = DEFAULT_SELECTED_NUMERATOR_PATH,
    denominator_path: str | Path = DEFAULT_DENOMINATOR_PATH,
    safe_yield_path: str | Path = DEFAULT_SAFE_YIELD_PATH,
    admitted_residual_path: str | Path = DEFAULT_ADMITTED_RESIDUAL_PATH,
    tdc_support_path: str | Path = DEFAULT_TDC_SUPPORT_PATH,
    pi_debt_audit_path: str | Path = DEFAULT_PI_DEBT_AUDIT_PATH,
    readiness_path: str | Path = DEFAULT_READINESS_PATH,
    channel_parity_path: str | Path = DEFAULT_CHANNEL_PARITY_PATH,
) -> list[dict[str, str]]:
    final_rows = _read_csv(Path(final_ratio_path))
    selected_n = _read_csv(Path(selected_numerator_path))
    denominator = _read_csv(Path(denominator_path))
    safe_yield = _read_csv(Path(safe_yield_path))
    residual = _read_csv(Path(admitted_residual_path))
    tdc = _read_csv(Path(tdc_support_path))
    debt_audit = _read_csv(Path(pi_debt_audit_path))
    readiness = _read_csv(Path(readiness_path))
    parity = _read_csv(Path(channel_parity_path))
    selected_final_count = sum(
        1 for row in final_rows if row.get("final_rw_m_selected") == "true"
    )
    selected_forecast_count = sum(
        1
        for row in final_rows
        if row.get("final_rw_m_selected") == "true"
        and row.get("period_object") == "forecast"
    )
    selected_n_count = sum(
        1 for row in selected_n if row.get("selected_marginal_n_allowed") == "true"
    )
    safe_yield_selected = [
        row for row in safe_yield if row.get("selected_safe_yield_delta_allowed") == "true"
    ]
    residual_selected = [
        row
        for row in residual
        if row.get("selected_admitted_disjoint_delta_allowed") == "true"
    ]
    debt_replacements = [
        row for row in debt_audit if row.get("replacement_recommended") == "true"
    ]
    tdc_available_count = sum(1 for row in tdc if _tdc_term_available_for_selected_n(row))
    rows = [
        _row(
            "final_rw_m_rows",
            str(len(final_rows)),
            "pass" if len(final_rows) == 117 else "fail",
            "final_marginal_model_snapshot",
            "missing_final_marginal_rows",
        ),
        _row(
            "final_rw_m_selected_rows",
            str(selected_final_count),
            "pass" if selected_final_count == 11 else "fail",
            "selected_current_forecast_rw_m_count",
            f"historical_or_incomplete_selected_rw_m;{SELECTED_RW_M_RWTAM_BLOCKED_USE}",
            claim_boundary=SELECTED_RW_M_CLAIM_BOUNDARY,
        ),
        _row(
            "selected_n_rows",
            str(selected_n_count),
            "pass" if selected_n_count == 11 else "fail",
            "selected_marginal_n_surface",
            "selected_n_missing_or_overselected",
        ),
        _row(
            "selected_d_rows",
            str(sum(1 for row in denominator if row.get("selected_marginal_D") == "true")),
            "pass"
            if sum(1 for row in denominator if row.get("selected_marginal_D") == "true")
            == 117
            else "fail",
            "selected_marginal_denominator_surface",
            "selected_d_missing_or_overselected",
        ),
        _row(
            "tdc_selected_support_rows",
            str(tdc_available_count),
            "pass"
            if len(tdc) == 11 and all(_tdc_term_available_for_selected_n(row) for row in tdc)
            else "fail",
            "tdc_income_addendum_or_fail_closed_zero",
            "tdc_term_missing_or_old_chi_support_selected",
        ),
        _row(
            "safe_yield_selected_nonzero_rows",
            str(len(safe_yield_selected)),
            "pass"
            if len(safe_yield_selected) == selected_final_count
            and all(Decimal(row.get("delta_safe_yield_bil") or "0") != 0 for row in safe_yield_selected)
            else "fail",
            "d1_safe_yield_selected_assumption_mode_current_forecast",
            "missing_or_zero_d1_after_promotion_gate",
        ),
        _row(
            "admitted_residual_selected_nonzero_rows",
            str(len(residual_selected)),
            "pass"
            if len(residual_selected) == selected_final_count
            and all(
                Decimal(row.get("delta_other_admitted_disjoint_bil") or "0") != 0
                for row in residual_selected
            )
            else "fail",
            "admitted_disjoint_residual_selected_private_safe_yield_assumption_mode",
            "missing_or_zero_residual_after_promotion_gate",
        ),
        _row(
            "pi_debt_replacement_rows",
            str(len(debt_replacements)),
            "pass" if len(debt_replacements) == selected_forecast_count else "fail",
            "public_interest_forecast_debt_stock_maturity_repricing_selected",
            "missing_forecast_explicit_debt_repricing_replacement",
        ),
        _row(
            "channel_parity_rows",
            str(len(parity)),
            "pass" if len(parity) >= 30 else "fail",
            "complete_channel_parity_matrix",
            "channel_omitted_from_parity_readout",
        ),
        _row(
            "readiness_checks_passed",
            str(sum(1 for row in readiness if row.get("check_status") == "pass")),
            "pass"
            if readiness
            and all(row.get("check_status") == "pass" for row in readiness)
            else "fail",
            "final_marginal_readiness_ledger",
            "readiness_check_failed",
        ),
    ]
    validate_final_marginal_readout_rows(rows)
    return rows


def write_final_marginal_readout_outputs(
    output_dir: str | Path,
    *,
    readout_rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    validate_final_marginal_readout_rows(readout_rows)
    path = out / "ratewall_final_marginal_readout.csv"
    write_rows(path, [dict(row) for row in readout_rows], FINAL_MARGINAL_READOUT_FIELDS)
    return {"final_marginal_readout_csv": path}


def validate_final_marginal_readout_rows(rows: Sequence[Mapping[str, str]]) -> None:
    if not rows:
        raise ValueError("final marginal readout rows are empty")
    for row in rows:
        if set(row) != set(FINAL_MARGINAL_READOUT_FIELDS):
            raise ValueError("final marginal readout schema mismatch")


def _row(
    metric_id: str,
    metric_value: str,
    metric_status: str,
    allowed_use: str,
    blocked_use: str,
    *,
    claim_boundary: str = "marginal_only_final_readout_uses_no_legacy_ratio_inputs",
) -> dict[str, str]:
    return {
        "final_marginal_readout_row_id": f"final_marginal_readout::{metric_id}",
        "metric_id": metric_id,
        "metric_value": metric_value,
        "metric_status": metric_status,
        "allowed_use": allowed_use,
        "blocked_use": blocked_use,
        "claim_boundary": claim_boundary,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _tdc_term_available_for_selected_n(row: Mapping[str, str]) -> bool:
    if (
        row.get("selected_tdc_formula_pass") == "true"
        and row.get("enters_selected_rw_m") == "true"
    ):
        return True
    return (
        row.get("selected_tdc_formula_pass") == "false"
        and row.get("enters_selected_rw_m") == "false"
        and row.get("marginal_tdc_support_bil") == "0"
        and "retired_chi_support_zero" in row.get("support_formula", "")
        and "income_addendum" in row.get("blocked_use", "")
    )
