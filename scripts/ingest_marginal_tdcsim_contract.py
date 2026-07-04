#!/usr/bin/env python3
"""Ingest TDCSim marginal TDC pair output into RateWall fail-closed artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.marginal_tdcsim_contract import (
    DEFAULT_BETA_SCHEDULE_PATH,
    DEFAULT_PAIR_DIR,
    DEFAULT_PAIR_ROOT,
    ingest_marginal_tdcsim_pair,
    ingest_marginal_tdcsim_pairs,
    write_marginal_tdcsim_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pair-dir",
        default=str(DEFAULT_PAIR_DIR),
        help="TDCSim marginal pair directory.",
    )
    parser.add_argument(
        "--pair-root",
        default=None,
        help=(
            "Directory whose immediate child directories contain TDCSim marginal "
            f"pair manifests. Defaults to {DEFAULT_PAIR_ROOT} when supplied "
            "without --pair-dir by callers."
        ),
    )
    parser.add_argument(
        "--beta-schedule-path",
        default=str(DEFAULT_BETA_SCHEDULE_PATH),
        help="RateWall marginal TDC beta schedule CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/marginal_tdcsim",
        help="Directory for RateWall marginal TDCSim ingest outputs.",
    )
    args = parser.parse_args()

    if args.pair_root:
        tables = ingest_marginal_tdcsim_pairs(
            pair_root=Path(args.pair_root),
            beta_schedule_path=Path(args.beta_schedule_path),
        )
    else:
        tables = ingest_marginal_tdcsim_pair(
            pair_dir=Path(args.pair_dir),
            beta_schedule_path=Path(args.beta_schedule_path),
        )
    outputs = write_marginal_tdcsim_outputs(
        Path(args.output_dir),
        ingest_rows=tables["ingest_rows"],
        support_rows=tables["support_rows"],
        state_composition_audit_rows=tables["state_composition_audit_rows"],
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"ingest_rows: {len(tables['ingest_rows'])}")
    print(f"support_rows: {len(tables['support_rows'])}")
    print(f"state_composition_audit_rows: {len(tables['state_composition_audit_rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
