#!/usr/bin/env python3
"""Build public-interest marginal delta staging artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.marginal_public_interest import (
    DEFAULT_CURRENT_COMPONENT_INPUT_PATH,
    DEFAULT_DEBT_REPRICING_INPUT_PATH,
    DEFAULT_FORECAST_PUBLIC_INTEREST_PATH,
    DEFAULT_FORECAST_REMITTANCE_PATH,
    DEFAULT_HISTORICAL_COMPONENT_INPUT_PATH,
    DEFAULT_PLUS100_PAIR_INPUT_PATH,
    DEFAULT_REMITTANCE_ABSORBER_ASSUMPTIONS_PATH,
    marginal_public_interest_component_rows,
    marginal_public_interest_debt_repricing_audit_rows,
    marginal_public_interest_delta_rows,
    write_marginal_public_interest_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--forecast-public-interest-path",
        default=str(DEFAULT_FORECAST_PUBLIC_INTEREST_PATH),
    )
    parser.add_argument(
        "--plus100-pair-input-path",
        default=str(DEFAULT_PLUS100_PAIR_INPUT_PATH),
        help="Optional same-state plus_100bp_year public-interest pair input CSV.",
    )
    parser.add_argument(
        "--current-component-input-path",
        default=str(DEFAULT_CURRENT_COMPONENT_INPUT_PATH),
        help="Current 2026 public-interest component assumption input CSV.",
    )
    parser.add_argument(
        "--historical-component-input-path",
        default=str(DEFAULT_HISTORICAL_COMPONENT_INPUT_PATH),
        help="Historical public-interest component assumption input CSV.",
    )
    parser.add_argument(
        "--forecast-remittance-path",
        default=str(DEFAULT_FORECAST_REMITTANCE_PATH),
        help="Forecast remittance baseline path for public-interest timing rows.",
    )
    parser.add_argument(
        "--remittance-absorber-assumptions-path",
        default=str(DEFAULT_REMITTANCE_ABSORBER_ASSUMPTIONS_PATH),
        help="Current/forecast remittance demand conversion assumptions.",
    )
    parser.add_argument(
        "--debt-repricing-input-path",
        default=str(DEFAULT_DEBT_REPRICING_INPUT_PATH),
        help="Optional explicit debt-stock/maturity repricing route input for audit.",
    )
    parser.add_argument(
        "--selected-forecast-debt-service-mode",
        default="local_rate_slope",
        choices=["local_rate_slope"],
        help="Selected forecast debt-service component mode.",
    )
    parser.add_argument(
        "--selected-remittance-demand-mode",
        default="memo_zero_current_demand",
        choices=["memo_zero_current_demand"],
        help="Selected remittance demand treatment.",
    )
    parser.add_argument(
        "--write-component-table",
        action="store_true",
        default=True,
        help="Write the component table next to the summary table.",
    )
    parser.add_argument(
        "--write-assumption-audit",
        action="store_true",
        default=False,
        help="Reserved for a later assumption-audit sidecar; no-op in this tranche.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/marginal_public_interest",
    )
    args = parser.parse_args()

    component_rows = marginal_public_interest_component_rows(
        forecast_public_interest_path=Path(args.forecast_public_interest_path),
        current_component_input_path=Path(args.current_component_input_path),
        historical_component_input_path=Path(args.historical_component_input_path),
        forecast_remittance_path=Path(args.forecast_remittance_path),
        remittance_absorber_assumptions_path=Path(
            args.remittance_absorber_assumptions_path
        ),
        debt_repricing_input_path=Path(args.debt_repricing_input_path),
    )
    rows = marginal_public_interest_delta_rows(
        forecast_public_interest_path=Path(args.forecast_public_interest_path),
        plus100_pair_input_path=Path(args.plus100_pair_input_path),
        current_component_input_path=Path(args.current_component_input_path),
        historical_component_input_path=Path(args.historical_component_input_path),
        forecast_remittance_path=Path(args.forecast_remittance_path),
        remittance_absorber_assumptions_path=Path(
            args.remittance_absorber_assumptions_path
        ),
        debt_repricing_input_path=Path(args.debt_repricing_input_path),
        component_rows=component_rows,
    )
    debt_repricing_audit = marginal_public_interest_debt_repricing_audit_rows(
        component_rows=component_rows,
        debt_repricing_input_path=Path(args.debt_repricing_input_path),
    )
    outputs = write_marginal_public_interest_outputs(
        Path(args.output_dir),
        delta_rows=rows,
        component_rows=component_rows if args.write_component_table else None,
        debt_repricing_audit_rows=debt_repricing_audit,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"delta_rows: {len(rows)}")
    print(f"component_rows: {len(component_rows)}")
    print(f"debt_repricing_audit_rows: {len(debt_repricing_audit)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
