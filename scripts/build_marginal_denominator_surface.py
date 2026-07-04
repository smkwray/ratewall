#!/usr/bin/env python3
"""Build final-object marginal denominator surface artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.marginal_denominator import (
    DEFAULT_CURRENT_BENCHMARK_PATH,
    DEFAULT_DENOMINATOR_SEED_PATH,
    DEFAULT_GDP_PATH,
    DEFAULT_HISTORICAL_DENOMINATOR_PATH,
    DEFAULT_OBJECT_CONFIG_PATH,
    denominator_state_multiplier_rows,
    marginal_denominator_audit_rows,
    marginal_denominator_surface_rows,
    rate_environment_exposure_diagnostic_rows,
    write_marginal_denominator_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--object-config-path",
        default=str(DEFAULT_OBJECT_CONFIG_PATH),
        help="Marginal object YAML path.",
    )
    parser.add_argument(
        "--gdp-path",
        default=str(DEFAULT_GDP_PATH),
        help="Historical/current nominal GDP CSV path.",
    )
    parser.add_argument(
        "--current-benchmark-path",
        default=str(DEFAULT_CURRENT_BENCHMARK_PATH),
        help="Current benchmark CSV containing current/forecast nominal GDP.",
    )
    parser.add_argument(
        "--historical-denominator-path",
        default=str(DEFAULT_HISTORICAL_DENOMINATOR_PATH),
        help="Historical denominator convention review CSV path.",
    )
    parser.add_argument(
        "--seed-path",
        default=None,
        help=(
            "Optional deterministic denominator seed. When supplied, rebuilds D "
            f"from {DEFAULT_DENOMINATOR_SEED_PATH} style rows instead of raw GDP inputs."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/marginal_denominator",
        help="Directory for marginal denominator outputs.",
    )
    args = parser.parse_args()

    surface_rows = marginal_denominator_surface_rows(
        object_config_path=Path(args.object_config_path),
        gdp_path=Path(args.gdp_path),
        current_benchmark_path=Path(args.current_benchmark_path),
        historical_denominator_path=Path(args.historical_denominator_path),
        seed_path=Path(args.seed_path) if args.seed_path else None,
    )
    audit_rows = marginal_denominator_audit_rows(surface_rows)
    diagnostic_rows = rate_environment_exposure_diagnostic_rows()
    state_multiplier_rows = denominator_state_multiplier_rows(surface_rows)
    outputs = write_marginal_denominator_outputs(
        Path(args.output_dir),
        surface_rows=surface_rows,
        audit_rows=audit_rows,
        diagnostic_rows=diagnostic_rows,
        state_multiplier_rows=state_multiplier_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"surface_rows: {len(surface_rows)}")
    print(f"audit_rows: {len(audit_rows)}")
    print(f"diagnostic_rows: {len(diagnostic_rows)}")
    print(f"state_multiplier_rows: {len(state_multiplier_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
