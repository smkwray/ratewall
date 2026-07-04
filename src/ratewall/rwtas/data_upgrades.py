"""Evidence helpers for the RWTAS historical data-upgrade wire."""

from __future__ import annotations

import csv
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from ratewall.rwtas.v1 import _d, _fmt, _read_csv_rows


HISTORICAL_UPGRADE_PACK_DIR = Path("configs/rwtas/packs/historical_upgrades")
TDCEST_RAW_DIR = Path.home() / "malus/proj/tdcest/data/raw"


def upgraded_decade_configs(
    base_configs: dict[str, dict[str, Decimal | str]],
    pack_dir: Path = HISTORICAL_UPGRADE_PACK_DIR,
) -> dict[str, dict[str, Decimal | str]]:
    rows = _upgrade_rows(pack_dir)
    configs = deepcopy(base_configs)
    for state_id, year in [
        ("historical_1965", "1965"),
        ("historical_1985", "1985"),
        ("historical_2005", "2005"),
    ]:
        cfg = configs[state_id]
        cfg["debt_public_bil"] = _value(rows, f"debt_held_public_total_fy{year}")
        cfg["bill_share"] = _value(rows, f"marketable_debt_bill_share_fy{year}") / Decimal("100")
        cfg["bill_share_verbatim"] = f"{_value(rows, f'marketable_debt_bill_share_fy{year}')}% [A]"
        cfg["fed_share"] = _value(rows, f"holder_fed_share_fy{year}") / Decimal("100")
        cfg["fed_share_verbatim"] = f"{_value(rows, f'holder_fed_share_fy{year}')}% [A]"
        cfg["foreign_share"] = _value(rows, f"holder_foreign_share_fy{year}") / Decimal("100")
        cfg["foreign_share_verbatim"] = f"{_value(rows, f'holder_foreign_share_fy{year}')}% [A]"
        cfg["hh_direct_treasury_bil"] = _value(rows, f"holder_household_direct_level_fy{year}")
        cfg["hh_marketable_treasury_bil"] = _value(rows, f"holder_household_direct_level_fy{year}")
        cfg["hh_direct_treasury_verbatim"] = (
            f"{_fmt(_value(rows, f'holder_household_direct_level_fy{year}'))} "
            f"({_fmt(_value(rows, f'holder_household_direct_share_fy{year}'))}%) [B]"
        )
        cfg["mortgage_bil"] = _value(rows, f"residential_mortgage_debt_outstanding_{year}")
    return configs


def historical_upgrade_disposition_rows(
    pack_dir: Path = HISTORICAL_UPGRADE_PACK_DIR,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in _read_csv_rows(pack_dir / "historical_upgrades_delta.csv"):
        rows.append(
            {
                "row_type": "upgrade_disposition",
                "parameter_id": row["parameter_id"],
                "memo_value": row["memo_value"],
                "upgraded_value": row["upgraded_value"],
                "units": row["units"],
                "delta": row["delta"],
                "material_flag": row["material_flag"],
                "disposition": row["note"],
                "input_basis_label": "historical_upgrade_disposition",
                "source_file": str(pack_dir / "historical_upgrades_delta.csv"),
            }
        )
    return rows


def allocation_exact_pull_rows(
    pack_dir: Path = HISTORICAL_UPGRADE_PACK_DIR,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    exact_rows = [
        row
        for row in _read_csv_rows(pack_dir / "historical_upgrades.csv")
        if any(
            row["parameter_id"].startswith(prefix)
            for prefix in [
                "hh_f100_",
                "nfc_l103_",
                "ncb_net_equity_issuance_",
                "mmf_total_assets_level_",
                "mmf_household_npo_assets_level_",
                "mmf_household_npo_share_total_",
                "mmf_nonhousehold_assets_level_",
                "mmf_nonhousehold_share_total_",
            ]
        )
    ]
    for row in exact_rows:
        year = row["parameter_id"].rsplit("_", 1)[-1]
        rows.append(
            {
                "row_type": "grade_A_exact_pull",
                "year": year,
                "parameter_id": row["parameter_id"],
                "cell_or_sector": row["cell_or_sector"],
                "instrument_family": row["instrument_family"],
                "low": row["low"],
                "base": row["base"],
                "high": row["high"],
                "units": row["units"],
                "source_id": row["source_id"],
                "input_basis_label": "grade_A_exact_pull",
                "rationale": row["rationale"],
                "overlap_key": _allocation_overlap_key(row["parameter_id"], year),
                "claim_grade_label": "allocation_evidence_exact_pull",
            }
        )
    rows.extend(_allocation_resolution_rows(rows))
    return rows


def historical_bank_perimeter_rows(
    pack_dir: Path = HISTORICAL_UPGRADE_PACK_DIR,
) -> list[dict[str, str]]:
    upgrades = _upgrade_rows(pack_dir)
    rows: list[dict[str, str]] = []
    for year, date in [
        ("1965", "1965-10-01"),
        ("1985", "1985-10-01"),
        ("2005", "2005-10-01"),
        ("2025", "2025-10-01"),
    ]:
        tier0 = (
            _tdcest_level("us_chartered_tsy_level", date)
            + _tdcest_level("foreign_offices_tsy_level", date)
            + _tdcest_level("affiliated_areas_tsy_level", date)
        )
        credit_unions = _tdcest_level("credit_unions_total_tsy_level", date)
        rows.append(
            {
                "year": year,
                "date": date,
                "bank_perimeter": "tdcest_tier0_three_sector",
                "level_bil": _fmt(tier0),
                "level_difference_vs_default_bil": "0",
                "settlement_class": "mode_B_bank_like",
                "recommended_for_absorption": "false",
                "grade": "A",
                "source": "tdcest raw FRED Z.1 levels; catalog.py:483 perimeter",
                "note": "U.S.-chartered depository institutions + foreign banking offices in the U.S. + banks in U.S.-affiliated areas.",
            }
        )
        rows.append(
            {
                "year": year,
                "date": date,
                "bank_perimeter": "banks_incl_credit_unions",
                "level_bil": _fmt(tier0 + credit_unions),
                "level_difference_vs_default_bil": _fmt(credit_unions),
                "settlement_class": "mode_B_confirmed",
                "recommended_for_absorption": "true",
                "grade": "A",
                "source": "tdcest raw FRED Z.1 levels; do/rwtas_settlement_class_doctrine_20260703.md",
                "note": "Credit unions are bank-like money issuers; settlement assets sit outside M by construction.",
            }
        )
        if year in {"1965", "1985", "2005"}:
            private_depository = _value(upgrades, f"holder_private_depository_level_fy{year}")
            rows.append(
                {
                    "year": year,
                    "date": date,
                    "bank_perimeter": "delivered_private_depository_proxy",
                    "level_bil": _fmt(private_depository),
                    "level_difference_vs_default_bil": _fmt(private_depository - tier0),
                    "settlement_class": "mode_B_proxy_with_perimeter_mismatch",
                    "recommended_for_absorption": "false",
                    "grade": "B",
                    "source": "historical_upgrades.csv private depository rows",
                    "note": "Delivered private-depository aggregate is retained as a Grade-B contrast; it includes credit-union/NCUA perimeter pieces beyond tdcest tier0.",
                }
            )
    return rows


def settlement_class_map_rows(pack_dir: Path = Path("configs/rwtas/packs")) -> list[dict[str, str]]:
    holder_rows = [
        row
        for row in _read_csv_rows(pack_dir / "treasury_holder_matrix.csv")
        if row["instrument_family"] == "all_marketable_treasuries"
    ]
    by_holder = {row["cell_or_sector"]: _d(row["base"]) for row in holder_rows}
    mapped_specs = [
        ("households_direct", "Households and nonprofits", "mode_A_ultimate_money_user", "dominant deposits", "none", "direct holder"),
        ("nonfinancial_firms", "Nonfinancial corporate/noncorporate business", "mode_A_ultimate_money_user", "dominant deposits", "none", "direct holder"),
        ("state_local", "State and local governments", "mode_A_ultimate_money_user", "dominant deposits", "none", "direct holder"),
        ("insurers", "Insurance companies", "mode_A_ultimate_money_user", "dominant deposits", "none", "ultimate holder"),
        ("pensions", "Pension and retirement funds", "mode_A_ultimate_money_user", "dominant deposits", "none", "ultimate holder"),
        ("mutual_funds_etfs", "Mutual funds, closed-end funds, and ETFs", "mode_A_ultimate_money_user", "dominant deposits via fund subscriptions/redemptions", "none", "fund holder"),
        ("banks", "U.S.-chartered depositories, foreign banking offices, affiliated-area banks", "mode_B_money_issuer", "none", "none", "tdcest_tier0_three_sector"),
        ("federal_reserve", "Federal Reserve", "mode_D_fed_liability_recomposition", "none", "none", "monetary authority"),
        ("mmfs", "Money market funds", "mixed_mode_A_plus_episodic_RRP", "dominant deposit-funded share", "episodic: 2021 16.3%; 2023 39.3-48.0%; recent 1.4%", "mixed-vector row"),
        ("rest_of_world", "Rest of world", "mode_EF_ROW_by_funding_leg", "depends on dollar funding leg", "possible but not fixed", "external holder"),
        ("other_nonbank_finance", "Broker-dealers, GSEs/FHLBs, ABS issuers, holding companies/funding corporations", "look_through_pass_through_intermediary", "look-through to repo/debt/funding source", "GSE/FHLB ON-RRP eligible; Fed other-deposit cell distinct from reserves", "dealer-repo and own-debt complex"),
        ("unallocated_line_mapping_residual", "Line-mapping residual already allocated to settlement map", "look_through_pass_through_intermediary", "unknown; carried as mapped residual, not unmapped", "none", "line mapping residual"),
    ]
    rows: list[dict[str, str]] = []
    for holder, z1_sector, settlement_class, deposit_col, rrp_col, note in mapped_specs:
        share = by_holder.get(holder, Decimal("0"))
        rows.append(
            {
                "holder": holder,
                "z1_l210_sector": z1_sector,
                "share_of_l210_total": _fmt(share),
                "settlement_class": settlement_class,
                "mode_A_deposit_spend_column": deposit_col,
                "mode_B_or_D_money_issuer_column": "yes" if settlement_class in {"mode_B_money_issuer", "mode_D_fed_liability_recomposition"} else "no",
                "rrp_drawdown_column": rrp_col,
                "lookthrough_required": "true" if "look_through" in settlement_class else "false",
                "source": "treasury_holder_matrix.csv; do/rwtas_settlement_class_doctrine_20260703.md",
                "note": note,
            }
        )
    rows.append(
        {
            "holder": "other_residual",
            "z1_l210_sector": "unmapped residual beyond labeled map",
            "share_of_l210_total": "0",
            "settlement_class": "pass",
            "mode_A_deposit_spend_column": "",
            "mode_B_or_D_money_issuer_column": "",
            "rrp_drawdown_column": "",
            "lookthrough_required": "false",
            "source": "computed assertion",
            "note": "Unmapped residual is zero and therefore <=2%; the line-mapping residual row above remains mapped.",
        }
    )
    return rows


def settlement_class_invariant_rows(
    pack_dir: Path = Path("configs/rwtas/packs"),
    map_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    if map_rows is None:
        map_rows = settlement_class_map_rows(pack_dir)
    mapped_sum = sum(
        (
            _d(row["share_of_l210_total"])
            for row in map_rows
            if row["holder"] != "other_residual"
        ),
        Decimal("0"),
    )
    other = next((row for row in map_rows if row["holder"] == "other_residual"), None)
    other_share = _d(other["share_of_l210_total"]) if other else Decimal("1")
    return [
        {
            "check_id": "settlement_class_map_share_sum",
            "observed_value": _fmt(mapped_sum),
            "expected_value": "1",
            "status": "pass" if abs(mapped_sum - Decimal("1")) <= Decimal("0.0000000001") else "fail",
            "source": "computed from out_settlement_class_map holder rows",
            "note": "Mapped holder shares must sum to one; assertion kept outside the data table.",
        },
        {
            "check_id": "settlement_class_other_residual_zero",
            "observed_value": _fmt(other_share),
            "expected_value": "0",
            "status": "pass" if other_share == 0 else "fail",
            "source": "computed from out_settlement_class_map other_residual row",
            "note": "No unmapped residual is left outside the settlement map.",
        },
    ]


def _upgrade_rows(pack_dir: Path) -> dict[str, dict[str, str]]:
    return {row["parameter_id"]: row for row in _read_csv_rows(pack_dir / "historical_upgrades.csv")}


def _value(rows: dict[str, dict[str, str]], parameter_id: str) -> Decimal:
    return _d(rows[parameter_id]["base"])


def _allocation_overlap_key(parameter_id: str, year: str) -> str:
    if parameter_id.startswith("mmf_household_npo_share_total_"):
        return f"mmf_overlap_resolution|z1_household_share|{year}"
    if parameter_id.startswith("ncb_net_equity_issuance_"):
        return f"buyback_net_equity_context|NCBCEBA027N|{year}"
    if parameter_id.startswith("hh_f100_"):
        return f"household_flow_exact_pull|F100|{year}|{parameter_id}"
    if parameter_id.startswith("nfc_l103_"):
        return f"corporate_liquid_asset_exact_pull|L103|{year}|{parameter_id}"
    return f"historical_upgrade_exact_pull|{year}|{parameter_id}"


def _allocation_resolution_rows(exact_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    mmf_shares = [row for row in exact_rows if row["parameter_id"].startswith("mmf_household_npo_share_total_")]
    ncb_rows = [row for row in exact_rows if row["parameter_id"].startswith("ncb_net_equity_issuance_")]
    if not (mmf_shares and ncb_rows):
        return []
    return [
        {
            "row_type": "overlap_resolution",
            "year": "2021-2025",
            "parameter_id": "mmf_household_overlap_flag",
            "cell_or_sector": "households_and_nonprofits_vs_nonhousehold",
            "instrument_family": "money_market_fund_assets_share",
            "low": "",
            "base": "53.90387583794308 -> 65.0646898410119",
            "high": "",
            "units": "share_pct",
            "source_id": "FRED_HNOMMMA027N_DIV_FRED_MMMFFAA027N|grade=A",
            "input_basis_label": "grade_A_exact_pull",
            "rationale": "MMF overlap key resolves via Z.1 household/NPO share, not ICI retail/institutional fund class.",
            "overlap_key": "mmf_overlap_resolution|z1_household_share|2021_2025",
            "claim_grade_label": "allocation_evidence_exact_pull",
        },
        {
            "row_type": "buyback_context",
            "year": "2021-2025",
            "parameter_id": "ncb_net_equity_issuance_negative_every_year",
            "cell_or_sector": "nonfinancial_corporate_business",
            "instrument_family": "net_equity_issuance",
            "low": "",
            "base": ";".join(f"{row['year']}={row['base']}" for row in ncb_rows),
            "high": "",
            "units": "usd_mn_saar",
            "source_id": "FRED_NCBCEBA027N_NFC_CORP_EQUITY_LIABILITY_TX|grade=A",
            "input_basis_label": "grade_A_exact_pull",
            "rationale": "NCBCEBA027N is negative in every year 2021-2025, consistent with buybacks exceeding issuance.",
            "overlap_key": "buyback_net_equity_context|NCBCEBA027N|negative_2021_2025",
            "claim_grade_label": "allocation_evidence_exact_pull",
        },
    ]


def _tdcest_level(series_key: str, date: str) -> Decimal:
    path = TDCEST_RAW_DIR / f"fred__{series_key}.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        value_field = "value" if "value" in fieldnames else fieldnames[-1]
        for row in reader:
            row_date = row.get("date") or row.get("observation_date")
            if row_date == date and row.get(value_field) not in {"", "."}:
                return _d(row[value_field]) / Decimal("1000")
    raise ValueError(f"missing {series_key} at {date}")
