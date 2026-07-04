"""Materialize bounded policy-path source-author acquisition attempts.

This script records deterministic public/source-author URL download attempts for
the policy-path web-acquisition task packet. The resulting raw manifest is
review-only provenance. It is deliberately not a source-protocol admission layer.
"""

from __future__ import annotations

import csv
import hashlib
import mimetypes
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = (
    ROOT
    / "outputs/tables/"
    "ratewall_policy_path_source_author_manual_acquisition_execution_preflight_results.csv"
)
OUT_DIR = ROOT / "data/raw/policy_path_source_author_web_acquisition_attempts"
MANIFEST = OUT_DIR / "policy_path_real_source_author_web_acquisition_attempt_manifest.csv"

USMPD_LANDING = (
    "https://www.frbsf.org/research-and-insights/data-and-indicators/"
    "us-monetary-policy-event-study-database/"
)
USMPD_XLSX = "https://www.frbsf.org/wp-content/uploads/USMPD.xlsx"
USMPD_MPS_ZIP = "https://www.frbsf.org/wp-content/uploads/monetary-policy-surprises.zip"
SOFR_HTML = (
    "https://www.federalreserve.gov/econres/feds/"
    "constructing-high-frequency-monetary-policy-surprises-from-sofr-futures.htm"
)
SOFR_PDF = "https://www.federalreserve.gov/econres/feds/files/2024034pap.pdf"
SOFR_ZIP = "https://www.federalreserve.gov/econres/feds/files/feds2024034.zip"

URL_TARGETS = {
    USMPD_LANDING: "sf_fed_usmpd_landing_page.html",
    USMPD_XLSX: "sf_fed_usmpd.xlsx",
    USMPD_MPS_ZIP: "sf_fed_monetary_policy_surprises.zip",
    SOFR_HTML: "fed_sofr_continuity_landing_page.html",
    SOFR_PDF: "fed_sofr_continuity_2024034pap.pdf",
    SOFR_ZIP: "fed_sofr_continuity_accessible_materials.zip",
}


FIELD_URLS = {
    "source_cell_unit_sign__effective_contract_family_by_era": [
        SOFR_HTML,
        SOFR_PDF,
        USMPD_LANDING,
    ],
    "source_cell_unit_sign__literal_na_handling": [USMPD_XLSX, USMPD_MPS_ZIP],
    "source_cell_unit_sign__percentage_point_basis_point_conversion": [
        USMPD_LANDING,
        USMPD_MPS_ZIP,
        SOFR_PDF,
    ],
    "source_cell_unit_sign__source_instrument_code": [USMPD_XLSX, USMPD_LANDING],
    "source_cell_unit_sign__source_workbook_cell_unit": [USMPD_XLSX, USMPD_MPS_ZIP],
    "bps_year_formula__horizon_weights": [USMPD_MPS_ZIP, SOFR_PDF, SOFR_ZIP],
    "bps_year_formula__rate_change_unit_conversion": [
        USMPD_LANDING,
        USMPD_MPS_ZIP,
        SOFR_PDF,
    ],
    "bps_year_formula__sign_convention": [USMPD_MPS_ZIP, SOFR_ZIP],
    "event_date_horizon_grid__contract_reference_interval": [
        USMPD_XLSX,
        SOFR_PDF,
        SOFR_HTML,
    ],
    "event_date_horizon_grid__event_date": [USMPD_XLSX, USMPD_LANDING],
    "event_date_horizon_grid__event_specific_horizon_start_end_dates": [
        USMPD_XLSX,
        SOFR_PDF,
    ],
    "event_date_horizon_grid__event_window": [USMPD_LANDING, USMPD_XLSX],
    "event_date_horizon_grid__literal_na_exclusion": [USMPD_XLSX],
    "loading_back_transform__factor_definition": [USMPD_MPS_ZIP, USMPD_LANDING],
    "loading_back_transform__instrument_loadings": [USMPD_MPS_ZIP, USMPD_XLSX],
    "loading_back_transform__rotation_sign_rule": [USMPD_MPS_ZIP],
    "loading_back_transform__scalar_to_cell_back_transform": [
        USMPD_MPS_ZIP,
        USMPD_XLSX,
    ],
    "loading_back_transform__source_code_replication_command": [USMPD_MPS_ZIP],
}

FIELDS = [
    "policy_path_real_source_author_web_acquisition_attempt_manifest_row_id",
    "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id",
    "authored_field_name",
    "bounded_attempt_class",
    "source_author_search_query_recorded",
    "deterministic_public_url_identified",
    "candidate_source_urls",
    "candidate_source_url_roles",
    "download_attempt_status",
    "downloaded_artifact_paths",
    "downloaded_artifact_sha256s",
    "downloaded_artifact_sizes",
    "downloaded_artifact_content_types",
    "downloaded_at_utc",
    "source_family_after_attempt",
    "attempt_result_status",
    "exact_attempt_blocker",
    "next_backend_action_after_attempt",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str) -> tuple[Path | None, str]:
    target = OUT_DIR / URL_TARGETS[url]
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "RateWall research acquisition audit/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = response.read()
        target.write_bytes(payload)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"{type(exc).__name__}:{exc}"
    return target, "downloaded"


def _join(values: list[str]) -> str:
    return ";".join(values)


def main() -> int:
    if not INPUT.exists():
        print(f"missing input: {INPUT}", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with INPUT.open(encoding="utf-8", newline="") as handle:
        preflight_rows = list(csv.DictReader(handle))

    downloaded: dict[str, tuple[Path | None, str]] = {}
    for urls in FIELD_URLS.values():
        for url in urls:
            if url not in downloaded:
                downloaded[url] = _download(url)

    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    rows: list[dict[str, str]] = []
    for preflight in preflight_rows:
        field = preflight.get("authored_field_name", "")
        search_task = (
            preflight.get("acquisition_execution_preflight_class")
            == "source_author_search_download_preflight_result"
        )
        urls = FIELD_URLS.get(field, []) if search_task else []
        paths: list[str] = []
        hashes: list[str] = []
        sizes: list[str] = []
        content_types: list[str] = []
        errors: list[str] = []
        for url in urls:
            path, status = downloaded[url]
            if path is None:
                errors.append(f"{url}::{status}")
                continue
            rel_path = path.relative_to(ROOT).as_posix()
            paths.append(rel_path)
            hashes.append(_sha256(path))
            sizes.append(str(path.stat().st_size))
            content_types.append(
                mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            )

        if search_task and paths:
            attempt_class = "bounded_public_source_author_download_attempt"
            deterministic = "true"
            download_status = (
                "downloaded_reusable_public_artifact_hashes_recorded_review_only"
            )
            attempt_status = "blocked_public_artifact_acquired_not_field_evidence"
            blocker = (
                f"{field} has bounded public source-author artifact downloads "
                "with hashes, but downloaded artifacts and metadata remain "
                "review-only until locator-grain evidence and pass-rule "
                "adjudication are completed."
            )
            next_action = (
                "parse_downloaded_public_artifacts_for_locator_grain_evidence_then_adjudicate_pass_rule_fail_closed"
            )
        elif search_task:
            attempt_class = "bounded_public_source_author_download_no_hit"
            deterministic = "false"
            download_status = "blocked_no_reusable_public_artifact_downloaded"
            attempt_status = "blocked_no_deterministic_public_source_artifact"
            blocker = (
                f"{field} did not yield a reusable public source-author artifact "
                f"during bounded acquisition attempt: {_join(errors)}"
            )
            next_action = (
                "manual_source_author_search_or_authenticated_acquisition_required"
            )
        else:
            attempt_class = "manual_authenticated_new_source_family_blocker"
            deterministic = "false"
            download_status = "blocked_no_download_manual_authenticated_or_new_source_family_required"
            attempt_status = "blocked_manual_authenticated_or_new_source_family_required"
            blocker = (
                f"{field} remains a manual-authenticated/new-source-family "
                "blocker; no automated public web acquisition attempt can "
                "satisfy the required promotion-grade locator."
            )
            next_action = (
                "manual_authenticated_or_new_source_family_acquisition_required"
            )

        rows.append(
            {
                "policy_path_real_source_author_web_acquisition_attempt_manifest_row_id": (
                    f"policy_path_real_source_author_web_acquisition_attempt_manifest::{len(rows) + 1:04d}"
                ),
                "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id": preflight.get(
                    "policy_path_source_author_manual_acquisition_execution_preflight_result_row_id",
                    "",
                ),
                "authored_field_name": field,
                "bounded_attempt_class": attempt_class,
                "source_author_search_query_recorded": preflight.get(
                    "attempted_query_or_handoff", ""
                ),
                "deterministic_public_url_identified": deterministic,
                "candidate_source_urls": _join(urls),
                "candidate_source_url_roles": (
                    "official_source_author_or_official_source_author_companion_artifact"
                    if urls
                    else ""
                ),
                "download_attempt_status": download_status,
                "downloaded_artifact_paths": _join(paths),
                "downloaded_artifact_sha256s": _join(hashes),
                "downloaded_artifact_sizes": _join(sizes),
                "downloaded_artifact_content_types": _join(content_types),
                "downloaded_at_utc": now if paths else "",
                "source_family_after_attempt": preflight.get("target_source_family", ""),
                "attempt_result_status": attempt_status,
                "exact_attempt_blocker": blocker,
                "next_backend_action_after_attempt": next_action,
            }
        )

    with MANIFEST.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(MANIFEST.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
