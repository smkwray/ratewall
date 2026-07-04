"""Final release-package artifacts for RateWall."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from ratewall.generated_text_claim_scan import (
    GENERATED_TEXT_CLAIM_BOUNDARY_SCAN_FIELDS,
    generated_text_claim_boundary_scan_rows,
)
from ratewall.databook.backend_surface_schema import (
    BACKEND_ARTIFACT_CLAIM_BOUNDARY_MANIFEST_FIELDS,
    BACKEND_SURFACE_SCHEMA_CONTRACT_FIELDS,
    RELEASE_ARCHIVE_REPRODUCIBILITY_AUDIT_FIELDS,
    backend_artifact_claim_boundary_manifest_rows,
    backend_surface_schema_contract_rows,
    release_archive_reproducibility_audit_rows,
)
from ratewall.sources.base import utc_now_iso


@dataclass(frozen=True)
class ReleaseArtifacts:
    final_paper: Path
    final_paper_quarto: Path
    slide_deck: Path
    slide_deck_quarto: Path
    release_manifest: Path
    claim_audit: Path
    source_appendix: Path
    empirical_appendix: Path
    limitations_appendix: Path
    validation_package: Path
    public_readme: Path
    release_index: Path
    reproduction_commands: Path
    public_release_checklist: Path
    publication_claim_decision_memo: Path
    release_16_bounded_publication_closeout_memo: Path
    release_16_reviewer_blocker_text: Path
    release_17_external_review_packet: Path
    release_17_publication_polish_memo: Path
    release_18_publication_freeze_memo: Path
    release_19_post_audit_methodology_memo: Path
    release_20_submission_readiness_memo: Path
    release_21_backend_closeout_memo: Path
    release_22_backend_fix_memo: Path
    release_23_backend_fix_memo: Path
    release_23_reproducibility_manifest: Path
    release_23_archive_verification_audit: Path
    figure_plate: Path
    table_plate: Path
    archival_manifest: Path
    source_archive: Path
    citation_metadata: Path
    package_smoke: Path


def build_release_package(
    *,
    output_dir: Path = Path("outputs"),
    snapshot_bundle: Path = Path("data/raw/ratewall_snapshot.json"),
) -> ReleaseArtifacts:
    tables_dir = output_dir / "tables"
    reports_dir = output_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    context = _load_release_context(
        tables_dir=tables_dir, snapshot_bundle=snapshot_bundle
    )

    claim_audit = tables_dir / "ratewall_claim_boundary_audit.csv"
    claim_rows = _claim_audit_rows(context)
    _write_csv(claim_audit, claim_rows, CLAIM_AUDIT_FIELDS)

    final_paper = reports_dir / "ratewall_final_paper.md"
    final_paper.write_text(_final_paper_text(context, claim_rows), encoding="utf-8")

    final_paper_quarto = reports_dir / "ratewall_final_paper.qmd"
    final_paper_quarto.write_text(
        _final_paper_quarto_text(context, claim_rows), encoding="utf-8"
    )

    slide_deck = reports_dir / "ratewall_deck_ready.md"
    slide_deck.write_text(_slide_deck_text(context), encoding="utf-8")

    slide_deck_quarto = reports_dir / "ratewall_public_deck.qmd"
    slide_deck_quarto.write_text(_slide_deck_quarto_text(context), encoding="utf-8")

    source_appendix = reports_dir / "ratewall_source_provenance_appendix.md"
    source_appendix.write_text(_source_appendix_text(context), encoding="utf-8")

    empirical_appendix = reports_dir / "ratewall_empirical_method_appendix.md"
    empirical_appendix.write_text(_empirical_appendix_text(context), encoding="utf-8")

    limitations_appendix = reports_dir / "ratewall_limitations_appendix.md"
    limitations_appendix.write_text(
        _limitations_appendix_text(context, claim_rows), encoding="utf-8"
    )

    validation_package = reports_dir / "ratewall_validation_package.md"
    validation_package.write_text(
        _validation_package_text(context, claim_rows), encoding="utf-8"
    )

    public_readme = reports_dir / "ratewall_public_readme.md"
    public_readme.write_text(_public_readme_text(context, claim_rows), encoding="utf-8")

    theory_of_change = reports_dir / "ratewall_theory_of_change.md"
    theory_of_change.write_text(_theory_of_change_text(), encoding="utf-8")

    release_index = reports_dir / "ratewall_release_artifact_index.md"
    reproduction_commands = reports_dir / "ratewall_reproduction_commands.md"
    public_release_checklist = reports_dir / "ratewall_public_release_checklist.md"
    publication_claim_decision_memo = (
        reports_dir / "ratewall_publication_claim_decision_memo.md"
    )
    publication_claim_decision_memo.write_text(
        _publication_claim_decision_memo_text(context),
        encoding="utf-8",
    )
    release_16_bounded_publication_closeout_memo = (
        reports_dir / "ratewall_release_16_bounded_publication_closeout_memo.md"
    )
    release_16_bounded_publication_closeout_memo.write_text(
        _release_16_bounded_publication_closeout_memo_text(context),
        encoding="utf-8",
    )
    release_16_reviewer_blocker_text = (
        reports_dir / "ratewall_release_16_reviewer_blocker_text.md"
    )
    release_16_reviewer_blocker_text.write_text(
        _release_16_reviewer_blocker_text(context),
        encoding="utf-8",
    )
    release_17_external_review_packet = (
        reports_dir / "ratewall_release_17_external_review_packet.md"
    )
    release_17_external_review_packet.write_text(
        _release_17_external_review_packet_text(context),
        encoding="utf-8",
    )
    release_17_publication_polish_memo = (
        reports_dir / "ratewall_release_17_publication_polish_memo.md"
    )
    release_17_publication_polish_memo.write_text(
        _release_17_publication_polish_memo_text(context),
        encoding="utf-8",
    )
    release_18_publication_freeze_memo = (
        reports_dir / "ratewall_release_18_publication_freeze_memo.md"
    )
    release_18_publication_freeze_memo.write_text(
        _release_18_publication_freeze_memo_text(context),
        encoding="utf-8",
    )
    release_19_post_audit_methodology_memo = (
        reports_dir / "ratewall_release_19_post_audit_methodology_memo.md"
    )
    release_19_post_audit_methodology_memo.write_text(
        _release_19_post_audit_methodology_memo_text(context),
        encoding="utf-8",
    )
    release_20_submission_readiness_memo = (
        reports_dir / "ratewall_release_20_submission_readiness_memo.md"
    )
    release_20_submission_readiness_memo.write_text(
        _release_20_submission_readiness_memo_text(context),
        encoding="utf-8",
    )
    release_21_backend_closeout_memo = (
        reports_dir / "ratewall_release_21_backend_closeout_memo.md"
    )
    release_21_backend_closeout_memo.write_text(
        _release_21_backend_closeout_memo_text(context),
        encoding="utf-8",
    )
    release_22_backend_fix_memo = (
        reports_dir / "ratewall_release_22_backend_fix_memo.md"
    )
    release_22_backend_fix_memo.write_text(
        _release_22_backend_fix_memo_text(context),
        encoding="utf-8",
    )
    release_23_backend_fix_memo = (
        reports_dir / "ratewall_release_23_backend_fix_memo.md"
    )
    release_23_backend_fix_memo.write_text(
        _release_23_backend_fix_memo_text(context),
        encoding="utf-8",
    )
    figure_plate = reports_dir / "ratewall_figure_plate.md"
    figure_plate.write_text(_figure_plate_text(context), encoding="utf-8")
    table_plate = reports_dir / "ratewall_table_plate.md"
    table_plate.write_text(_table_plate_text(context), encoding="utf-8")
    citation_metadata = reports_dir / "CITATION.cff"
    citation_metadata.write_text(_citation_metadata_text(), encoding="utf-8")
    package_smoke = reports_dir / "ratewall_package_smoke.md"
    package_smoke.write_text(_package_smoke_text(), encoding="utf-8")
    archival_manifest = tables_dir / "ratewall_release_archive_manifest.json"
    source_archive = output_dir / "release" / "ratewall_release_23_0_source_archive.zip"
    release_23_reproducibility_manifest = (
        tables_dir / "ratewall_release_23_reproducibility_hash_manifest.json"
    )
    release_23_archive_verification_audit = (
        tables_dir / "ratewall_release_23_archive_hash_verification_audit.csv"
    )

    release_manifest = tables_dir / "ratewall_release_manifest.json"
    preliminary_artifacts = ReleaseArtifacts(
        final_paper=final_paper,
        final_paper_quarto=final_paper_quarto,
        slide_deck=slide_deck,
        slide_deck_quarto=slide_deck_quarto,
        release_manifest=release_manifest,
        claim_audit=claim_audit,
        source_appendix=source_appendix,
        empirical_appendix=empirical_appendix,
        limitations_appendix=limitations_appendix,
        validation_package=validation_package,
        public_readme=public_readme,
        release_index=release_index,
        reproduction_commands=reproduction_commands,
        public_release_checklist=public_release_checklist,
        publication_claim_decision_memo=publication_claim_decision_memo,
        release_16_bounded_publication_closeout_memo=(
            release_16_bounded_publication_closeout_memo
        ),
        release_16_reviewer_blocker_text=release_16_reviewer_blocker_text,
        release_17_external_review_packet=release_17_external_review_packet,
        release_17_publication_polish_memo=release_17_publication_polish_memo,
        release_18_publication_freeze_memo=release_18_publication_freeze_memo,
        release_19_post_audit_methodology_memo=(release_19_post_audit_methodology_memo),
        release_20_submission_readiness_memo=release_20_submission_readiness_memo,
        release_21_backend_closeout_memo=release_21_backend_closeout_memo,
        release_22_backend_fix_memo=release_22_backend_fix_memo,
        release_23_backend_fix_memo=release_23_backend_fix_memo,
        release_23_reproducibility_manifest=release_23_reproducibility_manifest,
        release_23_archive_verification_audit=release_23_archive_verification_audit,
        figure_plate=figure_plate,
        table_plate=table_plate,
        archival_manifest=archival_manifest,
        source_archive=source_archive,
        citation_metadata=citation_metadata,
        package_smoke=package_smoke,
    )
    release_index.write_text(
        _release_artifact_index_text(context, preliminary_artifacts),
        encoding="utf-8",
    )
    reproduction_commands.write_text(
        _reproduction_commands_text(),
        encoding="utf-8",
    )
    public_release_checklist.write_text(
        _public_release_checklist_text(context, claim_rows),
        encoding="utf-8",
    )

    final_artifacts = ReleaseArtifacts(
        final_paper=final_paper,
        final_paper_quarto=final_paper_quarto,
        slide_deck=slide_deck,
        slide_deck_quarto=slide_deck_quarto,
        release_manifest=release_manifest,
        claim_audit=claim_audit,
        source_appendix=source_appendix,
        empirical_appendix=empirical_appendix,
        limitations_appendix=limitations_appendix,
        validation_package=validation_package,
        public_readme=public_readme,
        release_index=release_index,
        reproduction_commands=reproduction_commands,
        public_release_checklist=public_release_checklist,
        publication_claim_decision_memo=publication_claim_decision_memo,
        release_16_bounded_publication_closeout_memo=(
            release_16_bounded_publication_closeout_memo
        ),
        release_16_reviewer_blocker_text=release_16_reviewer_blocker_text,
        release_17_external_review_packet=release_17_external_review_packet,
        release_17_publication_polish_memo=release_17_publication_polish_memo,
        release_18_publication_freeze_memo=release_18_publication_freeze_memo,
        release_19_post_audit_methodology_memo=(release_19_post_audit_methodology_memo),
        release_20_submission_readiness_memo=release_20_submission_readiness_memo,
        release_21_backend_closeout_memo=release_21_backend_closeout_memo,
        release_22_backend_fix_memo=release_22_backend_fix_memo,
        release_23_backend_fix_memo=release_23_backend_fix_memo,
        release_23_reproducibility_manifest=release_23_reproducibility_manifest,
        release_23_archive_verification_audit=release_23_archive_verification_audit,
        figure_plate=figure_plate,
        table_plate=table_plate,
        archival_manifest=archival_manifest,
        source_archive=source_archive,
        citation_metadata=citation_metadata,
        package_smoke=package_smoke,
    )
    release_manifest.write_text(
        json.dumps(
            _manifest_payload(
                context,
                claim_rows=claim_rows,
                artifacts=final_artifacts,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    generated_text_claim_boundary_scan = (
        tables_dir / "ratewall_generated_text_claim_boundary_scan.csv"
    )
    _write_csv(
        generated_text_claim_boundary_scan,
        generated_text_claim_boundary_scan_rows(output_dir),
        GENERATED_TEXT_CLAIM_BOUNDARY_SCAN_FIELDS,
    )
    _write_csv(
        tables_dir / "ratewall_backend_surface_schema_contract.csv",
        backend_surface_schema_contract_rows(
            tables_dir=tables_dir,
            release_manifest_path=release_manifest,
        ),
        BACKEND_SURFACE_SCHEMA_CONTRACT_FIELDS,
    )
    _write_csv(
        tables_dir / "ratewall_backend_artifact_claim_boundary_manifest.csv",
        backend_artifact_claim_boundary_manifest_rows(
            tables_dir=tables_dir,
            release_manifest_path=release_manifest,
        ),
        BACKEND_ARTIFACT_CLAIM_BOUNDARY_MANIFEST_FIELDS,
    )
    release_23_reproducibility_manifest.write_text(
        json.dumps(
            _release_23_reproducibility_manifest_payload(
                context=context,
                artifacts=final_artifacts,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    planned_archive_paths = _planned_source_archive_paths(context, final_artifacts)
    release_archive_reproducibility_audit = (
        tables_dir / "ratewall_release_archive_reproducibility_audit.csv"
    )
    _write_csv(
        release_archive_reproducibility_audit,
        release_archive_reproducibility_audit_rows(
            tables_dir=tables_dir,
            release_manifest_path=release_manifest,
            source_archive_path=source_archive,
            planned_archive_paths=planned_archive_paths,
        ),
        RELEASE_ARCHIVE_REPRODUCIBILITY_AUDIT_FIELDS,
    )
    planned_archive_paths = _planned_source_archive_paths(context, final_artifacts)
    _write_csv(
        release_archive_reproducibility_audit,
        release_archive_reproducibility_audit_rows(
            tables_dir=tables_dir,
            release_manifest_path=release_manifest,
            source_archive_path=source_archive,
            planned_archive_paths=planned_archive_paths,
        ),
        RELEASE_ARCHIVE_REPRODUCIBILITY_AUDIT_FIELDS,
    )
    _write_source_archive(
        archive_path=source_archive,
        context=context,
        artifacts=final_artifacts,
    )
    _write_csv(
        release_23_archive_verification_audit,
        _release_23_archive_verification_rows(
            archive_path=source_archive,
            manifest_path=release_23_reproducibility_manifest,
        ),
        RELEASE_23_ARCHIVE_VERIFICATION_FIELDS,
    )
    archival_manifest.write_text(
        json.dumps(
            _archival_manifest_payload(
                context=context,
                artifacts=final_artifacts,
                archive_path=source_archive,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return ReleaseArtifacts(
        final_paper=final_paper,
        final_paper_quarto=final_paper_quarto,
        slide_deck=slide_deck,
        slide_deck_quarto=slide_deck_quarto,
        release_manifest=release_manifest,
        claim_audit=claim_audit,
        source_appendix=source_appendix,
        empirical_appendix=empirical_appendix,
        limitations_appendix=limitations_appendix,
        validation_package=validation_package,
        public_readme=public_readme,
        release_index=release_index,
        reproduction_commands=reproduction_commands,
        public_release_checklist=public_release_checklist,
        publication_claim_decision_memo=publication_claim_decision_memo,
        release_16_bounded_publication_closeout_memo=(
            release_16_bounded_publication_closeout_memo
        ),
        release_16_reviewer_blocker_text=release_16_reviewer_blocker_text,
        release_17_external_review_packet=release_17_external_review_packet,
        release_17_publication_polish_memo=release_17_publication_polish_memo,
        release_18_publication_freeze_memo=release_18_publication_freeze_memo,
        release_19_post_audit_methodology_memo=(release_19_post_audit_methodology_memo),
        release_20_submission_readiness_memo=release_20_submission_readiness_memo,
        release_21_backend_closeout_memo=release_21_backend_closeout_memo,
        release_22_backend_fix_memo=release_22_backend_fix_memo,
        release_23_backend_fix_memo=release_23_backend_fix_memo,
        release_23_reproducibility_manifest=release_23_reproducibility_manifest,
        release_23_archive_verification_audit=release_23_archive_verification_audit,
        figure_plate=figure_plate,
        table_plate=table_plate,
        archival_manifest=archival_manifest,
        source_archive=source_archive,
        citation_metadata=citation_metadata,
        package_smoke=package_smoke,
    )


CLAIM_AUDIT_FIELDS = [
    "boundary",
    "audit_status",
    "evidence_artifact",
    "finding",
    "release_action",
]


def _load_release_context(
    *, tables_dir: Path, snapshot_bundle: Path
) -> dict[str, object]:
    provenance_path = tables_dir / "source_provenance.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    sources = list(provenance.get("sources", []))
    empirical_results = _read_csv(tables_dir / "ratewall_empirical_results.csv")
    outcome_panel = _read_csv(tables_dir / "ratewall_empirical_outcome_panel.csv")
    causal_audit = _read_csv(tables_dir / "ratewall_causal_identification_audit.csv")
    causal_blocker = _read_csv(tables_dir / "ratewall_causal_defensibility_blocker.csv")
    support_diagnostics = _read_csv(
        tables_dir / "ratewall_event_study_support_diagnostics.csv"
    )
    event_study_robustness = _read_csv(
        tables_dir / "ratewall_event_study_robustness.csv"
    )
    submission_decision = _read_csv(
        tables_dir / "ratewall_submission_identification_decision.csv"
    )
    dynamic_lp_feasibility = _read_csv(
        tables_dir / "ratewall_dynamic_lp_feasibility_diagnostics.csv"
    )
    proxy_svar_feasibility = _read_csv(
        tables_dir / "ratewall_proxy_svar_feasibility_diagnostics.csv"
    )
    dynamic_causal_blocker = _read_csv(
        tables_dir / "ratewall_dynamic_causal_final_blocker.csv"
    )
    event_study_hac = _read_csv(tables_dir / "ratewall_event_study_hac_diagnostics.csv")
    pretrend_placebo = _read_csv(
        tables_dir / "ratewall_pretrend_placebo_diagnostics.csv"
    )
    promotion_contract = _read_csv(
        tables_dir / "ratewall_dynamic_identification_promotion_contract_disabled.csv"
    )
    release_4_blocker = _read_csv(
        tables_dir / "ratewall_release_4_0_dynamic_causal_final_blocker.csv"
    )
    release_4_checklist = _read_csv(
        tables_dir / "ratewall_release_4_0_submission_checklist.csv"
    )
    external_review_issue_matrix = _read_csv(
        tables_dir / "ratewall_external_review_issue_matrix.csv"
    )
    journal_manifest_path = tables_dir / "ratewall_journal_submission_manifest.json"
    journal_manifest = (
        json.loads(journal_manifest_path.read_text(encoding="utf-8"))
        if journal_manifest_path.exists()
        else {}
    )
    release_4_manifest_path = (
        tables_dir / "ratewall_release_4_0_submission_manifest.json"
    )
    release_4_manifest = (
        json.loads(release_4_manifest_path.read_text(encoding="utf-8"))
        if release_4_manifest_path.exists()
        else {}
    )
    controlled_dynamic_lp_panel = _read_csv(
        tables_dir / "ratewall_controlled_dynamic_lp_panel.csv"
    )
    controlled_dynamic_lp_results = _read_csv(
        tables_dir / "ratewall_controlled_dynamic_lp_results.csv"
    )
    controlled_dynamic_lp_support = _read_csv(
        tables_dir / "ratewall_controlled_dynamic_lp_support_diagnostics.csv"
    )
    release_5_decision = _read_csv(
        tables_dir / "ratewall_release_5_0_identification_decision.csv"
    )
    release_5_proxy_blocker = _read_csv(
        tables_dir / "ratewall_release_5_0_proxy_svar_final_blocker.csv"
    )
    release_5_manifest_path = (
        tables_dir / "ratewall_release_5_0_dynamic_causal_manifest.json"
    )
    release_5_manifest = (
        json.loads(release_5_manifest_path.read_text(encoding="utf-8"))
        if release_5_manifest_path.exists()
        else {}
    )
    proxy_svar_system_panel = _read_csv(
        tables_dir / "ratewall_proxy_svar_system_panel.csv"
    )
    proxy_svar_relevance = _read_csv(
        tables_dir / "ratewall_proxy_svar_proxy_relevance_diagnostics.csv"
    )
    proxy_svar_residual = _read_csv(
        tables_dir / "ratewall_proxy_svar_residual_diagnostics.csv"
    )
    proxy_svar_timing = _read_csv(
        tables_dir / "ratewall_proxy_svar_timing_support_diagnostics.csv"
    )
    release_6_decision = _read_csv(
        tables_dir / "ratewall_release_6_0_identification_decision.csv"
    )
    release_6_proxy_blocker = _read_csv(
        tables_dir / "ratewall_release_6_0_proxy_svar_final_blocker.csv"
    )
    release_6_valuation_frontier = _read_csv(
        tables_dir / "ratewall_release_6_0_valuation_incidence_frontier_disabled.csv"
    )
    release_6_manifest_path = (
        tables_dir / "ratewall_release_6_0_system_identification_manifest.json"
    )
    release_6_manifest = (
        json.loads(release_6_manifest_path.read_text(encoding="utf-8"))
        if release_6_manifest_path.exists()
        else {}
    )
    release_7_lag_selection = _read_csv(
        tables_dir / "ratewall_release_7_0_var_lag_selection.csv"
    )
    release_7_reduced_form_estimates = _read_csv(
        tables_dir / "ratewall_release_7_0_reduced_form_system_estimates.csv"
    )
    release_7_residual_covariance = _read_csv(
        tables_dir / "ratewall_release_7_0_residual_covariance.csv"
    )
    release_7_proxy_support = _read_csv(
        tables_dir / "ratewall_release_7_0_proxy_relevance_support.csv"
    )
    release_7_timing_audit = _read_csv(
        tables_dir / "ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv"
    )
    release_7_promotion_contract = _read_csv(
        tables_dir / "ratewall_release_7_0_claim_promotion_contract_disabled.csv"
    )
    release_7_decision = _read_csv(
        tables_dir / "ratewall_release_7_0_identification_decision.csv"
    )
    release_7_proxy_blocker = _read_csv(
        tables_dir / "ratewall_release_7_0_proxy_svar_final_blocker.csv"
    )
    release_7_manifest_path = (
        tables_dir / "ratewall_release_7_0_system_identification_manifest.json"
    )
    release_7_manifest = (
        json.loads(release_7_manifest_path.read_text(encoding="utf-8"))
        if release_7_manifest_path.exists()
        else {}
    )
    release_8_proxy_specification = _read_csv(
        tables_dir / "ratewall_release_8_0_proxy_specification_audit.csv"
    )
    release_8_structural_gap = _read_csv(
        tables_dir / "ratewall_release_8_0_structural_gap_ledger.csv"
    )
    release_8_nonpromotion_proof = _read_csv(
        tables_dir / "ratewall_release_8_0_nonpromotion_proof.csv"
    )
    release_8_decision = _read_csv(
        tables_dir / "ratewall_release_8_0_identification_decision.csv"
    )
    release_8_manifest_path = (
        tables_dir / "ratewall_release_8_0_system_identification_manifest.json"
    )
    release_8_manifest = (
        json.loads(release_8_manifest_path.read_text(encoding="utf-8"))
        if release_8_manifest_path.exists()
        else {}
    )
    release_9_proxy_registry = _read_csv(
        tables_dir / "ratewall_release_9_0_external_proxy_source_registry.csv"
    )
    release_9_proxy_support = _read_csv(
        tables_dir / "ratewall_release_9_0_external_proxy_support_audit.csv"
    )
    release_9_decision = _read_csv(
        tables_dir / "ratewall_release_9_0_structural_identification_decision.csv"
    )
    release_9_nonpromotion_proof = _read_csv(
        tables_dir / "ratewall_release_9_0_final_nonpromotion_proof.csv"
    )
    release_9_manifest_path = (
        tables_dir / "ratewall_release_9_0_structural_identification_manifest.json"
    )
    release_9_manifest = (
        json.loads(release_9_manifest_path.read_text(encoding="utf-8"))
        if release_9_manifest_path.exists()
        else {}
    )
    robustness_manifest_path = (
        tables_dir / "ratewall_empirical_robustness_manifest.json"
    )
    robustness_manifest = (
        json.loads(robustness_manifest_path.read_text(encoding="utf-8"))
        if robustness_manifest_path.exists()
        else {}
    )
    impulse = _read_csv(tables_dir / "ratewall_100bps_impulse.csv")
    scenarios = _read_csv(tables_dir / "ratewall_scenarios.csv")
    metrics = _read_csv(tables_dir / "ratewall_databook_metrics.csv")
    dashboard = _read_csv(tables_dir / "ratewall_score_dashboard.csv")
    limitations = _read_csv(tables_dir / "evidence_limitations.csv")
    valuation_gate = _read_csv(
        tables_dir / "treasury_valuation_engine_readiness_gate.csv"
    )
    pricing_audit = _read_csv(tables_dir / "treasury_pricing_switch_audit_disabled.csv")
    readiness = _read_csv(tables_dir / "treasury_valuation_readiness_coverage.csv")
    tdc_ledger = _read_csv(tables_dir / "ratewall_tdc_deposit_channel_ledger.csv")
    tdc_impulse = _read_csv(
        tables_dir / "ratewall_tdc_ru_financing_deposit_impulse.csv"
    )
    tdc_historical_panel = _read_csv(tables_dir / "ratewall_tdc_historical_panel.csv")
    deposit_pricing_pass_through = _read_csv(
        tables_dir / "ratewall_deposit_pricing_pass_through_context.csv"
    )
    tdc_historical_reconciliation = _read_csv(
        tables_dir / "ratewall_tdc_historical_reconciliation.csv"
    )
    threshold_simulation = _read_csv(tables_dir / "ratewall_threshold_simulation.csv")
    threshold_calibration_ranges = _read_csv(
        tables_dir / "ratewall_threshold_calibration_ranges.csv"
    )
    threshold_calibrated_simulation = _read_csv(
        tables_dir / "ratewall_threshold_calibrated_simulation.csv"
    )
    du_ru_tga_calibration_bridge = _read_csv(
        tables_dir / "ratewall_du_ru_tga_calibration_bridge.csv"
    )
    assumption_sets = _read_csv(tables_dir / "ratewall_assumption_sets.csv")
    condition_frontier = _read_csv(tables_dir / "ratewall_condition_frontier.csv")
    offset_decomposition = _read_csv(tables_dir / "ratewall_offset_decomposition.csv")
    public_impulse_factorization = _read_csv(
        tables_dir / "ratewall_public_impulse_factorization.csv"
    )
    public_liability_repricing_ladder = _read_csv(
        tables_dir / "ratewall_public_liability_repricing_ladder.csv"
    )
    public_liability_repricing_evidence_bridge = _read_csv(
        tables_dir / "ratewall_public_liability_repricing_evidence_bridge.csv"
    )
    public_liability_repricing_reconciliation_gap = _read_csv(
        tables_dir / "ratewall_public_liability_repricing_reconciliation_gap.csv"
    )
    mspd_table3_bucket_repricing_gate = _read_csv(
        tables_dir / "ratewall_mspd_table3_bucket_repricing_gate.csv"
    )
    interest_recipient_leakage_bridge = _read_csv(
        tables_dir / "ratewall_interest_recipient_leakage_bridge.csv"
    )
    interest_recipient_leakage_evidence_gap = _read_csv(
        tables_dir / "ratewall_interest_recipient_leakage_evidence_gap.csv"
    )
    treasury_recipient_leakage_source_gate = _read_csv(
        tables_dir / "ratewall_treasury_recipient_leakage_source_gate.csv"
    )
    public_finance_timing_path = _read_csv(
        tables_dir / "ratewall_public_finance_timing_path.csv"
    )
    public_finance_timing_evidence_gap = _read_csv(
        tables_dir / "ratewall_public_finance_timing_evidence_gap.csv"
    )
    public_finance_timing_design_test_scaffold = _read_csv(
        tables_dir / "ratewall_public_finance_timing_design_test_scaffold.csv"
    )
    safe_yield_offset_drag_pairing_gap = _read_csv(
        tables_dir / "ratewall_safe_yield_offset_drag_pairing_gap.csv"
    )
    bnpl_zero_interest_float_evidence_gap = _read_csv(
        tables_dir / "ratewall_bnpl_zero_interest_float_evidence_gap.csv"
    )
    financialized_balance_sheet_evidence_gap = _read_csv(
        tables_dir / "ratewall_financialized_balance_sheet_evidence_gap.csv"
    )
    firm_cash_debt_maturity_evidence_gap = _read_csv(
        tables_dir / "ratewall_firm_cash_debt_maturity_evidence_gap.csv"
    )
    conventional_drag_channel_evidence_gap = _read_csv(
        tables_dir / "ratewall_conventional_drag_channel_evidence_gap.csv"
    )
    conventional_drag_source_design_gate = _read_csv(
        tables_dir / "ratewall_conventional_drag_source_design_gate.csv"
    )
    denominator_response_design_scaffold = _read_csv(
        tables_dir / "ratewall_denominator_response_design_scaffold.csv"
    )
    denominator_response_design_test_scaffold = _read_csv(
        tables_dir / "ratewall_denominator_response_design_test_scaffold.csv"
    )
    denominator_response_gate_attempt = _read_csv(
        tables_dir / "ratewall_denominator_response_gate_attempt.csv"
    )
    denominator_aligned_response_panel_scaffold = _read_csv(
        tables_dir / "ratewall_denominator_aligned_response_panel_scaffold.csv"
    )
    denominator_event_outcome_cell_diagnostic = _read_csv(
        tables_dir / "ratewall_denominator_event_outcome_cell_diagnostic.csv"
    )
    denominator_event_outcome_panel_value_diagnostic = _read_csv(
        tables_dir / "ratewall_denominator_event_outcome_panel_value_diagnostic.csv"
    )
    denominator_event_level_response_panel = _read_csv(
        tables_dir / "ratewall_denominator_event_level_response_panel.csv"
    )
    denominator_uncertainty_pass_fail_review = _read_csv(
        tables_dir / "ratewall_denominator_uncertainty_pass_fail_review.csv"
    )
    denominator_panel_design_test_diagnostic = _read_csv(
        tables_dir / "ratewall_denominator_panel_design_test_diagnostic.csv"
    )
    denominator_pretrend_placebo_diagnostic = _read_csv(
        tables_dir / "ratewall_denominator_pretrend_placebo_diagnostic.csv"
    )
    denominator_shock_relevance_diagnostic = _read_csv(
        tables_dir / "ratewall_denominator_shock_relevance_diagnostic.csv"
    )
    denominator_sign_consistency_diagnostic = _read_csv(
        tables_dir / "ratewall_denominator_sign_consistency_diagnostic.csv"
    )
    denominator_horizon_sensitivity_diagnostic = _read_csv(
        tables_dir / "ratewall_denominator_horizon_sensitivity_diagnostic.csv"
    )
    denominator_outlier_window_robustness_diagnostic = _read_csv(
        tables_dir / "ratewall_denominator_outlier_window_robustness_diagnostic.csv"
    )
    denominator_design_readiness_decision = _read_csv(
        tables_dir / "ratewall_denominator_design_readiness_decision.csv"
    )
    denominator_formal_design_test_result_scaffold = _read_csv(
        tables_dir / "ratewall_denominator_formal_design_test_result_scaffold.csv"
    )
    denominator_formal_design_test_result = _read_csv(
        tables_dir / "ratewall_denominator_formal_design_test_result.csv"
    )
    denominator_response_estimate_diagnostic = _read_csv(
        tables_dir / "ratewall_denominator_response_estimate_diagnostic.csv"
    )
    denominator_cross_source_design_validation = _read_csv(
        tables_dir / "ratewall_denominator_cross_source_design_validation.csv"
    )
    denominator_evidence_upgrade_source_design_requirement = _read_csv(
        tables_dir
        / "ratewall_denominator_evidence_upgrade_source_design_requirement.csv"
    )
    denominator_evidence_upgrade_priority_queue = _read_csv(
        tables_dir / "ratewall_denominator_evidence_upgrade_priority_queue.csv"
    )
    denominator_evidence_upgrade_tier1_workplan = _read_csv(
        tables_dir / "ratewall_denominator_evidence_upgrade_tier1_workplan.csv"
    )
    denominator_evidence_upgrade_blocker_resolution_matrix = _read_csv(
        tables_dir
        / "ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv"
    )
    denominator_evidence_upgrade_blocker_status_rollup = _read_csv(
        tables_dir / "ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv"
    )
    conventional_drag_evidence_tranche = _read_csv(
        tables_dir / "ratewall_conventional_drag_evidence_tranche.csv"
    )
    conventional_drag_demand_conversion_admission = _read_csv(
        tables_dir / "ratewall_conventional_drag_demand_conversion_admission.csv"
    )
    conventional_drag_calibration_route = _read_csv(
        tables_dir / "ratewall_conventional_drag_calibration_route.csv"
    )
    conventional_drag_research_parameterization_source_contract = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_parameterization_source_contract.csv"
    )
    conventional_drag_research_parameterization_source_frontier = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_parameterization_source_frontier.csv"
    )
    conventional_drag_research_payload_manifest = _read_csv(
        tables_dir / "ratewall_conventional_drag_research_payload_manifest.csv"
    )
    conventional_drag_research_parameterization_parser_status = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_parameterization_parser_status.csv"
    )
    conventional_drag_research_payload_inner_inventory = _read_csv(
        tables_dir / "ratewall_conventional_drag_research_payload_inner_inventory.csv"
    )
    conventional_drag_research_extraction_candidate = _read_csv(
        tables_dir / "ratewall_conventional_drag_research_extraction_candidate.csv"
    )
    conventional_drag_research_extraction_gate_audit = _read_csv(
        tables_dir / "ratewall_conventional_drag_research_extraction_gate_audit.csv"
    )
    conventional_drag_research_extraction_gate_detail = _read_csv(
        tables_dir / "ratewall_conventional_drag_research_extraction_gate_detail.csv"
    )
    conventional_drag_research_source_method_bridge = _read_csv(
        tables_dir / "ratewall_conventional_drag_research_source_method_bridge.csv"
    )
    conventional_drag_research_source_code_interpretation = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_source_code_interpretation.csv"
    )
    conventional_drag_research_extended_source_code_interpretation = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_extended_source_code_interpretation.csv"
    )
    conventional_drag_research_fspdp_coverage_candidate_scan = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_fspdp_coverage_candidate_scan.csv"
    )
    mir_component_aggregation_review = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_mir_component_aggregation_normalization_review.csv"
    )
    mir_component_source_variant_review = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_mir_component_source_variant_review.csv"
    )
    conventional_drag_research_source_unit_conversion_review = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_source_unit_conversion_review.csv"
    )
    conventional_drag_research_mir_replication_source_unit_audit = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_mir_replication_source_unit_audit.csv"
    )
    conventional_drag_research_mir_source_unit_transformation_contract = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_mir_source_unit_transformation_contract.csv"
    )
    conventional_drag_research_mir_target_horizon_reconciliation_contract = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_mir_target_horizon_reconciliation_contract.csv"
    )
    conventional_drag_research_mir_horizon_rekeying_candidate_review = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_mir_horizon_rekeying_candidate_review.csv"
    )
    conventional_drag_research_mir_h24_source_unit_audit = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_mir_h24_source_unit_audit.csv"
    )
    conventional_drag_research_mir_h24_8q_rekeying_review = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_mir_h24_8q_rekeying_review.csv"
    )
    conventional_drag_research_mir_4q8q_conversion_readiness_review = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_mir_4q8q_conversion_readiness_review.csv"
    )
    conventional_drag_research_policy_path_normalization_bridge_review = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_policy_path_normalization_bridge_review.csv"
    )
    policy_path_research_shock_source_evidence_protocol_review = _read_csv(
        tables_dir
        / "ratewall_policy_path_research_shock_source_evidence_protocol_review.csv"
    )
    policy_path_source_code_workbook_object_inventory = _read_csv(
        tables_dir
        / "ratewall_policy_path_source_code_workbook_object_inventory.csv"
    )
    policy_path_source_code_workbook_protocol_deep_review = _read_csv(
        tables_dir
        / "ratewall_policy_path_source_code_workbook_protocol_deep_review.csv"
    )
    policy_path_usmpd_pca_loading_backtransform_review = _read_csv(
        tables_dir
        / "ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv"
    )
    policy_path_usmpd_scalar_score_replication_review = _read_csv(
        tables_dir
        / "ratewall_policy_path_usmpd_scalar_score_replication_review.csv"
    )
    policy_path_usmpd_pca_backtransform_gate_review = _read_csv(
        tables_dir / "ratewall_policy_path_usmpd_pca_backtransform_gate_review.csv"
    )
    policy_path_usmpd_instrument_decomposition_design_review = _read_csv(
        tables_dir
        / "ratewall_policy_path_usmpd_instrument_decomposition_design_review.csv"
    )
    policy_path_bps_year_candidate_path_design_contract = _read_csv(
        tables_dir / "ratewall_policy_path_bps_year_candidate_path_design_contract.csv"
    )
    policy_path_formula_replication_source_review = _read_csv(
        tables_dir / "ratewall_policy_path_formula_replication_source_review.csv"
    )
    policy_path_reviewed_bps_year_protocol_gap_matrix = _read_csv(
        tables_dir / "ratewall_policy_path_reviewed_bps_year_protocol_gap_matrix.csv"
    )
    policy_path_protocol_source_acquisition_work_queue = _read_csv(
        tables_dir
        / "ratewall_policy_path_protocol_source_acquisition_work_queue.csv"
    )
    policy_path_protocol_source_parse_execution_review = _read_csv(
        tables_dir
        / "ratewall_policy_path_protocol_source_parse_execution_review.csv"
    )
    policy_path_source_parse_synthesis_queue = _read_csv(
        tables_dir / "ratewall_policy_path_source_parse_synthesis_queue.csv"
    )
    policy_path_source_parse_action_execution = _read_csv(
        tables_dir / "ratewall_policy_path_source_parse_action_execution.csv"
    )
    policy_path_deeper_parse_execution_review = _read_csv(
        tables_dir / "ratewall_policy_path_deeper_parse_execution_review.csv"
    )
    policy_path_protocol_candidate_draft_review = _read_csv(
        tables_dir / "ratewall_policy_path_protocol_candidate_draft_review.csv"
    )
    policy_path_protocol_missing_evidence_acquisition_queue = _read_csv(
        tables_dir
        / "ratewall_policy_path_protocol_missing_evidence_acquisition_queue.csv"
    )
    policy_path_protocol_missing_evidence_parse_execution_review = _read_csv(
        tables_dir
        / "ratewall_policy_path_protocol_missing_evidence_parse_execution_review.csv"
    )
    policy_path_protocol_authoring_readiness_matrix = _read_csv(
        tables_dir / "ratewall_policy_path_protocol_authoring_readiness_matrix.csv"
    )
    policy_path_protocol_field_authoring_contract = _read_csv(
        tables_dir / "ratewall_policy_path_protocol_field_authoring_contract.csv"
    )
    policy_path_field_evidence_resolution_queue = _read_csv(
        tables_dir / "ratewall_policy_path_field_evidence_resolution_queue.csv"
    )
    fspdp_component_source_manifest = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_fspdp_component_source_manifest.csv"
    )
    fspdp_component_share_panel = _read_csv(
        tables_dir / "ratewall_conventional_drag_fspdp_component_share_panel.csv"
    )
    fspdp_coverage_weight_requirement_review = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_fspdp_coverage_weight_requirement_review.csv"
    )
    fspdp_coverage_priority_search_queue = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_fspdp_coverage_priority_search_queue.csv"
    )
    fspdp_source_code_search_review = _read_csv(
        tables_dir / "ratewall_conventional_drag_fspdp_source_code_search_review.csv"
    )
    fspdp_external_source_acquisition_action_plan = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_fspdp_external_source_acquisition_action_plan.csv"
    )
    fspdp_official_component_source_acquisition_execution = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_fspdp_official_component_source_acquisition_execution.csv"
    )
    fspdp_research_side_action_plan_extraction_review = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_fspdp_research_side_action_plan_extraction_review.csv"
    )
    current_demand_gdp_share_source_manifest = _read_csv(
        tables_dir / "ratewall_current_demand_gdp_share_source_manifest.csv"
    )
    current_demand_gdp_share_panel = _read_csv(
        tables_dir / "ratewall_current_demand_gdp_share_panel.csv"
    )
    conventional_drag_current_demand_mapping_bridge = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_current_demand_mapping_bridge.csv"
    )
    conventional_drag_research_extraction_conversion_bridge = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_research_extraction_conversion_bridge.csv"
    )
    conventional_drag_local_macro_panel = _read_csv(
        tables_dir / "ratewall_conventional_drag_local_macro_panel.csv"
    )
    conventional_drag_local_shock_quarterly = _read_csv(
        tables_dir / "ratewall_conventional_drag_local_shock_quarterly.csv"
    )
    conventional_drag_local_lp_design = _read_csv(
        tables_dir / "ratewall_conventional_drag_local_lp_design.csv"
    )
    conventional_drag_local_lp_diagnostic = _read_csv(
        tables_dir / "ratewall_conventional_drag_local_lp_diagnostic.csv"
    )
    conventional_drag_local_lp_estimate_diagnostic = _read_csv(
        tables_dir / "ratewall_conventional_drag_local_lp_estimate_diagnostic.csv"
    )
    conventional_drag_local_lp_robustness_diagnostic = _read_csv(
        tables_dir / "ratewall_conventional_drag_local_lp_robustness_diagnostic.csv"
    )
    conventional_drag_local_lp_sample_window_audit = _read_csv(
        tables_dir / "ratewall_conventional_drag_local_lp_sample_window_audit.csv"
    )
    conventional_drag_local_lp_admission_audit = _read_csv(
        tables_dir / "ratewall_conventional_drag_local_lp_admission_audit.csv"
    )
    openicpsr_replication_package_source_manifest = _read_csv(
        tables_dir / "ratewall_openicpsr_replication_package_source_manifest.csv"
    )
    frbus_model_benchmark_simulation_readiness = _read_csv(
        tables_dir / "ratewall_frbus_model_benchmark_simulation_readiness.csv"
    )
    frbus_conventional_drag_benchmark_protocol = _read_csv(
        tables_dir / "ratewall_frbus_conventional_drag_benchmark_protocol.csv"
    )
    frbus_official_model_package_inventory = _read_csv(
        tables_dir / "ratewall_frbus_official_model_package_inventory.csv"
    )
    frbus_official_model_benchmark_simulation_protocol = _read_csv(
        tables_dir
        / "ratewall_frbus_official_model_benchmark_simulation_protocol.csv"
    )
    frbus_runtime_runner_preflight = _read_csv(
        tables_dir / "ratewall_frbus_runtime_runner_preflight.csv"
    )
    frbus_runtime_runner_output_slots = _read_csv(
        tables_dir / "ratewall_frbus_runtime_runner_output_slots.csv"
    )
    frbus_benchmark_comparison_mapping_contract = _read_csv(
        tables_dir / "ratewall_frbus_benchmark_comparison_mapping_contract.csv"
    )
    frbus_benchmark_output_slot_extension_review = _read_csv(
        tables_dir / "ratewall_frbus_benchmark_output_slot_extension_review.csv"
    )
    conventional_drag_source_unit_aggregation_blocker_bridge = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv"
    )
    conventional_drag_mirgk_targeted_gap_source_followup = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_mirgk_targeted_gap_source_followup.csv"
    )
    conventional_drag_promotion_contract_checklist = _read_csv(
        tables_dir
        / "ratewall_conventional_drag_promotion_contract_checklist.csv"
    )
    tdsp_current_demand_source_review = _read_csv(
        tables_dir / "ratewall_tdsp_current_demand_source_review.csv"
    )
    tdsp_current_demand_unit_conversion = _read_csv(
        tables_dir / "ratewall_tdsp_current_demand_unit_conversion.csv"
    )
    tdsp_current_demand_diagnostic_mapping = _read_csv(
        tables_dir / "ratewall_tdsp_current_demand_diagnostic_mapping.csv"
    )
    tdsp_policy_path_normalization_blocker = _read_csv(
        tables_dir / "ratewall_tdsp_policy_path_normalization_blocker.csv"
    )
    tdsp_current_demand_admission_audit = _read_csv(
        tables_dir / "ratewall_tdsp_current_demand_admission_audit.csv"
    )
    pce_dpi_source_refresh_contract = _read_csv(
        tables_dir / "ratewall_pce_dpi_source_refresh_contract.csv"
    )
    tdsp_pce_dpi_refresh_diagnostic_mapping = _read_csv(
        tables_dir / "ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv"
    )
    policy_path_exposure_vector_design_gate = _read_csv(
        tables_dir / "ratewall_policy_path_exposure_vector_design_gate.csv"
    )
    policy_path_reviewed_protocol_source_context = _read_csv(
        tables_dir / "ratewall_policy_path_reviewed_protocol_source_context.csv"
    )
    policy_path_protocol_source_acquisition_registry = _read_csv(
        tables_dir / "ratewall_policy_path_protocol_source_acquisition_registry.csv"
    )
    policy_path_protocol_source_acquisition_audit = _read_csv(
        tables_dir / "ratewall_policy_path_protocol_source_acquisition_audit.csv"
    )
    policy_path_protocol_review_inventory = _read_csv(
        tables_dir / "ratewall_policy_path_protocol_review_inventory.csv"
    )
    policy_path_protocol_review_audit = _read_csv(
        tables_dir / "ratewall_policy_path_protocol_review_audit.csv"
    )
    policy_path_mps_scalar_replication_diagnostic = _read_csv(
        tables_dir / "ratewall_policy_path_mps_scalar_replication_diagnostic.csv"
    )
    policy_path_mps_scalar_replication_audit = _read_csv(
        tables_dir / "ratewall_policy_path_mps_scalar_replication_audit.csv"
    )
    policy_path_bps_year_blocker_decision = _read_csv(
        tables_dir / "ratewall_policy_path_bps_year_blocker_decision.csv"
    )
    policy_path_bps_year_blocker_decision_audit = _read_csv(
        tables_dir / "ratewall_policy_path_bps_year_blocker_decision_audit.csv"
    )
    policy_path_event_level_candidate_vector = _read_csv(
        tables_dir / "ratewall_policy_path_event_level_candidate_vector.csv"
    )
    policy_path_event_level_candidate_vector_audit = _read_csv(
        tables_dir / "ratewall_policy_path_event_level_candidate_vector_audit.csv"
    )
    policy_path_contract_interval_source_review = _read_csv(
        tables_dir / "ratewall_policy_path_contract_interval_source_review.csv"
    )
    policy_path_contract_spec_acquisition_blocker = _read_csv(
        tables_dir / "ratewall_policy_path_contract_spec_acquisition_blocker.csv"
    )
    policy_path_bps_year_source_protocol = _read_csv(
        tables_dir / "ratewall_policy_path_bps_year_source_protocol.csv"
    )
    policy_path_normalization_source_manifest = _read_csv(
        tables_dir / "ratewall_policy_path_normalization_source_manifest.csv"
    )
    policy_path_bps_year_normalization_review = _read_csv(
        tables_dir / "ratewall_policy_path_bps_year_normalization_review.csv"
    )
    policy_path_source_cell_unit_contract_review = _read_csv(
        tables_dir / "ratewall_policy_path_source_cell_unit_contract_review.csv"
    )
    policy_path_bps_year_protocol_closure = _read_csv(
        tables_dir / "ratewall_policy_path_bps_year_protocol_closure.csv"
    )
    policy_path_normalization_leak_audit = _read_csv(
        tables_dir / "ratewall_policy_path_normalization_leak_audit.csv"
    )
    tdsp_pce_dpi_policy_path_admission_audit = _read_csv(
        tables_dir / "ratewall_tdsp_pce_dpi_policy_path_admission_audit.csv"
    )
    tdsp_diagnostic_family_completion_gate = _read_csv(
        tables_dir / "ratewall_tdsp_diagnostic_family_completion_gate.csv"
    )
    interest_channel_horizon_timing_matrix = _read_csv(
        tables_dir / "ratewall_interest_channel_horizon_timing_matrix.csv"
    )
    interest_channel_promotion_gate = _read_csv(
        tables_dir / "ratewall_interest_channel_promotion_gate.csv"
    )
    interest_channel_evidence_upgrade_queue = _read_csv(
        tables_dir / "ratewall_interest_channel_evidence_upgrade_queue.csv"
    )
    high_priority_interest_channel_source_bridge = _read_csv(
        tables_dir / "ratewall_high_priority_interest_channel_source_bridge.csv"
    )
    source_gate_prior_narrowing_decision = _read_csv(
        tables_dir / "ratewall_source_gate_prior_narrowing_decision.csv"
    )
    source_gate_exhaustion_closure = _read_csv(
        tables_dir / "ratewall_source_gate_exhaustion_closure.csv"
    )
    restricted_data_gate_spec = _read_csv(
        tables_dir / "ratewall_restricted_data_gate_spec.csv"
    )
    assumption_mode_post_closure_boundary_map = _read_csv(
        tables_dir / "ratewall_assumption_mode_post_closure_boundary_map.csv"
    )
    sibling_evidence_bridge = _read_csv(
        tables_dir / "ratewall_sibling_evidence_bridge.csv"
    )
    sibling_evidence_upgrade_queue = _read_csv(
        tables_dir / "ratewall_sibling_evidence_upgrade_queue.csv"
    )
    interest_channel_module_registry = _read_csv(
        tables_dir / "ratewall_interest_channel_module_registry.csv"
    )
    interest_channel_completion_matrix = _read_csv(
        tables_dir / "ratewall_interest_channel_completion_matrix.csv"
    )
    dynamic_scenario_paths = _read_csv(
        tables_dir / "ratewall_dynamic_scenario_paths.csv"
    )
    dynamic_scenario_path_consistency_diagnostic = _read_csv(
        tables_dir / "ratewall_dynamic_scenario_path_consistency_diagnostic.csv"
    )
    dynamic_offset_ratio_path = _read_csv(
        tables_dir / "ratewall_dynamic_offset_ratio_path.csv"
    )
    scenario_crossing_diagnostic = _read_csv(
        tables_dir / "ratewall_scenario_crossing_diagnostic.csv"
    )
    dynamic_sensitivity_frontier = _read_csv(
        tables_dir / "ratewall_dynamic_sensitivity_frontier.csv"
    )
    dynamic_scenario_family_registry = _read_csv(
        tables_dir / "ratewall_dynamic_scenario_family_registry.csv"
    )
    dynamic_uncertainty_envelope = _read_csv(
        tables_dir / "ratewall_dynamic_uncertainty_envelope.csv"
    )
    dynamic_crossing_robustness = _read_csv(
        tables_dir / "ratewall_dynamic_crossing_robustness.csv"
    )
    flow_stage_decomposition = _read_csv(
        tables_dir / "ratewall_flow_stage_decomposition.csv"
    )
    gross_interest_subchannels = _read_csv(
        tables_dir / "ratewall_gross_interest_subchannels.csv"
    )
    public_finance_adjustment = _read_csv(
        tables_dir / "ratewall_public_finance_adjustment.csv"
    )
    net_countervailing_channels = _read_csv(
        tables_dir / "ratewall_net_countervailing_channels.csv"
    )
    wall_hit_scenarios = _read_csv(tables_dir / "ratewall_wall_hit_scenarios.csv")
    threshold_solver = _read_csv(tables_dir / "ratewall_threshold_solver.csv")
    assumption_sensitivity = _read_csv(
        tables_dir / "ratewall_assumption_sensitivity.csv"
    )
    parameter_frontier = _read_csv(tables_dir / "ratewall_parameter_frontier.csv")
    minimum_conditions = _read_csv(
        tables_dir / "ratewall_minimum_conditions_to_hit_wall.csv"
    )
    hit_fragility_frontier = _read_csv(
        tables_dir / "ratewall_hit_fragility_frontier.csv"
    )
    frontier_driver_ranking = _read_csv(
        tables_dir / "ratewall_frontier_driver_ranking.csv"
    )
    assumption_mode_driver_dominance_matrix = _read_csv(
        tables_dir / "ratewall_assumption_mode_driver_dominance_matrix.csv"
    )
    assumption_mode_pairwise_sensitivity_matrix = _read_csv(
        tables_dir / "ratewall_assumption_mode_pairwise_sensitivity_matrix.csv"
    )
    backend_invariant_guardrail_audit = _read_csv(
        tables_dir / "ratewall_backend_invariant_guardrail_audit.csv"
    )
    backend_completion_verdict = _read_csv(
        tables_dir / "ratewall_backend_completion_verdict.csv"
    )
    paper_channel_map = _read_csv(tables_dir / "ratewall_paper_channel_map.csv")
    paper_canonical_scenario_results = _read_csv(
        tables_dir / "ratewall_paper_canonical_scenario_results.csv"
    )
    paper_tdc_dynamic_contribution = _read_csv(
        tables_dir / "ratewall_paper_tdc_dynamic_contribution.csv"
    )
    paper_parameter_justification = _read_csv(
        tables_dir / "ratewall_paper_parameter_justification.csv"
    )
    paper_sensitivity_summary = _read_csv(
        tables_dir / "ratewall_paper_sensitivity_summary.csv"
    )
    paper_disabled_claims_appendix = _read_csv(
        tables_dir / "ratewall_paper_disabled_claims_appendix.csv"
    )
    paper_financialization_interpretation = _read_csv(
        tables_dir / "ratewall_paper_financialization_interpretation.csv"
    )
    paper_support_invariant_audit = _read_csv(
        tables_dir / "ratewall_paper_support_invariant_audit.csv"
    )
    backend_accounting_identity_audit = _read_csv(
        tables_dir / "ratewall_backend_accounting_identity_audit.csv"
    )
    paper_scenario_accounting_bridge = _read_csv(
        tables_dir / "ratewall_paper_scenario_accounting_bridge.csv"
    )
    paper_dynamic_scenario_summary = _read_csv(
        tables_dir / "ratewall_paper_dynamic_scenario_summary.csv"
    )
    conventional_drag_decomposition = _read_csv(
        tables_dir / "ratewall_conventional_drag_decomposition.csv"
    )
    split_denominator_comparison = _read_csv(
        tables_dir / "ratewall_split_denominator_comparison.csv"
    )
    denominator_sensitivity = _read_csv(
        tables_dir / "ratewall_denominator_sensitivity.csv"
    )
    split_denominator_uncertainty = _read_csv(
        tables_dir / "ratewall_split_denominator_uncertainty.csv"
    )
    split_denominator_regime_stability = _read_csv(
        tables_dir / "ratewall_split_denominator_regime_stability.csv"
    )
    denominator_literature_matrix = _read_csv(
        tables_dir / "ratewall_denominator_literature_matrix.csv"
    )
    split_denominator_joint_uncertainty = _read_csv(
        tables_dir / "ratewall_split_denominator_joint_uncertainty.csv"
    )
    split_denominator_joint_regime_stability = _read_csv(
        tables_dir / "ratewall_split_denominator_joint_regime_stability.csv"
    )
    denominator_classifier_comparison = _read_csv(
        tables_dir / "ratewall_denominator_classifier_comparison.csv"
    )
    backend_model_readiness_gate = _read_csv(
        tables_dir / "ratewall_backend_model_readiness_gate.csv"
    )
    chapter_readiness_self_audit = _read_csv(
        tables_dir / "ratewall_chapter_readiness_self_audit.csv"
    )
    financialized_balance_sheet_channel = _read_csv(
        tables_dir / "ratewall_financialized_balance_sheet_channel.csv"
    )
    financialization_proxy_registry = _read_csv(
        tables_dir / "ratewall_financialization_proxy_registry.csv"
    )
    financialization_proxy_source_gate = _read_csv(
        tables_dir / "ratewall_financialization_proxy_source_gate.csv"
    )
    financialization_source_gate = _read_csv(
        tables_dir / "ratewall_financialization_source_gate.csv"
    )
    financialization_restricted_protocols = _read_csv(
        tables_dir / "ratewall_financialization_restricted_protocols.csv"
    )
    financialization_double_count_audit = _read_csv(
        tables_dir / "ratewall_financialization_double_count_audit.csv"
    )
    financialization_overlap_audit = _read_csv(
        tables_dir / "ratewall_financialization_overlap_audit.csv"
    )
    financialization_artifact_traceability_matrix = _read_csv(
        tables_dir / "ratewall_financialization_artifact_traceability_matrix.csv"
    )
    equity_transmission_channel_map = _read_csv(
        tables_dir / "ratewall_equity_transmission_channel_map.csv"
    )
    equity_exposure_matrix = _read_csv(
        tables_dir / "ratewall_equity_exposure_matrix.csv"
    )
    equity_sensitivity_diagnostic = _read_csv(
        tables_dir / "ratewall_equity_sensitivity_diagnostic.csv"
    )
    equity_claim_status = _read_csv(tables_dir / "ratewall_equity_claim_status.csv")
    equity_evidence_workplan = _read_csv(
        tables_dir / "ratewall_equity_evidence_workplan.csv"
    )
    parameter_packs = _read_csv(tables_dir / "ratewall_parameter_packs.csv")
    frontier_summary = _read_csv(tables_dir / "ratewall_frontier_summary.csv")
    regime_map = _read_csv(tables_dir / "ratewall_regime_map.csv")
    assumption_mode_interpretation = _read_csv(
        tables_dir / "ratewall_assumption_mode_interpretation.csv"
    )
    prior_stack_diagnostic = _read_csv(
        tables_dir / "ratewall_prior_stack_diagnostic.csv"
    )
    scenario_ladder = _read_csv(tables_dir / "ratewall_scenario_ladder.csv")
    model_adequacy_matrix = _read_csv(tables_dir / "ratewall_model_adequacy_matrix.csv")
    assumption_mode_audit = _read_csv(
        tables_dir / "ratewall_assumption_mode_claim_boundary_audit.csv"
    )
    financialization_pressure = _read_csv(
        tables_dir / "ratewall_financialization_pressure.csv"
    )
    financialization_evidence_appendix = _read_csv(
        tables_dir / "ratewall_financialization_pressure_evidence_appendix.csv"
    )
    safe_asset_retention_context = _read_csv(
        tables_dir / "ratewall_safe_asset_retention_context.csv"
    )
    safe_asset_retention_evidence = _read_csv(
        tables_dir / "ratewall_safe_asset_retention_evidence_appendix.csv"
    )
    contractionary_benchmark_calibration = _read_csv(
        tables_dir / "ratewall_contractionary_benchmark_calibration.csv"
    )
    threshold_uncertainty_bands = _read_csv(
        tables_dir / "ratewall_threshold_uncertainty_bands.csv"
    )
    historical_threshold_validation = _read_csv(
        tables_dir / "ratewall_historical_threshold_validation.csv"
    )
    policy_boundary_synthesis = _read_csv(
        tables_dir / "ratewall_policy_boundary_synthesis.csv"
    )
    blocker_resolution_ledger = _read_csv(
        tables_dir / "ratewall_blocker_resolution_ledger.csv"
    )
    publication_claim_decision = _read_csv(
        tables_dir / "ratewall_publication_claim_decision.csv"
    )
    final_blocker_ledger = _read_csv(tables_dir / "ratewall_final_blocker_ledger.csv")
    release_16_source_resolution = _read_csv(
        tables_dir / "ratewall_release_16_source_resolution_closeout.csv"
    )
    release_16_no_further_promotion = _read_csv(
        tables_dir / "ratewall_release_16_no_further_promotion_ledger.csv"
    )
    release_17_external_review = _read_csv(
        tables_dir / "ratewall_release_17_external_review_audit.csv"
    )
    release_17_publication_polish = _read_csv(
        tables_dir / "ratewall_release_17_publication_polish_qa.csv"
    )
    release_17_blocker_reopen = _read_csv(
        tables_dir / "ratewall_release_17_blocker_reopen_decision.csv"
    )
    release_18_live_refresh = _read_csv(
        tables_dir / "ratewall_release_18_live_refresh_robustness_audit.csv"
    )
    buyer_case_sign_matrix = _read_csv(
        tables_dir / "ratewall_buyer_case_sign_matrix.csv"
    )
    recipient_mpc_scenarios = _read_csv(
        tables_dir / "ratewall_recipient_mpc_scenario_scaffold.csv"
    )
    release_19_invariants = _read_csv(
        tables_dir / "ratewall_release_19_accounting_invariant_audit.csv"
    )
    release_19_methodology = _read_csv(
        tables_dir / "ratewall_release_19_post_audit_methodology_audit.csv"
    )
    release_20_activity_benchmark = _read_csv(
        tables_dir / "ratewall_release_20_activity_demand_benchmark.csv"
    )
    release_20_lp_diagnostics = _read_csv(
        tables_dir / "ratewall_release_20_state_dependent_lp_diagnostics.csv"
    )
    release_20_decision = _read_csv(
        tables_dir / "ratewall_release_20_benchmark_submission_decision.csv"
    )
    release_21_live_refresh = _read_csv(
        tables_dir / "ratewall_release_21_live_refresh_endpoint_audit.csv"
    )
    release_21_benchmark_gate = _read_csv(
        tables_dir / "ratewall_release_21_final_benchmark_gate.csv"
    )
    release_21_backend_invariants = _read_csv(
        tables_dir / "ratewall_release_21_backend_invariant_audit.csv"
    )
    release_22_source_repro_audit = _read_csv(
        tables_dir / "ratewall_release_22_source_repro_accounting_audit.csv"
    )
    release_22_source_gate = _read_csv(
        tables_dir / "ratewall_release_22_core_output_source_gate.csv"
    )
    release_22_hash_manifest_path = (
        tables_dir / "ratewall_release_22_reproducibility_hash_manifest.json"
    )
    release_22_hash_manifest = (
        json.loads(release_22_hash_manifest_path.read_text(encoding="utf-8"))
        if release_22_hash_manifest_path.exists()
        else {}
    )
    release_23_source_status = _read_csv(
        tables_dir / "ratewall_release_23_source_status_propagation_audit.csv"
    )
    release_23_latest_as_of = _read_csv(
        tables_dir / "ratewall_release_23_latest_as_of_semantics_audit.csv"
    )
    release_23_threshold_mechanics = _read_csv(
        tables_dir / "ratewall_release_23_threshold_mechanics_feasibility_audit.csv"
    )
    release_23_calibration_plausibility = _read_csv(
        tables_dir / "ratewall_release_23_calibration_plausibility_audit.csv"
    )
    release_23_recipient_base = _read_csv(
        tables_dir / "ratewall_release_23_recipient_base_consistency_audit.csv"
    )
    threshold_claim_audit = _read_csv(
        tables_dir / "ratewall_threshold_claim_boundary_audit.csv"
    )
    tdc_source_coverage = _read_csv(tables_dir / "ratewall_tdc_source_coverage.csv")
    tdc_claim_audit = _read_csv(tables_dir / "ratewall_tdc_claim_boundary_audit.csv")
    return {
        "snapshot_bundle": snapshot_bundle,
        "provenance_path": provenance_path,
        "provenance": provenance,
        "sources": sources,
        "empirical_results": empirical_results,
        "outcome_panel": outcome_panel,
        "causal_audit": causal_audit,
        "causal_blocker": causal_blocker,
        "support_diagnostics": support_diagnostics,
        "event_study_robustness": event_study_robustness,
        "submission_decision": submission_decision,
        "dynamic_lp_feasibility": dynamic_lp_feasibility,
        "proxy_svar_feasibility": proxy_svar_feasibility,
        "dynamic_causal_blocker": dynamic_causal_blocker,
        "event_study_hac": event_study_hac,
        "pretrend_placebo": pretrend_placebo,
        "promotion_contract": promotion_contract,
        "release_4_blocker": release_4_blocker,
        "release_4_checklist": release_4_checklist,
        "external_review_issue_matrix": external_review_issue_matrix,
        "journal_manifest": journal_manifest,
        "journal_manifest_path": journal_manifest_path,
        "release_4_manifest": release_4_manifest,
        "release_4_manifest_path": release_4_manifest_path,
        "controlled_dynamic_lp_panel": controlled_dynamic_lp_panel,
        "controlled_dynamic_lp_results": controlled_dynamic_lp_results,
        "controlled_dynamic_lp_support": controlled_dynamic_lp_support,
        "release_5_decision": release_5_decision,
        "release_5_proxy_blocker": release_5_proxy_blocker,
        "release_5_manifest": release_5_manifest,
        "release_5_manifest_path": release_5_manifest_path,
        "proxy_svar_system_panel": proxy_svar_system_panel,
        "proxy_svar_relevance": proxy_svar_relevance,
        "proxy_svar_residual": proxy_svar_residual,
        "proxy_svar_timing": proxy_svar_timing,
        "release_6_decision": release_6_decision,
        "release_6_proxy_blocker": release_6_proxy_blocker,
        "release_6_valuation_frontier": release_6_valuation_frontier,
        "release_6_manifest": release_6_manifest,
        "release_6_manifest_path": release_6_manifest_path,
        "release_7_lag_selection": release_7_lag_selection,
        "release_7_reduced_form_estimates": release_7_reduced_form_estimates,
        "release_7_residual_covariance": release_7_residual_covariance,
        "release_7_proxy_support": release_7_proxy_support,
        "release_7_timing_audit": release_7_timing_audit,
        "release_7_promotion_contract": release_7_promotion_contract,
        "release_7_decision": release_7_decision,
        "release_7_proxy_blocker": release_7_proxy_blocker,
        "release_7_manifest": release_7_manifest,
        "release_7_manifest_path": release_7_manifest_path,
        "release_8_proxy_specification": release_8_proxy_specification,
        "release_8_structural_gap": release_8_structural_gap,
        "release_8_nonpromotion_proof": release_8_nonpromotion_proof,
        "release_8_decision": release_8_decision,
        "release_8_manifest": release_8_manifest,
        "release_8_manifest_path": release_8_manifest_path,
        "release_9_proxy_registry": release_9_proxy_registry,
        "release_9_proxy_support": release_9_proxy_support,
        "release_9_decision": release_9_decision,
        "release_9_nonpromotion_proof": release_9_nonpromotion_proof,
        "release_9_manifest": release_9_manifest,
        "release_9_manifest_path": release_9_manifest_path,
        "robustness_manifest": robustness_manifest,
        "robustness_manifest_path": robustness_manifest_path,
        "impulse": impulse,
        "scenarios": scenarios,
        "metrics": metrics,
        "dashboard": dashboard,
        "limitations": limitations,
        "valuation_gate": valuation_gate,
        "pricing_audit": pricing_audit,
        "readiness": readiness,
        "tdc_ledger": tdc_ledger,
        "tdc_impulse": tdc_impulse,
        "tdc_historical_panel": tdc_historical_panel,
        "deposit_pricing_pass_through": deposit_pricing_pass_through,
        "tdc_historical_reconciliation": tdc_historical_reconciliation,
        "threshold_simulation": threshold_simulation,
        "threshold_calibration_ranges": threshold_calibration_ranges,
        "threshold_calibrated_simulation": threshold_calibrated_simulation,
        "du_ru_tga_calibration_bridge": du_ru_tga_calibration_bridge,
        "assumption_sets": assumption_sets,
        "condition_frontier": condition_frontier,
        "offset_decomposition": offset_decomposition,
        "public_impulse_factorization": public_impulse_factorization,
        "public_liability_repricing_ladder": public_liability_repricing_ladder,
        "public_liability_repricing_evidence_bridge": (
            public_liability_repricing_evidence_bridge
        ),
        "public_liability_repricing_reconciliation_gap": (
            public_liability_repricing_reconciliation_gap
        ),
        "mspd_table3_bucket_repricing_gate": mspd_table3_bucket_repricing_gate,
        "interest_recipient_leakage_bridge": interest_recipient_leakage_bridge,
        "interest_recipient_leakage_evidence_gap": (
            interest_recipient_leakage_evidence_gap
        ),
        "treasury_recipient_leakage_source_gate": (
            treasury_recipient_leakage_source_gate
        ),
        "public_finance_timing_path": public_finance_timing_path,
        "public_finance_timing_evidence_gap": (public_finance_timing_evidence_gap),
        "public_finance_timing_design_test_scaffold": (
            public_finance_timing_design_test_scaffold
        ),
        "safe_yield_offset_drag_pairing_gap": safe_yield_offset_drag_pairing_gap,
        "bnpl_zero_interest_float_evidence_gap": (
            bnpl_zero_interest_float_evidence_gap
        ),
        "financialized_balance_sheet_evidence_gap": (
            financialized_balance_sheet_evidence_gap
        ),
        "firm_cash_debt_maturity_evidence_gap": (firm_cash_debt_maturity_evidence_gap),
        "conventional_drag_channel_evidence_gap": (
            conventional_drag_channel_evidence_gap
        ),
        "conventional_drag_source_design_gate": (conventional_drag_source_design_gate),
        "denominator_response_design_scaffold": (denominator_response_design_scaffold),
        "denominator_response_design_test_scaffold": (
            denominator_response_design_test_scaffold
        ),
        "denominator_response_gate_attempt": denominator_response_gate_attempt,
        "denominator_aligned_response_panel_scaffold": (
            denominator_aligned_response_panel_scaffold
        ),
        "denominator_event_outcome_cell_diagnostic": (
            denominator_event_outcome_cell_diagnostic
        ),
        "denominator_event_outcome_panel_value_diagnostic": (
            denominator_event_outcome_panel_value_diagnostic
        ),
        "denominator_event_level_response_panel": (
            denominator_event_level_response_panel
        ),
        "denominator_uncertainty_pass_fail_review": (
            denominator_uncertainty_pass_fail_review
        ),
        "denominator_panel_design_test_diagnostic": (
            denominator_panel_design_test_diagnostic
        ),
        "denominator_pretrend_placebo_diagnostic": (
            denominator_pretrend_placebo_diagnostic
        ),
        "denominator_shock_relevance_diagnostic": (
            denominator_shock_relevance_diagnostic
        ),
        "denominator_sign_consistency_diagnostic": (
            denominator_sign_consistency_diagnostic
        ),
        "denominator_horizon_sensitivity_diagnostic": (
            denominator_horizon_sensitivity_diagnostic
        ),
        "denominator_outlier_window_robustness_diagnostic": (
            denominator_outlier_window_robustness_diagnostic
        ),
        "denominator_design_readiness_decision": (
            denominator_design_readiness_decision
        ),
        "denominator_formal_design_test_result_scaffold": (
            denominator_formal_design_test_result_scaffold
        ),
        "denominator_formal_design_test_result": (
            denominator_formal_design_test_result
        ),
        "denominator_response_estimate_diagnostic": (
            denominator_response_estimate_diagnostic
        ),
        "denominator_cross_source_design_validation": (
            denominator_cross_source_design_validation
        ),
        "denominator_evidence_upgrade_source_design_requirement": (
            denominator_evidence_upgrade_source_design_requirement
        ),
        "denominator_evidence_upgrade_priority_queue": (
            denominator_evidence_upgrade_priority_queue
        ),
        "denominator_evidence_upgrade_tier1_workplan": (
            denominator_evidence_upgrade_tier1_workplan
        ),
        "denominator_evidence_upgrade_blocker_resolution_matrix": (
            denominator_evidence_upgrade_blocker_resolution_matrix
        ),
        "denominator_evidence_upgrade_blocker_status_rollup": (
            denominator_evidence_upgrade_blocker_status_rollup
        ),
        "conventional_drag_evidence_tranche": conventional_drag_evidence_tranche,
        "conventional_drag_demand_conversion_admission": (
            conventional_drag_demand_conversion_admission
        ),
        "conventional_drag_calibration_route": (
            conventional_drag_calibration_route
        ),
        "conventional_drag_research_parameterization_source_contract": (
            conventional_drag_research_parameterization_source_contract
        ),
        "conventional_drag_research_parameterization_source_frontier": (
            conventional_drag_research_parameterization_source_frontier
        ),
        "conventional_drag_research_payload_manifest": (
            conventional_drag_research_payload_manifest
        ),
        "conventional_drag_research_parameterization_parser_status": (
            conventional_drag_research_parameterization_parser_status
        ),
        "conventional_drag_research_payload_inner_inventory": (
            conventional_drag_research_payload_inner_inventory
        ),
        "conventional_drag_research_extraction_candidate": (
            conventional_drag_research_extraction_candidate
        ),
        "conventional_drag_research_extraction_gate_audit": (
            conventional_drag_research_extraction_gate_audit
        ),
        "conventional_drag_research_extraction_gate_detail": (
            conventional_drag_research_extraction_gate_detail
        ),
        "conventional_drag_research_source_method_bridge": (
            conventional_drag_research_source_method_bridge
        ),
        "conventional_drag_research_source_code_interpretation": (
            conventional_drag_research_source_code_interpretation
        ),
        "conventional_drag_research_extended_source_code_interpretation": (
            conventional_drag_research_extended_source_code_interpretation
        ),
        "conventional_drag_research_fspdp_coverage_candidate_scan": (
            conventional_drag_research_fspdp_coverage_candidate_scan
        ),
        "mir_component_aggregation_review": mir_component_aggregation_review,
        "mir_component_source_variant_review": (
            mir_component_source_variant_review
        ),
        "conventional_drag_research_source_unit_conversion_review": (
            conventional_drag_research_source_unit_conversion_review
        ),
        "conventional_drag_research_mir_replication_source_unit_audit": (
            conventional_drag_research_mir_replication_source_unit_audit
        ),
        "conventional_drag_research_mir_source_unit_transformation_contract": (
            conventional_drag_research_mir_source_unit_transformation_contract
        ),
        "conventional_drag_research_mir_target_horizon_reconciliation_contract": (
            conventional_drag_research_mir_target_horizon_reconciliation_contract
        ),
        "conventional_drag_research_mir_horizon_rekeying_candidate_review": (
            conventional_drag_research_mir_horizon_rekeying_candidate_review
        ),
        "conventional_drag_research_mir_h24_source_unit_audit": (
            conventional_drag_research_mir_h24_source_unit_audit
        ),
        "conventional_drag_research_mir_h24_8q_rekeying_review": (
            conventional_drag_research_mir_h24_8q_rekeying_review
        ),
        "conventional_drag_research_mir_4q8q_conversion_readiness_review": (
            conventional_drag_research_mir_4q8q_conversion_readiness_review
        ),
        "conventional_drag_research_policy_path_normalization_bridge_review": (
            conventional_drag_research_policy_path_normalization_bridge_review
        ),
        "policy_path_research_shock_source_evidence_protocol_review": (
            policy_path_research_shock_source_evidence_protocol_review
        ),
        "policy_path_source_code_workbook_object_inventory": (
            policy_path_source_code_workbook_object_inventory
        ),
        "policy_path_source_code_workbook_protocol_deep_review": (
            policy_path_source_code_workbook_protocol_deep_review
        ),
        "policy_path_usmpd_pca_loading_backtransform_review": (
            policy_path_usmpd_pca_loading_backtransform_review
        ),
        "policy_path_usmpd_scalar_score_replication_review": (
            policy_path_usmpd_scalar_score_replication_review
        ),
        "policy_path_usmpd_pca_backtransform_gate_review": (
            policy_path_usmpd_pca_backtransform_gate_review
        ),
        "policy_path_usmpd_instrument_decomposition_design_review": (
            policy_path_usmpd_instrument_decomposition_design_review
        ),
        "policy_path_bps_year_candidate_path_design_contract": (
            policy_path_bps_year_candidate_path_design_contract
        ),
        "policy_path_formula_replication_source_review": (
            policy_path_formula_replication_source_review
        ),
        "policy_path_reviewed_bps_year_protocol_gap_matrix": (
            policy_path_reviewed_bps_year_protocol_gap_matrix
        ),
        "policy_path_protocol_source_acquisition_work_queue": (
            policy_path_protocol_source_acquisition_work_queue
        ),
        "policy_path_protocol_source_parse_execution_review": (
            policy_path_protocol_source_parse_execution_review
        ),
        "policy_path_source_parse_synthesis_queue": (
            policy_path_source_parse_synthesis_queue
        ),
        "policy_path_source_parse_action_execution": (
            policy_path_source_parse_action_execution
        ),
        "policy_path_deeper_parse_execution_review": (
            policy_path_deeper_parse_execution_review
        ),
        "policy_path_protocol_candidate_draft_review": (
            policy_path_protocol_candidate_draft_review
        ),
        "policy_path_protocol_missing_evidence_acquisition_queue": (
            policy_path_protocol_missing_evidence_acquisition_queue
        ),
        "policy_path_protocol_missing_evidence_parse_execution_review": (
            policy_path_protocol_missing_evidence_parse_execution_review
        ),
        "policy_path_protocol_authoring_readiness_matrix": (
            policy_path_protocol_authoring_readiness_matrix
        ),
        "policy_path_protocol_field_authoring_contract": (
            policy_path_protocol_field_authoring_contract
        ),
        "policy_path_field_evidence_resolution_queue": (
            policy_path_field_evidence_resolution_queue
        ),
        "fspdp_component_source_manifest": fspdp_component_source_manifest,
        "fspdp_component_share_panel": fspdp_component_share_panel,
        "fspdp_coverage_weight_requirement_review": (
            fspdp_coverage_weight_requirement_review
        ),
        "fspdp_coverage_priority_search_queue": (
            fspdp_coverage_priority_search_queue
        ),
        "fspdp_source_code_search_review": fspdp_source_code_search_review,
        "fspdp_external_source_acquisition_action_plan": (
            fspdp_external_source_acquisition_action_plan
        ),
        "fspdp_official_component_source_acquisition_execution": (
            fspdp_official_component_source_acquisition_execution
        ),
        "fspdp_research_side_action_plan_extraction_review": (
            fspdp_research_side_action_plan_extraction_review
        ),
        "current_demand_gdp_share_source_manifest": (
            current_demand_gdp_share_source_manifest
        ),
        "current_demand_gdp_share_panel": current_demand_gdp_share_panel,
        "conventional_drag_current_demand_mapping_bridge": (
            conventional_drag_current_demand_mapping_bridge
        ),
        "conventional_drag_research_extraction_conversion_bridge": (
            conventional_drag_research_extraction_conversion_bridge
        ),
        "conventional_drag_local_macro_panel": conventional_drag_local_macro_panel,
        "conventional_drag_local_shock_quarterly": (
            conventional_drag_local_shock_quarterly
        ),
        "conventional_drag_local_lp_design": conventional_drag_local_lp_design,
        "conventional_drag_local_lp_diagnostic": (
            conventional_drag_local_lp_diagnostic
        ),
        "conventional_drag_local_lp_estimate_diagnostic": (
            conventional_drag_local_lp_estimate_diagnostic
        ),
        "conventional_drag_local_lp_robustness_diagnostic": (
            conventional_drag_local_lp_robustness_diagnostic
        ),
        "conventional_drag_local_lp_sample_window_audit": (
            conventional_drag_local_lp_sample_window_audit
        ),
        "conventional_drag_local_lp_admission_audit": (
            conventional_drag_local_lp_admission_audit
        ),
        "openicpsr_replication_package_source_manifest": (
            openicpsr_replication_package_source_manifest
        ),
        "frbus_model_benchmark_simulation_readiness": (
            frbus_model_benchmark_simulation_readiness
        ),
        "frbus_conventional_drag_benchmark_protocol": (
            frbus_conventional_drag_benchmark_protocol
        ),
        "frbus_official_model_package_inventory": (
            frbus_official_model_package_inventory
        ),
        "frbus_official_model_benchmark_simulation_protocol": (
            frbus_official_model_benchmark_simulation_protocol
        ),
        "frbus_runtime_runner_preflight": frbus_runtime_runner_preflight,
        "frbus_runtime_runner_output_slots": frbus_runtime_runner_output_slots,
        "frbus_benchmark_comparison_mapping_contract": (
            frbus_benchmark_comparison_mapping_contract
        ),
        "frbus_benchmark_output_slot_extension_review": (
            frbus_benchmark_output_slot_extension_review
        ),
        "conventional_drag_source_unit_aggregation_blocker_bridge": (
            conventional_drag_source_unit_aggregation_blocker_bridge
        ),
        "conventional_drag_mirgk_targeted_gap_source_followup": (
            conventional_drag_mirgk_targeted_gap_source_followup
        ),
        "conventional_drag_promotion_contract_checklist": (
            conventional_drag_promotion_contract_checklist
        ),
        "tdsp_current_demand_source_review": tdsp_current_demand_source_review,
        "tdsp_current_demand_unit_conversion": (
            tdsp_current_demand_unit_conversion
        ),
        "tdsp_current_demand_diagnostic_mapping": (
            tdsp_current_demand_diagnostic_mapping
        ),
        "tdsp_policy_path_normalization_blocker": (
            tdsp_policy_path_normalization_blocker
        ),
        "tdsp_current_demand_admission_audit": (
            tdsp_current_demand_admission_audit
        ),
        "pce_dpi_source_refresh_contract": pce_dpi_source_refresh_contract,
        "tdsp_pce_dpi_refresh_diagnostic_mapping": (
            tdsp_pce_dpi_refresh_diagnostic_mapping
        ),
        "policy_path_exposure_vector_design_gate": (
            policy_path_exposure_vector_design_gate
        ),
        "policy_path_reviewed_protocol_source_context": (
            policy_path_reviewed_protocol_source_context
        ),
        "policy_path_protocol_source_acquisition_registry": (
            policy_path_protocol_source_acquisition_registry
        ),
        "policy_path_protocol_source_acquisition_audit": (
            policy_path_protocol_source_acquisition_audit
        ),
        "policy_path_protocol_review_inventory": (
            policy_path_protocol_review_inventory
        ),
        "policy_path_protocol_review_audit": policy_path_protocol_review_audit,
        "policy_path_mps_scalar_replication_diagnostic": (
            policy_path_mps_scalar_replication_diagnostic
        ),
        "policy_path_mps_scalar_replication_audit": (
            policy_path_mps_scalar_replication_audit
        ),
        "policy_path_bps_year_blocker_decision": (
            policy_path_bps_year_blocker_decision
        ),
        "policy_path_bps_year_blocker_decision_audit": (
            policy_path_bps_year_blocker_decision_audit
        ),
        "policy_path_event_level_candidate_vector": policy_path_event_level_candidate_vector,
        "policy_path_event_level_candidate_vector_audit": (
            policy_path_event_level_candidate_vector_audit
        ),
        "policy_path_contract_interval_source_review": (
            policy_path_contract_interval_source_review
        ),
        "policy_path_contract_spec_acquisition_blocker": (
            policy_path_contract_spec_acquisition_blocker
        ),
        "policy_path_bps_year_source_protocol": (
            policy_path_bps_year_source_protocol
        ),
        "policy_path_normalization_source_manifest": (
            policy_path_normalization_source_manifest
        ),
        "policy_path_bps_year_normalization_review": (
            policy_path_bps_year_normalization_review
        ),
        "policy_path_source_cell_unit_contract_review": (
            policy_path_source_cell_unit_contract_review
        ),
        "policy_path_bps_year_protocol_closure": (
            policy_path_bps_year_protocol_closure
        ),
        "policy_path_normalization_leak_audit": (
            policy_path_normalization_leak_audit
        ),
        "tdsp_pce_dpi_policy_path_admission_audit": (
            tdsp_pce_dpi_policy_path_admission_audit
        ),
        "tdsp_diagnostic_family_completion_gate": (
            tdsp_diagnostic_family_completion_gate
        ),
        "interest_channel_horizon_timing_matrix": (
            interest_channel_horizon_timing_matrix
        ),
        "interest_channel_promotion_gate": interest_channel_promotion_gate,
        "interest_channel_evidence_upgrade_queue": (
            interest_channel_evidence_upgrade_queue
        ),
        "high_priority_interest_channel_source_bridge": (
            high_priority_interest_channel_source_bridge
        ),
        "source_gate_prior_narrowing_decision": (source_gate_prior_narrowing_decision),
        "source_gate_exhaustion_closure": source_gate_exhaustion_closure,
        "restricted_data_gate_spec": restricted_data_gate_spec,
        "assumption_mode_post_closure_boundary_map": (
            assumption_mode_post_closure_boundary_map
        ),
        "sibling_evidence_bridge": sibling_evidence_bridge,
        "sibling_evidence_upgrade_queue": sibling_evidence_upgrade_queue,
        "interest_channel_module_registry": interest_channel_module_registry,
        "interest_channel_completion_matrix": interest_channel_completion_matrix,
        "dynamic_scenario_paths": dynamic_scenario_paths,
        "dynamic_scenario_path_consistency_diagnostic": (
            dynamic_scenario_path_consistency_diagnostic
        ),
        "dynamic_offset_ratio_path": dynamic_offset_ratio_path,
        "scenario_crossing_diagnostic": scenario_crossing_diagnostic,
        "dynamic_sensitivity_frontier": dynamic_sensitivity_frontier,
        "dynamic_scenario_family_registry": dynamic_scenario_family_registry,
        "dynamic_uncertainty_envelope": dynamic_uncertainty_envelope,
        "dynamic_crossing_robustness": dynamic_crossing_robustness,
        "flow_stage_decomposition": flow_stage_decomposition,
        "gross_interest_subchannels": gross_interest_subchannels,
        "public_finance_adjustment": public_finance_adjustment,
        "net_countervailing_channels": net_countervailing_channels,
        "wall_hit_scenarios": wall_hit_scenarios,
        "threshold_solver": threshold_solver,
        "assumption_sensitivity": assumption_sensitivity,
        "parameter_frontier": parameter_frontier,
        "minimum_conditions": minimum_conditions,
        "hit_fragility_frontier": hit_fragility_frontier,
        "frontier_driver_ranking": frontier_driver_ranking,
        "assumption_mode_driver_dominance_matrix": (
            assumption_mode_driver_dominance_matrix
        ),
        "assumption_mode_pairwise_sensitivity_matrix": (
            assumption_mode_pairwise_sensitivity_matrix
        ),
        "backend_invariant_guardrail_audit": backend_invariant_guardrail_audit,
        "backend_completion_verdict": backend_completion_verdict,
        "paper_channel_map": paper_channel_map,
        "paper_canonical_scenario_results": paper_canonical_scenario_results,
        "paper_tdc_dynamic_contribution": paper_tdc_dynamic_contribution,
        "paper_parameter_justification": paper_parameter_justification,
        "paper_sensitivity_summary": paper_sensitivity_summary,
        "paper_disabled_claims_appendix": paper_disabled_claims_appendix,
        "paper_financialization_interpretation": (
            paper_financialization_interpretation
        ),
        "paper_support_invariant_audit": paper_support_invariant_audit,
        "backend_accounting_identity_audit": backend_accounting_identity_audit,
        "paper_scenario_accounting_bridge": paper_scenario_accounting_bridge,
        "paper_dynamic_scenario_summary": paper_dynamic_scenario_summary,
        "conventional_drag_decomposition": conventional_drag_decomposition,
        "split_denominator_comparison": split_denominator_comparison,
        "denominator_sensitivity": denominator_sensitivity,
        "split_denominator_uncertainty": split_denominator_uncertainty,
        "split_denominator_regime_stability": split_denominator_regime_stability,
        "denominator_literature_matrix": denominator_literature_matrix,
        "split_denominator_joint_uncertainty": split_denominator_joint_uncertainty,
        "split_denominator_joint_regime_stability": (
            split_denominator_joint_regime_stability
        ),
        "denominator_classifier_comparison": denominator_classifier_comparison,
        "backend_model_readiness_gate": backend_model_readiness_gate,
        "chapter_readiness_self_audit": chapter_readiness_self_audit,
        "financialized_balance_sheet_channel": financialized_balance_sheet_channel,
        "financialization_proxy_registry": financialization_proxy_registry,
        "financialization_proxy_source_gate": financialization_proxy_source_gate,
        "financialization_source_gate": financialization_source_gate,
        "financialization_restricted_protocols": financialization_restricted_protocols,
        "financialization_double_count_audit": financialization_double_count_audit,
        "financialization_overlap_audit": financialization_overlap_audit,
        "financialization_artifact_traceability_matrix": (
            financialization_artifact_traceability_matrix
        ),
        "equity_transmission_channel_map": equity_transmission_channel_map,
        "equity_exposure_matrix": equity_exposure_matrix,
        "equity_sensitivity_diagnostic": equity_sensitivity_diagnostic,
        "equity_claim_status": equity_claim_status,
        "equity_evidence_workplan": equity_evidence_workplan,
        "parameter_packs": parameter_packs,
        "frontier_summary": frontier_summary,
        "regime_map": regime_map,
        "assumption_mode_interpretation": assumption_mode_interpretation,
        "prior_stack_diagnostic": prior_stack_diagnostic,
        "scenario_ladder": scenario_ladder,
        "model_adequacy_matrix": model_adequacy_matrix,
        "assumption_mode_audit": assumption_mode_audit,
        "financialization_pressure": financialization_pressure,
        "financialization_evidence_appendix": financialization_evidence_appendix,
        "safe_asset_retention_context": safe_asset_retention_context,
        "safe_asset_retention_evidence": safe_asset_retention_evidence,
        "contractionary_benchmark_calibration": contractionary_benchmark_calibration,
        "threshold_uncertainty_bands": threshold_uncertainty_bands,
        "historical_threshold_validation": historical_threshold_validation,
        "policy_boundary_synthesis": policy_boundary_synthesis,
        "blocker_resolution_ledger": blocker_resolution_ledger,
        "publication_claim_decision": publication_claim_decision,
        "final_blocker_ledger": final_blocker_ledger,
        "release_16_source_resolution": release_16_source_resolution,
        "release_16_no_further_promotion": release_16_no_further_promotion,
        "release_17_external_review": release_17_external_review,
        "release_17_publication_polish": release_17_publication_polish,
        "release_17_blocker_reopen": release_17_blocker_reopen,
        "release_18_live_refresh": release_18_live_refresh,
        "buyer_case_sign_matrix": buyer_case_sign_matrix,
        "recipient_mpc_scenarios": recipient_mpc_scenarios,
        "release_19_invariants": release_19_invariants,
        "release_19_methodology": release_19_methodology,
        "release_20_activity_benchmark": release_20_activity_benchmark,
        "release_20_lp_diagnostics": release_20_lp_diagnostics,
        "release_20_decision": release_20_decision,
        "release_21_live_refresh": release_21_live_refresh,
        "release_21_benchmark_gate": release_21_benchmark_gate,
        "release_21_backend_invariants": release_21_backend_invariants,
        "release_22_source_repro_audit": release_22_source_repro_audit,
        "release_22_source_gate": release_22_source_gate,
        "release_22_hash_manifest": release_22_hash_manifest,
        "release_22_hash_manifest_path": release_22_hash_manifest_path,
        "release_23_source_status": release_23_source_status,
        "release_23_latest_as_of": release_23_latest_as_of,
        "release_23_threshold_mechanics": release_23_threshold_mechanics,
        "release_23_calibration_plausibility": release_23_calibration_plausibility,
        "release_23_recipient_base": release_23_recipient_base,
        "threshold_claim_audit": threshold_claim_audit,
        "tdc_source_coverage": tdc_source_coverage,
        "tdc_claim_audit": tdc_claim_audit,
        "tables_dir": tables_dir,
        "reports_dir": tables_dir.parent / "reports",
        "figures_dir": tables_dir.parent / "figures",
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _claim_audit_rows(context: dict[str, object]) -> list[dict[str, str]]:
    empirical = _rows(context, "empirical_results")
    pricing = _rows(context, "pricing_audit")
    valuation_gate = _rows(context, "valuation_gate")
    dashboard = _rows(context, "dashboard")
    causal_audit = _rows(context, "causal_audit")
    submission_decision = _rows(context, "submission_decision")
    dynamic_lp = _rows(context, "dynamic_lp_feasibility")
    proxy_svar = _rows(context, "proxy_svar_feasibility")
    dynamic_blocker = _rows(context, "dynamic_causal_blocker")
    hac_rows = _rows(context, "event_study_hac")
    placebo_rows = _rows(context, "pretrend_placebo")
    promotion_contract = _rows(context, "promotion_contract")
    release_4_blocker = _rows(context, "release_4_blocker")
    controlled_lp_results = _rows(context, "controlled_dynamic_lp_results")
    controlled_lp_support = _rows(context, "controlled_dynamic_lp_support")
    release_5_decision = _rows(context, "release_5_decision")
    release_5_proxy_blocker = _rows(context, "release_5_proxy_blocker")
    proxy_svar_system_panel = _rows(context, "proxy_svar_system_panel")
    release_6_decision = _rows(context, "release_6_decision")
    release_6_proxy_blocker = _rows(context, "release_6_proxy_blocker")
    release_7_reduced_form_estimates = _rows(
        context, "release_7_reduced_form_estimates"
    )
    release_7_proxy_support = _rows(context, "release_7_proxy_support")
    release_7_decision = _rows(context, "release_7_decision")
    release_7_proxy_blocker = _rows(context, "release_7_proxy_blocker")
    release_8_proxy_specification = _rows(context, "release_8_proxy_specification")
    release_8_structural_gap = _rows(context, "release_8_structural_gap")
    release_8_nonpromotion_proof = _rows(context, "release_8_nonpromotion_proof")
    release_8_decision = _rows(context, "release_8_decision")
    release_9_proxy_registry = _rows(context, "release_9_proxy_registry")
    release_9_proxy_support = _rows(context, "release_9_proxy_support")
    release_9_decision = _rows(context, "release_9_decision")
    release_9_nonpromotion_proof = _rows(context, "release_9_nonpromotion_proof")
    tdc_ledger = _rows(context, "tdc_ledger")
    tdc_impulse = _rows(context, "tdc_impulse")
    tdc_historical_panel = _rows(context, "tdc_historical_panel")
    deposit_pricing_pass_through = _rows(context, "deposit_pricing_pass_through")
    tdc_historical_reconciliation = _rows(context, "tdc_historical_reconciliation")
    tdc_source_coverage = _rows(context, "tdc_source_coverage")
    tdc_claim_audit = _rows(context, "tdc_claim_audit")
    threshold_simulation = _rows(context, "threshold_simulation")
    threshold_calibration_ranges = _rows(context, "threshold_calibration_ranges")
    threshold_calibrated_simulation = _rows(context, "threshold_calibrated_simulation")
    du_ru_tga_calibration_bridge = _rows(context, "du_ru_tga_calibration_bridge")
    financialization_pressure = _rows(context, "financialization_pressure")
    financialization_evidence_appendix = _rows(
        context, "financialization_evidence_appendix"
    )
    contractionary_benchmark_calibration = _rows(
        context, "contractionary_benchmark_calibration"
    )
    threshold_uncertainty_bands = _rows(context, "threshold_uncertainty_bands")
    historical_threshold_validation = _rows(context, "historical_threshold_validation")
    policy_boundary_synthesis = _rows(context, "policy_boundary_synthesis")
    blocker_resolution_ledger = _rows(context, "blocker_resolution_ledger")
    publication_claim_decision = _rows(context, "publication_claim_decision")
    final_blocker_ledger = _rows(context, "final_blocker_ledger")
    release_16_source_resolution = _rows(context, "release_16_source_resolution")
    release_16_no_further_promotion = _rows(context, "release_16_no_further_promotion")
    release_17_external_review = _rows(context, "release_17_external_review")
    release_17_publication_polish = _rows(context, "release_17_publication_polish")
    release_17_blocker_reopen = _rows(context, "release_17_blocker_reopen")
    release_18_live_refresh = _rows(context, "release_18_live_refresh")
    release_18_live_refresh = _rows(context, "release_18_live_refresh")
    threshold_claim_audit = _rows(context, "threshold_claim_audit")
    release_9_proxy_registry = _rows(context, "release_9_proxy_registry")
    release_9_proxy_support = _rows(context, "release_9_proxy_support")
    release_9_decision = _rows(context, "release_9_decision")
    release_9_nonpromotion_proof = _rows(context, "release_9_nonpromotion_proof")
    release_9_proxy_registry = _rows(context, "release_9_proxy_registry")
    release_9_proxy_support = _rows(context, "release_9_proxy_support")
    release_9_decision = _rows(context, "release_9_decision")
    release_9_nonpromotion_proof = _rows(context, "release_9_nonpromotion_proof")
    release_7_lag_selection = _rows(context, "release_7_lag_selection")
    release_7_reduced_form_estimates = _rows(
        context, "release_7_reduced_form_estimates"
    )
    release_7_residual_covariance = _rows(context, "release_7_residual_covariance")
    release_7_proxy_support = _rows(context, "release_7_proxy_support")
    release_7_timing_audit = _rows(context, "release_7_timing_audit")
    release_7_decision = _rows(context, "release_7_decision")
    release_7_proxy_blocker = _rows(context, "release_7_proxy_blocker")
    release_8_proxy_specification = _rows(context, "release_8_proxy_specification")
    release_8_structural_gap = _rows(context, "release_8_structural_gap")
    release_8_nonpromotion_proof = _rows(context, "release_8_nonpromotion_proof")
    release_8_decision = _rows(context, "release_8_decision")
    safe_asset_retention_context = _rows(context, "safe_asset_retention_context")
    safe_asset_retention_evidence = _rows(context, "safe_asset_retention_evidence")
    buyer_case_sign_matrix = _rows(context, "buyer_case_sign_matrix")
    recipient_mpc_scenarios = _rows(context, "recipient_mpc_scenarios")
    release_19_invariants = _rows(context, "release_19_invariants")
    release_19_methodology = _rows(context, "release_19_methodology")
    release_20_activity_benchmark = _rows(context, "release_20_activity_benchmark")
    release_20_lp_diagnostics = _rows(context, "release_20_lp_diagnostics")
    release_20_decision = _rows(context, "release_20_decision")
    release_21_live_refresh = _rows(context, "release_21_live_refresh")
    release_21_benchmark_gate = _rows(context, "release_21_benchmark_gate")
    release_21_backend_invariants = _rows(context, "release_21_backend_invariants")
    release_22_source_repro_audit = _rows(context, "release_22_source_repro_audit")
    release_22_source_gate = _rows(context, "release_22_source_gate")
    proxy_svar_system_panel = _rows(context, "proxy_svar_system_panel")
    proxy_svar_relevance = _rows(context, "proxy_svar_relevance")
    proxy_svar_residual = _rows(context, "proxy_svar_residual")
    proxy_svar_timing = _rows(context, "proxy_svar_timing")
    release_6_decision = _rows(context, "release_6_decision")
    release_6_proxy_blocker = _rows(context, "release_6_proxy_blocker")
    release_7_lag_selection = _rows(context, "release_7_lag_selection")
    release_7_reduced_form_estimates = _rows(
        context, "release_7_reduced_form_estimates"
    )
    release_7_residual_covariance = _rows(context, "release_7_residual_covariance")
    release_7_proxy_support = _rows(context, "release_7_proxy_support")
    release_7_timing_audit = _rows(context, "release_7_timing_audit")
    release_7_decision = _rows(context, "release_7_decision")
    release_7_proxy_blocker = _rows(context, "release_7_proxy_blocker")
    proxy_svar_system_panel = _rows(context, "proxy_svar_system_panel")
    proxy_svar_relevance = _rows(context, "proxy_svar_relevance")
    proxy_svar_residual = _rows(context, "proxy_svar_residual")
    proxy_svar_timing = _rows(context, "proxy_svar_timing")
    release_6_decision = _rows(context, "release_6_decision")
    release_6_proxy_blocker = _rows(context, "release_6_proxy_blocker")
    release_6_valuation_frontier = _rows(context, "release_6_valuation_frontier")
    release_7_lag_selection = _rows(context, "release_7_lag_selection")
    release_7_reduced_form_estimates = _rows(
        context, "release_7_reduced_form_estimates"
    )
    release_7_residual_covariance = _rows(context, "release_7_residual_covariance")
    release_7_proxy_support = _rows(context, "release_7_proxy_support")
    release_7_timing_audit = _rows(context, "release_7_timing_audit")
    release_7_promotion_contract = _rows(context, "release_7_promotion_contract")
    release_7_decision = _rows(context, "release_7_decision")
    release_7_proxy_blocker = _rows(context, "release_7_proxy_blocker")
    release_8_proxy_specification = _rows(context, "release_8_proxy_specification")
    release_8_structural_gap = _rows(context, "release_8_structural_gap")
    release_8_nonpromotion_proof = _rows(context, "release_8_nonpromotion_proof")
    release_8_decision = _rows(context, "release_8_decision")
    release_8_proxy_specification = _rows(context, "release_8_proxy_specification")
    release_8_structural_gap = _rows(context, "release_8_structural_gap")
    release_8_nonpromotion_proof = _rows(context, "release_8_nonpromotion_proof")
    release_8_decision = _rows(context, "release_8_decision")
    sources = list(context["sources"])
    required_provenance = all(
        row.get("source_id")
        and row.get("series_id")
        and row.get("source_url")
        and row.get("units")
        and row.get("frequency")
        and row.get("transform")
        and row.get("retrieved_at")
        for row in sources
    )
    raw_rate_rejected = empirical and all(
        row.get("raw_rate_change_identification_rejected") == "true"
        for row in empirical
    )
    causal_claim_disabled = causal_audit and all(
        row.get("causal_claim_enabled") == "false" for row in causal_audit
    )
    release_2_0_gate_ok = submission_decision and all(
        row.get("raw_rate_change_identification_rejected") == "true"
        and row.get("full_lp_proxy_svar_claim_enabled") == "false"
        and row.get("pricing_output_enabled") == "false"
        and row.get("incidence_claim_enabled") == "false"
        for row in submission_decision
    )
    release_3_0_gate_ok = (
        bool(dynamic_lp)
        and bool(proxy_svar)
        and bool(dynamic_blocker)
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("dynamic_lp_claim_enabled") == "false"
            and row.get("full_lp_proxy_svar_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in dynamic_lp
        )
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("full_lp_proxy_svar_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in proxy_svar
        )
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("dynamic_lp_claim_enabled") == "false"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("full_lp_proxy_svar_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in dynamic_blocker
        )
    )
    release_4_0_gate_ok = (
        bool(hac_rows)
        and bool(placebo_rows)
        and bool(promotion_contract)
        and bool(release_4_blocker)
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("dynamic_lp_claim_enabled") == "false"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in hac_rows + placebo_rows + promotion_contract + release_4_blocker
        )
        and all(
            row.get("full_lp_proxy_svar_claim_enabled") == "false"
            for row in promotion_contract + release_4_blocker
        )
    )
    release_5_0_gate_ok = (
        bool(controlled_lp_results)
        and bool(controlled_lp_support)
        and bool(release_5_decision)
        and bool(release_5_proxy_blocker)
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in controlled_lp_results
            + controlled_lp_support
            + release_5_decision
            + release_5_proxy_blocker
        )
        and all(
            row.get("full_lp_proxy_svar_claim_enabled") == "false"
            for row in release_5_decision + release_5_proxy_blocker
        )
    )
    release_6_0_gate_ok = (
        bool(proxy_svar_system_panel)
        and bool(proxy_svar_relevance)
        and bool(proxy_svar_residual)
        and bool(proxy_svar_timing)
        and bool(release_6_decision)
        and bool(release_6_proxy_blocker)
        and bool(release_6_valuation_frontier)
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in proxy_svar_system_panel
            + proxy_svar_relevance
            + proxy_svar_residual
            + proxy_svar_timing
        )
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("system_identification_claim_enabled") == "false"
            and row.get("valuation_incidence_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("reset_calendar_construction_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in release_6_decision + release_6_proxy_blocker
        )
        and all(
            row.get("pricing_output_enabled") == "false"
            and row.get("holder_bridge_enabled") == "false"
            and row.get("tax_assumptions_enabled") == "false"
            and row.get("mpc_assumptions_enabled") == "false"
            and row.get("welfare_incidence_enabled") == "false"
            and row.get("reset_calendar_construction_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in release_6_valuation_frontier
        )
    )
    release_7_0_gate_ok = (
        bool(release_7_lag_selection)
        and bool(release_7_reduced_form_estimates)
        and bool(release_7_residual_covariance)
        and bool(release_7_proxy_support)
        and bool(release_7_timing_audit)
        and bool(release_7_promotion_contract)
        and bool(release_7_decision)
        and bool(release_7_proxy_blocker)
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("system_identification_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in release_7_lag_selection
            + release_7_reduced_form_estimates
            + release_7_residual_covariance
            + release_7_proxy_support
        )
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("system_identification_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("reset_calendar_construction_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in release_7_timing_audit
            + release_7_promotion_contract
            + release_7_decision
            + release_7_proxy_blocker
        )
        and all(
            row.get("dynamic_identification_promotion_enabled") == "false"
            for row in release_7_promotion_contract
        )
        and all(
            row.get("valuation_incidence_claim_enabled") == "false"
            for row in release_7_decision + release_7_proxy_blocker
        )
    )
    release_8_0_gate_ok = (
        bool(release_8_proxy_specification)
        and bool(release_8_structural_gap)
        and bool(release_8_nonpromotion_proof)
        and bool(release_8_decision)
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("system_identification_claim_enabled") == "false"
            and row.get("dynamic_identification_promotion_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("reset_calendar_construction_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in release_8_proxy_specification
            + release_8_structural_gap
            + release_8_nonpromotion_proof
        )
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("system_identification_claim_enabled") == "false"
            and row.get("valuation_incidence_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("reset_calendar_construction_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in release_8_decision
        )
        and all(
            row.get("dynamic_identification_promotion_enabled") == "false"
            for row in release_8_proxy_specification
            + release_8_structural_gap
            + release_8_nonpromotion_proof
        )
    )
    release_9_0_gate_ok = (
        bool(release_9_proxy_registry)
        and bool(release_9_proxy_support)
        and bool(release_9_decision)
        and bool(release_9_nonpromotion_proof)
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("system_identification_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("reset_calendar_construction_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in release_9_proxy_support
            + release_9_decision
            + release_9_nonpromotion_proof
        )
        and all(
            row.get("structural_claim_enabled") == "false"
            and row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("pricing_output_enabled") == "false"
            and row.get("reset_calendar_construction_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in release_9_proxy_registry
        )
        and all(
            row.get("dynamic_identification_promotion_enabled") == "false"
            for row in release_9_proxy_support + release_9_nonpromotion_proof
        )
    )
    tdc_gate_ok = (
        bool(tdc_ledger)
        and bool(tdc_impulse)
        and bool(tdc_source_coverage)
        and bool(tdc_claim_audit)
        and all(
            row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in tdc_ledger + tdc_impulse
        )
        and any(
            Decimal(str(row.get("tdc_deposit_channel_impulse_bil", "0"))) > 0
            for row in tdc_impulse
        )
        and any(
            Decimal(str(row.get("tdc_deposit_channel_impulse_bil", "0"))) < 0
            for row in tdc_impulse
        )
        and all(row.get("audit_status") == "pass" for row in tdc_claim_audit)
    )
    tdc_historical_gate_ok = (
        bool(tdc_historical_panel)
        and bool(deposit_pricing_pass_through)
        and bool(tdc_historical_reconciliation)
        and all(
            row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            and row.get("welfare_claim_enabled") == "false"
            for row in tdc_historical_panel + deposit_pricing_pass_through
        )
        and any(row.get("source_coverage_status") for row in tdc_historical_panel)
        and any(
            row.get("source_coverage_status") == "source_backed_context"
            for row in deposit_pricing_pass_through
        )
        and any(
            row.get("coverage_status") in {"missing", "inferred_or_partial"}
            for row in tdc_historical_reconciliation
        )
    )
    threshold_gate_ok = (
        bool(threshold_simulation)
        and bool(financialization_pressure)
        and bool(threshold_claim_audit)
        and all(
            row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            and row.get("welfare_claim_enabled") == "false"
            and row.get("financialization_causal_claim_enabled") == "false"
            for row in threshold_simulation + financialization_pressure
        )
        and all(
            row.get("threshold_hit_under_assumptions") in {"true", "false"}
            for row in threshold_simulation
        )
        and all(row.get("audit_status") == "pass" for row in threshold_claim_audit)
    )
    release_13_gate_ok = (
        bool(threshold_calibration_ranges)
        and bool(threshold_calibrated_simulation)
        and bool(du_ru_tga_calibration_bridge)
        and bool(financialization_evidence_appendix)
        and any(
            row.get("source_status") == "sibling_derived_source_backed"
            for row in threshold_calibration_ranges
        )
        and all(
            row.get("threshold_hit_under_assumptions") in {"true", "false"}
            for row in threshold_calibrated_simulation
        )
        and all(
            row.get("financialization_causal_claim_enabled") == "false"
            for row in financialization_evidence_appendix
        )
        and all(
            row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            and row.get("welfare_claim_enabled") == "false"
            for row in threshold_calibrated_simulation
        )
    )
    release_14_gate_ok = (
        bool(contractionary_benchmark_calibration)
        and bool(threshold_uncertainty_bands)
        and bool(historical_threshold_validation)
        and bool(policy_boundary_synthesis)
        and any(
            row.get("calibration_status") == "source_backed_range"
            for row in contractionary_benchmark_calibration
        )
        and any(
            row.get("calibration_status") == "blocked_missing_exact_source_field"
            for row in contractionary_benchmark_calibration
        )
        and all(
            row.get("policy_failure_claim_enabled") == "false"
            for row in threshold_uncertainty_bands
        )
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("causal_claim_enabled") == "false"
            and row.get("policy_failure_claim_enabled") == "false"
            for row in historical_threshold_validation
        )
        and all(
            row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            and row.get("welfare_claim_enabled") == "false"
            and row.get("financialization_causal_claim_enabled") == "false"
            and row.get("policy_failure_claim_enabled") == "false"
            for row in policy_boundary_synthesis
        )
    )
    release_15_gate_ok = (
        bool(blocker_resolution_ledger)
        and bool(publication_claim_decision)
        and bool(final_blocker_ledger)
        and any(
            row.get("release_15_resolution_status", "").startswith("blocked")
            for row in blocker_resolution_ledger
        )
        and any(
            row.get("release_15_resolution_status") == "resolved_for_bounded_context"
            for row in blocker_resolution_ledger
        )
        and all(
            row.get("promotion_enabled") == "false"
            and row.get("claim_boundary") == "blocker_resolution_not_claim_promotion"
            for row in blocker_resolution_ledger
        )
        and any(
            row.get("publication_claim_enabled") == "true"
            for row in publication_claim_decision
        )
        and any(
            row.get("publication_decision") == "block_promotion"
            for row in publication_claim_decision
        )
        and all(
            row.get("promotion_claim_enabled") == "false"
            for row in publication_claim_decision
        )
        and all(
            row.get("promotion_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            and row.get("welfare_claim_enabled") == "false"
            and row.get("policy_failure_claim_enabled") == "false"
            for row in final_blocker_ledger
        )
    )
    release_16_gate_ok = (
        bool(release_16_source_resolution)
        and bool(release_16_no_further_promotion)
        and all(
            row.get("release_16_resolution_status") == "final_no_further_promotion"
            and row.get("promotion_enabled") == "false"
            and row.get("policy_failure_claim_enabled") == "false"
            and row.get("financialization_causal_claim_enabled") == "false"
            for row in release_16_source_resolution
        )
        and all(
            row.get("final_no_further_promotion") == "true"
            and row.get("promotion_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            and row.get("welfare_claim_enabled") == "false"
            and row.get("policy_failure_claim_enabled") == "false"
            and row.get("financialization_causal_claim_enabled") == "false"
            for row in release_16_no_further_promotion
        )
        and {
            "source_backed_context",
            "sibling_derived",
            "missing",
            "blocked",
        }
        <= {row.get("source_label") for row in release_16_source_resolution}
    )
    release_17_gate_ok = (
        bool(release_17_external_review)
        and bool(release_17_publication_polish)
        and bool(release_17_blocker_reopen)
        and all(
            row.get("review_status") == "pass"
            and row.get("promotion_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            and row.get("welfare_claim_enabled") == "false"
            and row.get("policy_failure_claim_enabled") == "false"
            and row.get("financialization_causal_claim_enabled") == "false"
            for row in release_17_external_review
        )
        and all(
            row.get("qa_status") == "pass"
            and row.get("generated_from_outputs") == "true"
            and row.get("manual_macro_values_allowed") == "false"
            and row.get("promotion_enabled") == "false"
            for row in release_17_publication_polish
        )
        and all(
            row.get("new_evidence_found") == "false"
            and row.get("blocker_reopened") == "false"
            and row.get("promotion_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            and row.get("welfare_claim_enabled") == "false"
            and row.get("policy_failure_claim_enabled") == "false"
            and row.get("financialization_causal_claim_enabled") == "false"
            for row in release_17_blocker_reopen
        )
    )
    release_18_gate_ok = bool(release_18_live_refresh) and all(
        row.get("refresh_status") == "pass"
        and row.get("stored_secrets_allowed") == "false"
        and row.get("pricing_output_enabled") == "false"
        and row.get("incidence_claim_enabled") == "false"
        and row.get("welfare_claim_enabled") == "false"
        and row.get("policy_failure_claim_enabled") == "false"
        and row.get("financialization_causal_claim_enabled") == "false"
        for row in release_18_live_refresh
    )
    release_19_gate_ok = (
        bool(safe_asset_retention_context)
        and bool(safe_asset_retention_evidence)
        and bool(buyer_case_sign_matrix)
        and bool(recipient_mpc_scenarios)
        and bool(release_19_invariants)
        and bool(release_19_methodology)
        and all(row.get("audit_status") == "pass" for row in release_19_invariants)
        and all(
            row.get("action_status") in {"accepted", "deferred", "blocked"}
            for row in release_19_methodology
        )
        and any(
            row.get("action_status") == "accepted" for row in release_19_methodology
        )
        and all(
            row.get("financialization_causal_claim_enabled") == "false"
            for row in safe_asset_retention_context + safe_asset_retention_evidence
        )
        and all(
            row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            and row.get("welfare_claim_enabled") == "false"
            for row in buyer_case_sign_matrix
            + recipient_mpc_scenarios
            + release_19_invariants
            + release_19_methodology
        )
    )
    release_20_gate_ok = (
        bool(release_20_activity_benchmark)
        and bool(release_20_lp_diagnostics)
        and bool(release_20_decision)
        and any(
            row.get("benchmark_object") == "coherent_gdp_share_contractionary_drag"
            and row.get("benchmark_status", "").startswith("blocked")
            for row in release_20_activity_benchmark
        )
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("policy_failure_claim_enabled") == "false"
            for row in release_20_activity_benchmark
        )
        and all(
            row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("dynamic_lp_claim_enabled") == "false"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("pricing_output_enabled") == "false"
            and row.get("incidence_claim_enabled") == "false"
            for row in release_20_lp_diagnostics
        )
        and all(
            row.get("threshold_recalibration_enabled") == "false"
            and row.get("dynamic_lp_claim_enabled") == "false"
            and row.get("proxy_svar_claim_enabled") == "false"
            and row.get("policy_failure_claim_enabled") == "false"
            and row.get("raw_rate_change_identification_rejected") == "true"
            for row in release_20_decision
        )
    )
    release_21_gate_ok = (
        bool(release_21_live_refresh)
        and bool(release_21_benchmark_gate)
        and bool(release_21_backend_invariants)
        and all(row.get("audit_status") == "pass" for row in release_21_live_refresh)
        and all(
            row.get("policy_failure_claim_enabled") == "false"
            and row.get("raw_rate_change_identification_rejected") == "true"
            and row.get("threshold_recalibration_enabled") == "false"
            for row in release_21_benchmark_gate
        )
        and any(
            row.get("gate_component") == "coherent_gdp_share_denominator"
            and row.get("gate_status", "").startswith("blocked")
            for row in release_21_benchmark_gate
        )
        and all(
            row.get("audit_status") == "pass" for row in release_21_backend_invariants
        )
    )
    release_22_gate_ok = (
        bool(release_22_source_repro_audit)
        and bool(release_22_source_gate)
        and all(
            row.get("audit_status") == "pass" for row in release_22_source_repro_audit
        )
        and all(
            row.get("claim_boundary") == "release_22_source_gate_not_claim_promotion"
            for row in release_22_source_gate
        )
    )
    release_23_semantic_rows = (
        _rows(context, "release_23_source_status")
        + _rows(context, "release_23_latest_as_of")
        + _rows(context, "release_23_threshold_mechanics")
        + _rows(context, "release_23_calibration_plausibility")
        + _rows(context, "release_23_recipient_base")
    )
    release_23_gate_ok = bool(release_23_semantic_rows) and all(
        row.get("audit_status") == "pass" for row in release_23_semantic_rows
    )
    pricing_disabled = _all_false(
        pricing + valuation_gate + dashboard,
        (
            "pricing_output_enabled",
            "valuation_pricing_output_enabled",
            "holder_allocation_enabled",
            "welfare_incidence_enabled",
            "incidence_claim_enabled",
            "reset_calendar_construction_enabled",
        ),
    )
    return [
        _audit_row(
            "higher_rates_always_raise_inflation",
            True,
            "ratewall_final_paper.md",
            "Final narrative uses conditional state-dependent language only.",
            "Keep bounded wording in paper and deck.",
        ),
        _audit_row(
            "fed_stopped_working",
            True,
            "ratewall_final_paper.md",
            "Final narrative rejects claims that the Fed has stopped working.",
            "Describe diminishing returns as a hypothesis, not a slogan.",
        ),
        _audit_row(
            "raw_policy_rate_change_shocks",
            bool(raw_rate_rejected),
            "ratewall_empirical_results.csv",
            "Empirical rows use SF Fed orthogonalized surprises, not raw rates.",
            "Block any raw-rate shock estimate from release artifacts.",
        ),
        _audit_row(
            "source_backed_no_hardcoded_current_macro",
            required_provenance,
            "source_provenance.json",
            "Required provenance fields are present for all source rows.",
            "Regenerate source snapshots before updating final claims.",
        ),
        _audit_row(
            "pricing_allocation_incidence_disabled",
            pricing_disabled,
            "treasury_pricing_switch_audit_disabled.csv",
            "Pricing, allocation, reset-calendar, welfare, and incidence switches are false.",
            "Keep disabled unless future opt-in tests deliberately enable them.",
        ),
        _audit_row(
            "descriptive_scenario_empirical_separation",
            True,
            "ratewall_release_manifest.json",
            "Manifest separates accounting, scenario, empirical, readiness, and release layers.",
            "Do not merge event-study estimates with mechanical impulse rows.",
        ),
        _audit_row(
            "release_1_1_causal_claim_gate",
            bool(causal_claim_disabled),
            "ratewall_causal_identification_audit.csv",
            "Release 1.1 causal audit keeps full LP/proxy-SVAR claims disabled unless future requirements are audited.",
            "Publish bounded event-study evidence or a machine-readable defensibility blocker, not wider causal claims.",
        ),
        _audit_row(
            "release_2_0_submission_identification_gate",
            bool(release_2_0_gate_ok),
            "ratewall_submission_identification_decision.csv",
            "Release 2.0 allows a bounded event-study appendix while keeping full LP/proxy-SVAR, pricing, and incidence claims disabled.",
            "Use submission diagnostics as bounded evidence and keep stronger claims blocked.",
        ),
        _audit_row(
            "release_3_0_dynamic_causal_gate",
            bool(release_3_0_gate_ok),
            "ratewall_dynamic_causal_final_blocker.csv",
            "Release 3.0 documents the journal-grade dynamic LP/proxy-SVAR frontier while keeping stronger causal, pricing, and incidence claims disabled.",
            "Use the final blocker as a journal-submission boundary unless future dynamic identification gates are deliberately implemented and tested.",
        ),
        _audit_row(
            "release_4_0_final_submission_gate",
            bool(release_4_0_gate_ok),
            "ratewall_release_4_0_dynamic_causal_final_blocker.csv",
            "Release 4.0 adds HAC/placebo diagnostics and a disabled promotion contract while keeping stronger causal, pricing, and incidence claims disabled.",
            "Publish the bounded event-study package or the final blocker, not an unsupported dynamic LP/proxy-SVAR claim.",
        ),
        _audit_row(
            "release_5_0_controlled_dynamic_lp_gate",
            bool(release_5_0_gate_ok),
            "ratewall_release_5_0_identification_decision.csv",
            "Release 5.0 adds controlled dynamic-LP outputs or a fail-closed blocker while keeping proxy-SVAR, pricing, and incidence claims disabled.",
            "Use controlled LP rows only as bounded admissible-shock evidence and keep proxy-SVAR/pricing/incidence gates closed.",
        ),
        _audit_row(
            "release_6_0_proxy_svar_system_gate",
            bool(release_6_0_gate_ok),
            "ratewall_release_6_0_identification_decision.csv",
            "Release 6.0 adds source-backed system diagnostics while keeping proxy-SVAR, pricing, reset-calendar, and incidence claims disabled.",
            "Use the system panel as review evidence only; keep proxy-SVAR/system identification blocked unless future gates are deliberately implemented.",
        ),
        _audit_row(
            "release_7_0_system_identification_gate",
            bool(release_7_0_gate_ok),
            "ratewall_release_7_0_identification_decision.csv",
            "Release 7.0 adds estimated reduced-form system diagnostics while keeping proxy-SVAR, pricing, reset-calendar, and incidence claims disabled.",
            "Use the reduced-form system as diagnostic evidence only; keep structural system-identification blocked unless all future gates pass.",
        ),
        _audit_row(
            "release_8_0_system_identification_nonpromotion_gate",
            bool(release_8_0_gate_ok),
            "ratewall_release_8_0_nonpromotion_proof.csv",
            "Release 8.0 audits admissible proxy specifications and preserves a final non-promotion proof while keeping structural system, pricing, reset-calendar, and incidence claims disabled.",
            "Use the Release 8.0 proof as the strongest current boundary unless future proxy support and structural assumption gates deliberately pass.",
        ),
        _audit_row(
            "release_9_0_external_proxy_publication_boundary_gate",
            bool(release_9_0_gate_ok),
            "ratewall_release_9_0_final_nonpromotion_proof.csv",
            "Release 9.0 expands the admissible external-proxy source frontier while keeping structural system, pricing, reset-calendar, and incidence claims disabled.",
            "Use the Release 9.0 proof as the publication boundary unless future structural assumption and claim-promotion gates deliberately pass.",
        ),
        _audit_row(
            "release_10_0_tdc_deposit_channel_gate",
            bool(tdc_gate_ok),
            "ratewall_tdc_claim_boundary_audit.csv",
            "Release 10.0 adds a TDC DU/RU deposit-channel accounting layer while keeping deposit pricing, welfare, and incidence claims separate and disabled.",
            "Use TDC outputs as source-coverage and accounting-scenario evidence; do not claim a universal deposit or inflation sign.",
        ),
        _audit_row(
            "release_11_0_historical_tdc_and_deposit_pricing_gate",
            bool(tdc_historical_gate_ok),
            "ratewall_tdc_historical_reconciliation.csv",
            "Release 11.0 adds historical partial TDC proxy rows and a separate deposit-pricing/pass-through context surface while keeping pricing, welfare, and incidence claims disabled.",
            "Use historical rows as source-coverage diagnostics and keep exact DU/RU bridge, pricing, incidence, and welfare claims blocked until future gates pass.",
        ),
        _audit_row(
            "release_12_0_threshold_and_financialization_gate",
            bool(threshold_gate_ok),
            "ratewall_threshold_simulation.csv",
            "Release 12.0 adds conditional threshold diagnostics; Release 19.0 reframes the old financialization-pressure wording as safe-asset-retention context while keeping policy-failure, causal-financialization, pricing, welfare, and incidence claims disabled.",
            "Use threshold rows only as explicit scenario assumptions; do not claim a universal RateWall date or causal financialization result.",
        ),
        _audit_row(
            "release_13_0_calibrated_threshold_gate",
            bool(release_13_gate_ok),
            "ratewall_threshold_calibrated_simulation.csv",
            "Release 13.0 adds source-labeled or sibling-derived calibration-context ranges while keeping review-status ranges demoted and remaining behavioral assumptions explicit.",
            "Use calibrated rows as bounded sensitivity diagnostics; do not promote final DU/RU/TGA, policy-failure, or causal-financialization claims.",
        ),
        _audit_row(
            "release_14_0_historical_threshold_validation_gate",
            bool(release_14_gate_ok),
            "ratewall_historical_threshold_validation.csv",
            "Release 14.0 adds historical-threshold validation, contractionary-benchmark calibration, uncertainty bands, and policy-boundary synthesis while preserving non-promotion boundaries.",
            "Use Release 14.0 as final sensitivity and boundary evidence, not as a universal RateWall date or causal policy-failure claim.",
        ),
        _audit_row(
            "release_15_0_publication_claim_decision_gate",
            bool(release_15_gate_ok),
            "ratewall_publication_claim_decision.csv",
            "Release 15.0 resolves the publication decision: bounded claims are enabled with labels while final threshold, policy-failure, pricing, incidence, welfare, and causal-financialization claims remain blocked.",
            "Publish bounded claims with explicit blocker ledgers; do not widen claim language.",
        ),
        _audit_row(
            "release_16_0_bounded_publication_closeout_gate",
            bool(release_16_gate_ok),
            "ratewall_release_16_no_further_promotion_ledger.csv",
            "Release 16.0 closes the source-resolution frontier with final no-further-promotion rows while keeping bounded publication claims intact.",
            "Use Release 16.0 as the publication closeout unless new source, method, and fail-closed tests deliberately reopen a blocker.",
        ),
        _audit_row(
            "release_17_0_external_review_publication_polish_gate",
            bool(release_17_gate_ok),
            "ratewall_release_17_blocker_reopen_decision.csv",
            "Release 17.0 audits reviewer-facing consistency and publication polish while keeping Release 16 blockers closed absent new evidence.",
            "Use Release 17.0 as external-review polish; do not reopen promotion claims without new source/method evidence and fail-closed tests.",
        ),
        _audit_row(
            "release_18_0_live_refresh_publication_freeze_gate",
            bool(release_18_gate_ok),
            "ratewall_release_18_live_refresh_robustness_audit.csv",
            "Release 18.0 adds live-refresh timeout and provenance fallback guards while preserving the Release 17 publication boundary.",
            "Use Release 18.0 as the publication-freeze refresh; do not widen claims because a source refresh succeeded.",
        ),
        _audit_row(
            "release_19_0_post_audit_methodology_gate",
            bool(release_19_gate_ok),
            "ratewall_release_19_post_audit_methodology_audit.csv",
            "Release 19.0 hardens the post-audit accounting, buyer-case, MPC, safe-asset, and benchmark-boundary layers while preserving non-promotion gates.",
            "Use Release 19.0 as the methodologically hardened submission-readiness layer; do not promote blocked threshold, incidence, welfare, or causal-financialization claims.",
        ),
        _audit_row(
            "release_20_0_submission_benchmark_gate",
            bool(release_20_gate_ok),
            "ratewall_release_20_benchmark_submission_decision.csv",
            "Release 20.0 adds coherent activity/demand benchmark context and admissible-shock diagnostics while blocking GDP-drag threshold promotion.",
            "Use Release 20.0 as submission-readiness evidence; do not publish final threshold dates or policy-failure claims without a promoted contractionary benchmark.",
        ),
        _audit_row(
            "release_21_0_backend_closeout_gate",
            bool(release_21_gate_ok),
            "ratewall_release_21_backend_invariant_audit.csv",
            "Release 21.0 hardens live-refresh progress/fallback behavior and keeps the final contractionary benchmark gate fail-closed.",
            "Use Release 21.0 as backend closeout evidence; do not promote final thresholds or policy-failure claims without a future benchmark gate.",
        ),
        _audit_row(
            "release_22_0_source_repro_accounting_gate",
            bool(release_22_gate_ok),
            "ratewall_release_22_source_repro_accounting_audit.csv",
            "Release 22.0 gates fallback MSPD repricing, vendors sibling calibration extracts, and hardens accounting/reproducibility checks.",
            "Use Release 22.0 as backend correction evidence; do not treat fallback/security-review rows as live source-backed threshold support.",
        ),
        _audit_row(
            "release_23_0_backend_semantic_and_archive_gate",
            bool(release_23_gate_ok),
            "ratewall_release_23_source_status_propagation_audit.csv",
            "Release 23.0 adds semantic backend audits for source-status propagation, latest-as-of metadata, threshold mechanics, calibration plausibility, and recipient-base consistency.",
            "Use Release 23.0 as backend hardening evidence; do not widen claims unless future source/method gates deliberately pass.",
        ),
    ]


def _audit_row(
    boundary: str,
    passed: bool,
    artifact: str,
    finding: str,
    action: str,
) -> dict[str, str]:
    return {
        "boundary": boundary,
        "audit_status": "pass" if passed else "fail",
        "evidence_artifact": artifact,
        "finding": finding,
        "release_action": action,
    }


def _rows(context: dict[str, object], key: str) -> list[dict[str, str]]:
    value = context[key]
    if isinstance(value, list):
        return value
    return []


def _all_false(rows: Iterable[dict[str, str]], fields: Iterable[str]) -> bool:
    observed = False
    for row in rows:
        for field in fields:
            if field not in row or row[field] == "":
                continue
            observed = True
            if row[field].lower() != "false" and row[field] != "0":
                return False
    return observed


def _final_paper_text(
    context: dict[str, object], claim_rows: list[dict[str, str]]
) -> str:
    impulse = _row_by(context, "impulse", "horizon", "1y")
    event_count = _count_status(
        context, "admissible_event_study_estimate_with_limitations"
    )
    association_count = _count_status(
        context, "admissible_shock_state_association_not_causal_lp"
    )
    blocker_count = _count_status(
        context, "final_documented_blocker_for_full_causal_lp_proxy_svar"
    )
    causal_blocker_rows = len(_rows(context, "causal_blocker"))
    support_rows = len(_rows(context, "support_diagnostics"))
    robustness_rows = len(_rows(context, "event_study_robustness"))
    dynamic_lp_rows = len(_rows(context, "dynamic_lp_feasibility"))
    proxy_svar_rows = len(_rows(context, "proxy_svar_feasibility"))
    dynamic_blocker_rows = len(_rows(context, "dynamic_causal_blocker"))
    hac_rows = len(_rows(context, "event_study_hac"))
    placebo_rows = len(_rows(context, "pretrend_placebo"))
    promotion_rows = len(_rows(context, "promotion_contract"))
    release_4_blocker_rows = len(_rows(context, "release_4_blocker"))
    controlled_lp_rows = len(_rows(context, "controlled_dynamic_lp_results"))
    release_5_decision_rows = len(_rows(context, "release_5_decision"))
    release_5_proxy_blocker_rows = len(_rows(context, "release_5_proxy_blocker"))
    system_panel_rows = len(_rows(context, "proxy_svar_system_panel"))
    release_6_decision_rows = len(_rows(context, "release_6_decision"))
    release_6_proxy_blocker_rows = len(_rows(context, "release_6_proxy_blocker"))
    release_7_estimate_rows = len(_rows(context, "release_7_reduced_form_estimates"))
    release_7_decision_rows = len(_rows(context, "release_7_decision"))
    release_7_proxy_blocker_rows = len(_rows(context, "release_7_proxy_blocker"))
    release_8_proxy_spec_rows = len(_rows(context, "release_8_proxy_specification"))
    release_8_gap_rows = len(_rows(context, "release_8_structural_gap"))
    release_8_proof_rows = len(_rows(context, "release_8_nonpromotion_proof"))
    release_8_decision_rows = len(_rows(context, "release_8_decision"))
    release_9_registry_rows = len(_rows(context, "release_9_proxy_registry"))
    release_9_support_rows = len(_rows(context, "release_9_proxy_support"))
    release_9_decision_rows = len(_rows(context, "release_9_decision"))
    release_9_proof_rows = len(_rows(context, "release_9_nonpromotion_proof"))
    tdc_ledger_rows = len(_rows(context, "tdc_ledger"))
    tdc_impulse_rows = len(_rows(context, "tdc_impulse"))
    tdc_coverage_rows = len(_rows(context, "tdc_source_coverage"))
    tdc_historical_rows = len(_rows(context, "tdc_historical_panel"))
    deposit_pricing_rows = len(_rows(context, "deposit_pricing_pass_through"))
    tdc_reconciliation_rows = len(_rows(context, "tdc_historical_reconciliation"))
    threshold_rows = len(_rows(context, "threshold_simulation"))
    financialization_rows = len(_rows(context, "financialization_pressure"))
    calibration_rows = len(_rows(context, "threshold_calibration_ranges"))
    calibrated_threshold_rows = len(_rows(context, "threshold_calibrated_simulation"))
    bridge_rows = len(_rows(context, "du_ru_tga_calibration_bridge"))
    financialization_evidence_rows = len(
        _rows(context, "financialization_evidence_appendix")
    )
    benchmark_rows = len(_rows(context, "contractionary_benchmark_calibration"))
    uncertainty_rows = len(_rows(context, "threshold_uncertainty_bands"))
    validation_rows = len(_rows(context, "historical_threshold_validation"))
    boundary_rows = len(_rows(context, "policy_boundary_synthesis"))
    blocker_resolution_rows = len(_rows(context, "blocker_resolution_ledger"))
    publication_claim_rows = len(_rows(context, "publication_claim_decision"))
    final_blocker_rows = len(_rows(context, "final_blocker_ledger"))
    release_16_source_resolution_rows = len(
        _rows(context, "release_16_source_resolution")
    )
    release_16_no_further_promotion_rows = len(
        _rows(context, "release_16_no_further_promotion")
    )
    release_17_external_review_rows = len(_rows(context, "release_17_external_review"))
    release_17_publication_polish_rows = len(
        _rows(context, "release_17_publication_polish")
    )
    release_17_blocker_reopen_rows = len(_rows(context, "release_17_blocker_reopen"))
    release_18_live_refresh_rows = len(_rows(context, "release_18_live_refresh"))
    release_20_activity_rows = len(_rows(context, "release_20_activity_benchmark"))
    release_20_lp_rows = len(_rows(context, "release_20_lp_diagnostics"))
    release_20_decision_rows = len(_rows(context, "release_20_decision"))
    metric_count = len(_rows(context, "metrics"))
    scenario_count = len(_rows(context, "scenarios"))
    audit_pass = all(row["audit_status"] == "pass" for row in claim_rows)
    impulse_value = impulse.get("annualized_public_interest_impulse_bil", "")
    return "\n".join(
        [
            "# At the Rate Wall",
            "",
            "## Abstract",
            "",
            "RateWall is a source-labeled backend package for studying "
            "debt-conditioned monetary transmission, with fallback/review "
            "demotions preserved on MSPD-dependent rows. It separates mechanical "
            "public-liability accounting, bounded scenario diagnostics, "
            "admissible-shock empirical estimates, and valuation-readiness "
            "limitations. It does not claim that higher rates always raise "
            "inflation or that the Federal Reserve has stopped working.",
            "",
            "## Main Evidence",
            "",
            f"- Mechanical accounting: 100 bps impulse table includes the 1y "
            f"annualized public-interest impulse value `{impulse_value}`.",
            f"- Descriptive data book: {metric_count} generated metric rows.",
            f"- Scenario diagnostics: {scenario_count} generated scenario rows.",
            f"- Empirical estimates: {event_count} bounded event-study rows and "
            f"{association_count} shock/state association rows.",
            f"- Stronger empirical claims: {blocker_count} full LP/proxy-SVAR "
            "blocker row keeps stronger causal language disabled.",
            f"- Release 2.0 causal gate: {causal_blocker_rows} machine-readable "
            "defensibility blocker row documents the maximum empirical claim.",
            f"- Release 2.0 submission diagnostics: {support_rows} support rows "
            f"and {robustness_rows} robustness rows keep the event-study appendix bounded.",
            f"- Release 3.0 journal gate: {dynamic_lp_rows} dynamic-LP feasibility rows, "
            f"{proxy_svar_rows} proxy-SVAR feasibility rows, and {dynamic_blocker_rows} "
            "final blocker row keep stronger dynamic causal language disabled.",
            f"- Release 4.0 final-submission gate: {hac_rows} HAC-style rows, "
            f"{placebo_rows} placebo rows, {promotion_rows} disabled promotion-contract "
            f"rows, and {release_4_blocker_rows} strengthened final blocker row.",
            f"- Release 5.0 dynamic-causal frontier: {controlled_lp_rows} "
            f"controlled dynamic-LP result rows, {release_5_decision_rows} "
            f"identification-decision rows, and {release_5_proxy_blocker_rows} "
            "proxy-SVAR blocker rows.",
            f"- Release 6.0 system-identification frontier: {system_panel_rows} "
            f"system-panel rows, {release_6_decision_rows} decision rows, and "
            f"{release_6_proxy_blocker_rows} proxy-SVAR/system blocker rows.",
            f"- Release 7.0 system-identification frontier: {release_7_estimate_rows} "
            f"reduced-form estimate rows, {release_7_decision_rows} decision "
            f"rows, and {release_7_proxy_blocker_rows} final blocker rows.",
            f"- Release 8.0 non-promotion frontier: {release_8_proxy_spec_rows} "
            f"proxy-specification audit rows, {release_8_gap_rows} structural "
            f"gap rows, {release_8_decision_rows} decision rows, and "
            f"{release_8_proof_rows} final proof rows.",
            f"- Release 9.0 publication-boundary frontier: {release_9_registry_rows} "
            f"external-proxy registry rows, {release_9_support_rows} support "
            f"audit rows, {release_9_decision_rows} decision rows, and "
            f"{release_9_proof_rows} final proof rows.",
            f"- Release 10.0 TDC deposit-channel layer: {tdc_ledger_rows} "
            f"accounting ledger rows, {tdc_impulse_rows} DU/RU financing "
            f"scenario rows, and {tdc_coverage_rows} source-coverage rows.",
            f"- Release 11.0 historical TDC and deposit-pricing layer: "
            f"{tdc_historical_rows} historical panel rows, "
            f"{deposit_pricing_rows} deposit-pricing context rows, and "
            f"{tdc_reconciliation_rows} reconciliation rows.",
            f"- Release 12.0 threshold and safe-asset-retention layer: "
            f"{threshold_rows} conditional threshold rows and "
            f"{financialization_rows} legacy bounded retention-context rows.",
            f"- Release 13.0 calibration layer: {calibration_rows} calibration "
            f"range rows, {calibrated_threshold_rows} calibrated threshold rows, "
            f"{bridge_rows} DU/RU/TGA bridge rows, and "
            f"{financialization_evidence_rows} financialization-evidence rows.",
            f"- Release 14.0 validation layer: {benchmark_rows} benchmark "
            f"calibration rows, {uncertainty_rows} uncertainty-band rows, "
            f"{validation_rows} historical validation rows, and {boundary_rows} "
            "policy-boundary rows.",
            f"- Release 15.0 publication decision: {blocker_resolution_rows} "
            f"blocker-resolution rows, {publication_claim_rows} publication "
            f"claim-decision rows, and {final_blocker_rows} final blocker rows.",
            f"- Release 16.0 closeout: {release_16_source_resolution_rows} "
            f"source-resolution rows and {release_16_no_further_promotion_rows} "
            "no-further-promotion rows.",
            f"- Release 17.0 external review and polish: "
            f"{release_17_external_review_rows} review rows, "
            f"{release_17_publication_polish_rows} polish QA rows, and "
            f"{release_17_blocker_reopen_rows} blocker-reopen decision rows.",
            f"- Release 18.0 live-refresh publication freeze: "
            f"{release_18_live_refresh_rows} refresh robustness rows.",
            f"- Release 20.0 submission benchmark: {release_20_activity_rows} "
            f"activity/demand benchmark rows, {release_20_lp_rows} LP "
            f"diagnostic rows, and {release_20_decision_rows} submission "
            "decision rows keep GDP-drag threshold promotion blocked.",
            "- Release 21.0 backend closeout: live-refresh endpoint logging, "
            "final benchmark gating, and accounting invariants are generated "
            "without PDF/deck claim promotion.",
            f"- Claim-boundary audit: {'passed' if audit_pass else 'failed'}",
            "",
            "## Interpretation",
            "",
            "The core contribution is a reproducible accounting and evidence "
            "package for the public-liability channel. The evidence supports "
            "state-dependent diagnostics and bounded empirical discussion, not "
            "a universal claim about the sign of rate hikes.",
            "",
            "## Release Artifacts",
            "",
            "- Source/provenance appendix: `ratewall_source_provenance_appendix.md`",
            "- Empirical-method appendix: `ratewall_empirical_method_appendix.md`",
            "- Causal-identification appendix: `ratewall_causal_identification_appendix.md`",
            "- Submission causal appendix: `ratewall_submission_causal_appendix.md`",
            "- Journal-submission appendix: `ratewall_journal_submission_appendix.md`",
            "- Release 4.0 final-submission memo: `ratewall_release_4_0_final_submission_memo.md`",
            "- Release 4.0 referee packet: `ratewall_release_4_0_referee_packet.md`",
            "- Release 5.0 dynamic-LP appendix: `ratewall_release_5_0_dynamic_lp_appendix.md`",
            "- Release 5.0 referee response: `ratewall_release_5_0_referee_response.md`",
            "- Release 6.0 proxy-SVAR/system appendix: `ratewall_release_6_0_proxy_svar_system_appendix.md`",
            "- Release 6.0 reviewer response: `ratewall_release_6_0_reviewer_response.md`",
            "- Release 7.0 system-identification appendix: `ratewall_release_7_0_system_identification_appendix.md`",
            "- Release 7.0 external review packet: `ratewall_release_7_0_external_review_packet.md`",
            "- Release 8.0 non-promotion appendix: `ratewall_release_8_0_system_nonpromotion_appendix.md`",
            "- Release 8.0 reviewer response: `ratewall_release_8_0_reviewer_response.md`",
            "- Release 9.0 structural-boundary appendix: `ratewall_release_9_0_structural_boundary_appendix.md`",
            "- Release 9.0 external-proxy review packet: `ratewall_release_9_0_external_proxy_review_packet.md`",
            "- Release 10.0 TDC appendix: `ratewall_tdc_deposit_channel_appendix.md`",
            "- Release 12.0 threshold table: `ratewall_threshold_simulation.csv`",
            "- Release 12.0 legacy retention-context table: `ratewall_financialization_pressure.csv`",
            "- Release 13.0 calibration ranges: `ratewall_threshold_calibration_ranges.csv`",
            "- Release 13.0 calibrated threshold table: `ratewall_threshold_calibrated_simulation.csv`",
            "- Release 13.0 DU/RU/TGA bridge: `ratewall_du_ru_tga_calibration_bridge.csv`",
            "- Release 13.0 legacy retention evidence appendix: `ratewall_financialization_pressure_evidence_appendix.csv`",
            "- Release 14.0 benchmark calibration: `ratewall_contractionary_benchmark_calibration.csv`",
            "- Release 14.0 uncertainty bands: `ratewall_threshold_uncertainty_bands.csv`",
            "- Release 14.0 historical validation: `ratewall_historical_threshold_validation.csv`",
            "- Release 14.0 policy-boundary synthesis: `ratewall_policy_boundary_synthesis.csv`",
            "- Release 15.0 blocker-resolution ledger: `ratewall_blocker_resolution_ledger.csv`",
            "- Release 15.0 publication-claim decision: `ratewall_publication_claim_decision.csv`",
            "- Release 15.0 final blocker ledger: `ratewall_final_blocker_ledger.csv`",
            "- Release 15.0 publication-claim memo: `ratewall_publication_claim_decision_memo.md`",
            "- Release 16.0 source-resolution closeout: `ratewall_release_16_source_resolution_closeout.csv`",
            "- Release 16.0 no-further-promotion ledger: `ratewall_release_16_no_further_promotion_ledger.csv`",
            "- Release 16.0 bounded-publication closeout memo: `ratewall_release_16_bounded_publication_closeout_memo.md`",
            "- Release 16.0 reviewer blocker text: `ratewall_release_16_reviewer_blocker_text.md`",
            "- Release 17.0 external review audit: `ratewall_release_17_external_review_audit.csv`",
            "- Release 17.0 publication polish QA: `ratewall_release_17_publication_polish_qa.csv`",
            "- Release 17.0 blocker reopen decision: `ratewall_release_17_blocker_reopen_decision.csv`",
            "- Release 17.0 external review packet: `ratewall_release_17_external_review_packet.md`",
            "- Release 17.0 publication polish memo: `ratewall_release_17_publication_polish_memo.md`",
            "- Release 18.0 live-refresh robustness audit: `ratewall_release_18_live_refresh_robustness_audit.csv`",
            "- Release 18.0 publication freeze memo: `ratewall_release_18_publication_freeze_memo.md`",
            "- Release 20.0 activity/demand benchmark: `ratewall_release_20_activity_demand_benchmark.csv`",
            "- Release 20.0 state-dependent LP diagnostics: `ratewall_release_20_state_dependent_lp_diagnostics.csv`",
            "- Release 20.0 benchmark submission decision: `ratewall_release_20_benchmark_submission_decision.csv`",
            "- Release 20.0 submission-readiness memo: `ratewall_release_20_submission_readiness_memo.md`",
            "- Release 21.0 live-refresh endpoint audit: `ratewall_release_21_live_refresh_endpoint_audit.csv`",
            "- Release 21.0 final benchmark gate: `ratewall_release_21_final_benchmark_gate.csv`",
            "- Release 21.0 backend invariant audit: `ratewall_release_21_backend_invariant_audit.csv`",
            "- Release 21.0 backend closeout memo: `ratewall_release_21_backend_closeout_memo.md`",
            "- Dynamic-causal blocker memo: `ratewall_dynamic_causal_blocker_memo.md`",
            "- Referee response compendium: `ratewall_referee_response_compendium.md`",
            "- External review response packet: `ratewall_external_review_response_packet.md`",
            "- Reviewer limitations memo: `ratewall_reviewer_limitations_memo.md`",
            "- Limitations appendix: `ratewall_limitations_appendix.md`",
            "- Validation package: `ratewall_validation_package.md`",
            "",
        ]
    )


def _final_paper_quarto_text(
    context: dict[str, object], claim_rows: list[dict[str, str]]
) -> str:
    source_counts = Counter(row.get("snapshot_kind", "") for row in context["sources"])
    impulse_rows = _rows(context, "impulse")
    dashboard_rows = _rows(context, "dashboard")
    empirical_statuses = Counter(
        row.get("result_status", "") for row in _rows(context, "empirical_results")
    )
    causal_audit_rows = _rows(context, "causal_audit")
    causal_blocker_rows = _rows(context, "causal_blocker")
    support_rows = _rows(context, "support_diagnostics")
    robustness_rows = _rows(context, "event_study_robustness")
    submission_decision = _rows(context, "submission_decision")
    dynamic_lp = _rows(context, "dynamic_lp_feasibility")
    proxy_svar = _rows(context, "proxy_svar_feasibility")
    dynamic_blocker = _rows(context, "dynamic_causal_blocker")
    hac_rows = _rows(context, "event_study_hac")
    placebo_rows = _rows(context, "pretrend_placebo")
    promotion_contract = _rows(context, "promotion_contract")
    release_4_blocker = _rows(context, "release_4_blocker")
    controlled_lp_results = _rows(context, "controlled_dynamic_lp_results")
    release_5_decision = _rows(context, "release_5_decision")
    release_5_proxy_blocker = _rows(context, "release_5_proxy_blocker")
    proxy_svar_system_panel = _rows(context, "proxy_svar_system_panel")
    proxy_svar_relevance = _rows(context, "proxy_svar_relevance")
    proxy_svar_residual = _rows(context, "proxy_svar_residual")
    proxy_svar_timing = _rows(context, "proxy_svar_timing")
    release_6_decision = _rows(context, "release_6_decision")
    release_6_proxy_blocker = _rows(context, "release_6_proxy_blocker")
    release_7_lag_selection = _rows(context, "release_7_lag_selection")
    release_7_reduced_form_estimates = _rows(
        context, "release_7_reduced_form_estimates"
    )
    release_7_residual_covariance = _rows(context, "release_7_residual_covariance")
    release_7_proxy_support = _rows(context, "release_7_proxy_support")
    release_7_timing_audit = _rows(context, "release_7_timing_audit")
    release_7_decision = _rows(context, "release_7_decision")
    release_7_proxy_blocker = _rows(context, "release_7_proxy_blocker")
    release_8_proxy_specification = _rows(context, "release_8_proxy_specification")
    release_8_structural_gap = _rows(context, "release_8_structural_gap")
    release_8_nonpromotion_proof = _rows(context, "release_8_nonpromotion_proof")
    release_8_decision = _rows(context, "release_8_decision")
    release_9_proxy_registry = _rows(context, "release_9_proxy_registry")
    release_9_proxy_support = _rows(context, "release_9_proxy_support")
    release_9_decision = _rows(context, "release_9_decision")
    release_9_nonpromotion_proof = _rows(context, "release_9_nonpromotion_proof")
    tdc_ledger = _rows(context, "tdc_ledger")
    tdc_impulse = _rows(context, "tdc_impulse")
    tdc_source_coverage = _rows(context, "tdc_source_coverage")
    tdc_historical_panel = _rows(context, "tdc_historical_panel")
    deposit_pricing_pass_through = _rows(context, "deposit_pricing_pass_through")
    tdc_historical_reconciliation = _rows(context, "tdc_historical_reconciliation")
    threshold_simulation = _rows(context, "threshold_simulation")
    threshold_calibration = _rows(context, "threshold_calibration_ranges")
    calibrated_threshold = _rows(context, "threshold_calibrated_simulation")
    du_ru_bridge = _rows(context, "du_ru_tga_calibration_bridge")
    financialization_pressure = _rows(context, "financialization_pressure")
    financialization_evidence = _rows(context, "financialization_evidence_appendix")
    benchmark_calibration = _rows(context, "contractionary_benchmark_calibration")
    threshold_uncertainty = _rows(context, "threshold_uncertainty_bands")
    historical_validation = _rows(context, "historical_threshold_validation")
    policy_boundary = _rows(context, "policy_boundary_synthesis")
    blocker_resolution = _rows(context, "blocker_resolution_ledger")
    publication_claim_decision = _rows(context, "publication_claim_decision")
    final_blocker_ledger = _rows(context, "final_blocker_ledger")
    release_16_source_resolution = _rows(context, "release_16_source_resolution")
    release_16_no_further_promotion = _rows(context, "release_16_no_further_promotion")
    release_17_external_review = _rows(context, "release_17_external_review")
    release_17_publication_polish = _rows(context, "release_17_publication_polish")
    release_17_blocker_reopen = _rows(context, "release_17_blocker_reopen")
    release_18_live_refresh = _rows(context, "release_18_live_refresh")
    claim_pass = all(row["audit_status"] == "pass" for row in claim_rows)
    one_year = _row_by(context, "impulse", "horizon", "1y")
    impulse_value = one_year.get("annualized_public_interest_impulse_bil", "")
    impulse_gdp = one_year.get("public_interest_impulse_gdp_pct", "")
    return "\n".join(
        [
            "---",
            'title: "At the Rate Wall"',
            'subtitle: "Public Debt, Reserve Balances, and the Diminishing Returns to Monetary Tightening"',
            'author: "RateWall reproducible research package"',
            "format:",
            "  pdf:",
            "    toc: true",
            "    number-sections: true",
            "    colorlinks: true",
            "    documentclass: article",
            "    fig-cap-location: bottom",
            "execute:",
            "  echo: false",
            "---",
            "",
            "# Abstract",
            "",
            "RateWall is a source-labeled release package for studying debt-conditioned "
            "monetary transmission. It separates mechanical public-liability "
            "accounting, scenario diagnostics, bounded event-study evidence, "
            "valuation-readiness limitations, and welfare/incidence boundaries. "
            "It does not claim that higher rates always raise inflation, and it "
            "does not claim that the Federal Reserve has stopped working.",
            "",
            "# Evidence Architecture",
            "",
            "The release is organized into five layers: descriptive accounting, "
            "scenario diagnostics, empirical estimates, valuation readiness, and "
            "paper/deck support. The manifest keeps these layers separate so "
            "mechanical impulse rows are not promoted into causal estimates.",
            "",
            "```{=latex}",
            "\\clearpage",
            "```",
            "",
            "## Source Base",
            "",
            f"Current source snapshot kinds: `{dict(source_counts)}`. The public "
            "release uses `source_provenance.json` for source identifiers, URLs, "
            "units, release/as-of dates where available, and retrieval timestamps.",
            "",
            "## Mechanical 100 bps Impulse",
            "",
            f"The generated 100 bps impulse table includes {len(impulse_rows)} "
            "horizons: 1q, 1y, 3y, and 10y. In the current release, the one-year "
            f"annualized public-interest impulse is `{impulse_value}` billion "
            f"dollars, or `{impulse_gdp}` percent of GDP in the generated table. "
            "This is accounting arithmetic, not an inflation-effect estimate.",
            "",
            "## RateWall Dashboard",
            "",
            f"The generated dashboard has {len(dashboard_rows)} components. It "
            "labels mechanical, empirical-readiness, welfare-boundary, and "
            "completion surfaces separately, with pricing and incidence switches "
            "disabled.",
            "",
            "# Empirical Status",
            "",
            f"Empirical result statuses: `{dict(empirical_statuses)}`. The "
            "release uses SF Fed orthogonalized monetary surprises and rejects "
            "raw policy-rate changes as shocks. Event-study rows are bounded "
            "estimates with limitations, not a full LP/proxy-SVAR package.",
            "",
            "## Release 2.0 Causal Gate",
            "",
            f"The causal-identification audit has {len(causal_audit_rows)} "
            f"rows and {len(causal_blocker_rows)} machine-readable blocker rows. "
            "The release keeps stronger LP/proxy-SVAR language disabled while "
            "preserving the bounded event-study evidence.",
            "",
            "## Release 2.0 Submission Diagnostics",
            "",
            f"Release 2.0 adds {len(support_rows)} support diagnostic rows, "
            f"{len(robustness_rows)} robustness rows, and {len(submission_decision)} "
            "submission-identification decision rows. These outputs support a "
            "bounded admissible-shock event-study appendix and keep full "
            "LP/proxy-SVAR claims disabled.",
            "",
            "## Release 3.0 Dynamic Causal Gate",
            "",
            f"Release 3.0 adds {len(dynamic_lp)} dynamic-LP feasibility rows, "
            f"{len(proxy_svar)} proxy-SVAR feasibility rows, and "
            f"{len(dynamic_blocker)} final dynamic-causal blocker rows. These "
            "outputs make the journal-submission frontier auditable while "
            "keeping dynamic LP/proxy-SVAR claims disabled.",
            "",
            "## Release 4.0 Final Submission Gate",
            "",
            f"Release 4.0 adds {len(hac_rows)} HAC-style uncertainty diagnostic "
            f"rows, {len(placebo_rows)} predetermined-level placebo rows, "
            f"{len(promotion_contract)} disabled promotion-contract rows, and "
            f"{len(release_4_blocker)} strengthened final blocker rows. These "
            "outputs answer reviewer identification questions without promoting "
            "the evidence into a full dynamic LP/proxy-SVAR design.",
            "",
            "## Release 5.0 Controlled Dynamic LP Frontier",
            "",
            f"Release 5.0 adds {len(controlled_lp_results)} controlled "
            f"dynamic-LP result rows, {len(release_5_decision)} identification "
            f"decision rows, and {len(release_5_proxy_blocker)} proxy-SVAR blocker "
            "rows. These outputs allow a bounded admissible-shock dynamic-LP "
            "appendix only where support/rank gates pass, while keeping "
            "proxy-SVAR, pricing, holder-incidence, tax, MPC, welfare, and "
            "reset-calendar outputs disabled.",
            "",
            "## Release 6.0 Proxy-SVAR/System Identification Frontier",
            "",
            f"Release 6.0 adds {len(proxy_svar_system_panel)} source-backed "
            f"monthly system-panel rows, {len(proxy_svar_relevance)} proxy "
            f"relevance diagnostic rows, {len(proxy_svar_residual)} residual "
            f"diagnostic rows, {len(proxy_svar_timing)} timing/support rows, "
            f"{len(release_6_decision)} decision rows, and "
            f"{len(release_6_proxy_blocker)} final blocker rows. These outputs "
            "strengthen the reviewer-facing system evidence while keeping "
            "proxy-SVAR, pricing, holder-incidence, tax, MPC, welfare, and "
            "reset-calendar outputs disabled.",
            "",
            "## Release 7.0 System-Identification Frontier",
            "",
            f"Release 7.0 adds {len(release_7_lag_selection)} lag-selection "
            f"rows, {len(release_7_reduced_form_estimates)} reduced-form "
            f"system estimate rows, {len(release_7_residual_covariance)} "
            f"residual covariance rows, {len(release_7_proxy_support)} proxy "
            f"support rows, {len(release_7_timing_audit)} timing/exogeneity/"
            f"invertibility audit rows, {len(release_7_decision)} decision "
            f"rows, and {len(release_7_proxy_blocker)} final blocker rows. "
            "These outputs strengthen the system-identification review surface "
            "while keeping proxy-SVAR/system, pricing, holder-incidence, tax, "
            "MPC, welfare, and reset-calendar outputs disabled.",
            "",
            "## Release 8.0 System-Identification Non-Promotion Proof",
            "",
            f"Release 8.0 adds {len(release_8_proxy_specification)} "
            f"admissible-proxy specification audit rows, "
            f"{len(release_8_structural_gap)} structural gap rows, "
            f"{len(release_8_decision)} decision rows, and "
            f"{len(release_8_nonpromotion_proof)} final non-promotion proof "
            "rows. These outputs sharpen the strongest current boundary: the "
            "package remains bounded unless future proxy relevance, timing, "
            "exogeneity, invertibility, placebo/pretrend, and explicit "
            "claim-promotion gates pass.",
            "",
            "## Release 9.0 External-Proxy Publication Boundary",
            "",
            f"Release 9.0 adds {len(release_9_proxy_registry)} "
            f"external-proxy source registry rows, "
            f"{len(release_9_proxy_support)} expanded proxy-support audit "
            f"rows, {len(release_9_decision)} structural decision rows, and "
            f"{len(release_9_nonpromotion_proof)} final non-promotion proof "
            "rows. It integrates the Federal Reserve BRW shock series as an "
            "additional admissible external-proxy candidate and keeps "
            "structural proxy-SVAR/system, pricing, holder-incidence, tax, "
            "MPC, welfare, and reset-calendar outputs disabled.",
            "",
            "## Release 10.0 TDC Deposit-Channel Layer",
            "",
            f"Release 10.0 adds {len(tdc_ledger)} TDC accounting ledger rows, "
            f"{len(tdc_impulse)} DU/RU financing scenario rows, and "
            f"{len(tdc_source_coverage)} source-coverage rows. The new layer "
            "separates deposit pricing/pass-through from deposit quantity "
            "accounting and treats the DU deposit effect of RU Treasury "
            "financing as an accounting scenario, not a final incidence, "
            "welfare, or inflation-sign claim.",
            "",
            "## Release 11.0 Historical TDC and Deposit-Pricing Layer",
            "",
            f"Release 11.0 adds {len(tdc_historical_panel)} historical TDC "
            f"panel rows, {len(deposit_pricing_pass_through)} deposit-pricing "
            f"context rows, and {len(tdc_historical_reconciliation)} "
            "reconciliation rows. The historical field is a partial "
            "source-backed proxy where the inputs exist, not a final TDC "
            "estimate. Deposit pricing/pass-through remains a separate "
            "evidence surface from DU/RU deposit-quantity accounting.",
            "",
            "## Release 12.0 Threshold And Financialization-Pressure Extension",
            "",
            f"Release 12.0 adds {len(threshold_simulation)} conditional "
            f"threshold simulation rows and {len(financialization_pressure)} "
            "legacy retention-context rows. Offset ratios are "
            "reported only under explicit horizon-scaled contractionary "
            "benchmark, maturity, RU-financing-condition, TGA, fiscal-offset, "
            "deposit-pass-through context, and financial-retention assumptions. "
            "The safe-asset-retention "
            "surface maps retained public-interest flows into observed "
            "safe-asset holder context; it is not a causal financialization "
            "estimate and it does not claim the Fed has stopped working.",
            "",
            "## Release 13.0 Calibrated Threshold Layer",
            "",
            f"Release 13.0 adds {len(threshold_calibration)} source-labeled or "
            f"sibling-derived calibration-context rows, {len(calibrated_threshold)} "
            f"calibrated threshold rows, {len(du_ru_bridge)} DU/RU/TGA bridge "
            f"rows, and {len(financialization_evidence)} bounded "
            "financialization-evidence rows. The calibrated table keeps "
            "review-status ranges as calibration-range sensitivity inputs and "
            "labels the remaining DU outlay, fiscal-offset, and contractionary "
            "benchmark assumptions explicitly. It is not a final threshold date, final TDC estimate, "
            "pricing result, incidence result, welfare result, or causal "
            "financialization estimate.",
            "",
            "## Release 14.0 Historical Threshold Validation",
            "",
            f"Release 14.0 adds {len(benchmark_calibration)} contractionary "
            f"benchmark calibration rows, {len(threshold_uncertainty)} "
            f"uncertainty-band rows, {len(historical_validation)} historical "
            f"validation rows, and {len(policy_boundary)} policy-boundary rows. "
            "The layer documents which inputs are source-labeled context and "
            "which remain blocked for promotion. It does not create a universal "
            "RateWall date, final contractionary benchmark, or causal policy-"
            "failure claim.",
            "",
            "## Release 15.0 Publication-Claim Decision",
            "",
            f"Release 15.0 adds {len(blocker_resolution)} blocker-resolution "
            f"rows, {len(publication_claim_decision)} publication-claim decision "
            f"rows, and {len(final_blocker_ledger)} final blocker rows. Bounded "
            "accounting and conditional sensitivity claims are publication-ready "
            "with labels. Final threshold-date, policy-failure, causal "
            "financialization, pricing, incidence, welfare, and universal-sign "
            "claims remain blocked.",
            "",
            "## Release 16.0 Bounded-Publication Closeout",
            "",
            f"Release 16.0 adds {len(release_16_source_resolution)} final "
            f"source-resolution closeout rows and "
            f"{len(release_16_no_further_promotion)} no-further-promotion rows. "
            "It makes the bounded-publication decision explicit: exact DU "
            "recipient split, final RU absorption, fiscal-offset behavior, "
            "dynamic contractionary benchmark promotion, and causal "
            "financialization remain blocked unless future source/method "
            "gates and fail-closed tests deliberately reopen them.",
            "",
            "## Release 17.0 External Review And Publication Polish",
            "",
            f"Release 17.0 adds {len(release_17_external_review)} "
            f"external-review audit rows, {len(release_17_publication_polish)} "
            f"publication-polish QA rows, and {len(release_17_blocker_reopen)} "
            "blocker-reopen decision rows. The layer hardens paper, deck, "
            "README, appendix, and archive consistency while keeping Release "
            "16 no-further-promotion blockers closed. It does not introduce a "
            "universal threshold date, policy-failure claim, final deposit "
            "sign, pricing result, incidence result, welfare result, or causal "
            "financialization result.",
            "",
            "## Release 18.0 Live Refresh And Publication Freeze",
            "",
            f"Release 18.0 adds {len(release_18_live_refresh)} live-refresh "
            "robustness rows. The layer bounds SSL/read stalls with source "
            "timeouts and provenance-preserving fallbacks, then freezes the "
            "publication boundary: source refresh success or fallback labeling "
            "does not promote policy-failure, final threshold-date, pricing, "
            "incidence, welfare, deposit-sign, universal inflation-sign, or "
            "causal-financialization claims.",
            "",
            "# Figure Plate",
            "",
            "- `outputs/figures/ratewall_100bps_impulse.svg`: mechanical 100 bps public-interest impulse.",
            "- `outputs/figures/ratewall_empirical_state_association.svg`: bounded shock/state association.",
            "- `outputs/figures/debt_held_public_gdp.svg`: debt held by public scaled by GDP.",
            "- `outputs/figures/reserves_gdp.svg`: reserve balances scaled by GDP.",
            "- `outputs/reports/ratewall_figure_plate.md`: full generated figure plate with roles.",
            "- `outputs/reports/ratewall_causal_identification_appendix.md`: causal gate.",
            "- `outputs/figures/ratewall_event_study_robustness.svg`: Release 2.0 event-study robustness.",
            "- `outputs/figures/ratewall_dynamic_causal_gate.svg`: Release 3.0 dynamic causal gate.",
            "- `outputs/figures/ratewall_release_4_0_identification_frontier.svg`: Release 4.0 identification frontier.",
            "- `outputs/figures/ratewall_release_5_0_dynamic_lp_estimates.svg`: Release 5.0 controlled dynamic-LP estimates.",
            "- `outputs/figures/ratewall_release_6_0_system_identification_gate.svg`: Release 6.0 system-identification gate.",
            "- `outputs/figures/ratewall_release_7_0_system_identification_frontier.svg`: Release 7.0 system-identification frontier.",
            "- `outputs/figures/ratewall_release_8_0_nonpromotion_gate.svg`: Release 8.0 non-promotion gate.",
            "- `outputs/figures/ratewall_release_9_0_structural_boundary.svg`: Release 9.0 structural boundary.",
            "",
            "# Table Plate",
            "",
            "The authoritative tables are generated CSV artifacts. The release table "
            "plate records the key tables, row counts, and claim role in "
            "`ratewall_table_plate.md`; the archive manifest records file "
            "hashes and byte sizes.",
            "",
            "# Claim Boundary Audit",
            "",
            f"Claim-boundary audit status: `{'pass' if claim_pass else 'fail'}`.",
            "",
            *[f"- `{row['boundary']}`: `{row['audit_status']}`" for row in claim_rows],
            "",
            "# Release Use",
            "",
            "Use the tables and appendices as the authoritative evidence surface. "
            "The paper and deck are generated synthesis layers; if release text "
            "ever conflicts with the source tables, fix the generator or the "
            "source artifact rather than widening the claim.",
            "",
        ]
    )


def _slide_deck_text(context: dict[str, object]) -> str:
    event_count = _count_status(
        context, "admissible_event_study_estimate_with_limitations"
    )
    source_counts = Counter(row.get("snapshot_kind", "") for row in context["sources"])
    dynamic_blocker_count = len(_rows(context, "dynamic_causal_blocker"))
    release_4_blocker_count = len(_rows(context, "release_4_blocker"))
    controlled_lp_count = len(_rows(context, "controlled_dynamic_lp_results"))
    release_6_blocker_count = len(_rows(context, "release_6_proxy_blocker"))
    release_7_estimate_count = len(_rows(context, "release_7_reduced_form_estimates"))
    release_7_blocker_count = len(_rows(context, "release_7_proxy_blocker"))
    release_8_proxy_spec_count = len(_rows(context, "release_8_proxy_specification"))
    release_8_proof_count = len(_rows(context, "release_8_nonpromotion_proof"))
    tdc_impulse_count = len(_rows(context, "tdc_impulse"))
    tdc_coverage_count = len(_rows(context, "tdc_source_coverage"))
    tdc_historical_count = len(_rows(context, "tdc_historical_panel"))
    deposit_pricing_count = len(_rows(context, "deposit_pricing_pass_through"))
    threshold_count = len(_rows(context, "threshold_simulation"))
    financialization_count = len(_rows(context, "financialization_pressure"))
    calibration_count = len(_rows(context, "threshold_calibration_ranges"))
    calibrated_threshold_count = len(_rows(context, "threshold_calibrated_simulation"))
    bridge_count = len(_rows(context, "du_ru_tga_calibration_bridge"))
    financialization_evidence_count = len(
        _rows(context, "financialization_evidence_appendix")
    )
    benchmark_count = len(_rows(context, "contractionary_benchmark_calibration"))
    uncertainty_count = len(_rows(context, "threshold_uncertainty_bands"))
    validation_count = len(_rows(context, "historical_threshold_validation"))
    boundary_count = len(_rows(context, "policy_boundary_synthesis"))
    blocker_resolution_count = len(_rows(context, "blocker_resolution_ledger"))
    publication_claim_count = len(_rows(context, "publication_claim_decision"))
    final_blocker_count = len(_rows(context, "final_blocker_ledger"))
    release_16_source_resolution_count = len(
        _rows(context, "release_16_source_resolution")
    )
    release_16_no_further_promotion_count = len(
        _rows(context, "release_16_no_further_promotion")
    )
    release_17_external_review_count = len(_rows(context, "release_17_external_review"))
    release_17_publication_polish_count = len(
        _rows(context, "release_17_publication_polish")
    )
    release_17_blocker_reopen_count = len(_rows(context, "release_17_blocker_reopen"))
    safe_asset_count = len(_rows(context, "safe_asset_retention_context"))
    buyer_case_count = len(_rows(context, "buyer_case_sign_matrix"))
    mpc_count = len(_rows(context, "recipient_mpc_scenarios"))
    release_19_invariant_count = len(_rows(context, "release_19_invariants"))
    release_19_methodology_count = len(_rows(context, "release_19_methodology"))
    release_18_live_refresh_count = len(_rows(context, "release_18_live_refresh"))
    release_20_activity_count = len(_rows(context, "release_20_activity_benchmark"))
    release_20_lp_count = len(_rows(context, "release_20_lp_diagnostics"))
    release_20_decision_count = len(_rows(context, "release_20_decision"))
    release_21_live_count = len(_rows(context, "release_21_live_refresh"))
    release_21_benchmark_count = len(_rows(context, "release_21_benchmark_gate"))
    release_21_invariant_count = len(_rows(context, "release_21_backend_invariants"))
    release_22_audit_count = len(_rows(context, "release_22_source_repro_audit"))
    release_22_gate_count = len(_rows(context, "release_22_source_gate"))
    return "\n".join(
        [
            "# RateWall Deck-Ready Outline",
            "",
            "## Slide 1: Research Question",
            "Debt-conditioned monetary transmission: when public liabilities "
            "change the marginal cost and effectiveness of tightening.",
            "",
            "## Slide 2: Architecture",
            "Separate accounting, scenarios, empirical estimates, valuation "
            "readiness, and welfare/incidence boundaries.",
            "",
            "## Slide 3: Source Base",
            f"Current provenance: {dict(source_counts)}.",
            "",
            "## Slide 4: Mechanical 100 bps Impulse",
            "Use `ratewall_100bps_impulse.csv` and `ratewall_100bps_impulse.svg`.",
            "",
            "## Slide 5: RateWall State Variables",
            "Use `ratewall_databook_metrics.csv` and selected generated SVGs.",
            "",
            "## Slide 6: Empirical Evidence",
            f"Report {event_count} bounded event-study estimates from SF Fed "
            "orthogonalized monetary surprises.",
            "",
            "## Slide 7: What Is Not Claimed",
            "No raw-rate shocks, no universal inflation-sign claim, no claim "
            "that the Fed has stopped working.",
            "",
            "## Slide 8: Release 3.0 Dynamic Causal Gate",
            f"Use {dynamic_blocker_count} final dynamic-causal blocker rows to "
            "explain why the package remains bounded rather than claiming a "
            "full LP/proxy-SVAR.",
            "",
            "## Slide 9: Release 4.0 Final Submission Gate",
            f"Use {release_4_blocker_count} strengthened final blocker rows "
            "plus HAC/placebo diagnostics to answer review questions without "
            "promoting stronger causal claims.",
            "",
            "## Slide 10: Release 5.0 Dynamic LP Frontier",
            f"Release 5.0 adds {controlled_lp_count} controlled dynamic-LP "
            "result rows where support gates allow; proxy-SVAR and pricing "
            "claims remain disabled.",
            "",
            "## Slide 11: Release 6.0 System Frontier",
            f"Use {release_6_blocker_count} final proxy-SVAR/system blocker "
            "rows plus the source-labeled system diagnostics to explain why "
            "Release 6.0 remains bounded.",
            "",
            "## Slide 12: Release 7.0 System Frontier",
            f"Use {release_7_blocker_count} final blocker rows and "
            f"{release_7_estimate_count} reduced-form estimate rows to explain "
            "why Release 7.0 remains a diagnostic system package rather than a "
            "proxy-SVAR claim.",
            "",
            "## Slide 13: Release 8.0 Non-Promotion Proof",
            f"Use {release_8_proxy_spec_count} proxy-specification audit rows "
            f"and {release_8_proof_count} proof rows to explain why structural "
            "system-identification remains unpromoted.",
            "",
            "## Slide 14: Release 10.0 TDC Deposit Channel",
            f"Use {tdc_impulse_count} DU/RU financing scenario rows and "
            f"{tdc_coverage_count} source-coverage rows to explain deposit "
            "quantity accounting separately from deposit pricing/pass-through.",
            "",
            "## Slide 15: Release 11.0 Historical TDC Context",
            f"Use {tdc_historical_count} historical partial-proxy rows and "
            f"{deposit_pricing_count} deposit-pricing context rows to separate "
            "DU/RU quantity accounting from deposit-rate pass-through evidence.",
            "",
            "## Slide 16: Release 12.0 Threshold Diagnostics",
            f"Use {threshold_count} conditional threshold rows and "
            f"{financialization_count} legacy retention-context rows to show "
            "which assumptions make offsets large without claiming policy "
            "failure or causal financialization.",
            "",
            "## Slide 17: Release 13.0 Calibrated Threshold Context",
            f"Use {calibration_count} calibration range rows, "
            f"{calibrated_threshold_count} calibrated threshold rows, and "
            f"{bridge_count} DU/RU/TGA bridge rows, plus "
            f"{financialization_evidence_count} financialization evidence rows, "
            "to show which assumptions are source-labeled or sibling-derived "
            "context and which remain sensitivity-review scenario assumptions.",
            "",
            "## Slide 18: Release 14.0 Historical Validation",
            f"Use {benchmark_count} benchmark rows, {uncertainty_count} "
            f"uncertainty-band rows, {validation_count} validation rows, and "
            f"{boundary_count} boundary rows to explain what remains blocked "
            "for threshold promotion.",
            "",
            "## Slide 19: Release 15.0 Publication Decision",
            f"Use {blocker_resolution_count} blocker rows, "
            f"{publication_claim_count} claim-decision rows, and "
            f"{final_blocker_count} final blocker rows to show bounded claims "
            "are publishable while promotion claims remain disabled.",
            "",
            "## Slide 20: Release 16.0 Bounded Publication Closeout",
            f"Use {release_16_source_resolution_count} source-resolution "
            f"closeout rows and {release_16_no_further_promotion_count} "
            "no-further-promotion rows to show the final bounded publication "
            "state without widening threshold, policy-failure, deposit-sign, "
            "pricing, incidence, welfare, or causal-financialization claims.",
            "",
            "## Slide 21: Release 17.0 External Review And Polish",
            f"Use {release_17_external_review_count} external-review rows, "
            f"{release_17_publication_polish_count} polish QA rows, and "
            f"{release_17_blocker_reopen_count} blocker-reopen decision rows "
            "to show the public surfaces are consistent and no Release 16 "
            "blocker was reopened without new source/method evidence.",
            "",
            "## Slide 22: Release 18.0 Live Refresh And Publication Freeze",
            f"Use {release_18_live_refresh_count} live-refresh robustness rows "
            "to show source-refresh stalls now fail closed into provenance-"
            "labeled fallbacks without widening publication claims.",
            "",
            "## Slide 23: Release 19.0 Post-Audit Methodology Hardening",
            f"Use {safe_asset_count} safe-asset rows, {buyer_case_count} "
            f"buyer-case rows, {mpc_count} MPC-scenario rows, "
            f"{release_19_invariant_count} invariant rows, and "
            f"{release_19_methodology_count} methodology rows to show the "
            "audit corrections without promoting incidence, welfare, or "
            "causal-financialization claims.",
            "",
            "## Slide 24: Release 20.0 Submission Benchmark Gate",
            f"Use {release_20_activity_count} activity/demand benchmark rows, "
            f"{release_20_lp_count} LP diagnostic rows, and "
            f"{release_20_decision_count} decision rows to show coherent "
            "admissible-shock evidence while blocking GDP-share threshold "
            "promotion.",
            "",
            "## Slide 25: Release 21.0 Backend Closeout",
            f"Use {release_21_live_count} live-refresh endpoint rows, "
            f"{release_21_benchmark_count} final benchmark gate rows, and "
            f"{release_21_invariant_count} backend invariant rows to show the "
            "backend is fail-closed without PDF/deck claim promotion.",
            "",
            "## Slide 26: Release 22.0 Backend Fixes",
            f"Use {release_22_audit_count} source/repro/accounting audit rows "
            f"and {release_22_gate_count} source-gate rows to show MSPD fallback "
            "status, vendored calibration extracts, and accounting invariants.",
            "",
            "## Slide 27: Valuation And Holder Boundaries",
            "Pricing, allocation weights, reset calendars, tax/MPC layers, "
            "welfare, and incidence remain disabled.",
            "",
            "## Slide 28: Limitations",
            "Use `ratewall_limitations_appendix.md` and `evidence_limitations.csv`.",
            "",
            "## Slide 28: Release Reproducibility",
            "Use `ratewall_release_manifest.json` and "
            "`ratewall_validation_package.md`.",
            "",
        ]
    )


def _slide_deck_quarto_text(context: dict[str, object]) -> str:
    source_counts = Counter(row.get("snapshot_kind", "") for row in context["sources"])
    one_year = _row_by(context, "impulse", "horizon", "1y")
    impulse_value = one_year.get("annualized_public_interest_impulse_bil", "")
    event_count = _count_status(
        context, "admissible_event_study_estimate_with_limitations"
    )
    blocker_count = _count_status(
        context, "final_documented_blocker_for_full_causal_lp_proxy_svar"
    )
    causal_blocker_count = len(_rows(context, "causal_blocker"))
    support_count = len(_rows(context, "support_diagnostics"))
    robustness_count = len(_rows(context, "event_study_robustness"))
    dynamic_lp_count = len(_rows(context, "dynamic_lp_feasibility"))
    proxy_svar_count = len(_rows(context, "proxy_svar_feasibility"))
    dynamic_blocker_count = len(_rows(context, "dynamic_causal_blocker"))
    hac_count = len(_rows(context, "event_study_hac"))
    placebo_count = len(_rows(context, "pretrend_placebo"))
    promotion_count = len(_rows(context, "promotion_contract"))
    release_4_blocker_count = len(_rows(context, "release_4_blocker"))
    controlled_lp_count = len(_rows(context, "controlled_dynamic_lp_results"))
    release_5_decision_count = len(_rows(context, "release_5_decision"))
    release_5_proxy_blocker_count = len(_rows(context, "release_5_proxy_blocker"))
    system_panel_count = len(_rows(context, "proxy_svar_system_panel"))
    relevance_count = len(_rows(context, "proxy_svar_relevance"))
    residual_count = len(_rows(context, "proxy_svar_residual"))
    release_6_decision_count = len(_rows(context, "release_6_decision"))
    release_6_proxy_blocker_count = len(_rows(context, "release_6_proxy_blocker"))
    release_7_lag_count = len(_rows(context, "release_7_lag_selection"))
    release_7_estimate_count = len(_rows(context, "release_7_reduced_form_estimates"))
    release_7_proxy_support_count = len(_rows(context, "release_7_proxy_support"))
    release_7_decision_count = len(_rows(context, "release_7_decision"))
    release_7_proxy_blocker_count = len(_rows(context, "release_7_proxy_blocker"))
    release_8_proxy_spec_count = len(_rows(context, "release_8_proxy_specification"))
    release_8_gap_count = len(_rows(context, "release_8_structural_gap"))
    release_8_proof_count = len(_rows(context, "release_8_nonpromotion_proof"))
    release_8_decision_count = len(_rows(context, "release_8_decision"))
    release_9_registry_count = len(_rows(context, "release_9_proxy_registry"))
    release_9_support_count = len(_rows(context, "release_9_proxy_support"))
    release_9_decision_count = len(_rows(context, "release_9_decision"))
    release_9_proof_count = len(_rows(context, "release_9_nonpromotion_proof"))
    tdc_ledger_count = len(_rows(context, "tdc_ledger"))
    tdc_impulse_count = len(_rows(context, "tdc_impulse"))
    tdc_historical_count = len(_rows(context, "tdc_historical_panel"))
    deposit_pricing_count = len(_rows(context, "deposit_pricing_pass_through"))
    tdc_reconciliation_count = len(_rows(context, "tdc_historical_reconciliation"))
    threshold_count = len(_rows(context, "threshold_simulation"))
    financialization_count = len(_rows(context, "financialization_pressure"))
    calibration_count = len(_rows(context, "threshold_calibration_ranges"))
    calibrated_threshold_count = len(_rows(context, "threshold_calibrated_simulation"))
    bridge_count = len(_rows(context, "du_ru_tga_calibration_bridge"))
    tdc_coverage_count = len(_rows(context, "tdc_source_coverage"))
    benchmark_count = len(_rows(context, "contractionary_benchmark_calibration"))
    uncertainty_count = len(_rows(context, "threshold_uncertainty_bands"))
    validation_count = len(_rows(context, "historical_threshold_validation"))
    boundary_count = len(_rows(context, "policy_boundary_synthesis"))
    blocker_resolution_count = len(_rows(context, "blocker_resolution_ledger"))
    publication_claim_count = len(_rows(context, "publication_claim_decision"))
    final_blocker_count = len(_rows(context, "final_blocker_ledger"))
    release_16_source_resolution_count = len(
        _rows(context, "release_16_source_resolution")
    )
    release_16_no_further_promotion_count = len(
        _rows(context, "release_16_no_further_promotion")
    )
    release_17_external_review_count = len(_rows(context, "release_17_external_review"))
    release_17_publication_polish_count = len(
        _rows(context, "release_17_publication_polish")
    )
    release_17_blocker_reopen_count = len(_rows(context, "release_17_blocker_reopen"))
    release_18_live_refresh_count = len(_rows(context, "release_18_live_refresh"))
    metric_count = len(_rows(context, "metrics"))
    return "\n".join(
        [
            "---",
            'title: "RateWall"',
            'subtitle: "Debt-conditioned monetary transmission"',
            "format:",
            "  pptx:",
            "    toc: false",
            "---",
            "",
            "# RateWall: the question",
            "",
            "When public liabilities are large, rate hikes can have two channels at once: conventional contraction and public-liability interest flows.",
            "",
            "# The release separates five evidence layers",
            "",
            "- Descriptive accounting",
            "- Scenario diagnostics",
            "- Bounded empirical estimates",
            "- Valuation-readiness limits",
            "- Welfare and incidence boundaries",
            "",
            "# Source base: live first, browser-download where needed",
            "",
            f"- Snapshot kinds: `{dict(source_counts)}`",
            "- Provenance records units, source URLs, release/as-of dates where available, and retrieval timestamps.",
            "",
            "# Mechanical accounting: the 100 bps impulse",
            "",
            f"- One-year annualized public-interest impulse: `{impulse_value}` billion dollars.",
            "- This is accounting arithmetic, not an inflation-effect estimate.",
            "",
            "# Data book: state variables, not a threshold slogan",
            "",
            f"- Generated metric rows: `{metric_count}`",
            "- Figures regenerate from source-labeled, fallback-aware tables.",
            "",
            "# Release 10.0: TDC deposit-channel accounting",
            "",
            f"- TDC accounting ledger rows: `{tdc_ledger_count}`",
            f"- DU/RU financing scenario rows: `{tdc_impulse_count}`",
            f"- TDC source-coverage rows: `{tdc_coverage_count}`",
            "- Deposit pricing/pass-through is tracked separately from deposit quantity accounting.",
            "- These are accounting scenarios, not final incidence or inflation-sign claims.",
            "",
            "# Release 11.0: historical TDC and deposit-pricing context",
            "",
            f"- Historical TDC panel rows: `{tdc_historical_count}`",
            f"- Deposit-pricing/pass-through context rows: `{deposit_pricing_count}`",
            f"- Historical reconciliation rows: `{tdc_reconciliation_count}`",
            "- Historical TDC rows are partial source-backed proxies where fields permit.",
            "- Deposit-pricing/pass-through remains separate from DU/RU quantity accounting.",
            "",
            "# Release 12.0: conditional threshold and legacy retention context",
            "",
            f"- Conditional threshold simulation rows: `{threshold_count}`",
            f"- Legacy bounded retention-context rows: `{financialization_count}`",
            "- Threshold hits are scenario diagnostics under explicit assumptions, not a claim that the Fed has stopped working.",
            "- Financialization-pressure rows map retained public-interest flows to holder context; they are not causal financialization estimates.",
            "",
            "# Release 13.0: calibrated threshold context",
            "",
            f"- Calibration range rows: `{calibration_count}`",
            f"- Calibrated threshold rows: `{calibrated_threshold_count}`",
            f"- DU/RU/TGA bridge rows: `{bridge_count}`",
            "- Source-labeled and sibling-derived ranges discipline scenario shares only as review-context inputs.",
            "- Remaining behavioral assumptions stay explicit and claim-bounded.",
            "",
            "# Release 14.0: historical threshold validation",
            "",
            f"- Benchmark calibration rows: `{benchmark_count}`",
            f"- Threshold uncertainty-band rows: `{uncertainty_count}`",
            f"- Historical validation rows: `{validation_count}`",
            f"- Policy-boundary synthesis rows: `{boundary_count}`",
            "- Threshold validation rows reconcile accounting/scenario layers against empirical and source-coverage gates.",
            "- The layer does not create a universal RateWall date, final contractionary benchmark, or policy-failure claim.",
            "",
            "# Release 15.0: publication-claim decision",
            "",
            f"- Blocker-resolution rows: `{blocker_resolution_count}`",
            f"- Publication-claim decision rows: `{publication_claim_count}`",
            f"- Final blocker rows: `{final_blocker_count}`",
            "- Bounded accounting and conditional sensitivity claims are publishable with labels.",
            "- Final threshold-date, policy-failure, causal financialization, pricing, incidence, and welfare claims remain blocked.",
            "",
            "# Release 16.0: bounded publication closeout",
            "",
            f"- Source-resolution closeout rows: `{release_16_source_resolution_count}`",
            f"- No-further-promotion rows: `{release_16_no_further_promotion_count}`",
            "- Exact DU recipient split, final RU absorption, fiscal-offset behavior, dynamic benchmark promotion, and causal financialization stay blocked.",
            "- This is a publication closeout, not a policy-failure, final threshold-date, pricing, incidence, welfare, or causal-financialization claim.",
            "",
            "# Release 17.0: external review and polish",
            "",
            f"- External-review audit rows: `{release_17_external_review_count}`",
            f"- Publication-polish QA rows: `{release_17_publication_polish_count}`",
            f"- Blocker-reopen decision rows: `{release_17_blocker_reopen_count}`",
            "- Paper, deck, README, appendices, archive, and validation surfaces remain aligned with the Release 16 bounded-publication closeout.",
            "- No blocker is reopened without new source/method evidence and fail-closed tests.",
            "",
            "# Release 18.0: live refresh and publication freeze",
            "",
            f"- Live-refresh robustness rows: `{release_18_live_refresh_count}`",
            "- SSL/read stalls fail closed into provenance-labeled fallback rows.",
            "- Refresh success or fallback labeling does not widen policy-failure, final threshold-date, pricing, incidence, welfare, deposit-sign, universal inflation-sign, or causal-financialization claims.",
            "",
            "# Empirical evidence: bounded event-study rows",
            "",
            f"- Bounded event-study estimates: `{event_count}`",
            "- Shock dataset: SF Fed orthogonalized monetary surprises.",
            "- Raw policy-rate changes remain rejected.",
            "",
            "# Stronger causal claims remain gated",
            "",
            f"- Full LP/proxy-SVAR blocker rows: `{blocker_count}`",
            f"- Release 2.0 defensibility blocker rows: `{causal_blocker_count}`",
            f"- Release 2.0 support diagnostic rows: `{support_count}`",
            f"- Release 2.0 robustness rows: `{robustness_count}`",
            "- No claim that higher rates always raise inflation.",
            "- No claim that the Fed has stopped working.",
            "",
            "# Release 3.0: dynamic causal frontier",
            "",
            f"- Dynamic LP feasibility rows: `{dynamic_lp_count}`",
            f"- Proxy-SVAR feasibility rows: `{proxy_svar_count}`",
            f"- Final dynamic-causal blocker rows: `{dynamic_blocker_count}`",
            "- Full LP/proxy-SVAR claims remain disabled.",
            "",
            "# Release 4.0: final submission frontier",
            "",
            f"- HAC-style uncertainty diagnostic rows: `{hac_count}`",
            f"- Predetermined-level placebo rows: `{placebo_count}`",
            f"- Disabled promotion-contract rows: `{promotion_count}`",
            f"- Strengthened final blocker rows: `{release_4_blocker_count}`",
            "- Stronger dynamic causal claims remain disabled.",
            "",
            "# Release 5.0: controlled dynamic LP frontier",
            "",
            f"- Controlled dynamic-LP result rows: `{controlled_lp_count}`",
            f"- Release 5.0 identification-decision rows: `{release_5_decision_count}`",
            f"- Proxy-SVAR final blocker rows: `{release_5_proxy_blocker_count}`",
            "- Bounded controlled LP appendix may be enabled; proxy-SVAR, pricing, and incidence outputs remain disabled.",
            "",
            "# Release 6.0: proxy-SVAR/system frontier",
            "",
            f"- Source-backed system-panel rows: `{system_panel_count}`",
            f"- Proxy relevance rows: `{relevance_count}`",
            f"- Residual diagnostic rows: `{residual_count}`",
            f"- Release 6.0 decision rows: `{release_6_decision_count}`",
            f"- Proxy-SVAR/system blocker rows: `{release_6_proxy_blocker_count}`",
            "- System diagnostics are review evidence only; proxy-SVAR, pricing, reset-calendar, and incidence outputs remain disabled.",
            "",
            "# Release 7.0: system-identification frontier",
            "",
            f"- Lag-selection rows: `{release_7_lag_count}`",
            f"- Reduced-form estimate rows: `{release_7_estimate_count}`",
            f"- Proxy support rows: `{release_7_proxy_support_count}`",
            f"- Release 7.0 decision rows: `{release_7_decision_count}`",
            f"- Final blocker rows: `{release_7_proxy_blocker_count}`",
            "- Reduced-form system diagnostics are review evidence only; proxy-SVAR/system, pricing, reset-calendar, and incidence outputs remain disabled.",
            "",
            "# Release 8.0: final system non-promotion proof",
            "",
            f"- Proxy-specification audit rows: `{release_8_proxy_spec_count}`",
            f"- Structural gap rows: `{release_8_gap_count}`",
            f"- Release 8.0 decision rows: `{release_8_decision_count}`",
            f"- Non-promotion proof rows: `{release_8_proof_count}`",
            "- Structural proxy-SVAR/system identification remains unpromoted; all disabled switches remain false.",
            "",
            "# Release 9.0: expanded external-proxy boundary",
            "",
            f"- External-proxy source registry rows: `{release_9_registry_count}`",
            f"- Expanded proxy-support audit rows: `{release_9_support_count}`",
            f"- Release 9.0 decision rows: `{release_9_decision_count}`",
            f"- Final publication-boundary proof rows: `{release_9_proof_count}`",
            "- BRW is integrated as an additional admissible proxy candidate; structural proxy-SVAR/system, pricing, reset-calendar, and incidence claims remain disabled.",
            "",
            "# Valuation boundary: fail closed",
            "",
            "- Pricing output: disabled",
            "- Holder allocation weights: disabled",
            "- Reset-calendar construction: disabled",
            "- Welfare/incidence output: disabled",
            "",
            "# Reproducible release",
            "",
            "- `ratewall_release_manifest.json`",
            "- `ratewall_claim_boundary_audit.csv`",
            "- `ratewall_validation_package.md`",
            "- `ratewall_release_23_reproducibility_hash_manifest.json`",
            "",
            "# Release 16.0 status",
            "",
            "- Paper, deck, appendices, README, archive manifest, and validation checklist regenerate from outputs.",
            "- The release is a bounded causal-evidence, calibrated conditional-threshold, historical-validation, publication-decision, and no-further-promotion closeout package, not a proxy-SVAR, pricing, incidence, welfare, policy-failure, final TDC, or causal-financialization engine.",
            "",
        ]
    )


def _publication_claim_decision_memo_text(context: dict[str, object]) -> str:
    blocker_rows = _rows(context, "blocker_resolution_ledger")
    claim_rows = _rows(context, "publication_claim_decision")
    final_rows = _rows(context, "final_blocker_ledger")
    blocked = [
        row
        for row in blocker_rows
        if row.get("release_15_resolution_status", "").startswith("blocked")
    ]
    enabled_claims = [
        row for row in claim_rows if row.get("publication_claim_enabled") == "true"
    ]
    lines = [
        "# RateWall Publication-Claim Decision Memo",
        "",
        "Release 15.0 is a final publication-boundary layer. It allows bounded "
        "accounting, scenario, and context claims with labels, and blocks final "
        "threshold, policy-failure, causal-financialization, pricing, incidence, "
        "welfare, and universal-sign claims.",
        "",
        "## Machine-Readable Inputs",
        "",
        f"- Blocker-resolution rows: {len(blocker_rows)}",
        f"- Publication-claim decision rows: {len(claim_rows)}",
        f"- Final blocker rows: {len(final_rows)}",
        f"- Blocked-for-promotion rows: {len(blocked)}",
        f"- Enabled bounded publication claims: {len(enabled_claims)}",
        "",
        "## Final Decision",
        "",
        "Publish the bounded RateWall package as source-labeled accounting with "
        "MSPD-dependent rows kept fallback/review context-only, "
        "conditional threshold sensitivity, bounded admissible-shock evidence, "
        "deposit-pricing context, and explicit blocker ledgers. Do not publish "
        "a universal RateWall date or claim that the Fed has stopped working.",
        "",
        "## Remaining Blockers",
        "",
    ]
    for row in blocker_rows:
        lines.append(
            f"- `{row.get('blocker_id')}`: "
            f"`{row.get('release_15_resolution_status')}`; "
            f"{row.get('remaining_gap')}"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "All promotion switches remain false. Any future promotion must be "
            "implemented as an explicit source/method gate with fail-closed "
            "tests before release text changes.",
            "",
        ]
    )
    return "\n".join(lines)


def _release_16_bounded_publication_closeout_memo_text(
    context: dict[str, object],
) -> str:
    source_resolution = _rows(context, "release_16_source_resolution")
    no_promotion = _rows(context, "release_16_no_further_promotion")
    source_labels = Counter(row.get("source_label", "") for row in source_resolution)
    closed_rows = [
        row
        for row in source_resolution
        if row.get("release_16_resolution_status") == "final_no_further_promotion"
    ]
    lines = [
        "# RateWall Release 16.0 Bounded-Publication Closeout Memo",
        "",
        "Release 16.0 closes the current source-resolution frontier. The package "
        "is publication-ready only as bounded accounting, calibrated scenario "
        "sensitivity, bounded admissible-shock evidence, TDC/deposit-channel "
        "context, and explicit no-further-promotion ledgers.",
        "",
        "## Machine-Readable Inputs",
        "",
        f"- Source-resolution closeout rows: {len(source_resolution)}",
        f"- Final no-further-promotion source rows: {len(closed_rows)}",
        f"- No-further-promotion ledger rows: {len(no_promotion)}",
        f"- Source labels: {dict(source_labels)}",
        "",
        "## Closeout Decision",
        "",
        "Do not widen the Release 15 bounded claims. The final threshold-date, "
        "policy-failure, exact DU/RU/TGA deposit effect, causal-financialization, "
        "pricing, holder-incidence, tax, MPC, welfare, allocation-weight, and "
        "reset-calendar-construction claims remain disabled.",
        "",
        "## Source-Resolution Frontier",
        "",
    ]
    for row in source_resolution:
        lines.append(
            f"- `{row.get('blocker_id')}`: "
            f"`{row.get('source_evidence_status')}`; "
            f"{row.get('allowed_publication_language')}; blocks "
            f"{row.get('blocked_publication_language')}"
        )
    lines.extend(
        [
            "",
            "## Reopening Rule",
            "",
            "Any future promotion must add a new source/method gate, regenerate "
            "the machine-readable ledgers, and prove fail-closed tests before "
            "release prose changes.",
            "",
        ]
    )
    return "\n".join(lines)


def _release_16_reviewer_blocker_text(context: dict[str, object]) -> str:
    no_promotion = _rows(context, "release_16_no_further_promotion")
    source_resolution = _rows(context, "release_16_source_resolution")
    lines = [
        "# RateWall Release 16.0 Reviewer Blocker Text",
        "",
        "The current evidence supports bounded accounting and scenario language, "
        "not stronger claims. The following blockers are final for this release "
        "because the required source fields, behavioral model, causal design, "
        "or explicit opt-in gates are absent.",
        "",
        "## No-Further-Promotion Rows",
        "",
    ]
    for row in no_promotion:
        lines.append(
            f"- `{row.get('claim_id')}`: allow "
            f"{row.get('allowed_claim')}; block {row.get('blocked_claim')}; "
            f"reopen only with {row.get('future_reopen_requirement')}."
        )
    lines.extend(
        [
            "",
            "## Source Evidence Status",
            "",
        ]
    )
    for row in source_resolution:
        lines.append(
            f"- `{row.get('blocker_id')}`: "
            f"`{row.get('source_label')}` / "
            f"`{row.get('source_evidence_status')}`."
        )
    lines.extend(
        [
            "",
            "## Boundary Language",
            "",
            "The paper should say the RateWall mechanism is a conditional public-"
            "liability accounting and scenario framework. It should not say "
            "higher rates always raise inflation, the Fed has stopped working, "
            "higher rates always raise deposits, a final threshold date has "
            "been found, or higher rates causally financialize the economy.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_appendix_text(context: dict[str, object]) -> str:
    sources = list(context["sources"])
    by_source = Counter(row.get("source_id", "") for row in sources)
    by_kind = Counter(row.get("snapshot_kind", "") for row in sources)
    lines = [
        "# Source And Provenance Appendix",
        "",
        f"- Source rows: {len(sources)}",
        f"- Snapshot kinds: {dict(by_kind)}",
        "",
        "## Source Families",
        "",
    ]
    for source_id, count in sorted(by_source.items()):
        lines.append(f"- {source_id}: {count}")
    lines.extend(
        [
            "",
            "## Provenance Fields",
            "",
            "Every source row is expected to carry source id, series id, URL, "
            "units, frequency, transform, source release/as-of date where "
            "available, and retrieval timestamp. Secrets are not stored in "
            "provenance URLs.",
            "",
        ]
    )
    return "\n".join(lines)


def _empirical_appendix_text(context: dict[str, object]) -> str:
    empirical = _rows(context, "empirical_results")
    panel = _rows(context, "outcome_panel")
    causal_audit = _rows(context, "causal_audit")
    causal_blocker = _rows(context, "causal_blocker")
    support_rows = _rows(context, "support_diagnostics")
    robustness_rows = _rows(context, "event_study_robustness")
    dynamic_lp = _rows(context, "dynamic_lp_feasibility")
    proxy_svar = _rows(context, "proxy_svar_feasibility")
    dynamic_blocker = _rows(context, "dynamic_causal_blocker")
    hac_rows = _rows(context, "event_study_hac")
    placebo_rows = _rows(context, "pretrend_placebo")
    promotion_contract = _rows(context, "promotion_contract")
    release_4_blocker = _rows(context, "release_4_blocker")
    controlled_lp_results = _rows(context, "controlled_dynamic_lp_results")
    controlled_lp_support = _rows(context, "controlled_dynamic_lp_support")
    release_5_decision = _rows(context, "release_5_decision")
    release_5_proxy_blocker = _rows(context, "release_5_proxy_blocker")
    proxy_svar_system_panel = _rows(context, "proxy_svar_system_panel")
    proxy_svar_relevance = _rows(context, "proxy_svar_relevance")
    proxy_svar_residual = _rows(context, "proxy_svar_residual")
    proxy_svar_timing = _rows(context, "proxy_svar_timing")
    release_6_decision = _rows(context, "release_6_decision")
    release_6_proxy_blocker = _rows(context, "release_6_proxy_blocker")
    release_7_lag_selection = _rows(context, "release_7_lag_selection")
    release_7_reduced_form_estimates = _rows(
        context, "release_7_reduced_form_estimates"
    )
    release_7_residual_covariance = _rows(context, "release_7_residual_covariance")
    release_7_proxy_support = _rows(context, "release_7_proxy_support")
    release_7_timing_audit = _rows(context, "release_7_timing_audit")
    release_7_promotion_contract = _rows(context, "release_7_promotion_contract")
    release_7_decision = _rows(context, "release_7_decision")
    release_7_proxy_blocker = _rows(context, "release_7_proxy_blocker")
    release_8_proxy_specification = _rows(context, "release_8_proxy_specification")
    release_8_structural_gap = _rows(context, "release_8_structural_gap")
    release_8_nonpromotion_proof = _rows(context, "release_8_nonpromotion_proof")
    release_8_decision = _rows(context, "release_8_decision")
    release_9_proxy_registry = _rows(context, "release_9_proxy_registry")
    release_9_proxy_support = _rows(context, "release_9_proxy_support")
    release_9_decision = _rows(context, "release_9_decision")
    release_9_nonpromotion_proof = _rows(context, "release_9_nonpromotion_proof")
    submission_decision = _rows(context, "submission_decision")
    statuses = Counter(row.get("result_status", "") for row in empirical)
    audit_statuses = Counter(row.get("audit_status", "") for row in causal_audit)
    outcomes = sorted({row.get("outcome_variable", "") for row in panel})
    lines = [
        "# Empirical Method Appendix",
        "",
        "## Identification",
        "",
        "The release uses SF Fed orthogonalized high-frequency monetary-policy "
        "surprises. Raw policy-rate changes are rejected as monetary shocks.",
        "",
        "## Outcome Panel",
        "",
        f"- Outcome-panel rows: {len(panel)}",
        f"- Outcomes: {', '.join(outcomes)}",
        "",
        "## Result Rows",
        "",
    ]
    for status, count in sorted(statuses.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(["", "## Release 2.0 Causal Gate", ""])
    for status, count in sorted(audit_statuses.items()):
        lines.append(f"- causal audit `{status}`: {count}")
    lines.append(f"- machine-readable blocker rows: {len(causal_blocker)}")
    lines.extend(["", "## Release 2.0 Submission Diagnostics", ""])
    lines.append(f"- support diagnostic rows: {len(support_rows)}")
    lines.append(f"- robustness rows: {len(robustness_rows)}")
    for row in submission_decision:
        lines.append(
            f"- `{row.get('decision_id', '')}`: `{row.get('decision_status', '')}`"
        )
    lines.extend(["", "## Release 3.0 Journal-Submission Gate", ""])
    lines.append(f"- dynamic LP feasibility rows: {len(dynamic_lp)}")
    lines.append(f"- proxy-SVAR feasibility rows: {len(proxy_svar)}")
    lines.append(f"- dynamic-causal final blocker rows: {len(dynamic_blocker)}")
    for row in dynamic_blocker:
        lines.append(
            f"- `{row.get('blocker_id', '')}`: `{row.get('blocker_status', '')}`"
        )
    lines.extend(["", "## Release 4.0 Final Submission Gate", ""])
    lines.append(f"- HAC-style diagnostic rows: {len(hac_rows)}")
    lines.append(f"- predetermined-level placebo rows: {len(placebo_rows)}")
    lines.append(f"- disabled promotion-contract rows: {len(promotion_contract)}")
    lines.append(f"- strengthened final blocker rows: {len(release_4_blocker)}")
    for row in release_4_blocker:
        lines.append(
            f"- `{row.get('blocker_id', '')}`: `{row.get('blocker_status', '')}`"
        )
    lines.extend(["", "## Release 5.0 Controlled Dynamic LP Gate", ""])
    lines.append(f"- controlled dynamic-LP result rows: {len(controlled_lp_results)}")
    lines.append(f"- controlled dynamic-LP support rows: {len(controlled_lp_support)}")
    lines.append(f"- identification-decision rows: {len(release_5_decision)}")
    lines.append(f"- proxy-SVAR blocker rows: {len(release_5_proxy_blocker)}")
    for row in release_5_decision:
        lines.append(
            f"- `{row.get('decision_id', '')}`: `{row.get('decision_status', '')}`"
        )
    lines.extend(["", "## Release 6.0 Proxy-SVAR/System Gate", ""])
    lines.append(f"- source-backed system-panel rows: {len(proxy_svar_system_panel)}")
    lines.append(f"- proxy relevance rows: {len(proxy_svar_relevance)}")
    lines.append(f"- residual diagnostic rows: {len(proxy_svar_residual)}")
    lines.append(f"- timing/support rows: {len(proxy_svar_timing)}")
    lines.append(f"- identification-decision rows: {len(release_6_decision)}")
    lines.append(f"- proxy-SVAR/system blocker rows: {len(release_6_proxy_blocker)}")
    for row in release_6_decision:
        lines.append(
            f"- `{row.get('decision_id', '')}`: `{row.get('decision_status', '')}`"
        )
    lines.extend(["", "## Release 7.0 System-Identification Gate", ""])
    lines.append(f"- lag-selection rows: {len(release_7_lag_selection)}")
    lines.append(
        f"- reduced-form estimate rows: {len(release_7_reduced_form_estimates)}"
    )
    lines.append(f"- residual covariance rows: {len(release_7_residual_covariance)}")
    lines.append(f"- proxy support rows: {len(release_7_proxy_support)}")
    lines.append(f"- timing/exogeneity audit rows: {len(release_7_timing_audit)}")
    lines.append(
        f"- disabled promotion-contract rows: {len(release_7_promotion_contract)}"
    )
    lines.append(f"- identification-decision rows: {len(release_7_decision)}")
    lines.append(f"- proxy-SVAR/system blocker rows: {len(release_7_proxy_blocker)}")
    for row in release_7_decision:
        lines.append(
            f"- `{row.get('decision_id', '')}`: `{row.get('decision_status', '')}`"
        )
    lines.extend(["", "## Release 8.0 System-Identification Non-Promotion Gate", ""])
    lines.append(
        f"- proxy-specification audit rows: {len(release_8_proxy_specification)}"
    )
    lines.append(f"- structural gap rows: {len(release_8_structural_gap)}")
    lines.append(f"- identification-decision rows: {len(release_8_decision)}")
    lines.append(f"- non-promotion proof rows: {len(release_8_nonpromotion_proof)}")
    for row in release_8_decision:
        lines.append(
            f"- `{row.get('decision_id', '')}`: `{row.get('decision_status', '')}`"
        )
    lines.extend(["", "## Release 9.0 External-Proxy Publication Boundary", ""])
    lines.append(f"- external-proxy registry rows: {len(release_9_proxy_registry)}")
    lines.append(f"- expanded proxy-support rows: {len(release_9_proxy_support)}")
    lines.append(f"- structural decision rows: {len(release_9_decision)}")
    lines.append(f"- final proof rows: {len(release_9_nonpromotion_proof)}")
    for row in release_9_decision:
        lines.append(
            f"- `{row.get('decision_id', '')}`: `{row.get('decision_status', '')}`"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Event-study rows are bounded estimates with limitations. They are "
            "now accompanied by a bounded controlled dynamic-LP appendix where "
            "support gates pass and reduced-form system diagnostics where source "
            "support allows, plus a Release 8.0 non-promotion proof. They do "
            "not authorize proxy-SVAR, pricing, welfare, or incidence claims. "
            "Release 9.0 adds a wider external-proxy frontier and preserves "
            "the same publication-boundary discipline.",
            "",
        ]
    )
    return "\n".join(lines)


def _limitations_appendix_text(
    context: dict[str, object], claim_rows: list[dict[str, str]]
) -> str:
    limitations = _rows(context, "limitations")
    readiness = _rows(context, "readiness")
    causal_blocker = _rows(context, "causal_blocker")
    submission_decision = _rows(context, "submission_decision")
    dynamic_lp = _rows(context, "dynamic_lp_feasibility")
    proxy_svar = _rows(context, "proxy_svar_feasibility")
    dynamic_blocker = _rows(context, "dynamic_causal_blocker")
    promotion_contract = _rows(context, "promotion_contract")
    release_4_blocker = _rows(context, "release_4_blocker")
    release_5_decision = _rows(context, "release_5_decision")
    release_5_proxy_blocker = _rows(context, "release_5_proxy_blocker")
    release_6_decision = _rows(context, "release_6_decision")
    release_6_proxy_blocker = _rows(context, "release_6_proxy_blocker")
    release_7_decision = _rows(context, "release_7_decision")
    release_7_proxy_blocker = _rows(context, "release_7_proxy_blocker")
    release_8_structural_gap = _rows(context, "release_8_structural_gap")
    release_8_nonpromotion_proof = _rows(context, "release_8_nonpromotion_proof")
    release_9_decision = _rows(context, "release_9_decision")
    release_9_nonpromotion_proof = _rows(context, "release_9_nonpromotion_proof")
    lines = [
        "# Limitations Appendix",
        "",
        "## Claim-Boundary Audit",
        "",
    ]
    for row in claim_rows:
        lines.append(f"- {row['boundary']}: {row['audit_status']}")
    lines.extend(["", "## Evidence-Limitation Rows", ""])
    for row in limitations:
        artifact = row.get("artifact", "")
        limitation = row.get("limitation", "") or row.get("needed_fields", "")
        lines.append(f"- {artifact}: {limitation}")
    lines.extend(["", "## Valuation Readiness", ""])
    for row in readiness:
        requirement = row.get("requirement", "") or row.get("component", "")
        status = row.get("status", "") or row.get("coverage_status", "")
        if requirement or status:
            lines.append(f"- {requirement}: {status}")
    lines.extend(["", "## Release 2.0 Causal Defensibility", ""])
    for row in causal_blocker:
        lines.append(f"- {row.get('blocker_id', '')}: {row.get('blocker_status', '')}")
        if row.get("required_resolution"):
            lines.append(f"  Required resolution: {row['required_resolution']}")
    lines.extend(["", "## Release 2.0 Submission Identification", ""])
    for row in submission_decision:
        if row.get("decision_status") in {"blocked", "fail"}:
            lines.append(
                f"- {row.get('decision_id', '')}: {row.get('required_value', '')}"
            )
    lines.extend(["", "## Release 3.0 Dynamic Causal Blocker", ""])
    for row in dynamic_lp + proxy_svar:
        if row.get("gate_status") in {"blocked", "fail"}:
            lines.append(f"- {row.get('gate_id', '')}: {row.get('required_value', '')}")
    for row in dynamic_blocker:
        lines.append(f"- {row.get('blocker_id', '')}: {row.get('blocker_status', '')}")
    lines.extend(["", "## Release 4.0 Final Submission Limit", ""])
    for row in promotion_contract:
        if row.get("requirement_status") != "pass":
            lines.append(
                f"- {row.get('requirement_id', '')}: {row.get('required_value', '')}"
            )
    for row in release_4_blocker:
        lines.append(f"- {row.get('blocker_id', '')}: {row.get('blocker_status', '')}")
    lines.extend(["", "## Release 5.0 Controlled Dynamic LP Limit", ""])
    for row in release_5_decision:
        if row.get("decision_status") in {"blocked", "fail"}:
            lines.append(
                f"- {row.get('decision_id', '')}: {row.get('required_value', '')}"
            )
    for row in release_5_proxy_blocker:
        lines.append(f"- {row.get('blocker_id', '')}: {row.get('blocker_status', '')}")
    lines.extend(["", "## Release 6.0 Proxy-SVAR/System Limit", ""])
    for row in release_6_decision:
        if row.get("decision_status") in {"blocked", "disabled_fail_closed"}:
            lines.append(
                f"- {row.get('decision_id', '')}: {row.get('required_value', '')}"
            )
    for row in release_6_proxy_blocker:
        lines.append(f"- {row.get('blocker_id', '')}: {row.get('blocker_status', '')}")
    lines.extend(["", "## Release 7.0 System-Identification Limit", ""])
    for row in release_7_decision:
        if (
            str(row.get("decision_status", "")).startswith("blocked")
            or row.get("decision_status") == "disabled_fail_closed"
        ):
            lines.append(
                f"- {row.get('decision_id', '')}: {row.get('required_value', '')}"
            )
    for row in release_7_proxy_blocker:
        lines.append(f"- {row.get('blocker_id', '')}: {row.get('blocker_status', '')}")
    lines.extend(["", "## Release 8.0 System-Identification Non-Promotion Limit", ""])
    for row in release_8_structural_gap:
        if (
            str(row.get("gap_status", "")).startswith("blocked")
            or row.get("gap_status") == "disabled_fail_closed"
        ):
            lines.append(f"- {row.get('gap_id', '')}: {row.get('required_value', '')}")
    for row in release_8_nonpromotion_proof:
        lines.append(f"- {row.get('proof_id', '')}: {row.get('proof_status', '')}")
    lines.extend(["", "## Release 9.0 External-Proxy Publication Boundary", ""])
    for row in release_9_decision:
        if str(row.get("decision_status", "")).startswith(
            "blocked"
        ) or "not_promoted" in str(row.get("decision_status", "")):
            lines.append(
                f"- {row.get('decision_id', '')}: {row.get('required_value', '')}"
            )
    for row in release_9_nonpromotion_proof:
        lines.append(f"- {row.get('proof_id', '')}: {row.get('proof_status', '')}")
    lines.append("")
    return "\n".join(lines)


def _validation_package_text(
    context: dict[str, object], claim_rows: list[dict[str, str]]
) -> str:
    failed = [row for row in claim_rows if row["audit_status"] != "pass"]
    causal_blocker = _rows(context, "causal_blocker")
    support_rows = _rows(context, "support_diagnostics")
    robustness_rows = _rows(context, "event_study_robustness")
    dynamic_lp = _rows(context, "dynamic_lp_feasibility")
    proxy_svar = _rows(context, "proxy_svar_feasibility")
    dynamic_blocker = _rows(context, "dynamic_causal_blocker")
    hac_rows = _rows(context, "event_study_hac")
    placebo_rows = _rows(context, "pretrend_placebo")
    promotion_contract = _rows(context, "promotion_contract")
    release_4_blocker = _rows(context, "release_4_blocker")
    controlled_lp_results = _rows(context, "controlled_dynamic_lp_results")
    release_5_decision = _rows(context, "release_5_decision")
    release_5_proxy_blocker = _rows(context, "release_5_proxy_blocker")
    proxy_svar_system_panel = _rows(context, "proxy_svar_system_panel")
    release_6_decision = _rows(context, "release_6_decision")
    release_6_proxy_blocker = _rows(context, "release_6_proxy_blocker")
    release_7_reduced_form_estimates = _rows(
        context, "release_7_reduced_form_estimates"
    )
    release_7_proxy_support = _rows(context, "release_7_proxy_support")
    release_7_decision = _rows(context, "release_7_decision")
    release_7_proxy_blocker = _rows(context, "release_7_proxy_blocker")
    release_8_proxy_specification = _rows(context, "release_8_proxy_specification")
    release_8_structural_gap = _rows(context, "release_8_structural_gap")
    release_8_nonpromotion_proof = _rows(context, "release_8_nonpromotion_proof")
    release_8_decision = _rows(context, "release_8_decision")
    return "\n".join(
        [
            "# RateWall Validation Package",
            "",
            "## Required Commands",
            "",
            "- `uv run ruff check .` with repo-safe cache variables.",
            "- `uv run python -B -m pytest` with repo-safe cache variables.",
            "- `ratewall data snapshot --mode live --output data/raw/ratewall_snapshot.json`.",
            "- `ratewall databook build --snapshot data/raw/ratewall_snapshot.json --output-dir outputs`.",
            "- `ratewall scenarios build --snapshot data/raw/ratewall_snapshot.json --output outputs/tables/ratewall_scenarios.csv`.",
            "- `ratewall empirical results --snapshot data/raw/ratewall_snapshot.json ...`.",
            "- `ratewall release build --snapshot data/raw/ratewall_snapshot.json --output-dir outputs` packages the existing output surface; add `--rebuild-databook full` only for an intentional full-surface rebuild.",
            "",
            "## Generated Gate Status",
            "",
            f"- Claim-audit failures: {len(failed)}",
            f"- Source rows: {len(context['sources'])}",
            f"- Empirical result rows: {len(_rows(context, 'empirical_results'))}",
            f"- Outcome-panel rows: {len(_rows(context, 'outcome_panel'))}",
            f"- Release 2.0 causal blocker rows: {len(causal_blocker)}",
            f"- Release 2.0 support diagnostic rows: {len(support_rows)}",
            f"- Release 2.0 robustness rows: {len(robustness_rows)}",
            f"- Release 3.0 dynamic LP feasibility rows: {len(dynamic_lp)}",
            f"- Release 3.0 proxy-SVAR feasibility rows: {len(proxy_svar)}",
            f"- Release 3.0 dynamic-causal blocker rows: {len(dynamic_blocker)}",
            f"- Release 4.0 HAC-style diagnostic rows: {len(hac_rows)}",
            f"- Release 4.0 placebo diagnostic rows: {len(placebo_rows)}",
            f"- Release 4.0 disabled promotion-contract rows: {len(promotion_contract)}",
            f"- Release 4.0 strengthened final blocker rows: {len(release_4_blocker)}",
            f"- Release 5.0 controlled dynamic-LP result rows: {len(controlled_lp_results)}",
            f"- Release 5.0 identification-decision rows: {len(release_5_decision)}",
            f"- Release 5.0 proxy-SVAR blocker rows: {len(release_5_proxy_blocker)}",
            f"- Release 6.0 system-panel rows: {len(proxy_svar_system_panel)}",
            f"- Release 6.0 identification-decision rows: {len(release_6_decision)}",
            f"- Release 6.0 proxy-SVAR/system blocker rows: {len(release_6_proxy_blocker)}",
            f"- Release 7.0 reduced-form estimate rows: {len(release_7_reduced_form_estimates)}",
            f"- Release 7.0 proxy support rows: {len(release_7_proxy_support)}",
            f"- Release 7.0 identification-decision rows: {len(release_7_decision)}",
            f"- Release 7.0 proxy-SVAR/system blocker rows: {len(release_7_proxy_blocker)}",
            f"- Release 8.0 proxy-specification audit rows: {len(release_8_proxy_specification)}",
            f"- Release 8.0 structural gap rows: {len(release_8_structural_gap)}",
            f"- Release 8.0 identification-decision rows: {len(release_8_decision)}",
            f"- Release 8.0 non-promotion proof rows: {len(release_8_nonpromotion_proof)}",
            f"- Release 9.0 external-proxy registry rows: {len(_rows(context, 'release_9_proxy_registry'))}",
            f"- Release 9.0 proxy-support audit rows: {len(_rows(context, 'release_9_proxy_support'))}",
            f"- Release 9.0 structural decision rows: {len(_rows(context, 'release_9_decision'))}",
            f"- Release 9.0 final proof rows: {len(_rows(context, 'release_9_nonpromotion_proof'))}",
            "",
            "This file is a generated release checklist. The current turn's "
            "terminal validation results should be reported alongside it.",
            "",
        ]
    )


def _public_readme_text(
    context: dict[str, object], claim_rows: list[dict[str, str]]
) -> str:
    source_counts = Counter(row.get("snapshot_kind", "") for row in context["sources"])
    empirical_statuses = Counter(
        row.get("result_status", "") for row in _rows(context, "empirical_results")
    )
    causal_blocker_count = len(_rows(context, "causal_blocker"))
    support_count = len(_rows(context, "support_diagnostics"))
    robustness_count = len(_rows(context, "event_study_robustness"))
    dynamic_blocker_count = len(_rows(context, "dynamic_causal_blocker"))
    release_4_blocker_count = len(_rows(context, "release_4_blocker"))
    controlled_lp_count = len(_rows(context, "controlled_dynamic_lp_results"))
    release_5_proxy_blocker_count = len(_rows(context, "release_5_proxy_blocker"))
    system_panel_count = len(_rows(context, "proxy_svar_system_panel"))
    release_6_proxy_blocker_count = len(_rows(context, "release_6_proxy_blocker"))
    release_7_estimate_count = len(_rows(context, "release_7_reduced_form_estimates"))
    release_7_proxy_blocker_count = len(_rows(context, "release_7_proxy_blocker"))
    release_8_proxy_spec_count = len(_rows(context, "release_8_proxy_specification"))
    release_8_proof_count = len(_rows(context, "release_8_nonpromotion_proof"))
    release_9_registry_count = len(_rows(context, "release_9_proxy_registry"))
    release_9_support_count = len(_rows(context, "release_9_proxy_support"))
    release_9_proof_count = len(_rows(context, "release_9_nonpromotion_proof"))
    tdc_ledger_count = len(_rows(context, "tdc_ledger"))
    tdc_impulse_count = len(_rows(context, "tdc_impulse"))
    tdc_historical_count = len(_rows(context, "tdc_historical_panel"))
    deposit_pricing_count = len(_rows(context, "deposit_pricing_pass_through"))
    tdc_reconciliation_count = len(_rows(context, "tdc_historical_reconciliation"))
    threshold_count = len(_rows(context, "threshold_simulation"))
    financialization_count = len(_rows(context, "financialization_pressure"))
    calibration_count = len(_rows(context, "threshold_calibration_ranges"))
    calibrated_threshold_count = len(_rows(context, "threshold_calibrated_simulation"))
    bridge_count = len(_rows(context, "du_ru_tga_calibration_bridge"))
    assumption_set_count = len(_rows(context, "assumption_sets"))
    wall_hit_count = sum(
        1
        for row in _rows(context, "wall_hit_scenarios")
        if row.get("wall_hit_under_assumptions") == "true"
    )
    wall_nonhit_count = sum(
        1
        for row in _rows(context, "wall_hit_scenarios")
        if row.get("wall_hit_under_assumptions") == "false"
    )
    dynamic_path_count = len(_rows(context, "dynamic_scenario_paths"))
    dynamic_consistency_count = len(
        _rows(context, "dynamic_scenario_path_consistency_diagnostic")
    )
    dynamic_solve_count = len(_rows(context, "dynamic_offset_ratio_path"))
    dynamic_family_count = len(_rows(context, "dynamic_scenario_family_registry"))
    dynamic_envelope_count = len(_rows(context, "dynamic_uncertainty_envelope"))
    dynamic_robustness_count = len(_rows(context, "dynamic_crossing_robustness"))
    dynamic_crossing_count = sum(
        1
        for row in _rows(context, "scenario_crossing_diagnostic")
        if row.get("crossing_status") == "scenario_implied_crossing_under_assumptions"
    )
    financialization_evidence_count = len(
        _rows(context, "financialization_evidence_appendix")
    )
    benchmark_count = len(_rows(context, "contractionary_benchmark_calibration"))
    uncertainty_count = len(_rows(context, "threshold_uncertainty_bands"))
    validation_count = len(_rows(context, "historical_threshold_validation"))
    boundary_count = len(_rows(context, "policy_boundary_synthesis"))
    blocker_resolution_count = len(_rows(context, "blocker_resolution_ledger"))
    publication_claim_count = len(_rows(context, "publication_claim_decision"))
    final_blocker_count = len(_rows(context, "final_blocker_ledger"))
    release_16_source_resolution_count = len(
        _rows(context, "release_16_source_resolution")
    )
    release_16_no_further_promotion_count = len(
        _rows(context, "release_16_no_further_promotion")
    )
    release_17_external_review_count = len(_rows(context, "release_17_external_review"))
    release_17_publication_polish_count = len(
        _rows(context, "release_17_publication_polish")
    )
    release_17_blocker_reopen_count = len(_rows(context, "release_17_blocker_reopen"))
    release_18_live_refresh_count = len(_rows(context, "release_18_live_refresh"))
    safe_asset_count = len(_rows(context, "safe_asset_retention_context"))
    buyer_case_count = len(_rows(context, "buyer_case_sign_matrix"))
    mpc_count = len(_rows(context, "recipient_mpc_scenarios"))
    release_19_invariant_count = len(_rows(context, "release_19_invariants"))
    release_19_methodology_count = len(_rows(context, "release_19_methodology"))
    release_20_activity_count = len(_rows(context, "release_20_activity_benchmark"))
    release_20_lp_count = len(_rows(context, "release_20_lp_diagnostics"))
    release_20_decision_count = len(_rows(context, "release_20_decision"))
    release_21_live_count = len(_rows(context, "release_21_live_refresh"))
    release_21_benchmark_count = len(_rows(context, "release_21_benchmark_gate"))
    release_21_invariant_count = len(_rows(context, "release_21_backend_invariants"))
    release_22_audit_count = len(_rows(context, "release_22_source_repro_audit"))
    release_22_gate_count = len(_rows(context, "release_22_source_gate"))
    claim_pass = all(row["audit_status"] == "pass" for row in claim_rows)
    return "\n".join(
        [
            "# RateWall",
            "",
            "RateWall is a reproducible research package for debt-conditioned "
            "monetary transmission and state-dependent monetary policy "
            "effectiveness. It studies whether high public debt, large "
            "interest-sensitive liquid claims, firm cash buffers, Fed-Treasury "
            "remittance timing, safe-asset allocation incentives, and embedded "
            "zero-interest credit structures can make rate hikes partly "
            "self-offsetting under some balance-sheet regimes. The backend "
            "builds source-labeled accounting, scenario, data-book, "
            "empirical-status, and release artifacts for that broader RateWall "
            "theory without promoting causal or incidence claims.",
            "",
            "## Boundaries",
            "",
            "- The package does not claim that higher rates always raise inflation.",
            "- The package does not claim that the Federal Reserve has stopped working.",
            "- Raw policy-rate changes are rejected as monetary shocks.",
            "- Pricing, holder allocation, tax, MPC, welfare, reset-calendar construction, and incidence outputs remain disabled.",
            "",
            "## Current Release State",
            "",
            f"- Source snapshot kinds: `{dict(source_counts)}`",
            f"- Empirical result statuses: `{dict(empirical_statuses)}`",
            f"- Release 2.0 causal defensibility blocker rows: `{causal_blocker_count}`",
            f"- Release 2.0 support/robustness rows: `{support_count}` / `{robustness_count}`",
            f"- Release 3.0 dynamic-causal final blocker rows: `{dynamic_blocker_count}`",
            f"- Release 4.0 strengthened final blocker rows: `{release_4_blocker_count}`",
            f"- Release 5.0 controlled dynamic-LP rows: `{controlled_lp_count}`",
            f"- Release 5.0 proxy-SVAR blocker rows: `{release_5_proxy_blocker_count}`",
            f"- Release 6.0 system-panel rows: `{system_panel_count}`",
            f"- Release 6.0 proxy-SVAR/system blocker rows: `{release_6_proxy_blocker_count}`",
            f"- Release 7.0 reduced-form estimate rows: `{release_7_estimate_count}`",
            f"- Release 7.0 proxy-SVAR/system blocker rows: `{release_7_proxy_blocker_count}`",
            f"- Release 8.0 proxy-specification audit rows: `{release_8_proxy_spec_count}`",
            f"- Release 8.0 non-promotion proof rows: `{release_8_proof_count}`",
            f"- Release 9.0 external-proxy registry rows: `{release_9_registry_count}`",
            f"- Release 9.0 proxy-support audit rows: `{release_9_support_count}`",
            f"- Release 9.0 final publication-boundary proof rows: `{release_9_proof_count}`",
            f"- Release 10.0 TDC ledger/scenario rows: `{tdc_ledger_count}` / `{tdc_impulse_count}`",
            f"- Release 11.0 historical TDC/pricing/reconciliation rows: `{tdc_historical_count}` / `{deposit_pricing_count}` / `{tdc_reconciliation_count}`",
            f"- Release 12.0 threshold/financialization rows: `{threshold_count}` / `{financialization_count}`",
            f"- Release 13.0 calibration/calibrated-threshold/bridge/evidence rows: `{calibration_count}` / `{calibrated_threshold_count}` / `{bridge_count}` / `{financialization_evidence_count}`",
            f"- Assumption Mode sets/hit/non-hit rows: `{assumption_set_count}` / `{wall_hit_count}` / `{wall_nonhit_count}`",
            "- Dynamic Assumption Mode path/consistency/solve/family/envelope/"
            "robustness/scenario-implied crossing rows: "
            f"`{dynamic_path_count}` / `{dynamic_consistency_count}` / "
            f"`{dynamic_solve_count}` / `{dynamic_family_count}` / "
            f"`{dynamic_envelope_count}` / `{dynamic_robustness_count}` / "
            f"`{dynamic_crossing_count}`",
            f"- Release 14.0 benchmark/uncertainty/validation/boundary rows: `{benchmark_count}` / `{uncertainty_count}` / `{validation_count}` / `{boundary_count}`",
            f"- Release 15.0 blocker/claim/final-decision rows: `{blocker_resolution_count}` / `{publication_claim_count}` / `{final_blocker_count}`",
            f"- Release 16.0 source-resolution/no-further-promotion rows: `{release_16_source_resolution_count}` / `{release_16_no_further_promotion_count}`",
            f"- Release 17.0 review/polish/reopen rows: `{release_17_external_review_count}` / `{release_17_publication_polish_count}` / `{release_17_blocker_reopen_count}`",
            f"- Release 18.0 live-refresh rows: `{release_18_live_refresh_count}`",
            f"- Release 19.0 safe-asset/buyer/MPC/invariant/methodology rows: `{safe_asset_count}` / `{buyer_case_count}` / `{mpc_count}` / `{release_19_invariant_count}` / `{release_19_methodology_count}`",
            f"- Release 20.0 activity-benchmark/LP-diagnostic/decision rows: `{release_20_activity_count}` / `{release_20_lp_count}` / `{release_20_decision_count}`",
            f"- Release 21.0 live-refresh/final-benchmark/invariant rows: `{release_21_live_count}` / `{release_21_benchmark_count}` / `{release_21_invariant_count}`",
            f"- Release 22.0 source-repro audit/source-gate rows: `{release_22_audit_count}` / `{release_22_gate_count}`",
            "- Release 23.0 semantic/archive hardening rows: "
            "`source-status / latest-as-of / threshold / calibration / recipient-base / archive`",
            f"- Claim-boundary audit: `{'pass' if claim_pass else 'fail'}`",
            "",
            "## Live Denominator Policy",
            "",
            "- Default runtime annual-flow denominator family: the "
            "literature-backed h4 endpoint proxy at `0.776217543454 pp GDP per "
            "100 bp-year` with interval `[0.350000000000, 1.300000000000]`.",
            "- Legacy `0.6/0.7 pp GDP` anchors remain sensitivity-only "
            "Assumption Mode counterpoints, not the default runtime policy.",
            "- Bounded h8 remains review-only/non-runtime cumulative evidence.",
            "- FRB/US remains benchmark-only context for scale and sign checks.",
            "- Runtime annual-flow support offsets should be consumed from "
            "`outputs/tables/ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv` "
            "or `outputs/tables/ratewall_runtime_annual_flow_support_offset_frontier_summary.csv`, "
            "which trace back to "
            "`outputs/tables/ratewall_runtime_annual_flow_support_offset_scenarios.csv` "
            "and must trace back to "
            "`outputs/tables/ratewall_annual_support_numerator_contract.csv`, "
            "`outputs/tables/ratewall_annual_support_numerator_contract_invariant_audit.csv`, "
            "`outputs/tables/ratewall_runtime_annual_flow_support_offset_readiness_registry.csv`, "
            "`outputs/tables/ratewall_annual_support_numerator_source_gate.csv`, and "
            "`outputs/tables/ratewall_annual_support_numerator_uncertainty_envelope.csv`. "
            "The compact-layer closeout and narrow reopen triggers now live in "
            "`outputs/tables/ratewall_runtime_annual_flow_support_offset_closeout_decision.csv`. "
            "Compact benchmark context and reviewer-facing limitations now live in "
            "`outputs/tables/ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv`, "
            "`outputs/reports/ratewall_runtime_annual_flow_support_offset_reviewer_packet.md`, "
            "and `outputs/reports/ratewall_runtime_annual_flow_support_offset_limitations.md`.",
            "",
            "## Main Generated Artifacts",
            "",
            "- `outputs/tables/ratewall_100bps_impulse.csv`",
            "- `outputs/tables/ratewall_databook_metrics.csv`",
            "- `outputs/tables/ratewall_scenarios.csv`",
            "- `outputs/tables/ratewall_empirical_results.csv`",
            "- `outputs/tables/ratewall_causal_identification_audit.csv`",
            "- `outputs/tables/ratewall_causal_defensibility_blocker.csv`",
            "- `outputs/tables/ratewall_empirical_robustness_manifest.json`",
            "- `outputs/tables/ratewall_event_study_support_diagnostics.csv`",
            "- `outputs/tables/ratewall_event_study_robustness.csv`",
            "- `outputs/tables/ratewall_submission_identification_decision.csv`",
            "- `outputs/tables/ratewall_dynamic_lp_feasibility_diagnostics.csv`",
            "- `outputs/tables/ratewall_proxy_svar_feasibility_diagnostics.csv`",
            "- `outputs/tables/ratewall_dynamic_causal_final_blocker.csv`",
            "- `outputs/tables/ratewall_journal_submission_manifest.json`",
            "- `outputs/tables/ratewall_event_study_hac_diagnostics.csv`",
            "- `outputs/tables/ratewall_pretrend_placebo_diagnostics.csv`",
            "- `outputs/tables/ratewall_dynamic_identification_promotion_contract_disabled.csv`",
            "- `outputs/tables/ratewall_release_4_0_dynamic_causal_final_blocker.csv`",
            "- `outputs/tables/ratewall_release_4_0_submission_manifest.json`",
            "- `outputs/tables/ratewall_controlled_dynamic_lp_results.csv`",
            "- `outputs/tables/ratewall_controlled_dynamic_lp_support_diagnostics.csv`",
            "- `outputs/tables/ratewall_release_5_0_identification_decision.csv`",
            "- `outputs/tables/ratewall_release_5_0_proxy_svar_final_blocker.csv`",
            "- `outputs/tables/ratewall_release_5_0_dynamic_causal_manifest.json`",
            "- `outputs/tables/ratewall_proxy_svar_system_panel.csv`",
            "- `outputs/tables/ratewall_proxy_svar_proxy_relevance_diagnostics.csv`",
            "- `outputs/tables/ratewall_proxy_svar_residual_diagnostics.csv`",
            "- `outputs/tables/ratewall_proxy_svar_timing_support_diagnostics.csv`",
            "- `outputs/tables/ratewall_release_6_0_identification_decision.csv`",
            "- `outputs/tables/ratewall_release_6_0_proxy_svar_final_blocker.csv`",
            "- `outputs/tables/ratewall_release_6_0_valuation_incidence_frontier_disabled.csv`",
            "- `outputs/tables/ratewall_release_6_0_system_identification_manifest.json`",
            "- `outputs/tables/ratewall_release_7_0_var_lag_selection.csv`",
            "- `outputs/tables/ratewall_release_7_0_reduced_form_system_estimates.csv`",
            "- `outputs/tables/ratewall_release_7_0_residual_covariance.csv`",
            "- `outputs/tables/ratewall_release_7_0_proxy_relevance_support.csv`",
            "- `outputs/tables/ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv`",
            "- `outputs/tables/ratewall_release_7_0_claim_promotion_contract_disabled.csv`",
            "- `outputs/tables/ratewall_release_7_0_identification_decision.csv`",
            "- `outputs/tables/ratewall_release_7_0_proxy_svar_final_blocker.csv`",
            "- `outputs/tables/ratewall_release_7_0_system_identification_manifest.json`",
            "- `outputs/tables/ratewall_release_8_0_proxy_specification_audit.csv`",
            "- `outputs/tables/ratewall_release_8_0_structural_gap_ledger.csv`",
            "- `outputs/tables/ratewall_release_8_0_nonpromotion_proof.csv`",
            "- `outputs/tables/ratewall_release_8_0_identification_decision.csv`",
            "- `outputs/tables/ratewall_release_8_0_system_identification_manifest.json`",
            "- `outputs/tables/ratewall_release_9_0_external_proxy_source_registry.csv`",
            "- `outputs/tables/ratewall_release_9_0_external_proxy_support_audit.csv`",
            "- `outputs/tables/ratewall_release_9_0_structural_identification_decision.csv`",
            "- `outputs/tables/ratewall_release_9_0_final_nonpromotion_proof.csv`",
            "- `outputs/tables/ratewall_release_9_0_structural_identification_manifest.json`",
            "- `outputs/tables/ratewall_tdc_deposit_channel_ledger.csv`",
            "- `outputs/tables/ratewall_tdc_ru_financing_deposit_impulse.csv`",
            "- `outputs/tables/ratewall_tdc_historical_panel.csv`",
            "- `outputs/tables/ratewall_deposit_pricing_pass_through_context.csv`",
            "- `outputs/tables/ratewall_tdc_historical_reconciliation.csv`",
            "- `outputs/tables/ratewall_tdcest_historical_estimator_bridge.csv`",
            "- `outputs/tables/ratewall_tdcest_monetary_route_bridge.csv`",
            "- `outputs/tables/ratewall_tdcest_mmf_route_split_context.csv`",
            "- `outputs/tables/ratewall_tdcest_z1_domestic_nonbank_sector_context.csv`",
            "- `outputs/tables/ratewall_tdc_rolling_pass_through_context.csv`",
            "- `outputs/tables/ratewall_historical_tdc_wall_ratio_path.csv`",
            "- `outputs/tables/ratewall_historical_assumption_mode_tdc_wall_ratio_path.csv`",
            "- `outputs/tables/ratewall_tdc_other_component_bridge.csv`",
            "- `outputs/tables/ratewall_tdc_deposit_credit_decomposition.csv`",
            "- `outputs/tables/ratewall_tdc_double_count_guardrail.csv`",
            "- `outputs/tables/ratewall_tdc_net_ratewall_effect.csv`",
            "- `outputs/tables/ratewall_tdc_materialization_semantic_summary.csv`",
            "- `outputs/tables/ratewall_tdc_historical_source_contract.csv`",
            "- `outputs/tables/ratewall_tdc_historical_selected_series.csv`",
            "- `outputs/tables/ratewall_canonical_tdc_accounting_path.csv`",
            "- `outputs/tables/ratewall_canonical_tdc_stitched_accounting_path.csv`",
            "- `outputs/tables/ratewall_canonical_tdc_accounting_source_hierarchy_audit.csv`",
            "- `outputs/tables/ratewall_tdcsim_projection_contract_bridge.csv`",
            "- `outputs/tables/ratewall_tdcsim_domestic_nonbank_funding_classification.csv`",
            "- `outputs/tables/ratewall_tdcsim_private_route_sensitivity_ingest.csv`",
            "- `outputs/tables/ratewall_tdcsim_assumption_mode_support_ingest.csv`",
            "- `outputs/tables/ratewall_tdcsim_assumption_mode_claim_gate.csv`",
            "- `outputs/tables/ratewall_tdcsim_assumption_mode_forecast_private_route_envelope.csv`",
            "- `outputs/tables/ratewall_tdcsim_assumption_mode_forecast_private_route_claim_gate.csv`",
            "- `outputs/tables/ratewall_qrawatch_tdcsim_scenario_registry.csv`",
            "- `outputs/tables/ratewall_qrawatch_tdcsim_provenance_audit.csv`",
            "- `outputs/tables/ratewall_qrawatch_tdcsim_bridge_invariant_audit.csv`",
            "- `outputs/tables/ratewall_tdc_forward_projection_surface.csv`",
            "- `outputs/tables/ratewall_tdc_forward_component_audit.csv`",
            "- `outputs/tables/ratewall_tdc_forward_overlap_guardrail.csv`",
            "- `outputs/tables/ratewall_tdc_forward_invariant_audit.csv`",
            "- `outputs/tables/ratewall_tdc_forward_assumption_registry.csv`",
            "- `outputs/tables/ratewall_tdc_forward_scenario_decomposition.csv`",
            "- `outputs/tables/ratewall_forecast_holder_tdc_consistency_bridge.csv`",
            "- `outputs/tables/ratewall_threshold_simulation.csv`",
            "- `outputs/tables/ratewall_threshold_calibration_ranges.csv`",
            "- `outputs/tables/ratewall_threshold_calibrated_simulation.csv`",
            "- `outputs/tables/ratewall_du_ru_tga_calibration_bridge.csv`",
            "- `outputs/tables/ratewall_assumption_sets.csv`",
            "- `outputs/tables/ratewall_condition_frontier.csv`",
            "- `outputs/tables/ratewall_offset_decomposition.csv`",
            "- `outputs/tables/ratewall_public_impulse_factorization.csv`",
            "- `outputs/tables/ratewall_public_liability_repricing_ladder.csv`",
            "- `outputs/tables/ratewall_public_liability_repricing_evidence_bridge.csv`",
            "- `outputs/tables/ratewall_public_liability_repricing_reconciliation_gap.csv`",
            "- `outputs/tables/ratewall_mspd_table3_bucket_repricing_gate.csv`",
            "- `outputs/tables/ratewall_treasury_bucket_repricing_prior_bridge.csv`",
            "- `outputs/tables/ratewall_interest_recipient_leakage_bridge.csv`",
            "- `outputs/tables/ratewall_interest_recipient_leakage_evidence_gap.csv`",
            "- `outputs/tables/ratewall_treasury_recipient_leakage_source_gate.csv`",
            "- `outputs/tables/ratewall_public_finance_timing_path.csv`",
            "- `outputs/tables/ratewall_public_finance_timing_evidence_gap.csv`",
            "- `outputs/tables/ratewall_public_finance_timing_design_test_scaffold.csv`",
            "- `outputs/tables/ratewall_safe_yield_offset_drag_pairing_gap.csv`",
            "- `outputs/tables/ratewall_bnpl_zero_interest_float_evidence_gap.csv`",
            "- `outputs/tables/ratewall_financialized_balance_sheet_evidence_gap.csv`",
            "- `outputs/tables/ratewall_firm_cash_debt_maturity_evidence_gap.csv`",
            "- `outputs/tables/ratewall_conventional_drag_channel_evidence_gap.csv`",
            "- `outputs/tables/ratewall_conventional_drag_source_design_gate.csv`",
            "- `outputs/tables/ratewall_denominator_response_design_scaffold.csv`",
            "- `outputs/tables/ratewall_denominator_response_design_test_scaffold.csv`",
            "- `outputs/tables/ratewall_denominator_response_gate_attempt.csv`",
            "- `outputs/tables/ratewall_denominator_aligned_response_panel_scaffold.csv`",
            "- `outputs/tables/ratewall_denominator_event_outcome_cell_diagnostic.csv`",
            "- `outputs/tables/ratewall_denominator_event_outcome_panel_value_diagnostic.csv`",
            "- `outputs/tables/ratewall_denominator_event_level_response_panel.csv`",
            "- `outputs/tables/ratewall_denominator_uncertainty_pass_fail_review.csv`",
            "- `outputs/tables/ratewall_denominator_panel_design_test_diagnostic.csv`",
            "- `outputs/tables/ratewall_denominator_pretrend_placebo_diagnostic.csv`",
            "- `outputs/tables/ratewall_denominator_shock_relevance_diagnostic.csv`",
            "- `outputs/tables/ratewall_denominator_sign_consistency_diagnostic.csv`",
            "- `outputs/tables/ratewall_denominator_horizon_sensitivity_diagnostic.csv`",
            "- `outputs/tables/ratewall_denominator_outlier_window_robustness_diagnostic.csv`",
            "- `outputs/tables/ratewall_denominator_design_readiness_decision.csv`",
            "- `outputs/tables/ratewall_denominator_formal_design_test_result_scaffold.csv`",
            "- `outputs/tables/ratewall_denominator_formal_design_test_result.csv`",
            "- `outputs/tables/ratewall_denominator_response_estimate_diagnostic.csv`",
            "- `outputs/tables/ratewall_denominator_cross_source_design_validation.csv`",
            "- `outputs/tables/ratewall_denominator_evidence_upgrade_source_design_requirement.csv`",
            "- `outputs/tables/ratewall_denominator_evidence_upgrade_priority_queue.csv`",
            "- `outputs/tables/ratewall_denominator_evidence_upgrade_tier1_workplan.csv`",
            "- `outputs/tables/ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv`",
            "- `outputs/tables/ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv`",
            "- `outputs/tables/ratewall_conventional_drag_evidence_tranche.csv`",
            "- `outputs/tables/ratewall_baml_source_history_repair_contract.csv`",
            "- `outputs/tables/ratewall_borrowing_cost_source_object_adjudication.csv`",
            "- `outputs/tables/ratewall_baml_effective_yield_source_access_gate.csv`",
            "- `outputs/tables/ratewall_hqm_source_proxy_lane_review.csv`",
            "- `outputs/tables/ratewall_hqm_event_window_feasibility.csv`",
            "- `outputs/tables/ratewall_hqm_event_outcome_panel_values.csv`",
            "- `outputs/tables/ratewall_hqm_formal_diagnostic_gate.csv`",
            "- `outputs/tables/ratewall_hqm_promotion_protocol_gate.csv`",
            "- `outputs/tables/ratewall_hqm_policy_path_exposure_admission.csv`",
            "- `outputs/tables/ratewall_hqm_policy_path_protocol_dependency_gate.csv`",
            "- `outputs/tables/ratewall_hqm_denominator_mapping_gate.csv`",
            "- `outputs/tables/ratewall_hqm_borrowing_cost_object_comparator.csv`",
            "- `outputs/tables/ratewall_baa_event_window_support_diagnostic.csv`",
            "- `outputs/tables/ratewall_baa_hqm_mapping_diagnostic.csv`",
            "- `outputs/tables/ratewall_baa_response_diagnostic.csv`",
            "- `outputs/tables/ratewall_baa_policy_path_normalization_gate.csv`",
            "- `outputs/tables/ratewall_baa_rights_proxy_uncertainty_review.csv`",
            "- `outputs/tables/ratewall_baa_current_demand_bridge_source_audit.csv`",
            "- `outputs/tables/ratewall_hqm_current_demand_bridge_gate.csv`",
            "- `outputs/tables/ratewall_conventional_drag_demand_conversion_admission.csv`",
            "- `outputs/tables/ratewall_conventional_drag_calibration_route.csv`",
            "- `outputs/tables/ratewall_conventional_drag_research_parameterization_source_contract.csv`",
            "- `outputs/tables/ratewall_tdsp_current_demand_source_review.csv`",
            "- `outputs/tables/ratewall_tdsp_current_demand_unit_conversion.csv`",
            "- `outputs/tables/ratewall_tdsp_current_demand_diagnostic_mapping.csv`",
            "- `outputs/tables/ratewall_tdsp_policy_path_normalization_blocker.csv`",
            "- `outputs/tables/ratewall_tdsp_current_demand_admission_audit.csv`",
            "- `outputs/tables/ratewall_pce_dpi_source_refresh_contract.csv`",
            "- `outputs/tables/ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv`",
            "- `outputs/tables/ratewall_policy_path_exposure_vector_design_gate.csv`",
            "- `outputs/tables/ratewall_policy_path_reviewed_protocol_source_context.csv`",
            "- `outputs/tables/ratewall_policy_path_bps_year_source_protocol.csv`",
            "- `outputs/tables/ratewall_tdsp_pce_dpi_policy_path_admission_audit.csv`",
            "- `outputs/tables/ratewall_tdsp_diagnostic_family_completion_gate.csv`",
            "- `outputs/tables/ratewall_interest_channel_horizon_timing_matrix.csv`",
            "- `outputs/tables/ratewall_interest_channel_promotion_gate.csv`",
            "- `outputs/tables/ratewall_interest_channel_evidence_upgrade_queue.csv`",
            "- `outputs/tables/ratewall_high_priority_interest_channel_source_bridge.csv`",
            "- `outputs/tables/ratewall_source_gate_prior_narrowing_decision.csv`",
            "- `outputs/tables/ratewall_source_gate_exhaustion_closure.csv`",
            "- `outputs/tables/ratewall_restricted_data_gate_spec.csv`",
            "- `outputs/tables/ratewall_assumption_mode_post_closure_boundary_map.csv`",
            "- `outputs/tables/ratewall_sibling_evidence_bridge.csv`",
            "- `outputs/tables/ratewall_sibling_evidence_upgrade_queue.csv`",
            "- `outputs/tables/ratewall_higher_rate_channel_registry.csv`",
            "- `outputs/tables/ratewall_corporate_net_interest_cashflow_bridge.csv`",
            "- `outputs/tables/ratewall_working_capital_cost_channel_diagnostic.csv`",
            "- `outputs/tables/ratewall_term_structure_pricing_carry_diagnostic.csv`",
            "- `outputs/tables/ratewall_interest_channel_module_registry.csv`",
            "- `outputs/tables/ratewall_interest_channel_completion_matrix.csv`",
            "- `outputs/tables/ratewall_dynamic_scenario_paths.csv`",
            "- `outputs/tables/ratewall_dynamic_scenario_path_consistency_diagnostic.csv`",
            "- `outputs/tables/ratewall_dynamic_offset_ratio_path.csv`",
            "- `outputs/tables/ratewall_scenario_crossing_diagnostic.csv`",
            "- `outputs/tables/ratewall_dynamic_sensitivity_frontier.csv`",
            "- `outputs/tables/ratewall_dynamic_scenario_family_registry.csv`",
            "- `outputs/tables/ratewall_dynamic_uncertainty_envelope.csv`",
            "- `outputs/tables/ratewall_tdc_materialization_semantic_summary.csv`",
            "- `outputs/tables/ratewall_dynamic_crossing_robustness.csv`",
            "- `outputs/tables/ratewall_flow_stage_decomposition.csv`",
            "- `outputs/tables/ratewall_gross_interest_subchannels.csv`",
            "- `outputs/tables/ratewall_public_finance_adjustment.csv`",
            "- `outputs/tables/ratewall_net_countervailing_channels.csv`",
            "- `outputs/tables/ratewall_wall_hit_scenarios.csv`",
            "- `outputs/tables/ratewall_threshold_solver.csv`",
            "- `outputs/tables/ratewall_assumption_sensitivity.csv`",
            "- `outputs/tables/ratewall_parameter_frontier.csv`",
            "- `outputs/tables/ratewall_minimum_conditions_to_hit_wall.csv`",
            "- `outputs/tables/ratewall_hit_fragility_frontier.csv`",
            "- `outputs/tables/ratewall_frontier_driver_ranking.csv`",
            "- `outputs/tables/ratewall_assumption_mode_driver_dominance_matrix.csv`",
            "- `outputs/tables/ratewall_assumption_mode_pairwise_sensitivity_matrix.csv`",
            "- `outputs/tables/ratewall_backend_invariant_guardrail_audit.csv`",
            "- `outputs/tables/ratewall_backend_completion_verdict.csv`",
            "- `outputs/tables/ratewall_paper_channel_map.csv`",
            "- `outputs/tables/ratewall_paper_canonical_scenario_results.csv`",
            "- `outputs/tables/ratewall_paper_tdc_dynamic_contribution.csv`",
            "- `outputs/tables/ratewall_paper_parameter_justification.csv`",
            "- `outputs/tables/ratewall_paper_sensitivity_summary.csv`",
            "- `outputs/tables/ratewall_paper_disabled_claims_appendix.csv`",
            "- `outputs/tables/ratewall_paper_financialization_interpretation.csv`",
            "- `outputs/tables/ratewall_paper_support_invariant_audit.csv`",
            "- `outputs/tables/ratewall_backend_accounting_identity_audit.csv`",
            "- `outputs/tables/ratewall_paper_scenario_accounting_bridge.csv`",
            "- `outputs/tables/ratewall_paper_dynamic_scenario_summary.csv`",
            "- `outputs/tables/ratewall_conventional_drag_decomposition.csv`",
            "- `outputs/tables/ratewall_split_denominator_comparison.csv`",
            "- `outputs/tables/ratewall_denominator_sensitivity.csv`",
            "- `outputs/tables/ratewall_split_denominator_uncertainty.csv`",
            "- `outputs/tables/ratewall_split_denominator_regime_stability.csv`",
            "- `outputs/tables/ratewall_denominator_literature_matrix.csv`",
            "- `outputs/tables/ratewall_split_denominator_joint_uncertainty.csv`",
            "- `outputs/tables/ratewall_split_denominator_joint_regime_stability.csv`",
            "- `outputs/tables/ratewall_denominator_classifier_comparison.csv`",
            "- `outputs/tables/ratewall_backend_model_readiness_gate.csv`",
            "- `outputs/tables/ratewall_chapter_readiness_self_audit.csv`",
            "- `outputs/tables/ratewall_financialized_balance_sheet_channel.csv`",
            "- `outputs/tables/ratewall_financialization_proxy_registry.csv`",
            "- `outputs/tables/ratewall_household_safe_asset_capture_proxy.csv`",
            "- `outputs/tables/ratewall_household_safe_asset_exposure_panel.csv`",
            "- `outputs/tables/ratewall_household_safe_asset_access_context.csv`",
            "- `outputs/tables/ratewall_retail_safe_yield_access_substitution_context.csv`",
            "- `outputs/tables/ratewall_retail_deposit_beta_gap_context.csv`",
            "- `outputs/tables/ratewall_retail_pass_through_dispersion_panel.csv`",
            "- `outputs/tables/ratewall_deposit_competition_conditioner.csv`",
            "- `outputs/tables/ratewall_deposit_mmf_substitution_surface.csv`",
            "- `outputs/tables/ratewall_personal_net_interest_position_context.csv`",
            "- `outputs/tables/ratewall_firm_liquid_asset_public_context.csv`",
            "- `outputs/tables/ratewall_firm_liquid_asset_cushion_panel.csv`",
            "- `outputs/tables/ratewall_firm_net_interest_cushion_context.csv`",
            "- `outputs/tables/ratewall_firm_rollover_pressure_panel.csv`",
            "- `outputs/tables/ratewall_firm_short_rate_exposure_proxy.csv`",
            "- `outputs/tables/ratewall_household_borrower_fragility_context.csv`",
            "- `outputs/tables/ratewall_bank_loan_repricing_context.csv`",
            "- `outputs/tables/ratewall_cre_refinancing_public_context.csv`",
            "- `outputs/tables/ratewall_private_credit_bdc_context.csv`",
            "- `outputs/tables/ratewall_safe_yield_paired_proxy_surface.csv`",
            "- `outputs/tables/ratewall_financialization_proxy_source_gate.csv`",
            "- `outputs/tables/ratewall_financialization_source_gate.csv`",
            "- `outputs/tables/ratewall_financialization_restricted_protocols.csv`",
            "- `outputs/tables/ratewall_financialization_double_count_audit.csv`",
            "- `outputs/tables/ratewall_financialization_overlap_audit.csv`",
            "- `outputs/tables/ratewall_financialization_artifact_traceability_matrix.csv`",
            "- `outputs/tables/ratewall_backend_expansion_context_registry.csv`",
            "- `outputs/tables/ratewall_assumption_mode_channel_promotion_decision.csv`",
            "- `outputs/tables/ratewall_assumption_mode_promoted_channel_contributions.csv`",
            "- `outputs/tables/ratewall_assumption_mode_overlap_guardrail_audit.csv`",
            "- `outputs/tables/ratewall_assumption_mode_recipient_conversion_overlap_audit.csv`",
            "- `outputs/tables/ratewall_assumption_mode_sidecar_channel_decision.csv`",
            "- `outputs/tables/ratewall_assumption_mode_sidecar_contributions.csv`",
            "- `outputs/tables/ratewall_assumption_mode_sidecar_reasonableness_audit.csv`",
            "- `outputs/tables/ratewall_assumption_mode_sidecar_frontier.csv`",
            "- `outputs/tables/ratewall_assumption_mode_sidecar_bundle_frontier.csv`",
            "- `outputs/tables/ratewall_assumption_mode_sidecar_driver_decomposition.csv`",
            "- `outputs/tables/ratewall_assumption_mode_dynamic_sidecar_driver_decomposition.csv`",
            "- `outputs/tables/ratewall_assumption_mode_dynamic_sidecar_paths.csv`",
            "- `outputs/tables/ratewall_assumption_mode_dynamic_sidecar_family_summary.csv`",
            "- `outputs/tables/ratewall_assumption_mode_dynamic_sidecar_secondary_paths.csv`",
            "- `outputs/tables/ratewall_assumption_mode_dynamic_sidecar_secondary_frontier.csv`",
            "- `outputs/tables/ratewall_assumption_mode_parameter_activation_ledger.csv`",
            "- `outputs/tables/ratewall_assumption_mode_channel_status_crosswalk.csv`",
            "- `outputs/tables/ratewall_assumption_mode_formula_identity_audit.csv`",
            "- `outputs/tables/ratewall_assumption_source_backing_ledger.csv`",
            "- `outputs/tables/ratewall_assumption_source_backing_invariant_audit.csv`",
            "- `outputs/tables/ratewall_qrawatch_tdcsim_scenario_registry.csv`",
            "- `outputs/tables/ratewall_qrawatch_tdcsim_provenance_audit.csv`",
            "- `outputs/tables/ratewall_qrawatch_tdcsim_bridge_invariant_audit.csv`",
            "- `outputs/tables/ratewall_generated_text_claim_boundary_scan.csv`",
            "- `outputs/tables/ratewall_restricted_protocol_falsification_matrix.csv`",
            "- `outputs/tables/ratewall_restricted_protocol_field_contract.csv`",
            "- `outputs/tables/ratewall_context_surface_no_main_ratio_audit.csv`",
            "- `outputs/tables/ratewall_conventional_drag_bounded_denominator_registry.csv`",
            "- `outputs/tables/ratewall_denominator_methodology_registry.csv`",
            "- `outputs/tables/ratewall_annual_flow_denominator_anchor_registry.csv`",
            "- `outputs/tables/ratewall_annual_flow_runtime_family_registry.csv`",
            "- `outputs/tables/ratewall_annual_support_denominator_compatibility_registry.csv`",
            "- `outputs/tables/ratewall_annual_support_numerator_component_registry.csv`",
            "- `outputs/tables/ratewall_annual_support_numerator_source_gate.csv`",
            "- `outputs/tables/ratewall_annual_support_numerator_contract.csv`",
            "- `outputs/tables/ratewall_annual_support_numerator_uncertainty_envelope.csv`",
            "- `outputs/tables/ratewall_annual_support_numerator_contract_invariant_audit.csv`",
            "- `outputs/tables/ratewall_runtime_annual_flow_support_offset_scenarios.csv`",
            "- `outputs/tables/ratewall_runtime_annual_flow_support_offset_readiness_registry.csv`",
            "- `outputs/tables/ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv`",
            "- `outputs/tables/ratewall_runtime_annual_flow_support_offset_frontier_summary.csv`",
            "- `outputs/tables/ratewall_runtime_annual_flow_support_offset_closeout_decision.csv`",
            "- `outputs/tables/ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv`",
            "- `outputs/tables/ratewall_scenario_denominator_anchor_lineage.csv`",
            "- `outputs/tables/ratewall_scenario_denominator_stack_comparison.csv`",
            "- `outputs/tables/ratewall_denominator_scale_conflict_adjudication.csv`",
            "- `outputs/tables/ratewall_h4_empirical_validation_registry.csv`",
            "- `outputs/tables/ratewall_denominator_scale_conflict_followup_decision.csv`",
            "- `outputs/tables/ratewall_noncanonical_current_demand_source_timing_contract.csv`",
            "- `outputs/tables/ratewall_noncanonical_current_demand_consumer_endpoint_decision.csv`",
            "- `outputs/tables/ratewall_conventional_drag_current_demand_ratio_gate.csv`",
            "- `outputs/tables/ratewall_noncanonical_current_demand_support_ratio_consumer.csv`",
            "- `outputs/tables/ratewall_residualized_ffr_literature_replication_audit.csv`",
            "- `outputs/tables/ratewall_residualized_ffr_literature_lp_results.csv`",
            "- `outputs/tables/ratewall_residualized_ffr_fwl_diagnostics.csv`",
            "- `outputs/tables/ratewall_residualized_ffr_private_demand_bridge.csv`",
            "- `outputs/tables/ratewall_residualized_ffr_normalization_bridge.csv`",
            "- `outputs/tables/ratewall_conventional_drag_fspdp_proxy_iv_frbus_benchmark_crosscheck.csv`",
            "- `outputs/tables/ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv`",
            "- `outputs/tables/ratewall_conventional_drag_fspdp_proxy_iv_weak_iv_safe_inference.csv`",
            "- `outputs/tables/ratewall_conventional_drag_denominator_promotion_rule_evaluation.csv`",
            "- `outputs/tables/ratewall_conventional_drag_fspdp_denominator_conversion_uncertainty_boundary.csv`",
            "- `outputs/tables/ratewall_conventional_drag_fspdp_gdp_share_conversion_design_gate.csv`",
            "- `outputs/tables/ratewall_conventional_drag_fspdp_gdp_share_conversion_method_admission.csv`",
            "- `outputs/tables/ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv`",
            "- `outputs/tables/ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv`",
            "- `outputs/tables/ratewall_conventional_drag_fspdp_lp_sample_share_closeout_decision.csv`",
            "- `outputs/tables/ratewall_fairparke_benchmark_run_inventory.csv`",
            "- `outputs/tables/ratewall_fairparke_benchmark_mapping_contract.csv`",
            "- `outputs/tables/ratewall_assumption_mode_recipient_leakage_absorber_basis_audit.csv`",
            "- `outputs/tables/ratewall_household_within_distribution_safe_asset_capture_context.csv`",
            "- `outputs/tables/ratewall_deposit_pass_through_dispersion_conditioner.csv`",
            "- `outputs/tables/ratewall_brokerage_tbill_mmf_access_context.csv`",
            "- `outputs/tables/ratewall_firm_interest_income_expense_balance_context.csv`",
            "- `outputs/tables/ratewall_firm_debt_maturity_wall_context.csv`",
            "- `outputs/tables/ratewall_bdc_private_credit_stress_marker_context.csv`",
            "- `outputs/tables/ratewall_cre_maturity_refi_pressure_context.csv`",
            "- `outputs/tables/ratewall_bnpl_zero_interest_float_context.csv`",
            "- `outputs/tables/ratewall_safe_asset_substitution_pairing_audit.csv`",
            "- `outputs/tables/ratewall_financialization_expansion_avoidance_audit.csv`",
            "- `outputs/tables/ratewall_bank_nim_credit_supply_context.csv`",
            "- `outputs/tables/ratewall_tax_timing_interest_income_context.csv`",
            "- `outputs/tables/ratewall_foreign_holder_interest_leakage_context.csv`",
            "- `outputs/tables/ratewall_public_finance_remittance_timing_stress_grid.csv`",
            "- `outputs/tables/ratewall_insurance_pension_asset_liability_context.csv`",
            "- `outputs/tables/ratewall_housing_lockin_cashflow_context.csv`",
            "- `outputs/tables/ratewall_dealer_inventory_carry_context.csv`",
            "- `outputs/tables/ratewall_equity_transmission_channel_map.csv`",
            "- `outputs/tables/ratewall_equity_exposure_matrix.csv`",
            "- `outputs/tables/ratewall_equity_sensitivity_diagnostic.csv`",
            "- `outputs/tables/ratewall_equity_claim_status.csv`",
            "- `outputs/tables/ratewall_equity_evidence_workplan.csv`",
            "- `outputs/tables/ratewall_parameter_packs.csv`",
            "- `outputs/tables/ratewall_frontier_summary.csv`",
            "- `outputs/tables/ratewall_regime_map.csv`",
            "- `outputs/tables/ratewall_assumption_mode_interpretation.csv`",
            "- `outputs/tables/ratewall_prior_stack_diagnostic.csv`",
            "- `outputs/tables/ratewall_scenario_ladder.csv`",
            "- `outputs/tables/ratewall_model_adequacy_matrix.csv`",
            "- `outputs/tables/ratewall_assumption_mode_claim_boundary_audit.csv`",
            "- `outputs/tables/ratewall_dynamic_scenario_paths.csv`",
            "- `outputs/tables/ratewall_dynamic_scenario_path_consistency_diagnostic.csv`",
            "- `outputs/tables/ratewall_dynamic_offset_ratio_path.csv`",
            "- `outputs/tables/ratewall_scenario_crossing_diagnostic.csv`",
            "- `outputs/tables/ratewall_dynamic_sensitivity_frontier.csv`",
            "- `outputs/tables/ratewall_dynamic_scenario_family_registry.csv`",
            "- `outputs/tables/ratewall_dynamic_uncertainty_envelope.csv`",
            "- `outputs/tables/ratewall_dynamic_crossing_robustness.csv`",
            "- `configs/ratewall_assumption_sets.yml`",
            "- `configs/ratewall_parameter_packs.yml`",
            "- `configs/ratewall_assumption_source_backing_overrides.yml`",
            "- `configs/ratewall_dynamic_scenario_paths.yml`",
            "- `outputs/reports/ratewall_dynamic_assumption_mode_equations.md`",
            "- `outputs/tables/ratewall_financialization_pressure.csv`",
            "- `outputs/tables/ratewall_financialization_pressure_evidence_appendix.csv`",
            "- `outputs/tables/ratewall_safe_asset_retention_context.csv`",
            "- `outputs/tables/ratewall_safe_asset_retention_evidence_appendix.csv`",
            "- `outputs/tables/ratewall_contractionary_benchmark_calibration.csv`",
            "- `outputs/tables/ratewall_threshold_uncertainty_bands.csv`",
            "- `outputs/tables/ratewall_historical_threshold_validation.csv`",
            "- `outputs/tables/ratewall_policy_boundary_synthesis.csv`",
            "- `outputs/tables/ratewall_blocker_resolution_ledger.csv`",
            "- `outputs/tables/ratewall_publication_claim_decision.csv`",
            "- `outputs/tables/ratewall_final_blocker_ledger.csv`",
            "- `outputs/tables/ratewall_release_16_source_resolution_closeout.csv`",
            "- `outputs/tables/ratewall_release_16_no_further_promotion_ledger.csv`",
            "- `outputs/tables/ratewall_release_17_external_review_audit.csv`",
            "- `outputs/tables/ratewall_release_17_publication_polish_qa.csv`",
            "- `outputs/tables/ratewall_release_17_blocker_reopen_decision.csv`",
            "- `outputs/tables/ratewall_release_18_live_refresh_robustness_audit.csv`",
            "- `outputs/tables/ratewall_buyer_case_sign_matrix.csv`",
            "- `outputs/tables/ratewall_recipient_mpc_scenario_scaffold.csv`",
            "- `outputs/tables/ratewall_release_19_accounting_invariant_audit.csv`",
            "- `outputs/tables/ratewall_release_19_post_audit_methodology_audit.csv`",
            "- `outputs/tables/ratewall_release_20_activity_demand_benchmark.csv`",
            "- `outputs/tables/ratewall_release_20_state_dependent_lp_diagnostics.csv`",
            "- `outputs/tables/ratewall_release_20_benchmark_submission_decision.csv`",
            "- `outputs/tables/ratewall_release_21_live_refresh_endpoint_audit.csv`",
            "- `outputs/tables/ratewall_release_21_final_benchmark_gate.csv`",
            "- `outputs/tables/ratewall_release_21_backend_invariant_audit.csv`",
            "- `outputs/tables/ratewall_release_22_source_repro_accounting_audit.csv`",
            "- `outputs/tables/ratewall_release_22_core_output_source_gate.csv`",
            "- `outputs/tables/ratewall_release_22_reproducibility_hash_manifest.json`",
            "- `outputs/tables/ratewall_release_23_source_status_propagation_audit.csv`",
            "- `outputs/tables/ratewall_release_23_latest_as_of_semantics_audit.csv`",
            "- `outputs/tables/ratewall_release_23_threshold_mechanics_feasibility_audit.csv`",
            "- `outputs/tables/ratewall_release_23_calibration_plausibility_audit.csv`",
            "- `outputs/tables/ratewall_release_23_recipient_base_consistency_audit.csv`",
            "- `outputs/tables/ratewall_release_23_reproducibility_hash_manifest.json`",
            "- `outputs/tables/ratewall_release_23_archive_hash_verification_audit.csv`",
            "- `outputs/tables/ratewall_threshold_claim_boundary_audit.csv`",
            "- `outputs/tables/ratewall_tdc_source_coverage.csv`",
            "- `outputs/tables/ratewall_tdc_claim_boundary_audit.csv`",
            "- `outputs/tables/ratewall_score_dashboard.csv`",
            "- `outputs/tables/ratewall_release_manifest.json`",
            "- `outputs/tables/ratewall_claim_boundary_audit.csv`",
            "- `outputs/reports/ratewall_theory_of_change.md`",
            "- `outputs/reports/ratewall_assumption_engine_memo.md`",
            "- `outputs/reports/ratewall_assumption_mode_theory_chapter.md`",
            "- `outputs/reports/ratewall_assumption_mode_model_audit_packet.md`",
            "- `outputs/reports/ratewall_assumption_mode_critique_response.md`",
            "- `outputs/reports/ratewall_professor_model_review_prompt.md`",
            "- `outputs/reports/ratewall_interest_channel_expansion_plan.md`",
            "- `outputs/reports/ratewall_backend_completion_readiness_report.md`",
            "- `outputs/reports/ratewall_assumption_mode_v1_stage_completion_report.md`",
            "- `outputs/reports/ratewall_assumption_mode_post_closure_boundary_memo.md`",
            "- `outputs/reports/ratewall_paper_support_backend_appendix.md`",
            "- `outputs/reports/ratewall_financialization_proxy_backend_audit.md`",
            "- `outputs/reports/ratewall_financialization_interpretation_memo.md`",
            "- `outputs/reports/ratewall_dynamic_assumption_mode_equations.md`",
            "- `outputs/reports/ratewall_split_denominator_evidence_workplan.md`",
            "- `outputs/reports/ratewall_denominator_evidence_review.md`",
            "- `outputs/reports/ratewall_equity_transmission_attenuation_memo.md`",
            "- `outputs/reports/ratewall_equity_evidence_workplan.md`",
            "- Compiled PDF/PPTX render artifacts are intentionally excluded from the backend source archive until a later render-focused agent regenerates and audits them.",
            "- `outputs/reports/ratewall_figure_plate.md`",
            "- `outputs/reports/ratewall_table_plate.md`",
            "- `outputs/reports/ratewall_causal_identification_appendix.md`",
            "- `outputs/reports/ratewall_reviewer_limitations_memo.md`",
            "- `outputs/reports/ratewall_submission_causal_appendix.md`",
            "- `outputs/reports/ratewall_external_review_response_packet.md`",
            "- `outputs/reports/ratewall_submission_appendix_index.md`",
            "- `outputs/reports/ratewall_journal_submission_appendix.md`",
            "- `outputs/reports/ratewall_dynamic_causal_blocker_memo.md`",
            "- `outputs/reports/ratewall_referee_response_compendium.md`",
            "- `outputs/reports/ratewall_release_4_0_final_submission_memo.md`",
            "- `outputs/reports/ratewall_release_4_0_referee_packet.md`",
            "- `outputs/reports/ratewall_release_5_0_dynamic_lp_appendix.md`",
            "- `outputs/reports/ratewall_release_5_0_referee_response.md`",
            "- `outputs/reports/ratewall_release_6_0_proxy_svar_system_appendix.md`",
            "- `outputs/reports/ratewall_release_6_0_reviewer_response.md`",
            "- `outputs/reports/ratewall_release_7_0_system_identification_appendix.md`",
            "- `outputs/reports/ratewall_release_7_0_external_review_packet.md`",
            "- `outputs/reports/ratewall_release_8_0_system_nonpromotion_appendix.md`",
            "- `outputs/reports/ratewall_release_8_0_reviewer_response.md`",
            "- `outputs/reports/ratewall_release_9_0_structural_boundary_appendix.md`",
            "- `outputs/reports/ratewall_release_9_0_external_proxy_review_packet.md`",
            "- `outputs/reports/ratewall_tdc_deposit_channel_appendix.md`",
            "- `outputs/reports/ratewall_publication_claim_decision_memo.md`",
            "- `outputs/reports/ratewall_release_16_bounded_publication_closeout_memo.md`",
            "- `outputs/reports/ratewall_release_16_reviewer_blocker_text.md`",
            "- `outputs/reports/ratewall_release_17_external_review_packet.md`",
            "- `outputs/reports/ratewall_release_17_publication_polish_memo.md`",
            "- `outputs/reports/ratewall_release_18_publication_freeze_memo.md`",
            "- `outputs/reports/ratewall_release_19_post_audit_methodology_memo.md`",
            "- `outputs/reports/ratewall_release_20_submission_readiness_memo.md`",
            "- `outputs/reports/ratewall_release_21_backend_closeout_memo.md`",
            "- `outputs/reports/ratewall_release_22_backend_fix_memo.md`",
            "- `outputs/reports/ratewall_release_23_backend_fix_memo.md`",
            "- `outputs/reports/CITATION.cff`",
            "- `outputs/release/ratewall_release_23_0_source_archive.zip`",
            "",
            "## Reproduction",
            "",
            "Use the command sheet at "
            "`outputs/reports/ratewall_reproduction_commands.md`. It records "
            "the repo-safe cache and bytecode settings used by the release.",
            "",
        ]
    )


def _release_artifact_index_text(
    context: dict[str, object], artifacts: ReleaseArtifacts
) -> str:
    layers = _manifest_payload(
        context,
        claim_rows=_claim_audit_rows(context),
        artifacts=artifacts,
    )["artifact_layers"]
    lines = [
        "# RateWall Release Artifact Index",
        "",
        "This generated index maps the public-release package to its evidence layers.",
        "",
    ]
    for layer, paths in layers.items():
        lines.extend([f"## {layer.replace('_', ' ').title()}", ""])
        for path in paths:
            lines.append(f"- `{path}`")
        lines.append("")
    lines.extend(
        [
            "## Public Release Reports",
            "",
            f"- `{artifacts.final_paper_quarto}`",
            f"- `{artifacts.slide_deck_quarto}`",
            "- `outputs/reports/ratewall_theory_of_change.md`",
            f"- `{artifacts.public_readme}`",
            f"- `{artifacts.release_index}`",
            f"- `{artifacts.reproduction_commands}`",
            f"- `{artifacts.public_release_checklist}`",
            f"- `{artifacts.publication_claim_decision_memo}`",
            f"- `{artifacts.release_16_bounded_publication_closeout_memo}`",
            f"- `{artifacts.release_16_reviewer_blocker_text}`",
            f"- `{artifacts.release_17_external_review_packet}`",
            f"- `{artifacts.release_17_publication_polish_memo}`",
            f"- `{artifacts.release_18_publication_freeze_memo}`",
            f"- `{artifacts.figure_plate}`",
            f"- `{artifacts.table_plate}`",
            "- `outputs/reports/ratewall_runtime_annual_flow_support_offset_reviewer_packet.md`",
            "- `outputs/reports/ratewall_runtime_annual_flow_support_offset_limitations.md`",
            f"- `{artifacts.citation_metadata}`",
            f"- `{artifacts.package_smoke}`",
            f"- `{artifacts.source_archive}`",
            "",
        ]
    )
    return "\n".join(lines)


def _reproduction_commands_text() -> str:
    env = (
        "UV_PROJECT_ENVIRONMENT=$HOME/venvs/ratewall "
        "PYTHONDONTWRITEBYTECODE=1 "
        "PYTHONPYCACHEPREFIX=/tmp/ratewall-pycache "
        "PYTEST_ADDOPTS='-p no:cacheprovider' "
        "UV_CACHE_DIR=/tmp/uv-cache-ratewall "
        "RUFF_CACHE_DIR=/tmp/ruff-cache-ratewall"
    )
    commands = [
        f"{env} uv run python -B -m ratewall.cli data snapshot --mode live --output data/raw/ratewall_snapshot.json",
        f"{env} uv run python -B -m ratewall.cli databook build --snapshot data/raw/ratewall_snapshot.json --output-dir outputs",
        f"{env} uv run python -B -m ratewall.cli scenarios build --snapshot data/raw/ratewall_snapshot.json --output outputs/tables/ratewall_scenarios.csv",
        f"{env} uv run python -B -m ratewall.cli empirical specs --output outputs/empirical/local_projection_specs.json",
        f"{env} uv run python -B -m ratewall.cli empirical shocks --output outputs/empirical/monetary_shock_datasets.json",
        f"{env} uv run python -B -m ratewall.cli empirical smoke --snapshot data/raw/ratewall_snapshot.json --output outputs/tables/empirical_smoke_panel.csv",
        f"{env} uv run python -B -m ratewall.cli empirical results --snapshot data/raw/ratewall_snapshot.json",
        f"{env} uv run python -B -m ratewall.cli release build --snapshot data/raw/ratewall_snapshot.json --output-dir outputs",
        f"{env} uv run ruff check .",
        f"{env} uv run python -B -m pytest",
        f"{env} uv build --out-dir /tmp/ratewall-dist",
        f'{env} uv run python -B -c "import ratewall; import ratewall.cli; print(ratewall.__version__)"',
    ]
    lines = [
        "# RateWall Reproduction Commands",
        "",
        "Run from the repository root.",
        "",
        "The environment prefix keeps bytecode and tool caches out of the repo.",
        "",
    ]
    for index, command in enumerate(commands, start=1):
        lines.extend([f"## Step {index}", "", f"```bash\n{command}\n```", ""])
    return "\n".join(lines)


def _public_release_checklist_text(
    context: dict[str, object], claim_rows: list[dict[str, str]]
) -> str:
    sources = list(context["sources"])
    failed_claims = [row for row in claim_rows if row["audit_status"] != "pass"]
    return "\n".join(
        [
            "# RateWall Public Release Checklist",
            "",
            f"- Source provenance rows: `{len(sources)}`",
            f"- Claim-boundary failures: `{len(failed_claims)}`",
            f"- Empirical result rows: `{len(_rows(context, 'empirical_results'))}`",
            f"- Data-book metric rows: `{len(_rows(context, 'metrics'))}`",
            f"- Scenario rows: `{len(_rows(context, 'scenarios'))}`",
            "",
            "## Required Gates",
            "",
            "- Ruff passes with repo-safe cache settings.",
            "- Pytest passes with `python -B` and pytest cache disabled.",
            "- Provenance stores no credentials or secrets.",
            "- `do/`, `data/`, and `outputs/` remain ignored.",
            "- Pricing/incidence/welfare/reset-calendar construction switches remain false.",
            "- Paper and deck render from generated Quarto sources.",
            "- Source archive manifest records checksums for release inputs.",
            "- Package build and import smoke checks pass.",
            "",
        ]
    )


def _figure_plate_text(context: dict[str, object]) -> str:
    metric_names = {row.get("metric", "") for row in _rows(context, "metrics")}
    candidates = [
        ("ratewall_100bps_impulse.svg", "Mechanical 100 bps public-interest impulse"),
        ("ratewall_empirical_state_association.svg", "Bounded shock/state association"),
        ("debt_held_public_gdp.svg", "Debt held by public scaled by GDP"),
        ("reserves_gdp.svg", "Reserve balances scaled by GDP"),
        ("on_rrp_gdp.svg", "ON RRP scaled by GDP"),
        ("net_interest_fytd_gdp.svg", "Net-interest flow scaled by GDP"),
        (
            "treasury_valuation_readiness_coverage_rows.svg",
            "Valuation-readiness coverage rows",
        ),
        ("treasury_pricing_switches_disabled.svg", "Disabled pricing switches"),
        ("ratewall_dynamic_causal_gate.svg", "Release 3.0 dynamic causal gate"),
        (
            "ratewall_release_4_0_identification_frontier.svg",
            "Release 4.0 identification frontier",
        ),
        (
            "ratewall_release_5_0_dynamic_lp_estimates.svg",
            "Release 5.0 controlled dynamic-LP estimates",
        ),
        (
            "ratewall_release_6_0_system_identification_gate.svg",
            "Release 6.0 system-identification gate",
        ),
        (
            "ratewall_release_7_0_system_identification_frontier.svg",
            "Release 7.0 reduced-form system-identification frontier",
        ),
        (
            "ratewall_release_8_0_nonpromotion_gate.svg",
            "Release 8.0 system-identification non-promotion gate",
        ),
        (
            "ratewall_release_9_0_structural_boundary.svg",
            "Release 9.0 external-proxy structural boundary",
        ),
        (
            "ratewall_threshold_simulation_rows.svg",
            "Release 12.0 conditional threshold simulation rows",
        ),
        (
            "financialization_pressure_context_rows.svg",
            "Release 12.0 legacy bounded retention-context rows",
        ),
        (
            "safe_asset_retention_context_rows.svg",
            "Release 19.0 safe-asset-retention context rows",
        ),
        (
            "ratewall_assumption_offset_ratio.svg",
            "Assumption Mode offset ratio by scenario",
        ),
        (
            "ratewall_assumption_wall_gap_excess.svg",
            "Assumption Mode wall gap or excess by scenario",
        ),
        (
            "ratewall_assumption_decisive_channel_ranking.svg",
            "Assumption Mode decisive-channel count",
        ),
        (
            "ratewall_assumption_minimum_condition_frontier.svg",
            "Assumption Mode minimum condition frontier",
        ),
    ]
    lines = [
        "# RateWall Figure Plate",
        "",
        "Figures are generated from source-labeled, fallback-aware tables and are not independent evidence.",
        "",
    ]
    for filename, role in candidates:
        metric_hint = filename.removesuffix(".svg")
        status = "metric_present" if metric_hint in metric_names else "release_figure"
        lines.append(f"- `outputs/figures/{filename}`: {role}; status `{status}`.")
    lines.append("")
    return "\n".join(lines)


def _table_plate_text(context: dict[str, object]) -> str:
    table_specs = [
        (
            "ratewall_100bps_impulse.csv",
            "descriptive_accounting",
            "100 bps impulse horizons",
        ),
        (
            "ratewall_databook_metrics.csv",
            "descriptive_accounting",
            "data-book metrics",
        ),
        ("ratewall_scenarios.csv", "scenario_diagnostics", "scenario diagnostics"),
        (
            "ratewall_tdc_deposit_channel_ledger.csv",
            "tdc_deposit_accounting",
            "Release 10.0 TDC DU/RU accounting ledger",
        ),
        (
            "ratewall_tdc_ru_financing_deposit_impulse.csv",
            "tdc_deposit_accounting",
            "Release 10.0 DU/RU financing deposit-channel scenarios",
        ),
        (
            "ratewall_tdc_historical_panel.csv",
            "tdc_historical_accounting",
            "Release 11.0 historical partial TDC panel",
        ),
        (
            "ratewall_deposit_pricing_pass_through_context.csv",
            "deposit_pricing_context",
            "Release 11.0 deposit-pricing/pass-through context",
        ),
        (
            "ratewall_tdc_historical_reconciliation.csv",
            "tdc_source_coverage",
            "Release 11.0 source-backed/inferred/missing reconciliation",
        ),
        (
            "ratewall_tdcest_historical_estimator_bridge.csv",
            "tdc_historical_accounting",
            "TDC estimator bridge to sibling historical estimates",
        ),
        (
            "ratewall_tdcest_monetary_route_bridge.csv",
            "tdc_historical_accounting",
            "TDC-EST monetary route scope bridge for domestic nonbanks and MMFs",
        ),
        (
            "ratewall_tdcest_mmf_route_split_context.csv",
            "tdc_historical_accounting",
            "SEC N-MFP MMF retail/nonretail Treasury and ON-RRP context split",
        ),
        (
            "ratewall_tdcest_z1_domestic_nonbank_sector_context.csv",
            "tdc_historical_accounting",
            "Z.1 domestic nonbank sector context, context-only and fail-closed",
        ),
        (
            "ratewall_tdc_rolling_pass_through_context.csv",
            "tdc_historical_accounting",
            "Rolling TDC deposit pass-through context",
        ),
        (
            "ratewall_historical_tdc_wall_ratio_path.csv",
            "tdc_historical_accounting",
            "Historical TDC wall-ratio path",
        ),
        (
            "ratewall_historical_assumption_mode_tdc_wall_ratio_path.csv",
            "tdc_historical_accounting",
            "Historical Assumption Mode wall-ratio path with TDC",
        ),
        (
            "ratewall_tdc_other_component_bridge.csv",
            "tdc_deposit_accounting",
            "TDC reduced-form deposit effect and gap-to-unity identity bridge",
        ),
        (
            "ratewall_tdc_deposit_credit_decomposition.csv",
            "tdc_deposit_accounting",
            "Memo-only TDC residual allocation pack, not live drag",
        ),
        (
            "ratewall_tdc_double_count_guardrail.csv",
            "tdc_deposit_accounting",
            "TDC residual replace-not-stack double-count guardrail",
        ),
        (
            "ratewall_tdc_net_ratewall_effect.csv",
            "tdc_deposit_accounting",
            "TDC reduced-form and unity-reference wall-ratio variants",
        ),
        (
            "ratewall_tdc_materialization_semantic_summary.csv",
            "tdc_deposit_accounting",
            "Review-only EA-TDC TDC-to-deposit materialization semantics",
        ),
        (
            "ratewall_tdc_historical_source_contract.csv",
            "tdc_contract_ingest",
            "Contract-driven tdcest historical source hierarchy",
        ),
        (
            "ratewall_tdc_historical_selected_series.csv",
            "tdc_contract_ingest",
            "Contract-driven historical TDC selected-series status",
        ),
        (
            "ratewall_canonical_tdc_accounting_path.csv",
            "tdc_contract_ingest",
            "Canonical TDC accounting path, not demand conversion",
        ),
        (
            "ratewall_canonical_tdc_stitched_accounting_path.csv",
            "tdc_contract_ingest",
            "Canonical historical/forward TDC accounting stitch",
        ),
        (
            "ratewall_canonical_tdc_accounting_source_hierarchy_audit.csv",
            "tdc_contract_ingest",
            "Canonical TDC accounting source hierarchy audit",
        ),
        (
            "ratewall_tdcsim_projection_contract_bridge.csv",
            "tdc_contract_ingest",
            "Validated tdcsim quarterly projection contract bridge",
        ),
        (
            "ratewall_tdcsim_domestic_nonbank_funding_classification.csv",
            "tdc_contract_ingest",
            "TDCSim domestic-nonbank funding-route classification gap contract",
        ),
        (
            "ratewall_tdcsim_private_route_sensitivity_ingest.csv",
            "tdc_contract_ingest",
            "TDCSim Private route bounded sensitivity sidecar",
        ),
        (
            "ratewall_tdcsim_assumption_mode_support_ingest.csv",
            "tdc_contract_ingest",
            "TDCSim Assumption Mode support registry ingest",
        ),
        (
            "ratewall_tdcsim_assumption_mode_claim_gate.csv",
            "tdc_contract_ingest",
            "TDCSim Assumption Mode no-promotion claim gate",
        ),
        (
            "ratewall_tdcsim_assumption_mode_forecast_private_route_envelope.csv",
            "tdc_contract_ingest",
            "TDCSim Assumption Mode forecast private-route flow envelope",
        ),
        (
            "ratewall_tdcsim_assumption_mode_forecast_private_route_claim_gate.csv",
            "tdc_contract_ingest",
            "TDCSim Assumption Mode forecast private-route no-promotion gate",
        ),
        (
            "ratewall_qrawatch_tdcsim_scenario_registry.csv",
            "backend_expansion_context_design",
            "Fail-closed QRA Watch to TDCSim scenario-contract registry",
        ),
        (
            "ratewall_qrawatch_tdcsim_provenance_audit.csv",
            "backend_expansion_context_design",
            "Source-backing provenance audit for QRA Watch scenario inputs",
        ),
        (
            "ratewall_qrawatch_tdcsim_bridge_invariant_audit.csv",
            "backend_expansion_context_design",
            "Invariant audit for QRA Watch/TDCSim bridge disabled runtime switches",
        ),
        (
            "ratewall_tdc_forward_projection_surface.csv",
            "tdc_contract_ingest",
            "Noncanonical tdcsim forward TDC projection surface",
        ),
        (
            "ratewall_tdc_forward_component_audit.csv",
            "tdc_contract_ingest",
            "tdcsim forward component mutual-exclusion audit",
        ),
        (
            "ratewall_tdc_forward_overlap_guardrail.csv",
            "tdc_contract_ingest",
            "Direct-interest overlap subtraction guardrail",
        ),
        (
            "ratewall_tdc_forward_invariant_audit.csv",
            "tdc_contract_ingest",
            "tdcsim forward contract invariant audit",
        ),
        (
            "ratewall_tdc_forward_assumption_registry.csv",
            "tdc_contract_ingest",
            "Assumption-only TDC deposit conversion registry",
        ),
        (
            "ratewall_tdc_forward_scenario_decomposition.csv",
            "tdc_contract_ingest",
            "Forward TDC scenario component decomposition for charts",
        ),
        (
            "ratewall_forecast_holder_tdc_consistency_bridge.csv",
            "tdc_deposit_accounting",
            "Legacy forecast holder/TDC scaffold, not final TDC projection",
        ),
        (
            "ratewall_threshold_simulation.csv",
            "threshold_scenarios",
            "Release 12.0 conditional RateWall threshold simulation",
        ),
        (
            "ratewall_threshold_calibration_ranges.csv",
            "threshold_calibration",
            "Release 13.0 source-labeled calibration-context ranges under review",
        ),
        (
            "ratewall_threshold_calibrated_simulation.csv",
            "threshold_calibration",
            "Release 13.0 calibrated conditional threshold simulation",
        ),
        (
            "ratewall_du_ru_tga_calibration_bridge.csv",
            "tdc_calibration_bridge",
            "Release 13.0 DU/RU/TGA sibling-source bridge evidence",
        ),
        (
            "ratewall_assumption_sets.csv",
            "assumption_mode",
            "Explicit speculative assumptions for RateWall hit/non-hit cases",
        ),
        (
            "ratewall_condition_frontier.csv",
            "assumption_mode",
            "Condition frontier showing when the wall hits under assumptions",
        ),
        (
            "ratewall_offset_decomposition.csv",
            "assumption_mode",
            "Countervailing versus contractionary component decomposition",
        ),
        (
            "ratewall_public_impulse_factorization.csv",
            "assumption_mode",
            "Factored public-liability repricing handles behind the compatibility multiplier",
        ),
        (
            "ratewall_public_liability_repricing_ladder.csv",
            "assumption_mode",
            "Public-liability repricing ladder scaffold for Treasury, Fed-liability, and remittance timing blocks",
        ),
        (
            "ratewall_public_liability_repricing_evidence_bridge.csv",
            "assumption_mode",
            "Source-status bridge for Treasury/Fed-liability repricing evidence blocks that preserves aggregate Assumption Mode behavior",
        ),
        (
            "ratewall_public_liability_repricing_reconciliation_gap.csv",
            "assumption_mode",
            "Promotion-gate diagnostic for public-liability repricing evidence blocks before any formula replacement of aggregate Assumption Mode handles",
        ),
        (
            "ratewall_mspd_table3_bucket_repricing_gate.csv",
            "assumption_mode",
            "MSPD Table 3 Treasury bucket repricing source gate covering live source status, fallback rows, maturity horizons, and stock-scale reconciliation",
        ),
        (
            "ratewall_treasury_bucket_repricing_prior_bridge.csv",
            "assumption_mode",
            "Source-backed Treasury maturity-bucket repricing bridge; excludes recipient leakage, holder allocation, and security-level reset-calendar promotion",
        ),
        (
            "ratewall_interest_recipient_leakage_bridge.csv",
            "assumption_mode",
            "Recipient and leakage bridge scaffold from gross interest cashflows to demand-relevant support",
        ),
        (
            "ratewall_interest_recipient_leakage_evidence_gap.csv",
            "assumption_mode",
            "Component-level evidence-gap diagnostic for narrowing Treasury/IORB/ON RRP/remittance demand-conversion assumptions without changing the main ratio",
        ),
        (
            "ratewall_treasury_recipient_leakage_source_gate.csv",
            "assumption_mode",
            "Treasury recipient/leakage source gate proving holder context alone cannot narrow treasury_interest_demand_share",
        ),
        (
            "ratewall_public_finance_timing_path.csv",
            "assumption_mode",
            "Fiscal, TGA, and remittance timing scaffold with current numerator and memo-only semantics",
        ),
        (
            "ratewall_public_finance_timing_evidence_gap.csv",
            "assumption_mode",
            "Component-level evidence-gap diagnostic for fiscal/TGA/remittance timing, netting, and non-additivity assumptions without changing the main ratio",
        ),
        (
            "ratewall_public_finance_timing_design_test_scaffold.csv",
            "assumption_mode",
            "Executable non-promotional metadata for fiscal/TGA/remittance timing tests before absorber prior narrowing",
        ),
        (
            "ratewall_safe_yield_offset_drag_pairing_gap.csv",
            "assumption_mode",
            "Evidence-gap diagnostic pairing safe-yield income support with allocation drag",
        ),
        (
            "ratewall_bnpl_zero_interest_float_evidence_gap.csv",
            "assumption_mode",
            "Evidence-gap diagnostic for the minor BNPL/zero-interest float channel",
        ),
        (
            "ratewall_financialized_balance_sheet_evidence_gap.csv",
            "assumption_mode",
            "Evidence-gap diagnostic for household yield optimization and financialized balance-sheet pro-forma channels",
        ),
        (
            "ratewall_firm_cash_debt_maturity_evidence_gap.csv",
            "assumption_mode",
            "Evidence-gap diagnostic for firm cash, debt maturity, refinancing, and external-finance heterogeneity",
        ),
        (
            "ratewall_conventional_drag_channel_evidence_gap.csv",
            "assumption_mode",
            "Evidence-gap diagnostic for conventional-drag denominator channels",
        ),
        (
            "ratewall_conventional_drag_source_design_gate.csv",
            "assumption_mode",
            "Source/design gate for denominator prior narrowing and split-denominator promotion",
        ),
        (
            "ratewall_denominator_response_design_scaffold.csv",
            "assumption_mode",
            "Admissible-shock response-design scaffold for future scalar and split denominator prior narrowing",
        ),
        (
            "ratewall_denominator_response_design_test_scaffold.csv",
            "assumption_mode",
            "Executable non-promotional metadata for denominator response tests by component and horizon",
        ),
        (
            "ratewall_denominator_response_gate_attempt.csv",
            "assumption_mode",
            "Concrete blocked gate attempt for denominator response evidence before prior narrowing",
        ),
        (
            "ratewall_denominator_aligned_response_panel_scaffold.csv",
            "assumption_mode",
            "Non-promotional source/frequency/horizon alignment scaffold for denominator response panels",
        ),
        (
            "ratewall_denominator_event_outcome_cell_diagnostic.csv",
            "assumption_mode",
            "Support-count and missing-window diagnostic for non-promotional denominator event/outcome cells",
        ),
        (
            "ratewall_denominator_event_outcome_panel_value_diagnostic.csv",
            "assumption_mode",
            "Non-promotional first/last event-outcome value diagnostic with design checks for denominator response panels",
        ),
        (
            "ratewall_denominator_event_level_response_panel.csv",
            "assumption_mode",
            "Non-promotional event-level denominator response panel from admitted SF Fed, FEDS/BRW, Romer-Romer, GDP, and IP snapshots; no uncertainty runner or prior narrowing",
        ),
        (
            "ratewall_denominator_uncertainty_pass_fail_review.csv",
            "assumption_mode",
            "Fail-closed diagnostic uncertainty/pass-fail review over the denominator event-level panel; not calibration-grade and no prior narrowing",
        ),
        (
            "ratewall_denominator_panel_design_test_diagnostic.csv",
            "assumption_mode",
            "Non-promotional denominator panel design-test diagnostics for pretrend/placebo, relevance, sign, horizon, and robustness gates",
        ),
        (
            "ratewall_denominator_pretrend_placebo_diagnostic.csv",
            "assumption_mode",
            "Diagnostic-only denominator pretrend/placebo statistic layer; no denominator prior narrowing or promotion",
        ),
        (
            "ratewall_denominator_shock_relevance_diagnostic.csv",
            "assumption_mode",
            "Diagnostic-only denominator shock-relevance statistic layer; no response estimate or raw-rate-shock promotion",
        ),
        (
            "ratewall_denominator_sign_consistency_diagnostic.csv",
            "assumption_mode",
            "Diagnostic-only denominator sign-consistency statistic layer; no signed response estimate or prior narrowing",
        ),
        (
            "ratewall_denominator_horizon_sensitivity_diagnostic.csv",
            "assumption_mode",
            "Diagnostic-only denominator horizon-sensitivity statistic layer; no horizon response estimate or promotion",
        ),
        (
            "ratewall_denominator_outlier_window_robustness_diagnostic.csv",
            "assumption_mode",
            "Diagnostic-only denominator outlier/window robustness statistic layer; no formula replacement or prior narrowing",
        ),
        (
            "ratewall_denominator_design_readiness_decision.csv",
            "assumption_mode",
            "Consolidated denominator design-readiness decision table over all five diagnostic statistic layers; no estimates, promotion, or prior narrowing",
        ),
        (
            "ratewall_denominator_formal_design_test_result_scaffold.csv",
            "assumption_mode",
            "Formal denominator future-runner scaffold over complete design-readiness cells; no response estimates, test results, promotion, or prior narrowing",
        ),
        (
            "ratewall_denominator_formal_design_test_result.csv",
            "assumption_mode",
            "Formal denominator diagnostic-runner object table; joins "
            "non-promotional diagnostic objects with no response estimates, "
            "promotion-grade test results, promotion, or prior narrowing",
        ),
        (
            "ratewall_denominator_response_estimate_diagnostic.csv",
            "assumption_mode",
            "Non-promotional denominator response-estimate diagnostic table; "
            "estimates are not used for priors, promotion, formulas, or main "
            "offset-ratio changes",
        ),
        (
            "ratewall_denominator_cross_source_design_validation.csv",
            "assumption_mode",
            "Fail-closed denominator cross-source/design validation table; "
            "classifies diagnostic cells while keeping priors, promotion, "
            "formulas, raw-rate-shock claims, and main-ratio mechanics locked",
        ),
        (
            "ratewall_denominator_evidence_upgrade_source_design_requirement.csv",
            "assumption_mode",
            "Grouped denominator evidence-upgrade/source-design requirements "
            "for blocked validation cells; diagnostic-only and not promotion",
        ),
        (
            "ratewall_denominator_evidence_upgrade_priority_queue.csv",
            "assumption_mode",
            "Diagnostic-only priority queue for blocked denominator evidence "
            "requirements; ranks review order without promotion or priors",
        ),
        (
            "ratewall_denominator_evidence_upgrade_tier1_workplan.csv",
            "assumption_mode",
            "Tier-1 denominator evidence-upgrade workplan contracts; maps "
            "current artifacts, missing evidence, candidate designs, and "
            "fail-closed gates without promotion",
        ),
        (
            "ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv",
            "assumption_mode",
            "Long-form blocker-resolution matrix for tier-1 denominator "
            "workplans; decomposes missing evidence, diagnostic repair, "
            "peer-design, provenance, and admission-gate blockers",
        ),
        (
            "ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv",
            "assumption_mode",
            "Diagnostic blocker-status rollup by tier-1 workplan and blocker "
            "category; summarizes unresolved counts, action coverage, "
            "provenance coverage, and blocked admission status",
        ),
        (
            "ratewall_conventional_drag_evidence_tranche.csv",
            "assumption_mode",
            "First conventional-drag evidence tranche over tier-1 workplan "
            "cells; emits diagnostic shock/outcome estimates where current "
            "artifacts support them while keeping promotion gates closed",
        ),
        (
            "ratewall_baml_source_history_repair_contract.csv",
            "assumption_mode",
            "BAML source-history repair contract; records current public "
            "history limits and blocks BAML denominator admission until source "
            "history, support, and object semantics are repaired",
        ),
        (
            "ratewall_borrowing_cost_source_object_adjudication.csv",
            "assumption_mode",
            "Borrowing-cost source-object adjudication table; separates BAML "
            "OAS, effective-yield, HQM proxy, TDSP, and other candidates "
            "without admitting any replacement object",
        ),
        (
            "ratewall_baml_effective_yield_source_access_gate.csv",
            "assumption_mode",
            "BAML effective-yield source-access gate; records public metadata, "
            "ICE rights constraints, licensed-source requirements, snapshot "
            "contract fields, and event-window recomputation blockers",
        ),
        (
            "ratewall_hqm_source_proxy_lane_review.csv",
            "assumption_mode",
            "Official-public Treasury HQM proxy-lane review; source proxy "
            "context only, not high-yield or current-demand evidence",
        ),
        (
            "ratewall_hqm_event_window_feasibility.csv",
            "assumption_mode",
            "Treasury HQM event-window feasibility counts by shock and horizon; "
            "support diagnostics only, not response estimates or promotion",
        ),
        (
            "ratewall_hqm_event_outcome_panel_values.csv",
            "assumption_mode",
            "Observed Treasury HQM event/outcome panel values; diagnostic "
            "sidecar with all promotion and main-ratio switches disabled",
        ),
        (
            "ratewall_hqm_formal_diagnostic_gate.csv",
            "assumption_mode",
            "Treasury HQM formal diagnostic gate; reports OLS/pretrend/placebo/"
            "robustness diagnostics while blocking promotion-grade use",
        ),
        (
            "ratewall_hqm_promotion_protocol_gate.csv",
            "assumption_mode",
            "Treasury HQM promotion protocol gate; records which source stages "
            "pass nonpromotionally and which denominator gates remain blocked",
        ),
        (
            "ratewall_hqm_policy_path_exposure_admission.csv",
            "assumption_mode",
            "Treasury HQM policy-path exposure admission gate; blocks scalar "
            "shock use until source-admitted bps-year path vectors exist",
        ),
        (
            "ratewall_hqm_policy_path_protocol_dependency_gate.csv",
            "assumption_mode",
            "Treasury HQM dependency gate linking HQM path exposure to the "
            "global policy-path protocol blockers",
        ),
        (
            "ratewall_hqm_denominator_mapping_gate.csv",
            "assumption_mode",
            "Treasury HQM denominator mapping gate; permits high-quality proxy "
            "semantics only and blocks high-yield/current-demand overclaims",
        ),
        (
            "ratewall_hqm_borrowing_cost_object_comparator.csv",
            "assumption_mode",
            "Quantified Treasury HQM object-comparator diagnostic; aligns "
            "available candidate borrowing-cost sources by month and keeps "
            "HQM blocked from denominator promotion",
        ),
        (
            "ratewall_baa_event_window_support_diagnostic.csv",
            "assumption_mode",
            "BAA event-window support diagnostic; counts registered monetary "
            "shock support by horizon while keeping BAA blocked from denominator "
            "promotion",
        ),
        (
            "ratewall_baa_hqm_mapping_diagnostic.csv",
            "assumption_mode",
            "BAA/HQM mapping diagnostic; summarizes overlap, level differences, "
            "correlation, and stability windows without promoting BAA",
        ),
        (
            "ratewall_baa_response_diagnostic.csv",
            "assumption_mode",
            "BAA response diagnostic; summarizes nonpromotional response, "
            "pretrend, placebo, horizon, and trimmed-window checks while "
            "keeping Romer blocked",
        ),
        (
            "ratewall_baa_policy_path_normalization_gate.csv",
            "assumption_mode",
            "BAA policy-path normalization gate; records mechanical 100bp "
            "shock scaling while blocking 100bp-year and current-demand use",
        ),
        (
            "ratewall_baa_rights_proxy_uncertainty_review.csv",
            "assumption_mode",
            "BAA rights/proxy uncertainty review; records source history and "
            "diagnostics while blocking rights, proxy, mapping, policy-path, "
            "and current-demand promotion",
        ),
        (
            "ratewall_baa_current_demand_bridge_source_audit.csv",
            "assumption_mode",
            "BAA current-demand bridge source audit; checks response, macro, "
            "TDSP, and recipient-context routes while blocking conversion "
            "absent an independent BAA-yield-to-demand bridge",
        ),
        (
            "ratewall_hqm_current_demand_bridge_gate.csv",
            "assumption_mode",
            "Treasury HQM current-demand bridge gate; blocks GDP-share demand "
            "drag conversion until an independent source or model bridge exists",
        ),
        (
            "ratewall_conventional_drag_demand_conversion_admission.csv",
            "assumption_mode",
            "Fail-closed conversion admission surface for diagnostic "
            "conventional-drag rows; requires source-backed GDP-share and "
            "current-demand mappings before any denominator use",
        ),
        (
            "ratewall_conventional_drag_calibration_route.csv",
            "assumption_mode",
            "Fail-closed conventional-drag calibration route surface; decides "
            "whether regression diagnostics or research parameterization can "
            "be admitted before any denominator-prior use",
        ),
        (
            "ratewall_conventional_drag_research_parameterization_source_contract.csv",
            "assumption_mode",
            "Fail-closed required-field contract for a reviewed conventional-"
            "drag research parameterization route",
        ),
        (
            "ratewall_conventional_drag_research_parameterization_source_frontier.csv",
            "assumption_mode",
            "Fail-closed source-acquisition frontier for conventional-drag "
            "research parameterization candidates; no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_payload_manifest.csv",
            "assumption_mode",
            "Fail-closed manual/authenticated MIR/GK replication payload manifest; "
            "hash inventory only, no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_parameterization_parser_status.csv",
            "assumption_mode",
            "Fail-closed MIR/GK parser-status and extraction-prep surface; "
            "hash-backed file roles only, no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_payload_inner_inventory.csv",
            "assumption_mode",
            "Fail-closed MIR/GK inner-payload inventory; manual payload files "
            "are hashed or explicitly missing, no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_extraction_candidate.csv",
            "assumption_mode",
            "Fail-closed research extraction candidates for MIR/GK payload "
            "objects; parser metadata only, no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_extraction_gate_audit.csv",
            "assumption_mode",
            "Fail-closed research extraction gate audit for point estimate, "
            "uncertainty, normalization, mapping, replication, robustness, "
            "provenance, and promotion requirements",
        ),
        (
            "ratewall_conventional_drag_research_extraction_gate_detail.csv",
            "assumption_mode",
            "Fail-closed family-level MIR/GK extraction gate detail for raw "
            "and ambiguous source rows; review-only, no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_source_method_bridge.csv",
            "assumption_mode",
            "Fail-closed MIR/GK source-method bridge mapping parser families "
            "to target-contract proximity; no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_source_code_interpretation.csv",
            "assumption_mode",
            "Fail-closed MIR/GK source-code interpretation surface for nearest "
            "current-demand component IRFs; no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_extended_source_code_interpretation.csv",
            "assumption_mode",
            "Fail-closed extended MIR/GK source-code interpretation surface for "
            "FSPDP coverage gaps and non-FSPDP cross-checks; no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_fspdp_coverage_candidate_scan.csv",
            "assumption_mode",
            "Fail-closed MIR/GK FSPDP coverage-candidate scan; source candidates "
            "remain blocked on unit conversion, component weights, FSPDP coverage, "
            "and bps-year normalization",
        ),
        (
            "ratewall_conventional_drag_research_mir_component_aggregation_normalization_review.csv",
            "assumption_mode",
            "Fail-closed MIR component aggregation and normalization review; "
            "component/proxy evidence only, no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_mir_component_source_variant_review.csv",
            "assumption_mode",
            "Fail-closed MIR component source-variant review exposing multi-MAT "
            "supporting-source conflicts; no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_source_unit_conversion_review.csv",
            "assumption_mode",
            "Fail-closed research source-unit conversion review linking MIR "
            "component/proxy IRFs to FSPDP component shares; no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_mir_replication_source_unit_audit.csv",
            "assumption_mode",
            "Fail-closed MIR replication/source-unit audit reproducing "
            "authenticated MAT IRF cells; no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_mir_source_unit_transformation_contract.csv",
            "assumption_mode",
            "Fail-closed MIR source-unit transformation and sign-convention "
            "contract; no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_mir_target_horizon_reconciliation_contract.csv",
            "assumption_mode",
            "Fail-closed MIR target-horizon reconciliation contract; source "
            "month horizons are not admitted RateWall quarter horizons",
        ),
        (
            "ratewall_conventional_drag_research_mir_horizon_rekeying_candidate_review.csv",
            "assumption_mode",
            "Fail-closed MIR horizon rekeying candidate review; h12 is the "
            "only current exact 4q source-month candidate, no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_mir_h24_source_unit_audit.csv",
            "assumption_mode",
            "Fail-closed MIR h24 source-unit audit reproducing 24-month "
            "source cells for 8q review; no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_mir_h24_8q_rekeying_review.csv",
            "assumption_mode",
            "Fail-closed MIR h24-to-8q rekeying review; exact 8q horizon "
            "inputs only, no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_mir_4q8q_conversion_readiness_review.csv",
            "assumption_mode",
            "Fail-closed MIR 4q/8q conversion readiness review joining exact "
            "source horizons to FSPDP component shares; no denominator value",
        ),
        (
            "ratewall_conventional_drag_research_policy_path_normalization_bridge_review.csv",
            "assumption_mode",
            "Fail-closed MIR/GK research policy-path normalization bridge review; "
            "source shocks are not admitted 100bp-year paths and no denominator value",
        ),
        (
            "ratewall_policy_path_research_shock_source_evidence_protocol_review.csv",
            "assumption_mode",
            "Fail-closed policy-path source evidence protocol review for "
            "SF Fed/USMPD/Acosta/CME and MIR/GK research shocks; no bps-year "
            "or denominator value",
        ),
        (
            "ratewall_policy_path_source_code_workbook_object_inventory.csv",
            "assumption_mode",
            "Fail-closed inventory of USMPD/Acosta source-code, ZIP, and "
            "workbook objects; parser clues only and no bps-year value",
        ),
        (
            "ratewall_policy_path_source_code_workbook_protocol_deep_review.csv",
            "assumption_mode",
            "Fail-closed deep review of parsed USMPD/Acosta source-code and "
            "workbook objects against bps-year protocol gates",
        ),
        (
            "ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv",
            "assumption_mode",
            "Fail-closed USMPD PCA loading/back-transform review; loadings "
            "and Y1 scalar normalization are not bps-year path exposure",
        ),
        (
            "ratewall_policy_path_usmpd_scalar_score_replication_review.csv",
            "assumption_mode",
            "Fail-closed USMPD event-level scalar-score replication review; "
            "source MPS scores are not bps-year path exposure",
        ),
        (
            "ratewall_policy_path_usmpd_pca_backtransform_gate_review.csv",
            "assumption_mode",
            "Fail-closed USMPD PCA back-transform gate review identifying "
            "remaining path-normalization blockers",
        ),
        (
            "ratewall_policy_path_usmpd_instrument_decomposition_design_review.csv",
            "assumption_mode",
            "Fail-closed USMPD instrument-decomposition design review; scalar "
            "PC1/MPS loadings are not instrument-level bps-year path exposure",
        ),
        (
            "ratewall_policy_path_bps_year_candidate_path_design_contract.csv",
            "assumption_mode",
            "Fail-closed candidate path design contract joining USMPD scalar "
            "review to CME contract intervals without emitting bps-year exposure",
        ),
        (
            "ratewall_policy_path_formula_replication_source_review.csv",
            "assumption_mode",
            "Fail-closed policy-path formula/replication source review linking "
            "hashed sources to missing bps-year bridge evidence",
        ),
        (
            "ratewall_policy_path_reviewed_bps_year_protocol_gap_matrix.csv",
            "assumption_mode",
            "Fail-closed policy-path reviewed bps-year protocol gap matrix; "
            "cross-surface unit/horizon/integral/replication blockers only",
        ),
        (
            "ratewall_policy_path_protocol_source_acquisition_work_queue.csv",
            "assumption_mode",
            "Fail-closed policy-path protocol source-acquisition work queue; "
            "ranked source/download/parse actions only",
        ),
        (
            "ratewall_policy_path_protocol_source_parse_execution_review.csv",
            "assumption_mode",
            "Fail-closed policy-path protocol source parse-execution review; "
            "text/code/workbook clues only",
        ),
        (
            "ratewall_policy_path_source_parse_synthesis_queue.csv",
            "assumption_mode",
            "Fail-closed policy-path source-parse synthesis queue; ranked "
            "next parse/acquisition/protocol actions only",
        ),
        (
            "ratewall_policy_path_source_parse_action_execution.csv",
            "assumption_mode",
            "Fail-closed policy-path source-parse action-execution table; "
            "grouped deeper-parse/new-acquisition/protocol-authoring actions "
            "only",
        ),
        (
            "ratewall_policy_path_deeper_parse_execution_review.csv",
            "assumption_mode",
            "Fail-closed policy-path deeper-parse execution review; precise "
            "source snippets from existing hash-backed artifacts only",
        ),
        (
            "ratewall_policy_path_protocol_candidate_draft_review.csv",
            "assumption_mode",
            "Fail-closed policy-path protocol-candidate draft review; "
            "component-level snippet and missing-evidence rows only",
        ),
        (
            "ratewall_policy_path_protocol_missing_evidence_acquisition_queue.csv",
            "assumption_mode",
            "Fail-closed policy-path missing-evidence acquisition queue; "
            "ranked source acquisition/deeper-parse targets only",
        ),
        (
            "ratewall_policy_path_protocol_missing_evidence_parse_execution_review.csv",
            "assumption_mode",
            "Fail-closed policy-path missing-evidence parse-execution review; "
            "target-specific source snippets and blockers only",
        ),
        (
            "ratewall_policy_path_protocol_authoring_readiness_matrix.csv",
            "assumption_mode",
            "Fail-closed policy-path protocol authoring/readiness matrix; "
            "component deliverables and blockers only",
        ),
        (
            "ratewall_policy_path_protocol_field_authoring_contract.csv",
            "assumption_mode",
            "Fail-closed policy-path protocol field-authoring contract; "
            "required fields and pass/fail blockers only",
        ),
        (
            "ratewall_policy_path_field_evidence_resolution_queue.csv",
            "assumption_mode",
            "Fail-closed policy-path field evidence resolution queue; "
            "ranked extraction, invariant, and replication-design work only",
        ),
        (
            "ratewall_conventional_drag_fspdp_component_decomposition_bridge.csv",
            "assumption_mode",
            "Fail-closed FSPDP component decomposition bridge registering "
            "PCE and private fixed-investment component-weight requirements; "
            "no GDP-share drag or denominator value",
        ),
        (
            "ratewall_conventional_drag_fspdp_component_source_manifest.csv",
            "assumption_mode",
            "Source-backed BEA NIPA mirror component source manifest for FSPDP "
            "decomposition weights; conversion input only",
        ),
        (
            "ratewall_conventional_drag_fspdp_component_share_panel.csv",
            "assumption_mode",
            "Source-backed FSPDP component share panel; no conventional-drag "
            "estimate or denominator-prior input",
        ),
        (
            "ratewall_conventional_drag_fspdp_coverage_weight_requirement_review.csv",
            "assumption_mode",
            "Fail-closed bridge from MIR/GK FSPDP coverage targets to official "
            "component-share requirements; no denominator value",
        ),
        (
            "ratewall_conventional_drag_fspdp_coverage_priority_search_queue.csv",
            "assumption_mode",
            "Fail-closed source-code search queue ranking MIR/GK FSPDP "
            "coverage gaps by official component-share weight; no denominator "
            "value",
        ),
        (
            "ratewall_conventional_drag_fspdp_source_code_search_review.csv",
            "assumption_mode",
            "Fail-closed parsed-payload source-code/MAT search review for "
            "MIR/GK FSPDP coverage gaps; no denominator value",
        ),
        (
            "ratewall_conventional_drag_fspdp_external_source_acquisition_action_plan.csv",
            "assumption_mode",
            "Fail-closed external/source-acquisition action plan for MIR/GK "
            "FSPDP coverage gaps; no denominator value",
        ),
        (
            "ratewall_conventional_drag_fspdp_official_component_source_acquisition_execution.csv",
            "assumption_mode",
            "Fail-closed official BEA/FRED FSPDP component-source acquisition "
            "execution; source data only, no denominator value",
        ),
        (
            "ratewall_conventional_drag_fspdp_research_side_action_plan_extraction_review.csv",
            "assumption_mode",
            "Fail-closed research-side action-plan extraction review for "
            "MIR/GK and FRB/US FSPDP coverage gaps; no denominator value",
        ),
        (
            "ratewall_current_demand_gdp_share_source_manifest.csv",
            "assumption_mode",
            "Source-backed current-demand GDP-share source manifest for FSPDP, "
            "GDP, PCE, and fixed investment; conversion input only",
        ),
        (
            "ratewall_current_demand_gdp_share_panel.csv",
            "assumption_mode",
            "Source-backed current-demand GDP-share panel; no conventional-drag "
            "estimate or denominator-prior input",
        ),
        (
            "ratewall_conventional_drag_current_demand_mapping_bridge.csv",
            "assumption_mode",
            "Source-backed FSPDP/PCE/fixed-investment current-demand mapping "
            "bridge for research extraction; conversion review only",
        ),
        (
            "ratewall_conventional_drag_research_extraction_conversion_bridge.csv",
            "assumption_mode",
            "Fail-closed bridge from research extraction gates to the FSPDP "
            "conversion panel; no denominator calibration",
        ),
        (
            "ratewall_conventional_drag_local_macro_panel.csv",
            "assumption_mode",
            "Diagnostic-only local LP macro panel for current-demand outcomes; "
            "conversion input only, no drag estimate",
        ),
        (
            "ratewall_conventional_drag_local_shock_quarterly.csv",
            "assumption_mode",
            "Diagnostic-only quarterly source-defined monetary surprise surface; "
            "not admitted as 100bp-year policy path",
        ),
        (
            "ratewall_conventional_drag_local_lp_design.csv",
            "assumption_mode",
            "Fail-closed local LP design rows for conventional-drag research; "
            "no denominator calibration",
        ),
        (
            "ratewall_conventional_drag_local_lp_diagnostic.csv",
            "assumption_mode",
            "Blocked local LP diagnostic placeholders; no estimates or prior "
            "narrowing until policy-path normalization passes",
        ),
        (
            "ratewall_conventional_drag_local_lp_estimate_diagnostic.csv",
            "assumption_mode",
            "Source-unit local LP diagnostic estimates with HAC-style errors; "
            "not normalized to 100bp-year and not denominator calibration",
        ),
        (
            "ratewall_conventional_drag_local_lp_robustness_diagnostic.csv",
            "assumption_mode",
            "Source-unit local LP robustness, pretrend, and leave-one-out "
            "diagnostics; no promotion or denominator value",
        ),
        (
            "ratewall_conventional_drag_local_lp_sample_window_audit.csv",
            "assumption_mode",
            "Sample-window audit for source-unit local LP diagnostics; no "
            "100bp-year admission or denominator calibration",
        ),
        (
            "ratewall_conventional_drag_local_lp_admission_audit.csv",
            "assumption_mode",
            "Fail-closed admission audit for local LP diagnostic gates",
        ),
        (
            "ratewall_openicpsr_replication_package_source_manifest.csv",
            "assumption_mode",
            "Fail-closed openICPSR/AEA replication-package metadata manifest; "
            "no denominator value or runtime input",
        ),
        (
            "ratewall_frbus_model_benchmark_simulation_readiness.csv",
            "assumption_mode",
            "Fail-closed FRB/US model-benchmark simulation-readiness surface; "
            "no empirical denominator calibration",
        ),
        (
            "ratewall_frbus_conventional_drag_benchmark_protocol.csv",
            "assumption_mode",
            "Fail-closed FRB/US conventional-drag benchmark protocol; official "
            "model benchmark context only, no denominator calibration",
        ),
        (
            "ratewall_frbus_official_model_package_inventory.csv",
            "assumption_mode",
            "Fail-closed FRB/US official package inventory with source hashes "
            "and relevant model/data/demo files; no denominator calibration",
        ),
        (
            "ratewall_frbus_official_model_benchmark_simulation_protocol.csv",
            "assumption_mode",
            "Fail-closed FRB/US official-model simulation protocol; benchmark "
            "review only, no GDP-share drag or runtime input",
        ),
        (
            "ratewall_frbus_runtime_runner_preflight.csv",
            "assumption_mode",
            "Fail-closed FRB/US runtime-runner preflight with install, import, "
            "model-load, and official-demo command provenance",
        ),
        (
            "ratewall_frbus_runtime_runner_output_slots.csv",
            "assumption_mode",
            "FRB/US runtime output slots captured as official-model benchmark "
            "diagnostics only; no GDP-share drag or denominator calibration",
        ),
        (
            "ratewall_frbus_benchmark_comparison_mapping_contract.csv",
            "assumption_mode",
            "Fail-closed FRB/US benchmark comparison and mapping contract; "
            "pins runtime outputs and records promotion blockers only",
        ),
        (
            "ratewall_frbus_benchmark_output_slot_extension_review.csv",
            "assumption_mode",
            "Fail-closed FRB/US output-slot extension review for FSPDP coverage "
            "gaps; model outputs are benchmark-only, no denominator value",
        ),
        (
            "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv",
            "assumption_mode",
            "Fail-closed source-unit aggregation blocker bridge across MIR/GK "
            "and FRB/US routes; gate matrix only, no denominator value",
        ),
        (
            "ratewall_conventional_drag_mirgk_targeted_gap_source_followup.csv",
            "assumption_mode",
            "Fail-closed targeted MIR/GK source follow-up for PCE services, "
            "aggregate PCE, and direct private fixed investment gaps; parsed "
            "payload hits remain review-only, no denominator value",
        ),
        (
            "ratewall_conventional_drag_promotion_contract_checklist.csv",
            "assumption_mode",
            "Fail-closed promotion-contract checklist that converts the "
            "14-gate source-unit bridge into admission evidence and tolerance "
            "requirements; no denominator value or runtime promotion",
        ),
        (
            "ratewall_conventional_drag_empirical_target_registry.csv",
            "assumption_mode",
            "Compact fail-closed conventional-drag empirical target registry "
            "with one preferred FSPDP target and separated benchmark, research, "
            "proxy, context, and local-diagnostic routes; no denominator value",
        ),
        (
            "ratewall_conventional_drag_route_pruning_audit.csv",
            "assumption_mode",
            "Fail-closed conventional-drag route-pruning audit that preserves "
            "FRB/US benchmark-only, HOUST/PERMIT proxy-only, MIR/GK "
            "research-only, and local LP diagnostic-only boundaries",
        ),
        (
            "ratewall_conventional_drag_response_design_gate.csv",
            "assumption_mode",
            "Fail-closed conventional-drag response-design gate stack across "
            "policy-path, mapping, conversion, uncertainty, replication, "
            "robustness, and promotion requirements; no denominator value",
        ),
        (
            "ratewall_denominator_response_estimate_registry.csv",
            "assumption_mode",
            "Fail-closed denominator response-estimate design registry with "
            "local LP/proxy-SVAR, MIR/GK research, FRB/US benchmark, proxy, "
            "and canonical-placeholder cells; no admitted estimate",
        ),
        (
            "ratewall_denominator_formal_design_gate.csv",
            "assumption_mode",
            "Formal design gate audit for denominator response-estimate cells "
            "across policy-path, mapping, conversion, uncertainty, "
            "replication, robustness, and promotion gates; no admitted value",
        ),
        (
            "ratewall_tdsp_current_demand_source_review.csv",
            "assumption_mode",
            "Source-review gate for TDSP, GDP/PCE/DPI candidates, and scalar "
            "monetary-shock timing inputs in the TDSP current-demand bridge",
        ),
        (
            "ratewall_tdsp_current_demand_unit_conversion.csv",
            "assumption_mode",
            "Fail-closed unit-conversion requirements from TDSP percent-of-"
            "income units through current-demand dollars and GDP-share units",
        ),
        (
            "ratewall_tdsp_current_demand_diagnostic_mapping.csv",
            "assumption_mode",
            "Diagnostic TDSP-to-current-demand candidate mappings with HAC "
            "uncertainty where current snapshots support them; no promotion",
        ),
        (
            "ratewall_tdsp_policy_path_normalization_blocker.csv",
            "assumption_mode",
            "Policy-path 100bp-year normalization blockers for selected TDSP "
            "shock rows; scalar shocks are not path exposure vectors",
        ),
        (
            "ratewall_tdsp_current_demand_admission_audit.csv",
            "assumption_mode",
            "Source-backing-ledger admission audit for TDSP current-demand "
            "mapping rows; blocked rows cannot affect runtime mechanics",
        ),
        (
            "ratewall_pce_dpi_source_refresh_contract.csv",
            "assumption_mode",
            "Fail-closed FRED source-refresh contracts for missing PCE/DPI "
            "inputs needed by the TDSP current-demand bridge",
        ),
        (
            "ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv",
            "assumption_mode",
            "Diagnostic-only TDSP mappings rerun against the materialized "
            "PCE/DPI refresh bundle; not current-demand drag or promotion",
        ),
        (
            "ratewall_tdsp_diagnostic_family_completion_gate.csv",
            "assumption_mode",
            "Fail-closed TDSP diagnostic-family completion gate across source, "
            "mapping, refresh, policy-path, audit, and replication blockers",
        ),
        (
            "ratewall_policy_path_exposure_vector_design_gate.csv",
            "assumption_mode",
            "Fail-closed policy-path exposure-vector design gate for BRW, "
            "SF Fed, and Romer-Romer scalar monetary shock sources",
        ),
        (
            "ratewall_policy_path_reviewed_protocol_source_context.csv",
            "assumption_mode",
            "Materialized SF Fed policy-path source context; partial context "
            "only and not a bps-year vector or promotion gate pass",
        ),
        (
            "ratewall_policy_path_protocol_source_acquisition_registry.csv",
            "assumption_mode",
            "Fail-closed raw-source acquisition registry for USMPD, SOFR "
            "continuity, and Acosta/GSS replication candidates; not bps-year "
            "or runtime input",
        ),
        (
            "ratewall_policy_path_protocol_source_acquisition_audit.csv",
            "assumption_mode",
            "Audit of acquired policy-path protocol source artifacts, hashes, "
            "and blocked admission status",
        ),
        (
            "ratewall_policy_path_protocol_review_inventory.csv",
            "assumption_mode",
            "Blocked protocol-review inventory over USMPD, SOFR continuity, "
            "and Acosta/GSS source evidence; not bps-year or runtime input",
        ),
        (
            "ratewall_policy_path_protocol_review_audit.csv",
            "assumption_mode",
            "Audit of protocol-review inventory blockers and disabled runtime "
            "switches",
        ),
        (
            "ratewall_policy_path_mps_scalar_replication_diagnostic.csv",
            "assumption_mode",
            "USMPD mps.R scalar replication diagnostic; replicated scalar "
            "surprises only and not a bps-year path or runtime input",
        ),
        (
            "ratewall_policy_path_mps_scalar_replication_audit.csv",
            "assumption_mode",
            "Audit of USMPD scalar replication pass status, missing "
            "loadings/horizon weights, and disabled runtime switches",
        ),
        (
            "ratewall_policy_path_bps_year_blocker_decision.csv",
            "assumption_mode",
            "Terminal fail-closed decision that local USMPD/Acosta/SOFR "
            "materials do not supply a reviewed bps-year policy-path bridge",
        ),
        (
            "ratewall_policy_path_bps_year_blocker_decision_audit.csv",
            "assumption_mode",
            "Audit of bps-year blocker decision rows and disabled runtime "
            "switches",
        ),
        (
            "ratewall_policy_path_event_level_candidate_vector.csv",
            "assumption_mode",
            "SF Fed workbook FF/ED event-level candidate-vector extraction; "
            "not a reviewed horizon grid, bps-year protocol, or raw-rate shock",
        ),
        (
            "ratewall_policy_path_event_level_candidate_vector_audit.csv",
            "assumption_mode",
            "Extraction audit for the SF Fed event-level candidate vector; "
            "fail-closed and not a runtime policy-path admission",
        ),
        (
            "ratewall_policy_path_contract_interval_source_review.csv",
            "assumption_mode",
            "Contract interval and quote-rule review joined to SF Fed "
            "candidate-vector rows; not a bps-year path exposure",
        ),
        (
            "ratewall_policy_path_contract_spec_acquisition_blocker.csv",
            "assumption_mode",
            "Explicit blocker for official CME contract-spec acquisition "
            "when reproducible source artifacts are unavailable",
        ),
        (
            "ratewall_policy_path_bps_year_source_protocol.csv",
            "assumption_mode",
            "Fail-closed required-field protocol for source-backed bps-year "
            "policy-path exposure construction from scalar shock sources",
        ),
        (
            "ratewall_policy_path_normalization_source_manifest.csv",
            "assumption_mode",
            "Fail-closed manifest tying policy-path normalization source "
            "families to unit, horizon, formula, replication, and blocker "
            "status; not a bps-year path exposure",
        ),
        (
            "ratewall_policy_path_bps_year_normalization_review.csv",
            "assumption_mode",
            "Formula-step review rows for SF Fed candidate cells and USMPD "
            "scalar MPS replication; all bps-year outputs remain blank",
        ),
        (
            "ratewall_policy_path_source_cell_unit_contract_review.csv",
            "assumption_mode",
            "Source-cell unit/sign closure review that keeps official quote "
            "metadata separate from SF Fed workbook-cell admission",
        ),
        (
            "ratewall_policy_path_bps_year_protocol_closure.csv",
            "assumption_mode",
            "Full bps-year admission-gate closure surface; current rows remain "
            "blocked and emit no rate-change, bps-year, or GDP-share outputs",
        ),
        (
            "ratewall_policy_path_normalization_leak_audit.csv",
            "assumption_mode",
            "Executable audit preventing quote, scalar, literal-NA, static-"
            "quarter, prompt-number, or bps-year normalization leaks",
        ),
        (
            "ratewall_tdsp_pce_dpi_policy_path_admission_audit.csv",
            "assumption_mode",
            "Source-backing-ledger admission audit for PCE/DPI refresh "
            "contracts and policy-path exposure-vector blockers",
        ),
        (
            "ratewall_interest_channel_horizon_timing_matrix.csv",
            "assumption_mode",
            "Cross-channel horizon/timing registry for current, lagged, memo, and secondary channels",
        ),
        (
            "ratewall_interest_channel_promotion_gate.csv",
            "assumption_mode",
            "Consolidated source-status and promotion gate for all RateWall interest-rate channels",
        ),
        (
            "ratewall_interest_channel_evidence_upgrade_queue.csv",
            "assumption_mode",
            "Priority queue for source-specific evidence upgrades by channel load-bearing importance and classification impact",
        ),
        (
            "ratewall_high_priority_interest_channel_source_bridge.csv",
            "assumption_mode",
            "Source-specific bridge for the highest-load-bearing RateWall interest-channel evidence upgrades",
        ),
        (
            "ratewall_source_gate_prior_narrowing_decision.csv",
            "assumption_mode",
            "Current source-gate decision table showing why no top-priority prior can narrow in this build",
        ),
        (
            "ratewall_source_gate_exhaustion_closure.csv",
            "assumption_mode",
            "Final gate-by-gate source-mining closure surface for the current public/official/local evidence phase",
        ),
        (
            "ratewall_restricted_data_gate_spec.csv",
            "assumption_mode",
            "Restricted/licensed-data gate specification for promotion requirements after public source-mining exhaustion",
        ),
        (
            "ratewall_assumption_mode_post_closure_boundary_map.csv",
            "assumption_mode",
            "Post-source-closure reporting boundary map separating admitted context, blockers, restricted data requirements, assumptions, and disabled claims",
        ),
        (
            "ratewall_sibling_evidence_bridge.csv",
            "assumption_mode",
            "Sibling TDC/Treasury artifact bridge mapping reusable sibling evidence to RateWall source gates without empirical promotion",
        ),
        (
            "ratewall_sibling_evidence_upgrade_queue.csv",
            "assumption_mode",
            "Prioritized sibling-evidence upgrade queue ranked by load-bearing importance, gate potential, complexity, and forbidden-claim risk",
        ),
        (
            "ratewall_higher_rate_channel_registry.csv",
            "assumption_mode",
            "Higher-rate-channel ontology separating cashflow support, denominator drag, price-channel, nominal-sidecar, secondary, and scaffold-only roles",
        ),
        (
            "ratewall_corporate_net_interest_cashflow_bridge.csv",
            "assumption_mode",
            "Source-gated corporate net-interest cashflow bridge with cash-interest, refinancing-drag, and net-offset rows outside the main ratio",
        ),
        (
            "ratewall_working_capital_cost_channel_diagnostic.csv",
            "assumption_mode",
            "Diagnostic-only working-capital cost pass-through price-channel scaffold with no real-demand numerator or CPI forecast output",
        ),
        (
            "ratewall_term_structure_pricing_carry_diagnostic.csv",
            "assumption_mode",
            "Diagnostic-only term-structure carry-pricing scaffold with no forward-price, commodity, CPI, threshold-date, or pricing output",
        ),
        (
            "ratewall_interest_channel_module_registry.csv",
            "assumption_mode",
            "Module registry for the fuller RateWall interest-rate-channel build plan",
        ),
        (
            "ratewall_interest_channel_completion_matrix.csv",
            "assumption_mode",
            "Assumption Mode v1 completion matrix for main-ratio, secondary, diagnostic, and source-gated channels",
        ),
        (
            "ratewall_dynamic_scenario_paths.csv",
            "dynamic_assumption_mode",
            "Source-gated quarterly scenario inputs for debt/GDP, policy-rate, liquidity/TDC state, repricing, timing, and drag paths",
        ),
        (
            "ratewall_tdc_deposit_pass_through_source_import.csv",
            "dynamic_assumption_mode",
            "Source-backed EA-TDC deposit pass-through import rows for dynamic TDC liquidity-state scenarios",
        ),
        (
            "ratewall_tdc_ea_tdc_pass_through_calibration_import.csv",
            "dynamic_assumption_mode",
            "Versioned review-only import of EA-TDC pass-through estimates, rolling betas, pandemic exclusions, episode betas, state diagnostics, and manifests",
        ),
        (
            "ratewall_tdc_ea_tdc_pass_through_regime_validation_import.csv",
            "dynamic_assumption_mode",
            "Review-only import of EA-TDC pass-through regime-validation contract, classifier, estimates, validation table, and manifest; runtime selector remains blocked",
        ),
        (
            "ratewall_tdc_deposit_pass_through_regime_scenarios.csv",
            "dynamic_assumption_mode",
            "Scenario-only EA-TDC deposit pass-through regime paths, including normal-forward, rolling, full-sample, and liquidity-event step-up variants",
        ),
        (
            "ratewall_tdc_deposit_pass_through_scenario_contract.csv",
            "dynamic_assumption_mode",
            "Source-bound fail-closed TDC deposit pass-through scenario contract tying scenario values to EA-TDC imports, trigger evidence, promotion protocol, and validation blockers",
        ),
        (
            "ratewall_tdc_deposit_pass_through_trigger_validation_preflight.csv",
            "dynamic_assumption_mode",
            "Review-only TDC trigger-validation preflight joining scenario contracts, EA-TDC provenance, trigger blockers, and TDCSim contract context without enabling runtime selection",
        ),
        (
            "ratewall_tdc_deposit_pass_through_scenario_contract_invariant_audit.csv",
            "dynamic_assumption_mode",
            "Fail-closed invariant audit proving TDC source-import default-looking flags cannot override scenario-contract runtime/default blocks",
        ),
        (
            "ratewall_tdc_liquidity_regime_trigger_evidence.csv",
            "dynamic_assumption_mode",
            "Review-only EA-TDC liquidity-regime trigger evidence for TDC pass-through state dependence; not a runtime scenario selector",
        ),
        (
            "ratewall_tdc_liquidity_regime_trigger_promotion_protocol.csv",
            "dynamic_assumption_mode",
            "Fail-closed promotion-protocol requirement surface for any future TDC liquidity-regime trigger use",
        ),
        (
            "ratewall_tdc_liquidity_regime_trigger_validation_evidence.csv",
            "dynamic_assumption_mode",
            "Review-only validation evidence and blocker surface for TDC liquidity-regime trigger promotion fields",
        ),
        (
            "ratewall_dynamic_scenario_path_consistency_diagnostic.csv",
            "dynamic_assumption_mode",
            "Non-promotional configured-vs-growth-implied dynamic path consistency diagnostic",
        ),
        (
            "ratewall_dynamic_offset_ratio_path.csv",
            "dynamic_assumption_mode",
            "Period-by-period dynamic solves of the static Assumption Mode ratio under configured scenario paths",
        ),
        (
            "ratewall_scenario_crossing_diagnostic.csv",
            "dynamic_assumption_mode",
            "Scenario-implied crossing diagnostic; crossing periods are not empirical threshold dates",
        ),
        (
            "ratewall_dynamic_sensitivity_frontier.csv",
            "dynamic_assumption_mode",
            "Dynamic distance-to-wall frontier for countervailing totals, drag, and optional TDC liquidity-state add-ons",
        ),
        (
            "ratewall_dynamic_scenario_family_registry.csv",
            "dynamic_assumption_mode",
            "Dynamic scenario-family registry preserving static Assumption Mode v1 as the main classifier",
        ),
        (
            "ratewall_dynamic_uncertainty_envelope.csv",
            "dynamic_assumption_mode",
            "Source-gated final-period uncertainty variants over key dynamic path assumptions without prior narrowing",
        ),
        (
            "ratewall_dynamic_crossing_robustness.csv",
            "dynamic_assumption_mode",
            "Dynamic crossing robustness summary across configured uncertainty-envelope variants; not empirical threshold evidence",
        ),
        (
            "ratewall_flow_stage_decomposition.csv",
            "assumption_mode",
            "Mechanical cashflow, recipient-conversion, absorber, and attenuation stages",
        ),
        (
            "ratewall_gross_interest_subchannels.csv",
            "assumption_mode",
            "Gross Treasury, IORB, ON RRP/MMF, and remittance timing subchannels",
        ),
        (
            "ratewall_public_finance_adjustment.csv",
            "assumption_mode",
            "Fiscal, TGA, and remittance adjustment rows with staging basis",
        ),
        (
            "ratewall_net_countervailing_channels.csv",
            "assumption_mode",
            "Net additive countervailing and attenuation channels used in the numerator",
        ),
        (
            "ratewall_wall_hit_scenarios.csv",
            "assumption_mode",
            "Solved speculative RateWall wall-hit scenarios",
        ),
        (
            "ratewall_threshold_solver.csv",
            "assumption_mode",
            "Threshold solver answer rows for explicit assumptions",
        ),
        (
            "ratewall_assumption_sensitivity.csv",
            "assumption_mode",
            "Low/base/high handles for speculative assumption parameters",
        ),
        (
            "ratewall_parameter_frontier.csv",
            "assumption_mode",
            "One-parameter wall thresholds holding other assumptions fixed",
        ),
        (
            "ratewall_minimum_conditions_to_hit_wall.csv",
            "assumption_mode",
            "Minimum or maximum parameter conditions that would hit the wall",
        ),
        (
            "ratewall_hit_fragility_frontier.csv",
            "assumption_mode",
            "Reverse frontier showing how far hit assumptions can relax before non-hit",
        ),
        (
            "ratewall_frontier_driver_ranking.csv",
            "assumption_mode",
            "Ranked drivers nearest to each assumption set frontier",
        ),
        (
            "ratewall_assumption_mode_driver_dominance_matrix.csv",
            "assumption_mode",
            "Scenario-level driver dominance matrix linking ladder regimes, dominant components, frontier drivers, and fragility drivers without empirical promotion",
        ),
        (
            "ratewall_assumption_mode_pairwise_sensitivity_matrix.csv",
            "assumption_mode",
            "Pairwise Assumption Mode sensitivity matrix for top scenario drivers without empirical promotion or formula changes",
        ),
        (
            "ratewall_backend_invariant_guardrail_audit.csv",
            "assumption_mode",
            "Post-closure invariant audit proving closure, restricted-data, scenario, dynamic, and driver surfaces remain non-promotional",
        ),
        (
            "ratewall_backend_completion_verdict.csv",
            "assumption_mode",
            "Machine-readable current-backend completion verdict for the post-source-closure Assumption Mode phase",
        ),
        (
            "ratewall_paper_channel_map.csv",
            "paper_support_backend",
            "Paper-facing channel map with sign, evidence status, source-mode label, and disabled claim switches",
        ),
        (
            "ratewall_paper_canonical_scenario_results.csv",
            "paper_support_backend",
            "Canonical scenario-result table for paper drafting under Assumption Mode labels",
        ),
        (
            "ratewall_paper_tdc_dynamic_contribution.csv",
            "paper_support_backend",
            "TDC on/off dynamic contribution decomposition from existing dynamic rows",
        ),
        (
            "ratewall_paper_parameter_justification.csv",
            "paper_support_backend",
            "Parameter-pack justification table for explicit assumptions and source status",
        ),
        (
            "ratewall_paper_sensitivity_summary.csv",
            "paper_support_backend",
            "Sensitivity summary covering one-way frontiers, hit fragility, and pairwise residuals",
        ),
        (
            "ratewall_paper_disabled_claims_appendix.csv",
            "paper_support_backend",
            "Disabled-claims appendix preserving non-promotion boundaries for paper drafting",
        ),
        (
            "ratewall_paper_financialization_interpretation.csv",
            "paper_support_backend",
            "Sign-split financialization interpretation table for paper use; context/design only, not a composite index",
        ),
        (
            "ratewall_paper_support_invariant_audit.csv",
            "paper_support_backend",
            "Paper-support invariant audit for source-mode, completeness, and disabled-switch hygiene",
        ),
        (
            "ratewall_backend_accounting_identity_audit.csv",
            "paper_support_backend",
            "Numerical identity audit for displayed scenario ratios, component sums, TDC arithmetic, and dynamic boundaries",
        ),
        (
            "ratewall_paper_scenario_accounting_bridge.csv",
            "paper_support_backend",
            "Canonical scenario bridge linking numerator components and denominator drag pieces for paper traceability",
        ),
        (
            "ratewall_paper_dynamic_scenario_summary.csv",
            "paper_support_backend",
            "Dynamic scenario crossing and robustness summary under Assumption Mode boundaries",
        ),
        (
            "ratewall_conventional_drag_decomposition.csv",
            "assumption_mode",
            "Split-denominator conventional tightening component decomposition",
        ),
        (
            "ratewall_split_denominator_comparison.csv",
            "assumption_mode",
            "Scalar versus split-denominator RateWall classification comparison",
        ),
        (
            "ratewall_denominator_sensitivity.csv",
            "assumption_mode",
            "Denominator component sensitivity diagnostics",
        ),
        (
            "ratewall_split_denominator_uncertainty.csv",
            "assumption_mode",
            "Low/base/high split-denominator component stress diagnostics",
        ),
        (
            "ratewall_split_denominator_regime_stability.csv",
            "assumption_mode",
            "Regime stability across scalar, split, and denominator stress modes",
        ),
        (
            "ratewall_denominator_literature_matrix.csv",
            "assumption_mode",
            "Evidence-prior matrix for split-denominator channels",
        ),
        (
            "ratewall_split_denominator_joint_uncertainty.csv",
            "assumption_mode",
            "Joint split-denominator stress diagnostics",
        ),
        (
            "ratewall_split_denominator_joint_regime_stability.csv",
            "assumption_mode",
            "Regime stability across scalar, split, one-component, and joint stress modes",
        ),
        (
            "ratewall_denominator_classifier_comparison.csv",
            "assumption_mode",
            "Compact scalar, split, one-component, and joint classifier comparison",
        ),
        (
            "ratewall_backend_model_readiness_gate.csv",
            "assumption_mode",
            "Backend model-audit readiness gate that blocks writing and empirical promotion",
        ),
        (
            "ratewall_chapter_readiness_self_audit.csv",
            "assumption_mode",
            "Internal self-audit deciding whether another external audit is needed before chapter drafting",
        ),
        (
            "ratewall_financialized_balance_sheet_channel.csv",
            "assumption_mode",
            "Legacy optional pro-forma financialized balance-sheet amplifier channel; diagnostic only, not a financialization index",
        ),
        (
            "ratewall_financialization_proxy_registry.csv",
            "assumption_mode",
            "Sign-separated financialization proxy registry with closer-to-wall, farther-from-wall, and two-sided mechanism labels",
        ),
        (
            "ratewall_household_safe_asset_capture_proxy.csv",
            "financialization_proxy_context_design",
            "Context-only household safe-asset capture proxy surface",
        ),
        (
            "ratewall_household_safe_asset_exposure_panel.csv",
            "financialization_proxy_context_design",
            "Context-only household safe-asset exposure panel",
        ),
        (
            "ratewall_household_safe_asset_access_context.csv",
            "financialization_proxy_context_design",
            "Context-only household safe-asset access surface",
        ),
        (
            "ratewall_retail_safe_yield_access_substitution_context.csv",
            "financialization_proxy_context_design",
            "Context-only retail safe-yield access substitution surface",
        ),
        (
            "ratewall_retail_deposit_beta_gap_context.csv",
            "financialization_proxy_context_design",
            "Context-only retail deposit beta gap surface",
        ),
        (
            "ratewall_retail_pass_through_dispersion_panel.csv",
            "financialization_proxy_context_design",
            "Context-only retail pass-through dispersion panel",
        ),
        (
            "ratewall_deposit_competition_conditioner.csv",
            "financialization_proxy_context_design",
            "Context-only deposit competition conditioner surface",
        ),
        (
            "ratewall_deposit_mmf_substitution_surface.csv",
            "financialization_proxy_context_design",
            "Context-only deposit/MMF substitution surface",
        ),
        (
            "ratewall_personal_net_interest_position_context.csv",
            "financialization_proxy_context_design",
            "Context-only personal net-interest position surface",
        ),
        (
            "ratewall_firm_liquid_asset_public_context.csv",
            "financialization_proxy_context_design",
            "Context-only firm liquid-asset public context",
        ),
        (
            "ratewall_firm_liquid_asset_cushion_panel.csv",
            "financialization_proxy_context_design",
            "Context-only firm liquid-asset cushion panel",
        ),
        (
            "ratewall_firm_net_interest_cushion_context.csv",
            "financialization_proxy_context_design",
            "Context-only firm net-interest cushion surface",
        ),
        (
            "ratewall_firm_rollover_pressure_panel.csv",
            "financialization_proxy_context_design",
            "Context-only firm rollover-pressure panel",
        ),
        (
            "ratewall_firm_short_rate_exposure_proxy.csv",
            "financialization_proxy_context_design",
            "Context-only firm short-rate exposure proxy",
        ),
        (
            "ratewall_household_borrower_fragility_context.csv",
            "financialization_proxy_context_design",
            "Context-only household borrower fragility surface",
        ),
        (
            "ratewall_bank_loan_repricing_context.csv",
            "financialization_proxy_context_design",
            "Context-only bank loan repricing surface",
        ),
        (
            "ratewall_cre_refinancing_public_context.csv",
            "financialization_proxy_context_design",
            "Context-only CRE refinancing public context",
        ),
        (
            "ratewall_private_credit_bdc_context.csv",
            "financialization_proxy_context_design",
            "Context-only private-credit BDC context",
        ),
        (
            "ratewall_safe_yield_paired_proxy_surface.csv",
            "financialization_proxy_context_design",
            "Context-only safe-yield paired proxy surface",
        ),
        (
            "ratewall_financialization_proxy_source_gate.csv",
            "assumption_mode",
            "Fail-closed source-gate audit for financialization proxy promotion boundaries",
        ),
        (
            "ratewall_financialization_source_gate.csv",
            "assumption_mode",
            "Compatibility alias for the financialization proxy source-gate audit",
        ),
        (
            "ratewall_financialization_restricted_protocols.csv",
            "assumption_mode",
            "Restricted/licensed-data protocol docket for financialization proxy promotion designs",
        ),
        (
            "ratewall_financialization_double_count_audit.csv",
            "assumption_mode",
            "Double-count guardrail audit for financialization proxy overlap with existing RateWall channels",
        ),
        (
            "ratewall_financialization_overlap_audit.csv",
            "assumption_mode",
            "Alias overlap audit mirroring the double-count guardrail coverage for every financialization proxy",
        ),
        (
            "ratewall_financialization_artifact_traceability_matrix.csv",
            "assumption_mode",
            "Proxy-level traceability matrix tying registry rows to source gates, context artifacts, audits, and release discoverability",
        ),
        (
            "ratewall_backend_expansion_context_registry.csv",
            "assumption_mode",
            "Registry for external review financialization-expansion and additional-rate-channel context surfaces; non-promotional",
        ),
        (
            "ratewall_assumption_mode_channel_promotion_decision.csv",
            "assumption_mode",
            "Decision ledger separating Assumption Mode promoted terms, restricted-data rows, context-only rows, and avoid rows",
        ),
        (
            "ratewall_assumption_mode_promoted_channel_contributions.csv",
            "assumption_mode",
            "Scenario-level contribution table for optional Assumption Mode promoted financialization terms entering the ratio under explicit assumptions",
        ),
        (
            "ratewall_assumption_mode_overlap_guardrail_audit.csv",
            "assumption_mode",
            "Guardrail table preventing legacy generic safe-yield and firm-cash terms from silently stacking with explicit Assumption Mode modules",
        ),
        (
            "ratewall_assumption_mode_recipient_conversion_overlap_audit.csv",
            "assumption_mode",
            "Audit of explicit safe-yield/MMF offsets against canonical recipient-demand conversion terms",
        ),
        (
            "ratewall_assumption_mode_sidecar_channel_decision.csv",
            "assumption_mode",
            "Decision ledger for sidecar-only and dynamic-only Assumption Mode channels kept outside the canonical ratio",
        ),
        (
            "ratewall_assumption_mode_sidecar_contributions.csv",
            "assumption_mode",
            "Scenario-level sidecar contribution table for recipient-leakage, denominator-sidecar, and institutional-lag sensitivities",
        ),
        (
            "ratewall_assumption_mode_sidecar_reasonableness_audit.csv",
            "assumption_mode",
            "Magnitude and overlap-discount audit for sidecar-only Assumption Mode sensitivities",
        ),
        (
            "ratewall_assumption_mode_sidecar_frontier.csv",
            "assumption_mode",
            "Ranked frontier of secondary sidecar ratio movements versus the canonical ratio",
        ),
        (
            "ratewall_assumption_mode_sidecar_bundle_frontier.csv",
            "assumption_mode",
            "Guarded static-only sidecar bundle frontier preserving canonical ratio and classifier labels",
        ),
        (
            "ratewall_assumption_mode_sidecar_driver_decomposition.csv",
            "assumption_mode",
            "Channel-level decomposition of static sidecar interpretation drivers",
        ),
        (
            "ratewall_assumption_mode_dynamic_sidecar_driver_decomposition.csv",
            "assumption_mode",
            "Periodwise decomposition of dynamic-only sidecar variants kept outside canonical dynamic paths",
        ),
        (
            "ratewall_assumption_mode_dynamic_sidecar_paths.csv",
            "assumption_mode",
            "Dynamic-only sidecar path table that does not alter existing dynamic ratio or crossing classifications",
        ),
        (
            "ratewall_assumption_mode_dynamic_sidecar_family_summary.csv",
            "backend_expansion_context_design",
            "Scenario/family/variant summary of dynamic-only sidecar paths with peak, cumulative, nonzero-window, and shape diagnostics",
        ),
        (
            "ratewall_assumption_mode_dynamic_sidecar_secondary_paths.csv",
            "backend_expansion_context_design",
            "Period-level noncanonical secondary overlay diagnostics for eligible dynamic sidecars, with public-finance reapplication blocked",
        ),
        (
            "ratewall_assumption_mode_dynamic_sidecar_secondary_frontier.csv",
            "backend_expansion_context_design",
            "Scenario-level frontier of constructible dynamic sidecar secondary overlays, preserving canonical dynamic paths and classifier labels",
        ),
        (
            "ratewall_assumption_mode_parameter_activation_ledger.csv",
            "assumption_mode",
            "Scenario-parameter ledger showing pack coverage, activation status, layer placement, and zero-default invariance",
        ),
        (
            "ratewall_assumption_mode_channel_status_crosswalk.csv",
            "backend_expansion_context_design",
            "Machine-readable crosswalk connecting context, proxy, promotion, sidecar, dynamic, avoid, and final interpretation status",
        ),
        (
            "ratewall_assumption_mode_formula_identity_audit.csv",
            "assumption_mode",
            "Arithmetic identity audit for promoted Assumption Mode static terms, static sidecars, secondary ratios, and contribution-table bridges",
        ),
        (
            "ratewall_assumption_source_backing_ledger.csv",
            "backend_expansion_context_design",
            "Central source-backing class ledger for assumption handles and sibling scenario inputs",
        ),
        (
            "ratewall_assumption_source_backing_invariant_audit.csv",
            "backend_expansion_context_design",
            "Invariant audit for source-backing coverage, nonpromotion, and disabled forbidden switches",
        ),
        (
            "ratewall_qrawatch_tdcsim_scenario_registry.csv",
            "backend_expansion_context_design",
            "Fail-closed QRA Watch to TDCSim scenario-contract registry",
        ),
        (
            "ratewall_qrawatch_tdcsim_provenance_audit.csv",
            "backend_expansion_context_design",
            "Source-backing provenance audit for QRA Watch scenario inputs",
        ),
        (
            "ratewall_qrawatch_tdcsim_bridge_invariant_audit.csv",
            "backend_expansion_context_design",
            "Invariant audit for QRA Watch/TDCSim bridge disabled runtime switches",
        ),
        (
            "ratewall_generated_text_claim_boundary_scan.csv",
            "backend_expansion_context_design",
            "Generated-text claim-boundary lint for Markdown, CSV, and JSON artifacts with local boundary allowlists",
        ),
        (
            "ratewall_backend_surface_schema_contract.csv",
            "backend_expansion_context_design",
            "Generated-surface schema contract rejecting duplicate headers, pandas suffixes, promotion-sensitive leakage, and prompt-sourced numeric evidence",
        ),
        (
            "ratewall_backend_artifact_claim_boundary_manifest.csv",
            "backend_expansion_context_design",
            "Artifact claim-boundary and release-layer manifest proving review-only surfaces are not empirical estimates",
        ),
        (
            "ratewall_release_archive_reproducibility_audit.csv",
            "backend_expansion_context_design",
            "Release manifest and source-archive reproducibility audit with hashes, row counts, and archive membership checks",
        ),
        (
            "ratewall_restricted_protocol_falsification_matrix.csv",
            "assumption_mode",
            "Restricted-data design matrix for sample frame, timing, falsification, representativeness, promotion discipline, and abandonment rules",
        ),
        (
            "ratewall_restricted_protocol_field_contract.csv",
            "assumption_mode",
            "Field-level restricted-protocol schema contract expanding every required gate field while remaining design-only and fail-closed",
        ),
        (
            "ratewall_context_surface_no_main_ratio_audit.csv",
            "backend_expansion_context_design",
            "Artifact-level audit proving noncanonical context, protocol, sidecar, dynamic, and audit surfaces remain outside canonical mechanics",
        ),
        (
            "ratewall_conventional_drag_bounded_denominator_registry.csv",
            "backend_expansion_context_design",
            "Interval-first bounded h8 denominator registry using the weak-IV-safe h8 interval as the primary noncanonical object and proxy-IV center as review-only overlay context",
        ),
        (
            "ratewall_denominator_methodology_registry.csv",
            "backend_expansion_context_design",
            "Route registry separating the bounded h8 empirical overlay lane, the default literature-backed annual-flow runtime family, legacy sensitivity-only assumption anchors, and the FRB/US benchmark role",
        ),
        (
            "ratewall_annual_flow_denominator_anchor_registry.csv",
            "assumption_mode",
            "Annual-flow denominator-anchor registry recording the promoted literature runtime anchor, legacy sensitivity-only counterpoints, and an explicit non-anchor h8 overlay row",
        ),
        (
            "ratewall_annual_flow_runtime_family_registry.csv",
            "assumption_mode",
            "Runtime annual-flow denominator-family registry centering default runtime policy on the literature-backed h4 endpoint proxy with explicit CI and keeping legacy assumption-mode rows as sensitivity-only counterpoints",
        ),
        (
            "ratewall_annual_support_denominator_compatibility_registry.csv",
            "backend_expansion_context_design",
            "Compatibility registry distinguishing the default empirical annual-flow runtime pairing, legacy sensitivity-only annual-flow pairings, and non-commensurate cumulative-h8 overlay lanes",
        ),
        (
            "ratewall_annual_support_numerator_component_registry.csv",
            "assumption_mode",
            "Scenario-level annual-support numerator component registry separating direct runtime terms from memo, subtotal, and overlap-guard rows under the adopted annual-flow runtime architecture",
        ),
        (
            "ratewall_annual_support_numerator_source_gate.csv",
            "assumption_mode",
            "Component-level source, timing, memo/direct, and uncertainty classification gate for the runtime annual-flow numerator under the frozen denominator architecture",
        ),
        (
            "ratewall_annual_support_numerator_component_rollup.csv",
            "assumption_mode",
            "Component-family rollup proving direct annual-support numerator terms are included once while memo, subtotal, overlap, and total-identity rows remain excluded",
        ),
        (
            "ratewall_annual_support_numerator_contract.csv",
            "assumption_mode",
            "Fail-closed runtime numerator contract that reconciles direct current-window support components to the live annual-flow numerator total used in scenario support-offset calculations",
        ),
        (
            "ratewall_annual_support_numerator_uncertainty_envelope.csv",
            "assumption_mode",
            "Contract-level numerator-only uncertainty envelope built from the observed MPC-family runtime projection range for each year, maturity, and holder path",
        ),
        (
            "ratewall_annual_support_numerator_contract_invariant_audit.csv",
            "assumption_mode",
            "Invariant audit proving direct-component reconciliation, memo exclusion, and runtime admission for each annual-flow numerator contract row before runtime support-offset outputs are emitted",
        ),
        (
            "ratewall_runtime_annual_flow_support_offset_scenarios.csv",
            "assumption_mode",
            "Scenario-facing runtime annual-flow support-offset surface using the literature-backed denominator family as default, legacy anchors as sensitivity-only, and h8-family rows as blocked non-commensurate context; numeric outputs now require both numerator admission and denominator compatibility",
        ),
        (
            "ratewall_runtime_annual_flow_support_offset_readiness_registry.csv",
            "assumption_mode",
            "One-row-per-scenario readiness registry carrying numerator reconciliation, timing, uncertainty, denominator compatibility, and effective runtime admission for the annual-flow support-offset surface",
        ),
        (
            "ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv",
            "assumption_mode",
            "Compact one-row-per-contract adoption matrix carrying the default literature runtime row, explicit legacy sensitivity rows, and blocked h8-family overlay companions for annual-flow support-offset use",
        ),
        (
            "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv",
            "assumption_mode",
            "Compact year-level runtime support-offset frontier summary covering the default literature family plus explicit legacy sensitivity families with deterministic reference-case lineage",
        ),
        (
            "ratewall_runtime_annual_flow_support_offset_closeout_decision.csv",
            "assumption_mode",
            "Machine-readable closeout row stating that the compact annual-flow runtime support-offset layer is release-grade as a noncanonical diagnostic and recording the exact narrow reopen triggers",
        ),
        (
            "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv",
            "assumption_mode",
            "Compact benchmark-context overlay joining the default literature runtime row, legacy sensitivity rows, bounded h8 review-only interval context, and FRB/US benchmark-only points by forecast year",
        ),
        (
            "ratewall_ratio_object_registry.csv",
            "backend_expansion_context_design",
            "Object-split registry separating legacy static Assumption Mode, fixed annual-flow runtime, forecast/TDC-family, policy-path review-only, historical/forecast path-ratio, and state-distance objects",
        ),
        (
            "ratewall_active_output_index.csv",
            "backend_expansion_context_design",
            "Active output index assigning each live static, runtime, forecast, policy-path review, and registry artifact to an object family, denominator status, and admitted-use boundary",
        ),
        (
            "ratewall_paper_core_results_index.csv",
            "backend_expansion_context_design",
            "Compact paper-core results index classifying headline, sensitivity, guardrail, diagnostic, backend, and legacy outputs by admitted claim use",
        ),
        (
            "ratewall_reference_scenario_object_crosswalk.csv",
            "backend_expansion_context_design",
            "Reference-case crosswalk showing current values for the legacy static Assumption Mode lane, empirical runtime annual-flow lane, forecast interest-only lane, forecast TDC-family lane, and bounded H.8 review-only overlay",
        ),
        (
            "ratewall_joint_wall_probability_axis_registry.csv",
            "backend_expansion_context_design",
            "Registry of the named scenario axes and probability-claim boundary used by the conditional wall-hit grid",
        ),
        (
            "ratewall_joint_wall_probability_surface.csv",
            "backend_expansion_context_design",
            "Deterministic conditional wall-hit surface that keeps runtime annual-flow, forecast TDC-family, and forecast beta-sensitivity rows in separate object families",
        ),
        (
            "ratewall_joint_wall_probability_summary.csv",
            "backend_expansion_context_design",
            "Compact conditional named-grid wall-hit shares by object family and support variant, with empirical and posterior probability claims disabled",
        ),
        (
            "ratewall_wall_denominator_path_contract.csv",
            "backend_expansion_context_design",
            "Naming-discipline denominator contract that keeps the fixed runtime anchor live only for runtime rows and blocks silent reuse as the primary historical or forecast wall denominator",
        ),
        (
            "ratewall_path_ratio_numerator_ledger.csv",
            "backend_expansion_context_design",
            "Shared historical and forecast path-ratio numerator ledger separating direct versus memo components, timing roles, overlap buckets, and TDC lineage without altering the fixed runtime support-offset layer",
        ),
        (
            "ratewall_path_ratio_numerator_reconciliation_audit.csv",
            "backend_expansion_context_design",
            "Row-level reconciliation audit proving each shared path-ratio numerator ledger bundle sums its direct components to the reported historical or forecast numerator total",
        ),
        (
            "ratewall_tdc_overlap_audit.csv",
            "backend_expansion_context_design",
            "Explicit TDC overlap identity audit showing where direct-interest overlap is subtracted before demand conversion and where historical reduced-form TDC rows still lack overlap-level proof",
        ),
        (
            "ratewall_path_ratio_denominator_v1.csv",
            "backend_expansion_context_design",
            "Row-level denominator v1 surface for historical and forecast path-ratio work, exposing fixed anchor, explicit exposure fields, repricing fields, and near-zero guards without altering the runtime annual-flow layer",
        ),
        (
            "ratewall_path_ratio_tdc_adjustment_layer.csv",
            "backend_expansion_context_design",
            "Shared historical-versus-forecast TDC adjustment layer that standardizes overlap-proofed forecast TDC rows against reduced-form historical TDC comparison rows without promoting either into canonical runtime use",
        ),
        (
            "ratewall_historical_incremental_path_ratio.csv",
            "backend_expansion_context_design",
            "Default historical incremental path-ratio surface using the shared numerator ledger plus denominator v1, with near-zero transition guards that keep low-rate contexts from silently acting as headline wall-hit rows",
        ),
        (
            "ratewall_historical_incremental_path_ratio_tdc_comparison.csv",
            "backend_expansion_context_design",
            "Historical TDC comparison surface that joins default historical path-ratio rows to reduced-form historical TDC sidecars while keeping overlap-unproved adjustments non-headline and non-additive",
        ),
        (
            "ratewall_forecast_incremental_path_ratio.csv",
            "backend_expansion_context_design",
            "Default forecast incremental path-ratio surface using the annual holder-plus-TDC numerator bridge plus denominator v1, with explicit debt-share and repricing lineage and legacy comparison references kept non-headline",
        ),
        (
            "ratewall_forecast_incremental_path_ratio_tdc_comparison.csv",
            "backend_expansion_context_design",
            "Forecast TDC comparison surface that decomposes default forecast path-ratio rows into overlap-proofed no-TDC and TDC-delta components while keeping quarterly interest-only sidecars reference-only",
        ),
        (
            "ratewall_forecast_path_ratio_scenario_registry.csv",
            "backend_expansion_context_design",
            "Forecast scenario registry that makes the default path-ratio grid explicit across calibrated channel-conversion profiles, repricing path, holder mix, TDC path context, and denominator lineage",
        ),
        (
            "ratewall_forecast_channel_conversion_profile_registry.csv",
            "backend_expansion_context_design",
            "Forecast channel-conversion profile registry defining conservative, base, and demand-active Treasury-recipient, TDC ex-overlap, and bank-margin conversion bundles without promoting canonical incidence claims",
        ),
        (
            "ratewall_forecast_assumption_calibration_registry.csv",
            "backend_expansion_context_design",
            "Forecast assumption-calibration registry that materializes channel-conversion and deposit-pass-through parameter families with evidence class, admission status, and blocked-claim discipline",
        ),
        (
            "ratewall_forecast_assumption_bundle_registry.csv",
            "backend_expansion_context_design",
            "Forecast assumption-bundle registry linking each scenario row to its calibrated channel-conversion profile, holder mix, repricing path, and pass-through materialization status",
        ),
        (
            "ratewall_forecast_scenario_product_summary.csv",
            "backend_expansion_context_design",
            "Compact forecast scenario-product summary showing by year and calibrated assumption profile which bundle gets closest to the wall, which component dominates, and which assumption axis is doing the work",
        ),
        (
            "ratewall_forecast_treasury_recipient_calibration_registry.csv",
            "backend_expansion_context_design",
            "Treasury-recipient calibration registry that turns leakage and timing review context into explicit low, base, and high assumption overlays without promoting a source-closed beneficial-owner bridge",
        ),
        (
            "ratewall_forecast_treasury_recipient_calibration_comparison.csv",
            "backend_expansion_context_design",
            "Scenario-level Treasury calibration comparison surface showing how low, base, and high leakage or timing assumptions change only the Treasury support leg, numerator, ratio, and remaining gap while keeping TDC, pass-through, holder, and maturity axes fixed",
        ),
        (
            "ratewall_forecast_treasury_recipient_calibration_product_summary.csv",
            "backend_expansion_context_design",
            "Compact Treasury calibration product summary showing by year, channel-conversion profile, and Treasury calibration band which scenario gets closest to the wall under low, base, and high Treasury leakage or timing assumptions",
        ),
        (
            "ratewall_forecast_treasury_recipient_calibration_consumer_summary.csv",
            "backend_expansion_context_design",
            "Compact Treasury calibration consumer summary collapsing low, base, and high Treasury leakage or timing overlays into one year-profile row with ratio spread, remaining-gap spread, and frontier-stability status",
        ),
        (
            "ratewall_forecast_bank_margin_sidecar_summary.csv",
            "backend_expansion_context_design",
            "Forecast bank-margin sidecar summary showing that the best-scenario bank retained-margin lane remains explicitly non-depositor and subordinate relative to Treasury and TDC components unless future evidence changes its role",
        ),
        (
            "ratewall_forecast_path_ratio_decomposition.csv",
            "backend_expansion_context_design",
            "Direct-component decomposition surface for forecast path-ratio scenarios translating domestic nonbank interest support, bank retained margin support, and TDC current-demand support into component-level ratio contributions",
        ),
        (
            "ratewall_forecast_path_ratio_numerator_boundary_registry.csv",
            "backend_expansion_context_design",
            "Forecast numerator-boundary registry that separates recipient basis, leakage treatment, bank-retained-margin interpretation, and unmaterialized deposit-pass-through status across the default forecast path-ratio scenarios",
        ),
        (
            "ratewall_forecast_path_ratio_interpretation_registry.csv",
            "backend_expansion_context_design",
            "Forecast interpretation registry that ties each default forecast numerator component to source-backed context, assumption-only conversion status, and exact interpretation blockers without promoting depositor pass-through or canonical ratio claims",
        ),
        (
            "ratewall_forecast_path_ratio_recipient_leakage_registry.csv",
            "backend_expansion_context_design",
            "Forecast recipient-leakage registry that maps treasury-interest and bank-margin forecast components onto the existing leakage design gates, timing requirements, prior-narrowing decisions, and fail-closed evidence blockers without changing scenario math",
        ),
        (
            "ratewall_forecast_path_ratio_sensitivity_summary.csv",
            "backend_expansion_context_design",
            "Forecast sensitivity summary that measures how each year’s reference path-ratio row moves when MPC/current-demand, repricing, or holder-mix axes change one at a time",
        ),
        (
            "ratewall_forecast_path_ratio_scenario_frontier.csv",
            "backend_expansion_context_design",
            "Ranked forecast scenario frontier table exposing within-year and overall closest-to-wall ordering with linked dominant direct components and TDC adjustment lineage",
        ),
        (
            "ratewall_forecast_path_ratio_driver_ranking.csv",
            "backend_expansion_context_design",
            "Forecast driver-ranking surface that turns one-axis sensitivity rows into ranked closeness-to-wall drivers while separating numerator-only from mixed numerator-and-denominator movements",
        ),
        (
            "ratewall_forecast_path_ratio_driver_dominance_matrix.csv",
            "backend_expansion_context_design",
            "Year-level forecast driver-dominance matrix summarizing the strongest driver axis, its setting, and whether the closest-to-wall frontier scenario adopts that setting",
        ),
        (
            "ratewall_forecast_path_ratio_consumer_ladder.csv",
            "backend_expansion_context_design",
            "Compact forecast consumer ladder keeping each year’s top three closest-to-wall scenarios plus the reference scenario, with linked dominant-component interpretation boundaries and reportability status",
        ),
        (
            "ratewall_forecast_path_ratio_consumer_driver_summary.csv",
            "backend_expansion_context_design",
            "Compact year-level forecast driver summary carrying the dominant closeness-to-wall axis together with the matched-setting and frontier interpretation boundaries",
        ),
        (
            "ratewall_forecast_path_ratio_consumer_interpretation_summary.csv",
            "backend_expansion_context_design",
            "Compact forecast interpretation summary for reference and frontier scenarios, preserving source-backed-context-versus-assumption-only boundaries component by component without materializing deposit pass-through",
        ),
        (
            "ratewall_forecast_path_ratio_source_specific_interpretation_registry.csv",
            "backend_expansion_context_design",
            "Forecast component-level source-specific interpretation registry that distinguishes treasury holder-context richness from missing domestic recipient bridges, bank reserve/deposit-pricing context from missing bank-behavior bridges, and stable TDC overlap-only context from external recipient-leakage targets",
        ),
        (
            "ratewall_forecast_path_ratio_evidence_dependency_matrix.csv",
            "backend_expansion_context_design",
            "Year-level closest-to-wall dependency matrix linking the base and explicit-pass-through top1 forecast frontier rows to the treasury, bank-margin, or TDC-specific missing bridge that currently governs their interpretation",
        ),
        (
            "ratewall_forecast_path_ratio_evidence_targeting_registry.csv",
            "backend_expansion_context_design",
            "Compact forecast evidence-targeting registry summarizing which source-specific treasury or bank bridge is unresolved, how many forecast rows it affects, and how often the closest-to-wall frontier depends on it",
        ),
        (
            "ratewall_forecast_path_ratio_evidence_work_queue.csv",
            "backend_expansion_context_design",
            "Ordered forecast evidence work queue ranking the next treasury-recipient, bank-behavior, and TDC-boundary tasks by current frontier dependence and actionability",
        ),
        (
            "ratewall_forecast_treasury_recipient_bridge_packet.csv",
            "backend_expansion_context_design",
            "Machine-readable treasury bridge packet that packages current frontier dependence, holder and MMF context, missing domestic-recipient and spending-timing evidence, and the fail-closed design gate before any Treasury-interest prior narrowing",
        ),
        (
            "ratewall_forecast_treasury_recipient_source_targeting_matrix.csv",
            "backend_expansion_context_design",
            "Treasury-recipient source-targeting matrix that maps the frontier-binding bridge packet to TDC-EST cashflow basis, Z.1 holder context, TIC foreign leakage, MMF portfolio context, TDCSim funding-route gaps, and the fail-closed blocked uses for each evidence family",
        ),
        (
            "ratewall_forecast_bank_behavior_bridge_packet.csv",
            "backend_expansion_context_design",
            "Machine-readable bank behavior bridge packet that packages reserve and deposit-pricing context, missing deposit-beta and bank-distribution evidence, and the fail-closed design gate before any bank-margin prior narrowing",
        ),
        (
            "ratewall_forecast_treasury_beneficial_owner_recipient_bridge.csv",
            "backend_expansion_context_design",
            "Stage-by-stage forecast treasury bridge artifact that ties the frontier-binding Treasury packet to gross-cashflow basis, domestic/private holder context, foreign leakage, MMF intermediation, Fed remittance routing, and the fail-closed current-demand bridge gate",
        ),
        (
            "ratewall_forecast_treasury_recipient_best_proxy_basis.csv",
            "backend_expansion_context_design",
            "Treasury-recipient best-proxy basis table that links each source-targeting row to the bridge stage it can support, separating TDC-EST cashflow basis and Z.1/TIC/MMF context from blocked current-demand, final-recipient, and canonical runtime uses",
        ),
        (
            "ratewall_forecast_treasury_recipient_best_proxy_admission_review.csv",
            "backend_expansion_context_design",
            "Treasury-recipient best-proxy admission review that admits TDC-EST cashflow and Z.1/TIC/MMF/Fed context only for noncanonical bridge scaffolding while keeping prior narrowing, final-recipient incidence, and canonical runtime use blocked",
        ),
        (
            "ratewall_forecast_treasury_recipient_best_proxy_calculation_scaffold.csv",
            "backend_expansion_context_design",
            "Treasury-recipient best-proxy calculation scaffold that carries the admitted TDC-EST gross cashflow input while preserving Z.1/TIC/MMF/Fed context as non-amount scaffolding and blocking recipient-demand conversion",
        ),
        (
            "ratewall_forecast_treasury_recipient_best_proxy_gate_review.csv",
            "backend_expansion_context_design",
            "Treasury-recipient best-proxy gate review that records cashflow/context-only bridge passes while keeping current-demand conversion, prior narrowing, final-recipient incidence, and canonical runtime use fail-closed",
        ),
        (
            "ratewall_forecast_treasury_recipient_current_demand_evidence_contract.csv",
            "backend_expansion_context_design",
            "Treasury-recipient current-demand evidence contract that enumerates the admissible evidence needed before gross TDC-EST cashflow can become noncanonical current-demand support while preserving runtime, incidence, welfare, pricing, holder-allocation, and prior-narrowing blocks",
        ),
        (
            "ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy.csv",
            "backend_expansion_context_design",
            "Noncanonical assumption-mode Treasury-recipient sidecar that route-weights the domestic-nonbank cashflow envelope with Z.1 sector context and SEC N-MFP MMF splits while keeping current-demand evidence gates fail-closed",
        ),
        (
            "ratewall_forecast_bank_behavior_distribution_bridge.csv",
            "backend_expansion_context_design",
            "Stage-by-stage forecast bank bridge artifact that ties the bank packet to gross IORB basis, reserve and deposit-pricing context, bank intermediation context, and the fail-closed bank behavior/current-demand gate",
        ),
        (
            "ratewall_forecast_bank_behavior_current_demand_evidence_contract.csv",
            "backend_expansion_context_design",
            "Bank behavior current-demand evidence contract that records what evidence would be needed to move retained-margin support while keeping reserve income separate from depositor cashflow and preserving fail-closed claim gates",
        ),
        (
            "ratewall_final_recipient_current_demand_bridge_attempt.csv",
            "backend_expansion_context_design",
            "Narrow source-backed bridge-attempt result joining Treasury and bank current-demand contracts to actual source-scan counts, exact missing fields, and the fail-closed next-field queue",
        ),
        (
            "ratewall_treasury_recipient_source_contract_path.csv",
            "backend_expansion_context_design",
            "Treasury-recipient source-contract path that separates exhausted local cashflow, holder, MMF, TIC, and TDCSim context from the true source-owned final-recipient current-demand panel reopen trigger",
        ),
        (
            "ratewall_treasury_recipient_current_demand_proxy_scaffold.csv",
            "backend_expansion_context_design",
            "Treasury-recipient current-demand proxy scaffold that records route taxonomy, candidate public and restricted sources, inferred fields, and validation/nonadditivity checks without admitting current-demand support",
        ),
        (
            "ratewall_bank_behavior_bridge_source_contract_queue.csv",
            "backend_expansion_context_design",
            "Bank-behavior source-contract queue that ranks the missing IORB retention, depositor timing, borrower response, and nonadditivity evidence required before retained-margin support can become any current-demand bridge",
        ),
        (
            "ratewall_bank_behavior_rank1_source_contract_path.csv",
            "backend_expansion_context_design",
            "Bank-behavior rank-1 source-contract path that separates exhausted local public context from public aggregate extensions and the true source-owned IORB/depositor timing panel reopen trigger",
        ),
        (
            "ratewall_forecast_treasury_beneficial_owner_recipient_bridge_basis.csv",
            "backend_expansion_context_design",
            "Forecast treasury bridge-basis surface that links the treasury stage bridge to current public context, restricted-data gate specifications, and falsification rules for domestic-recipient, foreign-recycling, MMF, and tax-timing basis work without narrowing priors",
        ),
        (
            "ratewall_forecast_bank_behavior_distribution_bridge_basis.csv",
            "backend_expansion_context_design",
            "Forecast bank bridge-basis surface that links the bank stage bridge to gross IORB basis, deposit-beta and bank intermediation context, and the fail-closed design gate before any bank behavior/current-demand prior narrowing",
        ),
        (
            "ratewall_forecast_treasury_beneficial_owner_recipient_mapping_basis.csv",
            "backend_expansion_context_design",
            "Forecast treasury mapping-basis surface that turns the treasury bridge-basis layer into explicit public-context, restricted-data, falsification, and fail-closed eligibility rows showing what can and cannot be said now about beneficial-owner and domestic-recipient mapping",
        ),
        (
            "ratewall_forecast_bank_behavior_distribution_mapping_basis.csv",
            "backend_expansion_context_design",
            "Forecast bank mapping-basis surface that turns the bank bridge-basis layer into explicit public-context and fail-closed eligibility rows showing what can and cannot be said now about bank behavior and distribution mapping",
        ),
        (
            "ratewall_forecast_treasury_beneficial_owner_recipient_admission_candidate.csv",
            "backend_expansion_context_design",
            "Forecast treasury admission-candidate surface that turns the treasury mapping-basis rows into explicit public-only, restricted-data, and full-bridge-pass counterfactual statuses while keeping prior narrowing blocked",
        ),
        (
            "ratewall_forecast_bank_behavior_distribution_admission_candidate.csv",
            "backend_expansion_context_design",
            "Forecast bank admission-candidate surface that turns the bank mapping-basis rows into explicit public-only and full-bridge-pass counterfactual statuses while keeping depositor relabeling and prior narrowing blocked",
        ),
        (
            "ratewall_forecast_treasury_beneficial_owner_recipient_bridge_pass_review.csv",
            "backend_expansion_context_design",
            "Forecast treasury bridge-pass review surface that turns treasury admission candidates into explicit review-pass, restricted-design blocker, and fail-closed closeout rows without authorizing prior narrowing",
        ),
        (
            "ratewall_forecast_bank_behavior_distribution_bridge_pass_review.csv",
            "backend_expansion_context_design",
            "Forecast bank bridge-pass review surface that turns bank admission candidates into explicit review-pass and fail-closed closeout rows without relabeling bank-margin support as depositor cashflow",
        ),
        (
            "ratewall_forecast_path_ratio_pass_through_scenario_axis.csv",
            "backend_expansion_context_design",
            "Scenario-only deposit pass-through axis for forecast path-ratio work, built from source-backed and explicitly diagnostic pass-through estimates while keeping runtime selector promotion blocked",
        ),
        (
            "ratewall_forecast_path_ratio_pass_through_scenario_registry.csv",
            "backend_expansion_context_design",
            "Expanded forecast path-ratio scenario registry that cross-joins the validated base forecast grid with explicit deposit pass-through beta assumptions and rescales the full TDC deposit-balance leg",
        ),
        (
            "ratewall_forecast_path_ratio_pass_through_scenario_frontier.csv",
            "backend_expansion_context_design",
            "Ranked explicit-pass-through forecast frontier table exposing which combinations of MPC, repricing, holder mix, and deposit beta assumptions move each year closest to the wall",
        ),
        (
            "ratewall_critical_beta_frontier.csv",
            "backend_expansion_context_design",
            "Forecast-year critical-beta frontier solving the pass-through beta needed to hit the wall under the existing full-TDC deposit-balance beta contract",
        ),
        (
            "ratewall_forecast_path_ratio_pass_through_consumer_ladder.csv",
            "backend_expansion_context_design",
            "Compact explicit-pass-through consumer ladder keeping each year's top three closest-to-wall scenarios plus the reference pass-through scenario, while preserving scenario-only and noncanonical boundaries",
        ),
        (
            "ratewall_forecast_path_ratio_pass_through_consumer_interpretation_summary.csv",
            "backend_expansion_context_design",
            "Compact explicit-pass-through interpretation summary for ladder scenarios, showing which component is actually rescaled by deposit-beta assumptions and which treasury and bank components remain unchanged under existing source-backed-context versus assumption-only boundaries",
        ),
        (
            "ratewall_forecast_path_ratio_pass_through_comparison.csv",
            "backend_expansion_context_design",
            "Held-fixed forecast pass-through comparison surface isolating how changing deposit beta moves the TDC support leg, total numerator, wall ratio, and remaining gap while MPC, repricing, and holder mix stay fixed",
        ),
        (
            "ratewall_forecast_path_ratio_pass_through_delta_summary.csv",
            "backend_expansion_context_design",
            "Year-level explicit-pass-through delta summary highlighting the strongest ratio and gap movements for each pass-through scenario across held-fixed forecast bundles",
        ),
        (
            "ratewall_forecast_path_ratio_pass_through_dominance.csv",
            "backend_expansion_context_design",
            "Year-level dominance comparison showing whether explicit deposit pass-through or the existing non-pass-through driver axis is the larger mover of closeness to the wall",
        ),
        (
            "ratewall_forecast_product_decision_casebook.csv",
            "backend_expansion_context_design",
            "Compact forecast decision casebook joining each year-profile product row to Treasury calibration, bank sidecar, pass-through dominance, and evidence queue status while keeping the surface noncanonical",
        ),
        (
            "ratewall_forecast_product_pass_through_frontier_crosswalk.csv",
            "backend_expansion_context_design",
            "Year-level crosswalk comparing the base forecast product casebook row with the closest-to-wall explicit pass-through frontier row while preserving noncanonical Assumption Mode boundaries",
        ),
        (
            "ratewall_forecast_product_reviewer_decision_summary.csv",
            "backend_expansion_context_design",
            "Reviewer-facing year-level forecast decision summary joining the base/pass-through frontier crosswalk to evidence dependency and work-queue targets without promoting scenario rows",
        ),
        (
            "ratewall_historical_tdc_path_admission.csv",
            "backend_expansion_context_design",
            "Quarter-level historical TDC admission registry showing where reduced-form historical TDC stays comparison-only because selected-series coverage is empty, panel coverage is limited, or overlap proof is missing",
        ),
        (
            "ratewall_historical_tdc_source_hardening_audit.csv",
            "backend_expansion_context_design",
            "Aggregated historical TDC source-hardening audit summarizing selected-series, source-contract, reconciliation, panel, coverage, and quarter-level admission evidence without promoting reduced-form TDC into headline historical use",
        ),
        (
            "ratewall_historical_tdc_source_admission_targeting.csv",
            "backend_expansion_context_design",
            "Quarter-level historical TDC targeting matrix isolating selected-series bridge gaps, panel-field gaps, overlap-proof gaps, and source-backed-only candidate blockers without promoting any historical TDC row into headline use",
        ),
        (
            "ratewall_historical_tdc_component_gap_registry.csv",
            "backend_expansion_context_design",
            "Quarter-by-component historical TDC gap registry that decomposes the selected-series bridge, panel-field, and overlap-identity blockers into explicit next-source actions",
        ),
        (
            "ratewall_historical_tdc_source_backed_only_eligibility.csv",
            "backend_expansion_context_design",
            "Fail-closed historical TDC source-backed-only eligibility matrix showing where a nonheadline source-backed companion still remains blocked by selected-series bridge, panel, or overlap gaps",
        ),
        (
            "ratewall_historical_tdc_selected_series_bridge_alignment.csv",
            "backend_expansion_context_design",
            "Quarter-aware selected-series bridge alignment surface showing whether the selected historical TDC contract key is present in the estimator bridge, what fallback bridge estimators exist, and why alignment remains blocked",
        ),
        (
            "ratewall_historical_tdc_admission_feasibility_summary.csv",
            "backend_expansion_context_design",
            "Quarter-level historical TDC admission-feasibility summary that separates selected-series bridge failure from panel-field and overlap failure while keeping headline admission blocked",
        ),
        (
            "ratewall_historical_tdc_source_backed_companion_candidate.csv",
            "backend_expansion_context_design",
            "Fail-closed nonheadline source-backed historical TDC companion candidate registry that stays blank and blocked unless bridge coverage, overlap identity, and DU/RU-sensitive inputs all materially improve",
        ),
        (
            "ratewall_historical_tdc_selected_series_bridge_remediation_matrix.csv",
            "backend_expansion_context_design",
            "Quarter-by-candidate selected-series bridge remediation matrix that maps the missing selected historical TDC contract key against quarter-available estimator-bridge keys and records which candidates are only contextual surrogates rather than contract matches",
        ),
        (
            "ratewall_historical_tdc_du_ru_sensitive_panel_blocker_registry.csv",
            "backend_expansion_context_design",
            "Quarter-by-field DU/RU-sensitive panel blocker registry isolating exact recipient-split, security-absorption, and RU-sensitive context fields that still block any source-backed historical TDC companion even if bridge coverage improves",
        ),
        (
            "ratewall_historical_tdc_admission_candidate_matrix.csv",
            "backend_expansion_context_design",
            "Quarter-level historical TDC admission candidate matrix showing how bridge-only improvement would still leave panel and overlap blockers, and what remains after bridge plus DU/RU-sensitive panel remediation",
        ),
        (
            "ratewall_historical_tdc_post_bridge_admission_status.csv",
            "backend_expansion_context_design",
            "Quarter-level post-bridge historical TDC admission status surface that removes stale selected-series bridge blockers and owner-directed DU/RU blockers for executed quarters while preserving overlap, other-panel, and future-primary-target blockers",
        ),
        (
            "ratewall_historical_tdc_du_ru_methodology_panel.csv",
            "backend_expansion_context_design",
            "Owner-directed historical TDC DU/RU methodology panel that consumes TDC-EST interest allocation and Z.1 holder absorption from the TDC-EST RateWall export without admitting historical TDC into headline use",
        ),
        (
            "ratewall_historical_tdc_bridge_candidate_priority_queue.csv",
            "backend_expansion_context_design",
            "Aggregated selected-series bridge candidate priority queue ranking repeated surrogate estimator mappings by coverage, average quarter rank, and scope safety before any historical TDC admission work",
        ),
        (
            "ratewall_historical_tdc_post_bridge_blocker_queue.csv",
            "backend_expansion_context_design",
            "Post-bridge blocker queue isolating the smallest remaining overlap and other-panel tasks that would still block a nonheadline historical TDC companion after bridge and DU/RU-sensitive remediation",
        ),
        (
            "ratewall_historical_tdc_source_work_queue.csv",
            "backend_expansion_context_design",
            "Concrete historical TDC source-work queue that orders bridge mapping, DU/RU-sensitive panel sourcing, overlap proof, and remaining panel-field cleanup into one nonheadline backend task list",
        ),
        (
            "ratewall_historical_tdc_exact_du_ru_closure_contract.csv",
            "backend_expansion_context_design",
            "DU/RU closure contract that records owner-directed TDC-EST/Z.1 methodology coverage for bridge-executed quarters while preserving future coverage and nonheadline guardrails",
        ),
        (
            "ratewall_historical_tdc_overlap_identity_closure_contract.csv",
            "backend_expansion_context_design",
            "Fail-closed historical TDC overlap-identity closure contract that records the direct-interest overlap bridge required before reduced-form historical TDC can move beyond comparison-only use",
        ),
        (
            "ratewall_historical_tdc_primary_bridge_target_registry.csv",
            "backend_expansion_context_design",
            "Single-row primary bridge target registry locking the selected historical TDC bridge target, its contract lineage, coverage window, missing quarters, and why the bridge-prep layer prefers it over surrogate-only top-ranked candidates",
        ),
        (
            "ratewall_historical_tdc_selected_series_primary_target_mapping_plan.csv",
            "backend_expansion_context_design",
            "Quarter-by-quarter mapping plan from the selected historical TDC series key to the locked primary bridge target, showing where the primary target is available, where quarter-top candidates differ, and when bridge coverage is still absent",
        ),
        (
            "ratewall_historical_tdc_selected_series_bridge_execution.csv",
            "backend_expansion_context_design",
            "Quarter-by-quarter execution surface materializing the selected-series alias bridge to the locked contract-ingested primary TDC target for available quarters while keeping future missing quarters and headline promotion blocked",
        ),
        (
            "ratewall_historical_tdc_bridge_implementation_prep.csv",
            "backend_expansion_context_design",
            "Bridge-specific implementation-prep task surface stating which alias-mapping, future-quarter coverage, and contract-versus-surrogate boundary tasks must happen before any historical TDC companion can move beyond comparison-only status",
        ),
        (
            "ratewall_historical_incremental_path_ratio_frontier_summary.csv",
            "backend_expansion_context_design",
            "Compact historical frontier summary ranking reportable default path-ratio quarters while linking each quarter back to its historical TDC admission and comparison status",
        ),
        (
            "ratewall_historical_closest_approach_clean.csv",
            "backend_expansion_context_design",
            "Clean historical closest-approach chronology showing conservative, base, and aggressive rows with direct support, TDC sidecar support, drag, ratio, distance-to-wall ranks, and near-zero or missing-sidecar flags",
        ),
        (
            "ratewall_forecast_incremental_path_ratio_frontier_summary.csv",
            "backend_expansion_context_design",
            "Compact forecast frontier summary exposing deterministic reference, minimum, and maximum default path-ratio scenarios by forecast year with linked TDC comparison rows",
        ),
        (
            "ratewall_historical_forecast_wall_ratio_comparison_matrix.csv",
            "backend_expansion_context_design",
            "Machine-readable historical-versus-forecast comparison matrix that anchors each forecast year against the best reportable historical frontier and the broader transition-inclusive historical peak without promoting a canonical wall ratio",
        ),
        (
            "ratewall_distance_to_wall_state_surface.csv",
            "backend_expansion_context_design",
            "Explicit noncanonical state-distance sidecar surface that packages historical frontier rows plus forecast reference/minimum/maximum rows with ratio, numerator, denominator, remaining gap, wall-hit status, and dominant assumption signatures",
        ),
        (
            "ratewall_closest_to_wall_frontier.csv",
            "backend_expansion_context_design",
            "Ranked closest-to-wall frontier derived from the noncanonical state-distance sidecar, keeping reduced-form historical TDC comparison-only and quarterly forecast sidecars non-headline",
        ),
        (
            "ratewall_scenario_denominator_anchor_lineage.csv",
            "assumption_mode",
            "Scenario-level lineage table showing which denominator source each annual runtime or overlay row is using, with timing and empirical-status labels",
        ),
        (
            "ratewall_scenario_denominator_stack_comparison.csv",
            "assumption_mode",
            "Scenario-facing denominator stack showing the default literature-backed runtime anchor, legacy sensitivity-only annual-flow anchors, and review-only bounded h8 overlay rows side by side",
        ),
        (
            "ratewall_denominator_scale_conflict_adjudication.csv",
            "backend_expansion_context_design",
            "Review-only adjudication surface comparing bounded h8, corrected literature-bridge, and FRB/US denominator scales in common units",
        ),
        (
            "ratewall_h4_empirical_validation_registry.csv",
            "backend_expansion_context_design",
            "Review-only same-design h4 validation surface comparing the direct bounded h4 companion estimate against the promoted literature runtime family and the FRB/US h4 benchmark",
        ),
        (
            "ratewall_denominator_scale_conflict_followup_decision.csv",
            "backend_expansion_context_design",
            "Fail-closed decision surface stating that the literature-backed annual-flow runtime family is live and that any future reopen should be limited to h8 translation, h8-compatible numerator work, or genuinely new scale evidence",
        ),
        (
            "ratewall_noncanonical_current_demand_source_timing_contract.csv",
            "backend_expansion_context_design",
            "Fail-closed dual-lane source and timing contract for the review-only current-demand consumer, separating bounded h8 cumulative overlay use from literature annual-flow comparison use",
        ),
        (
            "ratewall_noncanonical_current_demand_consumer_endpoint_decision.csv",
            "backend_expansion_context_design",
            "Fail-closed endpoint decision recording that the shared dual-lane review-only consumer contract is sufficient and that any remaining denominator work should focus on interpretation of the bounded-h8 versus literature/FRB-US scale conflict",
        ),
        (
            "ratewall_conventional_drag_current_demand_ratio_gate.csv",
            "backend_expansion_context_design",
            "Noncanonical current-demand gate exposing the bounded h8 interval-first input while referencing the shared dual-lane review-only consumer contract and keeping canonical RW_Y blocked by design",
        ),
        (
            "ratewall_noncanonical_current_demand_support_ratio_consumer.csv",
            "backend_expansion_context_design",
            "Review-only annual support consumer now operating under an explicit dual-lane source/timing contract: bounded h8 non-ratio overlay rows plus review-only literature annual-flow comparison rows tied to the runtime-primary literature family",
        ),
        (
            "ratewall_residualized_ffr_literature_replication_audit.csv",
            "backend_expansion_context_design",
            "Published residualized-fed-funds GDP replication audit surface with a live review-only local replication lane",
        ),
        (
            "ratewall_residualized_ffr_literature_lp_results.csv",
            "backend_expansion_context_design",
            "Residualized-fed-funds LP result surface for GDP and private-demand outcomes under review-only bridge semantics",
        ),
        (
            "ratewall_residualized_ffr_fwl_diagnostics.csv",
            "backend_expansion_context_design",
            "RateWall-owned residualization/FWL/Newey-West diagnostic surface for the literature bridge lane",
        ),
        (
            "ratewall_residualized_ffr_private_demand_bridge.csv",
            "backend_expansion_context_design",
            "Outcome bridge separating GDP, FSPDP, PCE, and annual-flow literature-window translations under the residualized-fed-funds lane",
        ),
        (
            "ratewall_residualized_ffr_normalization_bridge.csv",
            "backend_expansion_context_design",
            "Shock-unit bridge mapping the literature shock into exact 100bp-year units, including review-only annual-flow window translations",
        ),
        (
            "ratewall_conventional_drag_fspdp_proxy_iv_frbus_benchmark_crosscheck.csv",
            "backend_expansion_context_design",
            "Review-only directional FRB/US cross-check for the proxy-IV controlled h8 candidate; benchmark context only, not denominator calibration",
        ),
        (
            "ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv",
            "backend_expansion_context_design",
            "Normalized 100bp-year FRB/US component-mapped FSPDP proxy benchmark for h4/h8/h12 shape and scale context only; never denominator calibration",
        ),
        (
            "ratewall_conventional_drag_fspdp_proxy_iv_weak_iv_safe_inference.csv",
            "backend_expansion_context_design",
            "Anderson-Rubin weak-IV-safe review for the long-sample proxy-IV h4 and h8 gates; bounded noncanonical admission only if the target D_Y interval excludes zero",
        ),
        (
            "ratewall_conventional_drag_denominator_promotion_rule_evaluation.csv",
            "backend_expansion_context_design",
            "Bounded h8 promotion-rule evaluation showing which review gates pass and whether weak-IV-safe inference clears bounded noncanonical admission",
        ),
        (
            "ratewall_conventional_drag_fspdp_denominator_conversion_uncertainty_boundary.csv",
            "backend_expansion_context_design",
            "Review-only FSPDP denominator conversion boundary preserving value-bearing LP response and uncertainty support without admitting GDP-share denominator fields",
        ),
        (
            "ratewall_conventional_drag_fspdp_gdp_share_conversion_design_gate.csv",
            "backend_expansion_context_design",
            "Source-backed FSPDP nominal GDP-share input design gate with conversion, uncertainty, denominator, and promotion blocked until separately admitted",
        ),
        (
            "ratewall_conventional_drag_fspdp_gdp_share_conversion_method_admission.csv",
            "backend_expansion_context_design",
            "Method-admission row for the log-exact nominal-share-scaled FSPDP conversion, limited to noncanonical sensitivity use and blocked from D_Y or main-ratio promotion",
        ),
        (
            "ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv",
            "backend_expansion_context_design",
            "LP-sample base-quarter FSPDP nominal GDP-share join feeding the noncanonical conversion sensitivity center without promoting a denominator",
        ),
        (
            "ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv",
            "backend_expansion_context_design",
            "Noncanonical FSPDP GDP-share conversion sensitivity rows across LP-sample, baseline, full-panel, and latest-share windows with all promotion switches disabled",
        ),
        (
            "ratewall_conventional_drag_fspdp_lp_sample_share_closeout_decision.csv",
            "backend_expansion_context_design",
            "Fail-closed LP-sample share closeout decision recording that the FSPDP lane remains noncanonical sensitivity only until new promotion-grade evidence appears",
        ),
        (
            "ratewall_fairparke_benchmark_run_inventory.csv",
            "backend_expansion_context_design",
            "Read-only Fair/Parke sibling-run inventory; secondary benchmark context only and current public exports are not monetary-tightening scenarios",
        ),
        (
            "ratewall_fairparke_benchmark_mapping_contract.csv",
            "backend_expansion_context_design",
            "Read-only Fair/Parke variable and component mapping contract; secondary to FRB/US and blocked on a compatible rate-path scenario",
        ),
        (
            "ratewall_assumption_mode_recipient_leakage_absorber_basis_audit.csv",
            "assumption_mode",
            "Recipient-leakage absorber-basis audit for conservative full-haircut and residualized diagnostics",
        ),
        (
            "ratewall_household_within_distribution_safe_asset_capture_context.csv",
            "assumption_mode",
            "Within-distribution household safe-asset capture context; no MPC, incidence, or demand conversion",
        ),
        (
            "ratewall_deposit_pass_through_dispersion_conditioner.csv",
            "assumption_mode",
            "Deposit pass-through dispersion conditioner; pricing and incidence claims disabled",
        ),
        (
            "ratewall_brokerage_tbill_mmf_access_context.csv",
            "assumption_mode",
            "Brokerage, T-bill, and MMF safe-yield access context; holder allocation disabled",
        ),
        (
            "ratewall_firm_interest_income_expense_balance_context.csv",
            "assumption_mode",
            "Firm interest income/expense balance context; two-sided and not a net expansion claim",
        ),
        (
            "ratewall_firm_debt_maturity_wall_context.csv",
            "assumption_mode",
            "Firm debt maturity-wall context and restricted-data design surface",
        ),
        (
            "ratewall_bdc_private_credit_stress_marker_context.csv",
            "assumption_mode",
            "BDC/private-credit stress-marker context; public slice remains nonrepresentative",
        ),
        (
            "ratewall_cre_maturity_refi_pressure_context.csv",
            "assumption_mode",
            "CRE maturity/refinancing-pressure context and restricted-data design surface",
        ),
        (
            "ratewall_bnpl_zero_interest_float_context.csv",
            "assumption_mode",
            "BNPL zero-interest float timing context; consumer incidence and welfare disabled",
        ),
        (
            "ratewall_safe_asset_substitution_pairing_audit.csv",
            "assumption_mode",
            "Safe-asset substitution pairing audit preventing one-sided safe-yield narrowing",
        ),
        (
            "ratewall_financialization_expansion_avoidance_audit.csv",
            "assumption_mode",
            "Negative-control audit for avoided composite index and public aggregate causal regression artifacts",
        ),
        (
            "ratewall_bank_nim_credit_supply_context.csv",
            "assumption_mode",
            "Bank NIM and credit-supply context; intermediation channel only",
        ),
        (
            "ratewall_tax_timing_interest_income_context.csv",
            "assumption_mode",
            "Interest-income tax timing context; tax incidence and current-demand conversion disabled",
        ),
        (
            "ratewall_foreign_holder_interest_leakage_context.csv",
            "assumption_mode",
            "Foreign holder interest-leakage context; beneficial-owner allocation disabled",
        ),
        (
            "ratewall_public_finance_remittance_timing_stress_grid.csv",
            "assumption_mode",
            "Public-finance remittance/TGA timing stress grid under deterministic assumptions",
        ),
        (
            "ratewall_insurance_pension_asset_liability_context.csv",
            "assumption_mode",
            "Insurance and pension asset-liability context; beneficiary incidence disabled",
        ),
        (
            "ratewall_housing_lockin_cashflow_context.csv",
            "assumption_mode",
            "Housing lock-in cash-flow context; borrower welfare and MPC disabled",
        ),
        (
            "ratewall_dealer_inventory_carry_context.csv",
            "assumption_mode",
            "Dealer inventory/carry context; market-functioning and pricing claims disabled",
        ),
        (
            "ratewall_equity_transmission_channel_map.csv",
            "assumption_mode",
            "Secondary equity transmission attenuation channel map",
        ),
        (
            "ratewall_equity_exposure_matrix.csv",
            "assumption_mode",
            "Firm and sector exposure matrix for equity transmission attenuation",
        ),
        (
            "ratewall_equity_sensitivity_diagnostic.csv",
            "assumption_mode",
            "RateWall state diagnostic for expected equity transmission patterns",
        ),
        (
            "ratewall_equity_claim_status.csv",
            "assumption_mode",
            "Claim-status guardrails for equity transmission attenuation",
        ),
        (
            "ratewall_equity_evidence_workplan.csv",
            "assumption_mode",
            "Evidence workplan for secondary equity transmission attenuation",
        ),
        (
            "ratewall_parameter_packs.csv",
            "assumption_mode",
            "Source-labeled low/base/high priors for speculative parameters",
        ),
        (
            "ratewall_frontier_summary.csv",
            "assumption_mode",
            "Compact frontier summary for theory-facing review",
        ),
        (
            "ratewall_regime_map.csv",
            "assumption_mode",
            "Hit, near-wall, attenuated, and robust non-hit regime map",
        ),
        (
            "ratewall_assumption_mode_interpretation.csv",
            "assumption_mode",
            "Writing-safe interpretation for each editable assumption regime",
        ),
        (
            "ratewall_prior_stack_diagnostic.csv",
            "assumption_mode",
            "Scenario-level prior-stacking diagnostic for wall-hit regimes",
        ),
        (
            "ratewall_scenario_ladder.csv",
            "assumption_mode",
            "Scenario ladder from base non-hit through near-wall and marginal hit cases",
        ),
        (
            "ratewall_model_adequacy_matrix.csv",
            "assumption_mode",
            "Professor-facing model adequacy and critique matrix",
        ),
        (
            "ratewall_assumption_mode_claim_boundary_audit.csv",
            "assumption_mode",
            "Claim-boundary audit for speculative Assumption Mode",
        ),
        (
            "ratewall_financialization_pressure.csv",
            "financialization_pressure_context",
            "Release 12.0 legacy bounded retention context",
        ),
        (
            "ratewall_financialization_pressure_evidence_appendix.csv",
            "financialization_pressure_context",
            "Release 13.0 legacy bounded retention evidence appendix",
        ),
        (
            "ratewall_safe_asset_retention_context.csv",
            "safe_asset_retention_context",
            "Release 19.0 safe-asset-retention context",
        ),
        (
            "ratewall_safe_asset_retention_evidence_appendix.csv",
            "safe_asset_retention_context",
            "Release 19.0 safe-asset-retention evidence appendix",
        ),
        (
            "ratewall_buyer_case_sign_matrix.csv",
            "buyer_case_scenarios",
            "Release 19.0 buyer-class sign matrix",
        ),
        (
            "ratewall_recipient_mpc_scenario_scaffold.csv",
            "recipient_mpc_scenarios",
            "Release 19.0 recipient-specific MPC scaffolding",
        ),
        (
            "ratewall_release_19_accounting_invariant_audit.csv",
            "post_audit_methodology",
            "Release 19.0 mechanical accounting invariant audit",
        ),
        (
            "ratewall_release_19_post_audit_methodology_audit.csv",
            "post_audit_methodology",
            "Release 19.0 accepted/deferred/blocked audit finding ledger",
        ),
        (
            "ratewall_release_20_activity_demand_benchmark.csv",
            "submission_benchmark",
            "Release 20.0 activity/demand benchmark context and blocker",
        ),
        (
            "ratewall_release_20_state_dependent_lp_diagnostics.csv",
            "submission_benchmark",
            "Release 20.0 admissible-shock LP diagnostic readiness",
        ),
        (
            "ratewall_release_20_benchmark_submission_decision.csv",
            "submission_benchmark",
            "Release 20.0 benchmark promotion and threshold-use decision",
        ),
        (
            "ratewall_release_21_live_refresh_endpoint_audit.csv",
            "backend_closeout",
            "Release 21.0 live-refresh endpoint progress and fallback audit",
        ),
        (
            "ratewall_release_21_final_benchmark_gate.csv",
            "backend_closeout",
            "Release 21.0 final benchmark denominator gate",
        ),
        (
            "ratewall_release_21_backend_invariant_audit.csv",
            "backend_closeout",
            "Release 21.0 backend accounting invariant audit",
        ),
        (
            "ratewall_release_22_source_repro_accounting_audit.csv",
            "backend_fix",
            "Release 22.0 source/repro/accounting audit",
        ),
        (
            "ratewall_release_22_core_output_source_gate.csv",
            "backend_fix",
            "Release 22.0 source gate for repricing, impulse, and threshold outputs",
        ),
        (
            "ratewall_release_22_reproducibility_hash_manifest.json",
            "backend_fix",
            "Release 22.0 backend reproducibility hash manifest",
        ),
        (
            "ratewall_release_23_source_status_propagation_audit.csv",
            "backend_fix",
            "Release 23.0 downstream source-status propagation audit",
        ),
        (
            "ratewall_release_23_latest_as_of_semantics_audit.csv",
            "backend_fix",
            "Release 23.0 latest_as_of metadata semantics audit",
        ),
        (
            "ratewall_release_23_threshold_mechanics_feasibility_audit.csv",
            "backend_fix",
            "Release 23.0 threshold mechanics feasibility audit",
        ),
        (
            "ratewall_release_23_calibration_plausibility_audit.csv",
            "backend_fix",
            "Release 23.0 calibration plausibility audit",
        ),
        (
            "ratewall_release_23_recipient_base_consistency_audit.csv",
            "backend_fix",
            "Release 23.0 recipient-base consistency audit",
        ),
        (
            "ratewall_release_23_reproducibility_hash_manifest.json",
            "backend_fix",
            "Release 23.0 archive reproducibility hash manifest",
        ),
        (
            "ratewall_release_23_archive_hash_verification_audit.csv",
            "backend_fix",
            "Release 23.0 source archive self-verification audit",
        ),
        (
            "ratewall_contractionary_benchmark_calibration.csv",
            "historical_threshold_validation",
            "Release 14.0 contractionary benchmark and remaining blockers",
        ),
        (
            "ratewall_threshold_uncertainty_bands.csv",
            "historical_threshold_validation",
            "Release 14.0 calibrated threshold uncertainty bands",
        ),
        (
            "ratewall_historical_threshold_validation.csv",
            "historical_threshold_validation",
            "Release 14.0 historical validation and non-promotion ledger",
        ),
        (
            "ratewall_policy_boundary_synthesis.csv",
            "historical_threshold_validation",
            "Release 14.0 policy-boundary synthesis",
        ),
        (
            "ratewall_blocker_resolution_ledger.csv",
            "publication_claim_decision",
            "Release 15.0 final blocker-resolution ledger",
        ),
        (
            "ratewall_publication_claim_decision.csv",
            "publication_claim_decision",
            "Release 15.0 publication-claim decision table",
        ),
        (
            "ratewall_final_blocker_ledger.csv",
            "publication_claim_decision",
            "Release 15.0 final machine-readable blocker ledger",
        ),
        (
            "ratewall_release_16_source_resolution_closeout.csv",
            "bounded_publication_closeout",
            "Release 16.0 final source-resolution closeout ledger",
        ),
        (
            "ratewall_release_16_no_further_promotion_ledger.csv",
            "bounded_publication_closeout",
            "Release 16.0 no-further-promotion publication ledger",
        ),
        (
            "ratewall_release_17_external_review_audit.csv",
            "external_review_publication_polish",
            "Release 17.0 external-review consistency audit",
        ),
        (
            "ratewall_release_17_publication_polish_qa.csv",
            "external_review_publication_polish",
            "Release 17.0 generated-surface publication polish QA",
        ),
        (
            "ratewall_release_17_blocker_reopen_decision.csv",
            "external_review_publication_polish",
            "Release 17.0 fail-closed blocker-reopen decision ledger",
        ),
        (
            "ratewall_release_18_live_refresh_robustness_audit.csv",
            "live_refresh_publication_freeze",
            "Release 18.0 live-source refresh robustness and freeze audit",
        ),
        (
            "ratewall_threshold_claim_boundary_audit.csv",
            "threshold_claim_boundary",
            "Release 12.0 threshold and financialization claim-boundary audit",
        ),
        (
            "ratewall_tdc_source_coverage.csv",
            "tdc_source_coverage",
            "Release 10.0 source coverage and missing-field ledger",
        ),
        (
            "ratewall_tdc_claim_boundary_audit.csv",
            "tdc_claim_boundary",
            "Release 10.0 TDC claim-boundary audit",
        ),
        (
            "ratewall_empirical_results.csv",
            "empirical_estimates",
            "bounded event-study/status rows",
        ),
        (
            "ratewall_causal_identification_audit.csv",
            "empirical_gate",
            "Release 2.0 causal-identification audit",
        ),
        (
            "ratewall_causal_defensibility_blocker.csv",
            "empirical_gate",
            "machine-readable stronger-causal-claim blocker",
        ),
        (
            "ratewall_event_study_support_diagnostics.csv",
            "empirical_submission",
            "Release 2.0 event-study support diagnostics",
        ),
        (
            "ratewall_event_study_robustness.csv",
            "empirical_submission",
            "Release 2.0 event-study robustness checks",
        ),
        (
            "ratewall_submission_identification_decision.csv",
            "empirical_submission",
            "Release 2.0 submission identification decision",
        ),
        (
            "ratewall_dynamic_lp_feasibility_diagnostics.csv",
            "empirical_journal_gate",
            "Release 3.0 dynamic LP feasibility diagnostics",
        ),
        (
            "ratewall_proxy_svar_feasibility_diagnostics.csv",
            "empirical_journal_gate",
            "Release 3.0 proxy-SVAR feasibility diagnostics",
        ),
        (
            "ratewall_dynamic_causal_final_blocker.csv",
            "empirical_journal_gate",
            "Release 3.0 final dynamic-causal blocker",
        ),
        (
            "ratewall_event_study_hac_diagnostics.csv",
            "empirical_final_submission",
            "Release 4.0 HAC-style uncertainty diagnostics",
        ),
        (
            "ratewall_pretrend_placebo_diagnostics.csv",
            "empirical_final_submission",
            "Release 4.0 predetermined-level placebo diagnostics",
        ),
        (
            "ratewall_dynamic_identification_promotion_contract_disabled.csv",
            "empirical_final_submission",
            "Release 4.0 disabled dynamic-identification promotion contract",
        ),
        (
            "ratewall_release_4_0_dynamic_causal_final_blocker.csv",
            "empirical_final_submission",
            "Release 4.0 strengthened final blocker",
        ),
        (
            "ratewall_controlled_dynamic_lp_results.csv",
            "empirical_dynamic_lp",
            "Release 5.0 bounded controlled dynamic-LP rows",
        ),
        (
            "ratewall_controlled_dynamic_lp_support_diagnostics.csv",
            "empirical_dynamic_lp",
            "Release 5.0 controlled dynamic-LP support diagnostics",
        ),
        (
            "ratewall_release_5_0_identification_decision.csv",
            "empirical_dynamic_lp",
            "Release 5.0 identification decision",
        ),
        (
            "ratewall_release_5_0_proxy_svar_final_blocker.csv",
            "empirical_dynamic_lp",
            "Release 5.0 proxy-SVAR blocker",
        ),
        (
            "ratewall_proxy_svar_system_panel.csv",
            "empirical_system_gate",
            "Release 6.0 source-backed system panel",
        ),
        (
            "ratewall_proxy_svar_proxy_relevance_diagnostics.csv",
            "empirical_system_gate",
            "Release 6.0 proxy relevance diagnostics",
        ),
        (
            "ratewall_proxy_svar_residual_diagnostics.csv",
            "empirical_system_gate",
            "Release 6.0 residual diagnostics",
        ),
        (
            "ratewall_proxy_svar_timing_support_diagnostics.csv",
            "empirical_system_gate",
            "Release 6.0 timing/support diagnostics",
        ),
        (
            "ratewall_release_6_0_identification_decision.csv",
            "empirical_system_gate",
            "Release 6.0 identification decision",
        ),
        (
            "ratewall_release_6_0_proxy_svar_final_blocker.csv",
            "empirical_system_gate",
            "Release 6.0 proxy-SVAR/system blocker",
        ),
        (
            "ratewall_release_6_0_valuation_incidence_frontier_disabled.csv",
            "empirical_system_gate",
            "Release 6.0 disabled valuation/incidence frontier",
        ),
        (
            "ratewall_release_7_0_var_lag_selection.csv",
            "empirical_system_gate",
            "Release 7.0 reduced-form system lag selection",
        ),
        (
            "ratewall_release_7_0_reduced_form_system_estimates.csv",
            "empirical_system_gate",
            "Release 7.0 reduced-form system estimates",
        ),
        (
            "ratewall_release_7_0_residual_covariance.csv",
            "empirical_system_gate",
            "Release 7.0 residual covariance diagnostics",
        ),
        (
            "ratewall_release_7_0_proxy_relevance_support.csv",
            "empirical_system_gate",
            "Release 7.0 proxy relevance support diagnostics",
        ),
        (
            "ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv",
            "empirical_system_gate",
            "Release 7.0 timing/exogeneity/invertibility audit",
        ),
        (
            "ratewall_release_7_0_identification_decision.csv",
            "empirical_system_gate",
            "Release 7.0 identification decision",
        ),
        (
            "ratewall_release_7_0_proxy_svar_final_blocker.csv",
            "empirical_system_gate",
            "Release 7.0 proxy-SVAR/system blocker",
        ),
        (
            "ratewall_release_8_0_proxy_specification_audit.csv",
            "empirical_system_nonpromotion",
            "Release 8.0 admissible proxy-specification audit",
        ),
        (
            "ratewall_release_8_0_structural_gap_ledger.csv",
            "empirical_system_nonpromotion",
            "Release 8.0 structural gap ledger",
        ),
        (
            "ratewall_release_8_0_nonpromotion_proof.csv",
            "empirical_system_nonpromotion",
            "Release 8.0 final non-promotion proof",
        ),
        (
            "ratewall_release_8_0_identification_decision.csv",
            "empirical_system_nonpromotion",
            "Release 8.0 identification decision",
        ),
        (
            "ratewall_release_9_0_external_proxy_source_registry.csv",
            "empirical_publication_boundary",
            "Release 9.0 external-proxy source registry",
        ),
        (
            "ratewall_release_9_0_external_proxy_support_audit.csv",
            "empirical_publication_boundary",
            "Release 9.0 external-proxy support audit",
        ),
        (
            "ratewall_release_9_0_structural_identification_decision.csv",
            "empirical_publication_boundary",
            "Release 9.0 structural identification decision",
        ),
        (
            "ratewall_release_9_0_final_nonpromotion_proof.csv",
            "empirical_publication_boundary",
            "Release 9.0 final non-promotion proof",
        ),
        (
            "ratewall_score_dashboard.csv",
            "dashboard",
            "mechanical/readiness/boundary dashboard",
        ),
        (
            "treasury_valuation_readiness_coverage.csv",
            "valuation_readiness",
            "non-pricing readiness ledger",
        ),
        (
            "ratewall_claim_boundary_audit.csv",
            "release_validation",
            "claim-boundary audit",
        ),
        ("source_provenance.json", "source_provenance", "source provenance bundle"),
    ]
    tables_dir = Path(context["tables_dir"])
    lines = [
        "# RateWall Table Plate",
        "",
        "| artifact | layer | rows | role |",
        "|---|---:|---:|---|",
    ]
    for filename, layer, role in table_specs:
        path = tables_dir / filename
        if not path.exists():
            rows = 0
        elif filename.endswith(".json"):
            rows = len(json.loads(path.read_text(encoding="utf-8")).get("sources", []))
        else:
            rows = len(_read_csv(path))
        lines.append(f"| `{path}` | {layer} | {rows} | {role} |")
    lines.append("")
    return "\n".join(lines)


def _citation_metadata_text() -> str:
    return "\n".join(
        [
            "cff-version: 1.2.0",
            'title: "RateWall: Public Debt, Reserve Balances, and the Diminishing Returns to Monetary Tightening"',
            'message: "If you use this research package, cite the generated release artifacts and source provenance."',
            "type: software",
            "authors:",
            "  - family-names: Wray",
            "    given-names: Shane",
            "version: 23.0.0",
            "date-released: 2026-05-12",
            'repository-code: "https://example.invalid/ratewall-private-release"',
            "keywords:",
            "  - monetary transmission",
            "  - public debt",
            "  - source-labeled accounting",
            "  - reproducible research",
            "license: LicenseRef-private-research-release",
            "",
        ]
    )


def _release_17_external_review_packet_text(context: dict[str, object]) -> str:
    review_rows = _rows(context, "release_17_external_review")
    blocker_rows = _rows(context, "release_17_blocker_reopen")
    reopened = sum(row.get("blocker_reopened") == "true" for row in blocker_rows)
    return "\n".join(
        [
            "# RateWall Release 17.0 External Review Packet",
            "",
            "Release 17.0 is an external-review and publication-polish layer. "
            "It reviews source/provenance, empirical-method, threshold, TDC "
            "deposit-channel, valuation-readiness, and closeout surfaces for "
            "consistency with the bounded-publication claim boundary.",
            "",
            f"- External-review audit rows: `{len(review_rows)}`",
            f"- Blocker-reopen decision rows: `{len(blocker_rows)}`",
            f"- Blockers reopened: `{reopened}`",
            "",
            "No blocker is reopened in this layer absent new source/method "
            "evidence and fail-closed tests. The package therefore keeps "
            "final threshold-date, policy-failure, universal inflation-sign, "
            "deposit-sign, pricing, incidence, welfare, and causal-"
            "financialization claims disabled.",
            "",
            "## Reviewed Components",
            "",
            *[
                f"- `{row.get('review_component')}`: "
                f"{row.get('reviewer_facing_finding')}"
                for row in review_rows
            ],
            "",
        ]
    )


def _release_17_publication_polish_memo_text(context: dict[str, object]) -> str:
    polish_rows = _rows(context, "release_17_publication_polish")
    return "\n".join(
        [
            "# RateWall Release 17.0 Publication Polish Memo",
            "",
            "This memo records the final generated-surface QA for public "
            "release materials. It is packaging and review discipline, not a "
            "new empirical or accounting claim.",
            "",
            f"- Publication-polish QA rows: `{len(polish_rows)}`",
            "- Manual current macro values remain disallowed.",
            "- Paper/deck/README/archive surfaces are generated from outputs.",
            "- Promotion, pricing, incidence, welfare, policy-failure, and "
            "causal-financialization claims remain disabled.",
            "",
            "## Surfaces",
            "",
            *[
                f"- `{row.get('surface')}` / `{row.get('artifact')}`: "
                f"{row.get('figure_table_role')}"
                for row in polish_rows
            ],
            "",
        ]
    )


def _release_18_publication_freeze_memo_text(context: dict[str, object]) -> str:
    refresh_rows = _rows(context, "release_18_live_refresh")
    pass_rows = sum(row.get("refresh_status") == "pass" for row in refresh_rows)
    fallback_counts = {
        row.get("refresh_component", ""): row.get("fallback_rows", "")
        for row in refresh_rows
    }
    fallback_summary = fallback_counts.get("fallback_provenance_guard", "0")
    return "\n".join(
        [
            "# RateWall Release 18.0 Publication Freeze Memo",
            "",
            "Release 18.0 hardens live-source refresh behavior with bounded "
            "socket and per-series deadlines plus provenance-preserving "
            "fallbacks. This is a release-refresh robustness layer, not a new "
            "claim-promotion layer.",
            "",
            f"- Live-refresh robustness rows: `{len(refresh_rows)}`",
            f"- Passing refresh rows: `{pass_rows}`",
            f"- Fallback rows in current snapshot/provenance context: `{fallback_summary}`",
            "- Stored secrets remain disallowed in provenance.",
            "- Pricing, incidence, welfare, policy-failure, final threshold-date, "
            "universal inflation-sign, deposit-sign, and causal-financialization "
            "claims remain disabled.",
            "",
            "## Refresh Guards",
            "",
            *[
                f"- `{row.get('refresh_component')}`: {row.get('live_refresh_policy')}"
                for row in refresh_rows
            ],
            "",
        ]
    )


def _release_19_post_audit_methodology_memo_text(context: dict[str, object]) -> str:
    methodology_rows = _rows(context, "release_19_methodology")
    invariant_rows = _rows(context, "release_19_invariants")
    accepted = sum(row.get("action_status") == "accepted" for row in methodology_rows)
    failed = sum(row.get("audit_status") == "fail" for row in invariant_rows)
    return "\n".join(
        [
            "# RateWall Release 19.0 Post-Audit Methodology Memo",
            "",
            "Release 19.0 accepts the external audit's core methodological "
            "criticisms as release gates: no Fed/remittance double counting, "
            "no additive RU-financing deposit leg, no deposit beta inside "
            "deposit-quantity accounting, no mixed-outcome GDP-drag benchmark, "
            "and no causal-financialization framing.",
            "",
            f"- Post-audit methodology rows: `{len(methodology_rows)}`",
            f"- Accepted audit actions: `{accepted}`",
            f"- Failed invariant rows: `{failed}`",
            "- Buyer-class and MPC tables are scenario scaffolds only; pricing, "
            "tax, MPC, incidence, and welfare switches remain disabled.",
            "",
            "## Audit Actions",
            "",
            *[
                f"- `{row.get('audit_finding')}`: "
                f"{row.get('action_status')} via `{row.get('evidence_artifact')}`"
                for row in methodology_rows
            ],
            "",
        ]
    )


def _release_20_submission_readiness_memo_text(context: dict[str, object]) -> str:
    activity_rows = _rows(context, "release_20_activity_benchmark")
    lp_rows = _rows(context, "release_20_lp_diagnostics")
    decision_rows = _rows(context, "release_20_decision")
    blocked = sum(
        row.get("decision_status", "").startswith("blocked") for row in decision_rows
    )
    diagnostics = sum(
        row.get("diagnostic_status") != "blocked_missing_artifact" for row in lp_rows
    )
    return "\n".join(
        [
            "# RateWall Release 20.0 Submission-Readiness Memo",
            "",
            "Release 20.0 converts the post-audit contractionary-benchmark "
            "frontier into a submission-readiness gate. It records coherent "
            "activity and labor-market response context from admissible-shock "
            "outputs, but it does not promote those rows into a GDP-share "
            "threshold denominator.",
            "",
            f"- Activity/demand benchmark rows: `{len(activity_rows)}`",
            f"- State-dependent LP diagnostic rows: `{len(lp_rows)}`",
            f"- Available diagnostic groups: `{diagnostics}`",
            f"- Benchmark submission-decision rows: `{len(decision_rows)}`",
            f"- Blocked benchmark-decision rows: `{blocked}`",
            "",
            "## Decisions",
            "",
            *[
                f"- `{row.get('decision_component')}`: "
                f"{row.get('decision_status')} via `{row.get('evidence_artifact')}`"
                for row in decision_rows
            ],
            "",
            "## Boundary",
            "",
            "The Release 20 outputs are paper-submission support. They keep "
            "raw-rate shock identification rejected, keep policy-failure and "
            "final threshold-date claims disabled, and keep threshold rows as "
            "conditional scenario diagnostics unless a future benchmark gate "
            "deliberately passes.",
            "",
        ]
    )


def _release_21_backend_closeout_memo_text(context: dict[str, object]) -> str:
    live_rows = _rows(context, "release_21_live_refresh")
    benchmark_rows = _rows(context, "release_21_benchmark_gate")
    invariant_rows = _rows(context, "release_21_backend_invariants")
    live_pass = sum(row.get("audit_status") == "pass" for row in live_rows)
    invariant_pass = sum(row.get("audit_status") == "pass" for row in invariant_rows)
    benchmark_blocked = sum(
        row.get("gate_status", "").startswith("blocked") for row in benchmark_rows
    )
    return "\n".join(
        [
            "# RateWall Release 21.0 Backend Closeout Memo",
            "",
            "Release 21.0 is backend-only. It hardens live refresh diagnostics, "
            "keeps the final contractionary benchmark gate fail-closed, and "
            "adds invariant rows for the corrected accounting identities.",
            "",
            f"- Live-refresh endpoint audit rows: `{len(live_rows)}`",
            f"- Passing live-refresh audit rows: `{live_pass}`",
            f"- Final benchmark gate rows: `{len(benchmark_rows)}`",
            f"- Blocked final benchmark rows: `{benchmark_blocked}`",
            f"- Backend invariant rows: `{len(invariant_rows)}`",
            f"- Passing backend invariant rows: `{invariant_pass}`",
            "",
            "## Backend Boundary",
            "",
            "The backend package remains conditional and non-promotional: no "
            "final threshold date, policy-failure claim, universal deposit sign, "
            "pricing/incidence/welfare output, raw-rate shock identification, "
            "or causal-financialization claim is enabled.",
            "",
            "## Gate Rows",
            "",
            *[
                f"- `{row.get('gate_component')}`: {row.get('gate_status')}"
                for row in benchmark_rows
            ],
            "",
        ]
    )


def _release_22_backend_fix_memo_text(context: dict[str, object]) -> str:
    source_gate = _rows(context, "release_22_source_gate")
    audit_rows = _rows(context, "release_22_source_repro_audit")
    hash_manifest = context.get("release_22_hash_manifest", {})
    hash_count = (
        hash_manifest.get("file_count", 0) if isinstance(hash_manifest, dict) else 0
    )
    source_gate_blocked = sum(
        "blocked" in row.get("gate_status", "") for row in source_gate
    )
    audit_pass = sum(row.get("audit_status") == "pass" for row in audit_rows)
    return "\n".join(
        [
            "# RateWall Release 22.0 Backend Fix Memo",
            "",
            "Release 22.0 is backend-only. It responds to the Release 21 external "
            "audit by gating MSPD fallback repricing, vendoring sibling-derived "
            "calibration extracts, separating current Fed remittance cash effects "
            "from future deferred-asset drag, fixing latest-record selection, and "
            "strengthening arithmetic/reproducibility checks.",
            "",
            f"- Core output source-gate rows: `{len(source_gate)}`",
            f"- Blocked or review source-gate rows: `{source_gate_blocked}`",
            f"- Source/repro/accounting audit rows: `{len(audit_rows)}`",
            f"- Passing source/repro/accounting audit rows: `{audit_pass}`",
            f"- Hash-manifest file records: `{hash_count}`",
            "",
            "## Backend Boundary",
            "",
            "Fallback or review MSPD status can support explicit fallback/context "
            "scenarios only. It cannot support live security-level repricing, final "
            "threshold-date, Fed-policy-failure, pricing/incidence/welfare, "
            "universal deposit-sign, or causal-financialization claims.",
            "",
            "## Source Gates",
            "",
            *[
                f"- `{row.get('artifact')}`: {row.get('gate_status')} "
                f"({row.get('allowed_use')})"
                for row in source_gate
            ],
            "",
        ]
    )


def _release_23_backend_fix_memo_text(context: dict[str, object]) -> str:
    semantic_rows = [
        *_rows(context, "release_23_source_status"),
        *_rows(context, "release_23_latest_as_of"),
        *_rows(context, "release_23_threshold_mechanics"),
        *_rows(context, "release_23_calibration_plausibility"),
        *_rows(context, "release_23_recipient_base"),
    ]
    pass_rows = sum(row.get("audit_status") == "pass" for row in semantic_rows)
    return "\n".join(
        [
            "# RateWall Release 23.0 Backend Fix Memo",
            "",
            "Release 23.0 is backend-only. It responds to the Release 22 external review "
            "audit by propagating fallback/review source status downstream, "
            "demoting calibrated threshold rows to sensitivity-review language, "
            "adding semantic audit tables, and producing a release-time archive "
            "hash manifest that can be checked against the source archive.",
            "",
            f"- Release 23 semantic audit rows: `{len(semantic_rows)}`",
            f"- Passing semantic audit rows: `{pass_rows}`",
            "- Source archive: `outputs/release/ratewall_release_23_0_source_archive.zip`",
            "- Archive manifest: `ratewall_release_23_reproducibility_hash_manifest.json`",
            "- Archive verification audit: `ratewall_release_23_archive_hash_verification_audit.csv`",
            "- Theory layer: `outputs/reports/ratewall_theory_of_change.md`",
            "",
            "## Backend Boundary",
            "",
            "Release 23.0 remains a backend hardening release. Fallback or review "
            "MSPD status is fallback/context-only; threshold outputs are scenario "
            "diagnostics; pricing, incidence, welfare, tax/MPC, allocation weights, "
            "reset-calendar construction, raw-rate shocks, final threshold dates, "
            "Fed-policy-failure claims, and causal-financialization claims remain "
            "disabled. Stale compiled PDF/PPTX render artifacts are intentionally "
            "excluded from the backend source archive until a render-focused agent "
            "regenerates and audits them.",
            "",
        ]
    )


def _theory_of_change_text() -> str:
    return "\n".join(
        [
            "# RateWall Theory of Change",
            "",
            "RateWall studies state-dependent monetary policy effectiveness in a "
            "high-debt, high-liquidity economy. The project asks when additional "
            "rate hikes remain contractionary but become partly self-offsetting "
            "through public-interest cashflows, liquid-asset income, firm cash "
            "buffers, remittance/fiscal timing, safe-asset allocation margins, "
            "and embedded zero-interest credit structures.",
            "",
            "The central claim is conditional: higher rates can have both "
            "contractionary and countervailing effects. RateWall does not claim "
            "that higher rates always raise inflation, that the Federal Reserve "
            "has stopped working, or that higher rates causally financialize the "
            "economy.",
            "",
            "## Core Question",
            "",
            "Under what balance-sheet conditions do higher interest rates become "
            "less effective at reducing demand or inflation because the same rate "
            "increase also raises income, liquidity returns, financing flows, or "
            "financial-allocation incentives?",
            "",
            "## Channel Map",
            "",
            "Conventional tightening channels include higher borrowing costs, "
            "tighter credit, lower asset values, higher hurdle rates for real "
            "investment, and reduced interest-sensitive spending.",
            "",
            "Countervailing channels include Treasury interest payments, IORB and "
            "ON RRP payments, Fed remittance and deferred-asset timing, interest "
            "income on liquid claims, firm cash cushions, safe-yield allocation "
            "incentives, and zero-interest consumer-credit structures whose value "
            "can rise when market rates rise.",
            "",
            "## State Variables",
            "",
            "- Public debt and privately held marketable Treasury debt relative to GDP.",
            "- Share of public liabilities repricing over short horizons.",
            "- Reserve balances, ON RRP exposure, money-market fund assets, deposits, "
            "and other interest-sensitive liquid claims.",
            "- Corporate cash and cash-equivalent buffers.",
            "- Recipient composition for Treasury interest, reserve interest, ON RRP "
            "payments, and remittance timing.",
            "- TGA build/spend-down state and buyer-class absorption state.",
            "- Availability, duration, and pricing incidence of zero-interest consumer "
            "credit, kept as scenario context until separately sourced.",
            "",
            "## Measurement Posture",
            "",
            "The backend remains source-gated. Mechanical accounting, scenario "
            "diagnostics, provenance, and boundary audits can advance before "
            "causal or incidence claims are promoted. Any threshold output remains "
            "conditional unless live source gates, component recipient maps, a "
            "coherent contractionary benchmark, and fail-closed tests pass.",
            "",
        ]
    )


def _package_smoke_text() -> str:
    return "\n".join(
        [
            "# RateWall Package Smoke Checks",
            "",
            "Run from the repository root with repo-safe cache settings:",
            "",
            "```bash",
            "UV_PROJECT_ENVIRONMENT=$HOME/venvs/ratewall PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/ratewall-pycache PYTEST_ADDOPTS='-p no:cacheprovider' UV_CACHE_DIR=/tmp/uv-cache-ratewall RUFF_CACHE_DIR=/tmp/ruff-cache-ratewall uv build --out-dir /tmp/ratewall-dist",
            "UV_PROJECT_ENVIRONMENT=$HOME/venvs/ratewall PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX=/tmp/ratewall-pycache PYTEST_ADDOPTS='-p no:cacheprovider' UV_CACHE_DIR=/tmp/uv-cache-ratewall RUFF_CACHE_DIR=/tmp/ruff-cache-ratewall uv run python -B -c \"import ratewall; import ratewall.cli; print(ratewall.__version__)\"",
            "```",
            "",
            "The generated validation package should record the actual terminal result.",
            "",
        ]
    )


def _manifest_payload(
    context: dict[str, object],
    *,
    claim_rows: list[dict[str, str]],
    artifacts: ReleaseArtifacts,
) -> dict[str, object]:
    empirical_statuses = Counter(
        row.get("result_status", "") for row in _rows(context, "empirical_results")
    )
    source_kinds = Counter(row.get("snapshot_kind", "") for row in context["sources"])
    payload = {
        "schema": "ratewall.release_manifest.v1",
        "generated_at": utc_now_iso(),
        "snapshot_bundle": str(context["snapshot_bundle"]),
        "source_snapshot_kind_counts": dict(source_kinds),
        "empirical_result_status_counts": dict(empirical_statuses),
        "claim_audit_status_counts": dict(
            Counter(row["audit_status"] for row in claim_rows)
        ),
        "artifact_layers": {
            "descriptive_accounting": [
                "outputs/tables/ratewall_100bps_impulse.csv",
                "outputs/tables/ratewall_databook_metrics.csv",
            ],
            "scenario_diagnostics": ["outputs/tables/ratewall_scenarios.csv"],
            "tdc_deposit_channel": [
                "outputs/tables/ratewall_tdc_deposit_channel_ledger.csv",
                "outputs/tables/ratewall_tdc_ru_financing_deposit_impulse.csv",
                "outputs/tables/ratewall_tdc_historical_panel.csv",
                "outputs/tables/ratewall_deposit_pricing_pass_through_context.csv",
                "outputs/tables/ratewall_tdc_historical_reconciliation.csv",
                "outputs/tables/ratewall_tdcest_historical_estimator_bridge.csv",
                "outputs/tables/ratewall_tdcest_monetary_route_bridge.csv",
                "outputs/tables/ratewall_tdcest_mmf_route_split_context.csv",
                "outputs/tables/ratewall_tdcest_z1_domestic_nonbank_sector_context.csv",
                "outputs/tables/ratewall_tdc_rolling_pass_through_context.csv",
                "outputs/tables/ratewall_historical_tdc_wall_ratio_path.csv",
                "outputs/tables/ratewall_historical_assumption_mode_tdc_wall_ratio_path.csv",
                "outputs/tables/ratewall_tdc_source_coverage.csv",
                "outputs/tables/ratewall_tdc_claim_boundary_audit.csv",
                "outputs/tables/ratewall_tdc_other_component_bridge.csv",
                "outputs/tables/ratewall_tdc_deposit_credit_decomposition.csv",
                "outputs/tables/ratewall_tdc_double_count_guardrail.csv",
                "outputs/tables/ratewall_tdc_net_ratewall_effect.csv",
                "outputs/tables/ratewall_tdc_materialization_semantic_summary.csv",
                "outputs/tables/ratewall_tdc_historical_source_contract.csv",
                "outputs/tables/ratewall_tdc_historical_selected_series.csv",
                "outputs/tables/ratewall_historical_tdc_source_hardening_audit.csv",
                "outputs/tables/ratewall_historical_tdc_source_admission_targeting.csv",
                "outputs/tables/ratewall_historical_tdc_component_gap_registry.csv",
                "outputs/tables/ratewall_historical_tdc_source_backed_only_eligibility.csv",
                "outputs/tables/ratewall_historical_tdc_selected_series_bridge_alignment.csv",
                "outputs/tables/ratewall_historical_tdc_admission_feasibility_summary.csv",
                "outputs/tables/ratewall_historical_tdc_source_backed_companion_candidate.csv",
                "outputs/tables/ratewall_historical_tdc_selected_series_bridge_remediation_matrix.csv",
                "outputs/tables/ratewall_historical_tdc_du_ru_sensitive_panel_blocker_registry.csv",
                "outputs/tables/ratewall_historical_tdc_admission_candidate_matrix.csv",
                "outputs/tables/ratewall_historical_tdc_post_bridge_admission_status.csv",
                "outputs/tables/ratewall_historical_tdc_du_ru_methodology_panel.csv",
                "outputs/tables/ratewall_historical_tdc_bridge_candidate_priority_queue.csv",
                "outputs/tables/ratewall_historical_tdc_post_bridge_blocker_queue.csv",
                "outputs/tables/ratewall_historical_tdc_source_work_queue.csv",
                "outputs/tables/ratewall_historical_tdc_exact_du_ru_closure_contract.csv",
                "outputs/tables/ratewall_historical_tdc_overlap_identity_closure_contract.csv",
                "outputs/tables/ratewall_historical_tdc_primary_bridge_target_registry.csv",
                "outputs/tables/ratewall_historical_tdc_selected_series_primary_target_mapping_plan.csv",
                "outputs/tables/ratewall_historical_tdc_selected_series_bridge_execution.csv",
                "outputs/tables/ratewall_historical_tdc_bridge_implementation_prep.csv",
                "outputs/tables/ratewall_canonical_tdc_accounting_path.csv",
                "outputs/tables/ratewall_canonical_tdc_stitched_accounting_path.csv",
                "outputs/tables/ratewall_canonical_tdc_accounting_source_hierarchy_audit.csv",
                "outputs/tables/ratewall_tdcsim_projection_contract_bridge.csv",
                "outputs/tables/ratewall_tdcsim_domestic_nonbank_funding_classification.csv",
                "outputs/tables/ratewall_tdcsim_private_route_sensitivity_ingest.csv",
                "outputs/tables/ratewall_tdcsim_assumption_mode_support_ingest.csv",
                "outputs/tables/ratewall_tdcsim_assumption_mode_claim_gate.csv",
                "outputs/tables/ratewall_tdcsim_assumption_mode_forecast_private_route_envelope.csv",
                "outputs/tables/ratewall_tdcsim_assumption_mode_forecast_private_route_claim_gate.csv",
                "outputs/tables/ratewall_qrawatch_tdcsim_scenario_registry.csv",
                "outputs/tables/ratewall_qrawatch_tdcsim_provenance_audit.csv",
                "outputs/tables/ratewall_qrawatch_tdcsim_bridge_invariant_audit.csv",
                "outputs/tables/ratewall_tdc_forward_projection_surface.csv",
                "outputs/tables/ratewall_tdc_forward_component_audit.csv",
                "outputs/tables/ratewall_tdc_forward_overlap_guardrail.csv",
                "outputs/tables/ratewall_tdc_forward_invariant_audit.csv",
                "outputs/tables/ratewall_tdc_forward_assumption_registry.csv",
                "outputs/tables/ratewall_tdc_forward_scenario_decomposition.csv",
                "outputs/tables/ratewall_forecast_holder_tdc_consistency_bridge.csv",
                "outputs/reports/ratewall_tdc_deposit_channel_appendix.md",
            ],
            "threshold_financialization_context": [
                "outputs/tables/ratewall_threshold_simulation.csv",
                "outputs/tables/ratewall_threshold_calibration_ranges.csv",
                "outputs/tables/ratewall_threshold_calibrated_simulation.csv",
                "outputs/tables/ratewall_du_ru_tga_calibration_bridge.csv",
                "outputs/tables/ratewall_financialization_pressure.csv",
                "outputs/tables/ratewall_financialization_pressure_evidence_appendix.csv",
                "outputs/tables/ratewall_safe_asset_retention_context.csv",
                "outputs/tables/ratewall_safe_asset_retention_evidence_appendix.csv",
                "outputs/tables/ratewall_contractionary_benchmark_calibration.csv",
                "outputs/tables/ratewall_threshold_uncertainty_bands.csv",
                "outputs/tables/ratewall_historical_threshold_validation.csv",
                "outputs/tables/ratewall_policy_boundary_synthesis.csv",
                "outputs/tables/ratewall_blocker_resolution_ledger.csv",
                "outputs/tables/ratewall_publication_claim_decision.csv",
                "outputs/tables/ratewall_final_blocker_ledger.csv",
                "outputs/tables/ratewall_release_16_source_resolution_closeout.csv",
                "outputs/tables/ratewall_release_16_no_further_promotion_ledger.csv",
                "outputs/tables/ratewall_release_17_external_review_audit.csv",
                "outputs/tables/ratewall_release_17_publication_polish_qa.csv",
                "outputs/tables/ratewall_release_17_blocker_reopen_decision.csv",
                "outputs/tables/ratewall_release_18_live_refresh_robustness_audit.csv",
                "outputs/tables/ratewall_buyer_case_sign_matrix.csv",
                "outputs/tables/ratewall_recipient_mpc_scenario_scaffold.csv",
                "outputs/tables/ratewall_release_19_accounting_invariant_audit.csv",
                "outputs/tables/ratewall_release_19_post_audit_methodology_audit.csv",
                "outputs/tables/ratewall_release_20_activity_demand_benchmark.csv",
                "outputs/tables/ratewall_release_20_state_dependent_lp_diagnostics.csv",
                "outputs/tables/ratewall_release_20_benchmark_submission_decision.csv",
                "outputs/tables/ratewall_release_21_live_refresh_endpoint_audit.csv",
                "outputs/tables/ratewall_release_21_final_benchmark_gate.csv",
                "outputs/tables/ratewall_release_21_backend_invariant_audit.csv",
                "outputs/tables/ratewall_threshold_claim_boundary_audit.csv",
            ],
            "financialization_proxy_context_design": [
                "outputs/tables/ratewall_financialization_proxy_registry.csv",
                "outputs/tables/ratewall_household_safe_asset_capture_proxy.csv",
                "outputs/tables/ratewall_household_safe_asset_exposure_panel.csv",
                "outputs/tables/ratewall_household_safe_asset_access_context.csv",
                "outputs/tables/ratewall_retail_safe_yield_access_substitution_context.csv",
                "outputs/tables/ratewall_retail_deposit_beta_gap_context.csv",
                "outputs/tables/ratewall_retail_pass_through_dispersion_panel.csv",
                "outputs/tables/ratewall_deposit_competition_conditioner.csv",
                "outputs/tables/ratewall_deposit_mmf_substitution_surface.csv",
                "outputs/tables/ratewall_personal_net_interest_position_context.csv",
                "outputs/tables/ratewall_firm_liquid_asset_public_context.csv",
                "outputs/tables/ratewall_firm_liquid_asset_cushion_panel.csv",
                "outputs/tables/ratewall_firm_net_interest_cushion_context.csv",
                "outputs/tables/ratewall_firm_rollover_pressure_panel.csv",
                "outputs/tables/ratewall_firm_short_rate_exposure_proxy.csv",
                "outputs/tables/ratewall_household_borrower_fragility_context.csv",
                "outputs/tables/ratewall_bank_loan_repricing_context.csv",
                "outputs/tables/ratewall_cre_refinancing_public_context.csv",
                "outputs/tables/ratewall_private_credit_bdc_context.csv",
                "outputs/tables/ratewall_safe_yield_paired_proxy_surface.csv",
                "outputs/tables/ratewall_financialization_proxy_source_gate.csv",
                "outputs/tables/ratewall_financialization_source_gate.csv",
                "outputs/tables/ratewall_financialization_restricted_protocols.csv",
                "outputs/tables/ratewall_financialization_double_count_audit.csv",
                "outputs/tables/ratewall_financialization_overlap_audit.csv",
                "outputs/tables/ratewall_financialization_artifact_traceability_matrix.csv",
                "outputs/tables/ratewall_paper_financialization_interpretation.csv",
                "outputs/reports/ratewall_financialization_proxy_backend_audit.md",
                "outputs/reports/ratewall_financialization_interpretation_memo.md",
            ],
            "backend_expansion_context_design": [
                "outputs/tables/ratewall_backend_expansion_context_registry.csv",
                "outputs/tables/ratewall_assumption_mode_channel_promotion_decision.csv",
                "outputs/tables/ratewall_assumption_mode_promoted_channel_contributions.csv",
                "outputs/tables/ratewall_assumption_mode_overlap_guardrail_audit.csv",
                "outputs/tables/ratewall_assumption_mode_recipient_conversion_overlap_audit.csv",
                "outputs/tables/ratewall_assumption_mode_sidecar_channel_decision.csv",
                "outputs/tables/ratewall_assumption_mode_sidecar_contributions.csv",
                "outputs/tables/ratewall_assumption_mode_sidecar_reasonableness_audit.csv",
                "outputs/tables/ratewall_assumption_mode_sidecar_frontier.csv",
                "outputs/tables/ratewall_assumption_mode_sidecar_bundle_frontier.csv",
                "outputs/tables/ratewall_assumption_mode_sidecar_driver_decomposition.csv",
                "outputs/tables/ratewall_assumption_mode_dynamic_sidecar_driver_decomposition.csv",
                "outputs/tables/ratewall_assumption_mode_dynamic_sidecar_paths.csv",
                "outputs/tables/ratewall_assumption_mode_dynamic_sidecar_family_summary.csv",
                "outputs/tables/ratewall_assumption_mode_dynamic_sidecar_secondary_paths.csv",
                "outputs/tables/ratewall_assumption_mode_dynamic_sidecar_secondary_frontier.csv",
                "outputs/tables/ratewall_assumption_mode_channel_status_crosswalk.csv",
                "outputs/tables/ratewall_assumption_mode_formula_identity_audit.csv",
                "outputs/tables/ratewall_assumption_source_backing_ledger.csv",
                "outputs/tables/ratewall_assumption_source_backing_invariant_audit.csv",
                "outputs/tables/ratewall_qrawatch_tdcsim_scenario_registry.csv",
                "outputs/tables/ratewall_qrawatch_tdcsim_provenance_audit.csv",
                "outputs/tables/ratewall_qrawatch_tdcsim_bridge_invariant_audit.csv",
                "outputs/tables/ratewall_generated_text_claim_boundary_scan.csv",
                "outputs/tables/ratewall_backend_surface_schema_contract.csv",
                "outputs/tables/ratewall_backend_artifact_claim_boundary_manifest.csv",
                "outputs/tables/ratewall_release_archive_reproducibility_audit.csv",
                "outputs/tables/ratewall_context_surface_no_main_ratio_audit.csv",
                "outputs/tables/ratewall_denominator_methodology_registry.csv",
                "outputs/tables/ratewall_annual_flow_denominator_anchor_registry.csv",
                "outputs/tables/ratewall_annual_flow_runtime_family_registry.csv",
                "outputs/tables/ratewall_annual_support_denominator_compatibility_registry.csv",
                "outputs/tables/ratewall_annual_support_numerator_component_registry.csv",
                "outputs/tables/ratewall_annual_support_numerator_source_gate.csv",
                "outputs/tables/ratewall_annual_support_numerator_component_rollup.csv",
                "outputs/tables/ratewall_annual_support_numerator_contract.csv",
                "outputs/tables/ratewall_annual_support_numerator_uncertainty_envelope.csv",
                "outputs/tables/ratewall_annual_support_numerator_contract_invariant_audit.csv",
                "outputs/tables/ratewall_runtime_annual_flow_support_offset_scenarios.csv",
                "outputs/tables/ratewall_runtime_annual_flow_support_offset_readiness_registry.csv",
                "outputs/tables/ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv",
                "outputs/tables/ratewall_runtime_annual_flow_support_offset_frontier_summary.csv",
                "outputs/tables/ratewall_runtime_annual_flow_support_offset_closeout_decision.csv",
                "outputs/tables/ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv",
                "outputs/tables/ratewall_scenario_denominator_anchor_lineage.csv",
                "outputs/tables/ratewall_scenario_denominator_stack_comparison.csv",
                "outputs/tables/ratewall_denominator_scale_conflict_adjudication.csv",
                "outputs/tables/ratewall_h4_empirical_validation_registry.csv",
                "outputs/tables/ratewall_denominator_scale_conflict_followup_decision.csv",
                "outputs/tables/ratewall_noncanonical_current_demand_source_timing_contract.csv",
                "outputs/tables/ratewall_noncanonical_current_demand_consumer_endpoint_decision.csv",
                "outputs/tables/ratewall_conventional_drag_current_demand_ratio_gate.csv",
                "outputs/tables/ratewall_noncanonical_current_demand_support_ratio_consumer.csv",
                "outputs/tables/ratewall_residualized_ffr_literature_replication_audit.csv",
                "outputs/tables/ratewall_residualized_ffr_literature_lp_results.csv",
                "outputs/tables/ratewall_residualized_ffr_fwl_diagnostics.csv",
                "outputs/tables/ratewall_residualized_ffr_private_demand_bridge.csv",
                "outputs/tables/ratewall_residualized_ffr_normalization_bridge.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_proxy_iv_frbus_benchmark_crosscheck.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_proxy_iv_weak_iv_safe_inference.csv",
                "outputs/tables/ratewall_conventional_drag_denominator_promotion_rule_evaluation.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_denominator_conversion_uncertainty_boundary.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_gdp_share_conversion_design_gate.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_gdp_share_conversion_method_admission.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_lp_sample_share_closeout_decision.csv",
                "outputs/tables/ratewall_fairparke_benchmark_run_inventory.csv",
                "outputs/tables/ratewall_fairparke_benchmark_mapping_contract.csv",
                "outputs/tables/ratewall_assumption_mode_recipient_leakage_absorber_basis_audit.csv",
                "outputs/tables/ratewall_household_within_distribution_safe_asset_capture_context.csv",
                "outputs/tables/ratewall_deposit_pass_through_dispersion_conditioner.csv",
                "outputs/tables/ratewall_brokerage_tbill_mmf_access_context.csv",
                "outputs/tables/ratewall_firm_interest_income_expense_balance_context.csv",
                "outputs/tables/ratewall_firm_debt_maturity_wall_context.csv",
                "outputs/tables/ratewall_bdc_private_credit_stress_marker_context.csv",
                "outputs/tables/ratewall_cre_maturity_refi_pressure_context.csv",
                "outputs/tables/ratewall_bnpl_zero_interest_float_context.csv",
                "outputs/tables/ratewall_safe_asset_substitution_pairing_audit.csv",
                "outputs/tables/ratewall_financialization_expansion_avoidance_audit.csv",
                "outputs/tables/ratewall_bank_nim_credit_supply_context.csv",
                "outputs/tables/ratewall_tax_timing_interest_income_context.csv",
                "outputs/tables/ratewall_foreign_holder_interest_leakage_context.csv",
                "outputs/tables/ratewall_public_finance_remittance_timing_stress_grid.csv",
                "outputs/tables/ratewall_insurance_pension_asset_liability_context.csv",
                "outputs/tables/ratewall_housing_lockin_cashflow_context.csv",
                "outputs/tables/ratewall_dealer_inventory_carry_context.csv",
            ],
            "assumption_mode": [
                "outputs/tables/ratewall_assumption_sets.csv",
                "outputs/tables/ratewall_interest_income_mpc_calibration_registry.csv",
                "outputs/tables/ratewall_interest_income_public_proxy_catalog.csv",
                "outputs/tables/ratewall_interest_income_proxy_range_registry.csv",
                "outputs/tables/ratewall_interest_income_claim_boundary_audit.csv",
                "outputs/tables/ratewall_post_covid_interest_income_wall_distance.csv",
                "outputs/tables/ratewall_historical_iorb_demand_proxy_path.csv",
                "outputs/tables/ratewall_historical_wall_ratio_path.csv",
                "outputs/tables/ratewall_historical_assumption_mode_wall_ratio_path.csv",
                "outputs/tables/ratewall_assumption_mode_parameter_activation_ledger.csv",
                "outputs/tables/ratewall_restricted_protocol_falsification_matrix.csv",
                "outputs/tables/ratewall_restricted_protocol_field_contract.csv",
                "outputs/tables/ratewall_condition_frontier.csv",
                "outputs/tables/ratewall_offset_decomposition.csv",
                "outputs/tables/ratewall_public_impulse_factorization.csv",
                "outputs/tables/ratewall_public_liability_repricing_ladder.csv",
                "outputs/tables/ratewall_public_liability_repricing_evidence_bridge.csv",
                "outputs/tables/ratewall_public_liability_repricing_reconciliation_gap.csv",
                "outputs/tables/ratewall_mspd_table3_bucket_repricing_gate.csv",
                "outputs/tables/ratewall_treasury_bucket_repricing_prior_bridge.csv",
                "outputs/tables/ratewall_interest_recipient_leakage_bridge.csv",
                "outputs/tables/ratewall_interest_recipient_leakage_evidence_gap.csv",
                "outputs/tables/ratewall_treasury_recipient_leakage_source_gate.csv",
                "outputs/tables/ratewall_public_finance_timing_path.csv",
                "outputs/tables/ratewall_public_finance_timing_evidence_gap.csv",
                "outputs/tables/ratewall_public_finance_timing_design_test_scaffold.csv",
                "outputs/tables/ratewall_safe_yield_offset_drag_pairing_gap.csv",
                "outputs/tables/ratewall_bnpl_zero_interest_float_evidence_gap.csv",
                "outputs/tables/ratewall_financialized_balance_sheet_evidence_gap.csv",
                "outputs/tables/ratewall_firm_cash_debt_maturity_evidence_gap.csv",
                "outputs/tables/ratewall_conventional_drag_channel_evidence_gap.csv",
                "outputs/tables/ratewall_conventional_drag_source_design_gate.csv",
                "outputs/tables/ratewall_denominator_response_design_scaffold.csv",
                "outputs/tables/ratewall_denominator_response_design_test_scaffold.csv",
                "outputs/tables/ratewall_denominator_response_gate_attempt.csv",
                "outputs/tables/ratewall_denominator_aligned_response_panel_scaffold.csv",
                "outputs/tables/ratewall_denominator_event_outcome_cell_diagnostic.csv",
                "outputs/tables/ratewall_denominator_event_outcome_panel_value_diagnostic.csv",
                "outputs/tables/ratewall_denominator_event_level_response_panel.csv",
                "outputs/tables/ratewall_denominator_uncertainty_pass_fail_review.csv",
                "outputs/tables/ratewall_denominator_panel_design_test_diagnostic.csv",
                "outputs/tables/ratewall_denominator_pretrend_placebo_diagnostic.csv",
                "outputs/tables/ratewall_denominator_shock_relevance_diagnostic.csv",
                "outputs/tables/ratewall_denominator_sign_consistency_diagnostic.csv",
                "outputs/tables/ratewall_denominator_horizon_sensitivity_diagnostic.csv",
                "outputs/tables/ratewall_denominator_outlier_window_robustness_diagnostic.csv",
                "outputs/tables/ratewall_denominator_design_readiness_decision.csv",
                "outputs/tables/ratewall_denominator_formal_design_test_result_scaffold.csv",
                "outputs/tables/ratewall_denominator_formal_design_test_result.csv",
                "outputs/tables/ratewall_denominator_response_estimate_diagnostic.csv",
                "outputs/tables/ratewall_denominator_cross_source_design_validation.csv",
                "outputs/tables/ratewall_denominator_evidence_upgrade_source_design_requirement.csv",
                "outputs/tables/ratewall_denominator_evidence_upgrade_priority_queue.csv",
                "outputs/tables/ratewall_denominator_evidence_upgrade_tier1_workplan.csv",
                "outputs/tables/ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv",
                "outputs/tables/ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv",
                "outputs/tables/ratewall_conventional_drag_evidence_tranche.csv",
                "outputs/tables/ratewall_baml_source_history_repair_contract.csv",
                "outputs/tables/ratewall_borrowing_cost_source_object_adjudication.csv",
                "outputs/tables/ratewall_baml_effective_yield_source_access_gate.csv",
                "outputs/tables/ratewall_hqm_source_proxy_lane_review.csv",
                "outputs/tables/ratewall_hqm_event_window_feasibility.csv",
                "outputs/tables/ratewall_hqm_event_outcome_panel_values.csv",
                "outputs/tables/ratewall_hqm_formal_diagnostic_gate.csv",
                "outputs/tables/ratewall_hqm_promotion_protocol_gate.csv",
                "outputs/tables/ratewall_hqm_policy_path_exposure_admission.csv",
                "outputs/tables/ratewall_hqm_policy_path_protocol_dependency_gate.csv",
                "outputs/tables/ratewall_hqm_denominator_mapping_gate.csv",
                "outputs/tables/ratewall_hqm_borrowing_cost_object_comparator.csv",
                "outputs/tables/ratewall_baa_event_window_support_diagnostic.csv",
                "outputs/tables/ratewall_baa_hqm_mapping_diagnostic.csv",
                "outputs/tables/ratewall_baa_response_diagnostic.csv",
                "outputs/tables/ratewall_baa_policy_path_normalization_gate.csv",
                "outputs/tables/ratewall_baa_rights_proxy_uncertainty_review.csv",
                "outputs/tables/ratewall_baa_current_demand_bridge_source_audit.csv",
                "outputs/tables/ratewall_hqm_current_demand_bridge_gate.csv",
                "outputs/tables/ratewall_conventional_drag_demand_conversion_admission.csv",
                "outputs/tables/ratewall_conventional_drag_calibration_route.csv",
                "outputs/tables/ratewall_conventional_drag_research_parameterization_source_contract.csv",
                "outputs/tables/ratewall_conventional_drag_research_parameterization_source_frontier.csv",
                "outputs/tables/ratewall_conventional_drag_research_payload_manifest.csv",
                "outputs/tables/ratewall_conventional_drag_research_parameterization_parser_status.csv",
                "outputs/tables/ratewall_conventional_drag_research_payload_inner_inventory.csv",
                "outputs/tables/ratewall_conventional_drag_research_extraction_candidate.csv",
                "outputs/tables/ratewall_conventional_drag_research_extraction_gate_audit.csv",
                "outputs/tables/ratewall_conventional_drag_research_extraction_gate_detail.csv",
                "outputs/tables/ratewall_conventional_drag_research_source_method_bridge.csv",
                "outputs/tables/ratewall_conventional_drag_research_source_code_interpretation.csv",
                "outputs/tables/ratewall_conventional_drag_research_extended_source_code_interpretation.csv",
                "outputs/tables/ratewall_conventional_drag_research_fspdp_coverage_candidate_scan.csv",
                "outputs/tables/ratewall_conventional_drag_research_mir_component_aggregation_normalization_review.csv",
                "outputs/tables/ratewall_conventional_drag_research_mir_component_source_variant_review.csv",
                "outputs/tables/ratewall_conventional_drag_research_source_unit_conversion_review.csv",
                "outputs/tables/ratewall_conventional_drag_research_mir_replication_source_unit_audit.csv",
                "outputs/tables/ratewall_conventional_drag_research_mir_source_unit_transformation_contract.csv",
                "outputs/tables/ratewall_conventional_drag_research_mir_target_horizon_reconciliation_contract.csv",
                "outputs/tables/ratewall_conventional_drag_research_mir_horizon_rekeying_candidate_review.csv",
                "outputs/tables/ratewall_conventional_drag_research_mir_h24_source_unit_audit.csv",
                "outputs/tables/ratewall_conventional_drag_research_mir_h24_8q_rekeying_review.csv",
                "outputs/tables/ratewall_conventional_drag_research_mir_4q8q_conversion_readiness_review.csv",
                "outputs/tables/ratewall_conventional_drag_research_policy_path_normalization_bridge_review.csv",
                "outputs/tables/ratewall_policy_path_research_shock_source_evidence_protocol_review.csv",
                "outputs/tables/ratewall_policy_path_source_code_workbook_object_inventory.csv",
                "outputs/tables/ratewall_policy_path_source_code_workbook_protocol_deep_review.csv",
                "outputs/tables/ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv",
                "outputs/tables/ratewall_policy_path_usmpd_scalar_score_replication_review.csv",
                "outputs/tables/ratewall_policy_path_usmpd_pca_backtransform_gate_review.csv",
                "outputs/tables/ratewall_policy_path_usmpd_instrument_decomposition_design_review.csv",
                "outputs/tables/ratewall_policy_path_bps_year_candidate_path_design_contract.csv",
                "outputs/tables/ratewall_policy_path_formula_replication_source_review.csv",
                "outputs/tables/ratewall_policy_path_reviewed_bps_year_protocol_gap_matrix.csv",
                "outputs/tables/ratewall_policy_path_protocol_source_acquisition_work_queue.csv",
                "outputs/tables/ratewall_policy_path_protocol_source_parse_execution_review.csv",
                "outputs/tables/ratewall_policy_path_source_parse_synthesis_queue.csv",
                "outputs/tables/ratewall_policy_path_source_parse_action_execution.csv",
                "outputs/tables/ratewall_policy_path_deeper_parse_execution_review.csv",
                "outputs/tables/ratewall_policy_path_protocol_candidate_draft_review.csv",
                "outputs/tables/ratewall_policy_path_protocol_missing_evidence_acquisition_queue.csv",
                "outputs/tables/ratewall_policy_path_protocol_missing_evidence_parse_execution_review.csv",
                "outputs/tables/ratewall_policy_path_protocol_authoring_readiness_matrix.csv",
                "outputs/tables/ratewall_policy_path_protocol_field_authoring_contract.csv",
                "outputs/tables/ratewall_policy_path_field_evidence_resolution_queue.csv",
                "outputs/tables/ratewall_ratio_layer_registry.csv",
                "outputs/tables/ratewall_ratio_object_registry.csv",
                "outputs/tables/ratewall_active_output_index.csv",
                "outputs/tables/ratewall_paper_core_results_index.csv",
                "outputs/tables/ratewall_reference_scenario_object_crosswalk.csv",
                "outputs/tables/ratewall_joint_wall_probability_axis_registry.csv",
                "outputs/tables/ratewall_joint_wall_probability_surface.csv",
                "outputs/tables/ratewall_joint_wall_probability_summary.csv",
                "outputs/tables/ratewall_wall_denominator_path_contract.csv",
                "outputs/tables/ratewall_path_ratio_numerator_ledger.csv",
                "outputs/tables/ratewall_path_ratio_numerator_reconciliation_audit.csv",
                "outputs/tables/ratewall_tdc_overlap_audit.csv",
                "outputs/tables/ratewall_path_ratio_denominator_v1.csv",
                "outputs/tables/ratewall_path_ratio_tdc_adjustment_layer.csv",
                "outputs/tables/ratewall_historical_incremental_path_ratio.csv",
                "outputs/tables/ratewall_historical_incremental_path_ratio_tdc_comparison.csv",
                "outputs/tables/ratewall_historical_tdc_path_admission.csv",
                "outputs/tables/ratewall_historical_tdc_source_hardening_audit.csv",
                "outputs/tables/ratewall_historical_tdc_source_admission_targeting.csv",
                "outputs/tables/ratewall_historical_tdc_component_gap_registry.csv",
                "outputs/tables/ratewall_historical_tdc_source_backed_only_eligibility.csv",
                "outputs/tables/ratewall_historical_tdc_selected_series_bridge_alignment.csv",
                "outputs/tables/ratewall_historical_tdc_admission_feasibility_summary.csv",
                "outputs/tables/ratewall_historical_tdc_source_backed_companion_candidate.csv",
                "outputs/tables/ratewall_historical_tdc_selected_series_bridge_remediation_matrix.csv",
                "outputs/tables/ratewall_historical_tdc_du_ru_sensitive_panel_blocker_registry.csv",
                "outputs/tables/ratewall_historical_tdc_admission_candidate_matrix.csv",
                "outputs/tables/ratewall_historical_tdc_post_bridge_admission_status.csv",
                "outputs/tables/ratewall_historical_tdc_du_ru_methodology_panel.csv",
                "outputs/tables/ratewall_historical_tdc_bridge_candidate_priority_queue.csv",
                "outputs/tables/ratewall_historical_tdc_post_bridge_blocker_queue.csv",
                "outputs/tables/ratewall_historical_tdc_source_work_queue.csv",
                "outputs/tables/ratewall_historical_tdc_exact_du_ru_closure_contract.csv",
                "outputs/tables/ratewall_historical_tdc_overlap_identity_closure_contract.csv",
                "outputs/tables/ratewall_historical_tdc_primary_bridge_target_registry.csv",
                "outputs/tables/ratewall_historical_tdc_selected_series_primary_target_mapping_plan.csv",
                "outputs/tables/ratewall_historical_tdc_selected_series_bridge_execution.csv",
                "outputs/tables/ratewall_historical_tdc_bridge_implementation_prep.csv",
                "outputs/tables/ratewall_historical_incremental_path_ratio_frontier_summary.csv",
                "outputs/tables/ratewall_historical_closest_approach_clean.csv",
                "outputs/tables/ratewall_forecast_incremental_path_ratio.csv",
                "outputs/tables/ratewall_forecast_incremental_path_ratio_tdc_comparison.csv",
                "outputs/tables/ratewall_forecast_path_ratio_scenario_registry.csv",
                "outputs/tables/ratewall_forecast_channel_conversion_profile_registry.csv",
                "outputs/tables/ratewall_forecast_assumption_calibration_registry.csv",
                "outputs/tables/ratewall_forecast_assumption_bundle_registry.csv",
                "outputs/tables/ratewall_forecast_scenario_product_summary.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_calibration_registry.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_calibration_comparison.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_calibration_product_summary.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_calibration_consumer_summary.csv",
                "outputs/tables/ratewall_forecast_bank_margin_sidecar_summary.csv",
                "outputs/tables/ratewall_forecast_path_ratio_decomposition.csv",
                "outputs/tables/ratewall_forecast_path_ratio_numerator_boundary_registry.csv",
                "outputs/tables/ratewall_forecast_path_ratio_interpretation_registry.csv",
                "outputs/tables/ratewall_forecast_path_ratio_recipient_leakage_registry.csv",
                "outputs/tables/ratewall_forecast_path_ratio_source_specific_interpretation_registry.csv",
                "outputs/tables/ratewall_forecast_path_ratio_evidence_dependency_matrix.csv",
                "outputs/tables/ratewall_forecast_path_ratio_evidence_targeting_registry.csv",
                "outputs/tables/ratewall_forecast_path_ratio_evidence_work_queue.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_bridge_packet.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_source_targeting_matrix.csv",
                "outputs/tables/ratewall_forecast_bank_behavior_bridge_packet.csv",
                "outputs/tables/ratewall_forecast_treasury_beneficial_owner_recipient_bridge.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_best_proxy_basis.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_best_proxy_admission_review.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_best_proxy_calculation_scaffold.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_best_proxy_gate_review.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_current_demand_evidence_contract.csv",
                "outputs/tables/ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy.csv",
                "outputs/tables/ratewall_forecast_bank_behavior_distribution_bridge.csv",
                "outputs/tables/ratewall_forecast_bank_behavior_current_demand_evidence_contract.csv",
                "outputs/tables/ratewall_final_recipient_current_demand_bridge_attempt.csv",
                "outputs/tables/ratewall_treasury_recipient_source_contract_path.csv",
                "outputs/tables/ratewall_treasury_recipient_current_demand_proxy_scaffold.csv",
                "outputs/tables/ratewall_bank_behavior_bridge_source_contract_queue.csv",
                "outputs/tables/ratewall_bank_behavior_rank1_source_contract_path.csv",
                "outputs/tables/ratewall_forecast_treasury_beneficial_owner_recipient_bridge_basis.csv",
                "outputs/tables/ratewall_forecast_bank_behavior_distribution_bridge_basis.csv",
                "outputs/tables/ratewall_forecast_treasury_beneficial_owner_recipient_mapping_basis.csv",
                "outputs/tables/ratewall_forecast_bank_behavior_distribution_mapping_basis.csv",
                "outputs/tables/ratewall_forecast_treasury_beneficial_owner_recipient_admission_candidate.csv",
                "outputs/tables/ratewall_forecast_bank_behavior_distribution_admission_candidate.csv",
                "outputs/tables/ratewall_forecast_treasury_beneficial_owner_recipient_bridge_pass_review.csv",
                "outputs/tables/ratewall_forecast_bank_behavior_distribution_bridge_pass_review.csv",
                "outputs/tables/ratewall_forecast_path_ratio_sensitivity_summary.csv",
                "outputs/tables/ratewall_forecast_path_ratio_scenario_frontier.csv",
                "outputs/tables/ratewall_forecast_path_ratio_driver_ranking.csv",
                "outputs/tables/ratewall_forecast_path_ratio_driver_dominance_matrix.csv",
                "outputs/tables/ratewall_forecast_path_ratio_consumer_ladder.csv",
                "outputs/tables/ratewall_forecast_path_ratio_consumer_driver_summary.csv",
                "outputs/tables/ratewall_forecast_path_ratio_consumer_interpretation_summary.csv",
                "outputs/tables/ratewall_forecast_path_ratio_pass_through_scenario_axis.csv",
                "outputs/tables/ratewall_forecast_path_ratio_pass_through_scenario_registry.csv",
                "outputs/tables/ratewall_forecast_path_ratio_pass_through_scenario_frontier.csv",
                "outputs/tables/ratewall_critical_beta_frontier.csv",
                "outputs/tables/ratewall_forecast_path_ratio_pass_through_consumer_ladder.csv",
                "outputs/tables/ratewall_forecast_path_ratio_pass_through_consumer_interpretation_summary.csv",
                "outputs/tables/ratewall_forecast_path_ratio_pass_through_comparison.csv",
                "outputs/tables/ratewall_forecast_path_ratio_pass_through_delta_summary.csv",
                "outputs/tables/ratewall_forecast_path_ratio_pass_through_dominance.csv",
                "outputs/tables/ratewall_forecast_product_decision_casebook.csv",
                "outputs/tables/ratewall_forecast_product_pass_through_frontier_crosswalk.csv",
                "outputs/tables/ratewall_forecast_product_reviewer_decision_summary.csv",
                "outputs/tables/ratewall_forecast_incremental_path_ratio_frontier_summary.csv",
                "outputs/tables/ratewall_historical_forecast_wall_ratio_comparison_matrix.csv",
                "outputs/tables/ratewall_distance_to_wall_state_surface.csv",
                "outputs/tables/ratewall_closest_to_wall_frontier.csv",
                "outputs/tables/ratewall_estimation_target_registry.csv",
                "outputs/tables/ratewall_channel_taxonomy_registry.csv",
                "outputs/tables/ratewall_historical_interpretation_audit.csv",
                "outputs/tables/ratewall_tdc_equation_variant_registry.csv",
                "outputs/tables/ratewall_policy_path_source_extraction_task_packet.csv",
                "outputs/tables/ratewall_policy_path_source_extraction_results.csv",
                "outputs/tables/ratewall_policy_path_source_extraction_result_adjudication.csv",
                "outputs/tables/ratewall_policy_path_authored_protocol_completion_audit.csv",
                "outputs/tables/ratewall_policy_path_protocol_completion_design_tranche.csv",
                "outputs/tables/ratewall_policy_path_field_specific_pass_rule_design.csv",
                "outputs/tables/ratewall_policy_path_field_specific_source_evidence_audit.csv",
                "outputs/tables/ratewall_policy_path_source_locator_binding_review.csv",
                "outputs/tables/ratewall_policy_path_exact_source_locator_remediation.csv",
                "outputs/tables/ratewall_policy_path_exact_locator_field_closure_diagnostic.csv",
                "outputs/tables/ratewall_policy_path_exact_locator_pass_rule_adjudication.csv",
                "outputs/tables/ratewall_policy_path_terminal_no_hit_closure.csv",
                "outputs/tables/ratewall_policy_path_independent_replication_target_design.csv",
                "outputs/tables/ratewall_policy_path_authored_fail_closed_invariant_design.csv",
                "outputs/tables/ratewall_policy_path_protocol_component_closure_rollup.csv",
                "outputs/tables/ratewall_policy_path_component_gate_execution_rollup.csv",
                "outputs/tables/ratewall_policy_path_locator_binding_closure_diagnostic.csv",
                "outputs/tables/ratewall_policy_path_full_protocol_admission_gate_summary.csv",
                "outputs/tables/ratewall_policy_path_source_bundle_field_exhaustion_decision.csv",
                "outputs/tables/ratewall_policy_path_source_bundle_component_exhaustion_decision.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_component_decomposition_bridge.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_component_source_manifest.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_component_share_panel.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_coverage_weight_requirement_review.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_coverage_priority_search_queue.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_source_code_search_review.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_external_source_acquisition_action_plan.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_official_component_source_acquisition_execution.csv",
                "outputs/tables/ratewall_conventional_drag_fspdp_research_side_action_plan_extraction_review.csv",
                "outputs/tables/ratewall_current_demand_gdp_share_source_manifest.csv",
                "outputs/tables/ratewall_current_demand_gdp_share_panel.csv",
                "outputs/tables/ratewall_conventional_drag_current_demand_mapping_bridge.csv",
                "outputs/tables/ratewall_conventional_drag_research_extraction_conversion_bridge.csv",
                "outputs/tables/ratewall_conventional_drag_local_macro_panel.csv",
                "outputs/tables/ratewall_conventional_drag_local_shock_quarterly.csv",
                "outputs/tables/ratewall_conventional_drag_local_lp_design.csv",
                "outputs/tables/ratewall_conventional_drag_local_lp_diagnostic.csv",
                "outputs/tables/ratewall_conventional_drag_local_lp_estimate_diagnostic.csv",
                "outputs/tables/ratewall_conventional_drag_local_lp_robustness_diagnostic.csv",
                "outputs/tables/ratewall_conventional_drag_local_lp_sample_window_audit.csv",
                "outputs/tables/ratewall_conventional_drag_local_lp_admission_audit.csv",
                "outputs/tables/ratewall_openicpsr_replication_package_source_manifest.csv",
                "outputs/tables/ratewall_frbus_model_benchmark_simulation_readiness.csv",
                "outputs/tables/ratewall_frbus_conventional_drag_benchmark_protocol.csv",
                "outputs/tables/ratewall_frbus_official_model_package_inventory.csv",
                "outputs/tables/ratewall_frbus_official_model_benchmark_simulation_protocol.csv",
                "outputs/tables/ratewall_frbus_runtime_runner_preflight.csv",
                "outputs/tables/ratewall_frbus_runtime_runner_output_slots.csv",
                "outputs/tables/ratewall_frbus_benchmark_comparison_mapping_contract.csv",
                "outputs/tables/ratewall_frbus_benchmark_output_slot_extension_review.csv",
                "outputs/tables/ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv",
                "outputs/tables/ratewall_conventional_drag_mirgk_targeted_gap_source_followup.csv",
                "outputs/tables/ratewall_conventional_drag_promotion_contract_checklist.csv",
                "outputs/tables/ratewall_conventional_drag_empirical_target_registry.csv",
                "outputs/tables/ratewall_conventional_drag_route_pruning_audit.csv",
                "outputs/tables/ratewall_conventional_drag_response_design_gate.csv",
                "outputs/tables/ratewall_denominator_response_estimate_registry.csv",
                "outputs/tables/ratewall_denominator_formal_design_gate.csv",
                "outputs/tables/ratewall_conventional_drag_response_execution_readiness_packet.csv",
                "outputs/tables/ratewall_local_lp_proxy_svar_diagnostic_run_packet.csv",
                "outputs/tables/ratewall_local_lp_proxy_svar_execution_preflight_results.csv",
                "outputs/tables/ratewall_local_lp_proxy_svar_route_closure_decision.csv",
                "outputs/tables/ratewall_conventional_drag_denominator_route_triage_synthesis.csv",
                "outputs/tables/ratewall_policy_path_100bp_year_blocker_action_resolution.csv",
                "outputs/tables/ratewall_policy_path_source_protocol_action_packet.csv",
                "outputs/tables/ratewall_policy_path_source_protocol_pass_rule_harness.csv",
                "outputs/tables/ratewall_policy_path_source_protocol_extraction_attempt_results.csv",
                "outputs/tables/ratewall_policy_path_source_protocol_attempt_closure_handoff.csv",
                "outputs/tables/ratewall_policy_path_promotion_grade_source_family_acquisition_packet.csv",
                "outputs/tables/ratewall_policy_path_promotion_grade_source_family_acquisition_execution_preflight_results.csv",
                "outputs/tables/ratewall_policy_path_source_family_execution_closure_selection_packet.csv",
                "outputs/tables/ratewall_policy_path_current_artifact_manual_review_execution_packet.csv",
                "outputs/tables/ratewall_policy_path_current_artifact_manual_review_result_attempt.csv",
                "outputs/tables/ratewall_policy_path_source_author_manual_acquisition_followup_packet.csv",
                "outputs/tables/ratewall_policy_path_source_author_manual_acquisition_execution_preflight_results.csv",
                "outputs/tables/ratewall_policy_path_real_source_author_web_acquisition_attempt_packet.csv",
                "outputs/tables/ratewall_policy_path_downloaded_artifact_locator_parse_adjudication_packet.csv",
                "outputs/tables/ratewall_policy_path_locator_candidate_pass_rule_review_decision_packet.csv",
                "outputs/tables/ratewall_tdsp_current_demand_source_review.csv",
                "outputs/tables/ratewall_tdsp_current_demand_unit_conversion.csv",
                "outputs/tables/ratewall_tdsp_current_demand_diagnostic_mapping.csv",
                "outputs/tables/ratewall_tdsp_policy_path_normalization_blocker.csv",
                "outputs/tables/ratewall_tdsp_current_demand_admission_audit.csv",
                "outputs/tables/ratewall_pce_dpi_source_refresh_contract.csv",
                "outputs/tables/ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv",
                "outputs/tables/ratewall_policy_path_exposure_vector_design_gate.csv",
                "outputs/tables/ratewall_policy_path_reviewed_protocol_source_context.csv",
                "outputs/tables/ratewall_policy_path_protocol_source_acquisition_registry.csv",
                "outputs/tables/ratewall_policy_path_protocol_source_acquisition_audit.csv",
                "outputs/tables/ratewall_policy_path_protocol_review_inventory.csv",
                "outputs/tables/ratewall_policy_path_protocol_review_audit.csv",
                "outputs/tables/ratewall_policy_path_mps_scalar_replication_diagnostic.csv",
                "outputs/tables/ratewall_policy_path_mps_scalar_replication_audit.csv",
                "outputs/tables/ratewall_policy_path_bps_year_blocker_decision.csv",
                "outputs/tables/ratewall_policy_path_bps_year_blocker_decision_audit.csv",
                "outputs/tables/ratewall_policy_path_event_level_candidate_vector.csv",
                "outputs/tables/ratewall_policy_path_event_level_candidate_vector_audit.csv",
                "outputs/tables/ratewall_policy_path_contract_interval_source_review.csv",
                "outputs/tables/ratewall_policy_path_contract_spec_acquisition_blocker.csv",
                "outputs/tables/ratewall_policy_path_bps_year_source_protocol.csv",
                "outputs/tables/ratewall_policy_path_normalization_source_manifest.csv",
                "outputs/tables/ratewall_policy_path_bps_year_normalization_review.csv",
                "outputs/tables/ratewall_policy_path_source_cell_unit_contract_review.csv",
                "outputs/tables/ratewall_policy_path_bps_year_protocol_closure.csv",
                "outputs/tables/ratewall_policy_path_normalization_leak_audit.csv",
                "outputs/tables/ratewall_tdsp_pce_dpi_policy_path_admission_audit.csv",
                "outputs/tables/ratewall_tdsp_diagnostic_family_completion_gate.csv",
                "outputs/tables/ratewall_interest_channel_horizon_timing_matrix.csv",
                "outputs/tables/ratewall_interest_channel_promotion_gate.csv",
                "outputs/tables/ratewall_interest_channel_evidence_upgrade_queue.csv",
                "outputs/tables/ratewall_high_priority_interest_channel_source_bridge.csv",
                "outputs/tables/ratewall_source_gate_prior_narrowing_decision.csv",
                "outputs/tables/ratewall_source_gate_exhaustion_closure.csv",
                "outputs/tables/ratewall_restricted_data_gate_spec.csv",
                "outputs/tables/ratewall_assumption_mode_post_closure_boundary_map.csv",
                "outputs/tables/ratewall_sibling_evidence_bridge.csv",
                "outputs/tables/ratewall_sibling_evidence_upgrade_queue.csv",
                "outputs/tables/ratewall_higher_rate_channel_registry.csv",
                "outputs/tables/ratewall_corporate_net_interest_cashflow_bridge.csv",
                "outputs/tables/ratewall_working_capital_cost_channel_diagnostic.csv",
                "outputs/tables/ratewall_term_structure_pricing_carry_diagnostic.csv",
                "outputs/tables/ratewall_interest_channel_module_registry.csv",
                "outputs/tables/ratewall_interest_channel_completion_matrix.csv",
                "outputs/tables/ratewall_dynamic_scenario_paths.csv",
                "outputs/tables/ratewall_tdc_ea_tdc_pass_through_calibration_import.csv",
                "outputs/tables/ratewall_tdc_ea_tdc_pass_through_regime_validation_import.csv",
                "outputs/tables/ratewall_tdc_deposit_pass_through_source_import.csv",
                "outputs/tables/ratewall_tdc_deposit_pass_through_regime_scenarios.csv",
                "outputs/tables/ratewall_tdc_deposit_pass_through_scenario_contract.csv",
                "outputs/tables/ratewall_tdc_deposit_pass_through_trigger_validation_preflight.csv",
                "outputs/tables/ratewall_tdc_deposit_pass_through_scenario_contract_invariant_audit.csv",
                "outputs/tables/ratewall_tdc_liquidity_regime_trigger_evidence.csv",
                "outputs/tables/ratewall_tdc_liquidity_regime_trigger_promotion_protocol.csv",
                "outputs/tables/ratewall_tdc_liquidity_regime_trigger_validation_evidence.csv",
                "outputs/tables/ratewall_dynamic_scenario_path_consistency_diagnostic.csv",
                "outputs/tables/ratewall_dynamic_offset_ratio_path.csv",
                "outputs/tables/ratewall_scenario_crossing_diagnostic.csv",
                "outputs/tables/ratewall_dynamic_sensitivity_frontier.csv",
                "outputs/tables/ratewall_dynamic_scenario_family_registry.csv",
                "outputs/tables/ratewall_dynamic_uncertainty_envelope.csv",
                "outputs/tables/ratewall_tdc_materialization_semantic_summary.csv",
                "outputs/tables/ratewall_dynamic_crossing_robustness.csv",
                "outputs/tables/ratewall_flow_stage_decomposition.csv",
                "outputs/tables/ratewall_gross_interest_subchannels.csv",
                "outputs/tables/ratewall_public_finance_adjustment.csv",
                "outputs/tables/ratewall_net_countervailing_channels.csv",
                "outputs/tables/ratewall_wall_hit_scenarios.csv",
                "outputs/tables/ratewall_threshold_solver.csv",
                "outputs/tables/ratewall_assumption_sensitivity.csv",
                "outputs/tables/ratewall_parameter_frontier.csv",
                "outputs/tables/ratewall_minimum_conditions_to_hit_wall.csv",
                "outputs/tables/ratewall_hit_fragility_frontier.csv",
                "outputs/tables/ratewall_frontier_driver_ranking.csv",
                "outputs/tables/ratewall_assumption_mode_driver_dominance_matrix.csv",
                "outputs/tables/ratewall_assumption_mode_pairwise_sensitivity_matrix.csv",
                "outputs/tables/ratewall_backend_invariant_guardrail_audit.csv",
                "outputs/tables/ratewall_backend_completion_verdict.csv",
                "outputs/tables/ratewall_paper_channel_map.csv",
                "outputs/tables/ratewall_paper_canonical_scenario_results.csv",
                "outputs/tables/ratewall_paper_tdc_dynamic_contribution.csv",
                "outputs/tables/ratewall_paper_parameter_justification.csv",
                "outputs/tables/ratewall_paper_sensitivity_summary.csv",
                "outputs/tables/ratewall_paper_disabled_claims_appendix.csv",
                "outputs/tables/ratewall_paper_financialization_interpretation.csv",
                "outputs/tables/ratewall_paper_support_invariant_audit.csv",
                "outputs/tables/ratewall_backend_accounting_identity_audit.csv",
                "outputs/tables/ratewall_paper_scenario_accounting_bridge.csv",
                "outputs/tables/ratewall_paper_dynamic_scenario_summary.csv",
                "outputs/tables/ratewall_conventional_drag_decomposition.csv",
                "outputs/tables/ratewall_split_denominator_comparison.csv",
                "outputs/tables/ratewall_denominator_sensitivity.csv",
                "outputs/tables/ratewall_split_denominator_uncertainty.csv",
                "outputs/tables/ratewall_split_denominator_regime_stability.csv",
                "outputs/tables/ratewall_denominator_literature_matrix.csv",
                "outputs/tables/ratewall_split_denominator_joint_uncertainty.csv",
                "outputs/tables/ratewall_split_denominator_joint_regime_stability.csv",
                "outputs/tables/ratewall_denominator_classifier_comparison.csv",
                "outputs/tables/ratewall_backend_model_readiness_gate.csv",
                "outputs/tables/ratewall_chapter_readiness_self_audit.csv",
                "outputs/tables/ratewall_financialized_balance_sheet_channel.csv",
                "outputs/tables/ratewall_equity_transmission_channel_map.csv",
                "outputs/tables/ratewall_equity_exposure_matrix.csv",
                "outputs/tables/ratewall_equity_sensitivity_diagnostic.csv",
                "outputs/tables/ratewall_equity_claim_status.csv",
                "outputs/tables/ratewall_equity_evidence_workplan.csv",
                "outputs/tables/ratewall_parameter_packs.csv",
                "outputs/tables/ratewall_frontier_summary.csv",
                "outputs/tables/ratewall_regime_map.csv",
                "outputs/tables/ratewall_assumption_mode_interpretation.csv",
                "outputs/tables/ratewall_prior_stack_diagnostic.csv",
                "outputs/tables/ratewall_scenario_ladder.csv",
                "outputs/tables/ratewall_model_adequacy_matrix.csv",
                "outputs/tables/ratewall_assumption_mode_claim_boundary_audit.csv",
                "outputs/reports/ratewall_assumption_engine_memo.md",
                "outputs/reports/ratewall_assumption_mode_theory_chapter.md",
                "outputs/reports/ratewall_assumption_mode_model_audit_packet.md",
                "outputs/reports/ratewall_assumption_mode_critique_response.md",
                "outputs/reports/ratewall_professor_model_review_prompt.md",
                "outputs/reports/ratewall_interest_channel_expansion_plan.md",
                "outputs/reports/ratewall_backend_completion_readiness_report.md",
                "outputs/reports/ratewall_assumption_mode_v1_stage_completion_report.md",
                "outputs/reports/ratewall_assumption_mode_post_closure_boundary_memo.md",
                "outputs/reports/ratewall_paper_support_backend_appendix.md",
                "outputs/reports/ratewall_financialization_interpretation_memo.md",
                "outputs/reports/ratewall_dynamic_assumption_mode_equations.md",
                "outputs/reports/ratewall_split_denominator_evidence_workplan.md",
                "outputs/reports/ratewall_denominator_evidence_review.md",
                "outputs/reports/ratewall_equity_transmission_attenuation_memo.md",
                "outputs/reports/ratewall_equity_evidence_workplan.md",
                "configs/ratewall_assumption_sets.yml",
                "configs/ratewall_parameter_packs.yml",
                "configs/ratewall_assumption_source_backing_overrides.yml",
            ],
            "empirical_estimates": [
                "outputs/tables/ratewall_empirical_outcome_panel.csv",
                "outputs/tables/ratewall_empirical_results.csv",
                "outputs/tables/ratewall_causal_identification_audit.csv",
                "outputs/tables/ratewall_causal_defensibility_blocker.csv",
                "outputs/tables/ratewall_empirical_robustness_manifest.json",
                "outputs/tables/ratewall_event_study_support_diagnostics.csv",
                "outputs/tables/ratewall_event_study_robustness.csv",
                "outputs/tables/ratewall_submission_identification_decision.csv",
                "outputs/tables/ratewall_dynamic_lp_feasibility_diagnostics.csv",
                "outputs/tables/ratewall_proxy_svar_feasibility_diagnostics.csv",
                "outputs/tables/ratewall_dynamic_causal_final_blocker.csv",
                "outputs/tables/ratewall_journal_submission_manifest.json",
                "outputs/tables/ratewall_event_study_hac_diagnostics.csv",
                "outputs/tables/ratewall_pretrend_placebo_diagnostics.csv",
                "outputs/tables/ratewall_dynamic_identification_promotion_contract_disabled.csv",
                "outputs/tables/ratewall_release_4_0_dynamic_causal_final_blocker.csv",
                "outputs/tables/ratewall_release_4_0_submission_checklist.csv",
                "outputs/tables/ratewall_external_review_issue_matrix.csv",
                "outputs/tables/ratewall_release_4_0_submission_manifest.json",
                "outputs/tables/ratewall_controlled_dynamic_lp_panel.csv",
                "outputs/tables/ratewall_controlled_dynamic_lp_results.csv",
                "outputs/tables/ratewall_controlled_dynamic_lp_support_diagnostics.csv",
                "outputs/tables/ratewall_release_5_0_identification_decision.csv",
                "outputs/tables/ratewall_release_5_0_proxy_svar_final_blocker.csv",
                "outputs/tables/ratewall_release_5_0_dynamic_causal_manifest.json",
                "outputs/tables/ratewall_proxy_svar_system_panel.csv",
                "outputs/tables/ratewall_proxy_svar_proxy_relevance_diagnostics.csv",
                "outputs/tables/ratewall_proxy_svar_residual_diagnostics.csv",
                "outputs/tables/ratewall_proxy_svar_timing_support_diagnostics.csv",
                "outputs/tables/ratewall_release_6_0_identification_decision.csv",
                "outputs/tables/ratewall_release_6_0_proxy_svar_final_blocker.csv",
                "outputs/tables/ratewall_release_6_0_valuation_incidence_frontier_disabled.csv",
                "outputs/tables/ratewall_release_6_0_system_identification_manifest.json",
                "outputs/tables/ratewall_release_7_0_var_lag_selection.csv",
                "outputs/tables/ratewall_release_7_0_reduced_form_system_estimates.csv",
                "outputs/tables/ratewall_release_7_0_residual_covariance.csv",
                "outputs/tables/ratewall_release_7_0_proxy_relevance_support.csv",
                "outputs/tables/ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv",
                "outputs/tables/ratewall_release_7_0_claim_promotion_contract_disabled.csv",
                "outputs/tables/ratewall_release_7_0_identification_decision.csv",
                "outputs/tables/ratewall_release_7_0_proxy_svar_final_blocker.csv",
                "outputs/tables/ratewall_release_7_0_system_identification_manifest.json",
                "outputs/tables/ratewall_release_8_0_proxy_specification_audit.csv",
                "outputs/tables/ratewall_release_8_0_structural_gap_ledger.csv",
                "outputs/tables/ratewall_release_8_0_nonpromotion_proof.csv",
                "outputs/tables/ratewall_release_8_0_identification_decision.csv",
                "outputs/tables/ratewall_release_8_0_system_identification_manifest.json",
                "outputs/tables/ratewall_release_9_0_external_proxy_source_registry.csv",
                "outputs/tables/ratewall_release_9_0_external_proxy_support_audit.csv",
                "outputs/tables/ratewall_release_9_0_structural_identification_decision.csv",
                "outputs/tables/ratewall_release_9_0_final_nonpromotion_proof.csv",
                "outputs/tables/ratewall_release_9_0_structural_identification_manifest.json",
                "outputs/reports/ratewall_causal_identification_appendix.md",
                "outputs/reports/ratewall_reviewer_limitations_memo.md",
                "outputs/reports/ratewall_submission_causal_appendix.md",
                "outputs/reports/ratewall_external_review_response_packet.md",
                "outputs/reports/ratewall_submission_appendix_index.md",
                "outputs/reports/ratewall_journal_submission_appendix.md",
                "outputs/reports/ratewall_dynamic_causal_blocker_memo.md",
                "outputs/reports/ratewall_referee_response_compendium.md",
                "outputs/reports/ratewall_release_3_0_cover_note.md",
                "outputs/reports/ratewall_release_4_0_final_submission_memo.md",
                "outputs/reports/ratewall_release_4_0_referee_packet.md",
                "outputs/reports/ratewall_release_4_0_identification_frontier_appendix.md",
                "outputs/reports/ratewall_release_5_0_dynamic_lp_appendix.md",
                "outputs/reports/ratewall_release_5_0_referee_response.md",
                "outputs/reports/ratewall_release_6_0_proxy_svar_system_appendix.md",
                "outputs/reports/ratewall_release_6_0_reviewer_response.md",
                "outputs/reports/ratewall_release_7_0_system_identification_appendix.md",
                "outputs/reports/ratewall_release_7_0_external_review_packet.md",
                "outputs/reports/ratewall_release_8_0_system_nonpromotion_appendix.md",
                "outputs/reports/ratewall_release_8_0_reviewer_response.md",
                "outputs/reports/ratewall_release_9_0_structural_boundary_appendix.md",
                "outputs/reports/ratewall_release_9_0_external_proxy_review_packet.md",
                "outputs/reports/ratewall_tdc_deposit_channel_appendix.md",
            ],
            "valuation_readiness": [
                "outputs/tables/treasury_valuation_readiness_coverage.csv",
                "outputs/tables/treasury_valuation_engine_readiness_gate.csv",
            ],
            "release_reports": [
                str(artifacts.final_paper),
                str(artifacts.final_paper_quarto),
                str(artifacts.slide_deck),
                str(artifacts.slide_deck_quarto),
                "outputs/reports/ratewall_theory_of_change.md",
                str(artifacts.source_appendix),
                str(artifacts.empirical_appendix),
                str(artifacts.limitations_appendix),
                str(artifacts.validation_package),
                str(artifacts.public_readme),
                str(artifacts.release_index),
                str(artifacts.reproduction_commands),
                str(artifacts.public_release_checklist),
                str(artifacts.publication_claim_decision_memo),
                str(artifacts.release_16_bounded_publication_closeout_memo),
                str(artifacts.release_16_reviewer_blocker_text),
                str(artifacts.release_17_external_review_packet),
                str(artifacts.release_17_publication_polish_memo),
                str(artifacts.release_18_publication_freeze_memo),
                str(artifacts.release_19_post_audit_methodology_memo),
                str(artifacts.release_20_submission_readiness_memo),
                str(artifacts.release_21_backend_closeout_memo),
                str(artifacts.figure_plate),
                str(artifacts.table_plate),
                str(artifacts.citation_metadata),
                str(artifacts.package_smoke),
                str(artifacts.source_archive),
            ],
        },
        "hard_boundaries": {
            "disabled_claim_switches": {
                "empirical_claim_enabled": False,
                "policy_failure_claim_enabled": False,
                "pricing_output_enabled": False,
                "incidence_claim_enabled": False,
                "welfare_claim_enabled": False,
                "tax_output_enabled": False,
                "mpc_output_enabled": False,
                "holder_allocation_enabled": False,
                "reset_calendar_construction_enabled": False,
                "raw_rate_shock_enabled": False,
                "causal_financialization_claim_enabled": False,
            },
            "higher_rates_always_raise_inflation": False,
            "fed_stopped_working": False,
            "higher_rates_always_raise_deposits": False,
            "deficits_always_create_deposits": False,
            "raw_rate_change_shocks": False,
            "pricing_output_enabled": False,
            "welfare_incidence_enabled": False,
            "causal_lp_proxy_svar_claim_enabled": False,
            "dynamic_lp_claim_enabled": False,
            "controlled_dynamic_lp_appendix_enabled": any(
                row.get("controlled_dynamic_lp_appendix_enabled") == "true"
                for row in _rows(context, "release_5_decision")
            ),
            "proxy_svar_claim_enabled": False,
            "system_identification_claim_enabled": False,
            "dynamic_identification_promotion_enabled": False,
            "expanded_external_proxy_frontier_enabled": bool(
                _rows(context, "release_9_proxy_registry")
            ),
            "defensible_structural_appendix_enabled": False,
            "reduced_form_system_diagnostics_enabled": bool(
                _rows(context, "release_7_reduced_form_estimates")
            ),
            "bounded_event_study_appendix_enabled": True,
            "valuation_incidence_claim_enabled": False,
            "reset_calendar_construction_enabled": False,
            "financialization_causal_claim_enabled": False,
            "threshold_policy_failure_claim_enabled": False,
        },
    }
    _split_empirical_diagnostics_layer(payload)
    return payload


def _split_empirical_diagnostics_layer(payload: dict[str, object]) -> None:
    layers = payload.get("artifact_layers", {})
    if not isinstance(layers, dict):
        return
    empirical = layers.get("empirical_estimates", [])
    if not isinstance(empirical, list):
        return
    estimate_paths: list[str] = []
    diagnostic_paths: list[str] = []
    for artifact in empirical:
        artifact_text = str(artifact)
        if _release_empirical_diagnostic_or_blocker(artifact_text):
            diagnostic_paths.append(artifact_text)
        else:
            estimate_paths.append(artifact_text)
    layers["empirical_estimates"] = estimate_paths
    if diagnostic_paths:
        layers["empirical_diagnostics_and_blockers"] = diagnostic_paths


def _release_empirical_diagnostic_or_blocker(artifact_path: str) -> bool:
    name = Path(artifact_path).name.lower()
    return any(
        token in name
        for token in (
            "audit",
            "blocker",
            "diagnostic",
            "manifest",
            "decision",
            "checklist",
            "contract_disabled",
            "support",
            "relevance",
            "timing",
            "proof",
            "reviewer",
            "review",
            "robustness",
            "appendix",
            "response",
            "frontier",
            "boundary",
            "memo",
            "packet",
            "cover_note",
        )
    )


def _archival_manifest_payload(
    *,
    context: dict[str, object],
    artifacts: ReleaseArtifacts,
    archive_path: Path,
) -> dict[str, object]:
    files = _unique_paths(_release_archive_files(context, artifacts))
    file_records = []
    for path in files:
        if path.exists() and path.is_file():
            file_records.append(
                {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
            )
    snapshot = Path(context["snapshot_bundle"])
    snapshot_record = {}
    if snapshot.exists() and snapshot.is_file():
        snapshot_record = {
            "path": str(snapshot),
            "bytes": snapshot.stat().st_size,
            "sha256": _sha256(snapshot),
            "archive_policy": "embedded_as_data/raw/ratewall_snapshot.json",
        }
    return {
        "schema": "ratewall.release_archive_manifest.v1",
        "generated_at": utc_now_iso(),
        "source_archive": {
            "path": str(archive_path),
            "bytes": archive_path.stat().st_size if archive_path.exists() else 0,
            "sha256": _sha256(archive_path) if archive_path.exists() else "",
        },
        "snapshot_bundle": snapshot_record,
        "file_count": len(file_records),
        "files": file_records,
        "claim_boundary": {
            "archive_is_release_packaging_not_new_evidence": True,
            "pricing_output_enabled": False,
            "incidence_output_enabled": False,
            "dynamic_lp_claim_enabled": False,
            "controlled_dynamic_lp_appendix_enabled": any(
                row.get("controlled_dynamic_lp_appendix_enabled") == "true"
                for row in _rows(context, "release_5_decision")
            ),
            "proxy_svar_claim_enabled": False,
            "system_identification_claim_enabled": False,
            "dynamic_identification_promotion_enabled": False,
            "expanded_external_proxy_frontier_enabled": bool(
                _rows(context, "release_9_proxy_registry")
            ),
            "defensible_structural_appendix_enabled": False,
            "valuation_incidence_claim_enabled": False,
            "reset_calendar_construction_enabled": False,
            "financialization_causal_claim_enabled": False,
            "threshold_policy_failure_claim_enabled": False,
        },
    }


RELEASE_23_ARCHIVE_VERIFICATION_FIELDS = [
    "audit_component",
    "audit_status",
    "evidence_artifact",
    "finding",
    "failure_action",
    "claim_boundary",
]


def _release_23_reproducibility_manifest_payload(
    *,
    context: dict[str, object],
    artifacts: ReleaseArtifacts,
) -> dict[str, object]:
    records = []
    for path in _unique_paths(_release_archive_files(context, artifacts)):
        if not path.exists() or not path.is_file():
            continue
        if path in {
            artifacts.release_23_reproducibility_manifest,
            artifacts.release_23_archive_verification_audit,
            Path(context["tables_dir"])
            / "ratewall_release_archive_reproducibility_audit.csv",
        }:
            continue
        records.append(
            {
                "archive_path": _archive_name_for_path(
                    path,
                    snapshot_path=Path(context["snapshot_bundle"]).resolve(),
                ),
                "source_path": _archive_name_for_path(
                    path,
                    snapshot_path=Path(context["snapshot_bundle"]).resolve(),
                ),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return {
        "schema": "ratewall.release_23_archive_reproducibility_manifest.v1",
        "generated_at": utc_now_iso(),
        "snapshot_bundle": "data/raw/ratewall_snapshot.json",
        "file_count": len(records),
        "files": records,
        "manifest_self_excluded_from_hash_records": True,
        "claim_boundary": {
            "hash_manifest_is_reproducibility_evidence_not_new_economic_claim": True,
            "pricing_output_enabled": False,
            "incidence_output_enabled": False,
            "policy_failure_claim_enabled": False,
        },
    }


def _release_23_archive_verification_rows(
    *,
    archive_path: Path,
    manifest_path: Path,
) -> list[dict[str, str]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = []
    mismatched = []
    absolute = []
    unsafe = []
    duplicate_manifest_paths = []
    seen_manifest_paths = set()
    unsafe_language_hits = []
    missing_required_gate_evidence = []
    compiled_render_artifacts = []
    with zipfile.ZipFile(archive_path) as archive:
        archive_names = archive.namelist()
        names = set(archive_names)
        compiled_render_artifacts = sorted(
            names
            & {
                "outputs/reports/ratewall_final_paper.pdf",
                "outputs/reports/ratewall_public_deck.pptx",
            }
        )
        duplicate_zip_names = sorted(
            name for name, count in Counter(archive_names).items() if count > 1
        )
        for record in manifest.get("files", []):
            archive_name = str(record.get("archive_path", ""))
            source_path = str(record.get("source_path", ""))
            if archive_name in seen_manifest_paths:
                duplicate_manifest_paths.append(archive_name)
            seen_manifest_paths.add(archive_name)
            for candidate in (archive_name, source_path):
                parts = Path(candidate).parts
                if candidate.startswith("/"):
                    absolute.append(candidate)
                if ".." in parts:
                    unsafe.append(candidate)
            if archive_name not in names:
                missing.append(archive_name)
                continue
            digest = hashlib.sha256(archive.read(archive_name)).hexdigest()
            if digest != record.get("sha256"):
                mismatched.append(archive_name)
        allowed_unlisted = {
            "outputs/tables/ratewall_release_archive_reproducibility_audit.csv",
            "outputs/tables/ratewall_release_23_reproducibility_hash_manifest.json",
            "outputs/tables/ratewall_release_23_archive_hash_verification_audit.csv",
        }
        unlisted = sorted(names - seen_manifest_paths - allowed_unlisted)
        required_gate_evidence = {
            "outputs/tables/treasury_maturity_ladder.csv",
            "outputs/tables/treasury_mspd_reconciliation.csv",
            "outputs/tables/ratewall_release_22_core_output_source_gate.csv",
        }
        missing_required_gate_evidence = sorted(required_gate_evidence - names)
        for name in names:
            if not _archive_text_lint_target(name):
                continue
            text = archive.read(name).decode("utf-8", errors="ignore")
            for phrase in _forbidden_release_23_phrases():
                if phrase in text:
                    unsafe_language_hits.append(f"{name}:{phrase}")
    ok = not (
        missing
        or mismatched
        or absolute
        or unsafe
        or duplicate_manifest_paths
        or duplicate_zip_names
        or unlisted
        or unsafe_language_hits
        or missing_required_gate_evidence
        or compiled_render_artifacts
    )
    return [
        {
            "audit_component": "release_23_source_archive_self_verification",
            "audit_status": "pass" if ok else "fail",
            "evidence_artifact": f"{archive_path};{manifest_path}",
            "finding": (
                "Release archive entries listed in the Release 23 manifest exist, "
                "hash-match, use relative safe paths, have no duplicate archive or "
                "manifest paths, and contain only explicitly allowed self-excluded "
                "manifest/audit extras."
                if ok
                else (
                    f"missing={len(missing)};mismatched={len(mismatched)};"
                    f"absolute_paths={len(absolute)};unsafe_paths={len(unsafe)};"
                    f"duplicate_manifest_paths={len(duplicate_manifest_paths)};"
                    f"duplicate_zip_names={len(duplicate_zip_names)};"
                    f"unlisted={len(unlisted)};"
                    f"unsafe_language_hits={len(unsafe_language_hits)};"
                    f"missing_required_gate_evidence={len(missing_required_gate_evidence)};"
                    f"compiled_render_artifacts={len(compiled_render_artifacts)}"
                )
            ),
            "failure_action": "block release until the archive verifies against the final manifest",
            "claim_boundary": "release_23_archive_reproducibility_not_economic_claim",
        }
    ]


def _archive_text_lint_target(name: str) -> bool:
    return (
        name == "README.md"
        or name.startswith("outputs/reports/")
        or name
        in {
            "outputs/tables/ratewall_scenarios.csv",
            "outputs/tables/ratewall_score_dashboard.csv",
            "outputs/tables/ratewall_tdc_ru_financing_deposit_impulse.csv",
            "outputs/tables/ratewall_threshold_calibrated_simulation.csv",
        }
    )


def _forbidden_release_23_phrases() -> tuple[str, ...]:
    return (
        "source_backed_mechanical_index",
        "generated_in_databook_from_source_backed",
        "source-backed accounting",
        "source-backed release package",
        "source-backed paper-support package",
        "source-backed tables",
        "Source-backed calibration-range",
        "source_backed_range_label",
        "source-backed and sibling-derived calibration",
        "source-backed or sibling-derived calibration",
        "live_security_level_source_backed",
        "generated_from_live_snapshot",
    )


def _archive_name_for_path(path: Path, *, snapshot_path: Path) -> str:
    if path.resolve() == snapshot_path:
        return "data/raw/ratewall_snapshot.json"
    parts = path.parts
    if "outputs" in parts:
        return Path(*parts[parts.index("outputs") :]).as_posix()
    return path.as_posix()


def _planned_source_archive_paths(
    context: dict[str, object], artifacts: ReleaseArtifacts
) -> set[str]:
    snapshot_path = Path(context["snapshot_bundle"]).resolve()
    return {
        _archive_name_for_path(path, snapshot_path=snapshot_path)
        for path in _unique_paths(_release_archive_files(context, artifacts))
        if path.exists() and path.is_file()
    }


def _write_source_archive(
    *,
    archive_path: Path,
    context: dict[str, object],
    artifacts: ReleaseArtifacts,
) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    files = _unique_paths(_release_archive_files(context, artifacts))
    snapshot_path = Path(context["snapshot_bundle"]).resolve()
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for file_path in files:
            if file_path.exists() and file_path.is_file():
                arcname = _archive_name_for_path(file_path, snapshot_path=snapshot_path)
                archive.write(file_path, arcname)


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    seen = set()
    unique = []
    for path in paths:
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _release_archive_files(
    context: dict[str, object], artifacts: ReleaseArtifacts
) -> list[Path]:
    tables_dir = Path(context["tables_dir"])
    reports_dir = Path(context["reports_dir"])
    source_files = [
        *sorted(Path("src").rglob("*.py")),
        *sorted(Path("tests").rglob("*.py")),
        *sorted(Path("configs").glob("*.yml")),
        *sorted(Path("configs").glob("*.yaml")),
        *sorted(Path("scripts").glob("*.py")),
    ]
    files = [
        *source_files,
        Path("README.md"),
        Path("pyproject.toml"),
        Path("uv.lock"),
        *sorted(Path("data/raw").rglob("*")),
        Path(context["snapshot_bundle"]),
        Path("data/raw/ratewall_pce_dpi_source_refresh_snapshot.json"),
        Path("data/raw/current_demand_gdp_share/current_demand_gdp_share_snapshot.json"),
        Path(
            "data/raw/current_demand_gdp_share/"
            "fspdp_component_decomposition_snapshot.json"
        ),
        Path(
            "data/raw/current_demand_gdp_share/fspdp_official_component_sources/"
            "fspdp_official_component_sources_manifest.json"
        ),
        Path("data/raw/current_demand_gdp_share/LA0000031Q027SBEA.csv"),
        Path("data/raw/current_demand_gdp_share/LB0000031Q020SBEA.csv"),
        Path("data/raw/current_demand_gdp_share/GDP.csv"),
        Path("data/raw/current_demand_gdp_share/GDPC1.csv"),
        Path("data/raw/current_demand_gdp_share/PCEC.csv"),
        Path("data/raw/current_demand_gdp_share/PCECC96.csv"),
        Path("data/raw/current_demand_gdp_share/FPI.csv"),
        Path("data/raw/current_demand_gdp_share/FPIC1.csv"),
        *sorted(
            Path("data/raw/current_demand_gdp_share")
            .joinpath("fspdp_component_decomposition_dbnomics")
            .glob("*.json")
        ),
        *sorted(
            Path("data/raw/current_demand_gdp_share")
            .joinpath("fspdp_official_component_sources/fred_csv")
            .glob("*.csv")
        ),
        *sorted(Path("data/raw/residualized_ffr_bridge").rglob("*")),
        Path("data/raw/ratewall_sibling_calibration/tdcsim/tdcsim_ratewall_manifest.json"),
        Path(
            "data/raw/ratewall_sibling_calibration/tdcsim/"
            "tdcsim_ratewall_quarterly_summary.csv"
        ),
        Path(
            "data/raw/ratewall_sibling_calibration/tdcsim/"
            "tdcsim_ratewall_quarterly_components.csv"
        ),
        Path(
            "data/raw/ratewall_sibling_calibration/tdcsim/"
            "tdcsim_ratewall_source_registry.csv"
        ),
        Path(
            "data/raw/ratewall_sibling_calibration/rowflow/"
            "rowflow_ratewall_foreign_route_support.csv"
        ),
        Path(
            "data/raw/ratewall_sibling_calibration/buycurve/"
            "buycurve_ratewall_auction_buyer_mix_support.csv"
        ),
        Path(
            "data/raw/ratewall_sibling_calibration/bidbridge/"
            "bidbridge_ratewall_dealer_warehousing_support.csv"
        ),
        Path(
            "data/raw/ratewall_sibling_calibration/tdcsim_assumption_mode/"
            "tdcsim_route_component_support_registry.csv"
        ),
        Path(
            "data/raw/ratewall_sibling_calibration/tdcsim_assumption_mode/"
            "tdcsim_route_component_verdict.csv"
        ),
        Path(
            "data/raw/ratewall_sibling_calibration/tdcsim_assumption_mode/"
            "tdcsim_assumption_mode_manifest.json"
        ),
        artifacts.final_paper,
        artifacts.final_paper_quarto,
        artifacts.slide_deck,
        artifacts.slide_deck_quarto,
        reports_dir / "ratewall_theory_of_change.md",
        reports_dir / "ratewall_assumption_engine_memo.md",
        reports_dir / "ratewall_assumption_mode_theory_chapter.md",
        reports_dir / "ratewall_assumption_mode_model_audit_packet.md",
        reports_dir / "ratewall_assumption_mode_critique_response.md",
        reports_dir / "ratewall_professor_model_review_prompt.md",
        reports_dir / "ratewall_interest_channel_expansion_plan.md",
        reports_dir / "ratewall_backend_completion_readiness_report.md",
        reports_dir / "ratewall_assumption_mode_v1_stage_completion_report.md",
        reports_dir / "ratewall_assumption_mode_post_closure_boundary_memo.md",
        reports_dir / "ratewall_paper_support_backend_appendix.md",
        reports_dir / "ratewall_financialization_proxy_backend_audit.md",
        reports_dir / "ratewall_financialization_interpretation_memo.md",
        reports_dir / "ratewall_split_denominator_evidence_workplan.md",
        reports_dir / "ratewall_denominator_evidence_review.md",
        artifacts.source_appendix,
        artifacts.empirical_appendix,
        artifacts.limitations_appendix,
        artifacts.validation_package,
        artifacts.public_readme,
        artifacts.release_index,
        artifacts.reproduction_commands,
        artifacts.public_release_checklist,
        artifacts.publication_claim_decision_memo,
        artifacts.release_16_bounded_publication_closeout_memo,
        artifacts.release_16_reviewer_blocker_text,
        artifacts.release_17_external_review_packet,
        artifacts.release_17_publication_polish_memo,
        artifacts.release_18_publication_freeze_memo,
        artifacts.release_19_post_audit_methodology_memo,
        artifacts.release_20_submission_readiness_memo,
        artifacts.release_21_backend_closeout_memo,
        artifacts.release_22_backend_fix_memo,
        artifacts.release_23_backend_fix_memo,
        artifacts.release_23_reproducibility_manifest,
        artifacts.figure_plate,
        artifacts.table_plate,
        reports_dir / "ratewall_runtime_annual_flow_support_offset_reviewer_packet.md",
        reports_dir / "ratewall_runtime_annual_flow_support_offset_limitations.md",
        artifacts.citation_metadata,
        artifacts.package_smoke,
        reports_dir / "ratewall_tdc_deposit_channel_appendix.md",
        reports_dir / "ratewall_equity_transmission_attenuation_memo.md",
        reports_dir / "ratewall_equity_evidence_workplan.md",
        tables_dir / "source_provenance.json",
        tables_dir / "ratewall_release_manifest.json",
        tables_dir / "ratewall_claim_boundary_audit.csv",
        tables_dir / "treasury_maturity_ladder.csv",
        tables_dir / "treasury_mspd_reconciliation.csv",
        tables_dir / "ratewall_100bps_impulse.csv",
        tables_dir / "ratewall_databook_metrics.csv",
        tables_dir / "ratewall_scenarios.csv",
        tables_dir / "ratewall_tdc_deposit_channel_ledger.csv",
        tables_dir / "ratewall_tdc_ru_financing_deposit_impulse.csv",
        tables_dir / "ratewall_tdc_historical_panel.csv",
        tables_dir / "ratewall_deposit_pricing_pass_through_context.csv",
        tables_dir / "ratewall_tdc_historical_reconciliation.csv",
        tables_dir / "ratewall_tdcest_historical_estimator_bridge.csv",
        tables_dir / "ratewall_tdcest_monetary_route_bridge.csv",
        tables_dir / "ratewall_tdcest_mmf_route_split_context.csv",
        tables_dir / "ratewall_tdcest_z1_domestic_nonbank_sector_context.csv",
        tables_dir / "ratewall_tdc_rolling_pass_through_context.csv",
        tables_dir / "ratewall_historical_tdc_wall_ratio_path.csv",
        tables_dir / "ratewall_historical_assumption_mode_tdc_wall_ratio_path.csv",
        tables_dir / "ratewall_tdc_other_component_bridge.csv",
        tables_dir / "ratewall_tdc_deposit_credit_decomposition.csv",
        tables_dir / "ratewall_tdc_double_count_guardrail.csv",
        tables_dir / "ratewall_tdc_net_ratewall_effect.csv",
        tables_dir / "ratewall_tdc_materialization_semantic_summary.csv",
        tables_dir / "ratewall_tdc_historical_source_contract.csv",
        tables_dir / "ratewall_tdc_historical_selected_series.csv",
        tables_dir / "ratewall_canonical_tdc_accounting_path.csv",
        tables_dir / "ratewall_canonical_tdc_stitched_accounting_path.csv",
        tables_dir / "ratewall_canonical_tdc_accounting_source_hierarchy_audit.csv",
        tables_dir / "ratewall_tdcsim_projection_contract_bridge.csv",
        tables_dir / "ratewall_tdcsim_domestic_nonbank_funding_classification.csv",
        tables_dir / "ratewall_tdcsim_private_route_sensitivity_ingest.csv",
        tables_dir / "ratewall_tdcsim_assumption_mode_support_ingest.csv",
        tables_dir / "ratewall_tdcsim_assumption_mode_claim_gate.csv",
        tables_dir / "ratewall_tdcsim_assumption_mode_forecast_private_route_envelope.csv",
        tables_dir / "ratewall_tdcsim_assumption_mode_forecast_private_route_claim_gate.csv",
        tables_dir / "ratewall_qrawatch_tdcsim_scenario_registry.csv",
        tables_dir / "ratewall_qrawatch_tdcsim_provenance_audit.csv",
        tables_dir / "ratewall_qrawatch_tdcsim_bridge_invariant_audit.csv",
        tables_dir / "ratewall_tdc_forward_projection_surface.csv",
        tables_dir / "ratewall_tdc_forward_component_audit.csv",
        tables_dir / "ratewall_tdc_forward_overlap_guardrail.csv",
        tables_dir / "ratewall_tdc_forward_invariant_audit.csv",
        tables_dir / "ratewall_tdc_forward_assumption_registry.csv",
        tables_dir / "ratewall_tdc_forward_scenario_decomposition.csv",
        tables_dir / "ratewall_forecast_holder_tdc_consistency_bridge.csv",
        tables_dir / "ratewall_threshold_simulation.csv",
        tables_dir / "ratewall_threshold_calibration_ranges.csv",
        tables_dir / "ratewall_threshold_calibrated_simulation.csv",
        tables_dir / "ratewall_du_ru_tga_calibration_bridge.csv",
        tables_dir / "ratewall_interest_income_mpc_calibration_registry.csv",
        tables_dir / "ratewall_interest_income_public_proxy_catalog.csv",
        tables_dir / "ratewall_interest_income_proxy_range_registry.csv",
        tables_dir / "ratewall_interest_income_claim_boundary_audit.csv",
        tables_dir / "ratewall_post_covid_interest_income_wall_distance.csv",
        tables_dir / "ratewall_historical_iorb_demand_proxy_path.csv",
        tables_dir / "ratewall_historical_wall_ratio_path.csv",
        tables_dir / "ratewall_historical_assumption_mode_wall_ratio_path.csv",
        tables_dir / "ratewall_assumption_sets.csv",
        tables_dir / "ratewall_condition_frontier.csv",
        tables_dir / "ratewall_offset_decomposition.csv",
        tables_dir / "ratewall_public_impulse_factorization.csv",
        tables_dir / "ratewall_public_liability_repricing_ladder.csv",
        tables_dir / "ratewall_public_liability_repricing_evidence_bridge.csv",
        tables_dir / "ratewall_public_liability_repricing_reconciliation_gap.csv",
        tables_dir / "ratewall_mspd_table3_bucket_repricing_gate.csv",
        tables_dir / "ratewall_treasury_bucket_repricing_prior_bridge.csv",
        tables_dir / "ratewall_interest_recipient_leakage_bridge.csv",
        tables_dir / "ratewall_interest_recipient_leakage_evidence_gap.csv",
        tables_dir / "ratewall_treasury_recipient_leakage_source_gate.csv",
        tables_dir / "ratewall_public_finance_timing_path.csv",
        tables_dir / "ratewall_public_finance_timing_evidence_gap.csv",
        tables_dir / "ratewall_public_finance_timing_design_test_scaffold.csv",
        tables_dir / "ratewall_safe_yield_offset_drag_pairing_gap.csv",
        tables_dir / "ratewall_bnpl_zero_interest_float_evidence_gap.csv",
        tables_dir / "ratewall_financialized_balance_sheet_evidence_gap.csv",
        tables_dir / "ratewall_firm_cash_debt_maturity_evidence_gap.csv",
        tables_dir / "ratewall_conventional_drag_channel_evidence_gap.csv",
        tables_dir / "ratewall_conventional_drag_source_design_gate.csv",
        tables_dir / "ratewall_denominator_response_design_scaffold.csv",
        tables_dir / "ratewall_denominator_response_design_test_scaffold.csv",
        tables_dir / "ratewall_denominator_response_gate_attempt.csv",
        tables_dir / "ratewall_denominator_aligned_response_panel_scaffold.csv",
        tables_dir / "ratewall_denominator_event_outcome_cell_diagnostic.csv",
        tables_dir / "ratewall_denominator_event_outcome_panel_value_diagnostic.csv",
        tables_dir / "ratewall_denominator_event_level_response_panel.csv",
        tables_dir / "ratewall_denominator_uncertainty_pass_fail_review.csv",
        tables_dir / "ratewall_denominator_panel_design_test_diagnostic.csv",
        tables_dir / "ratewall_denominator_pretrend_placebo_diagnostic.csv",
        tables_dir / "ratewall_denominator_shock_relevance_diagnostic.csv",
        tables_dir / "ratewall_denominator_sign_consistency_diagnostic.csv",
        tables_dir / "ratewall_denominator_horizon_sensitivity_diagnostic.csv",
        tables_dir / "ratewall_denominator_outlier_window_robustness_diagnostic.csv",
        tables_dir / "ratewall_denominator_design_readiness_decision.csv",
        tables_dir / "ratewall_denominator_formal_design_test_result_scaffold.csv",
        tables_dir / "ratewall_denominator_formal_design_test_result.csv",
        tables_dir / "ratewall_denominator_response_estimate_diagnostic.csv",
        tables_dir / "ratewall_denominator_cross_source_design_validation.csv",
        tables_dir / "ratewall_denominator_evidence_upgrade_source_design_requirement.csv",
        tables_dir / "ratewall_denominator_evidence_upgrade_priority_queue.csv",
        tables_dir / "ratewall_denominator_evidence_upgrade_tier1_workplan.csv",
        tables_dir / "ratewall_denominator_evidence_upgrade_blocker_resolution_matrix.csv",
        tables_dir / "ratewall_denominator_evidence_upgrade_blocker_status_rollup.csv",
        tables_dir / "ratewall_conventional_drag_evidence_tranche.csv",
        tables_dir / "ratewall_baml_source_history_repair_contract.csv",
        tables_dir / "ratewall_borrowing_cost_source_object_adjudication.csv",
        tables_dir / "ratewall_baml_effective_yield_source_access_gate.csv",
        tables_dir / "ratewall_hqm_source_proxy_lane_review.csv",
        tables_dir / "ratewall_hqm_event_window_feasibility.csv",
        tables_dir / "ratewall_hqm_event_outcome_panel_values.csv",
        tables_dir / "ratewall_hqm_formal_diagnostic_gate.csv",
        tables_dir / "ratewall_hqm_promotion_protocol_gate.csv",
        tables_dir / "ratewall_hqm_policy_path_exposure_admission.csv",
        tables_dir / "ratewall_hqm_policy_path_protocol_dependency_gate.csv",
        tables_dir / "ratewall_hqm_denominator_mapping_gate.csv",
        tables_dir / "ratewall_hqm_borrowing_cost_object_comparator.csv",
        tables_dir / "ratewall_baa_event_window_support_diagnostic.csv",
        tables_dir / "ratewall_baa_hqm_mapping_diagnostic.csv",
        tables_dir / "ratewall_baa_response_diagnostic.csv",
        tables_dir / "ratewall_baa_policy_path_normalization_gate.csv",
        tables_dir / "ratewall_baa_rights_proxy_uncertainty_review.csv",
        tables_dir / "ratewall_baa_current_demand_bridge_source_audit.csv",
        tables_dir / "ratewall_hqm_current_demand_bridge_gate.csv",
        tables_dir / "ratewall_conventional_drag_demand_conversion_admission.csv",
        tables_dir / "ratewall_conventional_drag_calibration_route.csv",
        tables_dir
        / "ratewall_conventional_drag_research_parameterization_source_contract.csv",
        tables_dir
        / "ratewall_conventional_drag_research_parameterization_source_frontier.csv",
        tables_dir / "ratewall_conventional_drag_research_payload_manifest.csv",
        tables_dir
        / "ratewall_conventional_drag_research_parameterization_parser_status.csv",
        tables_dir / "ratewall_conventional_drag_research_payload_inner_inventory.csv",
        tables_dir / "ratewall_conventional_drag_research_extraction_candidate.csv",
        tables_dir / "ratewall_conventional_drag_research_extraction_gate_audit.csv",
        tables_dir / "ratewall_conventional_drag_research_extraction_gate_detail.csv",
        tables_dir / "ratewall_conventional_drag_research_source_method_bridge.csv",
        tables_dir
        / "ratewall_conventional_drag_research_source_code_interpretation.csv",
        tables_dir
        / "ratewall_conventional_drag_research_extended_source_code_interpretation.csv",
        tables_dir
        / "ratewall_conventional_drag_research_fspdp_coverage_candidate_scan.csv",
        tables_dir
        / "ratewall_conventional_drag_research_mir_component_aggregation_normalization_review.csv",
        tables_dir
        / "ratewall_conventional_drag_research_mir_component_source_variant_review.csv",
        tables_dir
        / "ratewall_conventional_drag_research_source_unit_conversion_review.csv",
        tables_dir
        / "ratewall_conventional_drag_research_mir_replication_source_unit_audit.csv",
        tables_dir
        / "ratewall_conventional_drag_research_mir_source_unit_transformation_contract.csv",
        tables_dir
        / "ratewall_conventional_drag_research_mir_target_horizon_reconciliation_contract.csv",
        tables_dir
        / "ratewall_conventional_drag_research_mir_horizon_rekeying_candidate_review.csv",
        tables_dir
        / "ratewall_conventional_drag_research_mir_h24_source_unit_audit.csv",
        tables_dir
        / "ratewall_conventional_drag_research_mir_h24_8q_rekeying_review.csv",
        tables_dir
        / "ratewall_conventional_drag_research_mir_4q8q_conversion_readiness_review.csv",
        tables_dir
        / "ratewall_conventional_drag_research_policy_path_normalization_bridge_review.csv",
        tables_dir
        / "ratewall_policy_path_research_shock_source_evidence_protocol_review.csv",
        tables_dir / "ratewall_policy_path_source_code_workbook_object_inventory.csv",
        tables_dir
        / "ratewall_policy_path_source_code_workbook_protocol_deep_review.csv",
        tables_dir
        / "ratewall_policy_path_usmpd_pca_loading_backtransform_review.csv",
        tables_dir
        / "ratewall_policy_path_usmpd_scalar_score_replication_review.csv",
        tables_dir / "ratewall_policy_path_usmpd_pca_backtransform_gate_review.csv",
        tables_dir
        / "ratewall_policy_path_usmpd_instrument_decomposition_design_review.csv",
        tables_dir / "ratewall_policy_path_bps_year_candidate_path_design_contract.csv",
        tables_dir / "ratewall_policy_path_formula_replication_source_review.csv",
        tables_dir / "ratewall_policy_path_reviewed_bps_year_protocol_gap_matrix.csv",
        tables_dir / "ratewall_policy_path_protocol_source_acquisition_work_queue.csv",
        tables_dir / "ratewall_policy_path_protocol_source_parse_execution_review.csv",
        tables_dir / "ratewall_policy_path_source_parse_synthesis_queue.csv",
        tables_dir / "ratewall_policy_path_source_parse_action_execution.csv",
        tables_dir / "ratewall_policy_path_deeper_parse_execution_review.csv",
        tables_dir / "ratewall_policy_path_protocol_candidate_draft_review.csv",
        tables_dir
        / "ratewall_policy_path_protocol_missing_evidence_acquisition_queue.csv",
        tables_dir
        / "ratewall_policy_path_protocol_missing_evidence_parse_execution_review.csv",
        tables_dir / "ratewall_policy_path_protocol_authoring_readiness_matrix.csv",
        tables_dir / "ratewall_policy_path_protocol_field_authoring_contract.csv",
        tables_dir / "ratewall_policy_path_field_evidence_resolution_queue.csv",
        tables_dir / "ratewall_ratio_layer_registry.csv",
        tables_dir / "ratewall_ratio_object_registry.csv",
        tables_dir / "ratewall_active_output_index.csv",
        tables_dir / "ratewall_paper_core_results_index.csv",
        tables_dir / "ratewall_reference_scenario_object_crosswalk.csv",
        tables_dir / "ratewall_joint_wall_probability_axis_registry.csv",
        tables_dir / "ratewall_joint_wall_probability_surface.csv",
        tables_dir / "ratewall_joint_wall_probability_summary.csv",
        tables_dir / "ratewall_wall_denominator_path_contract.csv",
        tables_dir / "ratewall_path_ratio_numerator_ledger.csv",
        tables_dir / "ratewall_path_ratio_numerator_reconciliation_audit.csv",
        tables_dir / "ratewall_tdc_overlap_audit.csv",
        tables_dir / "ratewall_path_ratio_denominator_v1.csv",
        tables_dir / "ratewall_path_ratio_tdc_adjustment_layer.csv",
        tables_dir / "ratewall_historical_incremental_path_ratio.csv",
        tables_dir / "ratewall_historical_incremental_path_ratio_tdc_comparison.csv",
        tables_dir / "ratewall_historical_tdc_path_admission.csv",
        tables_dir / "ratewall_historical_tdc_source_hardening_audit.csv",
        tables_dir / "ratewall_historical_tdc_source_admission_targeting.csv",
        tables_dir / "ratewall_historical_tdc_component_gap_registry.csv",
        tables_dir / "ratewall_historical_tdc_source_backed_only_eligibility.csv",
        tables_dir / "ratewall_historical_tdc_selected_series_bridge_alignment.csv",
        tables_dir / "ratewall_historical_tdc_admission_feasibility_summary.csv",
        tables_dir / "ratewall_historical_tdc_source_backed_companion_candidate.csv",
        tables_dir / "ratewall_historical_tdc_selected_series_bridge_remediation_matrix.csv",
        tables_dir / "ratewall_historical_tdc_du_ru_sensitive_panel_blocker_registry.csv",
        tables_dir / "ratewall_historical_tdc_admission_candidate_matrix.csv",
        tables_dir / "ratewall_historical_tdc_post_bridge_admission_status.csv",
        tables_dir / "ratewall_historical_tdc_du_ru_methodology_panel.csv",
        tables_dir / "ratewall_historical_tdc_bridge_candidate_priority_queue.csv",
        tables_dir / "ratewall_historical_tdc_post_bridge_blocker_queue.csv",
        tables_dir / "ratewall_historical_tdc_source_work_queue.csv",
        tables_dir / "ratewall_historical_tdc_exact_du_ru_closure_contract.csv",
        tables_dir / "ratewall_historical_tdc_overlap_identity_closure_contract.csv",
        tables_dir / "ratewall_historical_tdc_primary_bridge_target_registry.csv",
        tables_dir / "ratewall_historical_tdc_selected_series_primary_target_mapping_plan.csv",
        tables_dir / "ratewall_historical_tdc_selected_series_bridge_execution.csv",
        tables_dir / "ratewall_historical_tdc_bridge_implementation_prep.csv",
        tables_dir / "ratewall_historical_incremental_path_ratio_frontier_summary.csv",
        tables_dir / "ratewall_historical_closest_approach_clean.csv",
        tables_dir / "ratewall_forecast_incremental_path_ratio.csv",
        tables_dir / "ratewall_forecast_incremental_path_ratio_tdc_comparison.csv",
        tables_dir / "ratewall_forecast_path_ratio_scenario_registry.csv",
        tables_dir / "ratewall_forecast_channel_conversion_profile_registry.csv",
        tables_dir / "ratewall_forecast_assumption_calibration_registry.csv",
        tables_dir / "ratewall_forecast_assumption_bundle_registry.csv",
        tables_dir / "ratewall_forecast_scenario_product_summary.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_calibration_registry.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_calibration_comparison.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_calibration_product_summary.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_calibration_consumer_summary.csv",
        tables_dir / "ratewall_forecast_bank_margin_sidecar_summary.csv",
        tables_dir / "ratewall_forecast_path_ratio_decomposition.csv",
        tables_dir / "ratewall_forecast_path_ratio_numerator_boundary_registry.csv",
        tables_dir / "ratewall_forecast_path_ratio_interpretation_registry.csv",
        tables_dir / "ratewall_forecast_path_ratio_recipient_leakage_registry.csv",
        tables_dir / "ratewall_forecast_path_ratio_source_specific_interpretation_registry.csv",
        tables_dir / "ratewall_forecast_path_ratio_evidence_dependency_matrix.csv",
        tables_dir / "ratewall_forecast_path_ratio_evidence_targeting_registry.csv",
        tables_dir / "ratewall_forecast_path_ratio_evidence_work_queue.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_bridge_packet.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_source_targeting_matrix.csv",
        tables_dir / "ratewall_forecast_bank_behavior_bridge_packet.csv",
        tables_dir / "ratewall_forecast_treasury_beneficial_owner_recipient_bridge.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_best_proxy_basis.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_best_proxy_admission_review.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_best_proxy_calculation_scaffold.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_best_proxy_gate_review.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_current_demand_evidence_contract.csv",
        tables_dir / "ratewall_forecast_treasury_recipient_domestic_nonbank_route_proxy.csv",
        tables_dir / "ratewall_forecast_bank_behavior_distribution_bridge.csv",
        tables_dir / "ratewall_forecast_bank_behavior_current_demand_evidence_contract.csv",
        tables_dir / "ratewall_final_recipient_current_demand_bridge_attempt.csv",
        tables_dir / "ratewall_treasury_recipient_source_contract_path.csv",
        tables_dir / "ratewall_treasury_recipient_current_demand_proxy_scaffold.csv",
        tables_dir / "ratewall_bank_behavior_bridge_source_contract_queue.csv",
        tables_dir / "ratewall_bank_behavior_rank1_source_contract_path.csv",
        tables_dir / "ratewall_forecast_treasury_beneficial_owner_recipient_bridge_basis.csv",
        tables_dir / "ratewall_forecast_bank_behavior_distribution_bridge_basis.csv",
        tables_dir / "ratewall_forecast_treasury_beneficial_owner_recipient_mapping_basis.csv",
        tables_dir / "ratewall_forecast_bank_behavior_distribution_mapping_basis.csv",
        tables_dir / "ratewall_forecast_treasury_beneficial_owner_recipient_admission_candidate.csv",
        tables_dir / "ratewall_forecast_bank_behavior_distribution_admission_candidate.csv",
        tables_dir / "ratewall_forecast_treasury_beneficial_owner_recipient_bridge_pass_review.csv",
        tables_dir / "ratewall_forecast_bank_behavior_distribution_bridge_pass_review.csv",
        tables_dir / "ratewall_forecast_path_ratio_sensitivity_summary.csv",
        tables_dir / "ratewall_forecast_path_ratio_scenario_frontier.csv",
        tables_dir / "ratewall_forecast_path_ratio_driver_ranking.csv",
        tables_dir / "ratewall_forecast_path_ratio_driver_dominance_matrix.csv",
        tables_dir / "ratewall_forecast_path_ratio_consumer_ladder.csv",
        tables_dir / "ratewall_forecast_path_ratio_consumer_driver_summary.csv",
        tables_dir / "ratewall_forecast_path_ratio_consumer_interpretation_summary.csv",
        tables_dir / "ratewall_forecast_path_ratio_pass_through_scenario_axis.csv",
        tables_dir / "ratewall_forecast_path_ratio_pass_through_scenario_registry.csv",
        tables_dir / "ratewall_forecast_path_ratio_pass_through_scenario_frontier.csv",
        tables_dir / "ratewall_critical_beta_frontier.csv",
        tables_dir / "ratewall_forecast_path_ratio_pass_through_consumer_ladder.csv",
        tables_dir / "ratewall_forecast_path_ratio_pass_through_consumer_interpretation_summary.csv",
        tables_dir / "ratewall_forecast_path_ratio_pass_through_comparison.csv",
        tables_dir / "ratewall_forecast_path_ratio_pass_through_delta_summary.csv",
        tables_dir / "ratewall_forecast_path_ratio_pass_through_dominance.csv",
        tables_dir / "ratewall_forecast_product_decision_casebook.csv",
        tables_dir / "ratewall_forecast_product_pass_through_frontier_crosswalk.csv",
        tables_dir / "ratewall_forecast_product_reviewer_decision_summary.csv",
        tables_dir / "ratewall_forecast_incremental_path_ratio_frontier_summary.csv",
        tables_dir / "ratewall_historical_forecast_wall_ratio_comparison_matrix.csv",
        tables_dir / "ratewall_distance_to_wall_state_surface.csv",
        tables_dir / "ratewall_closest_to_wall_frontier.csv",
        tables_dir / "ratewall_estimation_target_registry.csv",
        tables_dir / "ratewall_channel_taxonomy_registry.csv",
        tables_dir / "ratewall_historical_interpretation_audit.csv",
        tables_dir / "ratewall_tdc_equation_variant_registry.csv",
        tables_dir / "ratewall_policy_path_source_extraction_task_packet.csv",
        tables_dir / "ratewall_policy_path_source_extraction_results.csv",
        tables_dir / "ratewall_policy_path_source_extraction_result_adjudication.csv",
        tables_dir / "ratewall_policy_path_authored_protocol_completion_audit.csv",
        tables_dir / "ratewall_policy_path_protocol_completion_design_tranche.csv",
        tables_dir / "ratewall_policy_path_field_specific_pass_rule_design.csv",
        tables_dir / "ratewall_policy_path_field_specific_source_evidence_audit.csv",
        tables_dir / "ratewall_policy_path_source_locator_binding_review.csv",
        tables_dir / "ratewall_policy_path_exact_source_locator_remediation.csv",
        tables_dir / "ratewall_policy_path_exact_locator_field_closure_diagnostic.csv",
        tables_dir / "ratewall_policy_path_exact_locator_pass_rule_adjudication.csv",
        tables_dir / "ratewall_policy_path_terminal_no_hit_closure.csv",
        tables_dir / "ratewall_policy_path_independent_replication_target_design.csv",
        tables_dir / "ratewall_policy_path_authored_fail_closed_invariant_design.csv",
        tables_dir / "ratewall_policy_path_protocol_component_closure_rollup.csv",
        tables_dir / "ratewall_policy_path_component_gate_execution_rollup.csv",
        tables_dir / "ratewall_policy_path_locator_binding_closure_diagnostic.csv",
        tables_dir / "ratewall_policy_path_full_protocol_admission_gate_summary.csv",
        tables_dir / "ratewall_policy_path_source_bundle_field_exhaustion_decision.csv",
        tables_dir
        / "ratewall_policy_path_source_bundle_component_exhaustion_decision.csv",
        tables_dir / "ratewall_conventional_drag_fspdp_component_decomposition_bridge.csv",
        tables_dir / "ratewall_conventional_drag_fspdp_component_source_manifest.csv",
        tables_dir / "ratewall_conventional_drag_fspdp_component_share_panel.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_coverage_weight_requirement_review.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_coverage_priority_search_queue.csv",
        tables_dir / "ratewall_conventional_drag_fspdp_source_code_search_review.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_external_source_acquisition_action_plan.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_official_component_source_acquisition_execution.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_research_side_action_plan_extraction_review.csv",
        tables_dir / "ratewall_current_demand_gdp_share_source_manifest.csv",
        tables_dir / "ratewall_current_demand_gdp_share_panel.csv",
        tables_dir / "ratewall_conventional_drag_current_demand_mapping_bridge.csv",
        tables_dir
        / "ratewall_conventional_drag_research_extraction_conversion_bridge.csv",
        tables_dir / "ratewall_conventional_drag_local_macro_panel.csv",
        tables_dir / "ratewall_conventional_drag_local_shock_quarterly.csv",
        tables_dir / "ratewall_conventional_drag_local_lp_design.csv",
        tables_dir / "ratewall_conventional_drag_local_lp_diagnostic.csv",
        tables_dir / "ratewall_conventional_drag_local_lp_estimate_diagnostic.csv",
        tables_dir / "ratewall_conventional_drag_local_lp_robustness_diagnostic.csv",
        tables_dir / "ratewall_conventional_drag_local_lp_sample_window_audit.csv",
        tables_dir / "ratewall_conventional_drag_local_lp_admission_audit.csv",
        tables_dir / "ratewall_openicpsr_replication_package_source_manifest.csv",
        tables_dir / "ratewall_frbus_model_benchmark_simulation_readiness.csv",
        tables_dir / "ratewall_frbus_conventional_drag_benchmark_protocol.csv",
        tables_dir / "ratewall_frbus_official_model_package_inventory.csv",
        tables_dir / "ratewall_frbus_official_model_benchmark_simulation_protocol.csv",
        tables_dir / "ratewall_frbus_runtime_runner_preflight.csv",
        tables_dir / "ratewall_frbus_runtime_runner_output_slots.csv",
        tables_dir / "ratewall_frbus_benchmark_comparison_mapping_contract.csv",
        tables_dir / "ratewall_frbus_benchmark_output_slot_extension_review.csv",
        tables_dir / "ratewall_conventional_drag_source_unit_aggregation_blocker_bridge.csv",
        tables_dir / "ratewall_conventional_drag_mirgk_targeted_gap_source_followup.csv",
        tables_dir / "ratewall_conventional_drag_promotion_contract_checklist.csv",
        tables_dir / "ratewall_conventional_drag_empirical_target_registry.csv",
        tables_dir / "ratewall_conventional_drag_route_pruning_audit.csv",
        tables_dir / "ratewall_conventional_drag_response_design_gate.csv",
        tables_dir / "ratewall_denominator_response_estimate_registry.csv",
        tables_dir / "ratewall_denominator_formal_design_gate.csv",
        tables_dir
        / "ratewall_conventional_drag_response_execution_readiness_packet.csv",
        tables_dir / "ratewall_local_lp_proxy_svar_diagnostic_run_packet.csv",
        tables_dir
        / "ratewall_local_lp_proxy_svar_execution_preflight_results.csv",
        tables_dir / "ratewall_local_lp_proxy_svar_route_closure_decision.csv",
        tables_dir
        / "ratewall_conventional_drag_denominator_route_triage_synthesis.csv",
        tables_dir / "ratewall_policy_path_100bp_year_blocker_action_resolution.csv",
        tables_dir / "ratewall_policy_path_source_protocol_action_packet.csv",
        tables_dir / "ratewall_policy_path_source_protocol_pass_rule_harness.csv",
        tables_dir / "ratewall_policy_path_source_protocol_extraction_attempt_results.csv",
        tables_dir / "ratewall_policy_path_source_protocol_attempt_closure_handoff.csv",
        tables_dir
        / "ratewall_policy_path_promotion_grade_source_family_acquisition_packet.csv",
        tables_dir
        / "ratewall_policy_path_promotion_grade_source_family_acquisition_execution_preflight_results.csv",
        tables_dir
        / "ratewall_policy_path_source_family_execution_closure_selection_packet.csv",
        tables_dir
        / "ratewall_policy_path_current_artifact_manual_review_execution_packet.csv",
        tables_dir
        / "ratewall_policy_path_current_artifact_manual_review_result_attempt.csv",
        tables_dir
        / "ratewall_policy_path_source_author_manual_acquisition_followup_packet.csv",
        tables_dir
        / "ratewall_policy_path_source_author_manual_acquisition_execution_preflight_results.csv",
        tables_dir
        / "ratewall_policy_path_real_source_author_web_acquisition_attempt_packet.csv",
        tables_dir
        / "ratewall_policy_path_downloaded_artifact_locator_parse_adjudication_packet.csv",
        tables_dir
        / "ratewall_policy_path_locator_candidate_pass_rule_review_decision_packet.csv",
        Path(
            "data/raw/policy_path_source_author_web_acquisition_attempts/"
            "policy_path_real_source_author_web_acquisition_attempt_manifest.csv"
        ),
        Path(
            "data/raw/policy_path_source_author_web_acquisition_attempts/"
            "sf_fed_usmpd_landing_page.html"
        ),
        Path(
            "data/raw/policy_path_source_author_web_acquisition_attempts/"
            "sf_fed_usmpd.xlsx"
        ),
        Path(
            "data/raw/policy_path_source_author_web_acquisition_attempts/"
            "sf_fed_monetary_policy_surprises.zip"
        ),
        Path(
            "data/raw/policy_path_source_author_web_acquisition_attempts/"
            "fed_sofr_continuity_landing_page.html"
        ),
        Path(
            "data/raw/policy_path_source_author_web_acquisition_attempts/"
            "fed_sofr_continuity_2024034pap.pdf"
        ),
        Path(
            "data/raw/policy_path_source_author_web_acquisition_attempts/"
            "fed_sofr_continuity_accessible_materials.zip"
        ),
        Path(
            "data/raw/policy_path_downloaded_artifact_locator_parse_adjudication/"
            "policy_path_downloaded_artifact_locator_parse_adjudication_manifest.csv"
        ),
        Path(
            "data/raw/conventional_drag_parameterization_sources/"
            "frbus_runtime_runner_preflight.json"
        ),
        Path(
            "data/raw/conventional_drag_parameterization_sources/"
            "frbus_benchmark_output_slot_extension_review.json"
        ),
        tables_dir / "ratewall_tdsp_current_demand_source_review.csv",
        tables_dir / "ratewall_tdsp_current_demand_unit_conversion.csv",
        tables_dir / "ratewall_tdsp_current_demand_diagnostic_mapping.csv",
        tables_dir / "ratewall_tdsp_policy_path_normalization_blocker.csv",
        tables_dir / "ratewall_tdsp_current_demand_admission_audit.csv",
        tables_dir / "ratewall_pce_dpi_source_refresh_contract.csv",
        tables_dir / "ratewall_tdsp_pce_dpi_refresh_diagnostic_mapping.csv",
        tables_dir / "ratewall_policy_path_exposure_vector_design_gate.csv",
        tables_dir / "ratewall_policy_path_reviewed_protocol_source_context.csv",
        tables_dir / "ratewall_policy_path_protocol_source_acquisition_registry.csv",
        tables_dir / "ratewall_policy_path_protocol_source_acquisition_audit.csv",
        tables_dir / "ratewall_policy_path_protocol_review_inventory.csv",
        tables_dir / "ratewall_policy_path_protocol_review_audit.csv",
        tables_dir / "ratewall_policy_path_mps_scalar_replication_diagnostic.csv",
        tables_dir / "ratewall_policy_path_mps_scalar_replication_audit.csv",
        tables_dir / "ratewall_policy_path_bps_year_blocker_decision.csv",
        tables_dir / "ratewall_policy_path_bps_year_blocker_decision_audit.csv",
        tables_dir / "ratewall_policy_path_event_level_candidate_vector.csv",
        tables_dir / "ratewall_policy_path_event_level_candidate_vector_audit.csv",
        tables_dir / "ratewall_policy_path_contract_interval_source_review.csv",
        tables_dir / "ratewall_policy_path_contract_spec_acquisition_blocker.csv",
        tables_dir / "ratewall_policy_path_bps_year_source_protocol.csv",
        tables_dir / "ratewall_policy_path_normalization_source_manifest.csv",
        tables_dir / "ratewall_policy_path_bps_year_normalization_review.csv",
        tables_dir / "ratewall_policy_path_source_cell_unit_contract_review.csv",
        tables_dir / "ratewall_policy_path_bps_year_protocol_closure.csv",
        tables_dir / "ratewall_policy_path_normalization_leak_audit.csv",
        tables_dir / "ratewall_tdsp_pce_dpi_policy_path_admission_audit.csv",
        tables_dir / "ratewall_tdsp_diagnostic_family_completion_gate.csv",
        tables_dir / "ratewall_interest_channel_horizon_timing_matrix.csv",
        tables_dir / "ratewall_interest_channel_promotion_gate.csv",
        tables_dir / "ratewall_interest_channel_evidence_upgrade_queue.csv",
        tables_dir / "ratewall_high_priority_interest_channel_source_bridge.csv",
        tables_dir / "ratewall_source_gate_prior_narrowing_decision.csv",
        tables_dir / "ratewall_source_gate_exhaustion_closure.csv",
        tables_dir / "ratewall_restricted_data_gate_spec.csv",
        tables_dir / "ratewall_assumption_mode_post_closure_boundary_map.csv",
        tables_dir / "ratewall_sibling_evidence_bridge.csv",
        tables_dir / "ratewall_sibling_evidence_upgrade_queue.csv",
        tables_dir / "ratewall_interest_channel_module_registry.csv",
        tables_dir / "ratewall_higher_rate_channel_registry.csv",
        tables_dir / "ratewall_corporate_net_interest_cashflow_bridge.csv",
        tables_dir / "ratewall_working_capital_cost_channel_diagnostic.csv",
        tables_dir / "ratewall_term_structure_pricing_carry_diagnostic.csv",
        tables_dir / "ratewall_interest_channel_completion_matrix.csv",
        tables_dir / "ratewall_flow_stage_decomposition.csv",
        tables_dir / "ratewall_gross_interest_subchannels.csv",
        tables_dir / "ratewall_public_finance_adjustment.csv",
        tables_dir / "ratewall_net_countervailing_channels.csv",
        tables_dir / "ratewall_wall_hit_scenarios.csv",
        tables_dir / "ratewall_threshold_solver.csv",
        tables_dir / "ratewall_assumption_sensitivity.csv",
        tables_dir / "ratewall_parameter_frontier.csv",
        tables_dir / "ratewall_minimum_conditions_to_hit_wall.csv",
        tables_dir / "ratewall_hit_fragility_frontier.csv",
        tables_dir / "ratewall_frontier_driver_ranking.csv",
        tables_dir / "ratewall_assumption_mode_driver_dominance_matrix.csv",
        tables_dir / "ratewall_assumption_mode_pairwise_sensitivity_matrix.csv",
        tables_dir / "ratewall_backend_invariant_guardrail_audit.csv",
        tables_dir / "ratewall_backend_completion_verdict.csv",
        tables_dir / "ratewall_paper_channel_map.csv",
        tables_dir / "ratewall_paper_canonical_scenario_results.csv",
        tables_dir / "ratewall_paper_tdc_dynamic_contribution.csv",
        tables_dir / "ratewall_paper_parameter_justification.csv",
        tables_dir / "ratewall_paper_sensitivity_summary.csv",
        tables_dir / "ratewall_paper_disabled_claims_appendix.csv",
        tables_dir / "ratewall_paper_financialization_interpretation.csv",
        tables_dir / "ratewall_paper_support_invariant_audit.csv",
        tables_dir / "ratewall_backend_accounting_identity_audit.csv",
        tables_dir / "ratewall_paper_scenario_accounting_bridge.csv",
        tables_dir / "ratewall_paper_dynamic_scenario_summary.csv",
        tables_dir / "ratewall_conventional_drag_decomposition.csv",
        tables_dir / "ratewall_split_denominator_comparison.csv",
        tables_dir / "ratewall_denominator_sensitivity.csv",
        tables_dir / "ratewall_split_denominator_uncertainty.csv",
        tables_dir / "ratewall_split_denominator_regime_stability.csv",
        tables_dir / "ratewall_denominator_literature_matrix.csv",
        tables_dir / "ratewall_split_denominator_joint_uncertainty.csv",
        tables_dir / "ratewall_split_denominator_joint_regime_stability.csv",
        tables_dir / "ratewall_denominator_classifier_comparison.csv",
        tables_dir / "ratewall_backend_model_readiness_gate.csv",
        tables_dir / "ratewall_chapter_readiness_self_audit.csv",
        tables_dir / "ratewall_financialized_balance_sheet_channel.csv",
        tables_dir / "ratewall_financialization_proxy_registry.csv",
        tables_dir / "ratewall_household_safe_asset_capture_proxy.csv",
        tables_dir / "ratewall_household_safe_asset_exposure_panel.csv",
        tables_dir / "ratewall_household_safe_asset_access_context.csv",
        tables_dir / "ratewall_retail_safe_yield_access_substitution_context.csv",
        tables_dir / "ratewall_retail_deposit_beta_gap_context.csv",
        tables_dir / "ratewall_retail_pass_through_dispersion_panel.csv",
        tables_dir / "ratewall_deposit_competition_conditioner.csv",
        tables_dir / "ratewall_deposit_mmf_substitution_surface.csv",
        tables_dir / "ratewall_personal_net_interest_position_context.csv",
        tables_dir / "ratewall_firm_liquid_asset_public_context.csv",
        tables_dir / "ratewall_firm_liquid_asset_cushion_panel.csv",
        tables_dir / "ratewall_firm_net_interest_cushion_context.csv",
        tables_dir / "ratewall_firm_rollover_pressure_panel.csv",
        tables_dir / "ratewall_firm_short_rate_exposure_proxy.csv",
        tables_dir / "ratewall_household_borrower_fragility_context.csv",
        tables_dir / "ratewall_bank_loan_repricing_context.csv",
        tables_dir / "ratewall_cre_refinancing_public_context.csv",
        tables_dir / "ratewall_private_credit_bdc_context.csv",
        tables_dir / "ratewall_safe_yield_paired_proxy_surface.csv",
        tables_dir / "ratewall_financialization_proxy_source_gate.csv",
        tables_dir / "ratewall_financialization_source_gate.csv",
        tables_dir / "ratewall_financialization_restricted_protocols.csv",
        tables_dir / "ratewall_financialization_double_count_audit.csv",
        tables_dir / "ratewall_financialization_overlap_audit.csv",
        tables_dir / "ratewall_financialization_artifact_traceability_matrix.csv",
        tables_dir / "ratewall_backend_expansion_context_registry.csv",
        tables_dir / "ratewall_assumption_mode_channel_promotion_decision.csv",
        tables_dir / "ratewall_assumption_mode_promoted_channel_contributions.csv",
        tables_dir / "ratewall_assumption_mode_overlap_guardrail_audit.csv",
        tables_dir / "ratewall_assumption_mode_recipient_conversion_overlap_audit.csv",
        tables_dir / "ratewall_assumption_mode_sidecar_channel_decision.csv",
        tables_dir / "ratewall_assumption_mode_sidecar_contributions.csv",
        tables_dir / "ratewall_assumption_mode_sidecar_reasonableness_audit.csv",
        tables_dir / "ratewall_assumption_mode_sidecar_frontier.csv",
        tables_dir / "ratewall_assumption_mode_sidecar_bundle_frontier.csv",
        tables_dir / "ratewall_assumption_mode_sidecar_driver_decomposition.csv",
        tables_dir
        / "ratewall_assumption_mode_dynamic_sidecar_driver_decomposition.csv",
        tables_dir / "ratewall_assumption_mode_dynamic_sidecar_paths.csv",
        tables_dir / "ratewall_assumption_mode_dynamic_sidecar_family_summary.csv",
        tables_dir / "ratewall_assumption_mode_dynamic_sidecar_secondary_paths.csv",
        tables_dir / "ratewall_assumption_mode_dynamic_sidecar_secondary_frontier.csv",
        tables_dir / "ratewall_assumption_mode_parameter_activation_ledger.csv",
        tables_dir / "ratewall_assumption_mode_channel_status_crosswalk.csv",
        tables_dir / "ratewall_assumption_mode_formula_identity_audit.csv",
        tables_dir / "ratewall_assumption_source_backing_ledger.csv",
        tables_dir / "ratewall_assumption_source_backing_invariant_audit.csv",
        tables_dir / "ratewall_qrawatch_tdcsim_scenario_registry.csv",
        tables_dir / "ratewall_qrawatch_tdcsim_provenance_audit.csv",
        tables_dir / "ratewall_qrawatch_tdcsim_bridge_invariant_audit.csv",
        tables_dir / "ratewall_generated_text_claim_boundary_scan.csv",
        tables_dir / "ratewall_backend_surface_schema_contract.csv",
        tables_dir / "ratewall_backend_artifact_claim_boundary_manifest.csv",
        tables_dir / "ratewall_release_archive_reproducibility_audit.csv",
        tables_dir / "ratewall_restricted_protocol_falsification_matrix.csv",
        tables_dir / "ratewall_restricted_protocol_field_contract.csv",
        tables_dir / "ratewall_context_surface_no_main_ratio_audit.csv",
        tables_dir / "ratewall_conventional_drag_bounded_denominator_registry.csv",
        tables_dir / "ratewall_denominator_methodology_registry.csv",
        tables_dir / "ratewall_annual_flow_denominator_anchor_registry.csv",
        tables_dir / "ratewall_annual_flow_runtime_family_registry.csv",
        tables_dir / "ratewall_annual_support_denominator_compatibility_registry.csv",
        tables_dir / "ratewall_annual_support_numerator_component_registry.csv",
        tables_dir / "ratewall_annual_support_numerator_source_gate.csv",
        tables_dir / "ratewall_annual_support_numerator_component_rollup.csv",
        tables_dir / "ratewall_annual_support_numerator_contract.csv",
        tables_dir / "ratewall_annual_support_numerator_uncertainty_envelope.csv",
        tables_dir / "ratewall_annual_support_numerator_contract_invariant_audit.csv",
        tables_dir / "ratewall_runtime_annual_flow_support_offset_scenarios.csv",
        tables_dir / "ratewall_runtime_annual_flow_support_offset_readiness_registry.csv",
        tables_dir / "ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv",
        tables_dir / "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv",
        tables_dir / "ratewall_runtime_annual_flow_support_offset_closeout_decision.csv",
        tables_dir / "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv",
        tables_dir / "ratewall_scenario_denominator_anchor_lineage.csv",
        tables_dir / "ratewall_scenario_denominator_stack_comparison.csv",
        tables_dir / "ratewall_denominator_scale_conflict_adjudication.csv",
        tables_dir / "ratewall_h4_empirical_validation_registry.csv",
        tables_dir / "ratewall_denominator_scale_conflict_followup_decision.csv",
        tables_dir / "ratewall_noncanonical_current_demand_source_timing_contract.csv",
        tables_dir / "ratewall_noncanonical_current_demand_consumer_endpoint_decision.csv",
        tables_dir / "ratewall_conventional_drag_current_demand_ratio_gate.csv",
        tables_dir / "ratewall_noncanonical_current_demand_support_ratio_consumer.csv",
        tables_dir / "ratewall_residualized_ffr_literature_replication_audit.csv",
        tables_dir / "ratewall_residualized_ffr_literature_lp_results.csv",
        tables_dir / "ratewall_residualized_ffr_fwl_diagnostics.csv",
        tables_dir / "ratewall_residualized_ffr_private_demand_bridge.csv",
        tables_dir / "ratewall_residualized_ffr_normalization_bridge.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_proxy_iv_frbus_benchmark_crosscheck.csv",
        tables_dir / "ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_proxy_iv_weak_iv_safe_inference.csv",
        tables_dir
        / "ratewall_conventional_drag_denominator_promotion_rule_evaluation.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_denominator_conversion_uncertainty_boundary.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_gdp_share_conversion_design_gate.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_gdp_share_conversion_method_admission.csv",
        tables_dir / "ratewall_conventional_drag_fspdp_lp_sample_base_share_join.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_gdp_share_conversion_sensitivity.csv",
        tables_dir
        / "ratewall_conventional_drag_fspdp_lp_sample_share_closeout_decision.csv",
        tables_dir / "ratewall_fairparke_benchmark_run_inventory.csv",
        tables_dir / "ratewall_fairparke_benchmark_mapping_contract.csv",
        tables_dir
        / "ratewall_assumption_mode_recipient_leakage_absorber_basis_audit.csv",
        tables_dir / "ratewall_household_within_distribution_safe_asset_capture_context.csv",
        tables_dir / "ratewall_deposit_pass_through_dispersion_conditioner.csv",
        tables_dir / "ratewall_brokerage_tbill_mmf_access_context.csv",
        tables_dir / "ratewall_firm_interest_income_expense_balance_context.csv",
        tables_dir / "ratewall_firm_debt_maturity_wall_context.csv",
        tables_dir / "ratewall_bdc_private_credit_stress_marker_context.csv",
        tables_dir / "ratewall_cre_maturity_refi_pressure_context.csv",
        tables_dir / "ratewall_bnpl_zero_interest_float_context.csv",
        tables_dir / "ratewall_safe_asset_substitution_pairing_audit.csv",
        tables_dir / "ratewall_financialization_expansion_avoidance_audit.csv",
        tables_dir / "ratewall_bank_nim_credit_supply_context.csv",
        tables_dir / "ratewall_tax_timing_interest_income_context.csv",
        tables_dir / "ratewall_foreign_holder_interest_leakage_context.csv",
        tables_dir / "ratewall_public_finance_remittance_timing_stress_grid.csv",
        tables_dir / "ratewall_insurance_pension_asset_liability_context.csv",
        tables_dir / "ratewall_housing_lockin_cashflow_context.csv",
        tables_dir / "ratewall_dealer_inventory_carry_context.csv",
        tables_dir / "ratewall_equity_transmission_channel_map.csv",
        tables_dir / "ratewall_equity_exposure_matrix.csv",
        tables_dir / "ratewall_equity_sensitivity_diagnostic.csv",
        tables_dir / "ratewall_equity_claim_status.csv",
        tables_dir / "ratewall_equity_evidence_workplan.csv",
        tables_dir / "ratewall_parameter_packs.csv",
        tables_dir / "ratewall_calibration_parameter_recommendations.csv",
        tables_dir / "ratewall_calibration_source_acquisition_plan.csv",
        tables_dir / "ratewall_denominator_calibration_design_gate.csv",
        tables_dir / "ratewall_recipient_leakage_design_gate.csv",
        tables_dir / "ratewall_public_finance_timing_bridge.csv",
        tables_dir / "ratewall_frontier_summary.csv",
        tables_dir / "ratewall_regime_map.csv",
        tables_dir / "ratewall_assumption_mode_interpretation.csv",
        tables_dir / "ratewall_prior_stack_diagnostic.csv",
        tables_dir / "ratewall_scenario_ladder.csv",
        tables_dir / "ratewall_model_adequacy_matrix.csv",
        tables_dir / "ratewall_assumption_mode_claim_boundary_audit.csv",
        tables_dir / "ratewall_financialization_pressure.csv",
        tables_dir / "ratewall_financialization_pressure_evidence_appendix.csv",
        tables_dir / "ratewall_safe_asset_retention_context.csv",
        tables_dir / "ratewall_safe_asset_retention_evidence_appendix.csv",
        tables_dir / "ratewall_contractionary_benchmark_calibration.csv",
        tables_dir / "ratewall_threshold_uncertainty_bands.csv",
        tables_dir / "ratewall_historical_threshold_validation.csv",
        tables_dir / "ratewall_policy_boundary_synthesis.csv",
        tables_dir / "ratewall_blocker_resolution_ledger.csv",
        tables_dir / "ratewall_publication_claim_decision.csv",
        tables_dir / "ratewall_final_blocker_ledger.csv",
        tables_dir / "ratewall_release_16_source_resolution_closeout.csv",
        tables_dir / "ratewall_release_16_no_further_promotion_ledger.csv",
        tables_dir / "ratewall_release_17_external_review_audit.csv",
        tables_dir / "ratewall_release_17_publication_polish_qa.csv",
        tables_dir / "ratewall_release_17_blocker_reopen_decision.csv",
        tables_dir / "ratewall_release_18_live_refresh_robustness_audit.csv",
        tables_dir / "ratewall_buyer_case_sign_matrix.csv",
        tables_dir / "ratewall_recipient_mpc_scenario_scaffold.csv",
        tables_dir / "ratewall_release_19_accounting_invariant_audit.csv",
        tables_dir / "ratewall_release_19_post_audit_methodology_audit.csv",
        tables_dir / "ratewall_release_20_activity_demand_benchmark.csv",
        tables_dir / "ratewall_release_20_state_dependent_lp_diagnostics.csv",
        tables_dir / "ratewall_release_20_benchmark_submission_decision.csv",
        tables_dir / "ratewall_release_21_live_refresh_endpoint_audit.csv",
        tables_dir / "ratewall_release_21_final_benchmark_gate.csv",
        tables_dir / "ratewall_release_21_backend_invariant_audit.csv",
        tables_dir / "ratewall_release_22_source_repro_accounting_audit.csv",
        tables_dir / "ratewall_release_22_core_output_source_gate.csv",
        tables_dir / "ratewall_release_22_reproducibility_hash_manifest.json",
        tables_dir / "ratewall_release_23_source_status_propagation_audit.csv",
        tables_dir / "ratewall_release_23_reproducibility_hash_manifest.json",
        tables_dir / "ratewall_release_23_latest_as_of_semantics_audit.csv",
        tables_dir / "ratewall_release_23_threshold_mechanics_feasibility_audit.csv",
        tables_dir / "ratewall_release_23_calibration_plausibility_audit.csv",
        tables_dir / "ratewall_release_23_recipient_base_consistency_audit.csv",
        tables_dir / "ratewall_threshold_claim_boundary_audit.csv",
        tables_dir / "ratewall_tdc_source_coverage.csv",
        tables_dir / "ratewall_tdc_claim_boundary_audit.csv",
        tables_dir / "ratewall_empirical_results.csv",
        tables_dir / "ratewall_empirical_outcome_panel.csv",
        tables_dir / "ratewall_causal_identification_audit.csv",
        tables_dir / "ratewall_causal_defensibility_blocker.csv",
        tables_dir / "ratewall_empirical_robustness_manifest.json",
        tables_dir / "ratewall_event_study_support_diagnostics.csv",
        tables_dir / "ratewall_event_study_robustness.csv",
        tables_dir / "ratewall_submission_identification_decision.csv",
        tables_dir / "ratewall_dynamic_lp_feasibility_diagnostics.csv",
        tables_dir / "ratewall_proxy_svar_feasibility_diagnostics.csv",
        tables_dir / "ratewall_dynamic_causal_final_blocker.csv",
        tables_dir / "ratewall_journal_submission_manifest.json",
        tables_dir / "ratewall_event_study_hac_diagnostics.csv",
        tables_dir / "ratewall_pretrend_placebo_diagnostics.csv",
        tables_dir / "ratewall_dynamic_identification_promotion_contract_disabled.csv",
        tables_dir / "ratewall_release_4_0_dynamic_causal_final_blocker.csv",
        tables_dir / "ratewall_release_4_0_submission_checklist.csv",
        tables_dir / "ratewall_external_review_issue_matrix.csv",
        tables_dir / "ratewall_release_4_0_submission_manifest.json",
        tables_dir / "ratewall_controlled_dynamic_lp_panel.csv",
        tables_dir / "ratewall_controlled_dynamic_lp_results.csv",
        tables_dir / "ratewall_controlled_dynamic_lp_support_diagnostics.csv",
        tables_dir / "ratewall_release_5_0_identification_decision.csv",
        tables_dir / "ratewall_release_5_0_proxy_svar_final_blocker.csv",
        tables_dir / "ratewall_release_5_0_dynamic_causal_manifest.json",
        tables_dir / "ratewall_proxy_svar_system_panel.csv",
        tables_dir / "ratewall_proxy_svar_proxy_relevance_diagnostics.csv",
        tables_dir / "ratewall_proxy_svar_residual_diagnostics.csv",
        tables_dir / "ratewall_proxy_svar_timing_support_diagnostics.csv",
        tables_dir / "ratewall_release_6_0_identification_decision.csv",
        tables_dir / "ratewall_release_6_0_proxy_svar_final_blocker.csv",
        tables_dir / "ratewall_release_6_0_valuation_incidence_frontier_disabled.csv",
        tables_dir / "ratewall_release_6_0_system_identification_manifest.json",
        tables_dir / "ratewall_release_7_0_var_lag_selection.csv",
        tables_dir / "ratewall_release_7_0_reduced_form_system_estimates.csv",
        tables_dir / "ratewall_release_7_0_residual_covariance.csv",
        tables_dir / "ratewall_release_7_0_proxy_relevance_support.csv",
        tables_dir / "ratewall_release_7_0_timing_exogeneity_invertibility_audit.csv",
        tables_dir / "ratewall_release_7_0_claim_promotion_contract_disabled.csv",
        tables_dir / "ratewall_release_7_0_identification_decision.csv",
        tables_dir / "ratewall_release_7_0_proxy_svar_final_blocker.csv",
        tables_dir / "ratewall_release_7_0_system_identification_manifest.json",
        tables_dir / "ratewall_release_8_0_proxy_specification_audit.csv",
        tables_dir / "ratewall_release_8_0_structural_gap_ledger.csv",
        tables_dir / "ratewall_release_8_0_nonpromotion_proof.csv",
        tables_dir / "ratewall_release_8_0_identification_decision.csv",
        tables_dir / "ratewall_release_8_0_system_identification_manifest.json",
        tables_dir / "ratewall_release_9_0_external_proxy_source_registry.csv",
        tables_dir / "ratewall_release_9_0_external_proxy_support_audit.csv",
        tables_dir / "ratewall_release_9_0_structural_identification_decision.csv",
        tables_dir / "ratewall_release_9_0_final_nonpromotion_proof.csv",
        tables_dir / "ratewall_release_9_0_structural_identification_manifest.json",
        tables_dir / "ratewall_score_dashboard.csv",
        tables_dir / "treasury_valuation_readiness_coverage.csv",
        tables_dir / "treasury_valuation_engine_readiness_gate.csv",
        tables_dir / "ratewall_dynamic_scenario_paths.csv",
        tables_dir / "ratewall_tdc_ea_tdc_pass_through_calibration_import.csv",
        tables_dir / "ratewall_tdc_ea_tdc_pass_through_regime_validation_import.csv",
        tables_dir / "ratewall_tdc_deposit_pass_through_source_import.csv",
        tables_dir / "ratewall_tdc_deposit_pass_through_regime_scenarios.csv",
        tables_dir / "ratewall_tdc_deposit_pass_through_scenario_contract.csv",
        tables_dir / "ratewall_tdc_deposit_pass_through_trigger_validation_preflight.csv",
        tables_dir / "ratewall_tdc_deposit_pass_through_scenario_contract_invariant_audit.csv",
        tables_dir / "ratewall_tdc_liquidity_regime_trigger_evidence.csv",
        tables_dir / "ratewall_tdc_liquidity_regime_trigger_promotion_protocol.csv",
        tables_dir / "ratewall_tdc_liquidity_regime_trigger_validation_evidence.csv",
        tables_dir / "ratewall_dynamic_scenario_path_consistency_diagnostic.csv",
        tables_dir / "ratewall_dynamic_offset_ratio_path.csv",
        tables_dir / "ratewall_scenario_crossing_diagnostic.csv",
        tables_dir / "ratewall_dynamic_sensitivity_frontier.csv",
        tables_dir / "ratewall_dynamic_scenario_family_registry.csv",
        tables_dir / "ratewall_dynamic_uncertainty_envelope.csv",
        tables_dir / "ratewall_dynamic_crossing_robustness.csv",
        *sorted(Path("data/raw/romer_romer").glob("*.csv")),
        *sorted(Path("data/raw/romer_romer").glob("*.json")),
        *sorted(Path("data/raw/policy_path_protocol_sources").glob("*")),
        *sorted(Path("data/raw/conventional_drag_parameterization_sources").glob("*")),
        *sorted(Path("data/raw/policy_path_contract_interval_sources").glob("*")),
        *sorted(Path("data/raw/ratewall_sibling_calibration").glob("*.csv")),
        *sorted(Path("data/raw/ratewall_sibling_calibration").glob("*.json")),
        Path("configs/ratewall_assumption_sets.yml"),
        Path("configs/ratewall_parameter_packs.yml"),
        Path("configs/ratewall_assumption_source_backing_overrides.yml"),
        Path("configs/ratewall_dynamic_scenario_paths.yml"),
        reports_dir / "ratewall_dynamic_assumption_mode_equations.md",
    ]
    return files


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row_by(
    context: dict[str, object], key: str, field: str, value: str
) -> dict[str, str]:
    for row in _rows(context, key):
        if row.get(field) == value:
            return row
    return {}


def _count_status(context: dict[str, object], status: str) -> int:
    return sum(
        row.get("result_status") == status
        for row in _rows(context, "empirical_results")
    )
