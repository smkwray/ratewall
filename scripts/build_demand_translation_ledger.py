#!/usr/bin/env python3
"""Build D9 demand-translation registry and ledger artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.demand_translation_ledger import (
    DEFAULT_REGISTRY_PATH,
    build_all,
    write_demand_translation_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry-path",
        default=str(DEFAULT_REGISTRY_PATH),
        help="Demand-translation registry YAML path.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/demand_translation_ledger",
        help="Directory for D9 demand-translation outputs.",
    )
    args = parser.parse_args()

    tables = build_all(registry_path=Path(args.registry_path))
    outputs = write_demand_translation_outputs(
        Path(args.output_dir),
        registry_rows=tables["registry_rows"],
        object_role_rows=tables["object_role_rows"],
        demand_translation_rows=tables["demand_translation_rows"],
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"registry_rows: {len(tables['registry_rows'])}")
    print(f"object_role_rows: {len(tables['object_role_rows'])}")
    print(f"demand_translation_rows: {len(tables['demand_translation_rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
