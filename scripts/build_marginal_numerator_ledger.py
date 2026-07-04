#!/usr/bin/env python3
"""Build fail-closed marginal numerator ledger artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.marginal_numerator_ledger import (
    build_all,
    write_marginal_numerator_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/marginal_numerator",
        help="Directory for marginal numerator ledger outputs.",
    )
    args = parser.parse_args()

    tables = build_all()
    outputs = write_marginal_numerator_outputs(
        Path(args.output_dir),
        channel_rows=tables["channel_rows"],
        diagnostic_rows=tables["diagnostic_rows"],
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"channel_rows: {len(tables['channel_rows'])}")
    print(f"diagnostic_rows: {len(tables['diagnostic_rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
