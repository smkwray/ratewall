#!/usr/bin/env python3
"""Build selected marginal numerator fail-closed surface."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.marginal_selected_numerator import (
    DEFAULT_ADMITTED_RESIDUAL_PATH,
    DEFAULT_DENOMINATOR_PATH,
    DEFAULT_HISTORICAL_WINDOW_PATH,
    DEFAULT_PUBLIC_INTEREST_PATH,
    DEFAULT_SAFE_YIELD_PATH,
    DEFAULT_TDC_SUPPORT_PATH,
    marginal_overlap_audit_rows,
    marginal_selected_numerator_rows,
    write_marginal_selected_numerator_outputs,
)
from ratewall.databook.marginal_channel_parity import (
    channel_period_parity_rows,
    write_channel_period_parity_output,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--denominator-path", default=str(DEFAULT_DENOMINATOR_PATH))
    parser.add_argument("--public-interest-path", default=str(DEFAULT_PUBLIC_INTEREST_PATH))
    parser.add_argument("--tdc-support-path", default=str(DEFAULT_TDC_SUPPORT_PATH))
    parser.add_argument("--safe-yield-path", default=str(DEFAULT_SAFE_YIELD_PATH))
    parser.add_argument("--admitted-residual-path", default=str(DEFAULT_ADMITTED_RESIDUAL_PATH))
    parser.add_argument("--historical-window-path", default=str(DEFAULT_HISTORICAL_WINDOW_PATH))
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/marginal_numerator",
    )
    args = parser.parse_args()

    rows = marginal_selected_numerator_rows(
        denominator_path=Path(args.denominator_path),
        public_interest_path=Path(args.public_interest_path),
        tdc_support_path=Path(args.tdc_support_path),
        safe_yield_path=Path(args.safe_yield_path),
        admitted_residual_path=Path(args.admitted_residual_path),
        historical_window_path=Path(args.historical_window_path),
    )
    overlap = marginal_overlap_audit_rows(rows)
    outputs = write_marginal_selected_numerator_outputs(
        Path(args.output_dir),
        selected_rows=rows,
        overlap_rows=overlap,
    )
    outputs.update(
        write_channel_period_parity_output(
            Path(args.output_dir),
            parity_rows=channel_period_parity_rows(rows),
        )
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"selected_rows: {len(rows)}")
    print(f"overlap_rows: {len(overlap)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
