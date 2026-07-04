#!/usr/bin/env python3
"""Build marginal RateWall object contract and channel ledger artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.marginal_object_ledger import (
    DEFAULT_CHANNEL_REGISTRY_PATH,
    DEFAULT_CURRENT_BRIDGE_PATH,
    DEFAULT_FORECAST_SURFACE_PATH,
    DEFAULT_HISTORICAL_DENOMINATOR_PATH,
    DEFAULT_HISTORICAL_ROOT_PATH,
    DEFAULT_OBJECT_CONFIG_PATH,
    build_all,
    write_marginal_object_ledger_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--object-config-path",
        default=str(DEFAULT_OBJECT_CONFIG_PATH),
        help="Marginal object YAML path.",
    )
    parser.add_argument(
        "--channel-registry-path",
        default=str(DEFAULT_CHANNEL_REGISTRY_PATH),
        help="Marginal channel registry YAML path.",
    )
    parser.add_argument("--current-bridge-path", default=str(DEFAULT_CURRENT_BRIDGE_PATH))
    parser.add_argument("--forecast-surface-path", default=str(DEFAULT_FORECAST_SURFACE_PATH))
    parser.add_argument("--historical-root-path", default=str(DEFAULT_HISTORICAL_ROOT_PATH))
    parser.add_argument(
        "--historical-denominator-path",
        default=str(DEFAULT_HISTORICAL_DENOMINATOR_PATH),
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/marginal_object_ledger",
        help="Directory for marginal object ledger outputs.",
    )
    args = parser.parse_args()

    tables = build_all(
        object_config_path=Path(args.object_config_path),
        channel_registry_path=Path(args.channel_registry_path),
        current_bridge_path=Path(args.current_bridge_path),
        forecast_surface_path=Path(args.forecast_surface_path),
        historical_root_path=Path(args.historical_root_path),
        historical_denominator_path=Path(args.historical_denominator_path),
    )
    outputs = write_marginal_object_ledger_outputs(
        Path(args.output_dir),
        contract_rows=tables["contract_rows"],
        channel_status_rows=tables["channel_status_rows"],
        row_role_reset_rows=tables["row_role_reset_rows"],
        complete_inventory_rows=tables["complete_inventory_rows"],
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"contract_rows: {len(tables['contract_rows'])}")
    print(f"channel_status_rows: {len(tables['channel_status_rows'])}")
    print(f"row_role_reset_rows: {len(tables['row_role_reset_rows'])}")
    print(f"complete_inventory_rows: {len(tables['complete_inventory_rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
