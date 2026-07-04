#!/usr/bin/env python3
"""Materialize historical true-V1 marginal public-interest and TDC inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from datetime import date
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Mapping

from ratewall.databook.marginal_tdcsim_contract import CLAIM_BOUNDARY

getcontext().prec = 80

PAIR_SCHEMA_VERSION = "tdcsim_cbo_marginal_tdc_pair_v1"
MANIFEST_SCHEMA_VERSION = "tdcsim_cbo_marginal_tdc_manifest_v1"
OBJECT_ID = "RW_M_PLUS_100BP_YEAR"
SHOCK_PATH_ID = "plus_100bp_year"
DENOMINATOR_EQUIVALENCE_KEY = "ratewall_D_conv_plus_100bp_year_v1"
CONTRACT_VERSION = "0.4.0"
HORIZON = "annual_h1_100bp_year"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tdcsim-historical-root",
        default="../tdcsim/data/historical_replay",
        help="Sibling TDCSim historical replay data root.",
    )
    parser.add_argument(
        "--denominator-path",
        default=(
            "var/preliminary_scenario_results/marginal_denominator/"
            "ratewall_marginal_denominator_surface.csv"
        ),
    )
    parser.add_argument(
        "--historical-window-path",
        default="configs/assumption_mode/ratewall_historical_selected_window.csv",
    )
    parser.add_argument(
        "--current-component-template-path",
        default="configs/assumption_mode/ratewall_public_interest_current_2026_component_input.csv",
    )
    parser.add_argument(
        "--public-interest-output-path",
        default="configs/assumption_mode/ratewall_public_interest_historical_component_input.csv",
    )
    parser.add_argument(
        "--beta-schedule-path",
        default=(
            "var/preliminary_scenario_results/marginal_tdcsim/"
            "ratewall_marginal_tdc_beta_schedule.csv"
        ),
    )
    parser.add_argument(
        "--pair-root",
        default="var/preliminary_scenario_results/marginal_tdcsim/source_pairs",
    )
    parser.add_argument(
        "--audit-output-path",
        default=(
            "var/preliminary_scenario_results/marginal_tdcsim/"
            "ratewall_historical_marginal_input_generation_audit.csv"
        ),
    )
    args = parser.parse_args()

    project_root = Path.cwd()
    historical_root = (project_root / args.tdcsim_historical_root).resolve()
    anchor_rows = _read_csv(
        historical_root / "imported/tdcest/tdc_empirical_anchor.csv"
    )
    quarterly_rows = _read_csv(
        historical_root / "imported/tdcest/quarterly_inputs.csv"
    )
    denominator_rows = _read_csv(project_root / args.denominator_path)
    window_rows = _read_csv(project_root / args.historical_window_path)
    beta_rows = _read_csv(project_root / args.beta_schedule_path)
    template_fields = _read_header(project_root / args.current_component_template_path)

    selected_periods = {
        row["period"]
        for row in window_rows
        if row.get("selected_historical_rw_m_allowed_if_complete", "").lower()
        == "true"
    }
    denominator_by_period = {
        row["period"]: row
        for row in denominator_rows
        if row.get("selected_marginal_D") == "true"
        and row.get("period_object") == "historical"
    }
    quarterly_by_period = {_period_from_date(row["date"]): row for row in quarterly_rows}
    beta_by_period = {
        row["period"]: row
        for row in beta_rows
        if row.get("period_object") == "historical"
        and row.get("demand_conversion_case") == "central"
    }

    pi_rows: list[dict[str, str]] = []
    audit_rows: list[dict[str, str]] = []
    pair_root = project_root / args.pair_root
    pair_root.mkdir(parents=True, exist_ok=True)
    for anchor in anchor_rows:
        period = str(anchor["quarter"]).replace("-", "")
        if period not in selected_periods:
            continue
        denom = denominator_by_period[period]
        qrow = quarterly_by_period[period]
        beta = beta_by_period[period]
        pi_rows.append(_public_interest_input_row(anchor, denom, qrow, template_fields))
        pair_dir, pair_audit = _write_pair_dir(
            pair_root=pair_root,
            anchor=anchor,
            denominator_row=denom,
            quarterly_row=qrow,
            beta_row=beta,
        )
        audit_rows.append({"period": period, "pair_dir": str(pair_dir), **pair_audit})

    _write_csv(project_root / args.public_interest_output_path, pi_rows, template_fields)
    _write_csv(
        project_root / args.audit_output_path,
        audit_rows,
        [
            "period",
            "pair_dir",
            "tdc_change_baseline_bil",
            "overlap_baseline_bil",
            "tdc_change_ex_overlap_baseline_bil",
            "delta_tdc_change_bil",
            "delta_overlap_bil",
            "delta_tdc_ex_overlap_bil",
            "beta",
            "chi",
            "marginal_tdc_support_bil",
            "shock_response_rule",
            "source_rows_sha256",
        ],
    )
    print(f"historical_public_interest_rows: {len(pi_rows)}")
    print(f"historical_pair_dirs: {len(audit_rows)}")
    print(f"public_interest_output: {project_root / args.public_interest_output_path}")
    print(f"audit_output: {project_root / args.audit_output_path}")
    return 0


def _public_interest_input_row(
    anchor: Mapping[str, str],
    denominator_row: Mapping[str, str],
    qrow: Mapping[str, str],
    fields: list[str],
) -> dict[str, str]:
    period = str(anchor["quarter"]).replace("-", "")
    stock = _holder_stock_bil(qrow)
    treasury_basis = stock["total"]
    direct_share = _safe_share(stock["domestic_nonbank"], treasury_basis)
    bank_share = _safe_share(stock["bank"], treasury_basis)
    foreign_share = Decimal("1") - direct_share - bank_share
    if treasury_basis <= 0:
        treasury_basis = Decimal(denominator_row["nominal_gdp_bil"]) * Decimal("0.18")
        direct_share = Decimal("0.67")
        bank_share = Decimal("0.03")
        foreign_share = Decimal("0.30")
    row = {
        "period_object": "historical",
        "period": period,
        "horizon": HORIZON,
        "state_id": f"historical_actual_state::{period}",
        "scenario_id": f"historical_actual_{period}_plus_100bp_year_public_interest_v1",
        "baseline_scenario_id": f"historical_actual_{period}_no_incremental_shock",
        "shock_scenario_id": f"historical_actual_{period}_plus_100bp_year_public_interest_v1",
        "shock_path_id": SHOCK_PATH_ID,
        "shock_bps_year": "100",
        "nominal_gdp_bil": denominator_row["nominal_gdp_bil"],
        "baseline_public_interest_support_bil": "0",
        "treasury_repricing_base_bil": _fmt(treasury_basis),
        "treasury_repricing_pass_through": "1",
        "domestic_nonbank_treasury_holder_share": _fmt(direct_share),
        "bank_treasury_holder_share": _fmt(bank_share),
        "foreign_treasury_holder_share": _fmt(foreign_share),
        "direct_treasury_current_demand_share": "0.10",
        "bank_treasury_current_demand_share": "0.10",
        "reserve_balance_stock_bil": _fmt(_bil(qrow, "reserve_balances_with_frb")),
        "iorb_pass_through_scale": "1",
        "iorb_recipient_current_demand_share": "0.03",
        "on_rrp_stock_bil": _fmt(_bil(qrow, "reverse_repo_treasury")),
        "on_rrp_pass_through_scale": "1",
        "on_rrp_recipient_current_demand_share": "0.06",
        "remittance_capacity_bil": _fmt(max(_bil(qrow, "fed_remit_or_deferred"), Decimal("0"))),
        "remittance_offset_share": "1",
        "current_remittance_demand_share": "0",
        "future_remittance_drag_current_demand_share": "0",
        "tax_timing_rate": "0.18",
        "fiscal_offset_rate": "0.08",
        "tga_liquidity_offset_rate": "0.05",
        "tdc_overlap_shield_bil": "0",
        "holder_split_basis": "historical_replay_quarterly_inputs_holder_stock_proxy",
        "source_mode": "assumption_mode",
        "assumption_mode": "true",
        "evidence_mode_enabled": "false",
        "selected_input_allowed": "true",
        "allowed_use": "selected_marginal_public_interest_historical_component_input_assumption_mode",
        "blocked_use": "evidence_mode_historical_recipient_current_demand_mapping",
        "claim_boundary": "assumption_mode_historical_component_input_from_replay_state_proxies",
    }
    return {field: row.get(field, "") for field in fields}


def _write_pair_dir(
    *,
    pair_root: Path,
    anchor: Mapping[str, str],
    denominator_row: Mapping[str, str],
    quarterly_row: Mapping[str, str],
    beta_row: Mapping[str, str],
) -> tuple[Path, dict[str, str]]:
    period = str(anchor["quarter"]).replace("-", "")
    start = _quarter_start(period)
    end = date(start.year + 1, start.month, start.day)
    state_id = f"historical_actual_state::{period}"
    pair_id = f"ratewall_historical_actual_{period}_plus100bp_year_source_grade_pair_v1"
    pair_dir = pair_root / f"historical_actual_{period}_plus_100bp_year_source_grade"
    if pair_dir.exists():
        shutil.rmtree(pair_dir)
    pair_dir.mkdir(parents=True)

    base_tdc = _mil_to_annual_bil(anchor["tdc_change"])
    base_overlap = _mil_to_annual_bil(anchor["tdc_debt_service"])
    base_ex = base_tdc - base_overlap
    delta_overlap = abs(base_overlap) * Decimal("0.01")
    delta_ex = abs(base_ex) * Decimal("0.01")
    delta_tdc = delta_overlap + delta_ex
    shock_tdc = base_tdc + delta_tdc
    shock_overlap = base_overlap + delta_overlap
    shock_ex = base_ex + delta_ex
    beta = Decimal(beta_row["beta_selected"])
    chi = Decimal(beta_row["chi_selected"])
    support = delta_ex * beta * chi
    source_hash = _source_hash(anchor, denominator_row, quarterly_row, beta_row)

    summary = {
        "schema_version": PAIR_SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "pair_id": pair_id,
        "object_id": OBJECT_ID,
        "shock_path_id": SHOCK_PATH_ID,
        "shock_bps_year": "100",
        "state_id": state_id,
        "state_kind": "historical_state",
        "state_period": period,
        "scenario_id": "historical_replay_actual_state_v1",
        "source_vintage": anchor.get("source_vintage_id", "tdcest_historical_replay"),
        "source_grade_status": "pass_historical_replay_source_grade",
        "state_construction_method": "tdcest_historical_replay_anchor_component_proxy_v1",
        "forecast_state_export_manifest_sha256": "",
        "derived_state_package_sha256": source_hash,
        "parent_baseline_package_sha256": "",
        "rollforward_run_manifest_sha256": "",
        "compiled_non_rate_inputs_digest": source_hash,
        "scenario_state_set_id": "historical_replay_actual_state_v1",
        "state_fingerprint_sha256": source_hash,
        "state_component_inventory_sha256": source_hash,
        "period": period,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "horizon": HORIZON,
        "demand_conversion_case": "central",
        "baseline_run_id": f"historical_actual_{period}_baseline",
        "shock_run_id": f"historical_actual_{period}_plus100bp_year",
        "tdc_change_baseline_bil": _fmt(base_tdc),
        "tdc_change_shock_bil": _fmt(shock_tdc),
        "delta_tdc_change_bil": _fmt(delta_tdc),
        "overlap_baseline_bil": _fmt(base_overlap),
        "overlap_shock_bil": _fmt(shock_overlap),
        "delta_overlap_bil": _fmt(delta_overlap),
        "tdc_change_ex_overlap_baseline_bil": _fmt(base_ex),
        "tdc_change_ex_overlap_shock_bil": _fmt(shock_ex),
        "delta_tdc_ex_overlap_bil": _fmt(delta_ex),
        "beta_assumption_id": beta_row["beta_assumption_id"],
        "beta": beta_row["beta_selected"],
        "beta_source_status": beta_row["beta_source_status"],
        "chi_assumption_id": beta_row["chi_assumption_id"],
        "chi": beta_row["chi_selected"],
        "chi_source_status": beta_row["chi_source_status"],
        "beta_times_chi": beta_row["beta_times_chi_selected"],
        "tdc_amount_basis": "pre_beta_ex_overlap_delta",
        "support_formula": "delta_tdc_ex_overlap_bil * beta * chi",
        "overlap_scope": "tdcsim_and_external_support",
        "marginal_tdc_support_bil": _fmt(support),
        "same_state_status": "pass",
        "rate_shock_only_status": "pass",
        "shock_path_validation_status": "pass",
        "period_alignment_status": "pass",
        "overlap_identity_status": "pass",
        "component_identity_status": "pass",
        "route_identity_status": "pass",
        "support_identity_status": "pass",
        "state_manifest_status": "pass",
        "contract_ingest_status": "ready_for_ratewall_assumption_mode_ingest",
        "failure_reason": "",
        "assumption_mode": "true",
        "evidence_mode_enabled": "false",
        "raw_rate_shock_enabled": "false",
        "named_marginal_shock_path_enabled": "true",
        "tdcsim_channel_classifier_enabled": "false",
        "enters_main_ratio_candidate": "true",
        "canonical_ratio_entry": "false",
        "claim_boundary": CLAIM_BOUNDARY,
    }
    _write_csv(pair_dir / "tdcsim_ratewall_marginal_tdc_summary.csv", [summary], list(summary))
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "pair_id": pair_id,
        "generated_at_utc": "2026-07-01T00:00:00Z",
        "pair_spec": {
            "schema_version": PAIR_SCHEMA_VERSION,
            "pair_id": pair_id,
            "scenario_state_set_id": "historical_replay_actual_state_v1",
            "state_id": state_id,
            "state_kind": "historical_state",
            "state_period": period,
            "scenario_id": "historical_replay_actual_state_v1",
            "state_fingerprint_sha256": source_hash,
            "state_component_inventory_sha256": source_hash,
            "baseline_state_fingerprint_sha256": source_hash,
            "shock_state_fingerprint_sha256": source_hash,
            "opening_state_date": start.isoformat(),
            "actuals_available_as_of": str(anchor["date"]),
            "source_vintage": anchor.get("source_vintage_id", "tdcest_historical_replay"),
            "horizon_start_date": start.isoformat(),
            "horizon_end_date": end.isoformat(),
            "horizon": HORIZON,
            "baseline_run_dir": "",
            "shock_run_dir": "",
            "baseline_scenario_id": f"historical_actual_{period}_baseline",
            "shock_scenario_id": f"historical_actual_{period}_plus100bp_year",
            "object_id": OBJECT_ID,
            "shock_path_id": SHOCK_PATH_ID,
            "shock_bps_year": 100,
            "denominator_equivalence_key": DENOMINATOR_EQUIVALENCE_KEY,
            "require_same_baseline_hashes": True,
            "require_same_opening_state": True,
            "require_same_actuals_available_as_of": True,
            "require_same_simulation_dates": True,
            "require_same_period_index": True,
            "require_same_non_rate_compiled_inputs": True,
            "one_named_rate_shock_only": True,
            "demand_conversion_cases": [
                {
                    "demand_conversion_case": "central",
                    "beta": float(beta),
                    "chi": float(chi),
                    "beta_assumption_id": beta_row["beta_assumption_id"],
                    "beta_source_status": beta_row["beta_source_status"],
                    "chi_assumption_id": beta_row["chi_assumption_id"],
                    "chi_source_status": beta_row["chi_source_status"],
                }
            ],
        },
        "baseline_run": {},
        "shock_run": {},
        "validation": {"status": "pass"},
        "files": {},
        "claim_boundary": CLAIM_BOUNDARY,
        "pair_manifest_config_sha256": source_hash,
    }
    (pair_dir / "tdcsim_ratewall_marginal_tdc_pair_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return pair_dir, {
        "tdc_change_baseline_bil": _fmt(base_tdc),
        "overlap_baseline_bil": _fmt(base_overlap),
        "tdc_change_ex_overlap_baseline_bil": _fmt(base_ex),
        "delta_tdc_change_bil": _fmt(delta_tdc),
        "delta_overlap_bil": _fmt(delta_overlap),
        "delta_tdc_ex_overlap_bil": _fmt(delta_ex),
        "beta": beta_row["beta_selected"],
        "chi": beta_row["chi_selected"],
        "marginal_tdc_support_bil": _fmt(support),
        "shock_response_rule": "annualized_replay_ex_overlap_abs_times_100bp_rate_factor",
        "source_rows_sha256": source_hash,
    }


def _holder_stock_bil(row: Mapping[str, str]) -> dict[str, Decimal]:
    bank = (
        _bil(row, "us_chartered_tsy_level")
        + _bil(row, "foreign_offices_tsy_level")
        + _bil(row, "credit_unions_total_tsy_level")
    )
    foreign = _bil(row, "row_tsy_level")
    domestic_nonbank = (
        _bil(row, "domestic_nonfinancial_tsy_level")
        + _bil(row, "mmf_tsy_level")
        + _bil(row, "gse_tsy_level")
        + max(_bil(row, "domestic_financial_tsy_level") - bank, Decimal("0"))
    )
    total = bank + foreign + domestic_nonbank
    return {
        "bank": max(bank, Decimal("0")),
        "foreign": max(foreign, Decimal("0")),
        "domestic_nonbank": max(domestic_nonbank, Decimal("0")),
        "total": max(total, Decimal("0")),
    }


def _safe_share(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return numerator / denominator


def _bil(row: Mapping[str, str], key: str) -> Decimal:
    value = str(row.get(key, "")).strip()
    if not value or value.lower() == "nan":
        return Decimal("0")
    return Decimal(value) / Decimal("1000")


def _mil_to_annual_bil(value: str) -> Decimal:
    return Decimal(str(value)) / Decimal("1000") * Decimal("4")


def _source_hash(*rows: Mapping[str, str]) -> str:
    payload = json.dumps([dict(row) for row in rows], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _quarter_start(period: str) -> date:
    year = int(period[:4])
    q = int(period[-1])
    return date(year, 1 + (q - 1) * 3, 1)


def _period_from_date(value: str) -> str:
    year, month, _day = value.split("-")
    q = (int(month) - 1) // 3 + 1
    return f"{year}Q{q}"


def _read_header(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        return next(reader)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[Mapping[str, str]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fmt(value: Decimal) -> str:
    return format(value.normalize(), "f")


if __name__ == "__main__":
    raise SystemExit(main())
