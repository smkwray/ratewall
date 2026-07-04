"""Timestamped official-source demo snapshots.

Demo snapshots are deliberately small and marked as stubs. They let the
pipeline, accounting, charting, scenario, and empirical surfaces regenerate
without hardcoding live macro facts into model code.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from ratewall.sources.base import RetrievalMetadata, SourceSnapshot, utc_now_iso
from ratewall.sources.registry import SourceRegistry


DEMO_RECORDS: dict[str, list[dict[str, str]]] = {
    "WRESBAL": [
        {"date": "2021-10-06", "value": "4200000"},
        {"date": "2021-12-29", "value": "4050000"},
        {"date": "2026-04-23", "value": "3032588"},
        {"date": "2026-05-06", "value": "3032588"},
    ],
    "RRPONTSYD": [
        {"date": "2026-04-23", "value": "125000"},
        {"date": "2026-05-06", "value": "125000"},
    ],
    "GDP": [
        {"date": "2021-10-01", "value": "24700"},
        {"date": "2026-01-01", "value": "30000"},
    ],
    "FEDFUNDS": [
        {"date": "2026-01-01", "value": "4.25"},
        {"date": "2026-03-01", "value": "4.30"},
        {"date": "2026-04-01", "value": "4.35"},
    ],
    "IORB": [
        {"date": "2021-10-01", "value": "0.15"},
        {"date": "2021-12-31", "value": "0.15"},
        {"date": "2026-01-02", "value": "4.40"},
        {"date": "2026-03-31", "value": "4.40"},
        {"date": "2026-04-01", "value": "4.40"},
    ],
    "IOER": [
        {"date": "2008-10-09", "value": "0.75"},
        {"date": "2021-07-28", "value": "0.15"},
    ],
    "PII": [
        {"date": "2021-10-01", "value": "1500"},
        {"date": "2026-01-01", "value": "2050"},
        {"date": "2026-04-01", "value": "2060"},
    ],
    "NA000309Q": [
        {"date": "1960-01-01", "value": "5000"},
        {"date": "2021-10-01", "value": "120000"},
        {"date": "2026-01-01", "value": "235000"},
    ],
    "NA000310Q": [
        {"date": "1960-01-01", "value": "1000"},
        {"date": "2021-10-01", "value": "55000"},
        {"date": "2026-01-01", "value": "71000"},
    ],
    "PCEPILFE": [
        {"date": "2026-01-01", "value": "130.0"},
        {"date": "2026-04-01", "value": "131.0"},
    ],
    "INDPRO": [
        {"date": "2026-01-01", "value": "104.0"},
        {"date": "2026-04-01", "value": "104.5"},
    ],
    "UNRATE": [
        {"date": "2026-01-01", "value": "4.0"},
        {"date": "2026-04-01", "value": "4.1"},
    ],
    "TDSP": [{"date": "2026-01-01", "value": "11.2"}],
    "BUSLOANS": [{"date": "2026-05-06", "value": "2900"}],
    "TOTLL": [{"date": "2026-05-06", "value": "12600"}],
    "DPSACBW027SBOG": [{"date": "2026-05-06", "value": "18000"}],
    "SNDR": [{"date": "2026-05-04", "value": "0.41"}],
    "DTB3": [{"date": "2026-05-08", "value": "3.58"}],
    "WTREGEN": [{"date": "2026-05-06", "value": "800000"}],
    "NFCI": [{"date": "2026-05-01", "value": "-0.45"}],
    "BAMLH0A0HYM2": [{"date": "2026-05-07", "value": "3.25"}],
    "BAA": [{"date": "2026-05-01", "value": "5.80"}],
    "TREASURY_HQM_EOM_10Y_PAR": [
        {
            "date": "1984-01-31",
            "value": "12.39",
            "maturity_years": "10",
            "yield_measure": "end_of_month_par_yield",
        },
        {
            "date": "2018-12-31",
            "value": "4.29",
            "maturity_years": "10",
            "yield_measure": "end_of_month_par_yield",
        },
        {
            "date": "2026-04-30",
            "value": "5.11",
            "maturity_years": "10",
            "yield_measure": "end_of_month_par_yield",
        },
    ],
    "FDHBPIN": [{"date": "2026-01-01", "value": "17000"}],
    "FDHBFIN": [{"date": "2026-01-01", "value": "9200"}],
    "FDHBFRBN": [{"date": "2026-01-01", "value": "5000"}],
    "BOGZ1LM153061105Q": [{"date": "2026-01-01", "value": "2900"}],
    "BOGZ1FL763061100Q": [{"date": "2026-01-01", "value": "1700"}],
    "BOGZ1FL633061105Q": [{"date": "2026-01-01", "value": "2450"}],
    "BOGZ1FL653061105Q": [{"date": "2026-01-01", "value": "1600"}],
    "BOGZ1FL523061105Q": [{"date": "2026-01-01", "value": "650"}],
    "BOGZ1FL573061105Q": [{"date": "2026-01-01", "value": "540"}],
    "debt_to_penny": [
        {
            "record_date": "2026-04-28",
            "debt_held_public_amt": "31260000000000",
            "src_line_nbr": "demo_stub",
        },
        {
            "record_date": "2026-05-05",
            "debt_held_public_amt": "31260000000000",
            "src_line_nbr": "demo_stub",
        }
    ],
    "mts_table_4": [
        {
            "record_date": "2026-04-30",
            "classification_desc": "Total--Interest on the Public Debt",
            "current_fytd_net_outly_amt": "620000000000",
        }
    ],
    "treasury_mspd_table_3": [
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class1_desc": "Bills Maturity Value",
            "security_class2_desc": "demo_bill",
            "issue_date": "2026-01-30",
            "maturity_date": "2026-06-30",
            "issued_amt": "3000000",
            "redeemed_amt": "0",
            "outstanding_amt": "3000000",
            "interest_rate_pct": "0",
        },
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class1_desc": "Notes",
            "security_class2_desc": "demo_note",
            "issue_date": "2024-04-30",
            "maturity_date": "2028-04-30",
            "issued_amt": "6000000",
            "redeemed_amt": "0",
            "outstanding_amt": "6000000",
            "interest_rate_pct": "4.00",
            "interest_pay_date_1": "04/30",
            "interest_pay_date_2": "10/31",
            "inflation_adj_amt": "0",
        },
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class1_desc": "Bonds",
            "security_class2_desc": "demo_bond",
            "issue_date": "2016-04-30",
            "maturity_date": "2036-04-30",
            "issued_amt": "10000000",
            "redeemed_amt": "0",
            "outstanding_amt": "10000000",
            "interest_rate_pct": "4.50",
            "interest_pay_date_1": "04/30",
            "interest_pay_date_2": "10/31",
            "inflation_adj_amt": "0",
        },
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class1_desc": "Floating Rate Notes",
            "security_class2_desc": "demo_frn",
            "issue_date": "2026-04-30",
            "maturity_date": "2028-04-30",
            "issued_amt": "1000000",
            "redeemed_amt": "0",
            "outstanding_amt": "1000000",
            "interest_rate_pct": "4.37",
            "interest_pay_date_1": "01/31",
            "interest_pay_date_2": "04/30",
            "interest_pay_date_3": "07/31",
            "interest_pay_date_4": "10/31",
            "inflation_adj_amt": "0",
        },
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class1_desc": "Treasury Inflation-Protected Securities",
            "security_class2_desc": "demo_tips",
            "issue_date": "2026-04-30",
            "maturity_date": "2031-04-15",
            "issued_amt": "1500000",
            "redeemed_amt": "0",
            "outstanding_amt": "1500000",
            "interest_rate_pct": "1.75",
            "interest_pay_date_1": "04/15",
            "interest_pay_date_2": "10/15",
            "inflation_adj_amt": "25000",
        },
    ],
    "treasury_mspd_table_1": [
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class_desc": "Bills",
            "debt_held_public_mil_amt": "3000000",
            "intragov_hold_mil_amt": "0",
            "total_mil_amt": "3000000",
        },
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class_desc": "Notes",
            "debt_held_public_mil_amt": "6000000",
            "intragov_hold_mil_amt": "0",
            "total_mil_amt": "6000000",
        },
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class_desc": "Bonds",
            "debt_held_public_mil_amt": "10000000",
            "intragov_hold_mil_amt": "0",
            "total_mil_amt": "10000000",
        },
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class_desc": "Floating Rate Notes",
            "debt_held_public_mil_amt": "1000000",
            "intragov_hold_mil_amt": "0",
            "total_mil_amt": "1000000",
        },
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class_desc": "Treasury Inflation-Protected Securities",
            "debt_held_public_mil_amt": "1500000",
            "intragov_hold_mil_amt": "0",
            "total_mil_amt": "1500000",
        },
        {
            "record_date": "2026-04-30",
            "security_type_desc": "Marketable",
            "security_class_desc": "Total Marketable",
            "debt_held_public_mil_amt": "21500000",
            "intragov_hold_mil_amt": "0",
            "total_mil_amt": "21500000",
        },
    ],
    "treasury_buybacks": [
        {
            "operationStatus": "Results",
            "operationStartDTM": "2026-05-07T17:40:00Z",
            "operationCloseDTM": "2026-05-07T18:00:00Z",
            "settlementDT": "2026-05-08",
            "operationType": "Liquidity Support",
            "securityType": "Nominal Coupons",
            "maturityBucket": "1Mo to 2Y",
            "totalParAmountAccepted": "100000000",
            "totalParAmountOffered": "200000000",
            "maxParAmountRedeemed": "4000000000",
            "numberIssuesAccepted": "1",
            "numberIssuesEligible": "1",
            "securityDetails": [
                {
                    "cusipNumber": "demo_note",
                    "maturityDate": "2028-04-30",
                    "couponRate": "4.00",
                    "weightedAverageAcceptedPrice": "100.125",
                    "parAmountAccepted": "100000000",
                }
            ],
        }
    ],
    "treasury_auction_frn_terms": [
        {
            "record_date": "2026-04-30",
            "cusip": "demo_frn",
            "security_type": "Note",
            "security_term": "2-Year",
            "auction_date": "2026-04-22",
            "issue_date": "2026-04-30",
            "maturity_date": "2028-04-30",
            "floating_rate": "Yes",
            "frn_index_determination_date": "2026-04-28",
            "frn_index_determination_rate": "4.250",
            "spread": "0.120",
            "high_discnt_margin": "0.120",
            "int_payment_frequency": "Quarterly",
        }
    ],
    "treasury_auction_tips_terms": [
        {
            "record_date": "2026-04-30",
            "cusip": "demo_tips",
            "security_type": "Note",
            "security_term": "5-Year",
            "auction_date": "2026-04-23",
            "issue_date": "2026-04-30",
            "maturity_date": "2031-04-15",
            "inflation_index_security": "Yes",
            "index_ratio_on_issue_date": "1.002350",
            "ref_cpi_on_dated_date": "325.967400",
            "ref_cpi_on_issue_date": "326.733900",
            "cpi_base_reference_period": "1982-1984=100",
            "int_payment_frequency": "Semi-Annual",
        }
    ],
    "treasury_frn_daily_indexes": [
        {
            "record_date": "2026-05-08",
            "frn": "2-Year",
            "cusip": "demo_frn",
            "original_dated_date": "2026-04-30",
            "original_issue_date": "2026-04-30",
            "maturity_date": "2028-04-30",
            "spread": "0.120",
            "start_of_accrual_period": "2026-04-30",
            "end_of_accrual_period": "2026-07-31",
            "daily_index": "4.250",
            "daily_int_accrual_rate": "0.00012139",
            "daily_accrued_int_per100": "0.012139",
            "accr_int_per100_pmt_period": "0.097112",
        }
    ],
    "treasury_tips_cpi_detail": [
        {
            "cusip": "demo_tips",
            "original_issue_date": "2026-04-30",
            "index_date": "2026-05-08",
            "ref_cpi": "326.90000",
            "index_ratio": "1.002860",
            "pdf_link": "https://fiscaldata.treasury.gov/datasets/tips-cpi-data/",
            "xml_link": "https://fiscaldata.treasury.gov/datasets/tips-cpi-data/",
        }
    ],
    "tic_treasury_sector_transactions": [
        {
            "month": "2023-01",
            "total_net_foreign_purchases_mil": "12345",
            "foreign_official_institutions_mil": "4567",
            "other_foreigners_mil": "7788",
            "international_regional_organizations_mil": "-10",
            "scope_note": (
                "TIC tressect reports net purchases of Treasury bonds and notes "
                "by foreign sector; it is a transaction split, not a stock-holder split."
            ),
        }
    ],
    "tic_foreign_treasury_stock_split": [
        {
            "component": "total_treasury_securities",
            "as_of_quarter": "December 2025",
            "all_foreign_holders_mil": "9270975",
            "foreign_official_holders_mil": "3886999",
            "other_foreign_holders_mil": "5383976",
            "official_share": "0.419267",
            "other_share": "0.580733",
            "source_note": "Demo row shaped like TIC total-liabilities Treasury stock split.",
        },
        {
            "component": "long_term_treasury_securities",
            "as_of_quarter": "December 2025",
            "all_foreign_holders_mil": "7823349",
            "foreign_official_holders_mil": "3498522",
            "other_foreign_holders_mil": "4324827",
            "official_share": "0.447185",
            "other_share": "0.552815",
            "source_note": "Demo row shaped like TIC total-liabilities Treasury stock split.",
        },
        {
            "component": "short_term_treasury_securities",
            "as_of_quarter": "December 2025",
            "all_foreign_holders_mil": "1447626",
            "foreign_official_holders_mil": "388477",
            "other_foreign_holders_mil": "1059149",
            "official_share": "0.268363",
            "other_share": "0.731637",
            "source_note": "Demo row shaped like TIC total-liabilities Treasury stock split.",
        },
    ],
    "ofr_mmf_treasury_holdings": [
        {
            "mnemonic": "MMF-MMF_TOT-M",
            "channel": "total_investments",
            "date": "2026-03-31",
            "value": "7100000000000",
            "short_name": "MMF total investments",
            "long_name": "Money Market Mutual Fund Investments: Total",
            "unit": "USD",
            "frequency": "Monthly",
        },
        {
            "mnemonic": "MMF-MMF_T_TOT-M",
            "channel": "us_treasury_securities",
            "date": "2026-03-31",
            "value": "2800000000000",
            "short_name": "MMF Treasury securities",
            "long_name": "Money Market Mutual Fund Investments in U.S. Treasury Securities",
            "unit": "USD",
            "frequency": "Monthly",
        },
        {
            "mnemonic": "MMF-MMF_RP_T_TOT-M",
            "channel": "treasury_repo_total",
            "date": "2026-03-31",
            "value": "1500000000000",
            "short_name": "MMF Treasury repo",
            "long_name": (
                "Money Market Mutual Fund Investments in Repurchase Agreements "
                "Backed by U.S. Treasury Securities: Total"
            ),
            "unit": "USD",
            "frequency": "Monthly",
        },
    ],
    "sec_nmfp_mmf_treasury_cusip_holdings": [
        {
            "record_type": "aggregate",
            "period_role": "latest",
            "channel": "direct_security",
            "security_bucket": "total",
            "report_date": "2026-04-07",
            "value": "2750000000000",
            "value_bil": "2750",
            "cusip": "",
            "issuer": "",
            "title": "",
            "maturity_date": "",
            "series_name": "",
            "source_note": "Demo SEC N-MFP aggregate direct Treasury holding row.",
        },
        {
            "record_type": "aggregate",
            "period_role": "latest",
            "channel": "repo_collateral",
            "security_bucket": "total",
            "report_date": "2026-04-07",
            "value": "1480000000000",
            "value_bil": "1480",
            "cusip": "",
            "issuer": "",
            "title": "",
            "maturity_date": "",
            "series_name": "",
            "source_note": "Demo SEC N-MFP aggregate Treasury repo collateral row.",
        },
        {
            "record_type": "cusip",
            "period_role": "latest",
            "channel": "direct_security",
            "security_bucket": "frn",
            "report_date": "2026-04-07",
            "value": "12000000000",
            "value_bil": "12",
            "cusip": "demo_frn",
            "issuer": "United States Treasury",
            "title": "Floating Rate Note",
            "maturity_date": "2028-04-30",
            "series_name": "Demo Government Money Market Fund",
            "source_note": "Demo SEC N-MFP CUSIP row for downstream matching.",
        },
        {
            "record_type": "cusip",
            "period_role": "latest",
            "channel": "direct_security",
            "security_bucket": "tips",
            "report_date": "2026-04-07",
            "value": "7000000000",
            "value_bil": "7",
            "cusip": "demo_tips",
            "issuer": "United States Treasury",
            "title": "Treasury Inflation-Protected Security",
            "maturity_date": "2031-04-15",
            "series_name": "Demo Government Money Market Fund",
            "source_note": "Demo SEC N-MFP CUSIP row for downstream matching.",
        },
        {
            "record_type": "aggregate",
            "period_role": "historical",
            "channel": "direct_security",
            "security_bucket": "total",
            "report_date": "2026-03-07",
            "value": "2680000000000",
            "value_bil": "2680",
            "cusip": "",
            "issuer": "",
            "title": "",
            "maturity_date": "",
            "series_name": "",
            "source_note": "Demo SEC N-MFP prior-month aggregate row.",
        },
        {
            "record_type": "aggregate",
            "period_role": "historical",
            "channel": "repo_collateral",
            "security_bucket": "total",
            "report_date": "2026-03-07",
            "value": "1420000000000",
            "value_bil": "1420",
            "cusip": "",
            "issuer": "",
            "title": "",
            "maturity_date": "",
            "series_name": "",
            "source_note": "Demo SEC N-MFP prior-month aggregate row.",
        },
    ],
    "cbo_budget_economic_outlook": [
        {
            "publication_date": "2026-01-01",
            "title": "Budget and Economic Outlook",
            "deficit_2026_gdp_share": "0.058",
            "net_interest_2026_gdp_share": "0.033",
            "net_interest_2036_gdp_share": "0.046",
        },
        {
            "record_type": "cbo_projection",
            "release_date": "2026-02",
            "source_file": "demo_cbo_budget_projection.xlsx",
            "source_table": "Table 1-1",
            "source_row_label": "Net interest",
            "metric": "net_interest_gdp_pct",
            "fiscal_year": "2036",
            "value": "4.6",
            "units": "percent_of_gdp",
        },
        {
            "record_type": "cbo_projection",
            "release_date": "2026-02",
            "source_file": "demo_cbo_budget_projection.xlsx",
            "source_table": "Table 1-1",
            "source_row_label": "Debt held by the public",
            "metric": "debt_held_public_gdp_pct",
            "fiscal_year": "2036",
            "value": "120.0",
            "units": "percent_of_gdp",
        },
        {
            "record_type": "cbo_projection",
            "release_date": "2026-02",
            "source_file": "demo_cbo_budget_projection.xlsx",
            "source_table": "Table 1-1",
            "source_row_label": "Total deficit (-)",
            "metric": "deficit_gdp_pct",
            "fiscal_year": "2036",
            "value": "-6.7",
            "units": "percent_of_gdp",
        },
        {
            "record_type": "cbo_projection",
            "release_date": "2026-02",
            "source_file": "demo_cbo_budget_projection.xlsx",
            "source_table": "Table 1-3",
            "source_row_label": "Average interest rate on debt held by the public (percent)",
            "metric": "average_interest_rate_debt_public_pct",
            "fiscal_year": "2036",
            "value": "3.9",
            "units": "percent",
        }
    ],
    "h41_current": [
        {
            "release_date": "2026-05-07",
            "deferred_asset_amt": "210000",
            "remittances_to_treasury_amt": "0",
        }
    ],
    "treasury_repricing_anchor": [
        {
            "as_of_date": "2026-05-05",
            "matures_within_12m_share": "0.33",
            "average_maturity_months": "70",
            "one_quarter_share": "0.12",
            "three_year_share": "0.58",
            "ten_year_share": "1.00",
        }
    ],
    "nyfed_soma_summary": [
        {
            "as_of_date": "2026-05-07",
            "summary": "demo_stub",
            "soma_treasury_holdings_amt": "4300000000000",
        }
    ],
    "nyfed_sofr": [{"effectiveDate": "2026-05-07", "percentRate": "3.62"}],
    "distributional_interest_exposure": [
        {
            "as_of_date": "2026-01-01",
            "top10_interest_bearing_asset_share": "0.62",
            "bottom50_interest_bearing_asset_share": "0.04",
            "middle40_interest_bearing_asset_share": "0.34",
            "top10_liability_share": "0.25",
            "middle40_liability_share": "0.44",
            "bottom50_liability_share": "0.31",
            "top10_us_government_municipal_securities_mil": "900000",
            "middle40_us_government_municipal_securities_mil": "240000",
            "bottom50_us_government_municipal_securities_mil": "30000",
            "top10_debt_securities_mil": "1200000",
            "middle40_debt_securities_mil": "350000",
            "bottom50_debt_securities_mil": "50000",
            "top10_liabilities_mil": "2500000",
            "middle40_liabilities_mil": "4400000",
            "bottom50_liabilities_mil": "3100000",
        }
    ],
    "sf_fed_monetary_policy_surprises": [
        {
            "date": "2026-04-29",
            "raw_surprise_bps": "2.0",
            "orthogonalized_surprise_bps": "1.1",
        }
    ],
    "fed_brw_monetary_policy_shocks": [
        {
            "month": "1994-01-01",
            "monthly_shock_pctpt": "0",
            "fomc_date": "1994-02-04",
            "fomc_shock_pctpt": "0.1048625",
            "source_variant": "updated_2021_03_04",
        },
        {
            "month": "1994-02-01",
            "monthly_shock_pctpt": "0.1048625",
            "fomc_date": "1994-03-22",
            "fomc_shock_pctpt": "-0.0243272",
            "source_variant": "updated_2021_03_04",
        },
        {
            "month": "1994-03-01",
            "monthly_shock_pctpt": "-0.0243272",
            "fomc_date": "1994-05-17",
            "fomc_shock_pctpt": "-0.0110494",
            "source_variant": "updated_2021_03_04",
        },
    ],
    "romer_romer_2004": [
        {
            "date": "1994-01-01",
            "shock_bps": "0.0",
            "source_variant": "demo_converted_monthly_narrative_shock",
        },
        {
            "date": "1994-02-01",
            "shock_bps": "10.48625",
            "source_variant": "demo_converted_monthly_narrative_shock",
        },
        {
            "date": "1994-03-01",
            "shock_bps": "-2.43272",
            "source_variant": "demo_converted_monthly_narrative_shock",
        },
    ],
}


def build_demo_snapshots(
    registry: SourceRegistry,
    *,
    clock: Callable[[], datetime] | None = None,
) -> list[SourceSnapshot]:
    retrieved_at = utc_now_iso(clock)
    snapshots: list[SourceSnapshot] = []
    for series_id, records in DEMO_RECORDS.items():
        spec = registry.series_definition(series_id)
        release_date = _release_date(records[0])
        snapshots.append(
            SourceSnapshot(
                metadata=RetrievalMetadata(
                    source_id=spec.source,
                    series_id=series_id,
                    source_url=spec.endpoint,
                    units=spec.units,
                    frequency=spec.frequency,
                    transform=spec.transform,
                    retrieved_at=retrieved_at,
                    source_release_at=release_date,
                    snapshot_kind="demo_stub",
                    note="Pipeline fixture using an official source URL; not a live estimate.",
                ),
                records=records,
            )
        )
    return snapshots


def fallback_snapshot(
    registry: SourceRegistry,
    series_id: str,
    *,
    reason: str,
    clock: Callable[[], datetime] | None = None,
) -> SourceSnapshot:
    """Return a clearly marked fallback snapshot for a failed live parser."""

    demo = next(
        snapshot
        for snapshot in build_demo_snapshots(registry, clock=clock)
        if snapshot.metadata.series_id == series_id
    )
    return SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id=demo.metadata.source_id,
            series_id=demo.metadata.series_id,
            source_url=demo.metadata.source_url,
            units=demo.metadata.units,
            frequency=demo.metadata.frequency,
            transform=demo.metadata.transform,
            retrieved_at=demo.metadata.retrieved_at,
            source_release_at=demo.metadata.source_release_at,
            snapshot_kind="fallback_stub",
            note=f"Live parser fallback: {reason}",
        ),
        records=demo.records,
    )


def _release_date(record: dict[str, str]) -> str | None:
    for key in (
        "date",
        "record_date",
        "release_date",
        "as_of_date",
        "effectiveDate",
        "operationStartDTM",
        "report_date",
        "index_date",
        "as_of_quarter",
    ):
        if key in record:
            return record[key]
    return None
