#!/usr/bin/env python3
"""Build the marginal-only final RateWall readout."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.final_marginal_readout import (
    final_marginal_readout_rows,
    write_final_marginal_readout_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/final_marginal_model",
    )
    args = parser.parse_args()

    readout_rows = final_marginal_readout_rows()
    outputs = write_final_marginal_readout_outputs(
        Path(args.output_dir),
        readout_rows=readout_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"readout_rows: {len(readout_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
