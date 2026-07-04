"""Materialize NDFI/private-credit context source snapshots."""

from __future__ import annotations

import argparse
import hashlib
import re
from collections.abc import Callable
from pathlib import Path
from urllib.request import Request, urlopen

from ratewall.data.snapshots import read_snapshot_bundle, write_snapshot_bundle
from ratewall.sources.base import RetrievalMetadata, SourceSnapshot, utc_now_iso
from ratewall.sources.registry import SourceRegistry


FED_PRIVATE_CREDIT_SERIES_ID = "fed_private_credit_notes"
FED_INDIRECT_CREDIT_SUPPLY_SERIES_ID = "fed_indirect_credit_supply_private_credit"
OFR_PRIVATE_CREDIT_COUNTERPARTY_SERIES_ID = (
    "ofr_private_credit_counterparty_exposure_context"
)


def _fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 ratewall-research"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _extract_record(html: str) -> dict[str, str]:
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    lowered = plain.lower()
    required_markers = {
        "private credit growth and monetary policy transmission": "title",
        "direct lending": "direct_lending_context",
        "leveraged loans": "leveraged_loan_context",
        "floating": "floating_rate_context",
        "sofr": "sofr_context",
        "reset": "repricing_context",
    }
    missing = [name for marker, name in required_markers.items() if marker not in lowered]
    if missing:
        raise ValueError(
            "Fed private-credit note missing expected markers: " + ", ".join(missing)
        )
    return {
        "date": "2024-08-02",
        "publication_date": "2024-08-02",
        "source_note": "Private Credit Growth and Monetary Policy Transmission",
        "source_scope": "private_credit_direct_lending_and_leveraged_loan_context",
        "evidence_role": "ndfi_private_credit_transmission_context_only",
        "floating_rate_marker_verified": "true",
        "sofr_marker_verified": "true",
        "repricing_marker_verified": "true",
        "direct_lending_marker_verified": "true",
        "leveraged_loan_marker_verified": "true",
        "exposure_size_available": "false",
        "borrower_pass_through_available": "false",
        "split_denominator_promotion_allowed": "false",
        "prior_narrowing_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "empirical_threshold_date_enabled": "false",
        "policy_failure_claim_enabled": "false",
        "causal_financialization_claim_enabled": "false",
    }


def _extract_fed_indirect_credit_supply_record(html: str) -> dict[str, str]:
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    lowered = plain.lower()
    required_markers = {
        "indirect credit supply": "title",
        "banks lend to business development companies": "bank_bdc_chain_context",
        "bdcs": "bdc_context",
        "pass on to firms": "borrower_pass_through_context",
        "weaker interest coverage ratios": "interest_coverage_context",
        "supervisory bank loan-level data": "nonpublic_supervisory_data_context",
    }
    missing = [name for marker, name in required_markers.items() if marker not in lowered]
    if missing:
        raise ValueError(
            "Fed indirect-credit-supply page missing expected markers: "
            + ", ".join(missing)
        )
    return {
        "date": "2025-10-31",
        "publication_date": "2025-08",
        "source_note": (
            "Indirect Credit Supply: How Bank Lending to Private Credit Shapes "
            "Monetary Policy Transmission"
        ),
        "source_scope": "bank_bdc_private_credit_intermediation_context",
        "evidence_role": "ndfi_private_credit_borrower_pass_through_context_only",
        "bank_bdc_intermediation_chain_marker_verified": "true",
        "borrower_pass_through_marker_verified": "true",
        "interest_coverage_marker_verified": "true",
        "nonpublic_supervisory_data_marker_verified": "true",
        "public_reusable_loan_level_artifact_available": "false",
        "exposure_size_available": "false",
        "borrower_pass_through_available": "context_only_not_promotable",
        "split_denominator_promotion_allowed": "false",
        "prior_narrowing_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "empirical_threshold_date_enabled": "false",
        "policy_failure_claim_enabled": "false",
        "causal_financialization_claim_enabled": "false",
    }


def _extract_ofr_counterparty_record(html: str) -> dict[str, str]:
    plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    lowered = plain.lower()
    required_markers = {
        "measuring counterparty exposures to private credit": "title",
        "published: march 12, 2026": "publication_date",
        "counterparty exposures between banks and private credit funds": "counterparty_exposure_context",
        "main channel for risk transmission": "risk_transmission_context",
        "private credit has expanded significantly": "growth_context",
        "forged linkages with traditional financial institutions": "bank_linkage_context",
    }
    missing = [name for marker, name in required_markers.items() if marker not in lowered]
    if missing:
        raise ValueError(
            "OFR private-credit counterparty page missing expected markers: "
            + ", ".join(missing)
        )
    return {
        "date": "2026-03-12",
        "publication_date": "2026-03-12",
        "source_note": "Measuring Counterparty Exposures to Private Credit",
        "source_scope": "private_credit_fund_bank_counterparty_exposure_context",
        "evidence_role": "ndfi_private_credit_counterparty_exposure_context_only",
        "form_pf_context_marker_verified": "false",
        "counterparty_exposure_marker_verified": "true",
        "bank_linkage_marker_verified": "true",
        "public_reusable_fund_level_artifact_available": "false",
        "exposure_size_available": "context_only_not_promotable",
        "maturity_liquidity_context_available": "false",
        "borrower_pass_through_available": "false",
        "split_denominator_promotion_allowed": "false",
        "prior_narrowing_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "empirical_threshold_date_enabled": "false",
        "policy_failure_claim_enabled": "false",
        "causal_financialization_claim_enabled": "false",
    }


def _snapshot(
    *,
    registry: SourceRegistry,
    series_id: str,
    note_prefix: str,
    record_extractor: Callable[[str], dict[str, str]],
) -> SourceSnapshot:
    series = registry.series_definition(series_id)
    html = _fetch_text(series.endpoint)
    html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    record = record_extractor(html)
    note = (
        f"{note_prefix};"
        f"source_html_sha256={html_sha};"
        "source_record_count=1;"
        f"first_observation_date={record['date']};"
        f"latest_observation_date={record['date']};"
        "ndfi_private_credit_gate_passed=false;"
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
    for snapshot in (
        _snapshot(
            registry=registry,
            series_id=FED_PRIVATE_CREDIT_SERIES_ID,
            note_prefix="fed_private_credit_transmission_context_only",
            record_extractor=_extract_record,
        ),
        _snapshot(
            registry=registry,
            series_id=FED_INDIRECT_CREDIT_SUPPLY_SERIES_ID,
            note_prefix="fed_indirect_credit_supply_private_credit_context_only",
            record_extractor=_extract_fed_indirect_credit_supply_record,
        ),
        _snapshot(
            registry=registry,
            series_id=OFR_PRIVATE_CREDIT_COUNTERPARTY_SERIES_ID,
            note_prefix="ofr_private_credit_counterparty_exposure_context_only",
            record_extractor=_extract_ofr_counterparty_record,
        ),
    ):
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
