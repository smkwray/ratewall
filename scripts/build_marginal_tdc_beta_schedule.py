#!/usr/bin/env python3
"""Build the selected marginal TDC beta/chi schedule."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.marginal_tdc_beta import (
    DEFAULT_DENOMINATOR_PATH,
    DEFAULT_HISTORICAL_WINDOW_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_SENSITIVITY_OUTPUT_PATH,
    write_beta_schedule,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--denominator-path", default=str(DEFAULT_DENOMINATOR_PATH))
    parser.add_argument(
        "--historical-window-path",
        default=str(DEFAULT_HISTORICAL_WINDOW_PATH),
    )
    parser.add_argument("--output-path", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument(
        "--sensitivity-output-path",
        default=str(DEFAULT_SENSITIVITY_OUTPUT_PATH),
    )
    args = parser.parse_args()

    outputs = write_beta_schedule(
        Path(args.project_root),
        denominator_path=Path(args.denominator_path),
        historical_window_path=Path(args.historical_window_path),
        output_path=Path(args.output_path),
        sensitivity_output_path=Path(args.sensitivity_output_path),
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
