#!/usr/bin/env python3
"""Build the full marginal channel parity/readiness matrix."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ratewall.databook.marginal_channel_parity import (
    channel_period_parity_rows,
    write_channel_period_parity_output,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--selected-numerator-path",
        default=(
            "var/preliminary_scenario_results/marginal_numerator/"
            "ratewall_marginal_selected_numerator_surface.csv"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/marginal_numerator",
    )
    args = parser.parse_args()

    selected_rows = _read_csv(Path(args.selected_numerator_path))
    parity_rows = channel_period_parity_rows(selected_rows)
    outputs = write_channel_period_parity_output(
        Path(args.output_dir),
        parity_rows=parity_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"parity_rows: {len(parity_rows)}")
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
