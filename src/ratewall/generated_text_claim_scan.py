"""Generated-artifact claim-boundary scan for RateWall."""

from __future__ import annotations

import csv
import json
import os
import re
import signal
import threading
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path


GENERATED_TEXT_CLAIM_BOUNDARY_SCAN_FIELDS = [
    "artifact_path",
    "artifact_kind",
    "claim_rule_id",
    "forbidden_pattern",
    "allowed_boundary_patterns",
    "total_match_count",
    "allowed_boundary_match_count",
    "allowed_boundary_pattern_hit",
    "forbidden_unqualified_match_count",
    "sample_unqualified_match",
    "scan_window_chars",
    "audit_status",
    "failure_mode_if_false",
    "claim_boundary",
]

GENERATED_TEXT_CLAIM_BOUNDARY = (
    "generated_text_claim_boundary_scan_not_claim_adjudication_not_evidence_promotion"
)

SCAN_WINDOW_CHARS = 500
DEFAULT_CLAIM_SCAN_WORKERS = max(1, ((os.cpu_count() or 1) * 3) // 5)


@dataclass(frozen=True)
class ClaimRule:
    claim_rule_id: str
    forbidden_pattern: str


CLAIM_RULES = [
    ClaimRule(
        "empirical_threshold_claim",
        r"\bempirical[- ]threshold (?:date|claim|estimate|promotion|result)s?\b",
    ),
    ClaimRule(
        "policy_failure_claim",
        r"\bpolicy[- ]failure (?:claim|threshold|estimate|promotion|result|output)s?\b",
    ),
    ClaimRule(
        "higher_rates_always_raise_inflation_claim",
        r"\bhigher rates always raise inflation\b|\brate hikes always raise inflation\b",
    ),
    ClaimRule(
        "pricing_output_claim",
        r"\bpricing[- ]output\b|\bpricing[- ]claim\b|\bmarket[- ]pricing\b",
    ),
    ClaimRule(
        "incidence_claim",
        (
            r"\bincidence[- ](?:claim|output|estimate|promotion|result)s?\b|"
            r"\b(?:claim|output|estimate|promotion|result)s?.{0,20}\bincidence\b"
        ),
    ),
    ClaimRule("welfare_claim", r"\bwelfare[- ]claim\b|\bwelfare[- ]output\b"),
    ClaimRule("tax_output_claim", r"\btax[- ]output\b|\btax[- ]claim\b"),
    ClaimRule(
        "mpc_claim",
        (
            r"\bMPC[- ](?:claim|output|estimate|promotion|result)s?\b|"
            r"\b(?:claim|output|estimate|promotion|result)s?.{0,20}\bMPC\b|"
            r"\bmarginal propensity to consume\b"
        ),
    ),
    ClaimRule(
        "holder_allocation_claim",
        (
            r"\bholder[- ]allocation[- ]"
            r"(?:claim|output|estimate|promotion|result)s?\b|"
            r"\b(?:claim|output|estimate|promotion|result)s?.{0,20}"
            r"\bholder[- ]allocation\b|\bbeneficial[- ]owner allocation\b|"
            r"\bforeign holder allocation\b"
        ),
    ),
    ClaimRule(
        "reset_calendar_construction_claim",
        (
            r"\breset[- ]calendar[- ]"
            r"(?:construction|claim|output|estimate|promotion|result)s?\b|"
            r"\b(?:claim|output|estimate|promotion|result)s?.{0,20}"
            r"\breset[- ]calendar\b"
        ),
    ),
    ClaimRule(
        "raw_rate_shock_claim",
        (
            r"\braw[- ]rate[- ]shock[- ]"
            r"(?:claim|estimate|identification|promotion|result|output)s?\b|"
            r"\braw policy[- ]rate changes as shocks\b"
        ),
    ),
    ClaimRule(
        "causal_financialization_claim",
        (
            r"\bcausal[- ]financialization[- ]"
            r"(?:claim|estimate|engine|evidence|promotion|result|output)s?\b|"
            r"\b(?:claim|estimate|engine|evidence|promotion|result|output)s?.{0,20}"
            r"\bcausal[- ]financialization\b"
        ),
    ),
    ClaimRule(
        "split_denominator_promotion_claim",
        r"\bsplit[- ]denominator promotion\b|\bpromot\w* split[- ]denominator\b",
    ),
    ClaimRule(
        "evidence_mode_promotion_claim",
        r"\bevidence mode promotion\b|\bpromot\w*.{0,40}\bevidence mode\b",
    ),
    ClaimRule(
        "canonical_sidecar_promotion_claim",
        r"\bsidecar.{0,40}canonical\b|\bcanonical.{0,40}sidecar\b",
    ),
    ClaimRule(
        "composite_financialization_index_claim",
        (
            r"\bcomposite financialization index\b|"
            r"\bfinancialization composite\b|\ball[- ]financialization index\b"
        ),
    ),
]

ALLOWED_BOUNDARY_PATTERNS = [
    r"\bdisabled\b",
    r"\b[a-z0-9_]+_enabled=false\b",
    r"\bclaim_enabled=false\b",
    r"\b[a-z0-9_-]+(?:\s+[a-z0-9_-]+)*\s+allowed:\s*`?false`?\b",
    r"\b[a-z0-9_]+_allowed=false\b",
    r"\bpromotion_gate_passed=false\b",
    r"\benters_main_ratio=false\b",
    r"\bnot enabled\b",
    r"\bnot a claim\b",
    r"\bdoes not claim\b",
    r"\bdoes not enable\b",
    r"\bdoes not mean\b",
    r"\bdoes not promote\b",
    r"\bdoes not report\b",
    r"\bdoes not widen\b",
    r"\bdoes not support\b",
    r"\bdoes not turn\b",
    r"\bdo not generate\b",
    r"\bdo not enable\b",
    r"\bdo not claim\b",
    r"\bdo not report\b",
    r"\bdo not use\b",
    r"\bshould not say\b",
    r"\bcannot estimate\b",
    r"\bcannot enable\b",
    r"\bcannot promote\b",
    r"\bcannot support\b",
    r"\bcannot be read\b",
    r"\bcannot be used\b",
    r"\bmust not be read\b",
    r"\bnot read as\b",
    r"\bnot to promote\b",
    r"\bnot treated as\b",
    r"\bnot sufficient\b",
    r"\bnot exposed\b",
    r"\bnot final\b",
    r"\bnot causal\b",
    r"\bnot a .{0,120}engine\b",
    r"\bnot a .{0,120}model\b",
    r"\bnot a .{0,120}estimate\b",
    r"\bnot a .{0,120}result\b",
    r"\bnot a .{0,120}effect\b",
    r"\bnot .{0,80}estimate\b",
    r"\bnot .{0,80}evidence\b",
    r"\bnot .{0,80}classifier\b",
    r"\bnot .{0,80}output\b",
    r"\bnot that an empirical\b",
    r"\bnot allowed\b",
    r"\bnot an empirical threshold\b",
    r"\bnot a .{0,40}claim\b",
    r"\bnot .{0,200}claims?\b",
    r"\bno .{0,260}claims?\b",
    r"\bno .{0,80}output\b",
    r"\bno .{0,80}estimate\b",
    r"\bno .{0,80}promotion\b",
    r"\bno .{0,80}index\b",
    r"\bno .{0,120}(?:engine|output|result|claim|construction|promotion|index|identification)\b",
    r"\bcannot .{0,200}claims?\b",
    r"\bcannot present\b",
    r"\bcannot .{0,80}estimate\b",
    r"\bwithout .{0,80}claims?\b",
    r"\bwithout .{0,80}output\b",
    r"\bwithout .{0,80}promotion\b",
    r"\bwithout .{0,80}empirical threshold\b",
    r"\bwithout .{0,160}(?:promoting|widening|enabling|claiming)\b",
    r"\bbefore any .{0,80}(?:output|claim|promotion|construction|result)\b",
    r"\bbefore .{0,80}(?:output|claim|promotion|construction|result)\b",
    r"\bmust not .{0,80}claims?\b",
    r"\bdo not .{0,260}claims?\b",
    r"\brather than claiming\b",
    r"\bno row .{0,260}(?:enables|promotes|creates)\b",
    r"\bexcludes? .{0,120}(?:output|claim|identification|construction|promotion|index|result)s?\b",
    r"\bnon[- ]pricing .{0,40}claim\b",
    r"\bdesign contract only\b",
    r"\bnot allowed[:=]\b",
    r"\bnot_allowed_use=",
    r"\bblocked_(?:scope|field|use)=",
    r"\bpromotion_blocker=",
    r"\bclaims_still_disabled_after_pass=",
    r"\bdisabled_claims_and_forbidden_outputs\b",
    r"\bclaim boundary\b",
    r"\bdisabled_switch_rows=\d+;",
    r"\bswitches remain false\b",
    r"\bseparate opt[- ]in model\b",
    r"\bunless .{0,80}(?:opt[- ]in|separate)\b",
    r"\bpreserving canonical ratio and classifier labels\b",
    r"\bno welfare claim\b",
    r"\bno incidence claim\b",
    r"\bno pricing claim\b",
    r"\bnot evidence mode promotion\b",
    r"\bnot empirical\b",
    r"\bnot policy failure\b",
    r"\bfail[- ]closed\b",
    r"\bcontext[- ]only\b",
    r"\bsidecar[- ]only\b",
    r"\bexcluded from canonical\b",
    r"\boutside the main ratio\b",
    r"\bkept outside\b",
    r"\bseparated from\b",
    r"\bnot canonical\b",
    r"\bnoncanonical\b",
    r"\bnot classifier\b",
    r"\bremaining evidence\b",
    r"\bevidence target\b",
    r"\bevidence needed\b",
    r"\bevidence gap\b",
    r"\bsource target\b",
    r"\bsource gap\b",
    r"\brejects\b",
    r"\breject\b",
    r"\binadmissible\b",
    r"\bvalidation-only\b",
    r"\bscaffold\b",
    r"\bremain blocked\b",
    r"\bremains blocked\b",
    r"\bremain barred\b",
    r"\bremains barred\b",
    r"\bremain disabled\b",
    r"\bremains disabled\b",
    r"\bblocked\b",
    r"\bblock\b",
    r"\bblocks\b",
    r"\bforbidden\b",
    r"\bdisallowed\b",
    r"\brejected\b",
    r"\bwithout changing\b",
    r"\bdesign_only\b",
]


def generated_text_claim_boundary_scan_rows(output_dir: Path) -> list[dict[str, str]]:
    """Scan generated Markdown/CSV/JSON artifacts for unqualified claim drift."""

    tasks = [
        (artifact_path.as_posix(), artifact_kind, rule)
        for artifact_path, artifact_kind in _generated_artifact_paths(output_dir)
        for rule in CLAIM_RULES
    ]
    if not tasks:
        return []

    workers = _claim_scan_workers()
    if workers == 1:
        scanned_rows = [_scan_artifact_claim_rule(task) for task in tasks]
    else:
        executor = ProcessPoolExecutor(max_workers=workers)
        restored_signals: dict[int, object] = {}

        def _shutdown_executor(*, wait: bool, terminate_workers: bool) -> None:
            processes = list((getattr(executor, "_processes", None) or {}).values())
            executor.shutdown(wait=wait, cancel_futures=True)
            if terminate_workers:
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                for process in processes:
                    process.join(timeout=5)
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=5)

        def _signal_shutdown(signum: int, _frame: object) -> None:
            _shutdown_executor(wait=False, terminate_workers=True)
            raise KeyboardInterrupt(
                f"generated text claim scan interrupted by signal {signum}"
            )

        if threading.current_thread() is threading.main_thread():
            for signum in (signal.SIGINT, signal.SIGTERM):
                restored_signals[signum] = signal.getsignal(signum)
                signal.signal(signum, _signal_shutdown)
        try:
            scanned_rows = list(executor.map(_scan_artifact_claim_rule, tasks))
        except BaseException:
            _shutdown_executor(wait=False, terminate_workers=True)
            raise
        else:
            _shutdown_executor(wait=True, terminate_workers=False)
        finally:
            for signum, handler in restored_signals.items():
                signal.signal(signum, handler)

    rows = [row for row in scanned_rows if row is not None]
    rows.sort(key=lambda row: (row["artifact_path"], row["claim_rule_id"]))
    return rows


def _claim_scan_workers() -> int:
    raw_workers = os.environ.get(
        "RATEWALL_CLAIM_SCAN_WORKERS", str(DEFAULT_CLAIM_SCAN_WORKERS)
    )
    try:
        workers = int(raw_workers)
    except ValueError as exc:
        raise ValueError(
            "RATEWALL_CLAIM_SCAN_WORKERS must be a positive integer"
        ) from exc
    if workers < 1:
        raise ValueError("RATEWALL_CLAIM_SCAN_WORKERS must be a positive integer")
    return workers


def _scan_artifact_claim_rule(
    task: tuple[str, str, ClaimRule],
) -> dict[str, str] | None:
    artifact_path_text, artifact_kind, rule = task
    artifact_path = Path(artifact_path_text)
    text = _artifact_text(artifact_path)
    if not text:
        return None

    matches = list(re.finditer(rule.forbidden_pattern, text, flags=re.IGNORECASE))
    allowed_hits = [
        _allowed_boundary_hit(text=text, start=match.start(), end=match.end())
        for match in matches
    ]
    allowed_matches = [match for match, hit in zip(matches, allowed_hits) if hit]
    allowed_boundary_pattern_hits = sorted({hit for hit in allowed_hits if hit})
    unqualified_matches = [match for match in matches if match not in allowed_matches]
    return {
        "artifact_path": artifact_path.as_posix(),
        "artifact_kind": artifact_kind,
        "claim_rule_id": rule.claim_rule_id,
        "forbidden_pattern": rule.forbidden_pattern,
        "allowed_boundary_patterns": ";".join(ALLOWED_BOUNDARY_PATTERNS),
        "total_match_count": str(len(matches)),
        "allowed_boundary_match_count": str(len(allowed_matches)),
        "allowed_boundary_pattern_hit": ";".join(allowed_boundary_pattern_hits),
        "forbidden_unqualified_match_count": str(len(unqualified_matches)),
        "sample_unqualified_match": _sample_match(text, unqualified_matches),
        "scan_window_chars": str(SCAN_WINDOW_CHARS),
        "audit_status": "pass" if not unqualified_matches else "fail",
        "failure_mode_if_false": (
            "generated artifact contains unqualified forbidden claim "
            "language without nearby boundary wording"
        ),
        "claim_boundary": GENERATED_TEXT_CLAIM_BOUNDARY,
    }


def _generated_artifact_paths(output_dir: Path) -> list[tuple[Path, str]]:
    reports_dir = output_dir / "reports"
    tables_dir = output_dir / "tables"
    artifacts: list[tuple[Path, str]] = []
    if reports_dir.exists():
        for path in sorted(reports_dir.iterdir()):
            if path.suffix.lower() in {".md", ".qmd", ".cff"}:
                artifacts.append((path, "markdown_report"))
    if tables_dir.exists():
        for path in sorted(tables_dir.iterdir()):
            if path.name == "ratewall_generated_text_claim_boundary_scan.csv":
                continue
            if path.suffix.lower() == ".csv":
                artifacts.append((path, "csv_table"))
            elif path.suffix.lower() == ".json":
                artifacts.append((path, "json_manifest"))
    return artifacts


def _artifact_text(path: Path) -> str:
    if path.suffix.lower() == ".csv":
        return _csv_text(path)
    if path.suffix.lower() == ".json":
        return _json_text(path)
    return path.read_text(encoding="utf-8", errors="replace")


def _csv_text(path: Path) -> str:
    chunks: list[str] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames:
            for row in reader:
                row_chunks = []
                for field, value in row.items():
                    if value and not _numeric_only(value):
                        row_chunks.append(f"{field}={value}")
                if row_chunks:
                    chunks.append(" | ".join(row_chunks))
        else:
            handle.seek(0)
            fallback_reader = csv.reader(handle)
            for row in fallback_reader:
                for value in row:
                    if value and not _numeric_only(value):
                        chunks.append(value)
    return "\n".join(chunks)


def _json_text(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    return json.dumps(payload, indent=2, sort_keys=True)


def _numeric_only(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    return bool(re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?", stripped))


def _allowed_boundary_hit(*, text: str, start: int, end: int) -> str:
    window = text[max(0, start - SCAN_WINDOW_CHARS) : end + SCAN_WINDOW_CHARS]
    for pattern in ALLOWED_BOUNDARY_PATTERNS:
        if re.search(pattern, window, flags=re.IGNORECASE):
            return pattern
    return ""


def _sample_match(text: str, matches: list[re.Match[str]]) -> str:
    if not matches:
        return ""
    match = matches[0]
    window = text[max(0, match.start() - 40) : match.end() + 40]
    return " ".join(window.split())
