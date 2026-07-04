"""Materialize fail-closed SLOOS source-context snapshots."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from urllib.request import Request, urlopen

from ratewall.data.snapshots import read_snapshot_bundle, write_snapshot_bundle
from ratewall.sources.base import RetrievalMetadata, SourceSnapshot, utc_now_iso
from ratewall.sources.registry import SourceRegistry


SLOOS_SERIES = (
    "sloos_consumer_lending",
    "sloos_cre",
    "sloos_ndfi_special_questions",
)

SOURCE_MARKERS: dict[str, tuple[str, ...]] = {
    "sloos_consumer_lending": (
        "weaker demand for credit card and auto loans",
        "tighter standards for other consumer loans",
    ),
    "sloos_cre": (
        "increase in the general level of interest rates",
        "decrease in customer refinancing of maturing loans",
        "lowered debt service coverage ratios",
    ),
    "sloos_ndfi_special_questions": (
        "tighter standards for all categories of NDFI loans",
        "shorter maximum maturities of loans or credit lines",
    ),
}

REVIEWED_SUMMARIES: dict[str, str] = {
    "sloos_consumer_lending": (
        "April 2026 SLOOS reports unchanged credit-card and auto standards, "
        "tighter standards for other consumer loans, and weaker demand for "
        "credit-card, auto, and other consumer loans."
    ),
    "sloos_cre": (
        "April 2026 SLOOS reports CRE demand context in which banks citing "
        "weaker demand over the past year identified higher interest rates "
        "and decreased refinancing of maturing loans among reasons. It also "
        "reports modest net shares of banks lowering debt service coverage "
        "ratios for CLD and multifamily CRE loans."
    ),
    "sloos_ndfi_special_questions": (
        "April 2026 SLOOS NDFI special questions report tighter standards "
        "for all NDFI loan categories and tighter terms including shorter "
        "maximum maturities, stricter covenants, stricter collateralization, "
        "higher risk premiums, and lower maximum credit-line sizes."
    ),
}


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "ratewall-source-audit/1.0"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def _plain_text(html: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", without_tags).strip()


def _snapshot(
    *,
    series_id: str,
    source_url: str,
    html: str,
    text: str,
    registry: SourceRegistry,
) -> SourceSnapshot:
    markers = SOURCE_MARKERS[series_id]
    missing = [marker for marker in markers if marker not in text]
    if missing:
        raise ValueError(
            f"{series_id} missing SLOOS source markers: {', '.join(missing)}"
        )
    series = registry.series[series_id]
    html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    cre_dscr_context = series_id == "sloos_cre"
    ndfi_terms_context = series_id == "sloos_ndfi_special_questions"
    consumer_context = series_id == "sloos_consumer_lending"
    note = (
        "sloos_official_release_context_only;"
        f"source_html_sha256={html_sha};"
        "source_record_count=1;"
        "survey_release=2026-04;"
        "source_markers_verified=true;"
        f"cre_dscr_term_context_available={str(cre_dscr_context).lower()};"
        f"cre_refinancing_demand_context_available={str(cre_dscr_context).lower()};"
        f"ndfi_term_tightening_context_available={str(ndfi_terms_context).lower()};"
        f"consumer_lending_context_available={str(consumer_context).lower()};"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "pricing_output_enabled=false;"
        "empirical_threshold_date_enabled=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=source_url,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at="2026-04",
            snapshot_kind="live_text_context",
            note=note,
        ),
        records=[
            {
                "date": "2026-04-01",
                "survey_release": "2026-04",
                "series_id": series_id,
                "reviewed_summary": REVIEWED_SUMMARIES[series_id],
                "source_markers_verified": "true",
                "source_marker_1": markers[0],
                "source_marker_2": markers[1],
                "source_marker_3": markers[2] if len(markers) > 2 else "",
                "cre_dscr_term_context_available": str(cre_dscr_context).lower(),
                "cre_refinancing_demand_context_available": str(
                    cre_dscr_context
                ).lower(),
                "ndfi_term_tightening_context_available": str(
                    ndfi_terms_context
                ).lower(),
                "consumer_lending_context_available": str(consumer_context).lower(),
                "method_blocker": (
                    "sloos_cre_dscr_and_refinancing_terms_are_qualitative_"
                    "survey_context_not_public_loan_level_dscr_refinancing_"
                    "outcome_or_real_activity_mapping"
                    if cre_dscr_context
                    else "sloos_context_only_not_promotion_grade_design"
                ),
                "promotion_gate_passed": "false",
                "prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "main_ratio_admission_allowed": "false",
            }
        ],
    )


def materialize(*, config: Path, snapshot_bundle: Path, output: Path) -> Path:
    registry = SourceRegistry.from_path(config)
    source_url = registry.series["sloos_consumer_lending"].endpoint
    html = _fetch_text(source_url)
    text = _plain_text(html)
    existing = read_snapshot_bundle(snapshot_bundle)
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in existing}
    for series_id in SLOOS_SERIES:
        by_series[series_id] = _snapshot(
            series_id=series_id,
            source_url=source_url,
            html=html,
            text=text,
            registry=registry,
        )
    ordered = [by_series[series_id] for series_id in sorted(by_series)]
    return write_snapshot_bundle(ordered, output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/sources.yml"))
    parser.add_argument(
        "--snapshot-bundle",
        type=Path,
        default=Path("data/raw/ratewall_snapshot.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("data/raw/ratewall_snapshot.json")
    )
    args = parser.parse_args()
    output = materialize(
        config=args.config,
        snapshot_bundle=args.snapshot_bundle,
        output=args.output,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
