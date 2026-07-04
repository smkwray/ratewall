#!/usr/bin/env python3
"""Build the final economist-facing RateWall readout."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.final_model_readout import (
    DEFAULT_OUTPUT_DIR,
    DEFAULT_PRELIMINARY_DIR,
    write_final_model_readout_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preliminary-dir",
        default=str(DEFAULT_PRELIMINARY_DIR),
        help="Directory containing preliminary scenario artifacts.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for the final readout outputs.",
    )
    args = parser.parse_args()

    outputs = write_final_model_readout_outputs(
        Path(args.output_dir),
        preliminary_dir=Path(args.preliminary_dir),
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
