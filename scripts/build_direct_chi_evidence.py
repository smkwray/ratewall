#!/usr/bin/env python3
"""Build direct chi / beta-chi evidence gate outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.beta_chi_assumption_discipline import (
    beta_chi_claim_gate_rows_from_directory,
    beta_chi_evidence_target_rows,
    beta_chi_robustness_threshold_rows,
)
from ratewall.databook.direct_beta_chi_panel import (
    DirectBetaChiPanelPaths,
    direct_beta_chi_panel_rows,
    direct_beta_chi_panel_source_candidate_rows,
    direct_beta_chi_panel_status_rows,
    write_direct_beta_chi_panel_outputs,
)
from ratewall.databook.direct_chi_evidence import (
    DEFAULT_TDCSIM_PERIOD_TDC_DIR,
    DirectChiSourcePaths,
    direct_beta_chi_estimator_contract_rows,
    direct_beta_chi_target_impact_rows,
    direct_chi_adjudication_rows,
    direct_chi_requirement_rows,
    direct_chi_source_inventory_rows,
    write_direct_chi_evidence_outputs,
)
from ratewall.databook.direct_chi_diagnostic_estimator import (
    DirectChiDiagnosticEstimatorPaths,
    direct_chi_diagnostic_estimator_rows,
    direct_chi_diagnostic_source_candidate_rows,
    write_direct_chi_diagnostic_estimator_outputs,
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
        "--tdcest-downstream-dir",
        default=str(Path.home() / "malus/proj/tdcest/data/processed"),
        help="TDC-est processed downstream handoff directory.",
    )
    parser.add_argument(
        "--tdcsim-period-tdc-dir",
        default=str(DEFAULT_TDCSIM_PERIOD_TDC_DIR),
        help="Optional TDCSim CBO package directory containing period TDC accounting outputs.",
    )
    parser.add_argument(
        "--local-current-demand-dir",
        default="data/raw/current_demand_gdp_share",
        help="Local RateWall current-demand source directory.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/direct_chi_evidence",
        help="Directory for direct chi evidence CSV and memo outputs.",
    )
    args = parser.parse_args()

    claim_gate_rows = beta_chi_claim_gate_rows_from_directory(args.suite_dir)
    thresholds = beta_chi_robustness_threshold_rows(claim_gate_rows)
    targets = beta_chi_evidence_target_rows(thresholds)
    requirements = direct_chi_requirement_rows(targets)
    diagnostic_rows = direct_chi_diagnostic_estimator_rows(
        paths=DirectChiDiagnosticEstimatorPaths(
            local_current_demand_dir=Path(args.local_current_demand_dir),
        )
    )
    panel_rows = direct_beta_chi_panel_rows(
        paths=DirectBetaChiPanelPaths(
            tdcsim_period_tdc_dir=Path(args.tdcsim_period_tdc_dir),
            local_current_demand_dir=Path(args.local_current_demand_dir),
        )
    )
    panel_status = direct_beta_chi_panel_status_rows(
        panel_rows,
        paths=DirectBetaChiPanelPaths(
            tdcsim_period_tdc_dir=Path(args.tdcsim_period_tdc_dir),
            local_current_demand_dir=Path(args.local_current_demand_dir),
        ),
    )
    sources = direct_chi_source_inventory_rows(
        paths=DirectChiSourcePaths(
            tdcsim_suite_dir=Path(args.suite_dir),
            tdcest_downstream_dir=Path(args.tdcest_downstream_dir),
            tdcsim_period_tdc_dir=Path(args.tdcsim_period_tdc_dir),
            local_current_demand_dir=Path(args.local_current_demand_dir),
        ),
        extra_candidate_rows=[
            *direct_beta_chi_panel_source_candidate_rows(panel_status),
            *direct_chi_diagnostic_source_candidate_rows(diagnostic_rows),
        ],
    )
    adjudications = direct_chi_adjudication_rows(
        requirement_rows=requirements,
        source_rows=sources,
    )
    estimator_contracts = direct_beta_chi_estimator_contract_rows(
        requirement_rows=requirements,
        source_rows=sources,
    )
    target_impacts = direct_beta_chi_target_impact_rows(
        requirement_rows=requirements,
        adjudication_rows=adjudications,
    )
    outputs = write_direct_chi_evidence_outputs(
        Path(args.output_dir),
        requirement_rows=requirements,
        source_rows=sources,
        adjudication_rows=adjudications,
        estimator_contract_rows=estimator_contracts,
        target_impact_rows=target_impacts,
    )
    diagnostic_outputs = write_direct_chi_diagnostic_estimator_outputs(
        Path(args.output_dir),
        rows=diagnostic_rows,
    )
    outputs.update(diagnostic_outputs)
    panel_outputs = write_direct_beta_chi_panel_outputs(
        Path(args.output_dir),
        panel_rows=panel_rows,
        status_rows=panel_status,
    )
    outputs.update(panel_outputs)
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"requirement_rows: {len(requirements)}")
    print(f"diagnostic_estimator_rows: {len(diagnostic_rows)}")
    print(f"direct_beta_chi_panel_rows: {len(panel_rows)}")
    print(f"direct_beta_chi_panel_status_rows: {len(panel_status)}")
    print(f"source_rows: {len(sources)}")
    print(f"adjudication_rows: {len(adjudications)}")
    print(f"estimator_contract_rows: {len(estimator_contracts)}")
    print(f"target_impact_rows: {len(target_impacts)}")
    print(
        "admitted_rows: "
        f"{sum(row['admission_result'] == 'admit_floor_from_direct_evidence' for row in adjudications)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
