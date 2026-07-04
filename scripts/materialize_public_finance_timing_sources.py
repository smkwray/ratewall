"""Materialize public-finance timing source snapshots into RateWall raw bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from ratewall.data.build import _fiscaldata_params
from ratewall.data.snapshots import read_snapshot_bundle, write_snapshot_bundle
from ratewall.sources.base import SourceSnapshot
from ratewall.sources.fiscaldata import FiscalDataAdapter
from ratewall.sources.registry import SourceRegistry


PUBLIC_FINANCE_TIMING_SERIES = ("treasury_dts",)


def _records_sha256(records: Sequence[object]) -> str:
    payload = json.dumps(
        list(records),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _date_range(snapshot: SourceSnapshot) -> tuple[str, str]:
    dates = sorted(
        str(record.get("record_date", ""))
        for record in snapshot.records
        if record.get("record_date")
    )
    if not dates:
        return "", ""
    return dates[0], dates[-1]


def _annotated_dts_snapshot(snapshot: SourceSnapshot) -> SourceSnapshot:
    first_date, latest_date = _date_range(snapshot)
    account_types = sorted(
        {
            str(record.get("account_type", ""))
            for record in snapshot.records
            if record.get("account_type")
        }
    )
    records_hash = _records_sha256(snapshot.records)
    note = (
        "public_finance_timing_tga_operating_cash_balance_context_only;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(snapshot.records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"account_types={','.join(account_types)};"
        "timing_nonadditivity_bridge_passed=false;"
        "absorber_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false"
    )
    return SourceSnapshot(
        metadata=replace(snapshot.metadata, note=note),
        records=snapshot.records,
    )


def materialize(
    *,
    config: Path,
    snapshot_bundle: Path,
    output: Path,
) -> Path:
    registry = SourceRegistry.from_path(config)
    adapter = FiscalDataAdapter(registry)
    existing = read_snapshot_bundle(snapshot_bundle)
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in existing}
    for series_id in PUBLIC_FINANCE_TIMING_SERIES:
        snapshot = adapter.pull_table(
            series_id,
            params=_fiscaldata_params(series_id),
            paginate=False,
        )
        by_series[series_id] = _annotated_dts_snapshot(snapshot)
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
    parser.add_argument("--output", type=Path, default=Path("data/raw/ratewall_snapshot.json"))
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
