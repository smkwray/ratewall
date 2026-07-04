"""Derive accounting inputs from source snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ratewall.accounting.rate_impulse import HorizonRepricing, RateImpulseInputs
from ratewall.sources.base import SourceSnapshot


@dataclass(frozen=True)
class DerivedAccountingInputs:
    reserves_bil: Decimal
    on_rrp_bil: Decimal
    gdp_bil: Decimal
    debt_held_public_bil: Decimal
    net_interest_fytd_bil: Decimal
    fed_deferred_asset_bil: Decimal
    horizons: tuple[HorizonRepricing, ...]
    provenance: dict[str, str]
    maturity_ladder: tuple[dict[str, Decimal | str], ...]

    def to_rate_impulse_inputs(self) -> RateImpulseInputs:
        return RateImpulseInputs(
            reserves=self.reserves_bil,
            on_rrp=self.on_rrp_bil,
            gdp=self.gdp_bil,
            horizons=self.horizons,
            existing_remittance_capacity=(
                Decimal("0") if self.fed_deferred_asset_bil > 0 else Decimal("0")
            ),
        )


def derive_accounting_inputs(
    snapshots: list[SourceSnapshot],
) -> DerivedAccountingInputs:
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in snapshots}
    reserves_bil = _latest_decimal(by_series["WRESBAL"]) / Decimal("1000")
    on_rrp_bil = _latest_decimal(by_series["RRPONTSYD"]) / Decimal("1000")
    gdp_bil = _latest_decimal(by_series["GDP"])
    debt_bil = _first_decimal(
        by_series["debt_to_penny"],
        ("debt_held_public_amt", "tot_pub_debt_out_amt"),
    ) / Decimal("1000000000")
    net_interest_bil = _first_decimal(
        by_series["mts_table_4"],
        ("current_fytd_net_outly_amt", "current_fytd_net_outlay_amt", "amount"),
        predicate=_is_public_debt_interest_total,
    ) / Decimal("1000000000")
    deferred_asset_bil = _first_decimal(
        by_series["h41_current"], ("deferred_asset_amt",)
    ) / Decimal("1000")
    anchor = _latest_record(by_series["treasury_repricing_anchor"])
    maturity_ladder = build_maturity_ladder(
        debt_bil=debt_bil,
        anchor=anchor,
        soma_snapshot=by_series.get("nyfed_soma_summary"),
        mspd_snapshot=by_series.get("treasury_mspd_table_3"),
    )
    horizons = tuple(
        HorizonRepricing(
            label=str(row["label"]),
            months=row["months"],
            debt_repricing=row["debt_repricing_bil"],
            source_status=str(row.get("source_status", "source_backed_ratewall_impulse")),
        )
        for row in maturity_ladder
    )
    provenance = {
        snapshot.metadata.series_id: snapshot.metadata.retrieved_at
        for snapshot in snapshots
    }
    return DerivedAccountingInputs(
        reserves_bil=reserves_bil,
        on_rrp_bil=on_rrp_bil,
        gdp_bil=gdp_bil,
        debt_held_public_bil=debt_bil,
        net_interest_fytd_bil=net_interest_bil,
        fed_deferred_asset_bil=deferred_asset_bil,
        horizons=horizons,
        provenance=provenance,
        maturity_ladder=maturity_ladder,
    )


def build_maturity_ladder(
    *,
    debt_bil: Decimal,
    anchor: dict,
    soma_snapshot: SourceSnapshot | None = None,
    mspd_snapshot: SourceSnapshot | None = None,
) -> tuple[dict[str, Decimal | str], ...]:
    """Construct a live repricing ladder from MSPD when available."""

    if (
        mspd_snapshot is not None
        and mspd_snapshot.records
        and mspd_snapshot.metadata.snapshot_kind != "fallback_stub"
    ):
        mspd_ladder = _mspd_maturity_ladder(
            debt_bil=debt_bil,
            mspd_snapshot=mspd_snapshot,
            soma_rate_sensitive_bil=_soma_rate_sensitive_bil(soma_snapshot),
        )
        if mspd_ladder:
            return mspd_ladder
    if mspd_snapshot is not None and mspd_snapshot.metadata.snapshot_kind == "fallback_stub":
        fallback_source_status = "anchor_fallback_not_live_security_level"
        fallback_note = (
            "JEC/Treasury anchor fallback used because Treasury FiscalData MSPD "
            "table 3 is fallback_stub; not live security-level repricing data"
        )
    else:
        fallback_source_status = "anchor_fallback_no_security_level_mspd"
        fallback_note = "JEC/Treasury anchor plus NY Fed SOMA bills/FRNs context"

    one_year_share = Decimal(str(anchor["matures_within_12m_share"]))
    rows = [
        ("1q", Decimal("3"), Decimal(str(anchor["one_quarter_share"]))),
        ("1y", Decimal("12"), one_year_share),
        ("3y", Decimal("36"), Decimal(str(anchor["three_year_share"]))),
        ("10y", Decimal("120"), Decimal(str(anchor["ten_year_share"]))),
    ]
    soma_rate_sensitive_bil = _soma_rate_sensitive_bil(soma_snapshot)
    return tuple(
        {
            "label": label,
            "months": months,
            "share_of_debt": share,
            "debt_repricing_bil": debt_bil * share,
            "soma_bills_frns_bil": soma_rate_sensitive_bil,
            "source_status": fallback_source_status,
            "source_snapshot_kind": (
                mspd_snapshot.metadata.snapshot_kind if mspd_snapshot is not None else "missing"
            ),
            "source_record_count": len(mspd_snapshot.records) if mspd_snapshot else 0,
            "source_note": fallback_note,
        }
        for label, months, share in rows
    )


def _mspd_maturity_ladder(
    *,
    debt_bil: Decimal,
    mspd_snapshot: SourceSnapshot,
    soma_rate_sensitive_bil: Decimal,
) -> tuple[dict[str, Decimal | str], ...]:
    latest_date = _latest_record(mspd_snapshot).get("record_date")
    if not latest_date:
        return ()
    as_of = date.fromisoformat(str(latest_date))
    horizon_months = (
        ("1q", Decimal("3")),
        ("1y", Decimal("12")),
        ("3y", Decimal("36")),
        ("10y", Decimal("120")),
    )
    repricing_by_horizon = {label: Decimal("0") for label, _months in horizon_months}
    for record in mspd_snapshot.records:
        if record.get("record_date") != latest_date:
            continue
        if str(record.get("security_type_desc", "")).lower() != "marketable":
            continue
        security_class = str(record.get("security_class1_desc", "")).lower()
        if security_class.startswith("total"):
            continue
        amount_bil = _mspd_amount_bil(record)
        if amount_bil <= 0:
            continue
        maturity = record.get("maturity_date")
        if _is_floating_rate(record):
            months_to_repricing = Decimal("0")
        elif maturity in (None, "", "null"):
            continue
        else:
            days = (date.fromisoformat(str(maturity)) - as_of).days
            if days < 0:
                continue
            months_to_repricing = Decimal(days) / Decimal("30.4375")
        for label, months in horizon_months:
            if months_to_repricing <= months:
                repricing_by_horizon[label] += amount_bil
    if not any(repricing_by_horizon.values()):
        return ()
    rows = []
    for label, months in horizon_months:
        repricing_bil = min(repricing_by_horizon[label], debt_bil)
        rows.append(
            {
                "label": label,
                "months": months,
                "share_of_debt": min(repricing_bil / debt_bil, Decimal("1")),
                "debt_repricing_bil": repricing_bil,
                "soma_bills_frns_bil": soma_rate_sensitive_bil,
                "source_status": (
                    "live_mspd_bucket_repricing_context"
                    if mspd_snapshot.metadata.snapshot_kind == "live"
                    else f"{mspd_snapshot.metadata.snapshot_kind}_security_level_fixture"
                ),
                "source_snapshot_kind": mspd_snapshot.metadata.snapshot_kind,
                "source_record_count": len(mspd_snapshot.records),
                "source_note": (
                    "Treasury FiscalData MSPD table 3 security-level maturity proxy; "
                    "FRNs treated as near-term repricing exposure; repricing dollars "
                    "capped at reconciled debt held by the public"
                ),
            }
        )
    return tuple(rows)


def _mspd_amount_bil(record: dict) -> Decimal:
    for field in ("current_month_outstanding_amt", "outstanding_amt"):
        value = record.get(field)
        parsed = _optional_decimal(value)
        if parsed is not None:
            return parsed / Decimal("1000")
    issued = record.get("issued_amt")
    redeemed = record.get("redeemed_amt")
    issued_amt = _optional_decimal(issued)
    if issued_amt is not None:
        redeemed_amt = _optional_decimal(redeemed) or Decimal("0")
        return max(issued_amt - redeemed_amt, Decimal("0")) / Decimal("1000")
    return Decimal("0")


def _optional_decimal(value) -> Decimal | None:
    if value in (None, "", ".", "null", "None"):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except Exception:
        return None


def _is_floating_rate(record: dict) -> bool:
    description = " ".join(
        str(record.get(field, ""))
        for field in ("security_class1_desc", "security_class3_desc")
    ).lower()
    return "floating rate" in description


def _soma_rate_sensitive_bil(snapshot: SourceSnapshot | None) -> Decimal:
    if snapshot is None or not snapshot.records:
        return Decimal("0")
    record = _latest_record(snapshot)
    total = Decimal("0")
    for field in ("bills", "frn"):
        value = record.get(field)
        if value not in (None, "", ".", "null"):
            total += Decimal(str(value).replace(",", ""))
    return total / Decimal("1000000000")


def _latest_decimal(snapshot: SourceSnapshot) -> Decimal:
    for record in _records_newest_first(snapshot):
        value = record.get("value")
        if value not in (None, "", "."):
            return Decimal(str(value))
    raise ValueError(f"no numeric observations for {snapshot.metadata.series_id}")


def _first_decimal(
    snapshot: SourceSnapshot,
    fields: tuple[str, ...],
    predicate=None,
) -> Decimal:
    for record in _records_newest_first(snapshot):
        if predicate is not None and not predicate(record):
            continue
        for field in fields:
            value = record.get(field)
            if value not in (None, "", ".", "null"):
                return Decimal(str(value).replace(",", ""))
    joined = ", ".join(fields)
    raise ValueError(f"no {joined} value for {snapshot.metadata.series_id}")


def _latest_record(snapshot: SourceSnapshot) -> dict:
    records = _records_newest_first(snapshot)
    if not records:
        raise ValueError(f"no records for {snapshot.metadata.series_id}")
    return records[0]


def _records_newest_first(snapshot: SourceSnapshot) -> list[dict]:
    records = [dict(record) for record in snapshot.records]
    date_keys = (
        "date",
        "record_date",
        "release_date",
        "as_of_date",
        "effectiveDate",
        "index_date",
        "month",
        "report_date",
    )

    def key(record: dict) -> str:
        for date_key in date_keys:
            if record.get(date_key):
                return str(record[date_key])
        return ""

    return sorted(records, key=key, reverse=True)


def _is_public_debt_interest_total(record: dict) -> bool:
    description = str(record.get("classification_desc", "")).lower()
    return "total--interest on the public debt" in description
