from pathlib import Path
import zipfile

from ratewall.databook.build_legacy import _release_22_reproducibility_hash_manifest_payload
from ratewall.release import ReleaseArtifacts, _release_archive_files
from scripts import materialize_release_inputs


def test_outer_audit_packet_source_tree_contains_release_inputs() -> None:
    """The top-level source tree must be runnable, not only a nested archive."""

    assert Path("configs/sources.yml").is_file(), (
        "copy configs/sources.yml from the release source archive before "
        "marking the backend stage complete"
    )
    assert Path("data/raw/ratewall_snapshot.json").is_file(), (
        "copy data/raw/ratewall_snapshot.json from the release source archive "
        "before marking the backend stage complete"
    )


def test_materialize_release_inputs_restores_archived_raw_tree(
    tmp_path, monkeypatch
) -> None:
    archive = tmp_path / "outputs" / "release" / "ratewall_release_23_0_source_archive.zip"
    archive.parent.mkdir(parents=True)
    with zipfile.ZipFile(archive, "w") as payload:
        payload.writestr("data/raw/ratewall_snapshot.json", "{}")
        payload.writestr(
            "data/raw/policy_path_protocol_sources/policy_path_protocol_review_inventory.csv",
            "id,status\nfixture,pass\n",
        )

    monkeypatch.setattr(materialize_release_inputs, "ROOT", tmp_path)
    monkeypatch.setattr(materialize_release_inputs, "ARCHIVE", archive)
    monkeypatch.setattr(
        materialize_release_inputs,
        "SNAPSHOT",
        tmp_path / "data" / "raw" / "ratewall_snapshot.json",
    )

    materialize_release_inputs._ensure_snapshot()

    assert (tmp_path / "data" / "raw" / "ratewall_snapshot.json").read_text(
        encoding="utf-8"
    ) == "{}"
    assert (
        tmp_path
        / "data"
        / "raw"
        / "policy_path_protocol_sources"
        / "policy_path_protocol_review_inventory.csv"
    ).read_text(encoding="utf-8") == "id,status\nfixture,pass\n"


def test_release_archive_files_exclude_stale_historical_reports(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    tables_dir = tmp_path / "outputs" / "tables"
    reports_dir = tmp_path / "outputs" / "reports"
    reports_dir.mkdir(parents=True)
    tables_dir.mkdir(parents=True)
    stale_report = reports_dir / "ratewall_causal_identification_appendix.md"
    stale_report.write_text("stale historical report\n", encoding="utf-8")
    residualized_input = (
        tmp_path
        / "data"
        / "raw"
        / "residualized_ffr_bridge"
        / "unpacked"
        / "Replication"
        / "fixture.csv"
    )
    residualized_input.parent.mkdir(parents=True)
    residualized_input.write_text("id,value\nfixture,1\n", encoding="utf-8")

    def report(name: str) -> Path:
        return reports_dir / name

    artifacts = ReleaseArtifacts(
        final_paper=report("ratewall_final_paper.md"),
        final_paper_quarto=report("ratewall_final_paper.qmd"),
        slide_deck=report("ratewall_deck_ready.md"),
        slide_deck_quarto=report("ratewall_public_deck.qmd"),
        release_manifest=tables_dir / "ratewall_release_manifest.json",
        claim_audit=tables_dir / "ratewall_claim_boundary_audit.csv",
        source_appendix=report("ratewall_source_provenance_appendix.md"),
        empirical_appendix=report("ratewall_empirical_method_appendix.md"),
        limitations_appendix=report("ratewall_limitations_appendix.md"),
        validation_package=report("ratewall_validation_package.md"),
        public_readme=report("ratewall_public_readme.md"),
        release_index=report("ratewall_release_artifact_index.md"),
        reproduction_commands=report("ratewall_reproduction_commands.md"),
        public_release_checklist=report("ratewall_public_release_checklist.md"),
        publication_claim_decision_memo=report(
            "ratewall_publication_claim_decision_memo.md"
        ),
        release_16_bounded_publication_closeout_memo=report(
            "ratewall_release_16_bounded_publication_closeout_memo.md"
        ),
        release_16_reviewer_blocker_text=report(
            "ratewall_release_16_reviewer_blocker_text.md"
        ),
        release_17_external_review_packet=report(
            "ratewall_release_17_external_review_packet.md"
        ),
        release_17_publication_polish_memo=report(
            "ratewall_release_17_publication_polish_memo.md"
        ),
        release_18_publication_freeze_memo=report(
            "ratewall_release_18_publication_freeze_memo.md"
        ),
        release_19_post_audit_methodology_memo=report(
            "ratewall_release_19_post_audit_methodology_memo.md"
        ),
        release_20_submission_readiness_memo=report(
            "ratewall_release_20_submission_readiness_memo.md"
        ),
        release_21_backend_closeout_memo=report(
            "ratewall_release_21_backend_closeout_memo.md"
        ),
        release_22_backend_fix_memo=report("ratewall_release_22_backend_fix_memo.md"),
        release_23_backend_fix_memo=report("ratewall_release_23_backend_fix_memo.md"),
        release_23_reproducibility_manifest=tables_dir
        / "ratewall_release_23_reproducibility_hash_manifest.json",
        release_23_archive_verification_audit=tables_dir
        / "ratewall_release_23_archive_hash_verification_audit.csv",
        figure_plate=report("ratewall_figure_plate.md"),
        table_plate=report("ratewall_table_plate.md"),
        archival_manifest=tables_dir / "ratewall_release_archive_manifest.json",
        source_archive=tmp_path
        / "outputs"
        / "release"
        / "ratewall_release_23_0_source_archive.zip",
        citation_metadata=report("CITATION.cff"),
        package_smoke=report("ratewall_package_smoke.md"),
    )

    archive_files = _release_archive_files(
        {
            "tables_dir": tables_dir,
            "reports_dir": reports_dir,
            "snapshot_bundle": tmp_path / "data" / "raw" / "ratewall_snapshot.json",
        },
        artifacts,
    )

    assert stale_report not in archive_files
    assert (
        Path("data/raw/residualized_ffr_bridge/unpacked/Replication/fixture.csv")
        in archive_files
    )
    assert artifacts.empirical_appendix in archive_files


def test_release_22_hash_manifest_excludes_stale_release_products(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    tables_dir = tmp_path / "outputs" / "tables"
    raw_dir = tmp_path / "data" / "raw"
    tables_dir.mkdir(parents=True)
    raw_dir.mkdir(parents=True)
    snapshot = raw_dir / "ratewall_snapshot.json"
    snapshot.write_text("{}\n", encoding="utf-8")
    backend_table = tables_dir / "ratewall_backend_model_readiness_gate.csv"
    backend_table.write_text("gate,status\nfixture,pass\n", encoding="utf-8")
    stale_release_manifest = tables_dir / "ratewall_release_manifest.json"
    stale_release_manifest.write_text('{"stale": true}\n', encoding="utf-8")
    stale_release_23_manifest = (
        tables_dir / "ratewall_release_23_reproducibility_hash_manifest.json"
    )
    stale_release_23_manifest.write_text('{"stale": true}\n', encoding="utf-8")

    payload = _release_22_reproducibility_hash_manifest_payload(
        snapshot_bundle=snapshot,
        tables_dir=tables_dir,
    )
    paths = {record["path"] for record in payload["files"]}

    assert backend_table.as_posix() in paths
    assert stale_release_manifest.as_posix() not in paths
    assert stale_release_23_manifest.as_posix() not in paths
