"""Federal Reserve Distributional Financial Accounts adapter."""

from __future__ import annotations

import csv
import io
import zipfile
from datetime import datetime
from decimal import Decimal
from typing import Callable
from urllib.request import Request, urlopen

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.registry import SourceRegistry


class FedDfaAdapter:
    def __init__(
        self,
        registry: SourceRegistry,
        *,
        opener: Callable = urlopen,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.registry = registry
        self.opener = opener
        self.clock = clock

    def pull_distributional_exposure(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "fed_dfa":
            raise ValueError(f"{series_id} is registered to {spec.source}, not fed_dfa")
        with open_with_timeout(self.opener, _request(spec.endpoint)) as response:
            archive_bytes = response.read()
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            with archive.open("dfa-networth-shares-detail.csv") as handle:
                shares_text = handle.read().decode("utf-8-sig")
            with archive.open("dfa-networth-levels-detail.csv") as handle:
                levels_text = handle.read().decode("utf-8-sig")
        if series_id == "fed_dfa_household_account_type_context":
            records = _account_type_records(levels_text=levels_text)
            transform_note = (
                "recipient_leakage_fed_dfa_household_account_type_context_only;"
                f"source_record_count={len(records)};"
                "tax_clawback_gate_passed=false;"
                "demand_conversion_prior_narrowing_allowed=false;"
                "formula_replacement_allowed=false;"
                "main_ratio_admission_allowed=false;"
                "incidence_output_enabled=false;"
                "welfare_tax_mpc_output_enabled=false"
            )
        elif series_id == "fed_dfa_household_liability_context":
            records = _household_liability_records(levels_text=levels_text)
            transform_note = (
                "fast_repricing_consumer_credit_dfa_liability_liquidity_context_only;"
                f"source_record_count={len(records)};"
                "product_balance_context_available=true;"
                "wealth_group_distribution_context_available=true;"
                "liquid_asset_proxy_context_available=true;"
                "borrower_level_microdata_available=false;"
                "payment_behavior_context_available=false;"
                "current_demand_conversion_available=false;"
                "denominator_prior_narrowing_allowed=false;"
                "split_denominator_promotion_allowed=false;"
                "formula_replacement_allowed=false;"
                "main_ratio_admission_allowed=false;"
                "incidence_output_enabled=false;"
                "welfare_tax_mpc_output_enabled=false"
            )
        else:
            records = _exposure_records(shares_text=shares_text, levels_text=levels_text)
            transform_note = None
        metadata = RetrievalMetadata(
            source_id="fed_dfa",
            series_id=series_id,
            source_url=spec.endpoint,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=records[0]["as_of_date"] if records else None,
            note=transform_note,
        )
        return SourceSnapshot(metadata=metadata, records=records)


def _exposure_records(*, shares_text: str, levels_text: str) -> list[dict[str, str]]:
    share_rows = list(csv.DictReader(io.StringIO(shares_text)))
    level_rows = list(csv.DictReader(io.StringIO(levels_text)))
    if not share_rows or not level_rows:
        raise ValueError("Fed DFA zip did not contain net worth share rows")
    latest_date = max(str(row["Date"]) for row in share_rows if row.get("Date"))
    latest_shares = [row for row in share_rows if row.get("Date") == latest_date]
    latest_levels = [row for row in level_rows if row.get("Date") == latest_date]
    by_category = {str(row["Category"]): row for row in latest_shares}
    levels_by_category = {str(row["Category"]): row for row in latest_levels}
    required = {"TopPt1", "RemainingTop1", "Next9", "Next40", "Bottom50"}
    missing = required - by_category.keys()
    if missing:
        raise ValueError("Fed DFA latest quarter missing categories: " + ", ".join(sorted(missing)))
    missing_levels = required - levels_by_category.keys()
    if missing_levels:
        raise ValueError("Fed DFA latest quarter missing level categories: " + ", ".join(sorted(missing_levels)))
    top10 = (
        _decimal(by_category["TopPt1"], "Debt securities")
        + _decimal(by_category["RemainingTop1"], "Debt securities")
        + _decimal(by_category["Next9"], "Debt securities")
    )
    top10_us_gov_muni = (
        _decimal(levels_by_category["TopPt1"], "U.S. government and municipal securities")
        + _decimal(levels_by_category["RemainingTop1"], "U.S. government and municipal securities")
        + _decimal(levels_by_category["Next9"], "U.S. government and municipal securities")
    )
    top10_debt_securities = (
        _decimal(levels_by_category["TopPt1"], "Debt securities")
        + _decimal(levels_by_category["RemainingTop1"], "Debt securities")
        + _decimal(levels_by_category["Next9"], "Debt securities")
    )
    top10_liabilities = (
        _decimal(levels_by_category["TopPt1"], "Liabilities")
        + _decimal(levels_by_category["RemainingTop1"], "Liabilities")
        + _decimal(levels_by_category["Next9"], "Liabilities")
    )
    return [
        {
            "as_of_date": latest_date,
            "top10_interest_bearing_asset_share": str(top10 / Decimal("100")),
            "middle40_interest_bearing_asset_share": str(
                _decimal(by_category["Next40"], "Debt securities") / Decimal("100")
            ),
            "bottom50_interest_bearing_asset_share": str(
                _decimal(by_category["Bottom50"], "Debt securities") / Decimal("100")
            ),
            "top10_liability_share": str(
                (
                    _decimal(by_category["TopPt1"], "Liabilities")
                    + _decimal(by_category["RemainingTop1"], "Liabilities")
                    + _decimal(by_category["Next9"], "Liabilities")
                )
                / Decimal("100")
            ),
            "middle40_liability_share": str(
                _decimal(by_category["Next40"], "Liabilities") / Decimal("100")
            ),
            "bottom50_liability_share": str(
                _decimal(by_category["Bottom50"], "Liabilities") / Decimal("100")
            ),
            "top10_us_government_municipal_securities_mil": str(top10_us_gov_muni),
            "middle40_us_government_municipal_securities_mil": str(
                _decimal(levels_by_category["Next40"], "U.S. government and municipal securities")
            ),
            "bottom50_us_government_municipal_securities_mil": str(
                _decimal(levels_by_category["Bottom50"], "U.S. government and municipal securities")
            ),
            "top10_debt_securities_mil": str(top10_debt_securities),
            "middle40_debt_securities_mil": str(
                _decimal(levels_by_category["Next40"], "Debt securities")
            ),
            "bottom50_debt_securities_mil": str(
                _decimal(levels_by_category["Bottom50"], "Debt securities")
            ),
            "top10_liabilities_mil": str(top10_liabilities),
            "middle40_liabilities_mil": str(
                _decimal(levels_by_category["Next40"], "Liabilities")
            ),
            "bottom50_liabilities_mil": str(
                _decimal(levels_by_category["Bottom50"], "Liabilities")
            ),
        }
    ]


def _account_type_records(*, levels_text: str) -> list[dict[str, str]]:
    level_rows = list(csv.DictReader(io.StringIO(levels_text)))
    if not level_rows:
        raise ValueError("Fed DFA zip did not contain net worth level rows")
    latest_date = max(str(row["Date"]) for row in level_rows if row.get("Date"))
    latest_levels = [row for row in level_rows if row.get("Date") == latest_date]
    levels_by_category = {str(row["Category"]): row for row in latest_levels}
    required = {"TopPt1", "RemainingTop1", "Next9", "Next40", "Bottom50"}
    missing = required - levels_by_category.keys()
    if missing:
        raise ValueError("Fed DFA latest quarter missing categories: " + ", ".join(sorted(missing)))
    categories: list[tuple[str, list[str]]] = [
        ("top_0_1", ["TopPt1"]),
        ("remaining_top_1", ["RemainingTop1"]),
        ("next_9", ["Next9"]),
        ("top_10", ["TopPt1", "RemainingTop1", "Next9"]),
        ("next_40", ["Next40"]),
        ("bottom_50", ["Bottom50"]),
    ]
    records: list[dict[str, str]] = []
    for group, source_categories in categories:
        rows = [levels_by_category[category] for category in source_categories]
        dc_pension = _sum_decimal(rows, "DC pension entitlements")
        db_pension = _sum_decimal(rows, "DB pension entitlements")
        annuities = _sum_decimal(rows, "Annuities")
        records.append(
            {
                "as_of_date": latest_date,
                "date": _quarter_date(latest_date),
                "wealth_group": group,
                "source_categories": ";".join(source_categories),
                "deposits_mil": str(_sum_decimal(rows, "Deposits")),
                "money_market_fund_shares_mil": str(
                    _sum_decimal(rows, "Money market fund shares")
                ),
                "debt_securities_mil": str(_sum_decimal(rows, "Debt securities")),
                "us_government_municipal_securities_mil": str(
                    _sum_decimal(rows, "U.S. government and municipal securities")
                ),
                "annuities_mil": str(annuities),
                "dc_pension_entitlements_mil": str(dc_pension),
                "db_pension_entitlements_mil": str(db_pension),
                "retirement_entitlements_mil": str(dc_pension + db_pension),
                "tax_deferred_or_retirement_account_context_available": "true",
                "source_specific_interest_recipient_mapping_available": "false",
                "state_tax_treatment_available": "false",
                "tax_payment_timing_available": "false",
                "current_demand_conversion_available": "false",
                "tax_clawback_gate_passed": "false",
                "demand_conversion_prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    return records


def _household_liability_records(*, levels_text: str) -> list[dict[str, str]]:
    level_rows = list(csv.DictReader(io.StringIO(levels_text)))
    if not level_rows:
        raise ValueError("Fed DFA zip did not contain net worth level rows")
    latest_date = max(str(row["Date"]) for row in level_rows if row.get("Date"))
    latest_levels = [row for row in level_rows if row.get("Date") == latest_date]
    levels_by_category = {str(row["Category"]): row for row in latest_levels}
    required = {"TopPt1", "RemainingTop1", "Next9", "Next40", "Bottom50"}
    missing = required - levels_by_category.keys()
    if missing:
        raise ValueError(
            "Fed DFA latest quarter missing categories: " + ", ".join(sorted(missing))
        )
    required_columns = {
        "Deposits",
        "Money market fund shares",
        "Liabilities",
        "Loans (Liabilities)",
        "Mortgages",
        "Home mortgages",
        "Consumer credit",
        "Depository institutions loans n.e.c.",
        "Other loans and advances (Liabilities)",
    }
    sample = levels_by_category["TopPt1"]
    missing_columns = required_columns - set(sample)
    if missing_columns:
        raise ValueError(
            "Fed DFA latest quarter missing liability columns: "
            + ", ".join(sorted(missing_columns))
        )
    categories: list[tuple[str, list[str]]] = [
        ("top_0_1", ["TopPt1"]),
        ("remaining_top_1", ["RemainingTop1"]),
        ("next_9", ["Next9"]),
        ("top_10", ["TopPt1", "RemainingTop1", "Next9"]),
        ("next_40", ["Next40"]),
        ("bottom_50", ["Bottom50"]),
    ]
    records: list[dict[str, str]] = []
    for group, source_categories in categories:
        rows = [levels_by_category[category] for category in source_categories]
        deposits = _sum_decimal(rows, "Deposits")
        mmf = _sum_decimal(rows, "Money market fund shares")
        liquid_assets_proxy = deposits + mmf
        consumer_credit = _sum_decimal(rows, "Consumer credit")
        records.append(
            {
                "as_of_date": latest_date,
                "date": _quarter_date(latest_date),
                "wealth_group": group,
                "source_categories": ";".join(source_categories),
                "liabilities_mil": str(_sum_decimal(rows, "Liabilities")),
                "loans_liabilities_mil": str(
                    _sum_decimal(rows, "Loans (Liabilities)")
                ),
                "mortgages_mil": str(_sum_decimal(rows, "Mortgages")),
                "home_mortgages_mil": str(
                    _sum_decimal(rows, "Home mortgages")
                ),
                "consumer_credit_mil": str(consumer_credit),
                "depository_institutions_loans_nec_mil": str(
                    _sum_decimal(rows, "Depository institutions loans n.e.c.")
                ),
                "other_loans_advances_liabilities_mil": str(
                    _sum_decimal(rows, "Other loans and advances (Liabilities)")
                ),
                "deposits_mil": str(deposits),
                "money_market_fund_shares_mil": str(mmf),
                "liquid_assets_proxy_mil": str(liquid_assets_proxy),
                "product_balance_context_available": "true",
                "wealth_group_distribution_context_available": "true",
                "liquid_asset_proxy_context_available": "true",
                "borrower_level_microdata_available": "false",
                "payment_behavior_context_available": "false",
                "current_demand_conversion_available": "false",
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    return records


def _sum_decimal(records: list[dict[str, str]], key: str) -> Decimal:
    return sum((_decimal(record, key) for record in records), Decimal("0"))


def _quarter_date(label: str) -> str:
    year, quarter = label.split(":Q", 1)
    month = {"1": "01", "2": "04", "3": "07", "4": "10"}[quarter]
    return f"{year}-{month}-01"


def _decimal(record: dict[str, str], key: str) -> Decimal:
    raw = record.get(key)
    if raw in (None, "", "NA"):
        raise ValueError(f"Fed DFA row missing {key}")
    return Decimal(str(raw).replace(",", ""))


def _request(url: str) -> Request:
    return Request(url, headers={"User-Agent": "Mozilla/5.0 ratewall-research"})
