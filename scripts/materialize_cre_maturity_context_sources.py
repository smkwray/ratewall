"""Materialize CRE maturity context source snapshots."""

from __future__ import annotations

import argparse
import hashlib
import re
from decimal import Decimal
from pathlib import Path
from urllib.request import Request, urlopen

from ratewall.data.snapshots import read_snapshot_bundle, write_snapshot_bundle
from ratewall.sources.base import RetrievalMetadata, SourceSnapshot, utc_now_iso
from ratewall.sources.registry import SourceRegistry


MBA_CRE_MATURITY_SERIES_ID = "mba_cre_maturity_ladder_context"


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 ratewall-research"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _extract_cre_maturity_record(html: str) -> dict[str, str]:
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    lowered = plain.lower()
    required_markers = {
        "seventeen percent": "maturing_share",
        "$875 billion": "maturing_balance",
        "$5.0 trillion": "outstanding_balance",
        "mature in 2026": "maturity_year",
        "commercial real estate survey of loan maturity volumes": "source_survey",
    }
    missing = [name for marker, name in required_markers.items() if marker not in lowered]
    if missing:
        raise ValueError(
            "MBA CRE maturity page missing expected markers: " + ", ".join(missing)
        )
    return {
        "date": "2026-02-01",
        "publication_date": "2026-02",
        "maturity_year": "2026",
        "maturing_balance_bil": "875",
        "outstanding_balance_bil": "5000",
        "maturing_share": str(Decimal("875") / Decimal("5000")),
        "previous_year_scheduled_maturing_balance_bil": "957",
        "reported_change_from_previous_year_pct": "-9",
        "source_survey": "2025 Commercial Real Estate Survey of Loan Maturity Volumes",
        "source_scope": "commercial_and_multifamily_mortgages_held_by_lenders_and_investors",
        "evidence_role": "cre_maturity_refinancing_context_only",
        "split_denominator_promotion_allowed": "false",
        "prior_narrowing_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "empirical_threshold_date_enabled": "false",
        "pricing_output_enabled": "false",
    }


def _snapshot(*, registry: SourceRegistry) -> SourceSnapshot:
    series = registry.series_definition(MBA_CRE_MATURITY_SERIES_ID)
    html = _fetch_text(series.endpoint)
    html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    record = _extract_cre_maturity_record(html)
    note = (
        "mba_cre_maturity_context_only;"
        f"source_html_sha256={html_sha};"
        "source_record_count=1;"
        "first_observation_date=2026-02-01;"
        "latest_observation_date=2026-02-01;"
        "cre_refinancing_gate_passed=false;"
        "split_denominator_promotion_allowed=false;"
        "prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false"
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=series.source,
            series_id=series.series_id,
            source_url=series.endpoint,
            units=series.units,
            frequency=series.frequency,
            transform=series.transform,
            retrieved_at=utc_now_iso(),
            source_release_at=record["publication_date"],
            snapshot_kind="live_text_context",
            note=note,
        ),
        records=[record],
    )


def materialize(*, config: Path, snapshot_bundle: Path, output: Path) -> Path:
    registry = SourceRegistry.from_path(config)
    existing = read_snapshot_bundle(snapshot_bundle)
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in existing}
    snapshot = _snapshot(registry=registry)
    by_series[snapshot.metadata.series_id] = snapshot
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
