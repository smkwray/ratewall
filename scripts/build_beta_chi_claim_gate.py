#!/usr/bin/env python3
"""Build beta-chi scenario-claim discipline outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.beta_chi_assumption_discipline import (
    beta_chi_chi_bridge_candidate_rows,
    beta_chi_chi_bridge_target_review_rows,
    beta_chi_chi_mapping_sensitivity_rows,
    beta_chi_claim_gate_rows_from_directory,
    beta_chi_evidence_target_rows,
    beta_chi_external_evidence_rows,
    beta_chi_external_floor_review_rows,
    beta_chi_robustness_threshold_rows,
    beta_chi_source_context_rows,
    beta_chi_source_review_rows,
    write_beta_chi_claim_gate_outputs,
)
from ratewall.databook.unified_scenario_results import DEFAULT_UNIFIED_SUITE_DIR


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite-dir",
        default=str(DEFAULT_UNIFIED_SUITE_DIR),
        help="TDCSim/CBO suite directory with manifest-backed beta-chi outputs.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/beta_chi_claim_gate",
        help="Directory for beta-chi claim-gate CSV and memo outputs.",
    )
    args = parser.parse_args()

    rows = beta_chi_claim_gate_rows_from_directory(args.suite_dir)
    threshold_rows = beta_chi_robustness_threshold_rows(rows)
    evidence_target_rows = beta_chi_evidence_target_rows(threshold_rows)
    source_context_rows = beta_chi_source_context_rows()
    source_review_rows = beta_chi_source_review_rows(
        evidence_target_rows=evidence_target_rows,
        source_context_rows=source_context_rows,
    )
    external_evidence_rows = beta_chi_external_evidence_rows()
    external_floor_review_rows = beta_chi_external_floor_review_rows(
        evidence_target_rows=evidence_target_rows,
        external_evidence_rows=external_evidence_rows,
    )
    chi_bridge_candidate_rows = beta_chi_chi_bridge_candidate_rows(
        external_evidence_rows,
    )
    chi_bridge_target_review_rows = beta_chi_chi_bridge_target_review_rows(
        evidence_target_rows=evidence_target_rows,
        chi_bridge_candidate_rows=chi_bridge_candidate_rows,
    )
    chi_mapping_sensitivity_rows = beta_chi_chi_mapping_sensitivity_rows(
        evidence_target_rows=evidence_target_rows,
        chi_bridge_candidate_rows=chi_bridge_candidate_rows,
    )
    outputs = write_beta_chi_claim_gate_outputs(
        Path(args.output_dir),
        rows=rows,
        threshold_rows=threshold_rows,
        evidence_target_rows=evidence_target_rows,
        source_context_rows=source_context_rows,
        source_review_rows=source_review_rows,
        external_evidence_rows=external_evidence_rows,
        external_floor_review_rows=external_floor_review_rows,
        chi_bridge_candidate_rows=chi_bridge_candidate_rows,
        chi_bridge_target_review_rows=chi_bridge_target_review_rows,
        chi_mapping_sensitivity_rows=chi_mapping_sensitivity_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"rows: {len(rows)}")
    print(f"threshold_rows: {len(threshold_rows)}")
    print(f"evidence_target_rows: {len(evidence_target_rows)}")
    print(f"source_context_rows: {len(source_context_rows)}")
    print(f"source_review_rows: {len(source_review_rows)}")
    print(f"external_evidence_rows: {len(external_evidence_rows)}")
    print(f"external_floor_review_rows: {len(external_floor_review_rows)}")
    print(f"chi_bridge_candidate_rows: {len(chi_bridge_candidate_rows)}")
    print(f"chi_bridge_target_review_rows: {len(chi_bridge_target_review_rows)}")
    print(f"chi_mapping_sensitivity_rows: {len(chi_mapping_sensitivity_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
