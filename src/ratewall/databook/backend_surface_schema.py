"""Backend schema and release-layer anti-overclaim audits."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from collections import Counter
from pathlib import Path


FORBIDDEN_SWITCH_FIELDS = [
    "empirical_claim_enabled",
    "policy_failure_claim_enabled",
    "pricing_output_enabled",
    "incidence_claim_enabled",
    "welfare_claim_enabled",
    "tax_output_enabled",
    "mpc_output_enabled",
    "holder_allocation_enabled",
    "reset_calendar_construction_enabled",
    "raw_rate_shock_enabled",
    "causal_financialization_claim_enabled",
]

BACKEND_SURFACE_SCHEMA_CONTRACT_FIELDS = [
    "schema_row_id",
    "artifact_name",
    "artifact_path",
    "field_position",
    "field_name",
    "semantic_role",
    "required_presence",
    "allowed_blank_status",
    "allowed_values",
    "promotion_sensitive",
    "forbidden_if_nonblank",
    "duplicate_header_count",
    "duplicate_semantic_field_group",
    "pandas_suffix_pattern_detected",
    "release_layer",
    "claim_boundary_status",
    "prompt_numeric_source_block_status",
    "schema_contract_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]

BACKEND_ARTIFACT_CLAIM_BOUNDARY_MANIFEST_FIELDS = [
    "manifest_row_id",
    "artifact_name",
    "artifact_path",
    "release_layer",
    "source_backing_class",
    "surface_type",
    "row_count",
    "field_count",
    "explicit_claim_boundary_values",
    "claim_boundary_status",
    "release_layer_classification_status",
    "review_only_artifact_status",
    "prompt_numeric_source_violation_count",
    "prompt_numeric_source_block_status",
    "artifact_claim_boundary_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]

RELEASE_ARCHIVE_REPRODUCIBILITY_AUDIT_FIELDS = [
    "archive_audit_row_id",
    "artifact_name",
    "artifact_path",
    "release_layer",
    "archive_member_path",
    "artifact_kind",
    "sha256",
    "row_count_or_size",
    "archive_included",
    "release_manifest_listed",
    "claim_boundary_status",
    "archive_reproducibility_status",
    "exact_blocker",
    "allowed_use",
    "blocked_use",
    "claim_boundary",
    *FORBIDDEN_SWITCH_FIELDS,
]

_PANDAS_SUFFIX_RE = re.compile(r".+\.\d+$")
_PROMPT_SOURCE_NEEDLES = (
    "external_review",
    "external_review",
    "external-review",
    "do/external_review",
    "external_review_",
)


def backend_surface_schema_contract_rows(
    *, tables_dir: Path, release_manifest_path: Path
) -> list[dict[str, str]]:
    layer_by_path = _release_layers(release_manifest_path)
    rows: list[dict[str, str]] = []
    row_id = 1
    for path in sorted(tables_dir.glob("*.csv")):
        header = _csv_header(path)
        counts = Counter(header)
        prompt_status = _prompt_numeric_source_status(path)
        release_layer = layer_by_path.get(
            _artifact_path(path), "not_in_release_manifest_local_generated_output"
        )
        has_claim_boundary = "claim_boundary" in header
        claim_boundary_status = (
            "pass_explicit_claim_boundary_field"
            if has_claim_boundary
            else "pass_layer_claim_boundary_assigned"
        )
        for position, field_name in enumerate(header, start=1):
            duplicate_count = counts[field_name]
            suffix_detected = bool(_PANDAS_SUFFIX_RE.fullmatch(field_name))
            semantic_group = _semantic_group(field_name)
            promotion_sensitive = _promotion_sensitive(field_name)
            schema_pass = duplicate_count == 1 and not suffix_detected
            rows.append(
                {
                    "schema_row_id": f"schema::{row_id:06d}",
                    "artifact_name": path.name,
                    "artifact_path": _artifact_path(path),
                    "field_position": str(position),
                    "field_name": field_name,
                    "semantic_role": _semantic_role(field_name),
                    "required_presence": "required_header_unique",
                    "allowed_blank_status": _allowed_blank_status(field_name),
                    "allowed_values": "true;false"
                    if field_name in FORBIDDEN_SWITCH_FIELDS
                    or field_name.endswith("_enabled")
                    or field_name.endswith("_allowed")
                    else "",
                    "promotion_sensitive": _bool(promotion_sensitive),
                    "forbidden_if_nonblank": (
                        "blocked_or_review_only_gate_not_passed"
                        if promotion_sensitive
                        else ""
                    ),
                    "duplicate_header_count": str(duplicate_count),
                    "duplicate_semantic_field_group": semantic_group,
                    "pandas_suffix_pattern_detected": _bool(suffix_detected),
                    "release_layer": release_layer,
                    "claim_boundary_status": claim_boundary_status,
                    "prompt_numeric_source_block_status": prompt_status,
                    "schema_contract_status": "pass" if schema_pass else "fail",
                    "exact_blocker": ""
                    if schema_pass
                    else "duplicate_header_or_pandas_suffix_field_detected",
                    "allowed_use": "backend_schema_contract_review_only",
                    "blocked_use": (
                        "denominator_prior;main_ratio;Evidence_Mode;pricing_output;"
                        "holder_allocation;raw_rate_shock;runtime_promotion"
                    ),
                    "claim_boundary": (
                        "backend_surface_schema_contract_not_empirical_promotion"
                    ),
                    **_false_switches(),
                }
            )
            row_id += 1
    return rows


def backend_artifact_claim_boundary_manifest_rows(
    *, tables_dir: Path, release_manifest_path: Path
) -> list[dict[str, str]]:
    layer_by_path = _release_layers(release_manifest_path)
    manifest_paths = set(layer_by_path)
    local_table_paths = {_artifact_path(path) for path in tables_dir.glob("*.csv")}
    paths = sorted(manifest_paths | local_table_paths)
    rows: list[dict[str, str]] = []
    for index, artifact_path in enumerate(paths, start=1):
        path = Path(artifact_path)
        actual_path = Path(artifact_path)
        if path.parts[:2] == ("outputs", "tables"):
            actual_path = tables_dir / path.name
        release_layer = layer_by_path.get(
            artifact_path, "not_in_release_manifest_local_generated_output"
        )
        header = _csv_header(actual_path) if actual_path.exists() else []
        row_count = _csv_row_count(actual_path) if actual_path.exists() else 0
        claim_values = _claim_boundary_values(actual_path) if actual_path.exists() else []
        prompt_violations = (
            _prompt_numeric_source_violation_count(actual_path)
            if actual_path.exists()
            else 0
        )
        review_only = _review_only_artifact(path.name, header, claim_values)
        review_status = (
            "fail_review_only_artifact_in_empirical_estimates_layer"
            if review_only and release_layer == "empirical_estimates"
            else "pass"
        )
        claim_status = (
            "pass_explicit_claim_boundary_values"
            if claim_values
            else "pass_release_layer_claim_boundary"
        )
        layer_status = (
            "pass_release_layer_or_local_generated_classified"
            if release_layer
            else "fail_missing_release_layer_classification"
        )
        status_pass = (
            review_status == "pass"
            and prompt_violations == 0
            and layer_status.startswith("pass")
            and claim_status.startswith("pass")
        )
        rows.append(
            {
                "manifest_row_id": f"artifact-claim::{index:05d}",
                "artifact_name": path.name,
                "artifact_path": artifact_path,
                "release_layer": release_layer,
                "source_backing_class": _source_backing_class(release_layer),
                "surface_type": _surface_type(path.name, header),
                "row_count": str(row_count),
                "field_count": str(len(header)),
                "explicit_claim_boundary_values": ";".join(claim_values[:12]),
                "claim_boundary_status": claim_status,
                "release_layer_classification_status": layer_status,
                "review_only_artifact_status": review_status,
                "prompt_numeric_source_violation_count": str(prompt_violations),
                "prompt_numeric_source_block_status": "pass"
                if prompt_violations == 0
                else "fail_prompt_source_numeric_leakage",
                "artifact_claim_boundary_status": "pass" if status_pass else "fail",
                "exact_blocker": ""
                if status_pass
                else "claim_boundary_release_layer_or_prompt_source_violation",
                "allowed_use": "artifact_claim_boundary_and_release_layer_review",
                "blocked_use": (
                    "denominator_prior;main_ratio;Evidence_Mode;pricing_output;"
                    "holder_allocation;raw_rate_shock;runtime_promotion"
                ),
                "claim_boundary": (
                    "backend_artifact_claim_boundary_manifest_not_empirical_promotion"
                ),
                **_false_switches(),
            }
        )
    return rows


def release_archive_reproducibility_audit_rows(
    *,
    tables_dir: Path,
    release_manifest_path: Path,
    source_archive_path: Path,
    planned_archive_paths: set[str] | None = None,
) -> list[dict[str, str]]:
    layer_by_path = _release_layers(release_manifest_path)
    archive_names = (
        planned_archive_paths
        if planned_archive_paths is not None
        else _archive_names(source_archive_path)
    )
    rows: list[dict[str, str]] = []
    for index, (artifact_path, release_layer) in enumerate(
        sorted(layer_by_path.items()), start=1
    ):
        path = Path(artifact_path)
        actual_path = tables_dir / path.name if path.parts[:2] == ("outputs", "tables") else path
        exists = actual_path.exists() and actual_path.is_file()
        source_archive_self = artifact_path == source_archive_path.as_posix()
        archive_included = artifact_path in archive_names or source_archive_self
        claim_status = (
            "pass_explicit_or_layer_claim_boundary"
            if exists
            else "blocked_artifact_missing_at_audit_time"
        )
        ok = exists and archive_included
        rows.append(
            {
                "archive_audit_row_id": f"archive-repro::{index:05d}",
                "artifact_name": path.name,
                "artifact_path": artifact_path,
                "release_layer": release_layer,
                "archive_member_path": artifact_path,
                "artifact_kind": _artifact_kind(path.name),
                "sha256": _sha256(actual_path) if exists else "",
                "row_count_or_size": str(_row_count_or_size(actual_path))
                if exists
                else "",
                "archive_included": _bool(archive_included),
                "release_manifest_listed": "true",
                "claim_boundary_status": claim_status,
                "archive_reproducibility_status": "pass" if ok else "blocked",
                "exact_blocker": ""
                if ok
                else "release_manifest_artifact_missing_from_source_archive",
                "allowed_use": "release_archive_reproducibility_review",
                "blocked_use": (
                    "denominator_prior;main_ratio;Evidence_Mode;pricing_output;"
                    "holder_allocation;raw_rate_shock;runtime_promotion"
                ),
                "claim_boundary": (
                    "release_archive_reproducibility_audit_not_empirical_promotion"
                ),
                **_false_switches(),
            }
        )
    return rows


def _release_layers(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    layers = manifest.get("artifact_layers", {})
    out: dict[str, str] = {}
    if not isinstance(layers, dict):
        return out
    for layer, artifacts in layers.items():
        if not isinstance(artifacts, list):
            continue
        for artifact in artifacts:
            out[str(artifact)] = str(layer)
    return out


def _csv_header(path: Path) -> list[str]:
    if not path.exists() or path.suffix != ".csv":
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle), [])


def _csv_row_count(path: Path) -> int:
    if not path.exists() or path.suffix != ".csv":
        return 0
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _ in reader)


def _claim_boundary_values(path: Path) -> list[str]:
    if not path.exists() or path.suffix != ".csv":
        return []
    values: set[str] = set()
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if "claim_boundary" not in (reader.fieldnames or []):
            return []
        for row in reader:
            value = row.get("claim_boundary", "").strip()
            if value:
                values.add(value)
            if len(values) >= 12:
                break
    return sorted(values)


def _prompt_numeric_source_status(path: Path) -> str:
    return (
        "pass"
        if _prompt_numeric_source_violation_count(path) == 0
        else "fail_prompt_source_numeric_leakage"
    )


def _prompt_numeric_source_violation_count(path: Path) -> int:
    if not path.exists() or path.suffix != ".csv":
        return 0
    violations = 0
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        source_fields = [field for field in fieldnames if _source_field(field)]
        sensitive_fields = [field for field in fieldnames if _sensitive_value_field(field)]
        for row in reader:
            source_text = " ".join(row.get(field, "") for field in source_fields).lower()
            if not any(needle in source_text for needle in _PROMPT_SOURCE_NEEDLES):
                continue
            for field in sensitive_fields:
                value = row.get(field, "").strip().lower()
                if _sensitive_value_leaked(field, value):
                    violations += 1
                    break
    return violations


def _source_field(field: str) -> bool:
    lowered = field.lower()
    return any(
        token in lowered
        for token in (
            "source",
            "artifact",
            "path",
            "citation",
            "url",
            "provenance",
            "memo",
        )
    )


def _sensitive_value_field(field: str) -> bool:
    lowered = field.lower()
    return (
        lowered.startswith("candidate_")
        or lowered
        in {
            "current_value_exact",
            "current_value_low",
            "current_value_base",
            "current_value_high",
        }
        or "estimate" in lowered
        or lowered.endswith("_allowed")
        or lowered.endswith("_enabled")
        or (
            lowered.startswith("enters_")
            and lowered != "enters_noncanonical_assumption_mode"
        )
        or "promotion" in lowered
        or "prior" in lowered
        or "bps_year" in lowered
        or "policy_rate_bps" in lowered
        or "pricing_output" in lowered
    )


def _sensitive_value_leaked(field: str, value: str) -> bool:
    if not value or value in {"false", "0", "0.0", "blocked", "none", "na"}:
        return False
    lowered = field.lower()
    if lowered.endswith("_allowed") or lowered.endswith("_enabled"):
        return value == "true"
    if lowered.startswith("enters_"):
        return value == "true"
    if "promotion" in lowered or "prior" in lowered:
        return value.startswith("pass") or value == "true"
    if lowered in {
        "current_value_exact",
        "current_value_low",
        "current_value_base",
        "current_value_high",
    }:
        return True
    return True


def _semantic_role(field: str) -> str:
    lowered = field.lower()
    if field == "claim_boundary":
        return "claim_boundary"
    if field in FORBIDDEN_SWITCH_FIELDS or lowered.endswith("_enabled"):
        return "forbidden_runtime_switch"
    if _promotion_sensitive(field):
        return "promotion_sensitive_field"
    if _source_field(field):
        return "source_or_provenance_field"
    if lowered.endswith("_status"):
        return "status_field"
    return "data_field"


def _semantic_group(field: str) -> str:
    if _PANDAS_SUFFIX_RE.fullmatch(field):
        return field.rsplit(".", 1)[0]
    return field


def _promotion_sensitive(field: str) -> bool:
    return _sensitive_value_field(field) or field in FORBIDDEN_SWITCH_FIELDS


def _allowed_blank_status(field: str) -> str:
    if _promotion_sensitive(field):
        return "blank_required_when_gate_blocked"
    return "blank_allowed_if_not_applicable"


def _review_only_artifact(
    artifact_name: str, header: list[str], claim_values: list[str]
) -> bool:
    lowered = artifact_name.lower()
    text = " ".join([lowered, *header, *claim_values]).lower()
    return any(
        token in text
        for token in (
            "review",
            "diagnostic",
            "audit",
            "blocked",
            "blocker",
            "candidate",
            "protocol",
            "preflight",
            "invariant",
            "manifest",
            "parser",
            "source_frontier",
            "source_contract",
            "local_lp",
            "not_empirical_promotion",
            "not_claim_promotion",
        )
    )


def _source_backing_class(release_layer: str) -> str:
    if release_layer == "empirical_estimates":
        return "empirical_release_layer_requires_existing_claim_audit"
    if release_layer == "descriptive_accounting":
        return "descriptive_accounting_release_layer"
    return "blocked_or_diagnostic_only"


def _surface_type(artifact_name: str, header: list[str]) -> str:
    lowered = artifact_name.lower()
    if "audit" in lowered:
        return "audit_surface"
    if "manifest" in lowered:
        return "manifest_surface"
    if "protocol" in lowered or "contract" in lowered:
        return "protocol_or_contract_surface"
    if "diagnostic" in lowered:
        return "diagnostic_surface"
    if "claim_boundary" in header:
        return "claim_boundary_surface"
    return "generated_table"


def _artifact_kind(artifact_name: str) -> str:
    if artifact_name.endswith(".csv"):
        return "csv_table"
    if artifact_name.endswith(".json"):
        return "json_manifest"
    if artifact_name.endswith(".md"):
        return "markdown_report"
    return "release_artifact"


def _row_count_or_size(path: Path) -> int:
    if path.suffix == ".csv":
        return _csv_row_count(path)
    return path.stat().st_size


def _archive_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    with zipfile.ZipFile(path) as archive:
        return set(archive.namelist())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_path(path: Path) -> str:
    parts = path.parts
    if "outputs" in parts:
        return Path(*parts[parts.index("outputs") :]).as_posix()
    return path.as_posix()


def _false_switches() -> dict[str, str]:
    return {field: "false" for field in FORBIDDEN_SWITCH_FIELDS}


def _bool(value: bool) -> str:
    return "true" if value else "false"
