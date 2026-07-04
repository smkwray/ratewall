#!/usr/bin/env python3
"""Build RateWall Phase-4 keep/freeze/cut manifests from live output metadata."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


DEFAULT_OUTPUT_DIR = Path("outputs")
DEFAULT_KEEP_MANIFEST = Path("configs/ratewall_keep_tables_20260607.yml")
DEFAULT_FREEZE_MANIFEST = Path("configs/ratewall_freeze_manifest_20260607.csv")
DEFAULT_CUT_MANIFEST = Path("configs/ratewall_cut_manifest_20260607.csv")

TIER1_CANDIDATES = {
    "ratewall_wall_hit_scenarios.csv": "paper_candidate_wall_hit",
    "ratewall_minimum_conditions_to_hit_wall.csv": "paper_candidate_minimum_conditions",
}

TIER2_SEEDS = {
    "ratewall_annual_flow_denominator_anchor_registry.csv": "denominator_anchor_registry",
    "ratewall_runtime_annual_flow_support_offset_scenarios.csv": "runtime_support_offset",
    "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv": "runtime_frontier_summary",
    "ratewall_annual_support_numerator_component_rollup.csv": "numerator_component_rollup",
    "ratewall_wall_denominator_path_contract.csv": "denominator_path_contract",
    "ratewall_denominator_literature_matrix.csv": "denominator_literature_matrix",
    "ratewall_calibration_parameter_recommendations.csv": "calibration_recommendations",
    "ratewall_parameter_packs.csv": "parameter_packs",
    "ratewall_denominator_sensitivity.csv": "denominator_sensitivity",
    "ratewall_forecast_path_ratio_scenario_frontier.csv": "forecast_frontier",
    "ratewall_forecast_path_ratio_pass_through_scenario_frontier.csv": "forecast_pass_through_frontier",
    "ratewall_forecast_product_reviewer_decision_summary.csv": "forecast_reviewer_decision",
    "ratewall_joint_wall_probability_axis_registry.csv": "joint_probability_axis_registry",
    "ratewall_joint_wall_probability_surface.csv": "joint_probability_surface",
    "ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv": "fspdp_conversion_sensitivity",
    "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv": "runtime_benchmark_overlay",
    "ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv": "fspdp_sample_base_share_join",
    "ratewall_tdc_materialization_semantic_summary.csv": "tdc_semantic_guardrail",
}

VOLATILE_DIAGNOSTIC_FREEZE_REASONS = {
    "ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv": (
        "review_only_frbus_benchmark_nondeterministic_across_temp_builds"
    ),
}

KEEP_NAME_PATTERNS = (
    "paper_core_results_index",
    "active_output_index",
    "reference_scenario_object_crosswalk",
    "ratio_object_registry",
    "tdc_double_count_guardrail",
    "publication_claim_decision",
    "annual_flow_runtime_family_registry",
)

FREEZE_PATTERNS = (
    "context",
    "gate",
    "audit",
    "workplan",
    "scaffold",
    "queue",
    "blocker",
    "source_contract",
    "review",
    "disabled",
)

CUT_PATTERNS = (
    "ratewall_release_",
    "beneficial_owner",
    "final_owner_allocation",
    "holder_allocation",
    "bank_behavior",
    "iorb_retention",
    "frn_reset",
    "tips_formula",
    "treasury_valuation",
    "reset_calendar",
    "security_level",
    "valuation_readiness",
)

BOOLEAN_COLUMNS = (
    "canonical_ratio_entry",
    "enters_main_ratio",
    "evidence_mode_enabled",
)


@dataclass(frozen=True)
class OutputRow:
    artifact_path: str
    output_name: str
    source: str
    row: dict[str, str]

    @property
    def filename(self) -> str:
        return Path(self.output_name or self.artifact_path).name


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _paper_core_rows(output_dir: Path) -> list[OutputRow]:
    path = output_dir / "tables" / "ratewall_paper_core_results_index.csv"
    rows: list[OutputRow] = []
    for row in _read_csv(path):
        rows.append(
            OutputRow(
                artifact_path=row["path"],
                output_name=row["output_name"],
                source="paper_core",
                row=row,
            )
        )
    return rows


def _active_rows(output_dir: Path) -> list[OutputRow]:
    path = output_dir / "tables" / "ratewall_active_output_index.csv"
    rows: list[OutputRow] = []
    for row in _read_csv(path):
        artifact_path = row["artifact_path"]
        rows.append(
            OutputRow(
                artifact_path=artifact_path,
                output_name=Path(artifact_path).name,
                source="active_output",
                row=row,
            )
        )
    return rows


def _existing_tables(output_dir: Path) -> set[str]:
    return {path.name for path in (output_dir / "tables").glob("*.csv")}


def _bool(row: dict[str, str], key: str) -> bool:
    return str(row.get(key, "")).strip().lower() == "true"


def _has_any(name: str, patterns: Iterable[str]) -> bool:
    lowered = name.lower()
    return any(pattern in lowered for pattern in patterns)


def _dedupe_rows(rows: Iterable[OutputRow]) -> dict[str, OutputRow]:
    deduped: dict[str, OutputRow] = {}
    for row in rows:
        existing = deduped.get(row.filename)
        if existing is None or existing.source != "paper_core":
            deduped[row.filename] = row
    return deduped


def build_manifests(output_dir: Path) -> tuple[dict, list[dict[str, str]], list[dict[str, str]]]:
    paper_rows = _paper_core_rows(output_dir)
    active_rows = _active_rows(output_dir)
    indexed = _dedupe_rows([*active_rows, *paper_rows])
    existing = _existing_tables(output_dir)

    tier1: list[dict[str, str]] = []
    tier2: list[dict[str, str]] = []
    keep_names: set[str] = set()

    for row in paper_rows:
        tier1.append(
            {
                "output_name": row.filename,
                "artifact_path": row.artifact_path,
                "reason": "paper_core_results_index",
                "source": row.source,
            }
        )
        keep_names.add(row.filename)

    for filename, reason in sorted(TIER1_CANDIDATES.items()):
        if filename in existing:
            tier1.append(
                {
                    "output_name": filename,
                    "artifact_path": f"outputs/tables/{filename}",
                    "reason": reason,
                    "source": "paper_candidate",
                }
            )
            keep_names.add(filename)

    for filename, reason in sorted(TIER2_SEEDS.items()):
        if filename in existing:
            tier2.append(
                {
                    "output_name": filename,
                    "artifact_path": f"outputs/tables/{filename}",
                    "reason": reason,
                    "source": "evidence2_seed_validated_present",
                }
            )
            keep_names.add(filename)

    for filename in sorted(existing):
        if _has_any(filename, KEEP_NAME_PATTERNS) and filename not in keep_names:
            tier2.append(
                {
                    "output_name": filename,
                    "artifact_path": f"outputs/tables/{filename}",
                    "reason": "spine_guardrail_or_registry",
                    "source": "name_rule",
                }
            )
            keep_names.add(filename)

    freeze_rows: list[dict[str, str]] = []
    cut_rows: list[dict[str, str]] = []
    for filename in sorted(existing):
        if filename in keep_names:
            continue
        row = indexed.get(filename)
        row_payload = row.row if row else {}
        indexed_status = row.source if row else "not_indexed"
        false_flags = all(not _bool(row_payload, col) for col in BOOLEAN_COLUMNS)
        if _has_any(filename, CUT_PATTERNS):
            cut_rows.append(
                {
                    "artifact_path": f"outputs/tables/{filename}",
                    "cut_reason": _first_pattern(filename, CUT_PATTERNS),
                    "keeper_exception": "false",
                    "active_output_index_status": indexed_status,
                }
            )
            continue
        if filename in VOLATILE_DIAGNOSTIC_FREEZE_REASONS:
            freeze_rows.append(
                {
                    "artifact_path": f"outputs/tables/{filename}",
                    "freeze_reason": VOLATILE_DIAGNOSTIC_FREEZE_REASONS[filename],
                    "last_good_sha256": "",
                    "enters_main_ratio": str(_bool(row_payload, "enters_main_ratio")).lower(),
                    "active_output_index_status": indexed_status,
                    "keeper_exception": "false",
                }
            )
            continue
        if false_flags or indexed_status == "not_indexed" or _has_any(filename, FREEZE_PATTERNS):
            freeze_rows.append(
                {
                    "artifact_path": f"outputs/tables/{filename}",
                    "freeze_reason": _freeze_reason(filename, false_flags, indexed_status),
                    "last_good_sha256": "",
                    "enters_main_ratio": str(_bool(row_payload, "enters_main_ratio")).lower(),
                    "active_output_index_status": indexed_status,
                    "keeper_exception": "false",
                }
            )

    keep_manifest = {
        "schema": "ratewall.keep_tables.v1",
        "generated_from": [
            "outputs/tables/ratewall_paper_core_results_index.csv",
            "outputs/tables/ratewall_active_output_index.csv",
            "Evidence round 2 de-bloat runbook seed rules",
            "FRB/US review-only benchmark excluded from hash keepers after repeat-build nondeterminism check",
        ],
        "tiers": {
            "tier1_paper_core": tier1,
            "tier2_diagnostics": tier2,
        },
    }
    return keep_manifest, freeze_rows, cut_rows


def _first_pattern(filename: str, patterns: Iterable[str]) -> str:
    lowered = filename.lower()
    for pattern in patterns:
        if pattern in lowered:
            return pattern
    return "pattern_match"


def _freeze_reason(filename: str, false_flags: bool, indexed_status: str) -> str:
    reasons: list[str] = []
    if false_flags:
        reasons.append("non_promoting_flags_false")
    if indexed_status == "not_indexed":
        reasons.append("not_in_active_or_paper_index")
    pattern = _first_pattern(filename, FREEZE_PATTERNS)
    if pattern != "pattern_match":
        reasons.append(f"name_pattern:{pattern}")
    return ";".join(reasons) or "outside_keep_set"


def write_manifests(
    *,
    output_dir: Path,
    keep_manifest_path: Path,
    freeze_manifest_path: Path,
    cut_manifest_path: Path,
) -> None:
    keep_manifest, freeze_rows, cut_rows = build_manifests(output_dir)
    keep_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    freeze_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    cut_manifest_path.parent.mkdir(parents=True, exist_ok=True)

    keep_manifest_path.write_text(
        yaml.safe_dump(keep_manifest, sort_keys=False),
        encoding="utf-8",
    )
    _write_csv(
        freeze_manifest_path,
        [
            "artifact_path",
            "freeze_reason",
            "last_good_sha256",
            "enters_main_ratio",
            "active_output_index_status",
            "keeper_exception",
        ],
        freeze_rows,
    )
    _write_csv(
        cut_manifest_path,
        [
            "artifact_path",
            "cut_reason",
            "keeper_exception",
            "active_output_index_status",
        ],
        cut_rows,
    )


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--keep-manifest", type=Path, default=DEFAULT_KEEP_MANIFEST)
    parser.add_argument("--freeze-manifest", type=Path, default=DEFAULT_FREEZE_MANIFEST)
    parser.add_argument("--cut-manifest", type=Path, default=DEFAULT_CUT_MANIFEST)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    if args.check:
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            keep = tmp / args.keep_manifest.name
            freeze = tmp / args.freeze_manifest.name
            cut = tmp / args.cut_manifest.name
            write_manifests(
                output_dir=args.output_dir,
                keep_manifest_path=keep,
                freeze_manifest_path=freeze,
                cut_manifest_path=cut,
            )
            expected = {
                args.keep_manifest: keep,
                args.freeze_manifest: freeze,
                args.cut_manifest: cut,
            }
            mismatches = [
                str(target)
                for target, generated in expected.items()
                if not target.exists()
                or target.read_text(encoding="utf-8") != generated.read_text(encoding="utf-8")
            ]
            if mismatches:
                raise SystemExit(
                    "debloat manifests are stale; regenerate: " + ", ".join(mismatches)
                )
        print("debloat manifests: pass")
        return 0

    write_manifests(
        output_dir=args.output_dir,
        keep_manifest_path=args.keep_manifest,
        freeze_manifest_path=args.freeze_manifest,
        cut_manifest_path=args.cut_manifest,
    )
    print(
        "wrote "
        f"{args.keep_manifest}, {args.freeze_manifest}, {args.cut_manifest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
