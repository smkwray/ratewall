#!/usr/bin/env python3
"""Build D2/D10 current-object bridge and freeze artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.current_object_bridge import (
    DEFAULT_CURRENT_OVERLAY_DIR,
    DEFAULT_RUNTIME_TABLE_DIR,
    DEFAULT_SAFE_YIELD_DIR,
    current_object_bridge_readout_markdown,
    current_object_bridge_rows,
    current_object_freeze_decision_rows,
    current_object_input_manifest_rows,
    write_current_object_bridge_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--current-overlay-dir",
        default=str(DEFAULT_CURRENT_OVERLAY_DIR),
        help="Directory containing current observed-overlay outputs.",
    )
    parser.add_argument(
        "--safe-yield-dir",
        default=str(DEFAULT_SAFE_YIELD_DIR),
        help="Directory containing realized safe-yield outputs.",
    )
    parser.add_argument(
        "--runtime-table-dir",
        default=str(DEFAULT_RUNTIME_TABLE_DIR),
        help="Directory containing runtime current benchmark inputs.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/current_object_bridge",
        help="Directory for current-object bridge outputs.",
    )
    args = parser.parse_args()

    manifest_rows = current_object_input_manifest_rows(
        runtime_table_dir=Path(args.runtime_table_dir)
    )
    bridge_rows = current_object_bridge_rows(
        current_overlay_dir=Path(args.current_overlay_dir),
        safe_yield_dir=Path(args.safe_yield_dir),
        runtime_table_dir=Path(args.runtime_table_dir),
    )
    freeze_rows = current_object_freeze_decision_rows(bridge_rows)
    readout = current_object_bridge_readout_markdown(
        bridge_rows=bridge_rows,
        freeze_decision_rows=freeze_rows,
        input_manifest_rows=manifest_rows,
    )
    outputs = write_current_object_bridge_outputs(
        Path(args.output_dir),
        bridge_rows=bridge_rows,
        freeze_decision_rows=freeze_rows,
        input_manifest_rows=manifest_rows,
        readout_markdown=readout,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"bridge_rows: {len(bridge_rows)}")
    print(f"freeze_decision_rows: {len(freeze_rows)}")
    print(f"input_manifest_rows: {len(manifest_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
