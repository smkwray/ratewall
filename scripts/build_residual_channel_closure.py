#!/usr/bin/env python3
"""Build residual/replacement channel closure artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.residual_channel_closure import (
    DEFAULT_FORECAST_READOUT_DIR,
    firm_liquidity_replacement_rows,
    residual_channel_admission_matrix_rows,
    residual_numerator_surface_rows,
    residual_safe_asset_drag_gate_rows,
    write_residual_channel_closure_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--forecast-readout-dir",
        default=str(DEFAULT_FORECAST_READOUT_DIR),
        help="Directory containing forecast readout CSVs.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/residual_channel_closure",
        help="Directory for residual channel closure outputs.",
    )
    args = parser.parse_args()
    forecast_dir = Path(args.forecast_readout_dir)

    firm_rows = firm_liquidity_replacement_rows(forecast_readout_dir=forecast_dir)
    safe_asset_rows = residual_safe_asset_drag_gate_rows(
        forecast_readout_dir=forecast_dir
    )
    matrix_rows = residual_channel_admission_matrix_rows(
        forecast_readout_dir=forecast_dir
    )
    residual_surface_rows = residual_numerator_surface_rows(
        forecast_readout_dir=forecast_dir
    )
    outputs = write_residual_channel_closure_outputs(
        Path(args.output_dir),
        firm_rows=firm_rows,
        safe_asset_rows=safe_asset_rows,
        matrix_rows=matrix_rows,
        residual_surface_rows=residual_surface_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"firm_rows: {len(firm_rows)}")
    print(f"safe_asset_rows: {len(safe_asset_rows)}")
    print(f"matrix_rows: {len(matrix_rows)}")
    print(f"residual_surface_rows: {len(residual_surface_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
