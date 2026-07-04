#!/usr/bin/env python3
"""Build the consolidated beta-chi calibration readout."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.beta_chi_calibration_readout import (
    DEFAULT_BETA_CHI_CLAIM_GATE_DIR,
    DEFAULT_DIRECT_CHI_EVIDENCE_DIR,
    beta_chi_calibration_decision_rows,
    beta_chi_calibration_summary_rows,
    write_beta_chi_calibration_readout_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--claim-gate-dir",
        default=str(DEFAULT_BETA_CHI_CLAIM_GATE_DIR),
        help="Directory containing beta-chi claim-gate outputs.",
    )
    parser.add_argument(
        "--direct-chi-dir",
        default=str(DEFAULT_DIRECT_CHI_EVIDENCE_DIR),
        help="Directory containing direct chi / beta-chi evidence outputs.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/beta_chi_calibration_readout",
        help="Directory for consolidated calibration readout outputs.",
    )
    args = parser.parse_args()

    summary_rows = beta_chi_calibration_summary_rows(
        claim_gate_dir=Path(args.claim_gate_dir),
        direct_chi_dir=Path(args.direct_chi_dir),
    )
    decision_rows = beta_chi_calibration_decision_rows(summary_rows)
    outputs = write_beta_chi_calibration_readout_outputs(
        Path(args.output_dir),
        summary_rows=summary_rows,
        decision_rows=decision_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    summary = summary_rows[0]
    print(f"current_beta: {summary['current_beta']}")
    print(f"current_chi: {summary['current_chi']}")
    print(f"current_beta_times_chi: {summary['current_beta_times_chi']}")
    print(f"direct_admitted_floor_rows: {summary['direct_admitted_floor_rows']}")
    print(f"estimator_ready_rows: {summary['estimator_ready_rows']}")
    print(f"calibration_decision: {summary['calibration_decision']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
