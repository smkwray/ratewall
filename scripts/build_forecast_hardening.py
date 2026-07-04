#!/usr/bin/env python3
"""Build forecast hardening sidecar artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.forecast_hardening import (
    DEFAULT_CBO_REVENUE_PATH,
    DEFAULT_DENOMINATOR_PARITY_DIR,
    DEFAULT_FORECAST_READOUT_DIR,
    forecast_assumption_ledger_rows,
    forecast_denominator_cd_robustness_rows,
    forecast_hardening_audit_rows,
    forecast_public_interest_sensitivity_rows,
    forecast_remittance_baseline_rows,
    forecast_residual_safe_yield_level_bound_rows,
    forecast_selected_d_rows,
    write_forecast_hardening_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--forecast-readout-dir",
        default=str(DEFAULT_FORECAST_READOUT_DIR),
        help="Directory containing forecast readout CSVs.",
    )
    parser.add_argument(
        "--denominator-parity-dir",
        default=str(DEFAULT_DENOMINATOR_PARITY_DIR),
        help="Directory containing denominator parity CSVs.",
    )
    parser.add_argument(
        "--cbo-revenue-path",
        default=str(DEFAULT_CBO_REVENUE_PATH),
        help="Optional local CBO revenue workbook path.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/forecast_hardening",
        help="Directory for forecast hardening outputs.",
    )
    args = parser.parse_args()
    forecast_dir = Path(args.forecast_readout_dir)
    denominator_dir = Path(args.denominator_parity_dir)

    selected_d_rows = forecast_selected_d_rows(
        forecast_readout_dir=forecast_dir,
        denominator_parity_dir=denominator_dir,
    )
    assumption_rows = forecast_assumption_ledger_rows()
    cd_rows = forecast_denominator_cd_robustness_rows(
        forecast_readout_dir=forecast_dir,
        denominator_parity_dir=denominator_dir,
    )
    public_interest_rows = forecast_public_interest_sensitivity_rows(
        forecast_readout_dir=forecast_dir,
    )
    remittance_rows = forecast_remittance_baseline_rows(
        forecast_readout_dir=forecast_dir,
        cbo_revenue_path=Path(args.cbo_revenue_path),
    )
    residual_rows = forecast_residual_safe_yield_level_bound_rows(
        forecast_readout_dir=forecast_dir,
    )
    audit_rows = forecast_hardening_audit_rows(
        selected_d_rows=selected_d_rows,
        cd_rows=cd_rows,
        remittance_rows=remittance_rows,
    )
    outputs = write_forecast_hardening_outputs(
        Path(args.output_dir),
        selected_d_rows=selected_d_rows,
        assumption_rows=assumption_rows,
        cd_rows=cd_rows,
        public_interest_rows=public_interest_rows,
        remittance_rows=remittance_rows,
        residual_rows=residual_rows,
        audit_rows=audit_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"selected_d_rows: {len(selected_d_rows)}")
    print(f"assumption_rows: {len(assumption_rows)}")
    print(f"cd_rows: {len(cd_rows)}")
    print(f"public_interest_rows: {len(public_interest_rows)}")
    print(f"remittance_rows: {len(remittance_rows)}")
    print(f"residual_rows: {len(residual_rows)}")
    print(f"audit_rows: {len(audit_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
