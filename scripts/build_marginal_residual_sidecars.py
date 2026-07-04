#!/usr/bin/env python3
"""Build marginal residual sidecars and admitted disjoint delta gate."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.marginal_residual_sidecars import (
    DEFAULT_ADMITTED_RESIDUAL_ASSUMPTIONS_PATH,
    DEFAULT_DENOMINATOR_PATH,
    DEFAULT_RESIDUAL_SAFE_YIELD_COMPONENT_ASSUMPTIONS_PATH,
    credit_insulation_sidecar_rows,
    marginal_admitted_disjoint_delta_rows,
    residual_safe_yield_sidecar_rows,
    write_marginal_residual_sidecar_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--denominator-path", default=str(DEFAULT_DENOMINATOR_PATH))
    parser.add_argument("--assumptions-path", default=str(DEFAULT_ADMITTED_RESIDUAL_ASSUMPTIONS_PATH))
    parser.add_argument(
        "--component-assumptions-path",
        default=str(DEFAULT_RESIDUAL_SAFE_YIELD_COMPONENT_ASSUMPTIONS_PATH),
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/marginal_residual",
    )
    args = parser.parse_args()

    admitted = marginal_admitted_disjoint_delta_rows(
        denominator_path=Path(args.denominator_path),
        assumptions_path=Path(args.assumptions_path),
    )
    outputs = write_marginal_residual_sidecar_outputs(
        Path(args.output_dir),
        admitted_rows=admitted,
        safe_yield_sidecar_rows=residual_safe_yield_sidecar_rows(
            admitted,
            component_assumptions_path=Path(args.component_assumptions_path),
        ),
        credit_sidecar_rows=credit_insulation_sidecar_rows(admitted),
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"admitted_disjoint_rows: {len(admitted)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
