#!/usr/bin/env python3
"""Build comparable current/forecast/historical model review artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.comparable_model_surface import (
    DEFAULT_CORE_SUPPORT_DIR,
    DEFAULT_CURRENT_OVERLAY_DIR,
    DEFAULT_DENOMINATOR_PARITY_DIR,
    DEFAULT_FORECAST_HARDENING_DIR,
    DEFAULT_FORECAST_READOUT_DIR,
    DEFAULT_HISTORICAL_ADAPTER_DIR,
    DEFAULT_HISTORICAL_PROVISIONAL_DIR,
    DEFAULT_METHODOLOGY_PARITY_DIR,
    DEFAULT_REALIZED_SAFE_YIELD_DIR,
    DEFAULT_RESIDUAL_CLOSURE_DIR,
    DEFAULT_SOURCE_METHOD_DIR,
    comparable_channel_surface_rows,
    comparable_denominator_surface_rows,
    comparable_gap_priority_rows,
    comparable_model_readout_markdown,
    comparable_model_status_rows,
    comparable_review_summary_rows,
    write_comparable_model_surface_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--methodology-parity-dir",
        default=str(DEFAULT_METHODOLOGY_PARITY_DIR),
        help="Directory containing methodology parity CSVs.",
    )
    parser.add_argument(
        "--core-support-dir",
        default=str(DEFAULT_CORE_SUPPORT_DIR),
        help="Directory containing core support parity CSVs.",
    )
    parser.add_argument(
        "--denominator-parity-dir",
        default=str(DEFAULT_DENOMINATOR_PARITY_DIR),
        help="Directory containing denominator parity CSVs.",
    )
    parser.add_argument(
        "--residual-closure-dir",
        default=str(DEFAULT_RESIDUAL_CLOSURE_DIR),
        help="Directory containing residual closure CSVs.",
    )
    parser.add_argument(
        "--historical-adapter-dir",
        default=str(DEFAULT_HISTORICAL_ADAPTER_DIR),
        help="Directory containing historical comparable adapter CSVs.",
    )
    parser.add_argument(
        "--source-method-dir",
        default=str(DEFAULT_SOURCE_METHOD_DIR),
        help="Directory containing source/method matrix CSVs.",
    )
    parser.add_argument(
        "--forecast-readout-dir",
        default=str(DEFAULT_FORECAST_READOUT_DIR),
        help="Directory containing forecast readout CSVs.",
    )
    parser.add_argument(
        "--forecast-hardening-dir",
        default=str(DEFAULT_FORECAST_HARDENING_DIR),
        help="Directory containing forecast hardening CSVs.",
    )
    parser.add_argument(
        "--current-overlay-dir",
        default=str(DEFAULT_CURRENT_OVERLAY_DIR),
        help="Directory containing current benchmark and overlay CSVs.",
    )
    parser.add_argument(
        "--realized-safe-yield-dir",
        default=str(DEFAULT_REALIZED_SAFE_YIELD_DIR),
        help="Directory containing realized safe-yield gate CSVs.",
    )
    parser.add_argument(
        "--historical-provisional-dir",
        default=str(DEFAULT_HISTORICAL_PROVISIONAL_DIR),
        help="Directory containing historical provisional estimate CSVs.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/comparable_model_surface",
        help="Directory for comparable model surface outputs.",
    )
    args = parser.parse_args()

    channel_rows = comparable_channel_surface_rows(
        methodology_parity_dir=Path(args.methodology_parity_dir),
        core_support_dir=Path(args.core_support_dir),
        residual_closure_dir=Path(args.residual_closure_dir),
        historical_adapter_dir=Path(args.historical_adapter_dir),
    )
    denominator_rows = comparable_denominator_surface_rows(
        methodology_parity_dir=Path(args.methodology_parity_dir),
        denominator_parity_dir=Path(args.denominator_parity_dir),
        historical_adapter_dir=Path(args.historical_adapter_dir),
    )
    summary_rows = comparable_review_summary_rows(
        channel_rows=channel_rows,
        denominator_rows=denominator_rows,
    )
    model_status_rows = comparable_model_status_rows(
        source_method_dir=Path(args.source_method_dir),
        forecast_readout_dir=Path(args.forecast_readout_dir),
        forecast_hardening_dir=Path(args.forecast_hardening_dir),
        current_overlay_dir=Path(args.current_overlay_dir),
        historical_provisional_dir=Path(args.historical_provisional_dir),
    )
    gap_priority_rows = comparable_gap_priority_rows(
        source_method_dir=Path(args.source_method_dir),
        current_overlay_dir=Path(args.current_overlay_dir),
        realized_safe_yield_dir=Path(args.realized_safe_yield_dir),
        historical_provisional_dir=Path(args.historical_provisional_dir),
    )
    readout = comparable_model_readout_markdown(
        channel_rows=channel_rows,
        denominator_rows=denominator_rows,
        summary_rows=summary_rows,
        model_status_rows=model_status_rows,
        gap_priority_rows=gap_priority_rows,
    )
    outputs = write_comparable_model_surface_outputs(
        Path(args.output_dir),
        channel_rows=channel_rows,
        denominator_rows=denominator_rows,
        summary_rows=summary_rows,
        model_status_rows=model_status_rows,
        gap_priority_rows=gap_priority_rows,
        readout_markdown=readout,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"channel_rows: {len(channel_rows)}")
    print(f"denominator_rows: {len(denominator_rows)}")
    print(f"summary_rows: {len(summary_rows)}")
    print(f"model_status_rows: {len(model_status_rows)}")
    print(f"gap_priority_rows: {len(gap_priority_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
