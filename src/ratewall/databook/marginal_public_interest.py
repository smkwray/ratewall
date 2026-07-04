"""Public-interest marginal delta staging for RW_M."""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from decimal import Decimal, getcontext
from pathlib import Path

from ratewall.databook.table_io import write_rows

getcontext().prec = 200

DEFAULT_FORECAST_PUBLIC_INTEREST_PATH = Path(
    "var/preliminary_scenario_results/forecast_10y/"
    "ratewall_forecast_public_interest_net_block.csv"
)
DEFAULT_PLUS100_PAIR_INPUT_PATH = Path(
    "configs/assumption_mode/ratewall_public_interest_plus100bp_year_pair_input.csv"
)
DEFAULT_CURRENT_COMPONENT_INPUT_PATH = Path(
    "configs/assumption_mode/ratewall_public_interest_current_2026_component_input.csv"
)
DEFAULT_HISTORICAL_COMPONENT_INPUT_PATH = Path(
    "configs/assumption_mode/ratewall_public_interest_historical_component_input.csv"
)
DEFAULT_FORECAST_REMITTANCE_PATH = Path(
    "var/preliminary_scenario_results/forecast_hardening/"
    "ratewall_forecast_remittance_baseline_path.csv"
)
DEFAULT_REMITTANCE_ABSORBER_ASSUMPTIONS_PATH = Path(
    "configs/assumption_mode/ratewall_public_interest_remittance_absorber_assumptions.csv"
)
DEFAULT_DEBT_REPRICING_INPUT_PATH = Path(
    "configs/assumption_mode/ratewall_public_interest_forecast_debt_repricing_input.csv"
)

BASELINE_FORECAST_SCENARIO_ID = "cbo_baseline_noop_v1"
PLUS100_PUBLIC_INTEREST_SCENARIO_ID = (
    "cbo_baseline_plus_100bp_year_public_interest_assumption_v1"
)
PLUS100_PUBLIC_INTEREST_SCENARIO_ID_V2 = (
    "cbo_baseline_plus_100bp_year_public_interest_assumption_v2"
)
PLUS100_SHOCK_PATH_ID = "plus_100bp_year"
PASS_SAME_STATE_STATUS = "pass_same_state_plus_100bp_year_delta"
PASS_ASSUMPTION_MODE_STATUS = (
    "pass_selected_assumption_mode_plus_100bp_year_public_interest_delta"
)
OUTPUT_QUANTUM = Decimal("0.000000000000000001")
RATE_DELTA_BPS_YEAR = Decimal("100")
RATE_DELTA_FACTOR = Decimal("0.01")

REQUIRED_COMPONENT_KEYS = [
    "direct_treasury_domestic_nonbank",
    "bank_treasury",
    "iorb_reserves",
    "on_rrp",
    "remittance_current_reduction",
    "remittance_future_deferred_asset",
    "tax_timing",
    "fiscal_offset",
    "tga_liquidity",
    "foreign_holder_leakage",
    "tdc_overlap_shield",
    "legacy_interest_replacement_memo",
]

MARGINAL_PUBLIC_INTEREST_DELTA_FIELDS = [
    "marginal_public_interest_delta_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "scenario_id",
    "baseline_scenario_id",
    "shock_scenario_id",
    "shock_path_id",
    "public_interest_pair_source_id",
    "source_mode",
    "assumption_mode",
    "evidence_mode_enabled",
    "public_interest_baseline_bil",
    "public_interest_shock_bil",
    "delta_public_interest_net_block_bil",
    "delta_direct_treasury_current_demand_support_bil",
    "delta_bank_treasury_current_demand_support_bil",
    "delta_iorb_interest_cashflow_bil",
    "delta_projected_iorb_current_demand_support_bil",
    "delta_on_rrp_interest_cashflow_bil",
    "delta_projected_on_rrp_current_demand_support_bil",
    "delta_fed_interest_expense_bil",
    "delta_current_remittance_reduction_bil",
    "delta_future_remittance_deferred_asset_addition_bil",
    "delta_projected_current_remittance_demand_offset_bil",
    "delta_projected_future_remittance_drag_demand_offset_bil",
    "delta_gross_public_interest_current_demand_support_bil",
    "delta_interest_income_tax_timing_drag_bil",
    "delta_net_interest_before_fiscal_tga_offsets_bil",
    "delta_fiscal_offset_bil",
    "delta_tga_liquidity_offset_bil",
    "delta_foreign_holder_leakage_bil",
    "tdc_overlap_shield_bil",
    "source_component_mode",
    "selected_debt_service_mode",
    "selected_operating_liability_mode",
    "selected_remittance_mode",
    "selected_absorber_mode",
    "holder_split_basis",
    "same_state_delta_status",
    "selected_pi_delta_allowed",
    "selection_gate_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_PUBLIC_INTEREST_COMPONENT_FIELDS = [
    "marginal_public_interest_component_row_id",
    "marginal_public_interest_delta_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "scenario_id",
    "baseline_scenario_id",
    "shock_scenario_id",
    "shock_path_id",
    "component_key",
    "component_family",
    "payer_sector",
    "recipient_sector",
    "holder_sector",
    "source_field",
    "baseline_cashflow_bil",
    "shock_cashflow_bil",
    "delta_cashflow_bil",
    "basis_stock_bil",
    "rate_delta_bps_year",
    "demand_translation_share",
    "delta_current_demand_support_bil",
    "sign_in_net",
    "enters_gross_public_interest",
    "enters_selected_net_public_interest",
    "overlap_guard_key",
    "tdc_overlap_policy",
    "source_mode",
    "assumption_mode",
    "evidence_mode_enabled",
    "selected_component_allowed",
    "selection_gate_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]

MARGINAL_PUBLIC_INTEREST_DEBT_REPRICING_AUDIT_FIELDS = [
    "public_interest_debt_repricing_audit_row_id",
    "period_object",
    "period",
    "horizon",
    "state_id",
    "shock_path_id",
    "selected_debt_service_mode",
    "marketable_debt_stock_bil",
    "repricing_share",
    "floating_rate_share",
    "domestic_nonbank_holder_share",
    "bank_holder_share",
    "foreign_holder_share",
    "pass_through",
    "direct_treasury_current_demand_share",
    "bank_treasury_current_demand_share",
    "explicit_direct_treasury_delta_bil",
    "explicit_bank_treasury_delta_bil",
    "local_slope_direct_treasury_delta_bil",
    "local_slope_bank_treasury_delta_bil",
    "direct_gap_bil",
    "bank_gap_bil",
    "replacement_recommended",
    "selection_status",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
]


class MarginalPublicInterestError(ValueError):
    """Raised when public-interest marginal staging is unsafe."""


def marginal_public_interest_delta_rows(
    *,
    forecast_public_interest_path: str | Path = DEFAULT_FORECAST_PUBLIC_INTEREST_PATH,
    plus100_pair_input_path: str | Path | None = DEFAULT_PLUS100_PAIR_INPUT_PATH,
    current_component_input_path: str | Path | None = DEFAULT_CURRENT_COMPONENT_INPUT_PATH,
    historical_component_input_path: str | Path | None = DEFAULT_HISTORICAL_COMPONENT_INPUT_PATH,
    forecast_remittance_path: str | Path = DEFAULT_FORECAST_REMITTANCE_PATH,
    remittance_absorber_assumptions_path: str | Path | None = DEFAULT_REMITTANCE_ABSORBER_ASSUMPTIONS_PATH,
    debt_repricing_input_path: str | Path | None = DEFAULT_DEBT_REPRICING_INPUT_PATH,
    component_rows: Sequence[Mapping[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Build public-interest deltas with selected same-state +100bp-year rows."""

    forecast_path = Path(forecast_public_interest_path)
    rows = _forecast_rows(forecast_path)
    if component_rows is None:
        component_rows = marginal_public_interest_component_rows(
            forecast_public_interest_path=forecast_path,
            current_component_input_path=(
                None
                if current_component_input_path is None
                else Path(current_component_input_path)
            ),
            historical_component_input_path=(
                None
                if historical_component_input_path is None
                else Path(historical_component_input_path)
            ),
            forecast_remittance_path=Path(forecast_remittance_path),
            remittance_absorber_assumptions_path=(
                None
                if remittance_absorber_assumptions_path is None
                else Path(remittance_absorber_assumptions_path)
            ),
            debt_repricing_input_path=(
                None
                if debt_repricing_input_path is None
                else Path(debt_repricing_input_path)
            ),
        )
    rows.extend(_selected_summary_rows_from_components(component_rows, forecast_path))
    if plus100_pair_input_path is not None and not any(
        row["period_object"] == "current" and row["selected_pi_delta_allowed"] == "true"
        for row in rows
    ):
        rows.extend(_plus100_pair_rows(Path(plus100_pair_input_path)))
    rows.extend(_missing_period_rows(include_current=not any(
        row["period_object"] == "current" and row["selected_pi_delta_allowed"] == "true"
        for row in rows
    )))
    validate_marginal_public_interest_delta_rows(rows)
    return rows


def marginal_public_interest_component_rows(
    *,
    forecast_public_interest_path: str | Path = DEFAULT_FORECAST_PUBLIC_INTEREST_PATH,
    current_component_input_path: str | Path | None = DEFAULT_CURRENT_COMPONENT_INPUT_PATH,
    historical_component_input_path: str | Path | None = DEFAULT_HISTORICAL_COMPONENT_INPUT_PATH,
    forecast_remittance_path: str | Path = DEFAULT_FORECAST_REMITTANCE_PATH,
    remittance_absorber_assumptions_path: str | Path | None = DEFAULT_REMITTANCE_ABSORBER_ASSUMPTIONS_PATH,
    debt_repricing_input_path: str | Path | None = DEFAULT_DEBT_REPRICING_INPUT_PATH,
) -> list[dict[str, str]]:
    """Build component-level public-interest rows before selected netting."""

    rows: list[dict[str, str]] = []
    forecast_path = Path(forecast_public_interest_path)
    remittance_absorber_by_key = _remittance_absorber_assumptions_by_key(
        None
        if remittance_absorber_assumptions_path is None
        else Path(remittance_absorber_assumptions_path)
    )
    debt_repricing_by_key = _debt_repricing_input_by_key(
        None if debt_repricing_input_path is None else Path(debt_repricing_input_path)
    )
    if forecast_path.exists():
        rows.extend(
            _forecast_selected_component_rows(
                forecast_path,
                Path(forecast_remittance_path),
                remittance_absorber_by_key,
                debt_repricing_by_key,
            )
        )
    if current_component_input_path is not None and Path(current_component_input_path).exists():
        rows.extend(
            _current_selected_component_rows(
                Path(current_component_input_path),
                remittance_absorber_by_key,
            )
        )
    if historical_component_input_path is not None and Path(historical_component_input_path).exists():
        rows.extend(
            _current_selected_component_rows(
                Path(historical_component_input_path),
                remittance_absorber_by_key,
            )
        )
    if rows:
        validate_marginal_public_interest_component_rows(rows)
    return rows


def write_marginal_public_interest_outputs(
    output_dir: str | Path,
    *,
    delta_rows: Sequence[Mapping[str, str]],
    component_rows: Sequence[Mapping[str, str]] | None = None,
    debt_repricing_audit_rows: Sequence[Mapping[str, str]] | None = None,
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "delta_csv": out / "ratewall_marginal_public_interest_delta.csv",
        "component_csv": out / "ratewall_marginal_public_interest_components.csv",
        "debt_repricing_audit_csv": out / "ratewall_public_interest_debt_repricing_audit.csv",
    }
    write_rows(
        paths["delta_csv"],
        [dict(row) for row in delta_rows],
        MARGINAL_PUBLIC_INTEREST_DELTA_FIELDS,
    )
    if component_rows is not None:
        write_rows(
            paths["component_csv"],
            [dict(row) for row in component_rows],
            MARGINAL_PUBLIC_INTEREST_COMPONENT_FIELDS,
        )
    if debt_repricing_audit_rows is not None:
        write_rows(
            paths["debt_repricing_audit_csv"],
            [dict(row) for row in debt_repricing_audit_rows],
            MARGINAL_PUBLIC_INTEREST_DEBT_REPRICING_AUDIT_FIELDS,
        )
    return paths


def marginal_public_interest_debt_repricing_audit_rows(
    *,
    component_rows: Sequence[Mapping[str, str]],
    debt_repricing_input_path: str | Path | None = DEFAULT_DEBT_REPRICING_INPUT_PATH,
) -> list[dict[str, str]]:
    selected_components = [
        row
        for row in component_rows
        if row.get("selected_component_allowed") == "true"
        and row.get("component_key")
        in {"direct_treasury_domestic_nonbank", "bank_treasury"}
    ]
    by_key: dict[tuple[str, str, str, str], dict[str, Mapping[str, str]]] = {}
    for row in selected_components:
        key = (
            row["period_object"],
            row["period"],
            row["state_id"],
            row["shock_path_id"],
        )
        by_key.setdefault(key, {})[row["component_key"]] = row
    input_by_key = _debt_repricing_input_by_key(
        None if debt_repricing_input_path is None else Path(debt_repricing_input_path)
    )
    rows = []
    for key, components in sorted(by_key.items()):
        direct = components.get("direct_treasury_domestic_nonbank")
        bank = components.get("bank_treasury")
        if direct is None or bank is None:
            continue
        input_row = input_by_key.get(key)
        rows.append(_debt_repricing_audit_row(key, direct, bank, input_row))
    validate_marginal_public_interest_debt_repricing_audit_rows(rows)
    return rows


def validate_marginal_public_interest_debt_repricing_audit_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalPublicInterestError("public-interest debt repricing audit rows are empty")
    for row in rows:
        if set(row) != set(MARGINAL_PUBLIC_INTEREST_DEBT_REPRICING_AUDIT_FIELDS):
            raise MarginalPublicInterestError("public-interest debt repricing audit schema mismatch")
        if row["replacement_recommended"] == "true":
            if row["selection_status"] != "pass_explicit_debt_repricing_replacement_candidate":
                raise MarginalPublicInterestError("debt repricing replacement status mismatch")
        else:
            if "selected_public_interest_replacement" not in row["blocked_use"]:
                raise MarginalPublicInterestError("debt repricing audit blocker missing")


def validate_marginal_public_interest_delta_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalPublicInterestError("public-interest delta rows are empty")
    selected_keys: set[tuple[str, str, str, str]] = set()
    for row in rows:
        if set(row) != set(MARGINAL_PUBLIC_INTEREST_DELTA_FIELDS):
            raise MarginalPublicInterestError("public-interest delta schema mismatch")
        if row["selected_pi_delta_allowed"] == "true":
            if row["shock_path_id"] != PLUS100_SHOCK_PATH_ID:
                raise MarginalPublicInterestError(
                    "selected public-interest delta must use plus_100bp_year"
                )
            if row["same_state_delta_status"] != PASS_SAME_STATE_STATUS:
                raise MarginalPublicInterestError(
                    "selected public-interest delta must pass same-state gate"
                )
            if row["selection_gate_status"] != PASS_ASSUMPTION_MODE_STATUS:
                raise MarginalPublicInterestError(
                    "selected public-interest delta must pass assumption-mode gate"
                )
            if row["source_mode"] not in {"source_grade", "assumption_mode"}:
                raise MarginalPublicInterestError(
                    "selected public-interest source_mode is unsupported"
                )
            if row["source_mode"] == "assumption_mode":
                if row["assumption_mode"] != "true" or row["evidence_mode_enabled"] != "false":
                    raise MarginalPublicInterestError(
                        "assumption-mode selected public-interest row mislabeled"
                    )
            key = (
                row["period"],
                row["horizon"],
                row["state_id"],
                row["shock_path_id"],
            )
            if key in selected_keys:
                raise MarginalPublicInterestError(
                    "duplicate selected public-interest full key"
                )
            selected_keys.add(key)
            baseline = Decimal(row["public_interest_baseline_bil"])
            shock = Decimal(row["public_interest_shock_bil"])
            delta = Decimal(row["delta_public_interest_net_block_bil"])
            if shock - baseline != delta:
                raise MarginalPublicInterestError(
                    "selected public-interest delta identity failed"
                )
            if (
                row["period_object"] == "current"
                and row["scenario_id"].endswith("_v1")
                and delta == 0
            ):
                raise MarginalPublicInterestError(
                    "current selected public-interest row is old zero placeholder"
                )
            missing_component_summary = [
                field
                for field in _blank_summary_component_fields()
                if field.startswith("delta_") and not row[field]
            ]
            if missing_component_summary:
                raise MarginalPublicInterestError(
                    "selected public-interest component summary missing"
                )
            component_net = _summary_component_net(row)
            if component_net != delta:
                raise MarginalPublicInterestError(
                    "selected public-interest component summary identity failed"
                )
        if row["selected_pi_delta_allowed"] == "false" and "selected_marginal_n" not in row["blocked_use"]:
            raise MarginalPublicInterestError("selected marginal N blocker missing")


def validate_marginal_public_interest_component_rows(
    rows: Sequence[Mapping[str, str]],
) -> None:
    if not rows:
        raise MarginalPublicInterestError("public-interest component rows are empty")
    selected_by_key: dict[tuple[str, str, str, str], set[str]] = {}
    for row in rows:
        if set(row) != set(MARGINAL_PUBLIC_INTEREST_COMPONENT_FIELDS):
            raise MarginalPublicInterestError("public-interest component schema mismatch")
        if row["selected_component_allowed"] == "true":
            if row["shock_path_id"] != PLUS100_SHOCK_PATH_ID:
                raise MarginalPublicInterestError(
                    "selected public-interest component must use plus_100bp_year"
                )
            if row["selection_gate_status"] != PASS_ASSUMPTION_MODE_STATUS:
                raise MarginalPublicInterestError(
                    "selected public-interest component gate failed"
                )
            key = (
                row["period_object"],
                row["period"],
                row["state_id"],
                row["shock_path_id"],
            )
            selected_by_key.setdefault(key, set()).add(row["component_key"])
            if row["component_key"] == "legacy_interest_replacement_memo":
                if row["enters_selected_net_public_interest"] != "false":
                    raise MarginalPublicInterestError("legacy interest memo entered selected net")
            if row["component_key"] in {
                "direct_treasury_domestic_nonbank",
                "bank_treasury",
                "iorb_reserves",
                "on_rrp",
            }:
                if row["tdc_overlap_policy"] != "excluded_from_tdc_default":
                    raise MarginalPublicInterestError(
                        "selected public-interest cashflow must be excluded from TDC default"
                    )
    required = set(REQUIRED_COMPONENT_KEYS)
    for key, component_keys in selected_by_key.items():
        missing = required - component_keys
        if missing:
            raise MarginalPublicInterestError(
                f"selected public-interest key {key} missing components: {sorted(missing)}"
            )


def _forecast_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    source_rows = _read_csv(path)
    by_year_scenario = {
        (row["fiscal_year"], row["scenario_id"]): row for row in source_rows
    }
    out: list[dict[str, str]] = []
    for row in source_rows:
        year = row["fiscal_year"]
        baseline_id = row["baseline_scenario_id"]
        baseline = by_year_scenario.get((year, baseline_id))
        if baseline is None:
            baseline_value = Decimal("0")
            status = "fail_closed_missing_forecast_baseline_state"
        else:
            baseline_value = Decimal(baseline["net_interest_after_fiscal_tga_offsets_bil"])
            status = "diagnostic_existing_forecast_delta_not_plus_100bp_year"
        shock_value = Decimal(row["net_interest_after_fiscal_tga_offsets_bil"])
        is_baseline = row["scenario_id"] == baseline_id
        if is_baseline:
            status = "fail_closed_baseline_row_not_shock_delta"
        out.append(
            {
                "marginal_public_interest_delta_row_id": (
                    f"marginal_public_interest_delta::forecast::{year}::{row['scenario_id']}"
                ),
                "period_object": "forecast",
                "period": year,
                "horizon": "annual_h1_100bp_year",
                "state_id": f"forecast_state::{year}::{row['scenario_id']}",
                "scenario_id": row["scenario_id"],
                "baseline_scenario_id": baseline_id,
                "shock_scenario_id": "" if is_baseline else row["scenario_id"],
                "shock_path_id": (
                    "baseline_no_shock"
                    if is_baseline
                    else "diagnostic_existing_forecast_scenario_not_plus_100bp_year"
                ),
                "public_interest_pair_source_id": (
                    "forecast_public_interest_net_block.diagnostic_existing_scenario"
                ),
                "source_mode": "diagnostic",
                "assumption_mode": "false",
                "evidence_mode_enabled": "false",
                "public_interest_baseline_bil": _fmt(baseline_value),
                "public_interest_shock_bil": _fmt(shock_value),
                "delta_public_interest_net_block_bil": _fmt(shock_value - baseline_value),
                **_blank_summary_component_fields(),
                "same_state_delta_status": status,
                "selected_pi_delta_allowed": "false",
                "selection_gate_status": "fail_closed_missing_plus_100bp_year_public_interest_pair",
                "allowed_use": "diagnostic_public_interest_delta_context",
                "blocked_use": "selected_marginal_n;selected_rw_m;canonical_headline_promotion",
                "claim_boundary": "forecast_public_interest_delta_not_selected_until_named_marginal_pair",
            }
        )
    return out


def _forecast_selected_component_rows(
    path: Path,
    remittance_path: Path,
    remittance_absorber_by_key: Mapping[tuple[str, str, str], Mapping[str, str]],
    debt_repricing_by_key: Mapping[tuple[str, str, str, str], Mapping[str, str]],
) -> list[dict[str, str]]:
    if not path.exists():
        return []
    source_rows = _read_csv(path)
    baseline_rows = [
        row for row in source_rows
        if row.get("scenario_id") == BASELINE_FORECAST_SCENARIO_ID
        and row.get("baseline_scenario_id") == BASELINE_FORECAST_SCENARIO_ID
    ]
    if not baseline_rows:
        return []
    required = {
        "fiscal_year",
        "net_interest_after_fiscal_tga_offsets_bil",
        "direct_treasury_current_demand_support_bil",
        "bank_treasury_current_demand_support_bil",
        "projected_iorb_interest_basis_bil",
        "projected_iorb_current_demand_support_bil",
        "projected_on_rrp_interest_basis_bil",
        "projected_on_rrp_current_demand_support_bil",
        "cbo_short_rate_pct",
        "iorb_rate_spread_vs_cbo_short_rate_pct",
        "on_rrp_rate_spread_vs_cbo_short_rate_pct",
        "gross_public_interest_current_demand_support_bil",
        "interest_income_tax_timing_drag_bil",
        "net_interest_before_fiscal_tga_offsets_bil",
        "fiscal_offset_bil",
        "tga_liquidity_offset_bil",
        "cbo_nominal_gdp_bil",
        "reserve_balance_stock_gdp_share",
        "on_rrp_stock_gdp_share",
    }
    if required - set(baseline_rows[0]):
        return []
    remittance_by_year = _remittance_by_year(remittance_path)
    source_by_key = {
        (row["fiscal_year"], row["scenario_id"]): row for row in source_rows
    }
    rows: list[dict[str, str]] = []
    for baseline in baseline_rows:
        year = baseline["fiscal_year"]
        up = source_by_key.get((year, "tdcsim_rate_up_25bp_v1"))
        down = source_by_key.get((year, "tdcsim_rate_down_25bp_v1"))
        if up is None or down is None:
            continue
        state_id = f"cbo_baseline_state::{year}"
        debt_input = debt_repricing_by_key.get(
            ("forecast", year, state_id, PLUS100_SHOCK_PATH_ID)
        )
        debt_values = _forecast_debt_service_values_from_input(debt_input)
        if debt_values is None:
            direct_delta = Decimal("2") * (
                Decimal(up["direct_treasury_current_demand_support_bil"])
                - Decimal(down["direct_treasury_current_demand_support_bil"])
            )
            direct_cashflow = direct_delta
            direct_basis_stock = Decimal("0")
            direct_demand_share = Decimal("1")
            bank_delta = Decimal("2") * (
                Decimal(up["bank_treasury_current_demand_support_bil"])
                - Decimal(down["bank_treasury_current_demand_support_bil"])
            )
            bank_cashflow = bank_delta
            bank_basis_stock = Decimal("0")
            bank_demand_share = Decimal("1")
            source_component_mode = "assumption_mode_local_rate_slope_from_prior_surface"
            selected_debt_service_mode = "local_rate_slope_rate_up_down_25bp"
            holder_split_basis = "embedded_in_prior_surface_no_second_haircut"
            claim_boundary = (
                "forecast_public_interest_assumption_mode_includes_direct_bank_"
                "local_rate_slope_plus_operating_liability_delta"
            )
        else:
            direct_delta = debt_values["direct_delta"]
            direct_cashflow = debt_values["direct_cashflow"]
            direct_basis_stock = debt_values["basis_stock"]
            direct_demand_share = debt_values["direct_demand_share"]
            bank_delta = debt_values["bank_delta"]
            bank_cashflow = debt_values["bank_cashflow"]
            bank_basis_stock = debt_values["basis_stock"]
            bank_demand_share = debt_values["bank_demand_share"]
            source_component_mode = "assumption_mode_explicit_forecast_debt_stock_maturity_repricing"
            selected_debt_service_mode = "explicit_forecast_debt_stock_maturity_repricing"
            holder_split_basis = "explicit_forecast_debt_stock_maturity_assumption_input"
            claim_boundary = (
                "assumption_mode_forecast_debt_stock_maturity_repricing_replaces_"
                "local_slope_direct_bank_inside_public_interest_only"
            )
        rows.extend(
            _component_rows_from_values(
                period_object="forecast",
                period=year,
                state_id=state_id,
                scenario_id=PLUS100_PUBLIC_INTEREST_SCENARIO_ID_V2,
                baseline_scenario_id=BASELINE_FORECAST_SCENARIO_ID,
                shock_scenario_id=PLUS100_PUBLIC_INTEREST_SCENARIO_ID_V2,
                baseline_public_interest_support=Decimal(
                    baseline["net_interest_after_fiscal_tga_offsets_bil"]
                ),
                direct_delta=direct_delta,
                direct_cashflow=direct_cashflow,
                direct_basis_stock=direct_basis_stock,
                direct_demand_share=direct_demand_share,
                bank_delta=bank_delta,
                bank_cashflow=bank_cashflow,
                bank_basis_stock=bank_basis_stock,
                bank_demand_share=bank_demand_share,
                iorb_values=_forecast_operating_values(baseline, "iorb"),
                on_rrp_values=_forecast_operating_values(baseline, "on_rrp"),
                remittance_capacity=Decimal(
                    remittance_by_year.get(year, {}).get("remittance_baseline_bil", "0")
                ),
                remittance_offset_share=Decimal("1"),
                current_remittance_demand_share=_remittance_absorber_share(
                    remittance_absorber_by_key,
                    period_object="forecast",
                    period=year,
                    state_id=state_id,
                    field="current_remittance_demand_share",
                    fallback=Decimal("0"),
                ),
                future_remittance_drag_current_demand_share=_remittance_absorber_share(
                    remittance_absorber_by_key,
                    period_object="forecast",
                    period=year,
                    state_id=state_id,
                    field="future_remittance_drag_current_demand_share",
                    fallback=Decimal("0"),
                ),
                tax_timing_rate=_safe_ratio(
                    Decimal(baseline["interest_income_tax_timing_drag_bil"]),
                    Decimal(baseline["gross_public_interest_current_demand_support_bil"]),
                ),
                fiscal_offset_rate=_safe_ratio(
                    Decimal(baseline["fiscal_offset_bil"]),
                    Decimal(baseline["net_interest_before_fiscal_tga_offsets_bil"]),
                ),
                tga_liquidity_offset_rate=_safe_ratio(
                    Decimal(baseline["tga_liquidity_offset_bil"]),
                    Decimal(baseline["net_interest_before_fiscal_tga_offsets_bil"]),
                ),
                delta_foreign_holder_leakage=Decimal("0"),
                tdc_overlap_shield=Decimal("0"),
                legacy_interest_support=Decimal(baseline["legacy_interest_support_bil"]),
                source_component_mode=source_component_mode,
                selected_debt_service_mode=selected_debt_service_mode,
                holder_split_basis=holder_split_basis,
                claim_boundary=claim_boundary,
            )
        )
    return rows


def _current_selected_component_rows(
    path: Path,
    remittance_absorber_by_key: Mapping[tuple[str, str, str], Mapping[str, str]],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in _read_csv(path):
        _validate_current_input(row)
        r = Decimal(row["shock_bps_year"]) / Decimal("10000")
        treasury_cashflow = (
            Decimal(row["treasury_repricing_base_bil"])
            * r
            * Decimal(row["treasury_repricing_pass_through"])
        )
        direct_cashflow = (
            treasury_cashflow * Decimal(row["domestic_nonbank_treasury_holder_share"])
        )
        bank_cashflow = treasury_cashflow * Decimal(row["bank_treasury_holder_share"])
        foreign_leakage = treasury_cashflow * Decimal(row["foreign_treasury_holder_share"])
        out.extend(
            _component_rows_from_values(
                period_object=row["period_object"],
                period=row["period"],
                state_id=row["state_id"],
                scenario_id=row["scenario_id"],
                baseline_scenario_id=row["baseline_scenario_id"],
                shock_scenario_id=row["shock_scenario_id"],
                baseline_public_interest_support=Decimal(
                    row["baseline_public_interest_support_bil"]
                ),
                direct_delta=direct_cashflow
                * Decimal(row["direct_treasury_current_demand_share"]),
                direct_cashflow=direct_cashflow,
                direct_basis_stock=Decimal(row["treasury_repricing_base_bil"]),
                direct_demand_share=Decimal(row["direct_treasury_current_demand_share"]),
                bank_delta=bank_cashflow
                * Decimal(row["bank_treasury_current_demand_share"]),
                bank_cashflow=bank_cashflow,
                bank_basis_stock=Decimal(row["treasury_repricing_base_bil"]),
                bank_demand_share=Decimal(row["bank_treasury_current_demand_share"]),
                iorb_values=_explicit_operating_values(
                    stock=Decimal(row["reserve_balance_stock_bil"]),
                    pass_through=Decimal(row["iorb_pass_through_scale"]),
                    demand_share=Decimal(row["iorb_recipient_current_demand_share"]),
                ),
                on_rrp_values=_explicit_operating_values(
                    stock=Decimal(row["on_rrp_stock_bil"]),
                    pass_through=Decimal(row["on_rrp_pass_through_scale"]),
                    demand_share=Decimal(row["on_rrp_recipient_current_demand_share"]),
                ),
                remittance_capacity=Decimal(row["remittance_capacity_bil"]),
                remittance_offset_share=Decimal(row["remittance_offset_share"]),
                current_remittance_demand_share=_remittance_absorber_share(
                    remittance_absorber_by_key,
                    period_object=row["period_object"],
                    period=row["period"],
                    state_id=row["state_id"],
                    field="current_remittance_demand_share",
                    fallback=Decimal(row["current_remittance_demand_share"]),
                ),
                future_remittance_drag_current_demand_share=_remittance_absorber_share(
                    remittance_absorber_by_key,
                    period_object=row["period_object"],
                    period=row["period"],
                    state_id=row["state_id"],
                    field="future_remittance_drag_current_demand_share",
                    fallback=Decimal(row["future_remittance_drag_current_demand_share"]),
                ),
                tax_timing_rate=Decimal(row["tax_timing_rate"]),
                fiscal_offset_rate=Decimal(row["fiscal_offset_rate"]),
                tga_liquidity_offset_rate=Decimal(row["tga_liquidity_offset_rate"]),
                delta_foreign_holder_leakage=foreign_leakage,
                tdc_overlap_shield=Decimal(row["tdc_overlap_shield_bil"]),
                legacy_interest_support=Decimal(row["baseline_public_interest_support_bil"]),
                source_component_mode="assumption_mode_explicit_current_component_input",
                selected_debt_service_mode="explicit_current_repricing_base_input",
                holder_split_basis=row["holder_split_basis"],
                claim_boundary=row["claim_boundary"],
            )
        )
    return out


def _component_rows_from_values(
    *,
    period_object: str,
    period: str,
    state_id: str,
    scenario_id: str,
    baseline_scenario_id: str,
    shock_scenario_id: str,
    baseline_public_interest_support: Decimal,
    direct_delta: Decimal,
    direct_cashflow: Decimal,
    direct_basis_stock: Decimal,
    direct_demand_share: Decimal,
    bank_delta: Decimal,
    bank_cashflow: Decimal,
    bank_basis_stock: Decimal,
    bank_demand_share: Decimal,
    iorb_values: Mapping[str, Decimal],
    on_rrp_values: Mapping[str, Decimal],
    remittance_capacity: Decimal,
    remittance_offset_share: Decimal,
    current_remittance_demand_share: Decimal,
    future_remittance_drag_current_demand_share: Decimal,
    tax_timing_rate: Decimal,
    fiscal_offset_rate: Decimal,
    tga_liquidity_offset_rate: Decimal,
    delta_foreign_holder_leakage: Decimal,
    tdc_overlap_shield: Decimal,
    legacy_interest_support: Decimal,
    source_component_mode: str,
    selected_debt_service_mode: str,
    holder_split_basis: str,
    claim_boundary: str,
) -> list[dict[str, str]]:
    delta_iorb_cashflow = iorb_values["delta_cashflow"]
    delta_on_rrp_cashflow = on_rrp_values["delta_cashflow"]
    delta_iorb_support = iorb_values["delta_support"]
    delta_on_rrp_support = on_rrp_values["delta_support"]
    delta_fed_interest_expense = delta_iorb_cashflow + delta_on_rrp_cashflow
    potential_remittance_hit = delta_fed_interest_expense * remittance_offset_share
    current_remittance_reduction = min(
        potential_remittance_hit,
        max(remittance_capacity, Decimal("0")),
    )
    future_deferred_asset = potential_remittance_hit - current_remittance_reduction
    current_remittance_offset = (
        -current_remittance_reduction * current_remittance_demand_share
    )
    future_remittance_offset = (
        -future_deferred_asset * future_remittance_drag_current_demand_share
    )
    gross = (
        direct_delta
        + bank_delta
        + delta_iorb_support
        + delta_on_rrp_support
        + current_remittance_offset
        + future_remittance_offset
    )
    tax_drag = gross * tax_timing_rate
    before_fiscal_tga = gross - tax_drag
    fiscal_offset = before_fiscal_tga * fiscal_offset_rate
    tga_offset = before_fiscal_tga * tga_liquidity_offset_rate
    delta_id = _selected_delta_row_id(period_object, period, scenario_id)
    common = {
        "marginal_public_interest_delta_row_id": delta_id,
        "period_object": period_object,
        "period": period,
        "horizon": "annual_h1_100bp_year",
        "state_id": state_id,
        "scenario_id": scenario_id,
        "baseline_scenario_id": baseline_scenario_id,
        "shock_scenario_id": shock_scenario_id,
        "shock_path_id": PLUS100_SHOCK_PATH_ID,
        "source_mode": "assumption_mode",
        "assumption_mode": "true",
        "evidence_mode_enabled": "false",
        "selected_component_allowed": "true",
        "selection_gate_status": PASS_ASSUMPTION_MODE_STATUS,
        "allowed_use": "selected_marginal_public_interest_component_assumption_mode",
    }

    specs = [
        _component_spec(
            key="direct_treasury_domestic_nonbank",
            family="debt_service_interest",
            payer="treasury",
            recipient="domestic_nonbank_private_holders",
            holder="domestic_nonbank",
            source_field="direct_treasury_current_demand_support_bil",
            baseline=Decimal("0"),
            delta_cashflow=direct_cashflow,
            basis=direct_basis_stock,
            demand_share=direct_demand_share,
            support=direct_delta,
            sign=Decimal("1"),
            gross=True,
            selected=True,
        ),
        _component_spec(
            key="bank_treasury",
            family="debt_service_interest",
            payer="treasury",
            recipient="banks",
            holder="bank",
            source_field="bank_treasury_current_demand_support_bil",
            baseline=Decimal("0"),
            delta_cashflow=bank_cashflow,
            basis=bank_basis_stock,
            demand_share=bank_demand_share,
            support=bank_delta,
            sign=Decimal("1"),
            gross=True,
            selected=True,
        ),
        _component_spec(
            key="iorb_reserves",
            family="fed_liability_interest",
            payer="federal_reserve",
            recipient="banks",
            holder="reserve_holder",
            source_field="projected_iorb_current_demand_support_bil",
            baseline=iorb_values["baseline_cashflow"],
            delta_cashflow=delta_iorb_cashflow,
            basis=iorb_values["basis_stock"],
            demand_share=iorb_values["demand_share"],
            support=delta_iorb_support,
            sign=Decimal("1"),
            gross=True,
            selected=True,
        ),
        _component_spec(
            key="on_rrp",
            family="fed_liability_interest",
            payer="federal_reserve",
            recipient="on_rrp_counterparties",
            holder="on_rrp_counterparty",
            source_field="projected_on_rrp_current_demand_support_bil",
            baseline=on_rrp_values["baseline_cashflow"],
            delta_cashflow=delta_on_rrp_cashflow,
            basis=on_rrp_values["basis_stock"],
            demand_share=on_rrp_values["demand_share"],
            support=delta_on_rrp_support,
            sign=Decimal("1"),
            gross=True,
            selected=True,
        ),
        _component_spec(
            key="remittance_current_reduction",
            family="remittance_timing",
            payer="federal_reserve",
            recipient="treasury",
            holder="public_sector",
            source_field="remittance_baseline_bil",
            baseline=remittance_capacity,
            delta_cashflow=-current_remittance_reduction,
            basis=remittance_capacity,
            demand_share=current_remittance_demand_share,
            support=current_remittance_offset,
            sign=Decimal("1"),
            gross=True,
            selected=True,
        ),
        _component_spec(
            key="remittance_future_deferred_asset",
            family="remittance_timing",
            payer="federal_reserve",
            recipient="future_treasury_revenue",
            holder="public_sector",
            source_field="future_remittance_deferred_asset_addition",
            baseline=Decimal("0"),
            delta_cashflow=-future_deferred_asset,
            basis=potential_remittance_hit,
            demand_share=future_remittance_drag_current_demand_share,
            support=future_remittance_offset,
            sign=Decimal("1"),
            gross=True,
            selected=True,
        ),
        _component_spec(
            key="tax_timing",
            family="tax_absorber",
            payer="private_recipients",
            recipient="treasury",
            holder="tax_authority",
            source_field="interest_income_tax_timing_drag_bil",
            baseline=Decimal("0"),
            delta_cashflow=tax_drag,
            basis=gross,
            demand_share=tax_timing_rate,
            support=tax_drag,
            sign=Decimal("-1"),
            gross=False,
            selected=True,
        ),
        _component_spec(
            key="fiscal_offset",
            family="fiscal_absorber",
            payer="public_sector",
            recipient="aggregate_demand_absorber",
            holder="fiscal_policy",
            source_field="fiscal_offset_bil",
            baseline=Decimal("0"),
            delta_cashflow=fiscal_offset,
            basis=before_fiscal_tga,
            demand_share=fiscal_offset_rate,
            support=fiscal_offset,
            sign=Decimal("-1"),
            gross=False,
            selected=True,
        ),
        _component_spec(
            key="tga_liquidity",
            family="liquidity_absorber",
            payer="treasury_general_account",
            recipient="liquidity_absorber",
            holder="public_sector_liquidity",
            source_field="tga_liquidity_offset_bil",
            baseline=Decimal("0"),
            delta_cashflow=tga_offset,
            basis=before_fiscal_tga,
            demand_share=tga_liquidity_offset_rate,
            support=tga_offset,
            sign=Decimal("-1"),
            gross=False,
            selected=True,
        ),
        _component_spec(
            key="foreign_holder_leakage",
            family="holder_leakage",
            payer="treasury",
            recipient="foreign_holders",
            holder="foreign",
            source_field="foreign_holder_leakage_bil",
            baseline=Decimal("0"),
            delta_cashflow=delta_foreign_holder_leakage,
            basis=delta_foreign_holder_leakage,
            demand_share=Decimal("0"),
            support=Decimal("0"),
            sign=Decimal("0"),
            gross=False,
            selected=False,
        ),
        _component_spec(
            key="tdc_overlap_shield",
            family="overlap_shield",
            payer="public_interest_block",
            recipient="tdc_overlap_removed",
            holder="not_applicable",
            source_field="tdc_overlap_shield_bil",
            baseline=Decimal("0"),
            delta_cashflow=tdc_overlap_shield,
            basis=tdc_overlap_shield,
            demand_share=Decimal("0"),
            support=Decimal("0"),
            sign=Decimal("0"),
            gross=False,
            selected=False,
        ),
        _component_spec(
            key="legacy_interest_replacement_memo",
            family="memo",
            payer="legacy_surface",
            recipient="not_selected",
            holder="not_applicable",
            source_field="legacy_interest_support_bil",
            baseline=legacy_interest_support,
            delta_cashflow=Decimal("0"),
            basis=legacy_interest_support,
            demand_share=Decimal("0"),
            support=Decimal("0"),
            sign=Decimal("0"),
            gross=False,
            selected=False,
        ),
    ]
    rows = []
    for spec in specs:
        blocked = (
            "tdc_default_support;standalone_selected_n"
            if spec["selected"] else "selected_marginal_n;selected_rw_m"
        )
        rows.append(
            {
                **common,
                "marginal_public_interest_component_row_id": (
                    "marginal_public_interest_component::"
                    f"{period_object}::{period}::{state_id}::plus_100bp_year::"
                    f"{spec['component_key']}"
                ),
                "component_key": spec["component_key"],
                "component_family": spec["component_family"],
                "payer_sector": spec["payer_sector"],
                "recipient_sector": spec["recipient_sector"],
                "holder_sector": spec["holder_sector"],
                "source_field": spec["source_field"],
                "baseline_cashflow_bil": _fmt(_quantize_output(spec["baseline"])),
                "shock_cashflow_bil": _fmt(_quantize_output(spec["baseline"] + spec["delta_cashflow"])),
                "delta_cashflow_bil": _fmt(_quantize_output(spec["delta_cashflow"])),
                "basis_stock_bil": _fmt(_quantize_output(spec["basis_stock"])),
                "rate_delta_bps_year": "100",
                "demand_translation_share": _fmt(spec["demand_share"]),
                "delta_current_demand_support_bil": _fmt(_quantize_output(spec["support"])),
                "sign_in_net": _fmt(spec["sign"]),
                "enters_gross_public_interest": str(spec["gross"]).lower(),
                "enters_selected_net_public_interest": str(spec["selected"]).lower(),
                "overlap_guard_key": f"public_interest::{spec['component_key']}",
                "tdc_overlap_policy": (
                    "excluded_from_tdc_default"
                    if spec["selected"] or spec["component_key"] in {
                        "foreign_holder_leakage",
                        "tdc_overlap_shield",
                    }
                    else "not_applicable_memo"
                ),
                "blocked_use": blocked,
                "claim_boundary": claim_boundary,
            }
        )
    return rows


def _operating_rate_delta(
    *,
    basis: Decimal,
    support: Decimal,
    short_rate: Decimal,
    spread: Decimal,
) -> tuple[Decimal, bool]:
    baseline_interest = basis * (short_rate + spread) / Decimal("100")
    if baseline_interest == 0:
        return Decimal("0"), False
    support_multiplier = support / baseline_interest
    return basis * Decimal("0.01") * support_multiplier, True


def _selected_summary_rows_from_components(
    component_rows: Sequence[Mapping[str, str]],
    forecast_public_interest_path: Path,
) -> list[dict[str, str]]:
    if not component_rows:
        return []
    baseline_by_key = _selected_baseline_by_key(forecast_public_interest_path)
    by_delta_id: dict[str, list[Mapping[str, str]]] = {}
    for row in component_rows:
        if row["selected_component_allowed"] == "true":
            by_delta_id.setdefault(row["marginal_public_interest_delta_row_id"], []).append(row)
    rows = []
    for delta_id, components in sorted(by_delta_id.items()):
        first = components[0]
        component_by_key = {row["component_key"]: row for row in components}
        baseline = baseline_by_key.get(
            (
                first["period_object"],
                first["period"],
                first["state_id"],
            ),
            Decimal("0"),
        )
        if first["period_object"] == "current":
            legacy = component_by_key["legacy_interest_replacement_memo"]
            baseline = Decimal(legacy["baseline_cashflow_bil"])
        values = _component_summary_values(component_by_key)
        delta = values["delta_public_interest_net_block_bil"]
        rows.append(
            {
                "marginal_public_interest_delta_row_id": delta_id,
                "period_object": first["period_object"],
                "period": first["period"],
                "horizon": first["horizon"],
                "state_id": first["state_id"],
                "scenario_id": first["scenario_id"],
                "baseline_scenario_id": first["baseline_scenario_id"],
                "shock_scenario_id": first["shock_scenario_id"],
                "shock_path_id": first["shock_path_id"],
                "public_interest_pair_source_id": (
                    "marginal_public_interest_components.selected_net_block"
                ),
                "source_mode": first["source_mode"],
                "assumption_mode": first["assumption_mode"],
                "evidence_mode_enabled": first["evidence_mode_enabled"],
                "public_interest_baseline_bil": _fmt(_quantize_output(baseline)),
                "public_interest_shock_bil": _fmt(_quantize_output(baseline + delta)),
                "delta_public_interest_net_block_bil": _fmt(_quantize_output(delta)),
                **{
                    key: _fmt(_quantize_output(value))
                    for key, value in values.items()
                },
                "source_component_mode": _summary_source_component_mode(first),
                "selected_debt_service_mode": _summary_debt_service_mode(first),
                "selected_operating_liability_mode": "stock_times_100bp",
                "selected_remittance_mode": "assumption_mode_remittance_absorber",
                "selected_absorber_mode": "baseline_surface_tax_fiscal_tga_rates",
                "holder_split_basis": _summary_holder_split_basis(first),
                "same_state_delta_status": PASS_SAME_STATE_STATUS,
                "selected_pi_delta_allowed": "true",
                "selection_gate_status": PASS_ASSUMPTION_MODE_STATUS,
                "allowed_use": "selected_marginal_public_interest_delta_assumption_mode",
                "blocked_use": (
                    "canonical_headline_promotion_without_final_gate;"
                    "old_current_benchmark_n"
                    if first["period_object"] == "current"
                    else "canonical_headline_promotion_without_final_gate"
                ),
                "claim_boundary": first["claim_boundary"],
            }
        )
    return rows


def _plus100_pair_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    rows = _read_csv(path)
    for row in rows:
        missing = set(MARGINAL_PUBLIC_INTEREST_DELTA_FIELDS) - set(row)
        for field in missing:
            row[field] = ""
        if set(row) != set(MARGINAL_PUBLIC_INTEREST_DELTA_FIELDS):
            raise MarginalPublicInterestError(
                "plus100 public-interest pair input schema mismatch"
            )
    return rows


def _forecast_debt_service_values_from_input(
    input_row: Mapping[str, str] | None,
) -> dict[str, Decimal] | None:
    if input_row is None:
        return None
    if input_row.get("selected_debt_repricing_replacement_allowed") != "true":
        return None
    required = {
        "marketable_debt_stock_bil",
        "repricing_share",
        "floating_rate_share",
        "domestic_nonbank_holder_share",
        "bank_holder_share",
        "pass_through",
        "direct_treasury_current_demand_share",
        "bank_treasury_current_demand_share",
    }
    if any(not input_row.get(field) for field in required):
        return None
    stock = Decimal(input_row["marketable_debt_stock_bil"])
    repricing_share = Decimal(input_row["repricing_share"])
    floating_share = Decimal(input_row["floating_rate_share"])
    pass_through = Decimal(input_row["pass_through"])
    domestic_share = Decimal(input_row["domestic_nonbank_holder_share"])
    bank_share = Decimal(input_row["bank_holder_share"])
    direct_demand = Decimal(input_row["direct_treasury_current_demand_share"])
    bank_demand = Decimal(input_row["bank_treasury_current_demand_share"])
    repricing_cashflow = stock * (repricing_share + floating_share) * RATE_DELTA_FACTOR * pass_through
    direct_cashflow = repricing_cashflow * domestic_share
    bank_cashflow = repricing_cashflow * bank_share
    return {
        "basis_stock": stock,
        "direct_cashflow": direct_cashflow,
        "direct_delta": direct_cashflow * direct_demand,
        "direct_demand_share": direct_demand,
        "bank_cashflow": bank_cashflow,
        "bank_delta": bank_cashflow * bank_demand,
        "bank_demand_share": bank_demand,
    }


def _summary_source_component_mode(first: Mapping[str, str]) -> str:
    if first["period_object"] == "current":
        return "assumption_mode_explicit_current_component_input"
    if first["period_object"] == "historical":
        return "assumption_mode_explicit_historical_replay_component_input"
    if "forecast_debt_stock_maturity_repricing" in first["claim_boundary"]:
        return "assumption_mode_explicit_forecast_debt_stock_maturity_repricing"
    return "assumption_mode_local_rate_slope_from_prior_surface"


def _summary_debt_service_mode(first: Mapping[str, str]) -> str:
    if first["period_object"] == "current":
        return "explicit_current_repricing_base_input"
    if first["period_object"] == "historical":
        return "explicit_historical_replay_state_repricing_base_input"
    if "forecast_debt_stock_maturity_repricing" in first["claim_boundary"]:
        return "explicit_forecast_debt_stock_maturity_repricing"
    return "local_rate_slope_rate_up_down_25bp"


def _summary_holder_split_basis(first: Mapping[str, str]) -> str:
    if first["period_object"] == "current":
        return "explicit_current_component_input"
    if first["period_object"] == "historical":
        return "explicit_historical_replay_quarterly_inputs"
    if "forecast_debt_stock_maturity_repricing" in first["claim_boundary"]:
        return "explicit_forecast_debt_stock_maturity_assumption_input"
    return "embedded_in_prior_surface_no_second_haircut"


def _debt_repricing_audit_row(
    key: tuple[str, str, str, str],
    direct: Mapping[str, str],
    bank: Mapping[str, str],
    input_row: Mapping[str, str] | None,
) -> dict[str, str]:
    period_object, period, state_id, shock_path_id = key
    local_direct = Decimal(direct["delta_current_demand_support_bil"])
    local_bank = Decimal(bank["delta_current_demand_support_bil"])
    if input_row is not None and input_row.get("selected_debt_repricing_replacement_allowed") == "true":
        stock = Decimal(input_row["marketable_debt_stock_bil"])
        repricing_share = Decimal(input_row["repricing_share"])
        floating_share = Decimal(input_row["floating_rate_share"])
        pass_through = Decimal(input_row["pass_through"])
        domestic_share = Decimal(input_row["domestic_nonbank_holder_share"])
        bank_share = Decimal(input_row["bank_holder_share"])
        foreign_share = Decimal(input_row["foreign_holder_share"])
        direct_demand = Decimal(input_row["direct_treasury_current_demand_share"])
        bank_demand = Decimal(input_row["bank_treasury_current_demand_share"])
        repricing_cashflow = stock * (repricing_share + floating_share) * RATE_DELTA_FACTOR * pass_through
        explicit_direct = repricing_cashflow * domestic_share * direct_demand
        explicit_bank = repricing_cashflow * bank_share * bank_demand
        replacement = True
        status = "pass_explicit_debt_repricing_replacement_candidate"
    else:
        stock = Decimal(input_row["marketable_debt_stock_bil"]) if input_row and input_row.get("marketable_debt_stock_bil") else Decimal("0")
        repricing_share = Decimal(input_row["repricing_share"]) if input_row and input_row.get("repricing_share") else Decimal("0")
        floating_share = Decimal(input_row["floating_rate_share"]) if input_row and input_row.get("floating_rate_share") else Decimal("0")
        pass_through = Decimal(input_row["pass_through"]) if input_row and input_row.get("pass_through") else Decimal("0")
        domestic_share = Decimal(input_row["domestic_nonbank_holder_share"]) if input_row and input_row.get("domestic_nonbank_holder_share") else Decimal("0")
        bank_share = Decimal(input_row["bank_holder_share"]) if input_row and input_row.get("bank_holder_share") else Decimal("0")
        foreign_share = Decimal(input_row["foreign_holder_share"]) if input_row and input_row.get("foreign_holder_share") else Decimal("0")
        direct_demand = Decimal(input_row["direct_treasury_current_demand_share"]) if input_row and input_row.get("direct_treasury_current_demand_share") else Decimal("0")
        bank_demand = Decimal(input_row["bank_treasury_current_demand_share"]) if input_row and input_row.get("bank_treasury_current_demand_share") else Decimal("0")
        explicit_direct = Decimal("0")
        explicit_bank = Decimal("0")
        replacement = False
        status = (
            input_row.get("selection_status", "fail_closed_no_explicit_debt_repricing_input")
            if input_row
            else "fail_closed_no_explicit_debt_repricing_input"
        )
    direct_gap = explicit_direct - local_direct if replacement else Decimal("0")
    bank_gap = explicit_bank - local_bank if replacement else Decimal("0")
    return {
        "public_interest_debt_repricing_audit_row_id": f"public_interest_debt_repricing_audit::{period_object}::{period}::{state_id}",
        "period_object": period_object,
        "period": period,
        "horizon": direct["horizon"],
        "state_id": state_id,
        "shock_path_id": shock_path_id,
        "selected_debt_service_mode": (
            "explicit_current_repricing_base_input"
            if period_object == "current"
            else "local_rate_slope_rate_up_down_25bp"
        ),
        "marketable_debt_stock_bil": _fmt(_quantize_output(stock)) if input_row else "",
        "repricing_share": _fmt(repricing_share) if input_row else "",
        "floating_rate_share": _fmt(floating_share) if input_row else "",
        "domestic_nonbank_holder_share": _fmt(domestic_share) if input_row else "",
        "bank_holder_share": _fmt(bank_share) if input_row else "",
        "foreign_holder_share": _fmt(foreign_share) if input_row else "",
        "pass_through": _fmt(pass_through) if input_row else "",
        "direct_treasury_current_demand_share": _fmt(direct_demand) if input_row else "",
        "bank_treasury_current_demand_share": _fmt(bank_demand) if input_row else "",
        "explicit_direct_treasury_delta_bil": (
            _fmt(_quantize_output(explicit_direct)) if replacement else ""
        ),
        "explicit_bank_treasury_delta_bil": (
            _fmt(_quantize_output(explicit_bank)) if replacement else ""
        ),
        "local_slope_direct_treasury_delta_bil": _fmt(_quantize_output(local_direct)),
        "local_slope_bank_treasury_delta_bil": _fmt(_quantize_output(local_bank)),
        "direct_gap_bil": _fmt(_quantize_output(direct_gap)) if replacement else "",
        "bank_gap_bil": _fmt(_quantize_output(bank_gap)) if replacement else "",
        "replacement_recommended": str(replacement).lower(),
        "selection_status": status,
        "allowed_use": "public_interest_debt_repricing_audit",
        "blocked_use": (
            "" if replacement else "selected_public_interest_replacement;selected_rw_m_rebuild"
        ),
        "claim_boundary": (
            "audit_only_replacement_candidate_not_applied_to_selected_pi"
            if replacement
            else "selected_pi_retains_existing_debt_service_mode_until_explicit_repricing_route_passes"
        ),
    }


def _debt_repricing_input_by_key(
    path: Path | None,
) -> dict[tuple[str, str, str, str], Mapping[str, str]]:
    if path is None or not path.exists():
        return {}
    return {
        (row.get("period_object", ""), row.get("period", ""), row.get("state_id", ""), row.get("shock_path_id", "")): row
        for row in _read_csv(path)
        if row.get("period_object") and row.get("period") and row.get("state_id") and row.get("shock_path_id")
    }


def _missing_period_rows(*, include_current: bool) -> list[dict[str, str]]:
    pairs = [("historical", "missing")]
    if include_current:
        pairs.insert(0, ("current", "2026"))
    return [
        {
            "marginal_public_interest_delta_row_id": f"marginal_public_interest_delta::{period_object}::missing",
            "period_object": period_object,
            "period": period,
            "horizon": "annual_h1_100bp_year",
            "state_id": f"{period_object}_state_missing",
            "scenario_id": "missing_plus_100bp_year_pair",
            "baseline_scenario_id": "missing",
            "shock_scenario_id": "missing_plus_100bp_year_pair",
            "shock_path_id": PLUS100_SHOCK_PATH_ID,
            "public_interest_pair_source_id": "missing_plus_100bp_year_pair",
            "source_mode": "missing",
            "assumption_mode": "false",
            "evidence_mode_enabled": "false",
            "public_interest_baseline_bil": "",
            "public_interest_shock_bil": "",
            "delta_public_interest_net_block_bil": "",
            **_blank_summary_component_fields(),
            "same_state_delta_status": "fail_closed_missing_same_state_public_interest_delta",
            "selected_pi_delta_allowed": "false",
            "selection_gate_status": "fail_closed_missing_plus_100bp_year_public_interest_pair",
            "allowed_use": "input_staging_gap",
            "blocked_use": "selected_marginal_n;selected_rw_m;canonical_headline_promotion",
            "claim_boundary": "no_selected_public_interest_delta_without_same_state_pair",
        }
        for period_object, period in pairs
    ]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return numerator / denominator


def _forecast_operating_values(row: Mapping[str, str], liability_key: str) -> dict[str, Decimal]:
    if liability_key == "iorb":
        stock = (
            Decimal(row["cbo_nominal_gdp_bil"])
            * Decimal(row["reserve_balance_stock_gdp_share"])
        )
        base_rate = (
            Decimal(row["cbo_short_rate_pct"])
            + Decimal(row["iorb_rate_spread_vs_cbo_short_rate_pct"])
        )
        expected_basis = Decimal(row["projected_iorb_interest_basis_bil"])
        support = Decimal(row["projected_iorb_current_demand_support_bil"])
    elif liability_key == "on_rrp":
        stock = (
            Decimal(row["cbo_nominal_gdp_bil"])
            * Decimal(row["on_rrp_stock_gdp_share"])
        )
        base_rate = (
            Decimal(row["cbo_short_rate_pct"])
            + Decimal(row["on_rrp_rate_spread_vs_cbo_short_rate_pct"])
        )
        expected_basis = Decimal(row["projected_on_rrp_interest_basis_bil"])
        support = Decimal(row["projected_on_rrp_current_demand_support_bil"])
    else:
        raise MarginalPublicInterestError(f"unknown liability key: {liability_key}")
    baseline_cashflow = stock * base_rate / Decimal("100")
    if abs(baseline_cashflow - expected_basis) > Decimal("0.000001"):
        raise MarginalPublicInterestError(
            f"{liability_key} stock/rate baseline interest reconciliation failed"
        )
    demand_share = _safe_ratio(support, baseline_cashflow)
    delta_cashflow = stock * RATE_DELTA_FACTOR
    return {
        "basis_stock": stock,
        "baseline_cashflow": baseline_cashflow,
        "delta_cashflow": delta_cashflow,
        "demand_share": demand_share,
        "delta_support": delta_cashflow * demand_share,
    }


def _explicit_operating_values(
    *,
    stock: Decimal,
    pass_through: Decimal,
    demand_share: Decimal,
) -> dict[str, Decimal]:
    delta_cashflow = stock * RATE_DELTA_FACTOR * pass_through
    return {
        "basis_stock": stock,
        "baseline_cashflow": Decimal("0"),
        "delta_cashflow": delta_cashflow,
        "demand_share": demand_share,
        "delta_support": delta_cashflow * demand_share,
    }


def _component_spec(
    *,
    key: str,
    family: str,
    payer: str,
    recipient: str,
    holder: str,
    source_field: str,
    baseline: Decimal,
    delta_cashflow: Decimal,
    basis: Decimal,
    demand_share: Decimal,
    support: Decimal,
    sign: Decimal,
    gross: bool,
    selected: bool,
) -> dict[str, Decimal | str | bool]:
    return {
        "component_key": key,
        "component_family": family,
        "payer_sector": payer,
        "recipient_sector": recipient,
        "holder_sector": holder,
        "source_field": source_field,
        "baseline": baseline,
        "delta_cashflow": delta_cashflow,
        "basis_stock": basis,
        "demand_share": demand_share,
        "support": support,
        "sign": sign,
        "gross": gross,
        "selected": selected,
    }


def _component_summary_values(
    component_by_key: Mapping[str, Mapping[str, str]],
) -> dict[str, Decimal]:
    def support(key: str) -> Decimal:
        return Decimal(component_by_key[key]["delta_current_demand_support_bil"])

    def cashflow(key: str) -> Decimal:
        return Decimal(component_by_key[key]["delta_cashflow_bil"])

    direct = support("direct_treasury_domestic_nonbank")
    bank = support("bank_treasury")
    iorb_cashflow = cashflow("iorb_reserves")
    iorb_support = support("iorb_reserves")
    on_rrp_cashflow = cashflow("on_rrp")
    on_rrp_support = support("on_rrp")
    current_remittance = cashflow("remittance_current_reduction") * Decimal("-1")
    future_remittance = cashflow("remittance_future_deferred_asset") * Decimal("-1")
    current_remittance_support = support("remittance_current_reduction")
    future_remittance_support = support("remittance_future_deferred_asset")
    gross = direct + bank + iorb_support + on_rrp_support + current_remittance_support + future_remittance_support
    tax = support("tax_timing")
    before = gross - tax
    fiscal = support("fiscal_offset")
    tga = support("tga_liquidity")
    net = before - fiscal - tga
    return {
        "delta_direct_treasury_current_demand_support_bil": direct,
        "delta_bank_treasury_current_demand_support_bil": bank,
        "delta_iorb_interest_cashflow_bil": iorb_cashflow,
        "delta_projected_iorb_current_demand_support_bil": iorb_support,
        "delta_on_rrp_interest_cashflow_bil": on_rrp_cashflow,
        "delta_projected_on_rrp_current_demand_support_bil": on_rrp_support,
        "delta_fed_interest_expense_bil": iorb_cashflow + on_rrp_cashflow,
        "delta_current_remittance_reduction_bil": current_remittance,
        "delta_future_remittance_deferred_asset_addition_bil": future_remittance,
        "delta_projected_current_remittance_demand_offset_bil": current_remittance_support,
        "delta_projected_future_remittance_drag_demand_offset_bil": future_remittance_support,
        "delta_gross_public_interest_current_demand_support_bil": gross,
        "delta_interest_income_tax_timing_drag_bil": tax,
        "delta_net_interest_before_fiscal_tga_offsets_bil": before,
        "delta_fiscal_offset_bil": fiscal,
        "delta_tga_liquidity_offset_bil": tga,
        "delta_foreign_holder_leakage_bil": cashflow("foreign_holder_leakage"),
        "tdc_overlap_shield_bil": cashflow("tdc_overlap_shield"),
        "delta_public_interest_net_block_bil": net,
    }


def _summary_component_net(row: Mapping[str, str]) -> Decimal:
    gross = Decimal(row["delta_gross_public_interest_current_demand_support_bil"])
    tax = Decimal(row["delta_interest_income_tax_timing_drag_bil"])
    fiscal = Decimal(row["delta_fiscal_offset_bil"])
    tga = Decimal(row["delta_tga_liquidity_offset_bil"])
    return gross - tax - fiscal - tga


def _selected_baseline_by_key(path: Path) -> dict[tuple[str, str, str], Decimal]:
    out: dict[tuple[str, str, str], Decimal] = {}
    if not path.exists():
        return out
    for row in _read_csv(path):
        if row.get("scenario_id") == BASELINE_FORECAST_SCENARIO_ID:
            year = row["fiscal_year"]
            out[("forecast", year, f"cbo_baseline_state::{year}")] = Decimal(
                row["net_interest_after_fiscal_tga_offsets_bil"]
            )
    return out


def _selected_delta_row_id(period_object: str, period: str, scenario_id: str) -> str:
    return f"marginal_public_interest_delta::{period_object}::{period}::{scenario_id}"


def _blank_summary_component_fields() -> dict[str, str]:
    fields = {
        field
        for field in MARGINAL_PUBLIC_INTEREST_DELTA_FIELDS
        if field.startswith("delta_")
        and field != "delta_public_interest_net_block_bil"
    }
    fields.update(
        {
            "tdc_overlap_shield_bil",
            "source_component_mode",
            "selected_debt_service_mode",
            "selected_operating_liability_mode",
            "selected_remittance_mode",
            "selected_absorber_mode",
            "holder_split_basis",
        }
    )
    return {field: "" for field in fields}


def _remittance_by_year(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    return {row["fiscal_year"]: row for row in _read_csv(path)}


def _remittance_absorber_assumptions_by_key(
    path: Path | None,
) -> dict[tuple[str, str, str], Mapping[str, str]]:
    if path is None or not path.exists():
        return {}
    return {
        (row.get("period_object", ""), row.get("period", ""), row.get("state_id", "")): row
        for row in _read_csv(path)
        if row.get("period_object") and row.get("period") and row.get("state_id")
    }


def _remittance_absorber_share(
    remittance_absorber_by_key: Mapping[tuple[str, str, str], Mapping[str, str]],
    *,
    period_object: str,
    period: str,
    state_id: str,
    field: str,
    fallback: Decimal,
) -> Decimal:
    row = remittance_absorber_by_key.get((period_object, period, state_id))
    if row is None:
        return fallback
    if row.get("selected_remittance_absorber_assumption_allowed") != "true":
        return fallback
    value = row.get(field, "")
    return Decimal(value) if value else fallback


def _validate_current_input(row: Mapping[str, str]) -> None:
    required = {
        "period_object",
        "period",
        "horizon",
        "state_id",
        "scenario_id",
        "baseline_scenario_id",
        "shock_scenario_id",
        "shock_path_id",
        "shock_bps_year",
        "nominal_gdp_bil",
        "baseline_public_interest_support_bil",
        "treasury_repricing_base_bil",
        "treasury_repricing_pass_through",
        "domestic_nonbank_treasury_holder_share",
        "bank_treasury_holder_share",
        "foreign_treasury_holder_share",
        "direct_treasury_current_demand_share",
        "bank_treasury_current_demand_share",
        "reserve_balance_stock_bil",
        "iorb_pass_through_scale",
        "iorb_recipient_current_demand_share",
        "on_rrp_stock_bil",
        "on_rrp_pass_through_scale",
        "on_rrp_recipient_current_demand_share",
        "remittance_capacity_bil",
        "remittance_offset_share",
        "current_remittance_demand_share",
        "future_remittance_drag_current_demand_share",
        "tax_timing_rate",
        "fiscal_offset_rate",
        "tga_liquidity_offset_rate",
        "tdc_overlap_shield_bil",
        "holder_split_basis",
        "source_mode",
        "assumption_mode",
        "evidence_mode_enabled",
        "selected_input_allowed",
        "allowed_use",
        "blocked_use",
        "claim_boundary",
    }
    missing = required - set(row)
    if missing:
        raise MarginalPublicInterestError(
            f"current component input missing columns: {sorted(missing)}"
        )
    if row["shock_path_id"] != PLUS100_SHOCK_PATH_ID or row["shock_bps_year"] != "100":
        raise MarginalPublicInterestError("current component input must use plus_100bp_year")
    if row["selected_input_allowed"] != "true":
        raise MarginalPublicInterestError("current component input is not selected")
    shares = (
        Decimal(row["domestic_nonbank_treasury_holder_share"])
        + Decimal(row["bank_treasury_holder_share"])
        + Decimal(row["foreign_treasury_holder_share"])
    )
    if abs(shares - Decimal("1")) > Decimal("0.000001"):
        raise MarginalPublicInterestError("current holder shares must sum to 1")


def _quantize_output(value: Decimal) -> Decimal:
    return value.quantize(OUTPUT_QUANTUM)


def _fmt(value: Decimal) -> str:
    return format(value, "f")
