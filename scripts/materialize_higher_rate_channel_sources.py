"""Materialize higher-rate channel source-context snapshots."""

from __future__ import annotations

import argparse
import csv
import html
import hashlib
import io
import json
import math
import re
import struct
import subprocess
import urllib.error
import urllib.request
import zipfile
from array import array
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Mapping, Sequence
from xml.etree import ElementTree as ET

from ratewall.data.snapshots import read_snapshot_bundle, write_snapshot_bundle
from ratewall.sources.base import RetrievalMetadata, SourceSnapshot, utc_now_iso
from ratewall.sources.fed_dfa import FedDfaAdapter
from ratewall.sources.fred import FredAdapter
from ratewall.sources.registry import SourceRegistry


SOURCE_ADMISSION_USER_AGENT = (
    "ratewall research source-admission shanewray@example.invalid"
)

HIGHER_RATE_FRED_SERIES: Mapping[str, str] = {
    "TOTALSL": "fast_repricing_consumer_credit_context_only",
    "REVOLSL": "fast_repricing_consumer_credit_context_only",
    "NONREVSL": "fast_repricing_consumer_credit_context_only",
    "TERMCBCCALLNS": "fast_repricing_consumer_credit_context_only",
    "CDSP": "fast_repricing_consumer_credit_payment_burden_context_only",
    "DRCCLACBS": "fast_repricing_consumer_credit_delinquency_context_only",
    "DRCLACBS": "fast_repricing_consumer_credit_delinquency_context_only",
    "CREACBM027NBOG": "cre_refinancing_bank_exposure_context_only",
    "DRCRELEXFACBS": "cre_refinancing_delinquency_context_only",
    "CORCREXFACBS": "cre_refinancing_chargeoff_context_only",
    "BOGZ1FL673065505Q": "cre_cmbs_abs_population_denominator_context_only",
    "ASCMA": "cre_total_commercial_mortgage_population_denominator_context_only",
    "TLNRESCONS": "cre_nonresidential_construction_real_activity_context_only",
    "PNRESCONS": "cre_private_nonresidential_construction_context_only",
    "PBNRESCONS": "cre_public_nonresidential_construction_context_only",
    "PLODGCONS": "cre_private_lodging_construction_context_only",
    "PROFCONS": "cre_private_office_construction_context_only",
    "PRCOMCONS": "cre_private_commercial_construction_context_only",
    "PRHLTHCONS": "cre_private_health_care_construction_context_only",
    "PREDUCONS": "cre_private_educational_construction_context_only",
    "PRAMUSCONS": "cre_private_amusement_recreation_construction_context_only",
    "PRMFGCONS": "cre_private_manufacturing_construction_context_only",
    "MORTGAGE30US": "mortgage_lockin_rate_context_only",
    "B112RC1Q027SBEA": "state_local_cash_interest_receipts_context_only",
}

CRE_PROPERTY_CONSTRUCTION_SERIES: Mapping[str, tuple[str, str]] = {
    "PNRESCONS": ("private_nonresidential_total", "private_total"),
    "PBNRESCONS": ("public_nonresidential_total", "public_total"),
    "PLODGCONS": ("private_lodging", "property_type"),
    "PROFCONS": ("private_office", "property_type"),
    "PRCOMCONS": ("private_commercial", "property_type"),
    "PRHLTHCONS": ("private_health_care", "property_type"),
    "PREDUCONS": ("private_educational", "property_type"),
    "PRAMUSCONS": ("private_amusement_and_recreation", "property_type"),
    "PRMFGCONS": ("private_manufacturing", "property_type"),
}

CFPB_CREDIT_CARD_FIGURE_DATA_SERIES_ID = "cfpb_credit_card_market_figure_data_2025"
CFPB_CREDIT_CARD_MARKET_REPORT_SERIES_ID = "cfpb_credit_card_market_report_2025"
CFPB_CREDIT_CARD_INTEREST_PAYMENT_MECHANICS_SERIES_ID = (
    "cfpb_credit_card_interest_payment_mechanics_context"
)
CFPB_CONSUMER_CREDIT_TRENDS_ALL_DATA_SERIES_ID = "cfpb_consumer_credit_trends_all_data"
CFPB_CONSUMER_CREDIT_TRENDS_CODEBOOK_SERIES_ID = "cfpb_consumer_credit_trends_codebook"
CFPB_TCCP_SURVEY_SERIES_ID = "cfpb_terms_credit_card_plans_2025h1"
CFPB_PAYMENT_AMOUNT_FURNISHING_SERIES_ID = "cfpb_payment_amount_furnishing_report"
CFPB_CREDIT_CARD_REVOLVERS_SERIES_ID = "cfpb_credit_card_revolvers_data_point"
CFPB_MEM_SAMPLE1_SERIES_ID = "cfpb_making_ends_meet_sample1_public_use"
CFPB_MEM_SAMPLES_3_6_SERIES_ID = "cfpb_making_ends_meet_samples_3_6_public_use"
PHILLY_FED_Y14_CREDIT_CARD_SERIES_ID = (
    "philadelphia_fed_y14_large_bank_credit_card_context"
)
NYFED_CONSUMER_CREDIT_PANEL_FAQ_SERIES_ID = "nyfed_consumer_credit_panel_faq"
NYFED_HOUSEHOLD_DEBT_CREDIT_REPORT_SERIES_ID = (
    "nyfed_household_debt_credit_report_2026q1"
)
FED_CRE_HIGH_GROWTH_DEPOSIT_SERIES_ID = "fed_cre_high_growth_deposit_accessible_data"
ATLANTA_FED_CREMI_LONGWEIGHTS_SERIES_ID = "atlanta_fed_cremi_longweights_context"
FED_CRE_EVERGREENING_EXTENSION_TERMS_SERIES_ID = (
    "fed_cre_evergreening_extension_terms_context"
)
FED_PRIVATE_CREDIT_CHARACTERISTICS_SERIES_ID = (
    "fed_private_credit_characteristics_accessible_data"
)
FED_BANK_LENDING_PRIVATE_CREDIT_SERIES_ID = (
    "fed_bank_lending_private_credit_financial_stability_context"
)
FED_INDIRECT_CREDIT_ACCESSIBLE_MATERIALS_SERIES_ID = (
    "fed_indirect_credit_supply_accessible_materials"
)
FED_CREDIT_BUREAU_HOUSEHOLD_DSR_SERIES_ID = (
    "fed_credit_bureau_household_dsr_accessible_data"
)
FED_STUDENT_LOAN_PAYMENT_RESTART_SPENDING_SERIES_ID = (
    "fed_student_loan_payment_restart_spending_context"
)
FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_SERIES_ID = (
    "fed_credit_card_limit_increase_debt_context"
)
FED_CREDIT_CARD_PROFITABILITY_REVOLVER_SERIES_ID = (
    "fed_credit_card_profitability_revolver_context"
)
FED_CREDIT_CARD_DELINQUENCY_PREDICTION_SERIES_ID = (
    "fed_credit_card_delinquency_prediction_context"
)
FED_CONSUMER_DELINQUENCY_DYNAMICS_SERIES_ID = (
    "fed_consumer_delinquency_dynamics_context"
)
FED_CREDIT_CARD_REWARDS_LIMIT_SPENDING_SERIES_ID = (
    "fed_credit_card_rewards_limit_spending_context"
)
FED_AUTO_LOAN_PAYMENT_DELINQUENCY_SERIES_ID = (
    "fed_auto_loan_payment_delinquency_context"
)
FED_AUTO_LOAN_PREPAYMENT_MATURITY_SERIES_ID = (
    "fed_auto_loan_prepayment_maturity_context"
)
BOSTON_FED_CREDIT_CARD_INTEREST_SPENDING_SERIES_ID = (
    "boston_fed_credit_card_interest_spending_response_context"
)
BOSTON_FED_CREDIT_CARD_SPENDING_CHANNEL_WP_SERIES_ID = (
    "boston_fed_credit_card_spending_channel_wp_context"
)
SEC_PRIVATE_FUND_AGGREGATE_ASSETS_SERIES_ID = (
    "sec_private_fund_statistics_aggregate_assets"
)
SEC_BDC_PUBLIC_FILING_AVAILABILITY_SERIES_ID = (
    "sec_bdc_public_filing_availability_context"
)
SEC_BDC_PORTFOLIO_INVESTMENT_TERMS_SERIES_ID = (
    "sec_bdc_portfolio_investment_terms_panel"
)
SEC_BDC_PORTFOLIO_PERFORMANCE_STATUS_SERIES_ID = (
    "sec_bdc_portfolio_performance_status_panel"
)
SEC_BDC_PORTFOLIO_TERMS_STATUS_JOIN_SERIES_ID = (
    "sec_bdc_portfolio_terms_status_join_panel"
)
SEC_BDC_PORTFOLIO_TERMS_STATUS_TIME_SERIES_ID = (
    "sec_bdc_portfolio_terms_status_time_panel"
)
SEC_BDC_FLOATING_RATE_PASS_THROUGH_DESIGN_SERIES_ID = (
    "sec_bdc_floating_rate_pass_through_design_context"
)
SEC_BDC_BORROWER_NAME_CONTINUITY_SERIES_ID = "sec_bdc_borrower_name_continuity_context"
SEC_BDC_INVESTMENT_SIGNATURE_CONTINUITY_SERIES_ID = (
    "sec_bdc_investment_signature_continuity_context"
)
SEC_BDC_RECURRING_INVESTMENT_VALUE_STATUS_SERIES_ID = (
    "sec_bdc_recurring_investment_value_status_context"
)
SEC_ABS_EE_CMBS_ASSET_LEVEL_SERIES_ID = "sec_abs_ee_cmbs_asset_level_performance_panel"
SEC_ABS_EE_CMBS_TIME_DIMENSION_SERIES_ID = "sec_abs_ee_cmbs_asset_time_dimension_panel"
SEC_ABS_EE_RECENT_FILING_INDEX_SERIES_ID = "sec_abs_ee_recent_filing_index_context"
SEC_ABS_EE_CMBS_XML_VERIFICATION_SERIES_ID = (
    "sec_abs_ee_candidate_cmbs_xml_verification_context"
)
SEC_ABS_EE_CMBS_REPRESENTATIVENESS_DESIGN_SERIES_ID = (
    "sec_abs_ee_cmbs_representativeness_design_review_context"
)
SEC_ABS_EE_CMBS_REVIEWED_BALANCE_COVERAGE_SERIES_ID = (
    "sec_abs_ee_cmbs_reviewed_balance_coverage_context"
)
SEC_ABS_EE_CMBS_MATURITY_STATUS_OUTCOME_SERIES_ID = (
    "sec_abs_ee_cmbs_maturity_status_outcome_review_context"
)
FED_Z1_CMBS_ABS_POPULATION_DENOMINATOR_SERIES_ID = (
    "fed_z1_cmbs_abs_commercial_mortgage_population_context"
)
FED_Z1_TOTAL_COMMERCIAL_MORTGAGE_POPULATION_SERIES_ID = (
    "fed_z1_total_commercial_mortgage_population_context"
)
FRED_NONRES_CONSTRUCTION_REAL_ACTIVITY_BRIDGE_SERIES_ID = (
    "fred_nonres_construction_real_activity_bridge_context"
)
FRED_CRE_PROPERTY_TYPE_CONSTRUCTION_BRIDGE_SERIES_ID = (
    "fred_cre_property_type_construction_bridge_context"
)
FED_DFA_HOUSEHOLD_LIABILITY_SERIES_ID = "fed_dfa_household_liability_context"
FED_SCF_SUMMARY_EXTRACT_SERIES_ID = "fed_scf_2022_summary_extract_context"
FED_SCF_WEIGHTED_SUMMARY_SERIES_ID = (
    "fed_scf_2022_weighted_consumer_credit_summary_context"
)
FED_SCF_REPLICATE_WEIGHT_METHOD_SERIES_ID = (
    "fed_scf_2022_replicate_weight_methodology_context"
)
FED_SCF_UNCERTAINTY_SERIES_ID = "fed_scf_2022_consumer_credit_uncertainty_context"
FED_SHED_FINANCIAL_FRAGILITY_SERIES_ID = (
    "fed_shed_2025_financial_fragility_credit_payment_context"
)
SEC_BDC_REVIEW_CIKS: Mapping[str, str] = {
    "0001287750": "ARCC",
    "0001655888": "OBDC",
    "0001422183": "FSK",
    "0001572694": "GSBD",
}
SEC_ABS_EE_CMBS_REVIEWED_FILINGS: tuple[Mapping[str, str], ...] = (
    {
        "trust_name": "BMO 2024-5C5 Mortgage Trust",
        "cik": "2027304",
        "accession_number": "0001888524-26-006627",
        "filing_date": "2026-04-01",
        "period_of_report": "2026-03-17",
        "xml_document": "exh_102.xml",
    },
    {
        "trust_name": "Wells Fargo Commercial Mortgage Trust 2025-5C7",
        "cik": "2093119",
        "accession_number": "0001539497-26-000359",
        "filing_date": "2026-02-12",
        "period_of_report": "2026-03-11",
        "xml_document": "exh_102.xml",
    },
    {
        "trust_name": "BMO 2022-C2 Mortgage Trust",
        "cik": "1932997",
        "accession_number": "0001888524-26-006629",
        "filing_date": "2026-04-01",
        "period_of_report": "2026-03-17",
        "xml_document": "exh_102.xml",
    },
    {
        "trust_name": "BMO 2023-5C1 Mortgage Trust",
        "cik": "1984246",
        "accession_number": "0001888524-26-006647",
        "filing_date": "2026-04-01",
        "period_of_report": "2026-03-17",
        "xml_document": "exh_102.xml",
    },
    {
        "trust_name": "BMO 2025-5C9 Mortgage Trust",
        "cik": "2048804",
        "accession_number": "0001888524-26-006637",
        "filing_date": "2026-04-01",
        "period_of_report": "2026-03-17",
        "xml_document": "exh_102.xml",
    },
    {
        "trust_name": "CD 2017-CD4 Mortgage Trust",
        "cik": "1702745",
        "accession_number": "0001888524-26-006869",
        "filing_date": "2026-04-03",
        "period_of_report": "2026-03-17",
        "xml_document": "exh_102.xml",
    },
)
SEC_ABS_EE_RECENT_INDEX_QUARTERS: tuple[tuple[int, int], ...] = (
    (2026, 1),
    (2026, 2),
)
SEC_ABS_EE_XML_VERIFICATION_PER_QUARTER = 8
CFPB_CREDIT_CARD_FIGURE_DATA_DEFAULT = Path(
    "data/raw/cfpb/cfpb_consumer-credit-card-market-report-figure-data_2025.xlsm"
)
CFPB_CREDIT_CARD_MARKET_REPORT_DEFAULT = Path(
    "data/raw/cfpb/cfpb_consumer-credit-card-market-report_2025.pdf"
)
CFPB_CREDIT_CARD_INTEREST_PAYMENT_MECHANICS_DEFAULT = Path(
    "data/raw/cfpb/cfpb_ask_credit_card_interest_calculation.html"
)
CFPB_CREDIT_CARD_PAYMENT_ALLOCATION_REGZ_DEFAULT = Path(
    "data/raw/cfpb/cfpb_regulation_z_1026_53_payment_allocation.html"
)
CFPB_CREDIT_CARD_PAYMENT_ALLOCATION_REGZ_URL = (
    "https://www.consumerfinance.gov/rules-policy/regulations/1026/53/"
)
CFPB_CONSUMER_CREDIT_TRENDS_ALL_DATA_DEFAULT = Path(
    "data/raw/cfpb/consumer_credit_trends_all_data.csv"
)
CFPB_CONSUMER_CREDIT_TRENDS_CODEBOOK_DEFAULT = Path(
    "data/raw/cfpb/CCT_dd_cb_all_files.xlsx"
)
CFPB_TCCP_SURVEY_DEFAULT = Path("data/raw/cfpb/cfpb_tccp-data_2025-06-30.xlsx")
CFPB_PAYMENT_AMOUNT_FURNISHING_DEFAULT = Path(
    "data/raw/cfpb/cfpb_quarterly-consumer-credit-trends_report_2020-11.pdf"
)
CFPB_CREDIT_CARD_REVOLVERS_DEFAULT = Path(
    "data/raw/cfpb/bcfp_data-point_credit-card-revolvers.pdf"
)
CFPB_MEM_SAMPLE1_DEFAULT = Path("data/raw/cfpb/cfpb_making-ends-meet_data-sample-1.zip")
CFPB_MEM_SAMPLES_3_6_DEFAULTS: Mapping[int, tuple[str, Path]] = {
    sample: (
        (
            "https://files.consumerfinance.gov/f/documents/"
            f"cfpb_making-ends-meet_data-sample-{sample}.zip"
        ),
        Path(f"data/raw/cfpb/cfpb_making-ends-meet_data-sample-{sample}.zip"),
    )
    for sample in (3, 4, 5, 6)
}
PHILLY_FED_Y14_CREDIT_CARD_BALANCES_URL = (
    "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/"
    "Y14/2025/Q4/25Q4-CreditCardBalances.csv?sc_lang=en"
)
PHILLY_FED_Y14_CREDIT_CARD_ORIGINATION_URL = (
    "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/"
    "Y14/2025/Q4/25Q4-CreditCardOrigination.csv?sc_lang=en"
)
PHILLY_FED_Y14_DEFINITIONS_URL = (
    "https://www.philadelphiafed.org/surveys-and-data/y14-definitions"
)
PHILLY_FED_Y14_METHODOLOGY_URL = (
    "https://www.philadelphiafed.org/surveys-and-data/y14-methodology"
)
PHILLY_FED_Y14_CREDIT_CARD_BALANCES_DEFAULT = Path(
    "data/raw/philadelphia_fed/25Q4-CreditCardBalances.csv"
)
PHILLY_FED_Y14_CREDIT_CARD_ORIGINATION_DEFAULT = Path(
    "data/raw/philadelphia_fed/25Q4-CreditCardOrigination.csv"
)
NYFED_HOUSEHOLD_DEBT_CREDIT_REPORT_DEFAULT = Path(
    "data/raw/nyfed/hhd_c_report_2026q1.xlsx"
)
FED_INDIRECT_CREDIT_ACCESSIBLE_MATERIALS_DEFAULT = Path("data/raw/fed/feds2025059.zip")
FED_CREDIT_BUREAU_HOUSEHOLD_DSR_ACCESSIBLE_DEFAULT = Path(
    "data/raw/fed/feds_notes_credit_bureau_household_dsr_accessible_data.html"
)
FED_CREDIT_BUREAU_HOUSEHOLD_DSR_ARTICLE_DEFAULT = Path(
    "data/raw/fed/feds_notes_credit_bureau_household_dsr_article.html"
)
FED_STUDENT_LOAN_PAYMENT_RESTART_SPENDING_HTML_DEFAULT = Path(
    "data/raw/fed/feds_notes_student_loan_payment_restart_spending.html"
)
FED_STUDENT_LOAN_PAYMENT_RESTART_SPENDING_ACCESSIBLE_DEFAULT = Path(
    "data/raw/fed/feds_notes_student_loan_payment_restart_spending_accessible.html"
)
FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_HTML_DEFAULT = Path(
    "data/raw/fed/feds_notes_credit_card_limit_increase_debt.html"
)
FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_ACCESSIBLE_DEFAULT = Path(
    "data/raw/fed/feds_notes_credit_card_limit_increase_debt_accessible.html"
)
FED_CREDIT_CARD_PROFITABILITY_HTML_DEFAULT = Path(
    "data/raw/fed/feds_notes_credit_card_profitability.html"
)
FED_CREDIT_CARD_DELINQUENCY_PREDICTION_HTML_DEFAULT = Path(
    "data/raw/fed/feds_notes_credit_card_delinquency_prediction.html"
)
FED_CREDIT_CARD_DELINQUENCY_PREDICTION_ACCESSIBLE_DEFAULT = Path(
    "data/raw/fed/feds_notes_credit_card_delinquency_prediction_accessible.html"
)
FED_CONSUMER_DELINQUENCY_DYNAMICS_HTML_DEFAULT = Path(
    "data/raw/fed/feds_notes_consumer_delinquency_dynamics.html"
)
FED_CONSUMER_DELINQUENCY_DYNAMICS_ACCESSIBLE_DEFAULT = Path(
    "data/raw/fed/feds_notes_consumer_delinquency_dynamics_accessible.html"
)
FED_CREDIT_CARD_REWARDS_LIMIT_SPENDING_DEFAULT = Path(
    "data/raw/fed/feds2023007_credit_card_rewards_accessible_materials.zip"
)
FED_AUTO_LOAN_PAYMENT_DELINQUENCY_HTML_DEFAULT = Path(
    "data/raw/fed/feds_notes_auto_loan_payment_delinquency.html"
)
FED_AUTO_LOAN_PAYMENT_DELINQUENCY_ACCESSIBLE_DEFAULT = Path(
    "data/raw/fed/feds_notes_auto_loan_payment_delinquency_accessible.html"
)
FED_AUTO_LOAN_PREPAYMENT_MATURITY_DEFAULT = Path(
    "data/raw/fed/feds2024056_auto_loan_prepayment_maturity.zip"
)
BOSTON_FED_CREDIT_CARD_INTEREST_SPENDING_DEFAULT = Path(
    "data/raw/boston_fed/how_interest_rate_changes_affect_credit_card_spending.html"
)
BOSTON_FED_CREDIT_CARD_SPENDING_CHANNEL_WP_DEFAULT = Path(
    "data/raw/boston_fed/WP2510_credit_card_spending_channel.pdf"
)
ATLANTA_FED_CREMI_LONGWEIGHTS_DEFAULT = Path(
    "data/raw/atlanta_fed/cremi_cbsa_contribution.csv"
)
ATLANTA_FED_CREMI_PAGE_DEFAULT = Path(
    "data/raw/atlanta_fed/cremi_market_index_page.html"
)
FED_CRE_EVERGREENING_EXTENSION_TERMS_HTML_DEFAULT = Path(
    "data/raw/fed/feds_2026_025_cre_evergreening.html"
)
FED_CRE_EVERGREENING_EXTENSION_TERMS_PDF_DEFAULT = Path(
    "data/raw/fed/feds_2026_025_cre_evergreening.pdf"
)
SEC_PRIVATE_FUND_AGGREGATE_ASSETS_DEFAULT = Path(
    "data/raw/sec/private_fund_aggregate_assets_2026_04_07.json"
)
SEC_BDC_PUBLIC_FILING_DIR_DEFAULT = Path("data/raw/sec/edgar_bdc_filings")
SEC_ABS_EE_CMBS_DIR_DEFAULT = Path("data/raw/sec/abs_ee_cmbs_filings")
FED_SCF_SUMMARY_EXTRACT_DEFAULT = Path("data/raw/fed_scf/scfp2022excel.zip")
FED_SCF_REPLICATE_WEIGHT_DEFAULT = Path("data/raw/fed_scf/scf2022rw1s.zip")
FED_SCF_STANDARD_ERROR_DOCUMENTATION_DEFAULT = Path(
    "data/raw/fed_scf/Standard_Error_Documentation.pdf"
)
FED_SCF_CODEBOOK_DEFAULT = Path("data/raw/fed_scf/codebk2022.txt")
FED_SHED_PUBLIC_USE_DATA_DEFAULT = Path(
    "data/raw/fed_shed/SHED_public_use_data_2025_CSV.zip"
)
FED_SHED_CODEBOOK_DEFAULT = Path("data/raw/fed_shed/SHED_2025codebook.pdf")
CFPB_CREDIT_CARD_USE_OF_CREDIT_SHEET = "xl/worksheets/sheet3.xml"
CFPB_CREDIT_CARD_COST_OF_CREDIT_SHEET = "xl/worksheets/sheet4.xml"
CFPB_CREDIT_CARD_PAYMENT_BEHAVIOR_SHEET = "xl/worksheets/sheet5.xml"
CFPB_CREDIT_CARD_AVAILABILITY_SHEET = "xl/worksheets/sheet7.xml"
CFPB_TCCP_SURVEY_SHEET = "xl/worksheets/sheet1.xml"
CFPB_MEM_SAMPLE1_CSV = "Sample1/MEM_S1W1W2W3_PUF.csv"
CFPB_MEM_SAMPLE1_CODEBOOK = "Sample1/MEM_S1W1W2W3_PUF_codebook.txt"
CFPB_MEM_SAMPLE1_README = "Sample1/README.txt"
CFPB_MEM_SAMPLE1_USER_GUIDE = "Sample1/MEM PUF User Guide.pdf"
CFPB_TCCP_REQUIRED_HEADERS = (
    "Institution Name",
    "Issued by Top 25 Institution",
    "Product Name",
    "Report Date",
    "Availability of Credit Card Plan",
    "Secured Card",
    "Targeted Credit Tiers",
    "Purchase APR Offered?",
    "Purchase APR Index",
    "Variable Rate Index",
    "Index",
    "Purchase APR Vary by Credit Tier",
    "Purchase APR no score",
    "Purchase APR poor",
    "Purchase APR good",
    "Purchase APR great",
    "Purchase APR min",
    "Purchase APR median",
    "Purchase APR max",
    "Grace Period Offered?",
    "Grace Period",
)
NYFED_CONSUMER_CREDIT_PANEL_FAQ_MARKERS = (
    "Access to the Consumer Credit Panel (CCP) microdata is limited to Federal Reserve System researchers",
    "due to contractual limitations with the data provider",
    "many aggregated looks at the data are provided on our data bank",
    "custom cuts of the data are not available",
    "The data include the statement balance",
    "It is impossible to distinguish between transactors",
)
NYFED_HOUSEHOLD_DEBT_CREDIT_EXPECTED_TITLES: Mapping[str, str] = {
    "Page 3 Data": "Total Debt Balance and Its Composition",
    "Page 10 Data": "Credit Limit and Balance for Credit Cards and HE Revolving",
    "Page 11 Data": "Total Balance by Delinquency Status",
    "Page 12 Data": "Percent of Balance 90+ Days Delinquent by Loan Type",
    "Page 20 Data": "Total Debt Balance by Age",
    "Page 21 Data": "Debt Share by Product Type and Age (2026Q1)",
    "Page 24 Data": "Transition into Serious Delinquency (90+) by Age",
    "Page 27 Data": "Transition into Serious Delinquency (90+) for Credit Cards by Age",
    "Page 32 Data": "Total Debt Balance per Capita* by State",
    "Page 35 Data": "Percent of Balance 90+ Days Late by State",
    "Page 38 Data": "Quarterly Transition Rates into 90+ Days Late by State*",
}
FED_CRE_HIGH_GROWTH_EXPECTED_FIGURES = (
    "Figure 1. CRE Origination Index",
    "Figure 2. Relative Importance of High-Growth Banks",
    "Figure 3. Portfolio Composition of CRE Loan Types",
    "Figure 4. CRE Loan Growth and Deposit Funding Share in the Same CBSA",
)
FED_CRE_HIGH_GROWTH_EXPECTED_MARKERS = (
    "Source: CRE Public Records and FR Y-14Q",
    "Source: CRE Public Records, FR Y-9C, and Call Reports",
    "Source: CRE Public Records",
    "Source: Summary of Deposits and CRE Public Records",
)
FED_PRIVATE_CREDIT_CHARACTERISTICS_EXPECTED_TABLES: Mapping[
    str, tuple[str, str, str]
] = {
    "Figure 1. Growth in Private Debt Allocations": (
        "private_credit_allocation_scale",
        "billions_of_dollars",
        "exposure_size_and_liquidity",
    ),
    "Figure 2. Top 20 Private Debt Managers": (
        "private_credit_manager_concentration",
        "billions_of_dollars",
        "exposure_size_and_liquidity",
    ),
    "Figure 3. Number of Loans in Pitchbook": (
        "private_credit_pitchbook_loan_count",
        "number_of_loans",
        "exposure_size",
    ),
    "Figure 4. Average Deal and Loan Size": (
        "private_credit_average_deal_loan_size",
        "millions_of_dollars",
        "exposure_size",
    ),
    "Figure 5. Loan Type": (
        "private_credit_loan_type_share",
        "percent",
        "loan_structure",
    ),
    "Figure 6. Credit Spreads": (
        "private_credit_credit_spread",
        "basis_points",
        "borrower_rate_context",
    ),
    "Figure 7. Maturity Wall in Private Credit": (
        "private_credit_maturity_wall_share",
        "percent_of_private_credit_loan_amount",
        "maturity",
    ),
    "Figure 8. Average Maturity in Private Credit": (
        "private_credit_average_maturity_at_origination",
        "years",
        "maturity",
    ),
    "Figure 9. Deal Types": (
        "private_credit_loan_amount_by_deal_type",
        "percent_of_private_credit_loan_amount",
        "loan_structure",
    ),
    "Figure 10. Average Loan Spread By Deal Type": (
        "private_credit_loan_spread_by_deal_type",
        "basis_points",
        "borrower_rate_context",
    ),
    "Figure 11. Average Number of Lenders in a single loan facility": (
        "private_credit_lenders_per_facility",
        "lenders_per_facility",
        "market_structure",
    ),
    "Figure 12. Interest Coverage Ratio has declined": (
        "private_credit_interest_coverage_ratio",
        "ratio",
        "borrower_resilience",
    ),
    "Figure 13. Year-to-Date Default Rate (As of Oct, 2023)": (
        "private_credit_default_rate",
        "percent",
        "borrower_resilience",
    ),
    "Figure 14. Share of Loans with 1st Liens": (
        "private_credit_lien_share",
        "percent",
        "collateral_structure",
    ),
    "Figure 15. Recovery Rate": (
        "private_credit_recovery_rate",
        "percent",
        "collateral_structure",
    ),
    "Figure 16. Share of Lower Collateral Sectors": (
        "private_credit_lower_collateral_sector_share",
        "percent",
        "sector_context",
    ),
}
FED_INDIRECT_CREDIT_ACCESSIBLE_EXPECTED_FILES = (
    "index.html",
    "accessible_figures.html",
)
FED_INDIRECT_CREDIT_ACCESSIBLE_EXPECTED_MARKERS = (
    "Indirect Credit Supply: How Bank Lending to Private Credit Shapes Monetary Policy Transmission",
    "Table 8:  BDCs' Reliance on Bank Financing and Monetary Pass Through",
    "Table 9:  Real Effects of BDC Financing during Tightening",
    "Figure 5: Aggregate Credit Volume and Borrowing Costs for Nonfinancial Businesses",
)
FED_INDIRECT_CREDIT_ACCESSIBLE_TABLES: Mapping[str, tuple[str, str, str, str]] = {
    "Table 8:  BDCs' Reliance on Bank Financing and Monetary Pass Through": (
        "bdc_bank_financing_monetary_pass_through",
        "2012Q3",
        "2023Q4",
        "borrower_pass_through",
    ),
    "Table 9:  Real Effects of BDC Financing during Tightening": (
        "bdc_credit_real_effects_during_tightening",
        "2012",
        "2023",
        "nonbank_to_real_activity",
    ),
}
FED_CREDIT_BUREAU_HOUSEHOLD_DSR_MARKERS = (
    "Introducing a Credit Bureau-Based Measure of U.S. Household Debt Service",
    "Credit Bureau Methodology",
)
FED_CREDIT_BUREAU_HOUSEHOLD_DSR_ARTICLE_MARKERS = (
    "Introducing a Credit Bureau-Based Measure of U.S. Household Debt Service",
    "monthly scheduled payments for each open tradeline",
    "The scheduled payment reported for credit cards is the minimum required payment",
    "These data include monthly scheduled payments",
)
FED_CREDIT_BUREAU_HOUSEHOLD_DSR_TABLES = (
    ("total_household_dsr", "figure_1_total_required_debt_service"),
    ("mortgage_dsr", "figure_2_mortgage_required_debt_service"),
    ("consumer_debt_dsr", "figure_2_consumer_required_debt_service"),
)
FED_STUDENT_LOAN_PAYMENT_RESTART_ACCESSIBLE_URL = (
    "https://www.federalreserve.gov/econres/notes/feds-notes/"
    "debt-payments-and-spending-evidence-from-the-2023-student-loan-payment-"
    "accessible-20250905.htm"
)
FED_STUDENT_LOAN_PAYMENT_RESTART_MARKERS = (
    "Debt Payments and Spending: Evidence from the 2023 Student Loan Payment Restart",
    "unique natural experiment",
    "Verisk Commerce Signals Spend Tracker",
    "55 million individuals and 89 million credit and debit cards",
    "Federal Reserve Bank of New York/Equifax Consumer Credit Panel",
    "18,178 ZIP codes",
    "roughly $80 billion at an annual rate",
    "0.3 percent of GDP",
    "student loan payments began at different times",
)
FED_STUDENT_LOAN_PAYMENT_RESTART_ACCESSIBLE_MARKERS = (
    "Post-Announcement",
    "Payment Resumption",
    "estimated at -$6.20",
    "estimated at -$12.20",
    "95 percent confidence bands ranging from -$11 to -$2",
    "95 percent confidence bands ranging from -$17 to -$7",
)
FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_ACCESSIBLE_URL = (
    "https://www.federalreserve.gov/econres/notes/feds-notes/"
    "more-credit-more-debt-new-evidence-on-automated-credit-decisions-"
    "accessible-20260116.htm"
)
FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_MARKERS = (
    "More Credit, More Debt: New Evidence on Automated Credit Decisions",
    "Automated Credit Decisions",
    "Federal Reserve Y-14M regulatory data",
    "more than 70 percent of the U.S. credit card market",
    "About 12 percent of credit cards receive limit increases annually",
    "about $160 billion dollars of new available credit each year",
    "approximately 80 percent",
    "revolving borrowers who carry balances month-to-month",
)
FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_ACCESSIBLE_MARKERS = (
    "Figure 1. Credit limits over time, by credit score",
    "subprime borrowers with credit scores below 600 are only $700",
    "a 285 percent increase",
    "superprime borrowers with credit scores above 760",
    "Figure 2. Limit increases among revolving and transacting accounts",
    "roughly 2 percent of transactors",
    "almost 4 percent of revolvers",
    "Figure 3. Revolving utilization around limit increases",
    "within about 6 months",
    "comprising about 30 percent of the credit limit increase",
)
FED_CREDIT_CARD_PROFITABILITY_MARKERS = (
    "Credit Card Profitability",
    "FR Y-14M Data",
    "constant sample of 13 banks",
    "covers about 80 percent of credit card balances",
    "Table 1. Costs of Using a Credit Card",
    "heavy revolvers",
    "light revolvers",
    "transactors",
    "Interest Charge",
)
FED_CREDIT_CARD_DELINQUENCY_PREDICTION_ACCESSIBLE_URL = (
    "https://www.federalreserve.gov/econres/notes/feds-notes/"
    "predicting-credit-card-delinquency-rates-accessible-20250228.htm"
)
FED_CREDIT_CARD_DELINQUENCY_PREDICTION_MARKERS = (
    "Predicting Credit Card Delinquency Rates",
    "using as explanatory variables factors commonly believed to affect "
    "household credit performance",
    "interest rates, the unemployment rate, the level of indebtedness",
    "We estimate the model over the period from 2000:Q1",
    "The model shows an increase in delinquencies of about 120 basis points",
    "we cannot make causal inferences",
)
FED_CREDIT_CARD_DELINQUENCY_PREDICTION_ACCESSIBLE_MARKERS = (
    "Seasonally Adjusted Credit Card Delinquency Rate",
    "Observed Seasonally Adjusted Credit Card Delinquency Rate",
    "Lower 95% Confidence Bound on Prediction",
    "Prime Rate Contribution",
    "Real Revolving Credit Contribution",
    "Nonprime Balance Share Contribution",
    "Predicted Seasonally Adjusted Credit Card Delinquency Rate with Counterfactual",
)
FED_CREDIT_CARD_DELINQUENCY_PREDICTION_TABLE_TITLES = (
    "seasonally_adjusted_credit_card_delinquency_rate",
    "observed_predicted_credit_card_delinquency_rate",
    "model_contribution_by_variable",
    "counterfactual_credit_card_delinquency_rate",
)
FED_CONSUMER_DELINQUENCY_DYNAMICS_ACCESSIBLE_URL = (
    "https://www.federalreserve.gov/econres/notes/feds-notes/"
    "a-note-on-recent-dynamics-of-consumer-delinquency-rates-accessible-"
    "20251124.htm"
)
FED_CONSUMER_DELINQUENCY_DYNAMICS_MARKERS = (
    "A Note on Recent Dynamics of Consumer Delinquency Rates",
    "Federal Reserve Bank of New York Consumer Credit Panel/Equifax",
    "nationally representative random sample of anonymized Equifax credit bureau data",
    "credit card and auto loan delinquency rates",
    "across credit scores, income groups, and by homeownership status",
)
FED_CONSUMER_DELINQUENCY_DYNAMICS_ACCESSIBLE_MARKERS = (
    "Credit Card Delinquency Rate",
    "Auto Loan Delinquency Rate",
    "Share of Subprime Borrowers",
    "Year-Over-Year Change in the Credit Card Delinquency Rate",
    "Subprime Credit Card Delinquency Rate",
    "Credit Card Delinquency Rate in Low-Income Census Tracts",
    "Credit Card Delinquency Rate for Mortgage Borrowers",
)
FED_CONSUMER_DELINQUENCY_DYNAMICS_TABLE_TITLES = (
    "aggregate_credit_card_auto_delinquency_rates",
    "credit_score_distribution",
    "credit_card_delinquency_yoy_change",
    "auto_loan_delinquency_yoy_change",
    "auto_loan_origination_vintage_delinquency_rates",
    "credit_card_delinquency_by_credit_score",
    "auto_loan_delinquency_by_credit_score",
    "credit_card_delinquency_by_income_tract",
    "auto_loan_delinquency_by_income_tract",
    "credit_card_delinquency_by_mortgage_status",
    "auto_loan_delinquency_by_mortgage_status",
)
FED_CREDIT_CARD_REWARDS_LIMIT_SPENDING_EXPECTED_FILES = (
    "index.html",
    "accessible_figures.html",
)
FED_CREDIT_CARD_REWARDS_LIMIT_SPENDING_MARKERS = (
    "Who Pays For Your Rewards? Redistribution in the Credit Card Market",
    "credit card data from the Federal Reserve Board's Y-14M reports",
    "bank-initiated credit limit increase",
    "The dependent variable is the change in average spending, repayments, or unpaid balances between the 6-month period before and the 6-month period after the credit limit increase",
    "Table 6:  Overindebtedness: Difference-in-Differences Analysis",
)
FED_AUTO_LOAN_PAYMENT_DELINQUENCY_ACCESSIBLE_URL = (
    "https://www.federalreserve.gov/econres/notes/feds-notes/"
    "rising-auto-loan-delinquencies-and-high-monthly-payments-accessible-"
    "20240926.htm"
)
FED_AUTO_LOAN_PAYMENT_DELINQUENCY_MARKERS = (
    "Rising Auto Loan Delinquencies and High Monthly Payments",
    "auto loans are an important sector in consumer credit",
    "about 25 percent of nonmortgage consumer credit",
    "New York Federal Reserve Consumer Credit Panel",
    "Experian AutoCount",
    "one percent random sample of all auto loans originated between 2017 and 2022",
    "average required monthly payments increased from $470 to about $600",
    "larger auto loan amount at origination, rather than the increases in interest rates",
    "around 37 percent of auto loan balances comprise loans originated in the previous 12 months",
    "log monthly payment",
)
FED_AUTO_LOAN_PAYMENT_DELINQUENCY_ACCESSIBLE_MARKERS = (
    "Figure 1. Auto Loan Delinquency Rates",
    "Figure 2. Cumulative Delinquency",
    "Figure 3. Average Monthly Payment",
    "Figure 4. Average Loan Size and Interest Rate",
)
FED_AUTO_LOAN_PREPAYMENT_MATURITY_EXPECTED_FILES = (
    "index.html",
    "accessible_figures.html",
)
FED_AUTO_LOAN_PREPAYMENT_MATURITY_MARKERS = (
    "One Month Longer, One Month Later? Prepayments in the Auto Loan Market",
    "Analyzing more than half of the auto loans originated during the past 16 years",
    "longer-maturity new car loans have significantly higher interest rates",
    "the majority of auto loans were prepaid",
    "liquidity constraints, uncertainty about future income, and monthly payment targeting",
)
FED_AUTO_LOAN_PREPAYMENT_MATURITY_ACCESSIBLE_MARKERS = (
    "Figure 1: Recent Trend of Average Auto Loan Maturity",
    "Figure 7: Trends of Prepayments of Auto Loans",
    "paid_over_scheduled",
)
BOSTON_FED_CREDIT_CARD_INTEREST_SPENDING_MARKERS = (
    "How Interest Rate Changes Affect Credit Card Spending",
    "when credit card interest rates increase by 1 percentage point, "
    "consumers reduce their credit card spending by 8.7 percent",
    "nearly 80 percent of all US credit card accounts",
    "2016-2025 period",
    "regression kink design",
    "consumer spending more broadly",
)
BOSTON_FED_CREDIT_CARD_SPENDING_CHANNEL_WP_MARKERS = (
    "The Credit Card Spending Channel of Monetary Policy",
    "Micro Evidence from Account-level Data",
    "regression kink design",
    "nearly 80 percent of all US credit cards",
    "Table 2: RKD Estimates of Interest-rate Elasticity",
    "Table 6: Response of Spending Growth at h = 2",
    "Jarocin",
    "Anderson",
    "Rubin confidence intervals",
)
FED_SCF_SUMMARY_EXTRACT_FILE = "SCFP2022.csv"
FED_SCF_REPLICATE_WEIGHT_FILE = "p22_rw1.dta"
FED_SHED_PUBLIC_USE_FILE = "public2025.csv"
FED_SCF_INDEX_PAGE_URL = "https://www.federalreserve.gov/econres/scfindex.htm"
FED_SCF_STANDARD_ERROR_DOCUMENTATION_URL = (
    "https://www.federalreserve.gov/econres/files/Standard_Error_Documentation.pdf"
)
FED_SCF_CODEBOOK_URL = "https://www.federalreserve.gov/econres/files/codebk2022.txt"
FED_SCF_REPLICATE_REQUIRED_INDEX_MARKERS = (
    "replicate weight files",
    "Standard Error Documentation",
    "Failure to account for the imputations and the complex sample design",
    "five separate imputation replicates",
)
FED_SCF_SUMMARY_EXTRACT_FIELDS = (
    "YY1",
    "Y1",
    "WGT",
    "INCOME",
    "NORMINC",
    "INCCAT",
    "NINCCAT",
    "AGE",
    "AGECL",
    "EDCL",
    "LIQ",
    "HLIQ",
    "CCBAL",
    "NOCCBAL",
    "HCCBAL",
    "CREDIT",
    "INSTALL",
    "HINSTALL",
    "DEBT",
    "HDEBT",
    "DEBT2INC",
    "CONSPAY",
    "REVPAY",
    "PIRREV",
)
FED_SCF_WEIGHTED_SUMMARY_GROUPS = (
    ("all", "", ""),
    ("income_category", "inccat", "1"),
    ("income_category", "inccat", "2"),
    ("income_category", "inccat", "3"),
    ("income_category", "inccat", "4"),
    ("income_category", "inccat", "5"),
    ("income_category", "inccat", "6"),
    ("normal_income_category", "ninccat", "1"),
    ("normal_income_category", "ninccat", "2"),
    ("normal_income_category", "ninccat", "3"),
    ("normal_income_category", "ninccat", "4"),
    ("normal_income_category", "ninccat", "5"),
    ("normal_income_category", "ninccat", "6"),
    ("age_category", "agecl", "1"),
    ("age_category", "agecl", "2"),
    ("age_category", "agecl", "3"),
    ("age_category", "agecl", "4"),
    ("age_category", "agecl", "5"),
    ("age_category", "agecl", "6"),
    ("credit_card_balance_status", "hccbal", "0"),
    ("credit_card_balance_status", "hccbal", "1"),
    ("debt_status", "hdebt", "0"),
    ("debt_status", "hdebt", "1"),
)
FED_SCF_UNCERTAINTY_METRICS = (
    ("mean_liquid_assets", "liq", "mean"),
    ("share_liquid_assets_positive", "hliq", "indicator_share"),
    ("mean_credit_card_balance", "ccbal", "mean"),
    ("share_credit_card_balance_positive", "hccbal", "indicator_share"),
    ("mean_debt", "debt", "mean"),
    ("share_debt_positive", "hdebt", "indicator_share"),
    ("mean_consumer_payment", "conspay", "mean"),
    ("mean_revolving_payment", "revpay", "mean"),
    ("mean_revolving_payment_income_ratio", "pirrev", "mean"),
)
FED_SCF_UNCERTAINTY_GROUPS = (
    ("all", "", ""),
    ("income_category", "inccat", "1"),
    ("income_category", "inccat", "2"),
    ("income_category", "inccat", "3"),
    ("income_category", "inccat", "4"),
    ("income_category", "inccat", "5"),
    ("income_category", "inccat", "6"),
    ("normal_income_category", "ninccat", "1"),
    ("normal_income_category", "ninccat", "2"),
    ("normal_income_category", "ninccat", "3"),
    ("normal_income_category", "ninccat", "4"),
    ("normal_income_category", "ninccat", "5"),
    ("normal_income_category", "ninccat", "6"),
    ("age_category", "agecl", "1"),
    ("age_category", "agecl", "2"),
    ("age_category", "agecl", "3"),
    ("age_category", "agecl", "4"),
    ("age_category", "agecl", "5"),
    ("age_category", "agecl", "6"),
    ("credit_card_balance_status", "hccbal", "0"),
    ("credit_card_balance_status", "hccbal", "1"),
    ("debt_status", "hdebt", "0"),
    ("debt_status", "hdebt", "1"),
)
FED_SHED_CODEBOOK_URL = (
    "https://www.federalreserve.gov/consumerscommunities/files/SHED_2025codebook.pdf"
)
ATLANTA_FED_CREMI_PAGE_URL = (
    "https://www.atlantafed.org/research-and-data/data/"
    "commercial-real-estate-market-index"
)
FED_CRE_EVERGREENING_EXTENSION_TERMS_PDF_URL = (
    "https://www.federalreserve.gov/econres/feds/files/2026025pap.pdf"
)
ATLANTA_FED_CREMI_REQUIRED_PAGE_MARKERS = (
    "Net Operating Income Index",
    "Market Cap Rate",
    "Asset Value",
    "the data provider does not allow the Federal Reserve Bank of Atlanta to share them externally",
)
FED_SHED_REQUIRED_FIELDS = (
    "shedid",
    "weight",
    "B2",
    "B3",
    "B3A_b",
    "C3P",
    "C4A",
    "E1_a",
    "E1_b",
    "E1_c",
    "E1_d",
    "E1_e",
    "pay_casheqv",
    "ppinc7",
    "ppagect4",
)
FED_SHED_GROUPS = (
    ("all", "", ""),
    ("income_category", "ppinc7", "Less than $10,000"),
    ("income_category", "ppinc7", "$10,000 to $24,999"),
    ("income_category", "ppinc7", "$25,000 to $49,999"),
    ("income_category", "ppinc7", "$50,000 to $74,999"),
    ("income_category", "ppinc7", "$75,000 to $99,999"),
    ("income_category", "ppinc7", "$100,000 to $149,999"),
    ("income_category", "ppinc7", "$150,000 or more"),
    ("age_category", "ppagect4", "18–29"),
    ("age_category", "ppagect4", "30–44"),
    ("age_category", "ppagect4", "45–59"),
    ("age_category", "ppagect4", "60+"),
)
STATA_NUMERIC_MISSING_THRESHOLD = 8.0e307
CFPB_MEM_SAMPLE1_REQUIRED_MARKERS: Mapping[str, tuple[str, ...]] = {
    "credit_card_payment_behavior": (
        "Has a credit card",
        "Unpaid credit card balance after last payment",
        "Expected change in credit card balance carried",
        "Used a credit card",
    ),
    "liquidity": (
        "HH balance in checking/savings accounts",
        "Amount of $2,000 expense HH could pay within a week",
        "How long HH could cover expenses if HH lost main income source",
    ),
    "bill_payment_stress": (
        "Expect to have difficulty paying for a bill/expense",
        "Past 12 months: Had difficulty with a bill/expense",
        "Paid another bill late or skipped a payment",
        "Cut back on other expenses",
    ),
    "income_context": (
        "HH annual income in 2018",
        "HH income variability",
        "Expectation for HH income in next year",
    ),
    "credit_score_context": (
        "Last time checked credit score or report",
        "Source of credit score or report",
        "Credit score change since last time checked",
    ),
}
CFPB_MEM_MULTISAMPLE_CATEGORY_MARKERS: Mapping[str, tuple[str, ...]] = {
    "credit_card_payment_behavior": (
        "credit card",
        "balance",
    ),
    "liquidity": (
        "savings",
        "checking",
    ),
    "bill_payment_stress": (
        "difficulty",
        "expense",
    ),
    "income_context": ("income",),
    "unexpected_expense_context": ("unexpected",),
}
PHILLY_FED_Y14_BALANCES_REQUIRED_COLUMNS = (
    "YRQTR",
    "Total Balances ($Billions)",
    "Number of Accounts (Millions)",
    "Share of Accounts Making the Minimum Payment",
    "Share of Accounts Making Greater Than the Minimum Payment but Less Than the Full Balance",
    "Share of Accounts Making the Full Balance Payment",
    "Revolving Balances Only ($Billions)",
    "Average Purchase APR: General Purpose",
    "Average Purchase APR: Private Label",
    "Total Purchase Volume ($Billions)",
    "Average Purchase Volume by Credit Score Group: <660 Credit Score",
    "Average Purchase Volume by Credit Score Group: 660-719 Credit Score",
    "Average Purchase Volume by Credit Score Group: >=720 Credit Score",
)
PHILLY_FED_Y14_ORIGINATION_REQUIRED_COLUMNS = (
    "YRQTR",
    "New Originations ($Billions)",
    "Number of New Accounts (Millions)",
    "Original Credit Score (50th percentile)",
    "Average Original Purchase APR: General Purpose",
    "Average Original Purchase APR: Private Label",
    "Percentage of New Accounts with <660 Credit Score",
    "Percentage of New Commitments with <660 Credit Score",
)
CFPB_PAYMENT_AMOUNT_FURNISHING_MARKERS = (
    "payment amount furnishing",
    "consumer reporting",
    "approximately five million de-identified credit records",
    "borrowers' actual payment",
    "table 1:",
    "Credit card",
    "Retail revolving",
    "actual payment amount furnished",
)
CFPB_PAYMENT_AMOUNT_FURNISHING_TABLE_VALUES: Mapping[str, tuple[str, str, str]] = {
    "Credit card": ("464", "285", "40"),
    "Retail revolving": ("212", "80", "71"),
    "Student loan": ("112", "50", "91"),
    "Auto": ("94", "84", "91"),
    "Mortgage": ("70", "66", "95"),
    "Other": ("60", "48", "93"),
    "All loan types": ("1011", "613", "65"),
}
CFPB_CREDIT_CARD_REVOLVERS_MARKERS = (
    "data point: credit card revolvers",
    "between april 2008 and april 2016",
    "covers approximately 85 percent of all credit card accounts",
    "end of cycle balance",
    "total payments made",
    "associated cardholders' credit score",
    "revolving episode",
    "patterns of repayment",
)
CFPB_CREDIT_CARD_REVOLVERS_METRICS: Mapping[str, tuple[str, str, str, str]] = {
    "ccdb_credit_card_account_coverage": (
        "approximately",
        "85",
        "percent_of_all_credit_card_accounts",
        r"covers approximately 85 percent of all credit card accounts",
    ),
    "active_account_revolver_share": (
        "approximately",
        "66.6667",
        "percent_of_active_accounts",
        r"among active accounts two of every three are revolvers",
    ),
    "monthly_transition_share": (
        "approximately",
        "10",
        "percent_of_accounts_per_month",
        r"transitions in and out of credit card debt.*1 in 10 accounts each month",
    ),
    "deep_subprime_revolver_share": (
        "approximately",
        "85",
        "percent_of_deep_subprime_accounts",
        r"deep-subprime borrowers.*about 85 percent revolve",
    ),
    "deep_subprime_transition_share": (
        "approximately",
        "5",
        "percent_of_accounts_per_month",
        r"only 1 in 20 accounts transitioning in any given month",
    ),
    "prime_episode_six_month_survival": (
        "exact_reported",
        "40",
        "percent_of_prime_episodes",
        r"prime episode will last 6 months or more is 40 percent",
    ),
    "prime_episode_more_than_two_years": (
        "approximately",
        "12",
        "percent_of_prime_episodes",
        r"about 12 percent of prime and 20 percent of subprime episodes last for more than 2 years",
    ),
    "subprime_episode_more_than_two_years": (
        "approximately",
        "20",
        "percent_of_subprime_episodes",
        r"about 12 percent of prime and 20 percent of subprime episodes last for more than 2 years",
    ),
    "mean_prime_revolving_episode_duration": (
        "exact_reported",
        "9",
        "months",
        r"episodes for prime and subprime accounts last for 9 and 13 months respectively",
    ),
    "mean_subprime_revolving_episode_duration": (
        "exact_reported",
        "13",
        "months",
        r"episodes for prime and subprime accounts last for 9 and 13 months respectively",
    ),
    "outstanding_balance_revolved_share": (
        "approximately",
        "82",
        "percent_of_outstanding_balances",
        r"nearly 82 percent of outstanding balances are revolved",
    ),
    "revolved_balance_one_year_plus_share": (
        "approximately",
        "70",
        "percent_of_revolved_balances",
        r"approximately 70 percent revolved balances.*accrue to accounts revolving continuously for a year or more",
    ),
}
CFPB_CREDIT_CARD_MARKET_REPORT_MARKERS = (
    "average annual percentage rate (apr) reached 25.2 percent",
    "the share of cardholders making only the minimum payment in 2024",
    "consumers were assessed $160 billion in interest charges",
    "prime rate the benchmark commercial banks use to set aprs increased a total of 5.1 percentage points",
    "almost all general purpose account interest rates are tied to a variable rate index",
    "increases to apr margin are typically reflected on new accounts and less frequently on existing accounts",
    "timing of these changes is open-ended and at the discretion of the lender",
    "report does not attribute a specific factor or group of factors",
)
CFPB_CREDIT_CARD_INTEREST_PAYMENT_MECHANICS_MARKERS = (
    "interest you owe daily",
    "average daily balance",
    "daily periodic rate",
    "minimum required",
    "highest interest rate",
)
CFPB_CREDIT_CARD_PAYMENT_ALLOCATION_REGZ_MARKERS = (
    "allocation of payments",
    "payment in excess of the required minimum periodic payment",
    "highest annual percentage rate",
    "required minimum periodic payment",
)
CFPB_CREDIT_CARD_MARKET_REPORT_METRICS: Mapping[str, tuple[str, str, str, str, str]] = {
    "average_apr_2024_all_cards": (
        "exact_reported",
        "25.2",
        "percent",
        "2024-12-31",
        r"average annual percentage rate \(apr\) reached 25\.2 percent",
    ),
    "new_general_purpose_account_apr_2024": (
        "exact_reported",
        "27.5",
        "percent",
        "2024-12-31",
        r"average apr for new general purpose accounts opened in 2024 was 27\.5",
    ),
    "minimum_payment_share_2024": (
        "exact_reported",
        "14",
        "percent_of_cardholders",
        "2024-12-31",
        r"made only the minimum payment up from 13 percent",
    ),
    "interest_charges_assessed_2024": (
        "exact_reported",
        "160",
        "billions_of_dollars",
        "2024-12-31",
        r"consumers were assessed \$160 billion in interest charges",
    ),
    "prime_rate_increase_2022_2023": (
        "exact_reported",
        "5.1",
        "percentage_points",
        "2023-12-31",
        r"prime rate .* increased a total of 5\.1 percentage points",
    ),
    "variable_index_rate_context": (
        "qualitative_reported",
        "almost_all_general_purpose_rates_tied_to_variable_index",
        "report_text_context",
        "2024-12-31",
        r"almost all general purpose account interest rates are tied to a variable rate index",
    ),
    "existing_account_apr_margin_timing_limitation": (
        "qualitative_reported",
        "existing_account_margin_changes_less_frequent_open_ended_timing",
        "report_text_context",
        "2024-12-31",
        r"increases to apr margin are typically reflected on new accounts and less frequently on existing accounts.*timing of these changes is open-ended",
    ),
    "issuer_apr_margin_attribution_limitation": (
        "qualitative_reported",
        "report_does_not_attribute_specific_factor_to_margin_changes",
        "report_text_context",
        "2024-12-31",
        r"report does not attribute a specific factor or group of factors",
    ),
}


def _records_sha256(records: Sequence[object]) -> str:
    payload = json.dumps(
        list(records),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _date_range(snapshot: SourceSnapshot) -> tuple[str, str]:
    dates = sorted(
        str(record.get("date", "")) for record in snapshot.records if record.get("date")
    )
    if not dates:
        return "", ""
    return dates[0], dates[-1]


def _annotated_context_snapshot(
    snapshot: SourceSnapshot, *, context_status: str
) -> SourceSnapshot:
    first_date, latest_date = _date_range(snapshot)
    records_hash = _records_sha256(snapshot.records)
    note = (
        f"{context_status};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(snapshot.records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "higher_rate_channel_gate_passed=false;"
        "prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false"
    )
    return SourceSnapshot(
        metadata=replace(snapshot.metadata, note=note),
        records=snapshot.records,
    )


def _download_source(url: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": SOURCE_ADMISSION_USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            output.write_bytes(response.read())
    except (TimeoutError, urllib.error.HTTPError, urllib.error.URLError):
        subprocess.run(
            [
                "curl",
                "-L",
                "--fail",
                "--silent",
                "--show-error",
                "-A",
                SOURCE_ADMISSION_USER_AGENT,
                "--output",
                str(output),
                url,
            ],
            check=True,
        )


def _pdf_text(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.replace("\u2019", "'").replace("\u2013", "-")


def _quarter_end_date(quarter: str) -> str:
    match = re.fullmatch(r"(\d{4})\s*Q([1-4])", quarter.strip())
    if match is None:
        raise ValueError(f"Unsupported quarter label: {quarter!r}")
    year = int(match.group(1))
    qtr = int(match.group(2))
    month = qtr * 3
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - timedelta(days=1)).isoformat()


def _month_day_year_date(value: str) -> str:
    match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", value.strip())
    if match is None:
        raise ValueError(f"Unsupported month/day/year label: {value!r}")
    month, day, year = (int(part) for part in match.groups())
    return date(year, month, day).isoformat()


def _sec_abs_ee_date(value: str) -> str:
    stripped = value.strip()
    dash_match = re.fullmatch(r"(\d{1,2})-(\d{1,2})-(\d{4})", stripped)
    if dash_match is not None:
        month, day, year = (int(part) for part in dash_match.groups())
        return date(year, month, day).isoformat()
    iso_match = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", stripped)
    if iso_match is not None:
        year, month, day = (int(part) for part in iso_match.groups())
        return date(year, month, day).isoformat()
    if not stripped:
        return ""
    raise ValueError(f"Unsupported SEC ABS-EE date label: {value!r}")


def _period_label_to_date(value: str) -> str:
    label = value.strip()
    if re.fullmatch(r"\d{4}\s*Q[1-4]", label):
        return _quarter_end_date(label.replace(" ", ""))
    if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", label):
        return _month_day_year_date(label)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", label):
        return label
    raise ValueError(f"Unsupported period label: {value!r}")


def _is_quarter_label(value: str | None) -> bool:
    return bool(value and re.fullmatch(r"\d{4}Q[1-4]", value.strip()))


def _clean_published_number(value: str) -> str:
    cleaned = (
        str(value).strip().replace("$", "").replace(",", "").replace("%", "").strip()
    )
    if cleaned.lower() in {"", "null", "nan"}:
        return ""
    return cleaned


def _fetch_text(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": SOURCE_ADMISSION_USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def _plain_text(html: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", text).strip()


def _strip_html(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(value))).strip()


def _html_table_rows(table_html: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for row_html in re.findall(r"<tr.*?</tr>", table_html, re.DOTALL | re.IGNORECASE):
        cells = [
            _strip_html(cell_html)
            for cell_html in re.findall(
                r"<t[dh][^>]*>(.*?)</t[dh]>",
                row_html,
                re.DOTALL | re.IGNORECASE,
            )
        ]
        if cells:
            rows.append(cells)
    return rows


def _clean_source_text(value: str) -> str:
    cleaned = re.sub(r"<!--.*?-->", " ", value, flags=re.DOTALL)
    cleaned = re.sub(r"<br\s*/?>", " ", cleaned, flags=re.IGNORECASE)
    cleaned = _strip_html(cleaned)
    cleaned = cleaned.replace("$$", "")
    cleaned = cleaned.replace("\\", "")
    cleaned = cleaned.replace("\xa0", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def _posted_date(text: str) -> str:
    match = re.search(r"Updated ([A-Za-z]+ \d{4})", text)
    return match.group(1) if match else ""


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    strings: list[str] = []
    for item in root.findall("x:si", ns):
        strings.append("".join(node.text or "" for node in item.findall(".//x:t", ns)))
    return strings


def _column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char.upper()) - ord("A") + 1)
    return index


def _column_letters(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def _sheet_values(path: Path, sheet_path: str) -> dict[tuple[int, int], str]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        shared = _shared_strings(archive)
        root = ET.fromstring(archive.read(sheet_path))
    values: dict[tuple[int, int], str] = {}
    for row in root.findall(".//x:sheetData/x:row", ns):
        row_index = int(row.attrib["r"])
        for cell in row.findall("x:c", ns):
            value_node = cell.find("x:v", ns)
            if value_node is None:
                continue
            raw_value = value_node.text or ""
            value = shared[int(raw_value)] if cell.attrib.get("t") == "s" else raw_value
            values[(row_index, _column_index(cell.attrib["r"]))] = value.strip()
    return values


def _worksheet_paths(path: Path) -> dict[str, str]:
    ns = {
        "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relmap = {
        relationship.attrib["Id"]: relationship.attrib["Target"]
        for relationship in relationships.findall("rel:Relationship", ns)
    }
    sheets: dict[str, str] = {}
    for sheet in workbook.findall("x:sheets/x:sheet", ns):
        sheet_name = sheet.attrib["name"]
        rel_id = sheet.attrib[
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        ]
        target = relmap[rel_id].lstrip("/")
        if target.startswith("worksheets/"):
            sheets[sheet_name] = f"xl/{target}"
    return sheets


def _nyfed_hhdc_unit(cells: Mapping[tuple[int, int], str], title: str) -> str:
    for row_index in range(2, 5):
        value = cells.get((row_index, 1), "").strip()
        if not value:
            continue
        lower = value.lower()
        if lower.startswith(("return to", "source:", "note:", "*")):
            continue
        if value == title:
            continue
        return value
    if "Riskscore" in title:
        return "risk_score_index"
    return "source_table_specific_unit"


def _nyfed_hhdc_header_row(
    cells: Mapping[tuple[int, int], str], *, max_row: int, max_column: int
) -> int:
    best: tuple[int, int] | None = None
    for row_index in range(3, min(max_row, 8) + 1):
        row_values = [
            cells.get((row_index, column_index), "")
            for column_index in range(1, min(max_column, 20) + 1)
        ]
        nonblank = [value for value in row_values if value]
        if len(nonblank) < 2:
            continue
        if any(
            value.lower().startswith(("return to", "source:", "note:"))
            for value in nonblank
        ):
            continue
        score = len(nonblank)
        if row_values[0].lower() in {"", "quarter"}:
            score += 3
        if best is None or score > best[0]:
            best = (score, row_index)
    if best is None:
        raise ValueError("NY Fed household-debt workbook table header not found")
    return best[1]


def _quarter_end(year: int, quarter: int) -> str:
    month = quarter * 3
    next_month = date(year + (month // 12), (month % 12) + 1, 1)
    return (next_month - timedelta(days=1)).isoformat()


def _nyfed_hhdc_period(value: str) -> tuple[str, str]:
    value = value.strip()
    quarter_match = re.fullmatch(r"(\d{2}|\d{4}):?Q([1-4])", value)
    if quarter_match:
        raw_year = int(quarter_match.group(1))
        year = (
            raw_year
            if raw_year >= 100
            else (2000 + raw_year if raw_year < 50 else 1900 + raw_year)
        )
        quarter = int(quarter_match.group(2))
        return _quarter_end(year, quarter), f"{year}:Q{quarter}"
    if re.fullmatch(r"\d+(?:\.0+)?", value):
        serial = int(float(value))
        if 30000 <= serial <= 60000:
            observed_date = date(1899, 12, 30) + timedelta(days=serial)
            quarter = (observed_date.month - 1) // 3 + 1
            return observed_date.isoformat(), f"{observed_date.year}:Q{quarter}"
    return "", ""


def _nyfed_hhdc_snapshot_period(title: str) -> tuple[str, str]:
    match = re.search(r"\((\d{4})\s*Q([1-4])\)", title)
    if not match:
        return "", ""
    year = int(match.group(1))
    quarter = int(match.group(2))
    return _quarter_end(year, quarter), f"{year}:Q{quarter}"


def _nyfed_hhdc_records(path: Path) -> list[dict[str, str]]:
    worksheets = _worksheet_paths(path)
    missing = [
        sheet_name
        for sheet_name in NYFED_HOUSEHOLD_DEBT_CREDIT_EXPECTED_TITLES
        if sheet_name not in worksheets
    ]
    if missing:
        raise ValueError(
            "NY Fed household-debt workbook missing expected data sheets: "
            + "; ".join(missing)
        )

    records: list[dict[str, str]] = []
    parsed_sheet_count = 0
    for sheet_name, sheet_path in worksheets.items():
        if not sheet_name.startswith("Page ") or not sheet_name.endswith(" Data"):
            continue
        cells = _sheet_values(path, sheet_path)
        title = cells.get((1, 1), "")
        expected_title = NYFED_HOUSEHOLD_DEBT_CREDIT_EXPECTED_TITLES.get(sheet_name)
        if expected_title is not None and title != expected_title:
            raise ValueError(
                "NY Fed household-debt workbook missing expected title "
                f"{sheet_name}: {expected_title}"
            )
        max_row = max(row for row, _ in cells)
        max_column = max(column for _, column in cells)
        header_row = _nyfed_hhdc_header_row(
            cells, max_row=max_row, max_column=max_column
        )
        metric_unit = _nyfed_hhdc_unit(cells, title)
        snapshot_date, snapshot_period = _nyfed_hhdc_snapshot_period(title)
        headers = {
            column_index: cells.get((header_row, column_index), "")
            for column_index in range(2, max_column + 1)
            if cells.get((header_row, column_index), "")
        }
        parsed_sheet_count += 1
        for row_index in range(header_row + 1, max_row + 1):
            row_key = cells.get((row_index, 1), "")
            if not row_key:
                continue
            if row_key.lower().startswith(("return to", "source:", "note:", "*")):
                continue
            row_date, row_period = _nyfed_hhdc_period(row_key)
            for column_index, column_label in headers.items():
                metric_value = cells.get((row_index, column_index), "")
                if metric_value == "":
                    continue
                column_date, column_period = _nyfed_hhdc_period(column_label)
                observation_date = row_date or column_date or snapshot_date
                observation_period = row_period or column_period or snapshot_period
                period_source = (
                    "row_key"
                    if row_date
                    else "column_label"
                    if column_date
                    else "title_snapshot"
                    if snapshot_date
                    else "not_date_specific"
                )
                records.append(
                    {
                        "date": observation_date,
                        "period": observation_period,
                        "period_source": period_source,
                        "source_sheet_name": sheet_name,
                        "source_sheet_path": sheet_path,
                        "source_table_title": title,
                        "source_table_unit": metric_unit,
                        "row_key": row_key,
                        "column_label": column_label,
                        "source_cell": f"{_column_letters(column_index)}{row_index}",
                        "metric_value": _normalize_source_number(metric_value),
                        "metric_unit": metric_unit,
                        "source_workbook_schema_reviewed": "true",
                        "product_balance_context_available": "true",
                        "age_distribution_context_available": "true",
                        "state_distribution_context_available": "true",
                        "delinquency_transition_context_available": "true",
                        "borrower_level_microdata_available": "false",
                        "income_distribution_available": "false",
                        "current_demand_conversion_available": "false",
                        "denominator_prior_narrowing_allowed": "false",
                        "split_denominator_promotion_allowed": "false",
                        "formula_replacement_allowed": "false",
                        "main_ratio_admission_allowed": "false",
                        "incidence_output_enabled": "false",
                        "welfare_tax_mpc_output_enabled": "false",
                    }
                )

    if parsed_sheet_count != 36:
        raise ValueError(
            "NY Fed household-debt workbook parsed unexpected data-sheet count: "
            f"{parsed_sheet_count}"
        )
    return records


def _normalize_source_number(value: str) -> str:
    if value == "":
        return ""
    if re.fullmatch(r"-?\d+(?:\.\d+)?(?:E-?\d+)?", value, flags=re.IGNORECASE):
        normalized = f"{float(value):.6f}".rstrip("0").rstrip(".")
        return "0" if normalized == "-0" else normalized
    return value


def _append_score_product_rows(
    records: list[dict[str, str]],
    *,
    cells: Mapping[tuple[int, int], str],
    row_range: range,
    metric: str,
    date_value: str,
    source_section: str,
    metric_unit: str,
    product_columns: Mapping[int, str],
) -> None:
    for row_index in row_range:
        credit_score_tier = cells[(row_index, 1)]
        for column, card_type in product_columns.items():
            records.append(
                {
                    "date": date_value,
                    "report_year": "2025",
                    "source_section": source_section,
                    "metric": metric,
                    "payment_band": "",
                    "credit_score_tier": credit_score_tier,
                    "card_type": card_type,
                    "metric_value": _normalize_source_number(
                        cells[(row_index, column)]
                    ),
                    "metric_unit": metric_unit,
                }
            )


def _append_grouped_share_rows(
    records: list[dict[str, str]],
    *,
    cells: Mapping[tuple[int, int], str],
    row_range: range,
    metric: str,
    date_value: str,
    source_section: str,
    metric_unit: str,
    group_field: str,
    group_columns: Mapping[int, str],
) -> None:
    for row_index in row_range:
        credit_score_tier = cells[(row_index, 1)]
        for column, group_value in group_columns.items():
            record = {
                "date": date_value,
                "report_year": "2025",
                "source_section": source_section,
                "metric": metric,
                "payment_band": "",
                "credit_score_tier": credit_score_tier,
                "card_type": "general_purpose",
                "metric_value": _normalize_source_number(cells[(row_index, column)]),
                "metric_unit": metric_unit,
            }
            record[group_field] = group_value
            records.append(record)


def _cfpb_payment_behavior_records(path: Path) -> list[dict[str, str]]:
    cells = _sheet_values(path, CFPB_CREDIT_CARD_PAYMENT_BEHAVIOR_SHEET)
    expected_markers = {
        (1, 1): "Section 4 - Payments, debt, and collections",
        (59, 1): "ANNUAL SHARE OF ACCOUNTS BY PAYMENT AMOUNT (Y-14)",
        (73, 1): "SHARE OF ACCOUNTS MAKING JUST THE MINIMUM PAYMENT DUE, 2024 (Y-14+)",
        (84, 1): "AVERAGE MINIMUM PAYMENT DUE, REVOLVING ACCOUNTS, 2024 (Y-14+)",
        (179, 1): "SHARE OF ACTIVE ACCOUNTS REVOLVING, 2024 (Y-14+)",
    }
    for cell, expected in expected_markers.items():
        if cells.get(cell) != expected:
            raise ValueError(
                f"CFPB credit-card workbook missing expected marker {cell}: {expected}"
            )

    records: list[dict[str, str]] = []
    for row_index in range(61, 71):
        year = cells[(row_index, 1)]
        for column, payment_band in {
            2: "less_than_10_percent_of_total_balance",
            3: "at_least_10_percent_but_less_than_total_balance",
            4: "total_balance",
        }.items():
            records.append(
                {
                    "date": f"{year}-12-31",
                    "report_year": "2025",
                    "source_section": "section_4_payments_debt_collections",
                    "metric": "annual_share_of_accounts_by_payment_amount",
                    "payment_band": payment_band,
                    "credit_score_tier": "all",
                    "card_type": "all_y14",
                    "metric_value": _normalize_source_number(
                        cells[(row_index, column)]
                    ),
                    "metric_unit": "share",
                }
            )

    for row_index in range(75, 82):
        credit_score_tier = cells[(row_index, 1)]
        for column, card_type in {2: "general_purpose", 3: "private_label"}.items():
            records.append(
                {
                    "date": "2024-12-31",
                    "report_year": "2025",
                    "source_section": "section_4_payments_debt_collections",
                    "metric": "share_accounts_just_minimum_payment_due_2024",
                    "payment_band": "just_minimum_payment_due",
                    "credit_score_tier": credit_score_tier,
                    "card_type": card_type,
                    "metric_value": _normalize_source_number(
                        cells[(row_index, column)]
                    ),
                    "metric_unit": "share",
                }
            )

    for row_index in range(86, 93):
        credit_score_tier = cells[(row_index, 1)]
        for column, card_type in {2: "general_purpose", 3: "private_label"}.items():
            records.append(
                {
                    "date": "2024-12-31",
                    "report_year": "2025",
                    "source_section": "section_4_payments_debt_collections",
                    "metric": "average_minimum_payment_due_revolving_accounts_2024",
                    "payment_band": "minimum_payment_due",
                    "credit_score_tier": credit_score_tier,
                    "card_type": card_type,
                    "metric_value": _normalize_source_number(
                        cells[(row_index, column)]
                    ),
                    "metric_unit": "dollars",
                }
            )

    for row_index in range(181, 187):
        credit_score_tier = cells[(row_index, 1)]
        for column, card_type in {2: "general_purpose", 3: "private_label"}.items():
            records.append(
                {
                    "date": "2024-12-31",
                    "report_year": "2025",
                    "source_section": "section_4_payments_debt_collections",
                    "metric": "share_active_accounts_revolving_2024",
                    "payment_band": "revolving_balance",
                    "credit_score_tier": credit_score_tier,
                    "card_type": card_type,
                    "metric_value": _normalize_source_number(
                        cells[(row_index, column)]
                    ),
                    "metric_unit": "share",
                }
            )

    for record in records:
        record.update(
            {
                "source_workbook_schema_reviewed": "true",
                "minimum_payment_behavior_context_available": "true",
                "credit_score_tier_context_available": "true",
                "borrower_level_microdata_available": "false",
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


def _cfpb_use_of_credit_records(path: Path) -> list[dict[str, str]]:
    cells = _sheet_values(path, CFPB_CREDIT_CARD_USE_OF_CREDIT_SHEET)
    expected_markers = {
        (1, 1): "Section 2 - Use of credit",
        (151, 1): "CREDIT CARD CONSUMERS, YEAR-END 2023 (CCIP)",
        (
            161,
            1,
        ): (
            "SHARE OF SCORED CONSUMERS BY NUMBER OF CREDIT CARD ACCOUNTS "
            "BY CREDIT SCORE TIER, YEAR-END 2023 (CCIP)"
        ),
        (
            958,
            1,
        ): "AVERAGE PER-ACCOUNT CYCLE-ENDING BALANCES, YEAR-END 2024 (CCIP)",
    }
    for cell, expected in expected_markers.items():
        if cells.get(cell) != expected:
            raise ValueError(
                f"CFPB credit-card workbook missing expected marker {cell}: {expected}"
            )

    records: list[dict[str, str]] = []
    _append_score_product_rows(
        records,
        cells=cells,
        row_range=range(153, 159),
        metric="credit_card_consumers_year_end_2023",
        date_value="2023-12-31",
        source_section="section_2_use_of_credit",
        metric_unit="count",
        product_columns={2: "general_purpose", 3: "private_label"},
    )
    _append_grouped_share_rows(
        records,
        cells=cells,
        row_range=range(163, 170),
        metric="share_scored_consumers_by_number_of_credit_card_accounts_2023",
        date_value="2023-12-31",
        source_section="section_2_use_of_credit",
        metric_unit="share",
        group_field="account_count_group",
        group_columns={
            2: "one_account",
            3: "two_accounts",
            4: "three_or_more",
            5: "none",
        },
    )
    _append_score_product_rows(
        records,
        cells=cells,
        row_range=range(960, 967),
        metric="average_per_account_cycle_ending_balances_2024",
        date_value="2024-12-31",
        source_section="section_2_use_of_credit",
        metric_unit="dollars",
        product_columns={2: "general_purpose", 3: "private_label"},
    )
    return records


def _cfpb_cost_of_credit_records(path: Path) -> list[dict[str, str]]:
    cells = _sheet_values(path, CFPB_CREDIT_CARD_COST_OF_CREDIT_SHEET)
    expected_markers = {
        (1, 1): "Section 3 - Cost of credit",
        (
            49,
            1,
        ): (
            "ANNUAL TOTAL COST OF CREDIT, AS A SHARE OF CYCLE-ENDING "
            "BALANCES, REVOLVING ACCOUNTS, 2024 (Y-14+)"
        ),
        (280, 1): "ANNUAL EFFECTIVE INTEREST RATE, REVOLVING ACCOUNTS, 2024 (Y-14+)",
        (
            437,
            1,
        ): (
            "SHARE OF GENERAL PURPOSE CREDIT CARDS ORIGINATED WITH AN "
            "INTRODUCTORY PROMOTIONAL INTEREST RATE BY ORIGINATION CREDIT "
            "SCORE (Y-14)"
        ),
        (
            609,
            1,
        ): (
            "SHARE OF GENERAL PURPOSE CREDIT CARD ACCOUNTS REVOLVING A "
            "BALANCE BY ORIGINATION CREDIT SCORE (Y-14)"
        ),
        (
            617,
            1,
        ): (
            "AVERAGE INTEREST CHARGED TO GENERAL PURPOSE CREDIT CARDS IN THE "
            "FIRST THREE YEARS AFTER ORIGINATION BY ORIGINATION CREDIT SCORE "
            "(Y-14)"
        ),
    }
    for cell, expected in expected_markers.items():
        if cells.get(cell) != expected:
            raise ValueError(
                f"CFPB credit-card workbook missing expected marker {cell}: {expected}"
            )

    records: list[dict[str, str]] = []
    _append_score_product_rows(
        records,
        cells=cells,
        row_range=range(51, 58),
        metric="annual_total_cost_of_credit_share_revolving_accounts_2024",
        date_value="2024-12-31",
        source_section="section_3_cost_of_credit",
        metric_unit="share",
        product_columns={2: "general_purpose", 3: "private_label"},
    )
    _append_score_product_rows(
        records,
        cells=cells,
        row_range=range(282, 289),
        metric="annual_effective_interest_rate_revolving_accounts_2024",
        date_value="2024-12-31",
        source_section="section_3_cost_of_credit",
        metric_unit="share",
        product_columns={2: "general_purpose", 3: "private_label"},
    )
    for row_index in range(439, 443):
        records.append(
            {
                "date": "2024-12-31",
                "report_year": "2025",
                "source_section": "section_3_cost_of_credit",
                "metric": "share_originated_with_introductory_promo_interest_rate",
                "payment_band": "",
                "credit_score_tier": cells[(row_index, 1)],
                "card_type": "general_purpose",
                "metric_value": _normalize_source_number(cells[(row_index, 2)]),
                "metric_unit": "share",
            }
        )
    _append_grouped_share_rows(
        records,
        cells=cells,
        row_range=range(611, 615),
        metric="share_accounts_revolving_balance_by_origination_score",
        date_value="2024-12-31",
        source_section="section_3_cost_of_credit",
        metric_unit="share",
        group_field="promotion_status",
        group_columns={
            2: "non_promotional_accounts",
            3: "promotional_accounts_month_after_promotion_end",
        },
    )
    _append_grouped_share_rows(
        records,
        cells=cells,
        row_range=range(619, 623),
        metric="average_interest_charged_first_three_years_after_origination",
        date_value="2024-12-31",
        source_section="section_3_cost_of_credit",
        metric_unit="dollars",
        group_field="promotion_status",
        group_columns={2: "no_introductory_promotion", 3: "introductory_promotion"},
    )
    return records


def _cfpb_availability_of_credit_records(path: Path) -> list[dict[str, str]]:
    cells = _sheet_values(path, CFPB_CREDIT_CARD_AVAILABILITY_SHEET)
    expected_markers = {
        (1, 1): "Section 6 - Availability of credit",
        (58, 1): "APPROVAL RATE BY CREDIT SCORE TIER, 2024 (MMI)",
        (527, 1): "AVERAGE APR ON NEW ACCOUNTS, GENERAL PURPOSE (Y-14)",
        (
            610,
            1,
        ): "AVERAGE UTILIZATION RATE BY CREDIT SCORE TIER, GENERAL PURPOSE (CCIP)",
    }
    for cell, expected in expected_markers.items():
        if cells.get(cell) != expected:
            raise ValueError(
                f"CFPB credit-card workbook missing expected marker {cell}: {expected}"
            )

    records: list[dict[str, str]] = []
    _append_score_product_rows(
        records,
        cells=cells,
        row_range=range(60, 66),
        metric="approval_rate_by_credit_score_tier_2024",
        date_value="2024-12-31",
        source_section="section_6_availability_of_credit",
        metric_unit="share",
        product_columns={2: "general_purpose", 3: "private_label"},
    )
    for row_index in range(529, 539):
        credit_score_tier = cells[(row_index, 1)]
        for column, year in {2: "2014", 3: "2024"}.items():
            records.append(
                {
                    "date": f"{year}-12-31",
                    "report_year": "2025",
                    "source_section": "section_6_availability_of_credit",
                    "metric": "average_apr_on_new_accounts_general_purpose",
                    "payment_band": "",
                    "credit_score_tier": credit_score_tier,
                    "card_type": "general_purpose",
                    "metric_value": _normalize_source_number(
                        cells[(row_index, column)]
                    ),
                    "metric_unit": "share",
                }
            )
    utilization_columns = {
        2: "Superprime",
        3: "Prime plus",
        4: "Prime",
        5: "Near-prime",
        6: "Subprime",
        7: "Deep subprime",
        8: "Overall",
    }
    for row_index in range(612, 622):
        year = cells[(row_index, 1)]
        for column, credit_score_tier in utilization_columns.items():
            records.append(
                {
                    "date": f"{year}-12-31",
                    "report_year": "2025",
                    "source_section": "section_6_availability_of_credit",
                    "metric": "average_utilization_rate_by_credit_score_tier",
                    "payment_band": "",
                    "credit_score_tier": credit_score_tier,
                    "card_type": "general_purpose",
                    "metric_value": _normalize_source_number(
                        cells[(row_index, column)]
                    ),
                    "metric_unit": "share",
                }
            )
    return records


def _cfpb_credit_card_context_records(path: Path) -> list[dict[str, str]]:
    records = [
        *_cfpb_use_of_credit_records(path),
        *_cfpb_cost_of_credit_records(path),
        *_cfpb_payment_behavior_records(path),
        *_cfpb_availability_of_credit_records(path),
    ]
    for record in records:
        record.update(
            {
                "source_workbook_schema_reviewed": "true",
                "payment_behavior_context_available": "true",
                "balance_by_credit_score_context_available": "true",
                "repricing_context_available": "true",
                "approval_rate_context_available": "true",
                "utilization_context_available": "true",
                "borrower_level_microdata_available": "false",
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


def _cfpb_credit_card_payment_behavior_snapshot(
    *, registry: SourceRegistry, source_workbook: Path
) -> SourceSnapshot:
    series = registry.series[CFPB_CREDIT_CARD_FIGURE_DATA_SERIES_ID]
    if not source_workbook.exists():
        _download_source(series.endpoint, source_workbook)
    records = _cfpb_credit_card_context_records(source_workbook)
    workbook_hash = _file_sha256(source_workbook)
    record_hash = _records_sha256(records)
    note = (
        "cfpb_credit_card_market_payment_balance_repricing_utilization_context_only;"
        f"source_workbook_sha256={workbook_hash};"
        f"source_records_sha256={record_hash};"
        f"source_record_count={len(records)};"
        "report_year=2025;"
        "data_years=2014-2024;"
        "minimum_payment_behavior_context_available=true;"
        "payment_behavior_context_available=true;"
        "credit_score_tier_context_available=true;"
        "balance_by_credit_score_context_available=true;"
        "repricing_context_available=true;"
        "approval_rate_context_available=true;"
        "utilization_context_available=true;"
        "borrower_level_microdata_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2025-12-30",
            snapshot_kind="live_workbook_context",
            note=note,
        ),
        records=records,
    )


def _cfpb_consumer_credit_trends_records(path: Path) -> list[dict[str, str]]:
    records = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    expected_columns = {
        "month",
        "date",
        "series",
        "subgroup",
        "subgroup_level",
        "loan_type",
        "value_type",
        "value",
        "value_yoy",
    }
    if not records:
        raise ValueError(f"{path} contains no CFPB Consumer Credit Trends rows")
    missing = expected_columns - set(records[0])
    if missing:
        raise ValueError(
            f"{path} missing CFPB Consumer Credit Trends columns: "
            f"{', '.join(sorted(missing))}"
        )
    normalized_records: list[dict[str, str]] = []
    for index, row in enumerate(records, start=2):
        observed_month = row["date"].strip()
        if not re.fullmatch(r"\d{4}-\d{2}", observed_month):
            raise ValueError(
                f"{path} row {index} has invalid monthly date: {observed_month}"
            )
        subgroup = row["subgroup"].strip()
        normalized_records.append(
            {
                "date": f"{observed_month}-01",
                "source_row_index_one_based": str(index),
                "source_month_index": row["month"].strip(),
                "source_month": observed_month,
                "series": row["series"].strip(),
                "subgroup": subgroup,
                "subgroup_level": row["subgroup_level"].strip(),
                "loan_type": row["loan_type"].strip(),
                "value_type": row["value_type"].strip(),
                "metric_value": _normalize_source_number(row["value"].strip()),
                "metric_value_yoy": _normalize_source_number(row["value_yoy"].strip()),
                "source_csv_schema_reviewed": "true",
                "product_distribution_context_available": "true",
                "credit_score_distribution_context_available": str(
                    subgroup == "score"
                ).lower(),
                "income_distribution_context_available": str(
                    subgroup == "income"
                ).lower(),
                "age_distribution_context_available": str(subgroup == "age").lower(),
                "borrower_level_microdata_available": "false",
                "liquidity_context_available": "false",
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
    return normalized_records


def _cfpb_consumer_credit_trends_codebook_records(
    path: Path,
) -> list[dict[str, str]]:
    worksheets = _worksheet_paths(path)
    expected_sheets = {
        "data dict for all_data.csv": (
            ("field_name", "field_description", "valid_values"),
            "all_data_csv_field",
        ),
        "data dict for indiv CSV files": (
            ("field_name", "field_description", "valid_values"),
            "individual_csv_field",
        ),
        "codebook": (
            ("subgroup", "subgroup_level", "definition"),
            "subgroup_level",
        ),
    }
    missing_sheets = set(expected_sheets) - set(worksheets)
    if missing_sheets:
        raise ValueError(
            f"{path} missing CFPB Consumer Credit Trends codebook sheets: "
            f"{', '.join(sorted(missing_sheets))}"
        )

    records: list[dict[str, str]] = []
    for sheet_name, (expected_headers, row_kind) in expected_sheets.items():
        cells = _sheet_values(path, worksheets[sheet_name])
        header_values = tuple(
            cells.get((1, col), "").strip()
            for col in range(1, len(expected_headers) + 1)
        )
        if header_values != expected_headers:
            raise ValueError(
                f"{path} sheet {sheet_name} has unexpected CFPB Consumer Credit "
                f"Trends codebook headers: {header_values!r}"
            )
        max_row = max((row for row, _ in cells), default=0)
        for row_index in range(2, max_row + 1):
            values = [
                cells.get((row_index, col), "").strip()
                for col in range(1, len(expected_headers) + 1)
            ]
            if not any(values):
                continue
            row = dict(zip(expected_headers, values, strict=True))
            records.append(
                {
                    "source_sheet_name": sheet_name,
                    "source_sheet_path": worksheets[sheet_name],
                    "source_row_index_one_based": str(row_index),
                    "row_kind": row_kind,
                    "field_name": row.get("field_name", ""),
                    "field_description": row.get("field_description", ""),
                    "valid_values": row.get("valid_values", ""),
                    "subgroup": row.get("subgroup", ""),
                    "subgroup_level": row.get("subgroup_level", ""),
                    "definition": row.get("definition", ""),
                    "source_workbook_schema_reviewed": "true",
                    "product_distribution_context_available": "true",
                    "credit_score_distribution_context_available": "true",
                    "income_distribution_context_available": "true",
                    "age_distribution_context_available": "true",
                    "borrower_level_microdata_available": "false",
                    "liquidity_context_available": "false",
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
    if not records:
        raise ValueError(
            f"{path} contains no CFPB Consumer Credit Trends codebook rows"
        )
    return records


def _cfpb_consumer_credit_trends_codebook_snapshot(
    *, registry: SourceRegistry, source_workbook: Path
) -> SourceSnapshot:
    series = registry.series[CFPB_CONSUMER_CREDIT_TRENDS_CODEBOOK_SERIES_ID]
    if not source_workbook.exists():
        _download_source(series.endpoint, source_workbook)
    records = _cfpb_consumer_credit_trends_codebook_records(source_workbook)
    workbook_hash = _file_sha256(source_workbook)
    records_hash = _records_sha256(records)
    sheet_names = sorted({record["source_sheet_name"] for record in records})
    row_kinds = sorted({record["row_kind"] for record in records})
    note = (
        "cfpb_consumer_credit_trends_schema_context_only;"
        f"source_workbook_sha256={workbook_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"source_sheet_count={len(sheet_names)};"
        f"source_sheets={','.join(sheet_names)};"
        f"row_kinds={','.join(row_kinds)};"
        "schema=field_name,field_description,valid_values,subgroup,"
        "subgroup_level,definition;"
        "borrower_level_microdata_available=false;"
        "liquidity_context_available=false;"
        "payment_behavior_context_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="codebook_specific",
            snapshot_kind="live_workbook_context",
            note=note,
        ),
        records=records,
    )


def _cfpb_consumer_credit_trends_snapshot(
    *, registry: SourceRegistry, source_csv: Path, codebook: Path
) -> SourceSnapshot:
    series = registry.series[CFPB_CONSUMER_CREDIT_TRENDS_ALL_DATA_SERIES_ID]
    codebook_series = registry.series[CFPB_CONSUMER_CREDIT_TRENDS_CODEBOOK_SERIES_ID]
    if not source_csv.exists():
        _download_source(series.endpoint, source_csv)
    if not codebook.exists():
        _download_source(codebook_series.endpoint, codebook)
    records = _cfpb_consumer_credit_trends_records(source_csv)
    source_csv_hash = _file_sha256(source_csv)
    codebook_hash = _file_sha256(codebook)
    records_hash = _records_sha256(records)
    source_rows = list(csv.DictReader(source_csv.open(encoding="utf-8", newline="")))
    first_source_month = min(row["date"] for row in source_rows)
    latest_source_month = max(row["date"] for row in source_rows)
    subgroup_values = sorted({row["subgroup"] for row in source_rows})
    loan_types = sorted({row["loan_type"] for row in source_rows})
    series_values = sorted({row["series"] for row in source_rows})
    note = (
        "cfpb_consumer_credit_trends_product_score_income_age_context_only;"
        f"source_csv_sha256={source_csv_hash};"
        f"source_codebook_sha256={codebook_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_month={first_source_month};"
        f"latest_observation_month={latest_source_month};"
        f"subgroups={','.join(subgroup_values)};"
        f"loan_types={','.join(loan_types)};"
        f"series={','.join(series_values)};"
        "schema=month,date,series,subgroup,subgroup_level,loan_type,value_type,value,value_yoy;"
        "product_distribution_context_available=true;"
        "credit_score_distribution_context_available=true;"
        "income_distribution_context_available=true;"
        "age_distribution_context_available=true;"
        "borrower_level_microdata_available=false;"
        "liquidity_context_available=false;"
        "payment_behavior_context_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at=latest_source_month,
            snapshot_kind="live_csv_context",
            note=note,
        ),
        records=records,
    )


def _tccp_apr_pct(value: str) -> str:
    normalized = _normalize_source_number(value.strip())
    if normalized == "":
        return ""
    try:
        raw_value = float(normalized)
        pct_value = raw_value * 100.0 if abs(raw_value) <= 1.0 else raw_value
        return _normalize_source_number(str(pct_value))
    except ValueError:
        return normalized


def _cfpb_tccp_survey_records(path: Path) -> list[dict[str, str]]:
    cells = _sheet_values(path, CFPB_TCCP_SURVEY_SHEET)
    headers = {
        col: cells.get((10, col), "").strip()
        for col in range(1, max(col for _, col in cells) + 1)
        if cells.get((10, col), "").strip()
    }
    header_to_col = {header: col for col, header in headers.items()}
    missing = set(CFPB_TCCP_REQUIRED_HEADERS) - set(header_to_col)
    if missing:
        raise ValueError(
            f"{path} missing CFPB TCCP columns: {', '.join(sorted(missing))}"
        )

    def cell(row: int, header: str) -> str:
        return cells.get((row, header_to_col[header]), "").strip()

    records: list[dict[str, str]] = []
    max_row = max(row for row, _ in cells)
    for row_index in range(11, max_row + 1):
        institution = cell(row_index, "Institution Name")
        product = cell(row_index, "Product Name")
        if not institution and not product:
            continue
        index_kind = cell(row_index, "Index")
        purchase_apr_index = cell(row_index, "Purchase APR Index")
        variable_rate_index = cell(row_index, "Variable Rate Index")
        variable_rate_context = str(
            index_kind.upper() == "V"
            or purchase_apr_index.lower() == "yes"
            or bool(variable_rate_index)
        ).lower()
        records.append(
            {
                "date": "2025-06-30",
                "reporting_period_start": "2025-01-01",
                "reporting_period_end": "2025-06-30",
                "source_row_index_one_based": str(row_index),
                "institution_name": institution,
                "issued_by_top_25_institution": cell(
                    row_index, "Issued by Top 25 Institution"
                ),
                "product_name": product,
                "source_report_date": cell(row_index, "Report Date"),
                "availability_of_credit_card_plan": cell(
                    row_index, "Availability of Credit Card Plan"
                ),
                "secured_card": cell(row_index, "Secured Card"),
                "targeted_credit_tiers": cell(row_index, "Targeted Credit Tiers"),
                "purchase_apr_offered": cell(row_index, "Purchase APR Offered?"),
                "purchase_apr_tied_to_index": purchase_apr_index,
                "variable_rate_index": variable_rate_index,
                "fixed_or_variable_index": index_kind,
                "purchase_apr_vary_by_credit_tier": cell(
                    row_index, "Purchase APR Vary by Credit Tier"
                ),
                "purchase_apr_no_score_pct": _tccp_apr_pct(
                    cell(row_index, "Purchase APR no score")
                ),
                "purchase_apr_poor_pct": _tccp_apr_pct(
                    cell(row_index, "Purchase APR poor")
                ),
                "purchase_apr_good_pct": _tccp_apr_pct(
                    cell(row_index, "Purchase APR good")
                ),
                "purchase_apr_great_pct": _tccp_apr_pct(
                    cell(row_index, "Purchase APR great")
                ),
                "purchase_apr_min_pct": _tccp_apr_pct(
                    cell(row_index, "Purchase APR min")
                ),
                "purchase_apr_median_pct": _tccp_apr_pct(
                    cell(row_index, "Purchase APR median")
                ),
                "purchase_apr_max_pct": _tccp_apr_pct(
                    cell(row_index, "Purchase APR max")
                ),
                "grace_period_offered": cell(row_index, "Grace Period Offered?"),
                "grace_period_days": _normalize_source_number(
                    cell(row_index, "Grace Period")
                ),
                "source_workbook_schema_reviewed": "true",
                "apr_unit_review_status": (
                    "workbook_decimal_fraction_converted_to_percentage_points"
                ),
                "credit_card_plan_terms_context_available": "true",
                "rate_sensitive_pricing_terms_context_available": "true",
                "fixed_variable_apr_context_available": "true",
                "variable_rate_index_context_available": variable_rate_context,
                "credit_score_tier_pricing_context_available": str(
                    cell(row_index, "Purchase APR Vary by Credit Tier").lower() == "yes"
                    or any(
                        cell(row_index, header)
                        for header in (
                            "Purchase APR no score",
                            "Purchase APR poor",
                            "Purchase APR good",
                            "Purchase APR great",
                        )
                    )
                ).lower(),
                "borrower_level_microdata_available": "false",
                "payment_behavior_context_available": "false",
                "current_demand_conversion_available": "false",
                "rate_sensitive_payment_drag_transmission_available": "false",
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    if not records:
        raise ValueError(f"{path} contains no CFPB TCCP product rows")
    return records


def _cfpb_tccp_survey_snapshot(
    *, registry: SourceRegistry, source_workbook: Path
) -> SourceSnapshot:
    series = registry.series[CFPB_TCCP_SURVEY_SERIES_ID]
    if not source_workbook.exists():
        _download_source(series.endpoint, source_workbook)
    records = _cfpb_tccp_survey_records(source_workbook)
    workbook_hash = _file_sha256(source_workbook)
    record_hash = _records_sha256(records)
    variable_count = sum(
        1
        for record in records
        if record["variable_rate_index_context_available"] == "true"
    )
    fixed_count = sum(
        1 for record in records if record["fixed_or_variable_index"].upper() == "F"
    )
    note = (
        "cfpb_tccp_credit_card_plan_terms_repricing_context_only;"
        f"source_workbook_sha256={workbook_hash};"
        f"source_records_sha256={record_hash};"
        f"source_record_count={len(records)};"
        "reporting_period_start=2025-01-01;"
        "reporting_period_end=2025-06-30;"
        f"variable_rate_or_indexed_product_count={variable_count};"
        f"fixed_rate_product_count={fixed_count};"
        "schema=product_level_purchase_apr_index_fixed_variable_credit_tier_and_grace_period_terms;"
        "apr_unit_review_status=workbook_decimal_fraction_converted_to_percentage_points;"
        "rate_sensitive_pricing_terms_context_available=true;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "borrower_level_microdata_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2025-06-30",
            snapshot_kind="live_workbook_context",
            note=note,
        ),
        records=records,
    )


def _cfpb_payment_amount_furnishing_records(text: str) -> list[dict[str, str]]:
    normalized = re.sub(r"\s+", " ", text.replace(",", "")).strip()
    marker_text = normalized.lower()
    missing = [
        marker
        for marker in CFPB_PAYMENT_AMOUNT_FURNISHING_MARKERS
        if marker.lower() not in marker_text
    ]
    if missing:
        raise ValueError(
            "CFPB payment amount furnishing report missing expected markers: "
            + "; ".join(missing)
        )
    records: list[dict[str, str]] = []
    for loan_type, (
        tradelines_mil,
        recent_payment_mil,
        actual_payment_pct,
    ) in CFPB_PAYMENT_AMOUNT_FURNISHING_TABLE_VALUES.items():
        loan_pattern = re.escape(loan_type).replace(r"\ ", r"\s+")
        pattern = (
            rf"{loan_pattern}\s+{tradelines_mil}\s+"
            rf"{recent_payment_mil}\s+{actual_payment_pct}%"
        )
        if re.search(pattern, normalized) is None:
            raise ValueError(
                "CFPB payment amount furnishing report missing Table 1 row: "
                f"{loan_type}"
            )
        records.append(
            {
                "date": "2020-03-31",
                "report_date": "2020-11-12",
                "source_table": "table_1_payment_amount_furnishing_by_loan_type",
                "loan_type": loan_type.lower().replace(" ", "_"),
                "tradelines_mil": tradelines_mil,
                "recent_payment_tradelines_mil": recent_payment_mil,
                "actual_payment_amount_furnished_pct": actual_payment_pct,
                "actual_payment_furnishing_context_available": "true",
                "payment_amount_credit_bureau_context_available": "true",
                "revolving_credit_payment_gap_context_available": str(
                    loan_type in {"Credit card", "Retail revolving"}
                ).lower(),
                "borrower_level_microdata_available": "false",
                "rate_sensitive_payment_drag_transmission_available": "false",
                "current_demand_response_available": "false",
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


def _cfpb_payment_amount_furnishing_snapshot(
    *, registry: SourceRegistry, source_pdf: Path
) -> SourceSnapshot:
    series = registry.series[CFPB_PAYMENT_AMOUNT_FURNISHING_SERIES_ID]
    if not source_pdf.exists():
        _download_source(series.endpoint, source_pdf)
    text = _pdf_text(source_pdf)
    records = _cfpb_payment_amount_furnishing_records(text)
    pdf_hash = _file_sha256(source_pdf)
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    note = (
        "cfpb_payment_amount_furnishing_credit_bureau_context_only;"
        f"source_pdf_sha256={pdf_hash};"
        f"source_text_sha256={text_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "report_date=2020-11-12;"
        "observation_date=2020-03-31;"
        "schema=loan_type_tradelines_recent_payment_tradelines_actual_payment_"
        "furnished_share;"
        "actual_payment_furnishing_context_available=true;"
        "payment_amount_credit_bureau_context_available=true;"
        "revolving_credit_payment_gap_context_available=true;"
        "borrower_level_microdata_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2020-11-12",
            snapshot_kind="live_pdf_context",
            note=note,
        ),
        records=records,
    )


def _cfpb_credit_card_market_report_records(text: str) -> list[dict[str, str]]:
    normalized = re.sub(r"\s+", " ", text.replace(",", "")).strip().lower()
    normalized = normalized.replace("’", "'").replace("\u2010", "-")
    missing = [
        marker
        for marker in CFPB_CREDIT_CARD_MARKET_REPORT_MARKERS
        if marker not in normalized
    ]
    if missing:
        raise ValueError(
            "CFPB credit card market report missing expected markers: "
            + "; ".join(missing)
        )
    records: list[dict[str, str]] = []
    for metric, (
        value_kind,
        metric_value,
        metric_unit,
        observation_date,
        pattern,
    ) in CFPB_CREDIT_CARD_MARKET_REPORT_METRICS.items():
        if re.search(pattern, normalized) is None:
            raise ValueError(
                f"CFPB credit card market report missing metric pattern: {metric}"
            )
        records.append(
            {
                "date": observation_date,
                "report_date": "2026-01-07",
                "report_year": "2025",
                "source_dataset": "cfpb_consumer_credit_card_market_report_2025",
                "source_population": "consumer_credit_card_market",
                "metric": metric,
                "value_kind": value_kind,
                "metric_value": metric_value,
                "metric_unit": metric_unit,
                "source_schema_reviewed": "true",
                "report_text_markers_verified": "true",
                "payment_behavior_context_available": "true",
                "minimum_payment_behavior_context_available": "true",
                "apr_repricing_context_available": "true",
                "variable_index_rate_context_available": "true",
                "existing_account_repricing_timing_limited": "true",
                "issuer_margin_attribution_available": "false",
                "borrower_level_microdata_available": "false",
                "rate_sensitive_payment_drag_transmission_available": "false",
                "current_demand_response_available": "false",
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


def _cfpb_credit_card_market_report_snapshot(
    *, registry: SourceRegistry, source_pdf: Path
) -> SourceSnapshot:
    series = registry.series[CFPB_CREDIT_CARD_MARKET_REPORT_SERIES_ID]
    if not source_pdf.exists():
        _download_source(series.endpoint, source_pdf)
    text = _pdf_text(source_pdf)
    records = _cfpb_credit_card_market_report_records(text)
    pdf_hash = _file_sha256(source_pdf)
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    note = (
        "cfpb_credit_card_market_report_apr_payment_transmission_"
        "limitations_context_only;"
        f"source_pdf_sha256={pdf_hash};"
        f"source_text_sha256={text_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "report_date=2026-01-07;"
        "report_year=2025;"
        "schema=metric_value_unit_with_report_text_markers_and_fail_closed_flags;"
        "minimum_payment_behavior_context_available=true;"
        "apr_repricing_context_available=true;"
        "variable_index_rate_context_available=true;"
        "existing_account_repricing_timing_limited=true;"
        "issuer_margin_attribution_available=false;"
        "borrower_level_microdata_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2026-01-07",
            snapshot_kind="live_pdf_context",
            note=note,
        ),
        records=records,
    )


def _cfpb_credit_card_interest_payment_mechanics_records(
    guidance_html: str, regulation_html: str
) -> list[dict[str, str]]:
    guidance_text = _plain_text(html.unescape(guidance_html))
    regulation_text = _plain_text(html.unescape(regulation_html))
    guidance_normalized = re.sub(r"\s+", " ", guidance_text).strip().lower()
    regulation_normalized = re.sub(r"\s+", " ", regulation_text).strip().lower()
    missing_guidance = [
        marker
        for marker in CFPB_CREDIT_CARD_INTEREST_PAYMENT_MECHANICS_MARKERS
        if marker not in guidance_normalized
    ]
    missing_regulation = [
        marker
        for marker in CFPB_CREDIT_CARD_PAYMENT_ALLOCATION_REGZ_MARKERS
        if marker not in regulation_normalized
    ]
    if missing_guidance or missing_regulation:
        raise ValueError(
            "CFPB credit card interest/payment mechanics missing markers: "
            + "; ".join([*missing_guidance, *missing_regulation])
        )

    metrics: tuple[tuple[str, str, str, str, str], ...] = (
        (
            "daily_interest_accrual_context",
            "reported_mechanics",
            "interest_calculated_daily_using_average_daily_balance",
            "credit_card_interest_calculation_context",
            "CFPB Ask CFPB interest calculation guidance",
        ),
        (
            "daily_periodic_rate_context",
            "reported_mechanics",
            "daily_periodic_rate_as_daily_interest_rate",
            "credit_card_interest_rate_context",
            "CFPB Ask CFPB interest calculation guidance",
        ),
        (
            "grace_period_full_payment_context",
            "reported_mechanics",
            "pay_full_balance_by_due_date_to_avoid_purchase_interest_when_grace_period_applies",
            "credit_card_interest_avoidance_context",
            "CFPB Ask CFPB interest calculation guidance",
        ),
        (
            "excess_payment_high_apr_allocation_context",
            "regulatory_mechanics",
            "excess_above_minimum_generally_allocated_first_to_highest_apr_balance",
            "credit_card_payment_allocation_context",
            "CFPB Regulation Z 1026.53",
        ),
        (
            "minimum_payment_allocation_limitation_context",
            "regulatory_mechanics",
            "minimum_required_payment_allocation_left_to_issuer_subject_to_rule_context",
            "credit_card_payment_allocation_limitation_context",
            "CFPB Regulation Z 1026.53",
        ),
        (
            "promotion_blocker_context",
            "fail_closed_blocker",
            "mechanics_do_not_identify_monetary_policy_rate_shock_payment_drag_or_current_demand_response",
            "promotion_blocker_context",
            "CFPB guidance and Regulation Z context",
        ),
    )
    records: list[dict[str, str]] = []
    for metric, value_kind, metric_value, metric_unit, source_marker in metrics:
        records.append(
            {
                "date": "2026-05-18",
                "source_dataset": (
                    "cfpb_credit_card_interest_payment_mechanics_context"
                ),
                "source_population": "consumer_credit_card_accounts",
                "metric": metric,
                "value_kind": value_kind,
                "metric_value": metric_value,
                "metric_unit": metric_unit,
                "source_marker": source_marker,
                "source_schema_reviewed": "true",
                "guidance_text_markers_verified": "true",
                "regulation_text_markers_verified": "true",
                "rate_sensitive_payment_mechanics_context_available": "true",
                "apr_to_finance_charge_mechanics_available": "true",
                "payment_allocation_mechanics_available": "true",
                "fast_repricing_credit_card_mechanics_context_available": "true",
                "fast_repricing_credit_card_auto_context_available": "false",
                "monetary_rate_shock_payment_drag_transmission_available": "false",
                "current_demand_response_available": "false",
                "current_demand_conversion_available": "false",
                "borrower_level_microdata_available": "false",
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "empirical_threshold_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return records


def _cfpb_credit_card_interest_payment_mechanics_snapshot(
    *, registry: SourceRegistry, source_html: Path, regulation_html: Path
) -> SourceSnapshot:
    series = registry.series[CFPB_CREDIT_CARD_INTEREST_PAYMENT_MECHANICS_SERIES_ID]
    if not source_html.exists():
        _download_source(series.endpoint, source_html)
    if not regulation_html.exists():
        _download_source(CFPB_CREDIT_CARD_PAYMENT_ALLOCATION_REGZ_URL, regulation_html)
    guidance_html = source_html.read_text(encoding="utf-8", errors="replace")
    regulation_text = regulation_html.read_text(encoding="utf-8", errors="replace")
    records = _cfpb_credit_card_interest_payment_mechanics_records(
        guidance_html, regulation_text
    )
    source_hash = _file_sha256(source_html)
    regulation_hash = _file_sha256(regulation_html)
    records_hash = _records_sha256(records)
    note = (
        "cfpb_credit_card_interest_payment_mechanics_context_only;"
        f"source_html_sha256={source_hash};"
        f"source_regulation_html_sha256={regulation_hash};"
        f"source_regulation_url={CFPB_CREDIT_CARD_PAYMENT_ALLOCATION_REGZ_URL};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "source_date=2024-01-22;"
        "schema=metric_value_unit_with_guidance_regulation_markers_and_fail_closed_flags;"
        "rate_sensitive_payment_mechanics_context_available=true;"
        "apr_to_finance_charge_mechanics_available=true;"
        "payment_allocation_mechanics_available=true;"
        "fast_repricing_credit_card_mechanics_context_available=true;"
        "fast_repricing_credit_card_auto_context_available=false;"
        "monetary_rate_shock_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "borrower_level_microdata_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2024-01-22",
            snapshot_kind="live_html_and_regulation_context",
            note=note,
        ),
        records=records,
    )


def _cfpb_credit_card_revolvers_records(text: str) -> list[dict[str, str]]:
    normalized = re.sub(r"\s+", " ", text.replace(",", "")).strip().lower()
    normalized = normalized.replace("’", "'").replace("\u2010", "-")
    missing = [
        marker
        for marker in CFPB_CREDIT_CARD_REVOLVERS_MARKERS
        if marker not in normalized
    ]
    if missing:
        raise ValueError(
            "CFPB credit card revolvers report missing expected markers: "
            + "; ".join(missing)
        )
    records: list[dict[str, str]] = []
    for metric, (
        value_kind,
        metric_value,
        metric_unit,
        pattern,
    ) in CFPB_CREDIT_CARD_REVOLVERS_METRICS.items():
        if re.search(pattern, normalized) is None:
            raise ValueError(
                f"CFPB credit card revolvers report missing metric pattern: {metric}"
            )
        records.append(
            {
                "date": "2016-04-30",
                "report_date": "2019-07-02",
                "sample_start": "2008-04-01",
                "sample_end": "2016-04-30",
                "source_dataset": "cfpb_credit_card_database_large_bank_accounts",
                "source_population": "general_purpose_credit_card_accounts",
                "metric": metric,
                "value_kind": value_kind,
                "metric_value": metric_value,
                "metric_unit": metric_unit,
                "source_schema_reviewed": "true",
                "sample_window_documented": "true",
                "payment_behavior_context_available": "true",
                "revolving_duration_context_available": "true",
                "credit_score_tier_context_available": "true",
                "public_borrower_level_microdata_available": "false",
                "rate_sensitive_payment_drag_transmission_available": "false",
                "current_demand_response_available": "false",
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


def _cfpb_credit_card_revolvers_snapshot(
    *, registry: SourceRegistry, source_pdf: Path
) -> SourceSnapshot:
    series = registry.series[CFPB_CREDIT_CARD_REVOLVERS_SERIES_ID]
    if not source_pdf.exists():
        _download_source(series.endpoint, source_pdf)
    text = _pdf_text(source_pdf)
    records = _cfpb_credit_card_revolvers_records(text)
    pdf_hash = _file_sha256(source_pdf)
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    note = (
        "cfpb_credit_card_revolver_duration_repayment_context_only;"
        f"source_pdf_sha256={pdf_hash};"
        f"source_text_sha256={text_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "report_date=2019-07-02;"
        "sample_start=2008-04-01;"
        "sample_end=2016-04-30;"
        "schema=metric_value_unit_with_sample_window_and_fail_closed_flags;"
        "payment_behavior_context_available=true;"
        "revolving_duration_context_available=true;"
        "credit_score_tier_context_available=true;"
        "public_borrower_level_microdata_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2019-07-02",
            snapshot_kind="live_pdf_context",
            note=note,
        ),
        records=records,
    )


def _fed_scf_summary_extract_records(source_zip: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(source_zip) as archive:
        names = archive.namelist()
        if FED_SCF_SUMMARY_EXTRACT_FILE not in names:
            raise ValueError(f"{source_zip} missing {FED_SCF_SUMMARY_EXTRACT_FILE}")
        with archive.open(FED_SCF_SUMMARY_EXTRACT_FILE) as handle:
            source_rows = list(
                csv.DictReader(
                    (line.decode("utf-8-sig") for line in handle),
                )
            )
    if not source_rows:
        raise ValueError("Fed SCF summary extract CSV had no records")
    missing = set(FED_SCF_SUMMARY_EXTRACT_FIELDS) - set(source_rows[0])
    if missing:
        raise ValueError(
            "Fed SCF summary extract missing required fields: "
            + ",".join(sorted(missing))
        )
    records: list[dict[str, str]] = []
    for index, row in enumerate(source_rows, start=2):
        record = {
            "date": "2022-01-01",
            "survey_year": "2022",
            "source_file": FED_SCF_SUMMARY_EXTRACT_FILE,
            "source_row_index_one_based": str(index),
            "source_csv_schema_reviewed": "true",
            "public_family_level_record_context_available": "true",
            "product_balance_context_available": "true",
            "income_distribution_context_available": "true",
            "liquidity_context_available": "true",
            "payment_behavior_context_available": "true",
            "borrower_level_credit_bureau_microdata_available": "false",
            "survey_design_uncertainty_required_before_estimation": "true",
            "current_demand_conversion_available": "false",
            "denominator_prior_narrowing_allowed": "false",
            "split_denominator_promotion_allowed": "false",
            "formula_replacement_allowed": "false",
            "main_ratio_admission_allowed": "false",
            "incidence_output_enabled": "false",
            "welfare_tax_mpc_output_enabled": "false",
        }
        for field in FED_SCF_SUMMARY_EXTRACT_FIELDS:
            record[field.lower()] = _normalize_source_number(row[field].strip())
        records.append(record)
    return records


def _fed_scf_summary_extract_snapshot(
    *, registry: SourceRegistry, source_zip: Path
) -> SourceSnapshot:
    series = registry.series[FED_SCF_SUMMARY_EXTRACT_SERIES_ID]
    if not source_zip.exists():
        _download_source(series.endpoint, source_zip)
    records = _fed_scf_summary_extract_records(source_zip)
    source_zip_hash = _file_sha256(source_zip)
    records_hash = _records_sha256(records)
    note = (
        "fed_scf_public_summary_extract_debt_liquidity_payment_context_only;"
        f"source_zip_sha256={source_zip_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"source_file={FED_SCF_SUMMARY_EXTRACT_FILE};"
        "survey_year=2022;"
        "schema=selected_scf_summary_extract_fields;"
        "public_family_level_record_context_available=true;"
        "product_balance_context_available=true;"
        "income_distribution_context_available=true;"
        "liquidity_context_available=true;"
        "payment_behavior_context_available=true;"
        "borrower_level_credit_bureau_microdata_available=false;"
        "survey_design_uncertainty_required_before_estimation=true;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2024-04-03",
            snapshot_kind="live_zip_csv_context",
            note=note,
        ),
        records=records,
    )


def _source_float(value: str) -> float:
    if value == "":
        return math.nan
    try:
        return float(value)
    except ValueError:
        return math.nan


def _summary_number(value: float) -> str:
    if not math.isfinite(value):
        return ""
    normalized = f"{value:.6f}".rstrip("0").rstrip(".")
    return "0" if normalized == "-0" else normalized


def _weighted_mean(rows: Sequence[dict[str, str]], field: str) -> float:
    numerator = 0.0
    denominator = 0.0
    for row in rows:
        value = _source_float(row.get(field, ""))
        weight = _source_float(row.get("wgt", "")) / 5.0
        if not math.isfinite(value) or not math.isfinite(weight) or weight <= 0:
            continue
        numerator += value * weight
        denominator += weight
    return numerator / denominator if denominator else math.nan


def _weighted_indicator_share(rows: Sequence[dict[str, str]], field: str) -> float:
    numerator = 0.0
    denominator = 0.0
    for row in rows:
        value = row.get(field, "")
        weight = _source_float(row.get("wgt", "")) / 5.0
        if value == "" or not math.isfinite(weight) or weight <= 0:
            continue
        numerator += (1.0 if value == "1" else 0.0) * weight
        denominator += weight
    return numerator / denominator if denominator else math.nan


def _weighted_median(rows: Sequence[dict[str, str]], field: str) -> float:
    pairs: list[tuple[float, float]] = []
    for row in rows:
        value = _source_float(row.get(field, ""))
        weight = _source_float(row.get("wgt", "")) / 5.0
        if not math.isfinite(value) or not math.isfinite(weight) or weight <= 0:
            continue
        pairs.append((value, weight))
    if not pairs:
        return math.nan
    pairs.sort(key=lambda pair: pair[0])
    midpoint = sum(weight for _, weight in pairs) / 2.0
    cumulative = 0.0
    for value, weight in pairs:
        cumulative += weight
        if cumulative >= midpoint:
            return value
    return pairs[-1][0]


def _fed_scf_weighted_summary_records(
    source_records: Sequence[dict[str, str]],
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    source_family_count = len({record.get("yy1", "") for record in source_records})
    for group_dimension, group_field, group_code in FED_SCF_WEIGHTED_SUMMARY_GROUPS:
        if group_dimension == "all":
            group_records = list(source_records)
            label = "all_public_extract_families"
            code = "all"
        else:
            group_records = [
                record
                for record in source_records
                if record.get(group_field, "") == group_code
            ]
            label = f"{group_field}_source_code_{group_code}"
            code = group_code
        if not group_records:
            continue
        weighted_family_count = 0.0
        for record in group_records:
            weight = _source_float(record.get("wgt", ""))
            if math.isfinite(weight) and weight > 0:
                weighted_family_count += weight / 5.0
        records.append(
            {
                "date": "2022-01-01",
                "survey_year": "2022",
                "source_file": FED_SCF_SUMMARY_EXTRACT_FILE,
                "source_extract_series_id": FED_SCF_SUMMARY_EXTRACT_SERIES_ID,
                "summary_method": "weighted_descriptive_summary_context_only",
                "weight_field": "wgt",
                "imputation_handling": "all_implicates_weight_divided_by_5",
                "public_family_id_field": "yy1",
                "source_public_extract_record_count": str(len(source_records)),
                "source_public_family_count": str(source_family_count),
                "source_group_record_count": str(len(group_records)),
                "source_group_family_count": str(
                    len({record.get("yy1", "") for record in group_records})
                ),
                "weighted_family_count": _summary_number(weighted_family_count),
                "group_dimension": group_dimension,
                "group_field": group_field,
                "group_code": code,
                "group_label": label,
                "weighted_mean_income": _summary_number(
                    _weighted_mean(group_records, "income")
                ),
                "weighted_median_income": _summary_number(
                    _weighted_median(group_records, "income")
                ),
                "weighted_mean_liquid_assets": _summary_number(
                    _weighted_mean(group_records, "liq")
                ),
                "weighted_median_liquid_assets": _summary_number(
                    _weighted_median(group_records, "liq")
                ),
                "weighted_share_liquid_assets_positive": _summary_number(
                    _weighted_indicator_share(group_records, "hliq")
                ),
                "weighted_mean_credit_card_balance": _summary_number(
                    _weighted_mean(group_records, "ccbal")
                ),
                "weighted_median_credit_card_balance": _summary_number(
                    _weighted_median(group_records, "ccbal")
                ),
                "weighted_share_credit_card_balance_positive": _summary_number(
                    _weighted_indicator_share(group_records, "hccbal")
                ),
                "weighted_mean_debt": _summary_number(
                    _weighted_mean(group_records, "debt")
                ),
                "weighted_median_debt": _summary_number(
                    _weighted_median(group_records, "debt")
                ),
                "weighted_share_debt_positive": _summary_number(
                    _weighted_indicator_share(group_records, "hdebt")
                ),
                "weighted_mean_debt_to_income": _summary_number(
                    _weighted_mean(group_records, "debt2inc")
                ),
                "weighted_mean_consumer_payment": _summary_number(
                    _weighted_mean(group_records, "conspay")
                ),
                "weighted_mean_revolving_payment": _summary_number(
                    _weighted_mean(group_records, "revpay")
                ),
                "weighted_mean_revolving_payment_income_ratio": _summary_number(
                    _weighted_mean(group_records, "pirrev")
                ),
                "survey_design_weighted_summary_available": "true",
                "replicate_weight_uncertainty_available": "false",
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


def _fed_scf_weighted_summary_snapshot(
    *, registry: SourceRegistry, source_zip: Path
) -> SourceSnapshot:
    series = registry.series[FED_SCF_WEIGHTED_SUMMARY_SERIES_ID]
    if not source_zip.exists():
        _download_source(series.endpoint, source_zip)
    source_records = _fed_scf_summary_extract_records(source_zip)
    records = _fed_scf_weighted_summary_records(source_records)
    source_zip_hash = _file_sha256(source_zip)
    records_hash = _records_sha256(records)
    note = (
        "fed_scf_public_summary_extract_weighted_consumer_credit_review_"
        "context_only;"
        f"source_zip_sha256={source_zip_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"source_extract_record_count={len(source_records)};"
        "survey_year=2022;"
        "schema=weighted_summary_by_all_income_normal_income_age_credit_"
        "card_balance_and_debt_status;"
        "survey_design_weighted_summary_available=true;"
        "replicate_weight_uncertainty_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2024-04-03",
            snapshot_kind="live_zip_csv_weighted_summary_context",
            note=note,
        ),
        records=records,
    )


def _storable_type_size(stata_type: int) -> int:
    sizes = {
        -10: 8,  # double
        -9: 4,  # float
        -8: 4,  # long
        -7: 2,  # int
        -6: 1,  # byte
    }
    if stata_type in sizes:
        return sizes[stata_type]
    if 1 <= stata_type <= 2045:
        return stata_type
    raise ValueError(f"Unsupported Stata storable type in SCF DTA: {stata_type}")


def _storable_numeric_value(blob: bytes, offset: int, stata_type: int) -> float:
    if stata_type == -10:
        value = struct.unpack("<d", blob[offset : offset + 8])[0]
    elif stata_type == -9:
        value = struct.unpack("<f", blob[offset : offset + 4])[0]
    elif stata_type == -8:
        value = float(struct.unpack("<i", blob[offset : offset + 4])[0])
    elif stata_type == -7:
        value = float(struct.unpack("<h", blob[offset : offset + 2])[0])
    elif stata_type == -6:
        value = float(struct.unpack("<b", blob[offset : offset + 1])[0])
    else:
        raise ValueError(f"Unsupported numeric SCF DTA type: {stata_type}")
    if value >= STATA_NUMERIC_MISSING_THRESHOLD:
        return math.nan
    return value


def _positive_weight_or_zero(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return max(0.0, value)


def _positive_multiplicity_or_zero(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    if value >= 100.0:
        return 0.0
    return max(0.0, value)


def _fed_scf_replicate_effective_weights(
    source_zip: Path,
) -> tuple[dict[str, array], dict[str, str]]:
    metadata = _fed_scf_replicate_weight_dta_metadata(source_zip)
    with zipfile.ZipFile(source_zip) as archive:
        dta_blob = archive.read(FED_SCF_REPLICATE_WEIGHT_FILE)
    header_start, header_end = _dta_tag_range(dta_blob, "header")
    header = dta_blob[header_start:header_end]
    k_start = header.index(b"<K>") + len(b"<K>")
    k_end = header.index(b"</K>")
    n_start = header.index(b"<N>") + len(b"<N>")
    n_end = header.index(b"</N>")
    variable_count = struct.unpack("<H", header[k_start:k_end])[0]
    observation_count = struct.unpack("<Q", header[n_start:n_end])[0]
    types_start, types_end = _dta_tag_range(dta_blob, "variable_types")
    types = list(
        struct.unpack("<" + "h" * variable_count, dta_blob[types_start:types_end])
    )
    names_start, names_end = _dta_tag_range(dta_blob, "varnames")
    varnames_blob = dta_blob[names_start:names_end]
    varnames = [
        varnames_blob[index * 129 : (index + 1) * 129]
        .split(b"\x00", 1)[0]
        .decode("ascii", errors="replace")
        for index in range(variable_count)
    ]
    offsets: list[int] = []
    running_offset = 0
    for stata_type in types:
        offsets.append(running_offset)
        running_offset += _storable_type_size(stata_type)
    data_start, data_end = _dta_tag_range(dta_blob, "data")
    expected_data_length = running_offset * observation_count
    if data_end - data_start != expected_data_length:
        raise ValueError(
            "Fed SCF replicate DTA data block size did not match schema: "
            f"{data_end - data_start} != {expected_data_length}"
        )
    yy1_index = varnames.index("yy1")
    weight_by_number = {
        int(name.removeprefix("wt1b")): index
        for index, name in enumerate(varnames)
        if re.fullmatch(r"wt1b\d+", name)
    }
    multiplier_by_number = {
        int(name.removeprefix("mm")): index
        for index, name in enumerate(varnames)
        if re.fullmatch(r"mm\d+", name)
    }
    if sorted(weight_by_number) != list(range(1, 1000)):
        raise ValueError("Fed SCF replicate DTA wt1b columns are not 1..999")
    if sorted(multiplier_by_number) != list(range(1, 1000)):
        raise ValueError("Fed SCF replicate DTA mm columns are not 1..999")
    effective_weights: dict[str, array] = {}
    for row_index in range(observation_count):
        row_offset = data_start + row_index * running_offset
        yy1 = _storable_numeric_value(
            dta_blob,
            row_offset + offsets[yy1_index],
            types[yy1_index],
        )
        if not math.isfinite(yy1):
            raise ValueError("Fed SCF replicate DTA row missing yy1 key")
        family_id = str(int(yy1))
        replicate_values = array("d")
        for replicate_number in range(1, 1000):
            weight_index = weight_by_number[replicate_number]
            multiplier_index = multiplier_by_number[replicate_number]
            weight = _storable_numeric_value(
                dta_blob,
                row_offset + offsets[weight_index],
                types[weight_index],
            )
            multiplier = _storable_numeric_value(
                dta_blob,
                row_offset + offsets[multiplier_index],
                types[multiplier_index],
            )
            replicate_values.append(
                _positive_weight_or_zero(weight)
                * _positive_multiplicity_or_zero(multiplier)
            )
        effective_weights[family_id] = replicate_values
    return effective_weights, {key: str(value) for key, value in metadata.items()}


def _scf_implicate_number(record: Mapping[str, str]) -> str:
    y1 = int(float(record["y1"]))
    yy1 = int(float(record["yy1"]))
    return str(y1 - 10 * yy1)


def _scf_metric_value(record: Mapping[str, str], field: str, metric_type: str) -> float:
    raw = record.get(field, "")
    if raw == "":
        return math.nan
    if metric_type == "indicator_share":
        return 1.0 if raw == "1" else 0.0
    return _source_float(raw)


def _scf_weighted_estimate(
    rows: Sequence[dict[str, str]],
    *,
    field: str,
    metric_type: str,
    weight_getter: Callable[[dict[str, str]], float],
) -> float:
    numerator = 0.0
    denominator = 0.0
    for row in rows:
        value = _scf_metric_value(row, field, metric_type)
        weight = weight_getter(row)
        if not math.isfinite(value) or not math.isfinite(weight) or weight <= 0:
            continue
        numerator += value * weight
        denominator += weight
    return numerator / denominator if denominator else math.nan


def _sample_standard_deviation(values: Sequence[float]) -> float:
    finite_values = [value for value in values if math.isfinite(value)]
    if len(finite_values) < 2:
        return math.nan
    mean_value = sum(finite_values) / len(finite_values)
    variance = sum((value - mean_value) ** 2 for value in finite_values) / (
        len(finite_values) - 1
    )
    return math.sqrt(variance)


def _fed_scf_uncertainty_records(
    source_records: Sequence[dict[str, str]],
    replicate_weights: Mapping[str, Sequence[float]],
) -> list[dict[str, str]]:
    source_family_ids = {record.get("yy1", "") for record in source_records}
    replicate_family_ids = set(replicate_weights)
    missing_replicate_families = sorted(source_family_ids - replicate_family_ids)
    if missing_replicate_families:
        raise ValueError(
            "Fed SCF summary extract has families missing replicate weights: "
            + ",".join(missing_replicate_families[:10])
        )
    rows_by_implicate: dict[str, list[dict[str, str]]] = {
        str(index): [] for index in range(1, 6)
    }
    for record in source_records:
        implicate = _scf_implicate_number(record)
        if implicate in rows_by_implicate:
            rows_by_implicate[implicate].append(dict(record))
    if any(len(rows) == 0 for rows in rows_by_implicate.values()):
        raise ValueError("Fed SCF public extract did not retain all five implicates")
    first_implicate_rows = rows_by_implicate["1"]
    records: list[dict[str, str]] = []
    for group_dimension, group_field, group_code in FED_SCF_UNCERTAINTY_GROUPS:
        if group_dimension == "all":

            def group_filter(row: Mapping[str, str]) -> bool:
                return True

            group_label = "all_public_extract_families"
            code = "all"
        else:

            def group_filter(
                row: Mapping[str, str],
                *,
                field: str = group_field,
                expected_code: str = group_code,
            ) -> bool:
                return row.get(field, "") == expected_code

            group_label = f"{group_field}_source_code_{group_code}"
            code = group_code
        grouped_by_implicate = {
            implicate: [row for row in rows if group_filter(row)]
            for implicate, rows in rows_by_implicate.items()
        }
        sampling_rows = [row for row in first_implicate_rows if group_filter(row)]
        source_group_family_count = len({row["yy1"] for row in sampling_rows})
        if not sampling_rows:
            continue
        replicate_denominators = array("d", [0.0 for _ in range(999)])
        for row in sampling_rows:
            for replicate_index, weight in enumerate(replicate_weights[row["yy1"]]):
                replicate_denominators[replicate_index] += weight
        weighted_family_count = sum(
            _source_float(row.get("wgt", "")) for row in sampling_rows
        )
        for metric_name, field, metric_type in FED_SCF_UNCERTAINTY_METRICS:
            implicate_estimates = [
                _scf_weighted_estimate(
                    rows,
                    field=field,
                    metric_type=metric_type,
                    weight_getter=lambda row: _source_float(row.get("wgt", "")),
                )
                for rows in grouped_by_implicate.values()
            ]
            finite_implicate_estimates = [
                estimate for estimate in implicate_estimates if math.isfinite(estimate)
            ]
            replicate_numerators = array("d", [0.0 for _ in range(999)])
            for row in sampling_rows:
                value = _scf_metric_value(row, field, metric_type)
                if not math.isfinite(value):
                    continue
                weights = replicate_weights[row["yy1"]]
                for replicate_index, weight in enumerate(weights):
                    replicate_numerators[replicate_index] += value * weight
            replicate_estimates = [
                (
                    replicate_numerators[index] / denominator
                    if denominator > 0
                    else math.nan
                )
                for index, denominator in enumerate(replicate_denominators)
            ]
            finite_replicate_estimates = [
                estimate for estimate in replicate_estimates if math.isfinite(estimate)
            ]
            support_passed = (
                len(finite_implicate_estimates) == 5
                and len(finite_replicate_estimates) == 999
            )
            imputation_sd = _sample_standard_deviation(implicate_estimates)
            sampling_sd = _sample_standard_deviation(replicate_estimates)
            combined_sd = (
                math.sqrt((6.0 / 5.0) * imputation_sd**2 + sampling_sd**2)
                if math.isfinite(imputation_sd) and math.isfinite(sampling_sd)
                else math.nan
            )
            point_estimate = (
                sum(finite_implicate_estimates) / len(finite_implicate_estimates)
                if finite_implicate_estimates
                else math.nan
            )
            ci_low = (
                point_estimate - 1.96 * combined_sd
                if math.isfinite(point_estimate) and math.isfinite(combined_sd)
                else math.nan
            )
            ci_high = (
                point_estimate + 1.96 * combined_sd
                if math.isfinite(point_estimate) and math.isfinite(combined_sd)
                else math.nan
            )
            records.append(
                {
                    "date": "2022-01-01",
                    "survey_year": "2022",
                    "source_extract_file": FED_SCF_SUMMARY_EXTRACT_FILE,
                    "replicate_weight_file": FED_SCF_REPLICATE_WEIGHT_FILE,
                    "source_extract_series_id": FED_SCF_SUMMARY_EXTRACT_SERIES_ID,
                    "replicate_weight_series_id": (
                        FED_SCF_REPLICATE_WEIGHT_METHOD_SERIES_ID
                    ),
                    "summary_method": (
                        "scf_meanit_replicate_weight_uncertainty_review_context_only"
                    ),
                    "point_estimate_method": (
                        "mean_across_five_implicate_weighted_estimates"
                    ),
                    "imputation_variance_method": (
                        "sample_variance_across_five_implicate_estimates"
                    ),
                    "sampling_variance_method": (
                        "sample_variance_across_999_first_implicate_"
                        "replicate_weight_estimates"
                    ),
                    "combined_standard_error_formula": (
                        "sqrt((6/5)*imputation_variance+sampling_variance)"
                    ),
                    "replicate_weight_effective_weight_formula": (
                        "max(0,wt1b_i)*max(0,mm_i)"
                    ),
                    "imputation_handling": (
                        "five_implicates_for_imputation_variance_first_"
                        "implicate_for_sampling_variance"
                    ),
                    "group_dimension": group_dimension,
                    "group_field": group_field,
                    "group_code": code,
                    "group_label": group_label,
                    "metric": metric_name,
                    "metric_field": field,
                    "metric_type": metric_type,
                    "point_estimate": _summary_number(point_estimate),
                    "imputation_standard_error": _summary_number(imputation_sd),
                    "sampling_standard_error": _summary_number(sampling_sd),
                    "combined_standard_error": _summary_number(combined_sd),
                    "ci_95_low": _summary_number(ci_low),
                    "ci_95_high": _summary_number(ci_high),
                    "implicate_estimate_count": str(len(finite_implicate_estimates)),
                    "replicate_estimate_count": str(len(finite_replicate_estimates)),
                    "source_public_extract_record_count": str(len(source_records)),
                    "source_public_family_count": str(len(source_family_ids)),
                    "source_group_family_count": str(source_group_family_count),
                    "weighted_family_count_first_implicate": _summary_number(
                        weighted_family_count
                    ),
                    "joined_summary_replicate_family_count": str(
                        len(source_family_ids & replicate_family_ids)
                    ),
                    "missing_replicate_family_count": "0",
                    "schema_support_check_passed": "true"
                    if support_passed
                    else "false",
                    "replicate_weight_uncertainty_executed": (
                        "true" if support_passed else "false"
                    ),
                    "current_demand_conversion_available": "false",
                    "denominator_prior_narrowing_allowed": "false",
                    "split_denominator_promotion_allowed": "false",
                    "formula_replacement_allowed": "false",
                    "main_ratio_admission_allowed": "false",
                    "incidence_output_enabled": "false",
                    "welfare_tax_mpc_output_enabled": "false",
                    "method_blocker": (
                        "current_demand_response_and_credit_repricing_"
                        "transmission_still_required_before_denominator_"
                        "promotion"
                    ),
                }
            )
    return records


def _fed_scf_uncertainty_snapshot(
    *,
    registry: SourceRegistry,
    summary_zip: Path,
    replicate_zip: Path,
    standard_error_pdf: Path,
    codebook: Path,
) -> SourceSnapshot:
    series = registry.series[FED_SCF_UNCERTAINTY_SERIES_ID]
    if not summary_zip.exists():
        _download_source(
            registry.series[FED_SCF_SUMMARY_EXTRACT_SERIES_ID].endpoint,
            summary_zip,
        )
    if not replicate_zip.exists():
        _download_source(
            registry.series[FED_SCF_REPLICATE_WEIGHT_METHOD_SERIES_ID].endpoint,
            replicate_zip,
        )
    if not standard_error_pdf.exists():
        _download_source(FED_SCF_STANDARD_ERROR_DOCUMENTATION_URL, standard_error_pdf)
    if not codebook.exists():
        _download_source(FED_SCF_CODEBOOK_URL, codebook)
    source_records = _fed_scf_summary_extract_records(summary_zip)
    replicate_weights, replicate_metadata = _fed_scf_replicate_effective_weights(
        replicate_zip
    )
    records = _fed_scf_uncertainty_records(source_records, replicate_weights)
    summary_zip_hash = _file_sha256(summary_zip)
    replicate_zip_hash = _file_sha256(replicate_zip)
    standard_error_pdf_hash = _file_sha256(standard_error_pdf)
    codebook_hash = _file_sha256(codebook)
    records_hash = _records_sha256(records)
    note = (
        "fed_scf_joined_replicate_weight_uncertainty_review_context_only;"
        f"summary_zip_sha256={summary_zip_hash};"
        f"replicate_weight_zip_sha256={replicate_zip_hash};"
        f"standard_error_documentation_pdf_sha256={standard_error_pdf_hash};"
        f"codebook_sha256={codebook_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"source_extract_record_count={len(source_records)};"
        f"source_public_family_count={len(replicate_weights)};"
        f"source_dta_observation_count={replicate_metadata['source_dta_observation_count']};"
        "replicate_weight_variable_count=999;"
        "summary_extract_join_executed=true;"
        "replicate_weight_uncertainty_executed=true;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2024-04-03",
            snapshot_kind="live_zip_csv_dta_uncertainty_context",
            note=note,
        ),
        records=records,
    )


def _read_fed_shed_rows(source_zip: Path) -> list[dict[str, str]]:
    with zipfile.ZipFile(source_zip) as archive:
        names = archive.namelist()
        if FED_SHED_PUBLIC_USE_FILE not in names:
            raise ValueError(f"{source_zip} missing {FED_SHED_PUBLIC_USE_FILE}")
        with archive.open(FED_SHED_PUBLIC_USE_FILE) as handle:
            rows = list(
                csv.DictReader(
                    (line.decode("utf-8-sig") for line in handle),
                )
            )
    if not rows:
        raise ValueError("Fed SHED public-use CSV had no records")
    missing = set(FED_SHED_REQUIRED_FIELDS) - set(rows[0])
    if missing:
        raise ValueError(
            "Fed SHED public-use CSV missing required fields: "
            + ",".join(sorted(missing))
        )
    return rows


def _shed_weighted_share(
    rows: Sequence[dict[str, str]],
    *,
    value_getter: Callable[[dict[str, str]], str],
    positive_values: set[str],
) -> tuple[float, int, int]:
    numerator = 0.0
    denominator = 0.0
    eligible_records = 0
    malformed_records = 0
    for row in rows:
        value = value_getter(row).strip()
        weight = _source_float(row.get("weight", ""))
        if value == "":
            continue
        if not math.isfinite(weight) or weight <= 0:
            malformed_records += 1
            continue
        eligible_records += 1
        numerator += (1.0 if value in positive_values else 0.0) * weight
        denominator += weight
    return (
        (numerator / denominator if denominator else math.nan),
        eligible_records,
        malformed_records,
    )


def _shed_any_yes_getter(fields: Sequence[str]) -> Callable[[dict[str, str]], str]:
    def getter(row: dict[str, str]) -> str:
        values = [row.get(field, "").strip() for field in fields]
        if any(value == "Yes" for value in values):
            return "Yes"
        if all(value in {"No", "Yes"} for value in values):
            return "No"
        return ""

    return getter


def _fed_shed_financial_fragility_records(
    source_zip: Path,
) -> list[dict[str, str]]:
    source_rows = _read_fed_shed_rows(source_zip)
    metric_specs: tuple[
        tuple[str, str, Callable[[dict[str, str]], str], set[str]], ...
    ] = (
        (
            "financially_okay_or_living_comfortably",
            "financial_wellbeing_context",
            lambda row: row.get("B2", ""),
            {"Doing okay", "Living comfortably"},
        ),
        (
            "financially_worse_off_than_12_months_ago",
            "financial_wellbeing_context",
            lambda row: row.get("B3", ""),
            {"Much worse off", "Somewhat worse off"},
        ),
        (
            "worse_off_due_to_higher_expenses",
            "expense_pressure_context",
            lambda row: row.get("B3A_b", ""),
            {"Yes"},
        ),
        (
            "can_cover_400_expense_with_cash_equivalent",
            "liquidity_fragility_context",
            lambda row: row.get("pay_casheqv", ""),
            {"Yes"},
        ),
        (
            "credit_card_paid_minimum_all_cards_last_month",
            "credit_payment_behavior_context",
            lambda row: row.get("C3P", ""),
            {"Paid at least the minimum payment on all credit cards"},
        ),
        (
            "credit_card_paid_less_than_minimum_any_card_last_month",
            "credit_payment_behavior_context",
            lambda row: row.get("C3P", ""),
            {"Did not pay or paid less than the minimum payment on at least one card"},
        ),
        (
            "credit_card_carried_unpaid_balance_some_or_more",
            "credit_payment_behavior_context",
            lambda row: row.get("C4A", ""),
            {"Some of the time", "Most or all of the time"},
        ),
        (
            "credit_card_carried_unpaid_balance_most_or_all",
            "credit_payment_behavior_context",
            lambda row: row.get("C4A", ""),
            {"Most or all of the time"},
        ),
        (
            "skipped_care_due_to_affordability_any",
            "current_expense_stress_context",
            _shed_any_yes_getter(("E1_a", "E1_b", "E1_c", "E1_d", "E1_e")),
            {"Yes"},
        ),
    )
    records: list[dict[str, str]] = []
    source_record_count = len(source_rows)
    for group_dimension, group_field, group_code in FED_SHED_GROUPS:
        if group_dimension == "all":
            group_rows = list(source_rows)
            group_label = "all_public_use_respondents"
            code = "all"
        else:
            group_rows = [
                row
                for row in source_rows
                if row.get(group_field, "").strip() == group_code
            ]
            group_label = f"{group_field}_{_slug(group_code)}"
            code = group_code
        if not group_rows:
            continue
        for metric, evidence_family, getter, positive_values in metric_specs:
            share, eligible_count, malformed_count = _shed_weighted_share(
                group_rows,
                value_getter=getter,
                positive_values=positive_values,
            )
            records.append(
                {
                    "date": "2025-10-01",
                    "survey_year": "2025",
                    "source_file": FED_SHED_PUBLIC_USE_FILE,
                    "source_record_count": str(source_record_count),
                    "source_group_record_count": str(len(group_rows)),
                    "eligible_response_count": str(eligible_count),
                    "malformed_weight_or_value_count": str(malformed_count),
                    "summary_method": "weighted_share_context_only",
                    "weight_field": "weight",
                    "group_dimension": group_dimension,
                    "group_field": group_field,
                    "group_code": code,
                    "group_label": group_label,
                    "metric": metric,
                    "metric_value": _summary_number(share),
                    "metric_unit": "weighted_share",
                    "evidence_family": evidence_family,
                    "source_csv_schema_reviewed": "true",
                    "codebook_schema_context_admitted": "true",
                    "financial_fragility_context_available": "true",
                    "liquidity_context_available": str(
                        evidence_family == "liquidity_fragility_context"
                    ).lower(),
                    "payment_behavior_context_available": str(
                        evidence_family == "credit_payment_behavior_context"
                    ).lower(),
                    "current_expense_stress_context_available": str(
                        evidence_family == "current_expense_stress_context"
                    ).lower(),
                    "rate_sensitive_payment_drag_transmission_available": "false",
                    "current_demand_conversion_available": "false",
                    "borrower_level_credit_bureau_microdata_available": "false",
                    "denominator_prior_narrowing_allowed": "false",
                    "split_denominator_promotion_allowed": "false",
                    "formula_replacement_allowed": "false",
                    "main_ratio_admission_allowed": "false",
                    "incidence_output_enabled": "false",
                    "welfare_tax_mpc_output_enabled": "false",
                    "method_blocker": (
                        "shed_public_survey_context_does_not_identify_rate_"
                        "sensitive_payment_drag_transmission_or_current_"
                        "demand_response"
                    ),
                }
            )
    return records


def _fed_shed_financial_fragility_snapshot(
    *,
    registry: SourceRegistry,
    source_zip: Path,
    codebook: Path,
) -> SourceSnapshot:
    series = registry.series[FED_SHED_FINANCIAL_FRAGILITY_SERIES_ID]
    if not source_zip.exists():
        _download_source(series.endpoint, source_zip)
    if not codebook.exists():
        _download_source(FED_SHED_CODEBOOK_URL, codebook)
    records = _fed_shed_financial_fragility_records(source_zip)
    source_zip_hash = _file_sha256(source_zip)
    codebook_hash = _file_sha256(codebook)
    records_hash = _records_sha256(records)
    source_rows = _read_fed_shed_rows(source_zip)
    note = (
        "fed_shed_2025_financial_fragility_credit_payment_context_only;"
        f"source_zip_sha256={source_zip_hash};"
        f"codebook_sha256={codebook_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"source_public_use_record_count={len(source_rows)};"
        "survey_year=2025;"
        "schema=weighted_shares_by_all_income_and_age_for_financial_"
        "fragility_liquidity_credit_payment_and_expense_stress;"
        "financial_fragility_context_available=true;"
        "payment_behavior_context_available=true;"
        "liquidity_context_available=true;"
        "current_expense_stress_context_available=true;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2026-05-13",
            snapshot_kind="live_zip_csv_weighted_summary_context",
            note=note,
        ),
        records=records,
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "value"


def _source_label_to_date(label: str) -> str:
    if re.fullmatch(r"\d{4}", label):
        return f"{label}-12-31"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", label):
        return label
    return "2024-02-23"


def _source_table_headers(table_html: str) -> list[str]:
    thead_match = re.search(
        r"<thead>(?P<thead>.*?)</thead>",
        table_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if thead_match is None:
        return []
    headers = [
        _strip_html(match.group("value"))
        for match in re.finditer(
            r"<(?:th|td)[^>]*class=\"colhead\"[^>]*>(?P<value>.*?)</(?:th|td)>",
            thead_match.group("thead"),
            flags=re.DOTALL | re.IGNORECASE,
        )
    ]
    return [header for header in headers if header and header != "\xa0"]


def _source_table_body_rows(table_html: str) -> list[tuple[str, list[str]]]:
    tbody_match = re.search(
        r"<tbody>(?P<tbody>.*?)</tbody>",
        table_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if tbody_match is None:
        return []
    rows: list[tuple[str, list[str]]] = []
    for row_match in re.finditer(
        r"<tr>(?P<row>.*?)</tr>",
        tbody_match.group("tbody"),
        flags=re.DOTALL | re.IGNORECASE,
    ):
        row_html = row_match.group("row")
        label_match = re.search(
            r"<th[^>]*>(?P<label>.*?)</th>",
            row_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if label_match is None:
            continue
        values = [
            _strip_html(match.group("value"))
            for match in re.finditer(
                r"<td[^>]*>(?P<value>.*?)</td>",
                row_html,
                flags=re.DOTALL | re.IGNORECASE,
            )
        ]
        rows.append((_strip_html(label_match.group("label")), values))
    return rows


def _generic_html_table_rows(table_html: str) -> list[tuple[str, list[str], list[str]]]:
    row_values: list[list[str]] = []
    for row_match in re.finditer(
        r"<tr[^>]*>(?P<row>.*?)</tr>",
        table_html,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        values = [
            _clean_source_text(match.group("value"))
            for match in re.finditer(
                r"<t[hd][^>]*>(?P<value>.*?)</t[hd]>",
                row_match.group("row"),
                flags=re.DOTALL | re.IGNORECASE,
            )
        ]
        if values:
            row_values.append(values)
    if not row_values:
        return []
    headers = row_values[0][1:]
    parsed_rows: list[tuple[str, list[str], list[str]]] = []
    for values in row_values[1:]:
        label = values[0]
        data_values = values[1:]
        data_headers = headers
        if len(data_headers) != len(data_values):
            data_headers = [
                f"value_{column_index}"
                for column_index in range(1, len(data_values) + 1)
            ]
        parsed_rows.append((label, data_headers, data_values))
    return parsed_rows


def _table_after_title(html_text: str, title: str) -> str:
    title_index = html_text.find(title)
    if title_index < 0:
        raise ValueError(f"Fed indirect-credit accessible materials missing {title}")
    table_start = html_text.find("<table", title_index)
    if table_start < 0:
        raise ValueError(
            f"Fed indirect-credit accessible materials missing table for {title}"
        )
    table_end = html_text.find("</table>", table_start)
    if table_end < 0:
        raise ValueError(
            f"Fed indirect-credit accessible materials has unclosed table for {title}"
        )
    return html_text[table_start : table_end + len("</table>")]


def _regression_cell_parts(value: str) -> tuple[str, str, str]:
    if not value or value == "&nbsp;":
        return "", "", ""
    normalized = value.replace(",", "")
    match = re.search(
        r"(?P<coef>-?\d+(?:\.\d+)?)(?P<stars>\*{1,3})?(?:\s*\((?P<se>-?\d+(?:\.\d+)?)\))?",
        normalized,
    )
    if match is None:
        return _normalize_source_number(normalized), "", ""
    return (
        _normalize_source_number(match.group("coef")),
        match.group("stars") or "",
        _normalize_source_number(match.group("se") or ""),
    )


def _fed_indirect_credit_accessible_material_records(
    *, index_html: str, accessible_figures_html: str
) -> list[dict[str, str]]:
    combined_text = _plain_text(index_html + " " + accessible_figures_html)
    raw_text = html.unescape(index_html + " " + accessible_figures_html)
    missing = [
        marker
        for marker in FED_INDIRECT_CREDIT_ACCESSIBLE_EXPECTED_MARKERS
        if marker not in combined_text and marker not in raw_text
    ]
    if missing:
        raise ValueError(
            "Fed indirect-credit accessible materials missing markers: "
            + "; ".join(missing)
        )

    records: list[dict[str, str]] = []
    for figure_index, figure_match in enumerate(
        re.finditer(
            r'<div id="(?P<figure_id>fig\d+)">(?P<figure_html>.*?)</div>',
            accessible_figures_html,
            flags=re.DOTALL | re.IGNORECASE,
        ),
        start=1,
    ):
        figure_html = figure_match.group("figure_html")
        title_match = re.search(
            r"<strong>(?P<title>.*?)</strong>",
            figure_html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        if title_match is None:
            continue
        title = _clean_source_text(title_match.group("title")).rstrip(": ")
        figure_text = _clean_source_text(figure_html)
        pass_through_context = title in {
            "Figure 2: Interest Rate on Bank Loans: BDCs versus non-BDCs",
            "Figure 4: BDCs' Financing: the increasing reliance on banks",
            "Figure 5: Aggregate Credit Volume and Borrowing Costs for Nonfinancial Businesses",
        }
        records.append(
            {
                "date": "2025-10-22",
                "source_record_type": "accessible_figure_description",
                "source_record_index_one_based": str(figure_index),
                "source_figure_id": figure_match.group("figure_id"),
                "source_table_title": "",
                "source_figure_title": title,
                "source_row_label": title,
                "source_column_label": "accessible_description",
                "metric": _slug(title),
                "metric_value": "accessible_description_available",
                "metric_value_raw": figure_text,
                "metric_unit": "qualitative_accessible_description",
                "coefficient": "",
                "standard_error": "",
                "significance_stars": "",
                "sample_start": "2012Q3",
                "sample_end": "2023Q4",
                "evidence_family": "private_credit_intermediation_context",
                "source_zip_schema_reviewed": "true",
                "bank_bdc_intermediation_context_available": "true",
                "borrower_pass_through_context_available": str(
                    pass_through_context
                ).lower(),
                "nonbank_to_real_activity_context_available": "false",
                "public_reusable_loan_level_artifact_available": "false",
                "underlying_supervisory_or_proprietary_data": "true",
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )

    for table_title, (
        base_metric,
        sample_start,
        sample_end,
        evidence_family,
    ) in FED_INDIRECT_CREDIT_ACCESSIBLE_TABLES.items():
        table_html = _table_after_title(index_html, table_title)
        table_rows = _generic_html_table_rows(table_html)
        if not table_rows:
            raise ValueError(
                f"Fed indirect-credit accessible table has no rows: {table_title}"
            )
        for row_index, (row_label, headers, values) in enumerate(table_rows, start=1):
            for column_index, (column_label, value) in enumerate(
                zip(headers, values, strict=True),
                start=1,
            ):
                if not value or value == "&nbsp;":
                    continue
                coefficient, stars, standard_error = _regression_cell_parts(value)
                records.append(
                    {
                        "date": "2025-10-22",
                        "source_record_type": "regression_table_cell",
                        "source_record_index_one_based": str(row_index),
                        "source_figure_id": "",
                        "source_table_title": table_title,
                        "source_figure_title": "",
                        "source_row_label": row_label,
                        "source_column_label": column_label,
                        "metric": (
                            f"{base_metric}_{_slug(row_label)}_{_slug(column_label)}"
                        ),
                        "metric_value": coefficient,
                        "metric_value_raw": value,
                        "metric_unit": "regression_table_cell",
                        "coefficient": coefficient,
                        "standard_error": standard_error,
                        "significance_stars": stars,
                        "sample_start": sample_start,
                        "sample_end": sample_end,
                        "evidence_family": evidence_family,
                        "source_zip_schema_reviewed": "true",
                        "bank_bdc_intermediation_context_available": "true",
                        "borrower_pass_through_context_available": str(
                            evidence_family == "borrower_pass_through"
                        ).lower(),
                        "nonbank_to_real_activity_context_available": str(
                            evidence_family == "nonbank_to_real_activity"
                        ).lower(),
                        "public_reusable_loan_level_artifact_available": "false",
                        "underlying_supervisory_or_proprietary_data": "true",
                        "denominator_prior_narrowing_allowed": "false",
                        "split_denominator_promotion_allowed": "false",
                        "formula_replacement_allowed": "false",
                        "main_ratio_admission_allowed": "false",
                        "incidence_output_enabled": "false",
                        "welfare_tax_mpc_output_enabled": "false",
                    }
                )
    return records


def _fed_indirect_credit_accessible_materials_snapshot(
    *, registry: SourceRegistry, source_zip: Path
) -> SourceSnapshot:
    series = registry.series[FED_INDIRECT_CREDIT_ACCESSIBLE_MATERIALS_SERIES_ID]
    if not source_zip.exists():
        _download_source(series.endpoint, source_zip)
    with zipfile.ZipFile(source_zip) as archive:
        missing = [
            expected
            for expected in FED_INDIRECT_CREDIT_ACCESSIBLE_EXPECTED_FILES
            if expected not in archive.namelist()
        ]
        if missing:
            raise ValueError(
                "Fed indirect-credit accessible ZIP missing expected files: "
                + "; ".join(missing)
            )
        index_html = archive.read("index.html").decode("utf-8", errors="replace")
        figures_html = archive.read("accessible_figures.html").decode(
            "utf-8", errors="replace"
        )
    records = _fed_indirect_credit_accessible_material_records(
        index_html=index_html,
        accessible_figures_html=figures_html,
    )
    zip_hash = _file_sha256(source_zip)
    index_hash = hashlib.sha256(index_html.encode("utf-8")).hexdigest()
    figures_hash = hashlib.sha256(figures_html.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    note = (
        "fed_indirect_credit_supply_accessible_materials_context_only;"
        f"source_zip_sha256={zip_hash};"
        f"index_html_sha256={index_hash};"
        f"accessible_figures_html_sha256={figures_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "tables=Table 8 monetary pass-through,Table 9 real effects;"
        "figures=accessible Figure 1-Figure 5 and appendix figures;"
        "bank_bdc_intermediation_context_available=true;"
        "borrower_pass_through_context_available=true;"
        "nonbank_to_real_activity_context_available=true;"
        "public_reusable_loan_level_artifact_available=false;"
        "underlying_supervisory_or_proprietary_data=true;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2025-10-22",
            snapshot_kind="live_accessible_zip_context",
            note=note,
        ),
        records=records,
    )


def _fed_credit_bureau_household_dsr_records(
    html_text: str, article_text: str | None = None
) -> list[dict[str, str]]:
    plain = _plain_text(html_text)
    article_plain = _plain_text(article_text or html_text)
    marker_search_text = plain.replace("\u2011", "-")
    article_marker_search_text = article_plain.replace("\u2011", "-")
    missing = [
        marker
        for marker in FED_CREDIT_BUREAU_HOUSEHOLD_DSR_MARKERS
        if marker not in marker_search_text
    ]
    if missing:
        raise ValueError(
            "Fed credit-bureau household DSR accessible data missing markers: "
            + "; ".join(missing)
        )
    article_missing = [
        marker
        for marker in FED_CREDIT_BUREAU_HOUSEHOLD_DSR_ARTICLE_MARKERS
        if marker not in article_marker_search_text
    ]
    if article_missing:
        raise ValueError(
            "Fed credit-bureau household DSR article missing markers: "
            + "; ".join(article_missing)
        )
    table_html_blocks = re.findall(
        r"<table.*?</table>",
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if len(table_html_blocks) != len(FED_CREDIT_BUREAU_HOUSEHOLD_DSR_TABLES):
        raise ValueError(
            "Fed credit-bureau household DSR accessible data expected "
            f"{len(FED_CREDIT_BUREAU_HOUSEHOLD_DSR_TABLES)} tables, found "
            f"{len(table_html_blocks)}"
        )

    records: list[dict[str, str]] = []
    for table_index, (component, source_figure) in enumerate(
        FED_CREDIT_BUREAU_HOUSEHOLD_DSR_TABLES
    ):
        rows = _html_table_rows(table_html_blocks[table_index])
        if not rows:
            raise ValueError(
                "Fed credit-bureau household DSR accessible table "
                f"{table_index + 1} is empty"
            )
        expected_header = ["Quarter", "Old Methodology", "Credit Bureau Methodology"]
        if rows[0] != expected_header:
            raise ValueError(
                "Fed credit-bureau household DSR accessible table "
                f"{table_index + 1} has unexpected header: {rows[0]}"
            )
        for source_row_number, row in enumerate(rows[1:], start=2):
            if len(row) != 3:
                raise ValueError(
                    "Fed credit-bureau household DSR accessible table "
                    f"{table_index + 1} row {source_row_number} has "
                    f"{len(row)} cells"
                )
            quarter, old_methodology, credit_bureau_methodology = row
            records.append(
                {
                    "date": _quarter_end_date(quarter.upper()),
                    "source_row_number_one_based": str(source_row_number),
                    "source_table_index": str(table_index + 1),
                    "source_figure": source_figure,
                    "component": component,
                    "quarter": quarter.upper(),
                    "old_methodology_dsr_pct_dpi": _clean_published_number(
                        old_methodology
                    ),
                    "credit_bureau_methodology_dsr_pct_dpi": _clean_published_number(
                        credit_bureau_methodology
                    ),
                    "metric_unit": "percent_of_disposable_personal_income",
                    "credit_bureau_scheduled_payment_context_available": "true",
                    "consumer_debt_component": str(
                        component == "consumer_debt_dsr"
                    ).lower(),
                    "credit_card_minimum_payment_method_context_available": "true",
                    "direct_required_payment_context_available": "true",
                    "borrower_level_microdata_publicly_reusable": "false",
                    "income_matched_to_borrower_records_available": "false",
                    "rate_sensitive_payment_drag_transmission_available": "false",
                    "current_demand_response_available": "false",
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


def _fed_credit_bureau_household_dsr_snapshot(
    *, registry: SourceRegistry, source_html: Path, article_html: Path
) -> SourceSnapshot:
    series = registry.series[FED_CREDIT_BUREAU_HOUSEHOLD_DSR_SERIES_ID]
    if not source_html.exists():
        _download_source(series.endpoint, source_html)
    article_url = series.endpoint.replace("20240904.htm", "20240904.html")
    if not article_html.exists():
        _download_source(article_url, article_html)
    html_text = source_html.read_text(encoding="utf-8")
    article_text = article_html.read_text(encoding="utf-8")
    records = _fed_credit_bureau_household_dsr_records(
        html_text,
        article_text,
    )
    source_html_hash = _file_sha256(source_html)
    article_html_hash = _file_sha256(article_html)
    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    component_counts = {
        component: sum(record["component"] == component for record in records)
        for component, _ in FED_CREDIT_BUREAU_HOUSEHOLD_DSR_TABLES
    }
    note = (
        "fed_credit_bureau_household_dsr_scheduled_payment_context_only;"
        f"source_html_sha256={source_html_hash};"
        f"source_article_html_sha256={article_html_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "source_table_count=3;"
        "component_counts="
        + ",".join(f"{key}:{value}" for key, value in component_counts.items())
        + ";"
        "credit_bureau_scheduled_payment_context_available=true;"
        "direct_required_payment_context_available=true;"
        "credit_card_minimum_payment_method_context_available=true;"
        "borrower_level_microdata_publicly_reusable=false;"
        "income_matched_to_borrower_records_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2024-09-04",
            snapshot_kind="live_accessible_html_table_context",
            note=note,
        ),
        records=records,
    )


def _fed_student_loan_payment_restart_spending_records(
    html_text: str, accessible_html: str
) -> list[dict[str, str]]:
    text = _plain_text(html_text)
    accessible_text = _plain_text(accessible_html)
    missing = [
        marker
        for marker in FED_STUDENT_LOAN_PAYMENT_RESTART_MARKERS
        if marker not in text
    ]
    missing.extend(
        marker
        for marker in FED_STUDENT_LOAN_PAYMENT_RESTART_ACCESSIBLE_MARKERS
        if marker not in accessible_text
    )
    if missing:
        raise ValueError(
            "Fed student-loan payment restart note missing expected markers: "
            + "; ".join(missing)
        )
    base_record = {
        "date": "2025-09-05",
        "publication_date": "2025-09-05",
        "source_page_schema_reviewed": "true",
        "source_accessible_page_reviewed": "true",
        "debt_payment_spending_response_context_available": "true",
        "student_loan_specific_context_available": "true",
        "monetary_rate_shock_payment_drag_transmission_available": "false",
        "fast_repricing_credit_card_auto_context_available": "false",
        "public_borrower_level_microdata_available": "false",
        "underlying_spending_data_publicly_reusable": "false",
        "current_demand_response_prior_narrowing_allowed": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "method_blocker": (
            "student_loan_payment_restart_spending_response_context_is_not_"
            "a_monetary_policy_rate_shock_or_fast_repricing_credit_card_auto_"
            "bridge_and_underlying_zip_spending_ccp_microdata_are_not_publicly_"
            "reusable"
        ),
    }
    rows = [
        {
            "metric": "spending_panel_coverage_context",
            "metric_value": (
                "55_million_individuals;89_million_cards;800_billion_annual_sales"
            ),
            "metric_unit": "verisk_aggregate_transaction_panel_context",
            "confidence_interval_95": "",
            "evidence_family": "spending_panel_context",
            "source_marker": "Verisk Commerce Signals Spend Tracker",
        },
        {
            "metric": "student_loan_ccp_zip_model_sample_context",
            "metric_value": "18178_zip_codes;1.25_trillion_eligible_student_debt",
            "metric_unit": "zip_level_ccp_student_loan_context",
            "confidence_interval_95": "",
            "evidence_family": "student_loan_balance_exposure_context",
            "source_marker": "FRBNY/Equifax Consumer Credit Panel",
        },
        {
            "metric": "post_announcement_spending_response_per_10000_debt",
            "metric_value": "-6.20",
            "metric_unit": "weekly_dollars_per_10000_student_loan_balance",
            "confidence_interval_95": "-11_to_-2",
            "evidence_family": "current_demand_response_context",
            "source_marker": "Figure 3 accessible text",
        },
        {
            "metric": "payment_resumption_spending_response_per_10000_debt",
            "metric_value": "-12.20",
            "metric_unit": "weekly_dollars_per_10000_student_loan_balance",
            "confidence_interval_95": "-17_to_-7",
            "evidence_family": "current_demand_response_context",
            "source_marker": "Figure 3 accessible text",
        },
        {
            "metric": "annualized_aggregate_demand_drag_context",
            "metric_value": "80_billion_annual_rate;0.3_percent_gdp;0.4_percent_pce",
            "metric_unit": "partial_equilibrium_back_of_envelope_context",
            "confidence_interval_95": "",
            "evidence_family": "aggregate_current_demand_context",
            "source_marker": "aggregate demand paragraph",
        },
        {
            "metric": "promotion_blocker_context",
            "metric_value": (
                "not_monetary_rate_shock;not_fast_repricing_credit_card_auto;"
                "underlying_spending_and_ccp_microdata_not_publicly_reusable"
            ),
            "metric_unit": "method_blocker",
            "confidence_interval_95": "",
            "evidence_family": "consumer_credit_promotion_blocker",
            "source_marker": "data limitations and footnotes",
        },
    ]
    records: list[dict[str, str]] = []
    for row_index, row in enumerate(rows, start=1):
        records.append(
            {
                **base_record,
                **row,
                "source_record_index_one_based": str(row_index),
                "current_demand_response_context_available": str(
                    row["evidence_family"]
                    in {
                        "current_demand_response_context",
                        "aggregate_current_demand_context",
                    }
                ).lower(),
            }
        )
    return records


def _fed_student_loan_payment_restart_spending_snapshot(
    *,
    registry: SourceRegistry,
    source_html: Path,
    source_accessible_html: Path,
) -> SourceSnapshot:
    series = registry.series[FED_STUDENT_LOAN_PAYMENT_RESTART_SPENDING_SERIES_ID]
    if not source_html.exists():
        _download_source(series.endpoint, source_html)
    if not source_accessible_html.exists():
        _download_source(
            FED_STUDENT_LOAN_PAYMENT_RESTART_ACCESSIBLE_URL,
            source_accessible_html,
        )
    html_text = source_html.read_text(encoding="utf-8", errors="replace")
    accessible_html = source_accessible_html.read_text(
        encoding="utf-8",
        errors="replace",
    )
    records = _fed_student_loan_payment_restart_spending_records(
        html_text,
        accessible_html,
    )
    html_hash = _file_sha256(source_html)
    accessible_hash = _file_sha256(source_accessible_html)
    records_hash = _records_sha256(records)
    note = (
        "fed_student_loan_payment_restart_spending_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_accessible_html_sha256={accessible_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "first_observation_date=2025-09-05;"
        "latest_observation_date=2025-09-05;"
        "debt_payment_spending_response_context_available=true;"
        "current_demand_response_context_available=true;"
        "student_loan_specific_context_available=true;"
        "monetary_rate_shock_payment_drag_transmission_available=false;"
        "fast_repricing_credit_card_auto_context_available=false;"
        "public_borrower_level_microdata_available=false;"
        "underlying_spending_data_publicly_reusable=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2025-09-05",
            snapshot_kind="live_html_and_accessible_context",
            note=note,
        ),
        records=records,
    )


def _fed_credit_card_limit_increase_debt_records(
    html_text: str, accessible_html: str
) -> list[dict[str, str]]:
    text = _plain_text(html_text).replace("\u2011", "-")
    accessible_text = _plain_text(accessible_html).replace("\u2011", "-")
    missing = [
        marker
        for marker in FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_MARKERS
        if marker not in text
    ]
    missing.extend(
        marker
        for marker in FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_ACCESSIBLE_MARKERS
        if marker not in accessible_text
    )
    if missing:
        raise ValueError(
            "Fed credit-card limit-increase debt note missing expected markers: "
            + "; ".join(missing)
        )
    base_record = {
        "date": "2026-01-16",
        "publication_date": "2026-01-16",
        "source_page_schema_reviewed": "true",
        "source_accessible_page_reviewed": "true",
        "fr_y14m_regulatory_data_context_available": "true",
        "credit_card_limit_increase_context_available": "true",
        "credit_card_debt_response_context_available": "true",
        "revolver_transactor_context_available": "true",
        "borrower_level_credit_score_context_available": "true",
        "underlying_account_microdata_publicly_reusable": "false",
        "public_borrower_level_microdata_available": "false",
        "monetary_rate_shock_payment_drag_transmission_available": "false",
        "fast_repricing_credit_card_auto_context_available": "false",
        "rate_sensitive_payment_drag_transmission_available": "false",
        "current_demand_response_available": "false",
        "current_demand_conversion_available": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "empirical_threshold_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
        "method_blocker": (
            "feds_note_supplies_fr_y14m_credit_card_limit_increase_and_debt_"
            "response_context_but_not_monetary_policy_rate_shock_fast_"
            "repricing_payment_drag_or_current_demand_transmission_and_"
            "underlying_account_level_regulatory_microdata_are_not_publicly_"
            "reusable"
        ),
    }
    rows = [
        {
            "metric": "fr_y14m_credit_card_market_coverage_context",
            "metric_value": "70",
            "metric_unit": "percent_of_us_credit_card_market_more_than",
            "evidence_family": "regulatory_data_coverage_context",
            "source_marker": "Federal Reserve Y-14M regulatory data",
        },
        {
            "metric": "annual_limit_increase_incidence_context",
            "metric_value": "12",
            "metric_unit": "percent_of_credit_cards_per_year",
            "evidence_family": "limit_increase_scale_context",
            "source_marker": "About 12 percent of credit cards receive limit increases annually",
        },
        {
            "metric": "annual_new_available_credit_context",
            "metric_value": "160",
            "metric_unit": "billions_of_dollars_per_year",
            "evidence_family": "limit_increase_scale_context",
            "source_marker": "about $160 billion dollars of new available credit each year",
        },
        {
            "metric": "bank_initiated_limit_increase_share_context",
            "metric_value": "80",
            "metric_unit": "percent_of_limit_increases",
            "evidence_family": "limit_increase_source_context",
            "source_marker": "approximately 80 percent",
        },
        {
            "metric": "quarterly_revolver_transactor_bank_increase_context",
            "metric_value": "revolvers_almost_4_percent;transactors_roughly_2_percent",
            "metric_unit": "quarterly_probability_context",
            "evidence_family": "revolver_targeting_context",
            "source_marker": "Figure 2 accessible text",
        },
        {
            "metric": "six_month_debt_response_after_limit_increase_context",
            "metric_value": "30",
            "metric_unit": "percent_of_credit_limit_increase",
            "evidence_family": "debt_response_context",
            "source_marker": "Figure 3 accessible text",
        },
        {
            "metric": "subprime_low_and_grow_limit_context",
            "metric_value": "origination_700;five_year_2700;growth_285",
            "metric_unit": "dollars_and_percent_growth_context",
            "evidence_family": "credit_score_limit_growth_context",
            "source_marker": "Figure 1 accessible text",
        },
        {
            "metric": "promotion_blocker_context",
            "metric_value": (
                "not_monetary_rate_shock;not_fast_repricing_payment_drag;"
                "not_current_demand_response;underlying_y14m_microdata_not_"
                "publicly_reusable"
            ),
            "metric_unit": "method_blocker",
            "evidence_family": "consumer_credit_promotion_blocker",
            "source_marker": "source design and data access limitation",
        },
    ]
    records: list[dict[str, str]] = []
    for row_index, row in enumerate(rows, start=1):
        records.append(
            {
                **base_record,
                **row,
                "source_record_index_one_based": str(row_index),
            }
        )
    return records


def _fed_credit_card_limit_increase_debt_snapshot(
    *,
    registry: SourceRegistry,
    source_html: Path,
    source_accessible_html: Path,
) -> SourceSnapshot:
    series = registry.series[FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_SERIES_ID]
    if not source_html.exists():
        _download_source(series.endpoint, source_html)
    if not source_accessible_html.exists():
        _download_source(
            FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_ACCESSIBLE_URL,
            source_accessible_html,
        )
    html_text = source_html.read_text(encoding="utf-8", errors="replace")
    accessible_html = source_accessible_html.read_text(
        encoding="utf-8",
        errors="replace",
    )
    records = _fed_credit_card_limit_increase_debt_records(
        html_text,
        accessible_html,
    )
    html_hash = _file_sha256(source_html)
    accessible_hash = _file_sha256(source_accessible_html)
    records_hash = _records_sha256(records)
    note = (
        "fed_credit_card_limit_increase_debt_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_accessible_html_sha256={accessible_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "first_observation_date=2026-01-16;"
        "latest_observation_date=2026-01-16;"
        "fr_y14m_regulatory_data_context_available=true;"
        "credit_card_limit_increase_context_available=true;"
        "credit_card_debt_response_context_available=true;"
        "revolver_transactor_context_available=true;"
        "underlying_account_microdata_publicly_reusable=false;"
        "public_borrower_level_microdata_available=false;"
        "monetary_rate_shock_payment_drag_transmission_available=false;"
        "fast_repricing_credit_card_auto_context_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2026-01-16",
            snapshot_kind="live_html_and_accessible_context",
            note=note,
        ),
        records=records,
    )


def _fed_credit_card_profitability_revolver_records(
    html_text: str,
) -> list[dict[str, str]]:
    text = _plain_text(html_text).replace("\u2011", "-")
    missing = [
        marker for marker in FED_CREDIT_CARD_PROFITABILITY_MARKERS if marker not in text
    ]
    if missing:
        raise ValueError(
            "Fed credit-card profitability note missing expected markers: "
            + "; ".join(missing)
        )

    table_title = "Table 1. Costs of Using a Credit Card"
    table_html = _table_after_title(html_text, table_title)
    table_rows = _generic_html_table_rows(table_html)
    if not table_rows:
        raise ValueError("Fed credit-card profitability Table 1 has no parsed rows")

    account_segments = (
        "heavy_revolver",
        "light_revolver",
        "transactor",
        "other_or_new_inactive",
    )
    allowed_metrics = {
        "Number of Accounts (in millions)": "millions_of_accounts",
        "Purchase Volume": "monthly_dollars_per_account_or_share",
        "Balance": "monthly_dollars_per_account_or_share",
        "Revolving Balance": "monthly_dollars_per_account_or_share",
        "Spread": "percent",
        "Interest Charge": "monthly_dollars_per_account_or_share",
        "Late Fee": "monthly_dollars_per_account_or_share",
        "Annual Fee": "monthly_dollars_per_account_or_share",
        "Other Fee": "monthly_dollars_per_account_or_share",
    }
    base_record = {
        "date": "2019-12-31",
        "publication_date": "2022-09-09",
        "sample_start": "2014-01-01",
        "sample_end": "2019-12-31",
        "source_page_schema_reviewed": "true",
        "source_table_reviewed": "true",
        "source_table_title": table_title,
        "fr_y14m_regulatory_data_context_available": "true",
        "large_issuer_credit_card_context_available": "true",
        "revolver_transactor_payment_burden_context_available": "true",
        "credit_card_payment_drag_magnitude_context_available": "true",
        "underlying_account_microdata_publicly_reusable": "false",
        "public_borrower_level_microdata_available": "false",
        "monetary_rate_shock_payment_drag_transmission_available": "false",
        "fast_repricing_credit_card_auto_context_available": "false",
        "rate_sensitive_payment_drag_transmission_available": "false",
        "current_demand_response_available": "false",
        "current_demand_conversion_available": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "empirical_threshold_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
        "method_blocker": (
            "feds_note_supplies_y14m_credit_card_revolver_transactor_"
            "interest_fee_balance_purchase_context_but_not_monetary_policy_"
            "rate_shock_fast_repricing_payment_drag_transmission_current_"
            "demand_response_or_public_reusable_account_microdata"
        ),
    }

    records: list[dict[str, str]] = []
    for row_label, _headers, values in table_rows:
        clean_row_label = _clean_source_text(row_label)
        if clean_row_label not in allowed_metrics:
            continue
        if len(values) != len(account_segments) * 2:
            raise ValueError(
                "Fed credit-card profitability Table 1 expected mean/share "
                f"pairs for {clean_row_label}, found {len(values)} cells"
            )
        for segment_index, segment in enumerate(account_segments):
            mean_value = values[segment_index * 2]
            share_value = values[(segment_index * 2) + 1]
            for value_type, raw_value, value_unit in (
                ("mean", mean_value, allowed_metrics[clean_row_label]),
                ("share", share_value, "percent_share"),
            ):
                if raw_value == "---":
                    continue
                records.append(
                    {
                        **base_record,
                        "source_record_type": "table_1_summary_cell",
                        "source_record_index_one_based": str(len(records) + 1),
                        "source_row_label": clean_row_label,
                        "account_usage_segment": segment,
                        "metric": (
                            "credit_card_profitability_"
                            f"{_slug(clean_row_label)}_{segment}_{value_type}"
                        ),
                        "metric_value": _normalize_source_number(raw_value),
                        "metric_value_raw": raw_value,
                        "metric_unit": value_unit,
                        "metric_value_type": value_type,
                        "evidence_family": (
                            "payment_drag_magnitude_context"
                            if clean_row_label
                            in {
                                "Interest Charge",
                                "Late Fee",
                                "Annual Fee",
                                "Other Fee",
                            }
                            else "revolver_transactor_balance_purchase_context"
                        ),
                    }
                )
    return records


def _fed_credit_card_profitability_revolver_snapshot(
    *,
    registry: SourceRegistry,
    source_html: Path,
) -> SourceSnapshot:
    series = registry.series[FED_CREDIT_CARD_PROFITABILITY_REVOLVER_SERIES_ID]
    if not source_html.exists():
        _download_source(series.endpoint, source_html)
    html_text = source_html.read_text(encoding="utf-8", errors="replace")
    records = _fed_credit_card_profitability_revolver_records(html_text)
    html_hash = _file_sha256(source_html)
    records_hash = _records_sha256(records)
    note = (
        "fed_credit_card_profitability_revolver_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "first_observation_date=2014-01-01;"
        "latest_observation_date=2019-12-31;"
        "fr_y14m_regulatory_data_context_available=true;"
        "revolver_transactor_payment_burden_context_available=true;"
        "credit_card_payment_drag_magnitude_context_available=true;"
        "underlying_account_microdata_publicly_reusable=false;"
        "public_borrower_level_microdata_available=false;"
        "monetary_rate_shock_payment_drag_transmission_available=false;"
        "fast_repricing_credit_card_auto_context_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2022-09-09",
            snapshot_kind="live_html_table_context",
            note=note,
        ),
        records=records,
    )


def _fed_credit_card_delinquency_prediction_records(
    *, html_text: str, accessible_html: str
) -> list[dict[str, str]]:
    page_text = _plain_text(html_text).replace("\u2011", "-")
    accessible_text = _plain_text(accessible_html).replace("\u2011", "-")
    missing_page = [
        marker
        for marker in FED_CREDIT_CARD_DELINQUENCY_PREDICTION_MARKERS
        if marker not in page_text
    ]
    missing_accessible = [
        marker
        for marker in FED_CREDIT_CARD_DELINQUENCY_PREDICTION_ACCESSIBLE_MARKERS
        if marker not in accessible_text
    ]
    if missing_page or missing_accessible:
        raise ValueError(
            "Fed credit-card delinquency prediction note missing expected markers: "
            + "; ".join(missing_page + missing_accessible)
        )

    tables = re.findall(
        r"<table.*?</table>", accessible_html, flags=re.DOTALL | re.IGNORECASE
    )
    if len(tables) != len(FED_CREDIT_CARD_DELINQUENCY_PREDICTION_TABLE_TITLES):
        raise ValueError(
            "Fed credit-card delinquency prediction accessible page expected "
            f"{len(FED_CREDIT_CARD_DELINQUENCY_PREDICTION_TABLE_TITLES)} tables, "
            f"found {len(tables)}"
        )

    base_record = {
        "publication_date": "2025-02-28",
        "sample_start": "2000-03-31",
        "sample_end": "2019-12-31",
        "out_of_sample_start": "2023-03-31",
        "out_of_sample_end": "2024-09-30",
        "source_page_schema_reviewed": "true",
        "source_accessible_page_reviewed": "true",
        "credit_card_delinquency_prediction_context_available": "true",
        "rate_sensitive_model_context_available": "true",
        "prime_rate_context_available": "true",
        "sloos_tightening_context_available": "true",
        "nonprime_balance_context_available": "true",
        "underlying_account_microdata_publicly_reusable": "false",
        "public_borrower_level_microdata_available": "false",
        "monetary_rate_shock_payment_drag_transmission_available": "false",
        "fast_repricing_credit_card_auto_context_available": "false",
        "rate_sensitive_payment_drag_transmission_available": "false",
        "current_demand_response_available": "false",
        "current_demand_conversion_available": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "empirical_threshold_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
        "method_blocker": (
            "feds_note_supplies_credit_card_delinquency_prediction_and_"
            "prime_rate_sloos_nonprime_balance_model_context_but_not_"
            "monetary_policy_rate_shock_payment_drag_transmission_current_"
            "demand_response_or_public_reusable_borrower_microdata"
        ),
    }

    records: list[dict[str, str]] = []
    for table_index, table_html in enumerate(tables, start=1):
        parsed_rows = _html_table_rows(table_html)
        if len(parsed_rows) < 2:
            raise ValueError(
                "Fed credit-card delinquency prediction accessible table "
                f"{table_index} has no parsed data rows"
            )
        headers = [_clean_source_text(header) for header in parsed_rows[0]]
        if headers[0] != "Date":
            raise ValueError(
                "Fed credit-card delinquency prediction accessible table "
                f"{table_index} first header is not Date"
            )
        table_title = FED_CREDIT_CARD_DELINQUENCY_PREDICTION_TABLE_TITLES[
            table_index - 1
        ]
        for row_number, row in enumerate(parsed_rows[1:], start=1):
            if len(row) != len(headers):
                raise ValueError(
                    "Fed credit-card delinquency prediction accessible table "
                    f"{table_index} row {row_number} expected {len(headers)} "
                    f"cells, found {len(row)}"
                )
            date_label = _clean_source_text(row[0])
            values = {
                _slug(header): _normalize_source_number(value)
                for header, value in zip(headers[1:], row[1:])
            }
            records.append(
                {
                    **base_record,
                    "date": _period_label_to_date(date_label),
                    "source_record_type": "accessible_table_row",
                    "source_record_index_one_based": str(len(records) + 1),
                    "source_table_index": str(table_index),
                    "source_table_title": table_title,
                    "source_row_label": date_label,
                    "metric": f"credit_card_delinquency_prediction_{table_title}",
                    "metric_value": json.dumps(values, sort_keys=True),
                    "metric_value_raw": "|".join(row[1:]),
                    "metric_unit": "percentage_points_or_contribution_points",
                    "metric_value_type": "accessible_table_row_values",
                    "evidence_family": (
                        "rate_sensitive_model_context"
                        if table_index in {2, 3, 4}
                        else "delinquency_rate_context"
                    ),
                }
            )

    summary_metrics = (
        (
            "model_estimation_sample_window_context",
            "2000Q1_2019Q4",
            "quarter_range",
            "rate_sensitive_model_context",
        ),
        (
            "preferred_model_explanatory_variables_context",
            "prime_rate;unemployment_rate;real_revolving_consumer_credit;"
            "sloos_tightening_lag_four_quarters;nonprime_balance_share_lag_four_quarters",
            "variable_list",
            "rate_sensitive_model_context",
        ),
        (
            "preferred_model_adjusted_r_squared_context",
            "0.97",
            "adjusted_r_squared",
            "rate_sensitive_model_context",
        ),
        (
            "predicted_postpandemic_delinquency_increase_context",
            "120",
            "basis_points",
            "out_of_sample_prediction_context",
        ),
        (
            "out_of_sample_prediction_window_context",
            "2023Q1_2024Q3",
            "quarter_range",
            "out_of_sample_prediction_context",
        ),
        (
            "monetary_policy_causal_inference_blocker_context",
            "source_says_explanatory_variables_can_affect_one_another_so_causal_inferences_not_available",
            "text",
            "promotion_blocker_context",
        ),
        (
            "public_reusable_microdata_blocker_context",
            "underlying_credit_bureau_and_model_source_microdata_not_public_reusable_from_note",
            "text",
            "promotion_blocker_context",
        ),
        (
            "payment_drag_current_demand_blocker_context",
            "delinquency_prediction_model_not_payment_drag_magnitude_or_current_demand_response_design",
            "text",
            "promotion_blocker_context",
        ),
    )
    for metric, value, unit, evidence_family in summary_metrics:
        records.append(
            {
                **base_record,
                "date": "2025-02-28",
                "source_record_type": "note_summary_context",
                "source_record_index_one_based": str(len(records) + 1),
                "source_table_index": "",
                "source_table_title": "",
                "source_row_label": metric,
                "metric": metric,
                "metric_value": value,
                "metric_value_raw": value,
                "metric_unit": unit,
                "metric_value_type": "note_summary_context",
                "evidence_family": evidence_family,
            }
        )
    return records


def _fed_credit_card_delinquency_prediction_snapshot(
    *,
    registry: SourceRegistry,
    source_html: Path,
    source_accessible_html: Path,
) -> SourceSnapshot:
    series = registry.series[FED_CREDIT_CARD_DELINQUENCY_PREDICTION_SERIES_ID]
    if not source_html.exists():
        _download_source(series.endpoint, source_html)
    if not source_accessible_html.exists():
        _download_source(
            FED_CREDIT_CARD_DELINQUENCY_PREDICTION_ACCESSIBLE_URL,
            source_accessible_html,
        )
    html_text = source_html.read_text(encoding="utf-8", errors="replace")
    accessible_html = source_accessible_html.read_text(
        encoding="utf-8", errors="replace"
    )
    records = _fed_credit_card_delinquency_prediction_records(
        html_text=html_text, accessible_html=accessible_html
    )
    first_date, latest_date = _date_range(
        SourceSnapshot(
            metadata=RetrievalMetadata(
                source_id=series.source,
                series_id=series.series_id,
                source_url=series.endpoint,
                units=series.units,
                frequency=series.frequency,
                transform=series.transform,
                retrieved_at=utc_now_iso(),
            ),
            records=records,
        )
    )
    html_hash = _file_sha256(source_html)
    accessible_hash = _file_sha256(source_accessible_html)
    records_hash = _records_sha256(records)
    note = (
        "fed_credit_card_delinquency_prediction_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_accessible_html_sha256={accessible_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "credit_card_delinquency_prediction_context_available=true;"
        "rate_sensitive_model_context_available=true;"
        "prime_rate_context_available=true;"
        "sloos_tightening_context_available=true;"
        "nonprime_balance_context_available=true;"
        "underlying_account_microdata_publicly_reusable=false;"
        "public_borrower_level_microdata_available=false;"
        "monetary_rate_shock_payment_drag_transmission_available=false;"
        "fast_repricing_credit_card_auto_context_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2025-02-28",
            snapshot_kind="live_html_and_accessible_table_context",
            note=note,
        ),
        records=records,
    )


def _fed_consumer_delinquency_dynamics_records(
    *, html_text: str, accessible_html: str
) -> list[dict[str, str]]:
    page_text = _plain_text(html.unescape(html_text)).replace("\u2011", "-")
    accessible_text = _plain_text(accessible_html).replace("\u2011", "-")
    missing = [
        marker
        for marker in FED_CONSUMER_DELINQUENCY_DYNAMICS_MARKERS
        if marker not in page_text
    ] + [
        marker
        for marker in FED_CONSUMER_DELINQUENCY_DYNAMICS_ACCESSIBLE_MARKERS
        if marker not in accessible_text
    ]
    if missing:
        raise ValueError(
            "Fed consumer delinquency dynamics note missing expected markers: "
            + "; ".join(missing)
        )

    tables = re.findall(
        r"<table.*?</table>", accessible_html, flags=re.DOTALL | re.IGNORECASE
    )
    if len(tables) != len(FED_CONSUMER_DELINQUENCY_DYNAMICS_TABLE_TITLES):
        raise ValueError(
            "Fed consumer delinquency dynamics accessible page expected "
            f"{len(FED_CONSUMER_DELINQUENCY_DYNAMICS_TABLE_TITLES)} tables, "
            f"found {len(tables)}"
        )

    base_record = {
        "publication_date": "2025-11-24",
        "source_page_schema_reviewed": "true",
        "source_accessible_page_reviewed": "true",
        "ccp_equifax_context_available": "true",
        "credit_card_auto_delinquency_context_available": "true",
        "credit_score_distribution_context_available": "true",
        "income_tract_context_available": "true",
        "mortgage_status_context_available": "true",
        "underlying_credit_bureau_microdata_publicly_reusable": "false",
        "public_borrower_level_microdata_available": "false",
        "monetary_rate_shock_payment_drag_transmission_available": "false",
        "fast_repricing_credit_card_auto_context_available": "false",
        "rate_sensitive_payment_drag_transmission_available": "false",
        "current_demand_response_available": "false",
        "current_demand_conversion_available": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "empirical_threshold_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
        "method_blocker": (
            "feds_note_supplies_public_ccp_equifax_credit_card_auto_"
            "delinquency_distribution_context_but_not_monetary_policy_rate_"
            "shock_payment_drag_transmission_current_demand_response_or_public_"
            "reusable_borrower_microdata"
        ),
    }

    records: list[dict[str, str]] = []
    for table_index, table_html in enumerate(tables, start=1):
        parsed_rows = _html_table_rows(table_html)
        if len(parsed_rows) < 2:
            raise ValueError(
                "Fed consumer delinquency dynamics accessible table "
                f"{table_index} has no parsed data rows"
            )
        headers = [_clean_source_text(header) for header in parsed_rows[0]]
        table_title = FED_CONSUMER_DELINQUENCY_DYNAMICS_TABLE_TITLES[table_index - 1]
        for row_number, row in enumerate(parsed_rows[1:], start=1):
            if len(row) != len(headers):
                raise ValueError(
                    "Fed consumer delinquency dynamics accessible table "
                    f"{table_index} row {row_number} expected {len(headers)} "
                    f"cells, found {len(row)}"
                )
            row_label = _clean_source_text(row[0])
            if headers[0] == "Date":
                date_value = _period_label_to_date(row_label)
                row_axis = "date"
            else:
                date_value = "2025-11-24"
                row_axis = _slug(headers[0])
            records.append(
                {
                    **base_record,
                    "date": date_value,
                    "source_record_type": "accessible_table_row",
                    "source_record_index_one_based": str(len(records) + 1),
                    "source_table_index": str(table_index),
                    "source_table_title": table_title,
                    "source_row_label": row_label,
                    "source_row_axis": row_axis,
                    "metric": f"consumer_delinquency_dynamics_{table_title}",
                    "metric_value": json.dumps(
                        {
                            _slug(header): _normalize_source_number(value)
                            for header, value in zip(headers[1:], row[1:])
                        },
                        sort_keys=True,
                    ),
                    "metric_value_raw": "|".join(row[1:]),
                    "metric_unit": "percent_or_percentage_point_change",
                    "metric_value_type": "accessible_table_row_values",
                    "evidence_family": (
                        "distributional_delinquency_context"
                        if table_index in {2, 6, 7, 8, 9, 10, 11}
                        else "aggregate_delinquency_context"
                    ),
                }
            )
    return records


def _fed_consumer_delinquency_dynamics_snapshot(
    *,
    registry: SourceRegistry,
    source_html: Path,
    source_accessible_html: Path,
) -> SourceSnapshot:
    series = registry.series[FED_CONSUMER_DELINQUENCY_DYNAMICS_SERIES_ID]
    if not source_html.exists():
        _download_source(series.endpoint, source_html)
    if not source_accessible_html.exists():
        _download_source(
            FED_CONSUMER_DELINQUENCY_DYNAMICS_ACCESSIBLE_URL,
            source_accessible_html,
        )
    records = _fed_consumer_delinquency_dynamics_records(
        html_text=source_html.read_text(encoding="utf-8", errors="replace"),
        accessible_html=source_accessible_html.read_text(
            encoding="utf-8", errors="replace"
        ),
    )
    first_date, latest_date = _date_range(
        SourceSnapshot(
            metadata=RetrievalMetadata(
                source_id=series.source,
                series_id=series.series_id,
                source_url=series.endpoint,
                units=series.units,
                frequency=series.frequency,
                transform=series.transform,
                retrieved_at=utc_now_iso(),
            ),
            records=records,
        )
    )
    html_hash = _file_sha256(source_html)
    accessible_hash = _file_sha256(source_accessible_html)
    records_hash = _records_sha256(records)
    note = (
        "fed_consumer_delinquency_dynamics_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_accessible_html_sha256={accessible_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "ccp_equifax_context_available=true;"
        "credit_card_auto_delinquency_context_available=true;"
        "credit_score_distribution_context_available=true;"
        "income_tract_context_available=true;"
        "mortgage_status_context_available=true;"
        "underlying_credit_bureau_microdata_publicly_reusable=false;"
        "public_borrower_level_microdata_available=false;"
        "monetary_rate_shock_payment_drag_transmission_available=false;"
        "fast_repricing_credit_card_auto_context_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2025-11-24",
            snapshot_kind="live_html_and_accessible_table_context",
            note=note,
        ),
        records=records,
    )


def _fed_credit_card_rewards_limit_spending_records(
    *, index_html: str, accessible_figures_html: str
) -> list[dict[str, str]]:
    combined_text = _plain_text(index_html + " " + accessible_figures_html).replace(
        "\u2011", "-"
    )
    raw_text = html.unescape(index_html + " " + accessible_figures_html)
    missing = [
        marker
        for marker in FED_CREDIT_CARD_REWARDS_LIMIT_SPENDING_MARKERS
        if marker not in combined_text and marker not in raw_text
    ]
    if missing:
        raise ValueError(
            "Fed credit-card rewards limit-spending materials missing markers: "
            + "; ".join(missing)
        )

    table_title = "Table 6:  Overindebtedness: Difference-in-Differences Analysis"
    table_html = _table_after_title(index_html, table_title)
    table_rows = _generic_html_table_rows(table_html)
    if not table_rows:
        raise ValueError("Fed credit-card rewards Table 6 has no parsed rows")

    base_record = {
        "date": "2019-03-31",
        "publication_date": "2023-01-20",
        "sample_start": "2018-09-01",
        "sample_end": "2019-09-30",
        "source_zip_schema_reviewed": "true",
        "source_index_html_reviewed": "true",
        "source_accessible_figures_reviewed": "true",
        "fr_y14m_regulatory_data_context_available": "true",
        "credit_limit_increase_design_context_available": "true",
        "credit_card_spending_response_context_available": "true",
        "credit_card_payment_behavior_context_available": "true",
        "credit_card_unpaid_balance_context_available": "true",
        "current_demand_response_context_available": "true",
        "monetary_rate_shock_payment_drag_transmission_available": "false",
        "fast_repricing_credit_card_auto_context_available": "false",
        "rate_sensitive_payment_drag_transmission_available": "false",
        "current_demand_conversion_available": "false",
        "public_borrower_level_microdata_available": "false",
        "underlying_y14m_account_microdata_publicly_reusable": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "tax_output_enabled": "false",
        "empirical_threshold_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
        "method_blocker": (
            "feds_paper_supplies_credit_card_limit_increase_spending_payment_"
            "and_unpaid_balance_response_context_but_not_monetary_policy_rate_"
            "shock_fast_repricing_payment_drag_current_demand_conversion_or_"
            "public_reusable_y14m_account_microdata"
        ),
    }

    records: list[dict[str, str]] = []
    for row_label, headers, values in table_rows:
        clean_row_label = _clean_source_text(row_label)
        if clean_row_label not in {
            "Reward Card",
            "Reward Card x Sub-Prime",
            "Reward Card x Near-Prime",
            "Reward Card x Prime",
            "Reward Card x Super-Prime",
            "* Observations",
        }:
            continue
        for column_label, value in zip(headers, values, strict=True):
            if not value:
                continue
            coefficient, stars, standard_error = _regression_cell_parts(value)
            if clean_row_label == "* Observations":
                coefficient = value.replace(",", "")
                stars = ""
                standard_error = ""
                evidence_family = "sample_support_context"
                metric_unit = "number_of_card_observations"
            elif "Spending" in column_label:
                evidence_family = "current_demand_response_context"
                metric_unit = "dollars_change_in_average_spending"
            elif "Payments" in column_label:
                evidence_family = "payment_response_context"
                metric_unit = "dollars_change_in_average_payments"
            elif "Unpaid Balances" in column_label:
                evidence_family = "unpaid_balance_response_context"
                metric_unit = "dollars_change_in_unpaid_balances"
            else:
                continue
            records.append(
                {
                    **base_record,
                    "source_record_type": (
                        "sample_support_cell"
                        if evidence_family == "sample_support_context"
                        else "regression_table_cell"
                    ),
                    "source_record_index_one_based": str(len(records) + 1),
                    "source_table_title": table_title,
                    "source_row_label": clean_row_label,
                    "source_column_label": _clean_source_text(column_label),
                    "metric": (
                        "credit_card_rewards_limit_increase_"
                        f"{_slug(clean_row_label)}_{_slug(column_label)}"
                    ),
                    "metric_value": coefficient,
                    "metric_value_raw": value,
                    "metric_unit": metric_unit,
                    "coefficient": coefficient,
                    "standard_error": standard_error,
                    "significance_stars": stars,
                    "evidence_family": evidence_family,
                    "current_demand_response_context_available": str(
                        evidence_family == "current_demand_response_context"
                    ).lower(),
                }
            )
    if len(records) < 10:
        raise ValueError(
            "Fed credit-card rewards Table 6 parsed too few usable cells: "
            f"{len(records)}"
        )
    return records


def _fed_credit_card_rewards_limit_spending_snapshot(
    *, registry: SourceRegistry, source_zip: Path
) -> SourceSnapshot:
    series = registry.series[FED_CREDIT_CARD_REWARDS_LIMIT_SPENDING_SERIES_ID]
    if not source_zip.exists():
        _download_source(series.endpoint, source_zip)
    with zipfile.ZipFile(source_zip) as archive:
        missing = [
            expected
            for expected in FED_CREDIT_CARD_REWARDS_LIMIT_SPENDING_EXPECTED_FILES
            if expected not in archive.namelist()
        ]
        if missing:
            raise ValueError(
                "Fed credit-card rewards accessible ZIP missing expected files: "
                + "; ".join(missing)
            )
        index_html = archive.read("index.html").decode("utf-8", errors="replace")
        figures_html = archive.read("accessible_figures.html").decode(
            "utf-8", errors="replace"
        )
    records = _fed_credit_card_rewards_limit_spending_records(
        index_html=index_html,
        accessible_figures_html=figures_html,
    )
    zip_hash = _file_sha256(source_zip)
    index_hash = hashlib.sha256(index_html.encode("utf-8")).hexdigest()
    figures_hash = hashlib.sha256(figures_html.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    note = (
        "fed_credit_card_rewards_limit_spending_context_only;"
        f"source_zip_sha256={zip_hash};"
        f"index_html_sha256={index_hash};"
        f"accessible_figures_html_sha256={figures_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "first_observation_date=2018-09-01;"
        "latest_observation_date=2019-09-30;"
        "fr_y14m_regulatory_data_context_available=true;"
        "credit_limit_increase_design_context_available=true;"
        "credit_card_spending_response_context_available=true;"
        "credit_card_payment_behavior_context_available=true;"
        "credit_card_unpaid_balance_context_available=true;"
        "current_demand_response_context_available=true;"
        "monetary_rate_shock_payment_drag_transmission_available=false;"
        "fast_repricing_credit_card_auto_context_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_conversion_available=false;"
        "public_borrower_level_microdata_available=false;"
        "underlying_y14m_account_microdata_publicly_reusable=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "tax_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2023-01-20",
            snapshot_kind="live_accessible_zip_context",
            note=note,
        ),
        records=records,
    )


def _fed_auto_loan_payment_delinquency_records(
    html_text: str, accessible_html: str
) -> list[dict[str, str]]:
    text = _plain_text(html_text).replace("\u2011", "-")
    accessible_text = _plain_text(accessible_html).replace("\u2011", "-")
    missing = [
        marker
        for marker in FED_AUTO_LOAN_PAYMENT_DELINQUENCY_MARKERS
        if marker not in text
    ]
    missing.extend(
        marker
        for marker in FED_AUTO_LOAN_PAYMENT_DELINQUENCY_ACCESSIBLE_MARKERS
        if marker not in accessible_text
    )
    if missing:
        raise ValueError(
            "Fed auto-loan payment/delinquency note missing expected markers: "
            + "; ".join(missing)
        )
    base_record = {
        "date": "2024-09-26",
        "publication_date": "2024-09-26",
        "source_page_schema_reviewed": "true",
        "source_accessible_page_reviewed": "true",
        "auto_loan_payment_context_available": "true",
        "auto_loan_delinquency_context_available": "true",
        "auto_loan_interest_rate_context_available": "true",
        "borrower_credit_score_context_available": "true",
        "borrower_income_proxy_context_available": "true",
        "rate_sensitive_payment_drag_transmission_available": "false",
        "monetary_rate_shock_payment_drag_transmission_available": "false",
        "current_demand_response_available": "false",
        "current_demand_conversion_available": "false",
        "public_borrower_level_microdata_available": "false",
        "underlying_ccp_experian_microdata_publicly_reusable": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "empirical_threshold_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
        "method_blocker": (
            "feds_note_supplies_auto_loan_monthly_payment_delinquency_credit_"
            "score_income_proxy_and_interest_rate_context_but_not_monetary_"
            "policy_rate_shock_payment_drag_transmission_current_demand_"
            "response_or_public_reusable_ccp_experian_borrower_microdata"
        ),
    }
    rows = [
        {
            "metric": "auto_share_of_nonmortgage_consumer_credit_context",
            "metric_value": "25",
            "metric_unit": "percent_of_nonmortgage_consumer_credit",
            "confidence_interval_95": "",
            "evidence_family": "auto_loan_market_scale_context",
            "source_marker": "introduction market scale",
        },
        {
            "metric": "ccp_auto_loan_analysis_sample_context",
            "metric_value": "one_percent_random_sample;2017_2022_originations",
            "metric_unit": "ccp_auto_loan_origination_sample_context",
            "confidence_interval_95": "",
            "evidence_family": "borrower_level_private_data_context",
            "source_marker": "data section",
        },
        {
            "metric": "auto_delinquency_pre_pandemic_gap_context",
            "metric_value": "60",
            "metric_unit": "basis_points_above_pre_pandemic_end_2023",
            "confidence_interval_95": "",
            "evidence_family": "delinquency_context",
            "source_marker": "recent trends paragraph",
        },
        {
            "metric": "recent_vintage_balance_share_context",
            "metric_value": "37;27",
            "metric_unit": (
                "percent_of_auto_loan_balances_originated_previous_12_months;"
                "percent_originated_previous_13_24_months"
            ),
            "confidence_interval_95": "",
            "evidence_family": "repricing_vintage_context",
            "source_marker": "recent vintage balance shares",
        },
        {
            "metric": "average_required_monthly_payment_increase_context",
            "metric_value": "470_to_600",
            "metric_unit": "dollars_jan_2020_to_jan_2023",
            "confidence_interval_95": "",
            "evidence_family": "payment_drag_context",
            "source_marker": "average required monthly payments",
        },
        {
            "metric": "log_payment_delinquency_lpm_spec3_context",
            "metric_value": "0.029",
            "metric_unit": (
                "coefficient_on_log_monthly_payment_for_30_day_delinquency_"
                "within_two_years"
            ),
            "confidence_interval_95": "",
            "evidence_family": "payment_delinquency_regression_context",
            "source_marker": "Table 1 specification 3",
        },
        {
            "metric": "monthly_payment_explained_delinquency_increase_context",
            "metric_value": "40",
            "metric_unit": "percent_of_two_year_delinquency_increase",
            "confidence_interval_95": "",
            "evidence_family": "payment_delinquency_regression_context",
            "source_marker": "monthly payment explanation paragraph",
        },
        {
            "metric": "subprime_and_prime_rate_increase_context",
            "metric_value": "140;300",
            "metric_unit": "basis_points_subprime;basis_points_prime_2020_to_2023",
            "confidence_interval_95": "",
            "evidence_family": "interest_rate_context",
            "source_marker": "Figure 4 discussion",
        },
        {
            "metric": "interest_rate_monthly_payment_increase_context",
            "metric_value": "15;40",
            "metric_unit": "dollars_subprime;dollars_prime_holding_loan_size_fixed",
            "confidence_interval_95": "",
            "evidence_family": "interest_rate_payment_mechanics_context",
            "source_marker": "monthly payment decomposition paragraph",
        },
        {
            "metric": "promotion_blocker_context",
            "metric_value": (
                "not_monetary_rate_shock;not_current_demand_response;"
                "underlying_ccp_experian_microdata_not_publicly_reusable"
            ),
            "metric_unit": "method_blocker",
            "confidence_interval_95": "",
            "evidence_family": "consumer_credit_promotion_blocker",
            "source_marker": "source design and data access limitation",
        },
    ]
    records: list[dict[str, str]] = []
    for row_index, row in enumerate(rows, start=1):
        records.append(
            {
                **base_record,
                **row,
                "source_record_index_one_based": str(row_index),
            }
        )
    return records


def _fed_auto_loan_payment_delinquency_snapshot(
    *,
    registry: SourceRegistry,
    source_html: Path,
    source_accessible_html: Path,
) -> SourceSnapshot:
    series = registry.series[FED_AUTO_LOAN_PAYMENT_DELINQUENCY_SERIES_ID]
    if not source_html.exists():
        _download_source(series.endpoint, source_html)
    if not source_accessible_html.exists():
        _download_source(
            FED_AUTO_LOAN_PAYMENT_DELINQUENCY_ACCESSIBLE_URL,
            source_accessible_html,
        )
    html_text = source_html.read_text(encoding="utf-8", errors="replace")
    accessible_html = source_accessible_html.read_text(
        encoding="utf-8",
        errors="replace",
    )
    records = _fed_auto_loan_payment_delinquency_records(html_text, accessible_html)
    html_hash = _file_sha256(source_html)
    accessible_hash = _file_sha256(source_accessible_html)
    records_hash = _records_sha256(records)
    note = (
        "fed_auto_loan_payment_delinquency_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_accessible_html_sha256={accessible_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "first_observation_date=2024-09-26;"
        "latest_observation_date=2024-09-26;"
        "auto_loan_payment_context_available=true;"
        "auto_loan_delinquency_context_available=true;"
        "auto_loan_interest_rate_context_available=true;"
        "borrower_credit_score_context_available=true;"
        "borrower_income_proxy_context_available=true;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "monetary_rate_shock_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "public_borrower_level_microdata_available=false;"
        "underlying_ccp_experian_microdata_publicly_reusable=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2024-09-26",
            snapshot_kind="live_html_and_accessible_context",
            note=note,
        ),
        records=records,
    )


def _excel_serial_date(serial_value: str) -> str:
    return (date(1899, 12, 30) + timedelta(days=int(serial_value))).isoformat()


def _fed_auto_loan_prepayment_maturity_records(
    *, index_html: str, accessible_figures_html: str
) -> list[dict[str, str]]:
    index_text = _plain_text(index_html).replace("\u2011", "-")
    figures_text = _plain_text(accessible_figures_html).replace("\u2011", "-")
    missing = [
        marker
        for marker in FED_AUTO_LOAN_PREPAYMENT_MATURITY_MARKERS
        if marker not in index_text
    ]
    missing.extend(
        marker
        for marker in FED_AUTO_LOAN_PREPAYMENT_MATURITY_ACCESSIBLE_MARKERS
        if marker not in figures_text
    )
    if missing:
        raise ValueError(
            "Fed auto-loan prepayment/maturity materials missing markers: "
            + "; ".join(missing)
        )

    base_record = {
        "publication_date": "2024-07-01",
        "source_zip_schema_reviewed": "true",
        "source_index_html_reviewed": "true",
        "source_accessible_figures_reviewed": "true",
        "auto_loan_maturity_context_available": "true",
        "auto_loan_prepayment_context_available": "true",
        "auto_loan_payment_behavior_context_available": "true",
        "auto_loan_interest_rate_context_available": "true",
        "payment_targeting_liquidity_context_available": "true",
        "rate_sensitive_payment_drag_transmission_available": "false",
        "monetary_rate_shock_payment_drag_transmission_available": "false",
        "current_demand_response_available": "false",
        "current_demand_conversion_available": "false",
        "public_borrower_level_microdata_available": "false",
        "underlying_auto_loan_microdata_publicly_reusable": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "empirical_threshold_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
        "method_blocker": (
            "feds_paper_supplies_auto_loan_maturity_prepayment_paid_over_"
            "scheduled_payment_and_payment_targeting_context_but_not_"
            "monetary_policy_rate_shock_payment_drag_transmission_current_"
            "demand_response_or_public_reusable_borrower_microdata"
        ),
    }

    records: list[dict[str, str]] = []
    figure_1 = re.search(
        "Figure 1: Recent Trend of Average Auto Loan Maturity.*?"
        "year New car loans Used car loans (?P<body>.*?) Return to text",
        figures_text,
    )
    if figure_1 is None:
        raise ValueError("Fed auto-loan prepayment ZIP missing Figure 1 data")
    for year, new_maturity, used_maturity in re.findall(
        r"(\d{4})\s+([0-9.]+)\s+([0-9.]+)",
        figure_1.group("body"),
    ):
        for vehicle_type, value in (
            ("new_car_loans", new_maturity),
            ("used_car_loans", used_maturity),
        ):
            records.append(
                {
                    **base_record,
                    "date": f"{year}-12-31",
                    "source_figure": "Figure 1",
                    "source_record_index_one_based": str(len(records) + 1),
                    "metric": f"auto_loan_average_maturity_{vehicle_type}",
                    "metric_label": vehicle_type,
                    "metric_value": _normalize_source_number(value),
                    "metric_unit": "months",
                    "evidence_family": "auto_loan_maturity_context",
                }
            )

    figure_7 = re.search(
        "Figure 7: Trends of Prepayments of Auto Loans.*?"
        "year By year of payoff By year of origination (?P<body>.*?) Return to text",
        figures_text,
    )
    if figure_7 is None:
        raise ValueError("Fed auto-loan prepayment ZIP missing Figure 7 data")
    for year, payoff_share, origination_share in re.findall(
        r"(\d{4})\s+([0-9.]+)(?:\s+([0-9.]+))?(?=\s+\d{4}\s|$)",
        figure_7.group("body"),
    ):
        records.append(
            {
                **base_record,
                "date": f"{year}-12-31",
                "source_figure": "Figure 7",
                "source_record_index_one_based": str(len(records) + 1),
                "metric": "auto_loan_prepayment_share_by_payoff_year",
                "metric_label": "by_year_of_payoff",
                "metric_value": _normalize_source_number(payoff_share),
                "metric_unit": "share",
                "evidence_family": "auto_loan_prepayment_context",
            }
        )
        if origination_share:
            records.append(
                {
                    **base_record,
                    "date": f"{year}-12-31",
                    "source_figure": "Figure 7",
                    "source_record_index_one_based": str(len(records) + 1),
                    "metric": "auto_loan_prepayment_share_by_origination_year",
                    "metric_label": "by_year_of_origination",
                    "metric_value": _normalize_source_number(origination_share),
                    "metric_unit": "share",
                    "evidence_family": "auto_loan_prepayment_context",
                }
            )

    paid_over_scheduled = re.search(
        r"Month paid_over_scheduled (?P<body>.*?) Return to text",
        figures_text,
    )
    if paid_over_scheduled is None:
        raise ValueError("Fed auto-loan prepayment ZIP missing paid/scheduled data")
    for serial_month, percent_value in re.findall(
        r"(\d{5})\s+([0-9.]+)%",
        paid_over_scheduled.group("body"),
    ):
        records.append(
            {
                **base_record,
                "date": _excel_serial_date(serial_month),
                "source_figure": "Figure 7",
                "source_record_index_one_based": str(len(records) + 1),
                "metric": "auto_loan_actual_paid_over_scheduled_payment",
                "metric_label": "paid_over_scheduled",
                "metric_value": _normalize_source_number(percent_value),
                "metric_unit": "percent_of_scheduled_payment",
                "evidence_family": "auto_loan_payment_behavior_context",
            }
        )

    summary_rows = (
        (
            "auto_loan_originations_sample_market_coverage_context",
            "55",
            "percent_of_entire_market",
            "source_design_context",
        ),
        (
            "auto_loan_underlying_sample_scale_context",
            "nearly_200_million_loans",
            "loan_count_context",
            "source_design_context",
        ),
        (
            "promotion_blocker_context",
            (
                "not_monetary_rate_shock;not_current_demand_response;"
                "underlying_auto_loan_microdata_not_publicly_reusable"
            ),
            "method_blocker",
            "consumer_credit_promotion_blocker",
        ),
    )
    for metric, value, unit, family in summary_rows:
        records.append(
            {
                **base_record,
                "date": "2024-07-01",
                "source_figure": "index_html",
                "source_record_index_one_based": str(len(records) + 1),
                "metric": metric,
                "metric_label": metric,
                "metric_value": value,
                "metric_unit": unit,
                "evidence_family": family,
            }
        )

    if len(records) < 100:
        raise ValueError(
            "Fed auto-loan prepayment/maturity parser produced too few rows: "
            f"{len(records)}"
        )
    return records


def _fed_auto_loan_prepayment_maturity_snapshot(
    *, registry: SourceRegistry, source_zip: Path
) -> SourceSnapshot:
    series = registry.series[FED_AUTO_LOAN_PREPAYMENT_MATURITY_SERIES_ID]
    if not source_zip.exists():
        _download_source(series.endpoint, source_zip)
    with zipfile.ZipFile(source_zip) as archive:
        missing = [
            expected
            for expected in FED_AUTO_LOAN_PREPAYMENT_MATURITY_EXPECTED_FILES
            if expected not in archive.namelist()
        ]
        if missing:
            raise ValueError(
                "Fed auto-loan prepayment accessible ZIP missing expected files: "
                + "; ".join(missing)
            )
        index_html = archive.read("index.html").decode("utf-8", errors="replace")
        figures_html = archive.read("accessible_figures.html").decode(
            "utf-8", errors="replace"
        )
    records = _fed_auto_loan_prepayment_maturity_records(
        index_html=index_html,
        accessible_figures_html=figures_html,
    )
    zip_hash = _file_sha256(source_zip)
    index_hash = hashlib.sha256(index_html.encode("utf-8")).hexdigest()
    figures_hash = hashlib.sha256(figures_html.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    note = (
        "fed_auto_loan_prepayment_maturity_context_only;"
        f"source_zip_sha256={zip_hash};"
        f"index_html_sha256={index_hash};"
        f"accessible_figures_html_sha256={figures_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "auto_loan_maturity_context_available=true;"
        "auto_loan_prepayment_context_available=true;"
        "auto_loan_payment_behavior_context_available=true;"
        "auto_loan_interest_rate_context_available=true;"
        "payment_targeting_liquidity_context_available=true;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "monetary_rate_shock_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "current_demand_conversion_available=false;"
        "public_borrower_level_microdata_available=false;"
        "underlying_auto_loan_microdata_publicly_reusable=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2025-01-31",
            snapshot_kind="live_accessible_zip_context",
            note=note,
        ),
        records=records,
    )


def _boston_fed_credit_card_interest_spending_records(
    html_text: str,
) -> list[dict[str, str]]:
    text = html.unescape(_plain_text(html_text))
    normalized = (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )
    missing = [
        marker
        for marker in BOSTON_FED_CREDIT_CARD_INTEREST_SPENDING_MARKERS
        if marker not in normalized
    ]
    if missing:
        raise ValueError(
            "Boston Fed credit-card interest spending article missing markers: "
            + "; ".join(missing)
        )

    base_record = {
        "date": "2026-03-25",
        "publication_date": "2026-03-25",
        "sample_start": "2016-01-01",
        "sample_end": "2025-12-31",
        "source_page_schema_reviewed": "true",
        "official_public_article_available": "true",
        "regression_kink_design_context_available": "true",
        "credit_card_spending_response_context_available": "true",
        "current_demand_response_context_available": "true",
        "rate_sensitive_payment_drag_transmission_available": "true",
        "monetary_rate_shock_payment_drag_transmission_available": "false",
        "aggregate_ffr_credit_card_spending_context_available": "true",
        "public_borrower_level_microdata_available": "false",
        "underlying_account_microdata_publicly_reusable": "false",
        "aggregate_current_demand_conversion_available": "false",
        "current_demand_conversion_available": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "empirical_threshold_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
        "method_blocker": (
            "boston_fed_article_supplies_credit_card_interest_rate_spending_"
            "response_context_but_not_monetary_policy_shock_not_public_"
            "reusable_account_microdata_and_not_aggregate_current_demand_"
            "conversion"
        ),
    }
    metrics = [
        (
            "credit_card_spending_response_per_1pp_apr_increase",
            "-8.7",
            "percent_next_month",
            "rate_sensitive_credit_card_spending_response",
        ),
        (
            "monthly_spending_change_per_1pp_apr_increase",
            "-74",
            "real_dollars_per_account_month",
            "rate_sensitive_credit_card_spending_response",
        ),
        (
            "revolving_balance_response_per_1pp_apr_increase",
            "-4",
            "percent_revolving_balance",
            "rate_sensitive_revolving_balance_response",
        ),
        (
            "revolver_spending_response_per_1pp_apr_increase",
            "-15",
            "percent_next_month",
            "revolver_spending_response",
        ),
        (
            "low_credit_score_spending_response_per_1pp_apr_increase",
            "-18",
            "percent_next_month",
            "credit_score_heterogeneity_context",
        ),
        (
            "high_credit_score_balance_response_per_1pp_apr_increase",
            "-7",
            "percent_outstanding_balance",
            "credit_score_heterogeneity_context",
        ),
        (
            "active_credit_card_account_coverage_2016_2025",
            "80",
            "approximate_percent_of_active_us_credit_card_accounts",
            "source_scope_context",
        ),
        (
            "credit_card_purchase_volume_2022",
            "5.83",
            "trillions_of_dollars",
            "payment_scale_context",
        ),
        (
            "credit_card_purchase_share_consumer_spending_2022",
            "20",
            "approximate_percent_of_consumer_spending",
            "payment_scale_context",
        ),
        (
            "aggregate_ffr_credit_card_spending_effect_peak_lag",
            "2",
            "months_after_rate_change",
            "aggregate_ffr_context_not_promotion_design",
        ),
    ]
    return [
        {
            **base_record,
            "source_record_index_one_based": str(index),
            "metric": metric,
            "metric_value": value,
            "metric_unit": unit,
            "evidence_family": family,
        }
        for index, (metric, value, unit, family) in enumerate(metrics, start=1)
    ]


def _boston_fed_credit_card_interest_spending_snapshot(
    *, registry: SourceRegistry, source_html: Path
) -> SourceSnapshot:
    series = registry.series[BOSTON_FED_CREDIT_CARD_INTEREST_SPENDING_SERIES_ID]
    if not source_html.exists():
        _download_source(series.endpoint, source_html)
    html_text = source_html.read_text(encoding="utf-8", errors="replace")
    records = _boston_fed_credit_card_interest_spending_records(html_text)
    html_hash = _file_sha256(source_html)
    records_hash = _records_sha256(records)
    note = (
        "boston_fed_credit_card_interest_rate_spending_response_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "publication_date=2026-03-25;"
        "sample_start=2016-01-01;"
        "sample_end=2025-12-31;"
        "credit_card_spending_response_context_available=true;"
        "current_demand_response_context_available=true;"
        "rate_sensitive_payment_drag_transmission_available=true;"
        "aggregate_ffr_credit_card_spending_context_available=true;"
        "monetary_rate_shock_payment_drag_transmission_available=false;"
        "public_borrower_level_microdata_available=false;"
        "underlying_account_microdata_publicly_reusable=false;"
        "aggregate_current_demand_conversion_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2026-03-25",
            snapshot_kind="live_html_article_context",
            note=note,
        ),
        records=records,
    )


def _boston_fed_credit_card_spending_channel_wp_records(
    pdf_text: str,
) -> list[dict[str, str]]:
    normalized = re.sub(
        r"\s+",
        " ",
        pdf_text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2019", "'")
        .replace("\u2212", "-"),
    )
    missing = [
        marker
        for marker in BOSTON_FED_CREDIT_CARD_SPENDING_CHANNEL_WP_MARKERS
        if marker not in normalized
    ]
    if missing:
        raise ValueError(
            "Boston Fed credit-card spending channel working paper missing "
            "markers: " + "; ".join(missing)
        )

    base_record = {
        "date": "2025-09-01",
        "publication_date": "2025-09-01",
        "sample_start": "2016-01-01",
        "sample_end": "2025-12-31",
        "working_paper_number": "25-10",
        "source_pdf_text_reviewed": "true",
        "official_public_working_paper_available": "true",
        "account_level_supervisory_design_context_available": "true",
        "public_borrower_level_microdata_available": "false",
        "underlying_account_microdata_publicly_reusable": "false",
        "regression_kink_design_context_available": "true",
        "multiway_clustered_standard_errors_available": "true",
        "local_projection_iv_context_available": "true",
        "monetary_shock_instrument_context_available": "true",
        "aggregate_ffr_credit_card_spending_context_available": "true",
        "rate_sensitive_payment_drag_transmission_available": "true",
        "monetary_rate_shock_payment_drag_transmission_available": "context_only",
        "promotion_grade_monetary_rate_shock_bridge_available": "false",
        "aggregate_current_demand_conversion_available": "false",
        "current_demand_conversion_available": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "empirical_threshold_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
        "method_blocker": (
            "boston_fed_working_paper_supplies_rkd_and_aggregate_lp_iv_"
            "estimate_context_but_underlying_y14m_account_microdata_are_not_"
            "publicly_reusable_total_spending_iv_ci_includes_zero_"
            "effective_f_statistics_are_below_promotion_grade_threshold_and_"
            "no_aggregate_current_demand_conversion_is_source_admitted"
        ),
    }
    metrics = [
        (
            "full_sample_account_months",
            "79982992",
            "",
            "",
            "",
            "account_months",
            "sample_scope_context",
            "table_1_text",
        ),
        (
            "full_sample_banks",
            "13",
            "",
            "",
            "",
            "banks",
            "sample_scope_context",
            "table_1_text",
        ),
        (
            "rkd_bandwidth",
            "2",
            "",
            "",
            "",
            "percentage_points_around_maximum_apr",
            "method_context",
            "table_2_note",
        ),
        (
            "rkd_spending_elasticity_col4",
            "-8.66",
            "2.91",
            "",
            "",
            "elasticity_per_1pp_apr_increase",
            "rkd_spending_estimate",
            "table_2_column_4",
        ),
        (
            "rkd_balance_elasticity_col4",
            "-3.71",
            "2.02",
            "",
            "",
            "elasticity_per_1pp_apr_increase",
            "rkd_balance_estimate",
            "table_3_column_4",
        ),
        (
            "rkd_revolver_spending_elasticity",
            "-15.29",
            "4.07",
            "",
            "",
            "elasticity_per_1pp_apr_increase",
            "rkd_revolver_spending_estimate",
            "table_4_column_1",
        ),
        (
            "rkd_transactor_spending_elasticity",
            "-1.66",
            "3.88",
            "",
            "",
            "elasticity_per_1pp_apr_increase",
            "rkd_transactor_spending_estimate",
            "table_4_column_2_insignificant",
        ),
        (
            "rkd_low_credit_score_spending_elasticity",
            "-17.89",
            "5.90",
            "",
            "",
            "elasticity_per_1pp_apr_increase",
            "rkd_credit_score_heterogeneity_estimate",
            "table_5_column_1",
        ),
        (
            "rkd_high_credit_score_balance_elasticity",
            "-7.12",
            "3.32",
            "",
            "",
            "elasticity_per_1pp_apr_increase",
            "rkd_credit_score_heterogeneity_estimate",
            "table_5_column_4",
        ),
        (
            "aggregate_lp_iv_revolver_spending_growth_h2",
            "-0.141",
            "",
            "-0.241",
            "-0.030",
            "log_point_spending_growth_response_per_1pp_ffr_increase",
            "aggregate_lp_iv_estimate_context",
            "table_6_column_2",
        ),
        (
            "aggregate_lp_iv_total_spending_growth_h2",
            "-0.0949",
            "",
            "-0.188",
            "0.044",
            "log_point_spending_growth_response_per_1pp_ffr_increase",
            "aggregate_lp_iv_estimate_context_total_ci_includes_zero",
            "table_6_column_4",
        ),
        (
            "aggregate_lp_iv_revolver_effective_f_stat",
            "5.175",
            "",
            "",
            "",
            "effective_f_stat",
            "weak_instrument_diagnostic_context",
            "table_6_column_2",
        ),
        (
            "aggregate_lp_iv_total_effective_f_stat",
            "4.629",
            "",
            "",
            "",
            "effective_f_stat",
            "weak_instrument_diagnostic_context",
            "table_6_column_4",
        ),
        (
            "aggregate_lp_iv_total_cumulative_h4",
            "-0.167",
            "",
            "",
            "",
            "log_point_cumulative_spending_growth_response",
            "aggregate_lp_iv_cumulative_context_pval_0_288",
            "table_6_column_4",
        ),
        (
            "aggregate_lp_iv_revolver_cumulative_h4",
            "-0.309",
            "",
            "",
            "",
            "log_point_cumulative_spending_growth_response",
            "aggregate_lp_iv_cumulative_context_pval_0_044",
            "table_6_column_2",
        ),
    ]
    return [
        {
            **base_record,
            "source_record_index_one_based": str(index),
            "metric": metric,
            "metric_value": value,
            "metric_standard_error": standard_error,
            "metric_lower_ci": lower_ci,
            "metric_upper_ci": upper_ci,
            "metric_unit": unit,
            "evidence_family": family,
            "source_table_or_section": source_table,
        }
        for index, (
            metric,
            value,
            standard_error,
            lower_ci,
            upper_ci,
            unit,
            family,
            source_table,
        ) in enumerate(metrics, start=1)
    ]


def _boston_fed_credit_card_spending_channel_wp_snapshot(
    *, registry: SourceRegistry, source_pdf: Path
) -> SourceSnapshot:
    series = registry.series[BOSTON_FED_CREDIT_CARD_SPENDING_CHANNEL_WP_SERIES_ID]
    if not source_pdf.exists():
        _download_source(series.endpoint, source_pdf)
    pdf_text = _pdf_text(source_pdf)
    records = _boston_fed_credit_card_spending_channel_wp_records(pdf_text)
    pdf_hash = _file_sha256(source_pdf)
    text_hash = hashlib.sha256(pdf_text.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    note = (
        "boston_fed_credit_card_spending_channel_working_paper_context_only;"
        f"source_pdf_sha256={pdf_hash};"
        f"source_text_sha256={text_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "publication_date=2025-09-01;"
        "sample_start=2016-01-01;"
        "sample_end=2025-12-31;"
        "rkd_estimate_context_available=true;"
        "local_projection_iv_context_available=true;"
        "monetary_shock_instrument_context_available=true;"
        "aggregate_ffr_credit_card_spending_context_available=true;"
        "multiway_clustered_standard_errors_available=true;"
        "anderson_rubin_confidence_interval_context_available=true;"
        "promotion_grade_monetary_rate_shock_bridge_available=false;"
        "public_borrower_level_microdata_available=false;"
        "underlying_account_microdata_publicly_reusable=false;"
        "aggregate_current_demand_conversion_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2025-09-01",
            snapshot_kind="live_pdf_research_context",
            note=note,
        ),
        records=records,
    )


def _fed_private_credit_accessible_table_records(
    html_text: str, *, require_all_tables: bool = True
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for title, (
        base_metric,
        metric_unit,
        evidence_family,
    ) in FED_PRIVATE_CREDIT_CHARACTERISTICS_EXPECTED_TABLES.items():
        table_matches = list(
            re.finditer(
                rf'<table[^>]+title="{re.escape(title)}".*?</table>',
                html_text,
                flags=re.DOTALL | re.IGNORECASE,
            )
        )
        if not table_matches and require_all_tables:
            raise ValueError(f"Fed private-credit page missing table: {title}")
        if not table_matches:
            continue
        for table_index, table_match in enumerate(table_matches, start=1):
            table_html = table_match.group(0)
            headers = _source_table_headers(table_html)
            body_rows = _source_table_body_rows(table_html)
            if not body_rows:
                raise ValueError(f"Fed private-credit table has no rows: {title}")
            for row_index, (label, values) in enumerate(body_rows, start=1):
                data_headers = (
                    headers[1:] if len(headers) == len(values) + 1 else headers
                )
                if len(data_headers) != len(values):
                    data_headers = [
                        f"value_{column_index}"
                        for column_index in range(1, len(values) + 1)
                    ]
                for column_index, (column_label, value) in enumerate(
                    zip(data_headers, values, strict=True),
                    start=1,
                ):
                    metric = (
                        base_metric
                        if len(values) == 1
                        else f"{base_metric}_{_slug(column_label)}"
                    )
                    records.append(
                        {
                            "date": _source_label_to_date(label),
                            "source_table_title": title,
                            "source_table_index_one_based": str(table_index),
                            "source_row_index_one_based": str(row_index),
                            "source_column_index_one_based": str(column_index),
                            "source_column_label": column_label,
                            "metric": metric,
                            "metric_label": label,
                            "metric_value": _normalize_source_number(
                                value.replace("%", "")
                            ),
                            "metric_unit": metric_unit,
                            "evidence_family": evidence_family,
                            "source_page_schema_reviewed": "true",
                            "private_credit_maturity_context_available": str(
                                evidence_family == "maturity"
                            ).lower(),
                            "private_credit_exposure_size_context_available": str(
                                evidence_family
                                in {
                                    "exposure_size",
                                    "exposure_size_and_liquidity",
                                }
                            ).lower(),
                            "private_credit_liquidity_context_available": str(
                                evidence_family == "exposure_size_and_liquidity"
                                and "dry powder" in column_label.lower()
                            ).lower(),
                            "borrower_rate_context_available": str(
                                evidence_family == "borrower_rate_context"
                            ).lower(),
                            "borrower_resilience_context_available": str(
                                evidence_family == "borrower_resilience"
                            ).lower(),
                            "collateral_structure_context_available": str(
                                evidence_family == "collateral_structure"
                            ).lower(),
                            "borrower_pass_through_context_available": "false",
                            "nonbank_to_real_activity_context_available": "false",
                            "denominator_prior_narrowing_allowed": "false",
                            "split_denominator_promotion_allowed": "false",
                            "formula_replacement_allowed": "false",
                            "main_ratio_admission_allowed": "false",
                            "incidence_output_enabled": "false",
                            "welfare_tax_mpc_output_enabled": "false",
                        }
                    )
    return records


def _fed_private_credit_characteristics_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[FED_PRIVATE_CREDIT_CHARACTERISTICS_SERIES_ID]
    html_text = _fetch_text(series.endpoint)
    records = _fed_private_credit_accessible_table_records(html_text)
    html_hash = hashlib.sha256(html_text.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    note = (
        "fed_private_credit_characteristics_accessible_data_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "source_tables=Figure 1-Figure 16 accessible data tables;"
        "private_credit_maturity_context_available=true;"
        "private_credit_exposure_size_context_available=true;"
        "private_credit_liquidity_context_available=true;"
        "borrower_rate_context_available=true;"
        "borrower_resilience_context_available=true;"
        "collateral_structure_context_available=true;"
        "borrower_pass_through_context_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2024-02-23",
            snapshot_kind="live_html_table_context",
            note=note,
        ),
        records=records,
    )


def _fed_bank_lending_private_credit_records(html_text: str) -> list[dict[str, str]]:
    required_markers = (
        "Bank Lending to Private Credit",
        "FR Y-14Q",
        "Bank loans to NBFIs",
        "Default probabilities",
        "Changes in Capital and Liquidity ratios",
    )
    missing_markers = [marker for marker in required_markers if marker not in html_text]
    if missing_markers:
        raise ValueError(
            "Fed bank-lending private-credit page missing expected markers: "
            + ", ".join(missing_markers)
        )

    table_specs: Mapping[str, tuple[str, str, str, str]] = {
        "Table 1: Bank loans to NBFIs in FR Y-14Q, as of 2024-Q4": (
            "2024-12-31",
            "bank_private_credit_exposure_terms",
            "bank_private_credit_lending_context",
            "bank loans to NBFIs",
        ),
        (
            "Table 2: BHC loans - Distribution of Default probabilities (%) "
            "by Rating, as of 2024-Q4"
        ): (
            "2024-12-31",
            "bank_private_credit_default_probability",
            "borrower_risk_context",
            "default probability distribution",
        ),
        "Table 3: Private Credit Vehicles: Changes in Capital and Liquidity ratios": (
            "2025-05-23",
            "bank_private_credit_capital_liquidity_stress",
            "capital_liquidity_stress_context",
            "capital and liquidity stress context",
        ),
    }

    def normalized_title(value: str) -> str:
        return re.sub(r"\s+", " ", value.replace("–", "-")).strip()

    table_matches_by_title: dict[str, str] = {}
    for table_match in re.finditer(
        r"<table[^>]+title=\"(?P<title>[^\"]+)\"[^>]*>.*?</table>",
        html_text,
        flags=re.DOTALL | re.IGNORECASE,
    ):
        table_title = html.unescape(table_match.group("title"))
        table_matches_by_title[normalized_title(table_title)] = table_match.group(0)

    tables: dict[str, str] = {}
    for title in table_specs:
        table_html = table_matches_by_title.get(normalized_title(title))
        if table_html is None:
            raise ValueError(
                f"Fed bank-lending private-credit page missing table: {title}"
            )
        tables[title] = table_html

    promotion_flags = {
        "borrower_pass_through_context_available": "false",
        "nonbank_to_real_activity_context_available": "false",
        "public_reusable_loan_level_artifact_available": "false",
        "underlying_y14q_supervisory_data_publicly_reusable": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "empirical_threshold_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
    }

    records: list[dict[str, str]] = []

    table1_title = "Table 1: Bank loans to NBFIs in FR Y-14Q, as of 2024-Q4"
    table1_headers = _source_table_headers(tables[table1_title])
    table1_rows = _source_table_body_rows(tables[table1_title])
    table1_metrics = (
        ("Loan Commitment ($ Billion)", "loan_commitment_bil", "billions_usd"),
        ("Utilization Rate (%)", "utilization_rate_pct", "percent"),
        ("Average Interest Rate (%)", "average_interest_rate_pct", "percent"),
        ("Time to Maturity (Years)", "time_to_maturity_years", "years"),
        ("Average Rating", "average_rating", "rating"),
        ("Delinquency Rate (%)", "delinquency_rate_pct", "percent"),
    )
    table1_data_headers = (
        table1_headers[1:]
        if len(table1_headers) == len(table1_metrics) + 1
        else table1_headers
    )
    if len(table1_rows) != 3 or len(table1_data_headers) != len(table1_metrics):
        raise ValueError("Fed bank-lending private-credit Table 1 schema changed")
    for row_index, (row_label, values) in enumerate(table1_rows, start=1):
        if len(values) != len(table1_metrics):
            raise ValueError("Fed bank-lending private-credit Table 1 row changed")
        for column_index, (
            (column_label, metric, metric_unit),
            source_header,
            value,
        ) in enumerate(
            zip(table1_metrics, table1_data_headers, values, strict=True), start=1
        ):
            records.append(
                {
                    "date": table_specs[table1_title][0],
                    "source_table_title": table1_title,
                    "source_table_index_one_based": "1",
                    "source_row_index_one_based": str(row_index),
                    "source_column_index_one_based": str(column_index),
                    "source_row_label": row_label,
                    "source_column_label": source_header or column_label,
                    "metric": metric,
                    "metric_label": f"{row_label} {column_label}",
                    "metric_value": _normalize_source_number(value.replace("%", "")),
                    "metric_unit": metric_unit,
                    "evidence_family": table_specs[table1_title][2],
                    "source_page_schema_reviewed": "true",
                    "bank_private_credit_exposure_context_available": "true",
                    "credit_line_utilization_context_available": str(
                        metric == "utilization_rate_pct"
                    ).lower(),
                    "borrower_rate_context_available": str(
                        metric == "average_interest_rate_pct"
                    ).lower(),
                    "maturity_context_available": str(
                        metric == "time_to_maturity_years"
                    ).lower(),
                    "delinquency_context_available": str(
                        metric == "delinquency_rate_pct"
                    ).lower(),
                    "default_probability_context_available": "false",
                    "capital_liquidity_stress_context_available": "false",
                    **promotion_flags,
                }
            )

    table2_title = (
        "Table 2: BHC loans - Distribution of Default probabilities (%) "
        "by Rating, as of 2024-Q4"
    )
    table2_rows = _source_table_body_rows(tables[table2_title])
    table2_groups = ("Other NBFIs", "Private Debt Funds", "BDCs")
    table2_stats = (
        ("Mean", "mean_default_probability_pct"),
        ("Median", "median_default_probability_pct"),
        ("% Obs", "observation_share_pct"),
    )
    if len(table2_rows) != 4:
        raise ValueError("Fed bank-lending private-credit Table 2 schema changed")
    for row_index, (rating_label, values) in enumerate(table2_rows, start=1):
        if len(values) != len(table2_groups) * len(table2_stats):
            raise ValueError("Fed bank-lending private-credit Table 2 row changed")
        for group_index, group_label in enumerate(table2_groups):
            for stat_index, (stat_label, metric) in enumerate(table2_stats):
                value_index = group_index * len(table2_stats) + stat_index
                records.append(
                    {
                        "date": table_specs[table2_title][0],
                        "source_table_title": table2_title,
                        "source_table_index_one_based": "2",
                        "source_row_index_one_based": str(row_index),
                        "source_column_index_one_based": str(value_index + 1),
                        "source_row_label": rating_label,
                        "source_column_label": f"{group_label} {stat_label}",
                        "metric": metric,
                        "metric_label": f"{group_label} {rating_label} {stat_label}",
                        "metric_value": _normalize_source_number(values[value_index]),
                        "metric_unit": "percent",
                        "evidence_family": table_specs[table2_title][2],
                        "source_page_schema_reviewed": "true",
                        "bank_private_credit_exposure_context_available": "false",
                        "credit_line_utilization_context_available": "false",
                        "borrower_rate_context_available": "false",
                        "maturity_context_available": "false",
                        "delinquency_context_available": "false",
                        "default_probability_context_available": "true",
                        "capital_liquidity_stress_context_available": "false",
                        **promotion_flags,
                    }
                )

    table3_title = (
        "Table 3: Private Credit Vehicles: Changes in Capital and Liquidity ratios"
    )
    table3_headers = _source_table_headers(tables[table3_title])
    table3_rows = _source_table_body_rows(tables[table3_title])
    table3_metrics = (
        ("Current (%)", "current_ratio_pct", "percent"),
        ("Drawdown rate assumption", "drawdown_rate_assumption", "share"),
        (
            "Implied Change in Numerator ($ Bil.)",
            "implied_change_numerator_bil",
            "billions_usd",
        ),
        (
            "Implied Change in denominator ($ Bil.)",
            "implied_change_denominator_bil",
            "billions_usd",
        ),
        ("New ratio (%)", "new_ratio_pct", "percent"),
    )
    table3_data_headers = (
        table3_headers[1:]
        if len(table3_headers) == len(table3_metrics) + 1
        else table3_headers
    )
    if len(table3_rows) != 2 or len(table3_data_headers) != len(table3_metrics):
        raise ValueError("Fed bank-lending private-credit Table 3 schema changed")
    for row_index, (ratio_label, values) in enumerate(table3_rows, start=1):
        if len(values) != len(table3_metrics):
            raise ValueError("Fed bank-lending private-credit Table 3 row changed")
        for column_index, (
            (column_label, metric, metric_unit),
            source_header,
            value,
        ) in enumerate(
            zip(table3_metrics, table3_data_headers, values, strict=True), start=1
        ):
            records.append(
                {
                    "date": table_specs[table3_title][0],
                    "source_table_title": table3_title,
                    "source_table_index_one_based": "3",
                    "source_row_index_one_based": str(row_index),
                    "source_column_index_one_based": str(column_index),
                    "source_row_label": ratio_label,
                    "source_column_label": source_header or column_label,
                    "metric": metric,
                    "metric_label": f"{ratio_label} {column_label}",
                    "metric_value": _normalize_source_number(value.replace("%", "")),
                    "metric_unit": metric_unit,
                    "evidence_family": table_specs[table3_title][2],
                    "source_page_schema_reviewed": "true",
                    "bank_private_credit_exposure_context_available": "false",
                    "credit_line_utilization_context_available": "false",
                    "borrower_rate_context_available": "false",
                    "maturity_context_available": "false",
                    "delinquency_context_available": "false",
                    "default_probability_context_available": "false",
                    "capital_liquidity_stress_context_available": "true",
                    **promotion_flags,
                }
            )

    return records


def _fed_bank_lending_private_credit_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[FED_BANK_LENDING_PRIVATE_CREDIT_SERIES_ID]
    html_text = _fetch_text(series.endpoint)
    records = _fed_bank_lending_private_credit_records(html_text)
    html_hash = hashlib.sha256(html_text.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    note = (
        "fed_bank_lending_private_credit_financial_stability_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "source_tables=Table 1 bank loans to NBFIs,"
        "Table 2 default probabilities,"
        "Table 3 capital and liquidity ratios;"
        "bank_private_credit_exposure_context_available=true;"
        "credit_line_utilization_context_available=true;"
        "borrower_rate_context_available=true;"
        "maturity_context_available=true;"
        "delinquency_context_available=true;"
        "default_probability_context_available=true;"
        "capital_liquidity_stress_context_available=true;"
        "borrower_pass_through_context_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "public_reusable_loan_level_artifact_available=false;"
        "underlying_y14q_supervisory_data_publicly_reusable=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "empirical_threshold_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at="2025-05-23",
            snapshot_kind="live_html_table_context",
            note=note,
        ),
        records=records,
    )


def _sec_private_fund_aggregate_asset_records(
    source_json: str,
) -> list[dict[str, str]]:
    data = json.loads(source_json)
    if not isinstance(data, dict):
        raise ValueError("SEC private-fund aggregate assets JSON is not an object")

    records: list[dict[str, str]] = []
    for table_id, table_payload in data.items():
        if not isinstance(table_payload, dict):
            raise ValueError(f"SEC private-fund table is not an object: {table_id}")
        metadata = table_payload.get("metadata")
        series_list = table_payload.get("data")
        if not isinstance(metadata, dict) or not isinstance(series_list, list):
            raise ValueError(
                "SEC private-fund table missing metadata or data: " + str(table_id)
            )
        title = str(metadata.get("title", "")).strip()
        caption = str(metadata.get("caption", "")).strip()
        units = str(metadata.get("units", "")).strip()
        if units != "usd":
            raise ValueError(f"SEC private-fund table has unexpected units: {units}")
        if "Question 8" in caption:
            metric = "gross_asset_value"
            form_pf_question = "8"
        elif "Question 9" in caption:
            metric = "net_asset_value"
            form_pf_question = "9"
        else:
            raise ValueError(
                f"SEC private-fund table caption lacks Form PF question: {caption}"
            )
        large_filer_only = str("Large Filers" in title).lower()
        for series in series_list:
            if not isinstance(series, dict):
                raise ValueError(
                    f"SEC private-fund series is not an object: {table_id}"
                )
            fund_type = str(series.get("name", "")).strip()
            points = series.get("data")
            if not fund_type or not isinstance(points, list):
                raise ValueError(
                    f"SEC private-fund series missing name/data: {table_id}"
                )
            for point_index, point in enumerate(points, start=1):
                if not isinstance(point, dict):
                    raise ValueError(
                        f"SEC private-fund data point is not an object: {table_id}"
                    )
                quarter = str(point.get("name", "")).strip()
                if not _is_quarter_label(quarter):
                    raise ValueError(
                        f"SEC private-fund data point has bad quarter: {quarter}"
                    )
                value = point.get("y")
                if value is None:
                    continue
                records.append(
                    {
                        "date": _quarter_end_date(quarter),
                        "calendar_quarter": quarter,
                        "source_table_id": table_id,
                        "source_table_title": title,
                        "source_table_caption": caption,
                        "source_point_index_one_based": str(point_index),
                        "fund_type": fund_type,
                        "metric": metric,
                        "form_pf_question": form_pf_question,
                        "metric_value_usd": _clean_published_number(str(value)),
                        "metric_unit": units,
                        "large_filer_only": large_filer_only,
                        "form_pf_aggregate_statistics_available": "true",
                        "private_fund_exposure_size_context_available": "true",
                        "private_fund_liquidity_fund_context_available": str(
                            "Liquidity Fund" in fund_type
                        ).lower(),
                        "public_reusable_fund_level_artifact_available": "false",
                        "public_reusable_borrower_level_artifact_available": "false",
                        "borrower_pass_through_context_available": "false",
                        "nonbank_to_real_activity_context_available": "false",
                        "underlying_form_pf_filing_data_aggregate_only": "true",
                        "denominator_prior_narrowing_allowed": "false",
                        "split_denominator_promotion_allowed": "false",
                        "formula_replacement_allowed": "false",
                        "main_ratio_admission_allowed": "false",
                        "incidence_output_enabled": "false",
                        "welfare_tax_mpc_output_enabled": "false",
                    }
                )
    if not records:
        raise ValueError("SEC private-fund aggregate assets JSON produced no records")
    return records


def _sec_private_fund_aggregate_assets_snapshot(
    *, registry: SourceRegistry, source_json_path: Path
) -> SourceSnapshot:
    series = registry.series[SEC_PRIVATE_FUND_AGGREGATE_ASSETS_SERIES_ID]
    if not source_json_path.exists():
        _download_source(series.endpoint, source_json_path)
    source_json = source_json_path.read_text(encoding="utf-8")
    records = _sec_private_fund_aggregate_asset_records(source_json)
    json_hash = hashlib.sha256(source_json.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    table_ids = sorted({record["source_table_id"] for record in records})
    fund_types = sorted({record["fund_type"] for record in records})
    note = (
        "sec_form_pf_private_fund_aggregate_assets_context_only;"
        f"source_json_sha256={json_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"source_tables={','.join(table_ids)};"
        f"fund_types={','.join(fund_types)};"
        "form_pf_aggregate_statistics_available=true;"
        "private_fund_exposure_size_context_available=true;"
        "private_fund_liquidity_fund_context_available=true;"
        "public_reusable_fund_level_artifact_available=false;"
        "public_reusable_borrower_level_artifact_available=false;"
        "borrower_pass_through_context_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2026-04-07",
            snapshot_kind="live_json_context",
            note=note,
        ),
        records=records,
    )


def _sec_bdc_latest_periodic_filing(
    submissions: Mapping[str, object],
) -> dict[str, str]:
    return _sec_bdc_recent_periodic_filings(submissions, max_filings=1)[0]


def _sec_bdc_recent_periodic_filings(
    submissions: Mapping[str, object], *, max_filings: int
) -> list[dict[str, str]]:
    filings = submissions.get("filings")
    if not isinstance(filings, Mapping):
        raise ValueError("SEC BDC submissions JSON missing filings object")
    recent = filings.get("recent")
    if not isinstance(recent, Mapping):
        raise ValueError("SEC BDC submissions JSON missing recent filings")
    forms = recent.get("form")
    accessions = recent.get("accessionNumber")
    primary_documents = recent.get("primaryDocument")
    filing_dates = recent.get("filingDate")
    report_dates = recent.get("reportDate")
    if not all(
        isinstance(value, list)
        for value in (forms, accessions, primary_documents, filing_dates, report_dates)
    ):
        raise ValueError("SEC BDC submissions recent filing arrays are unavailable")

    periodic_filings: list[dict[str, str]] = []
    for form, accession, primary_document, filing_date, report_date in zip(
        forms,
        accessions,
        primary_documents,
        filing_dates,
        report_dates,
        strict=False,
    ):
        form_text = str(form).strip()
        if form_text not in {"10-K", "10-Q"}:
            continue
        accession_text = str(accession).strip()
        primary_document_text = str(primary_document).strip()
        if not accession_text or not primary_document_text:
            raise ValueError("SEC BDC periodic filing missing accession/document")
        periodic_filings.append(
            {
                "form_type": form_text,
                "accession_number": accession_text,
                "primary_document": primary_document_text,
                "filing_date": str(filing_date).strip(),
                "report_date": str(report_date).strip(),
            }
        )
        if len(periodic_filings) >= max_filings:
            return periodic_filings
    if periodic_filings:
        return periodic_filings
    raise ValueError("SEC BDC submissions JSON has no recent 10-K/10-Q filing")


def _sec_bdc_submissions_for_single_filing(
    submissions: Mapping[str, object], filing: Mapping[str, str]
) -> str:
    single_filing_payload = dict(submissions)
    single_filing_payload["filings"] = {
        "recent": {
            "form": [filing["form_type"]],
            "accessionNumber": [filing["accession_number"]],
            "primaryDocument": [filing["primary_document"]],
            "filingDate": [filing["filing_date"]],
            "reportDate": [filing["report_date"]],
        }
    }
    return json.dumps(single_filing_payload, sort_keys=True)


def _sec_archive_document_url(
    *, cik: str, accession_number: str, primary_document: str
) -> str:
    accession_path = accession_number.replace("-", "")
    cik_path = str(int(cik))
    return (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{cik_path}/{accession_path}/{primary_document}"
    )


def _sec_bdc_public_filing_availability_record(
    *,
    cik: str,
    expected_ticker: str,
    submissions_json: str,
    filing_html: str,
) -> dict[str, str]:
    submissions = json.loads(submissions_json)
    if not isinstance(submissions, dict):
        raise ValueError("SEC BDC submissions payload is not an object")
    filing = _sec_bdc_latest_periodic_filing(submissions)
    registrant_name = str(submissions.get("name", "")).strip()
    tickers = [
        str(ticker).strip()
        for ticker in submissions.get("tickers", [])
        if str(ticker).strip()
    ]
    if expected_ticker and expected_ticker not in tickers:
        raise ValueError(
            "SEC BDC submissions JSON does not include expected ticker "
            f"{expected_ticker}: {tickers}"
        )

    plain_text = _plain_text(filing_html)
    lower_text = plain_text.lower()
    table_count = len(re.findall(r"<table\b", filing_html, flags=re.IGNORECASE))
    table_row_count = len(re.findall(r"<tr\b", filing_html, flags=re.IGNORECASE))
    if table_count == 0 or table_row_count == 0:
        raise ValueError("SEC BDC filing HTML has no parseable table structure")

    filing_url = _sec_archive_document_url(
        cik=cik,
        accession_number=filing["accession_number"],
        primary_document=filing["primary_document"],
    )
    portfolio_markers = (
        "schedule of investments",
        "portfolio companies",
        "investments at fair value",
        "consolidated schedule",
    )
    rate_markers = ("interest rate", "reference rate", "sofr", "libor")
    maturity_markers = ("maturity", "maturity date")
    fair_value_markers = ("fair value", "investments at fair value")
    lien_markers = ("first lien", "second lien", "senior secured")
    return {
        "date": filing["filing_date"],
        "report_date": filing["report_date"],
        "cik": cik,
        "registrant_name": registrant_name,
        "ticker": expected_ticker,
        "form_type": filing["form_type"],
        "accession_number": filing["accession_number"],
        "primary_document": filing["primary_document"],
        "filing_url": filing_url,
        "filing_table_count": str(table_count),
        "filing_table_row_count": str(table_row_count),
        "portfolio_disclosure_marker_available": str(
            any(marker in lower_text for marker in portfolio_markers)
        ).lower(),
        "rate_term_marker_available": str(
            any(marker in lower_text for marker in rate_markers)
        ).lower(),
        "maturity_marker_available": str(
            any(marker in lower_text for marker in maturity_markers)
        ).lower(),
        "fair_value_marker_available": str(
            any(marker in lower_text for marker in fair_value_markers)
        ).lower(),
        "lien_or_seniority_marker_available": str(
            any(marker in lower_text for marker in lien_markers)
        ).lower(),
        "public_reusable_company_filing_artifact_available": "true",
        "public_reusable_normalized_loan_level_panel_available": "false",
        "borrower_pass_through_context_available": "false",
        "nonbank_to_real_activity_context_available": "false",
        "source_schema_reviewed": "true",
        "method_blocker": (
            "sec_edgar_bdc_company_filings_are_public_but_this_gate_does_not_"
            "admit_a_normalized_cross_bdc_loan_level_panel_rate_shock_pass_"
            "through_design_or_nonbank_real_activity_bridge"
        ),
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
    }


def _sec_bdc_public_filing_availability_snapshot(
    *, registry: SourceRegistry, source_dir: Path
) -> SourceSnapshot:
    series = registry.series[SEC_BDC_PUBLIC_FILING_AVAILABILITY_SERIES_ID]
    source_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    json_hashes: dict[str, str] = {}
    html_hashes: dict[str, str] = {}
    for cik, ticker in SEC_BDC_REVIEW_CIKS.items():
        submissions_path = source_dir / f"CIK{cik}_submissions.json"
        submissions_url = f"{series.endpoint}CIK{cik}.json"
        if not submissions_path.exists():
            _download_source(submissions_url, submissions_path)
        submissions_json = submissions_path.read_text(encoding="utf-8")
        filing = _sec_bdc_latest_periodic_filing(json.loads(submissions_json))
        filing_url = _sec_archive_document_url(
            cik=cik,
            accession_number=filing["accession_number"],
            primary_document=filing["primary_document"],
        )
        filing_path = (
            source_dir / f"CIK{cik}_{filing['accession_number'].replace('-', '')}_"
            f"{filing['primary_document']}"
        )
        if not filing_path.exists():
            _download_source(filing_url, filing_path)
        filing_html = filing_path.read_text(encoding="utf-8", errors="replace")
        record = _sec_bdc_public_filing_availability_record(
            cik=cik,
            expected_ticker=ticker,
            submissions_json=submissions_json,
            filing_html=filing_html,
        )
        records.append(record)
        json_hashes[cik] = hashlib.sha256(submissions_json.encode("utf-8")).hexdigest()
        html_hashes[cik] = hashlib.sha256(filing_html.encode("utf-8")).hexdigest()

    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    note = (
        "sec_edgar_bdc_public_filing_availability_context_only;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "reviewed_ciks="
        f"{','.join(SEC_BDC_REVIEW_CIKS)};"
        "source_json_sha256_summary="
        f"{','.join(f'{cik}:{value}' for cik, value in json_hashes.items())};"
        "source_html_sha256_summary="
        f"{','.join(f'{cik}:{value}' for cik, value in html_hashes.items())};"
        "public_reusable_company_filing_artifact_available=true;"
        "public_reusable_normalized_loan_level_panel_available=false;"
        "borrower_pass_through_context_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="live_sec_edgar_filing_context",
            note=note,
        ),
        records=records,
    )


def _table_html_blocks(source_html: str) -> list[str]:
    return re.findall(
        r"<table\b.*?</table>", source_html, flags=re.DOTALL | re.IGNORECASE
    )


def _sec_bdc_candidate_schema(header: Sequence[str]) -> str:
    joined = " ".join(header).lower()
    if (
        "business description" in joined
        and "coupon" in joined
        and "maturity date" in joined
        and "fair value" in joined
    ):
        return "arcc_company_business_coupon_spread"
    if (
        "portfolio company" in joined
        and "industry" in joined
        and "floor" in joined
        and "fair value" in joined
    ):
        return "fsk_portfolio_company_rate_floor"
    if (
        "investment" in joined
        and "industry" in joined
        and "reference rate and spread" in joined
        and "fair value" in joined
    ):
        return "gsbd_investment_interest_rate"
    if (
        "company" in joined
        and "ref. rate" in joined
        and "maturity date" in joined
        and "fair value" in joined
    ):
        return "obdc_company_ref_cash_pik"
    return ""


def _sec_bdc_clean_amount_cells(values: Sequence[str]) -> list[str]:
    return [value for value in values if value not in {"", "$"}]


def _sec_bdc_is_investment_type(value: str) -> bool:
    lower = value.lower()
    return any(
        marker in lower
        for marker in (
            "loan",
            "debt",
            "note",
            "lien",
            "senior",
            "secured",
            "subordinated",
            "revolving",
            "preferred",
            "common",
            "equity",
            "warrant",
            "shares",
            "units",
        )
    )


def _sec_bdc_date_like_index(values: Sequence[str], start: int) -> int | None:
    for index in range(start, len(values)):
        if re.fullmatch(r"\d{1,2}/(?:\d{2}|\d{4})", values[index]) or re.fullmatch(
            r"\d{1,2}/\d{1,2}/(?:\d{2}|\d{4})", values[index]
        ):
            return index
    return None


def _sec_bdc_has_usable_terms(record: Mapping[str, str]) -> bool:
    if not record.get("borrower_or_issuer_name"):
        return False
    raw = record.get("raw_row_text", "").lower()
    if record["borrower_or_issuer_name"].lower().startswith("total "):
        return False
    if "total " in record["borrower_or_issuer_name"].lower() and not record.get(
        "maturity_date"
    ):
        return False
    return bool(
        record.get("maturity_date")
        or record.get("coupon_or_interest_rate")
        or record.get("reference_rate")
        or record.get("fair_value")
        or "sofr" in raw
        or "s+" in raw
        or "sf" in raw
    )


def _sec_bdc_plain_text(source_html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(source_html)))


def _sec_bdc_footnote_context(filing_html: str) -> dict[str, dict[str, str]]:
    text = _sec_bdc_plain_text(filing_html)
    patterns = {
        "non_accrual": re.compile(
            r"\(([A-Za-z0-9]+)\)\s+"
            r"((?:Loan|Asset|The investment)[^.]{0,180}"
            r"non-accrual status[^.]*\.)",
            flags=re.IGNORECASE,
        ),
        "non_income_producing": re.compile(
            r"\(([A-Za-z0-9]+)\)\s+([^()]{0,140}"
            r"non-income producing[^.]*\.)",
            flags=re.IGNORECASE,
        ),
        "maturity_extension_discussion": re.compile(
            r"\(([A-Za-z0-9]+)\)\s+([^()]{0,220}"
            r"(?:in discussions[^.]{0,120}extend the maturity|"
            r"extend the maturity date)[^.]*\.)",
            flags=re.IGNORECASE,
        ),
    }
    context: dict[str, dict[str, str]] = {}
    for category, pattern in patterns.items():
        category_context: dict[str, str] = {}
        for match in pattern.finditer(text):
            code = match.group(1)
            if code not in category_context:
                category_context[code] = match.group(2).strip()
        context[category] = category_context
    return context


def _sec_bdc_row_footnote_codes(record: Mapping[str, str]) -> set[str]:
    # Restrict performance status mapping to cells that carry explicit row-level
    # footnotes. Raw row text can include stale borrower text after colspans in
    # some filings, so it is not used for status assignment.
    return set(
        re.findall(
            r"\(([A-Za-z0-9]+)\)",
            " ".join(
                str(record.get(field, ""))
                for field in ("borrower_or_issuer_name", "footnotes")
            ),
        )
    )


def _sec_bdc_number(value: str) -> float | None:
    cleaned = (
        value.replace("$", "")
        .replace(",", "")
        .replace("—", "")
        .replace("–", "")
        .strip()
    )
    if not cleaned:
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("() ")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
        return None
    parsed = float(cleaned)
    return -parsed if negative else parsed


def _sec_bdc_ratio(numerator: str, denominator: str) -> str:
    parsed_numerator = _sec_bdc_number(numerator)
    parsed_denominator = _sec_bdc_number(denominator)
    if parsed_numerator is None or parsed_denominator in {None, 0.0}:
        return ""
    return f"{parsed_numerator / parsed_denominator:.6f}".rstrip("0").rstrip(".")


def _sec_bdc_performance_status_record(
    record: Mapping[str, str], footnote_context: Mapping[str, Mapping[str, str]]
) -> dict[str, str]:
    row_codes = _sec_bdc_row_footnote_codes(record)

    def matching_codes(category: str) -> list[str]:
        return sorted(row_codes & set(footnote_context.get(category, {})))

    non_accrual_codes = matching_codes("non_accrual")
    non_income_codes = matching_codes("non_income_producing")
    maturity_extension_codes = matching_codes("maturity_extension_discussion")

    fair_value_to_par = _sec_bdc_ratio(
        record.get("fair_value", ""), record.get("principal_or_par_value", "")
    )
    fair_value_to_cost = _sec_bdc_ratio(
        record.get("fair_value", ""), record.get("amortized_cost", "")
    )
    par_number = _sec_bdc_number(record.get("principal_or_par_value", ""))
    fair_value_number = _sec_bdc_number(record.get("fair_value", ""))
    fair_value_less_than_par = (
        fair_value_number is not None
        and par_number is not None
        and fair_value_number < par_number
    )
    pik_marker = bool(
        record.get("pik_component")
        or re.search(
            r"\bPIK\b|payment.?in.?kind",
            " ".join(
                record.get(field, "")
                for field in (
                    "coupon_or_interest_rate",
                    "reference_rate",
                    "spread",
                    "cash_component",
                    "raw_row_text",
                )
            ),
            flags=re.IGNORECASE,
        )
    )
    explicit_status_marker = bool(
        non_accrual_codes or non_income_codes or maturity_extension_codes or pik_marker
    )
    valuation_context_available = bool(fair_value_to_par or fair_value_to_cost)

    enriched = dict(record)
    enriched.update(
        {
            "source_schema_reviewed": "true",
            "public_reusable_company_filing_artifact_available": "true",
            "public_reusable_normalized_investment_terms_panel_available": "true",
            "public_reusable_borrower_level_performance_marker_available": str(
                explicit_status_marker or valuation_context_available
            ).lower(),
            "public_reusable_loan_level_pass_through_artifact_available": "false",
            "non_accrual_status_marker": str(bool(non_accrual_codes)).lower(),
            "non_accrual_footnote_codes": ",".join(non_accrual_codes),
            "non_accrual_footnote_text": " | ".join(
                footnote_context["non_accrual"][code] for code in non_accrual_codes
            ),
            "non_income_producing_marker": str(bool(non_income_codes)).lower(),
            "non_income_producing_footnote_codes": ",".join(non_income_codes),
            "maturity_extension_discussion_marker": str(
                bool(maturity_extension_codes)
            ).lower(),
            "maturity_extension_footnote_codes": ",".join(maturity_extension_codes),
            "pik_status_marker": str(pik_marker).lower(),
            "fair_value_to_principal_or_par_ratio": fair_value_to_par,
            "fair_value_to_amortized_cost_ratio": fair_value_to_cost,
            "fair_value_less_than_principal_or_par_marker": str(
                fair_value_less_than_par
            ).lower(),
            "valuation_gap_context_available": str(valuation_context_available).lower(),
            "portfolio_performance_status_context_available": str(
                explicit_status_marker or valuation_context_available
            ).lower(),
            "row_support_status": (
                "explicit_performance_status_marker_support"
                if explicit_status_marker
                else "valuation_gap_context_support"
                if valuation_context_available
                else "partial_performance_status_support_fail_closed"
            ),
            "missing_cell_blocker": (
                ""
                if explicit_status_marker or valuation_context_available
                else "missing_explicit_performance_marker_or_fair_value_ratio"
            ),
            "borrower_pass_through_context_available": "false",
            "nonbank_to_real_activity_context_available": "false",
            "method_blocker": (
                "public_bdc_performance_status_markers_are_admitted_but_no_"
                "monetary_pass_through_design_or_nonbank_real_activity_bridge_"
                "is_admitted"
            ),
            "denominator_prior_narrowing_allowed": "false",
            "split_denominator_promotion_allowed": "false",
            "formula_replacement_allowed": "false",
            "main_ratio_admission_allowed": "false",
            "incidence_output_enabled": "false",
            "welfare_tax_mpc_output_enabled": "false",
            "policy_failure_output_enabled": "false",
            "pricing_output_enabled": "false",
        }
    )
    return enriched


def _sec_bdc_terms_status_join_record(
    record: Mapping[str, str], footnote_context: Mapping[str, Mapping[str, str]]
) -> dict[str, str]:
    terms_support_status = record.get("row_support_status", "")
    terms_missing_blocker = record.get("missing_cell_blocker", "")
    enriched = _sec_bdc_performance_status_record(record, footnote_context)
    status_support_status = enriched.get("row_support_status", "")
    status_missing_blocker = enriched.get("missing_cell_blocker", "")
    terms_full = terms_support_status == "full_terms_support"
    status_available = (
        enriched.get("portfolio_performance_status_context_available") == "true"
    )
    blockers = [
        blocker
        for blocker in (
            terms_missing_blocker,
            status_missing_blocker,
            "missing_full_terms_support" if not terms_full else "",
            "missing_performance_status_or_valuation_context"
            if not status_available
            else "",
        )
        if blocker
    ]
    enriched.update(
        {
            "terms_row_support_status": terms_support_status,
            "terms_missing_cell_blocker": terms_missing_blocker,
            "performance_status_row_support_status": status_support_status,
            "performance_status_missing_cell_blocker": status_missing_blocker,
            "public_reusable_borrower_investment_terms_status_panel_available": "true",
            "public_reusable_borrower_level_terms_status_context_available": "true",
            "borrower_level_repayment_or_performance_status_context_available": str(
                status_available
            ).lower(),
            "monetary_pass_through_design_available": "false",
            "public_reusable_nonbank_real_activity_bridge_available": "false",
            "row_support_status": (
                "full_terms_and_performance_status_support"
                if terms_full and status_available
                else "partial_terms_status_support_fail_closed"
            ),
            "missing_cell_blocker": ";".join(blockers),
            "method_blocker": (
                "public_bdc_terms_status_join_rows_are_admitted_but_no_"
                "monetary_pass_through_design_repayment_schedule_panel_or_"
                "nonbank_real_activity_bridge_is_admitted"
            ),
        }
    )
    return enriched


def _sec_bdc_common_record(
    *,
    filing: Mapping[str, str],
    cik: str,
    ticker: str,
    registrant_name: str,
    filing_url: str,
    source_table_index: int,
    source_row_index: int,
    source_schema: str,
    raw_row: Sequence[str],
    borrower_or_issuer_name: str = "",
    business_description: str = "",
    industry: str = "",
    investment_type: str = "",
    coupon_or_interest_rate: str = "",
    reference_rate: str = "",
    spread: str = "",
    floor: str = "",
    cash_component: str = "",
    pik_component: str = "",
    acquisition_date: str = "",
    maturity_date: str = "",
    principal_or_par_value: str = "",
    shares_or_units: str = "",
    amortized_cost: str = "",
    fair_value: str = "",
    footnotes: str = "",
) -> dict[str, str]:
    raw_row_text = " | ".join(raw_row)
    record = {
        "date": filing["filing_date"],
        "report_date": filing["report_date"],
        "cik": cik,
        "ticker": ticker,
        "registrant_name": registrant_name,
        "form_type": filing["form_type"],
        "accession_number": filing["accession_number"],
        "filing_url": filing_url,
        "source_table_index": str(source_table_index),
        "source_row_index": str(source_row_index),
        "source_schema": source_schema,
        "borrower_or_issuer_name": borrower_or_issuer_name,
        "business_description": business_description,
        "industry": industry,
        "investment_type": investment_type,
        "coupon_or_interest_rate": coupon_or_interest_rate,
        "reference_rate": reference_rate,
        "spread": spread,
        "floor": floor,
        "cash_component": cash_component,
        "pik_component": pik_component,
        "acquisition_date": acquisition_date,
        "maturity_date": maturity_date,
        "principal_or_par_value": principal_or_par_value,
        "shares_or_units": shares_or_units,
        "amortized_cost": amortized_cost,
        "fair_value": fair_value,
        "amount_unit": "source_filing_table_units",
        "footnotes": footnotes,
        "raw_row_text": raw_row_text,
        "source_schema_reviewed": "true",
        "public_reusable_company_filing_artifact_available": "true",
        "public_reusable_normalized_investment_terms_panel_available": "true",
        "rate_term_available": str(
            bool(coupon_or_interest_rate or reference_rate or spread or cash_component)
        ).lower(),
        "maturity_available": str(bool(maturity_date)).lower(),
        "principal_or_par_available": str(bool(principal_or_par_value)).lower(),
        "fair_value_available": str(bool(fair_value)).lower(),
        "borrower_or_issuer_name_available": str(bool(borrower_or_issuer_name)).lower(),
        "row_support_status": (
            "full_terms_support"
            if borrower_or_issuer_name
            and maturity_date
            and (coupon_or_interest_rate or reference_rate or spread or cash_component)
            and principal_or_par_value
            and fair_value
            else "partial_terms_support_fail_closed"
        ),
        "missing_cell_blocker": ";".join(
            blocker
            for blocker, missing in (
                ("missing_borrower_or_issuer_name", not borrower_or_issuer_name),
                ("missing_maturity_date", not maturity_date),
                (
                    "missing_rate_or_reference_terms",
                    not (
                        coupon_or_interest_rate
                        or reference_rate
                        or spread
                        or cash_component
                    ),
                ),
                ("missing_principal_or_par_value", not principal_or_par_value),
                ("missing_fair_value", not fair_value),
            )
            if missing
        ),
        "borrower_pass_through_context_available": "false",
        "nonbank_to_real_activity_context_available": "false",
        "method_blocker": (
            "normalized_public_bdc_investment_terms_rows_are_admitted_but_"
            "no_monetary_pass_through_design_or_nonbank_real_activity_bridge_"
            "is_admitted"
        ),
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "policy_failure_output_enabled": "false",
        "pricing_output_enabled": "false",
    }
    if _sec_bdc_has_usable_terms(record):
        return record
    return {}


def _sec_bdc_parse_arcc_row(
    *,
    row: Sequence[str],
    current_borrower: str,
    common_kwargs: Mapping[str, object],
) -> tuple[dict[str, str], str]:
    if len(row) >= 12 and not _sec_bdc_is_investment_type(row[0]):
        tail = _sec_bdc_clean_amount_cells(row[8:])
        borrower = row[0]
        record = _sec_bdc_common_record(
            **common_kwargs,
            raw_row=row,
            borrower_or_issuer_name=borrower,
            business_description=row[1],
            investment_type=row[2],
            coupon_or_interest_rate=row[3],
            reference_rate=row[4],
            spread=row[5],
            acquisition_date=row[6],
            maturity_date=row[7],
            principal_or_par_value=tail[0] if len(tail) > 0 else "",
            amortized_cost=tail[1] if len(tail) > 1 else "",
            fair_value=tail[2] if len(tail) > 2 else "",
            footnotes=tail[3] if len(tail) > 3 else "",
        )
        return record, borrower
    if len(row) >= 9 and current_borrower and _sec_bdc_is_investment_type(row[0]):
        tail = _sec_bdc_clean_amount_cells(row[6:])
        record = _sec_bdc_common_record(
            **common_kwargs,
            raw_row=row,
            borrower_or_issuer_name=current_borrower,
            investment_type=row[0],
            coupon_or_interest_rate=row[1],
            reference_rate=row[2],
            spread=row[3],
            acquisition_date=row[4],
            maturity_date=row[5],
            principal_or_par_value=tail[0] if len(tail) > 0 else "",
            amortized_cost=tail[1] if len(tail) > 1 else "",
            fair_value=tail[2] if len(tail) > 2 else "",
            footnotes=tail[3] if len(tail) > 3 else "",
        )
        return record, current_borrower
    return {}, current_borrower


def _sec_bdc_parse_fsk_row(
    *, row: Sequence[str], common_kwargs: Mapping[str, object]
) -> dict[str, str]:
    if len(row) < 9:
        return {}
    maturity_index = _sec_bdc_date_like_index(row, 3)
    if maturity_index is None or maturity_index + 3 >= len(row):
        return {}
    rate_parts = row[3:maturity_index]
    tail = _sec_bdc_clean_amount_cells(row[maturity_index + 1 :])
    floor = rate_parts[-1] if rate_parts and "%" in rate_parts[-1] else ""
    return _sec_bdc_common_record(
        **common_kwargs,
        raw_row=row,
        borrower_or_issuer_name=row[0],
        footnotes=row[1],
        industry=row[2],
        reference_rate=rate_parts[0] if rate_parts else "",
        spread=" ".join(rate_parts[1:-1] if floor else rate_parts[1:]),
        floor=floor,
        maturity_date=row[maturity_index],
        principal_or_par_value=tail[0] if len(tail) > 0 else "",
        amortized_cost=tail[1] if len(tail) > 1 else "",
        fair_value=tail[2] if len(tail) > 2 else "",
    )


def _sec_bdc_parse_gsbd_row(
    *, row: Sequence[str], common_kwargs: Mapping[str, object]
) -> dict[str, str]:
    if len(row) < 12 or not row[1] or not row[4]:
        return {}
    tail = _sec_bdc_clean_amount_cells(row[5:])
    return _sec_bdc_common_record(
        **common_kwargs,
        raw_row=row,
        borrower_or_issuer_name=row[0],
        industry=row[1],
        coupon_or_interest_rate=row[2],
        reference_rate=row[3],
        maturity_date=row[4],
        principal_or_par_value=tail[0] if len(tail) > 0 else "",
        amortized_cost=tail[1] if len(tail) > 1 else "",
        fair_value=tail[2] if len(tail) > 2 else "",
        footnotes=tail[3] if len(tail) > 3 else "",
    )


def _sec_bdc_parse_obdc_row(
    *, row: Sequence[str], common_kwargs: Mapping[str, object]
) -> dict[str, str]:
    if len(row) < 8:
        return {}
    maturity_index = _sec_bdc_date_like_index(row, 3)
    if maturity_index is None:
        return {}
    tail = _sec_bdc_clean_amount_cells(row[maturity_index + 1 :])
    return _sec_bdc_common_record(
        **common_kwargs,
        raw_row=row,
        borrower_or_issuer_name=row[0],
        investment_type=row[1],
        reference_rate=row[2],
        cash_component=row[3] if maturity_index > 3 else "",
        pik_component=" ".join(row[4:maturity_index]) if maturity_index > 4 else "",
        maturity_date=row[maturity_index],
        principal_or_par_value=tail[0] if len(tail) > 0 else "",
        shares_or_units=tail[1] if len(tail) > 1 else "",
        amortized_cost=tail[2] if len(tail) > 2 else "",
        fair_value=tail[3] if len(tail) > 3 else "",
        footnotes=tail[4] if len(tail) > 4 else "",
    )


def _sec_bdc_portfolio_investment_terms_records(
    *,
    cik: str,
    expected_ticker: str,
    submissions_json: str,
    filing_html: str,
) -> list[dict[str, str]]:
    submissions = json.loads(submissions_json)
    if not isinstance(submissions, dict):
        raise ValueError("SEC BDC submissions payload is not an object")
    filing = _sec_bdc_latest_periodic_filing(submissions)
    registrant_name = str(submissions.get("name", "")).strip()
    filing_url = _sec_archive_document_url(
        cik=cik,
        accession_number=filing["accession_number"],
        primary_document=filing["primary_document"],
    )
    records: list[dict[str, str]] = []
    current_borrower = ""
    for table_index, table_html in enumerate(_table_html_blocks(filing_html)):
        table_rows = _html_table_rows(table_html)
        if not table_rows:
            continue
        header_index = -1
        source_schema = ""
        for candidate_index, row in enumerate(table_rows[:4]):
            source_schema = _sec_bdc_candidate_schema(row)
            if source_schema:
                header_index = candidate_index
                break
        if header_index < 0:
            continue
        current_borrower = ""
        for row_index, row in enumerate(
            table_rows[header_index + 1 :], start=header_index + 1
        ):
            if not row or row[0].lower().startswith("total "):
                continue
            common_kwargs = {
                "filing": filing,
                "cik": cik,
                "ticker": expected_ticker,
                "registrant_name": registrant_name,
                "filing_url": filing_url,
                "source_table_index": table_index,
                "source_row_index": row_index,
                "source_schema": source_schema,
            }
            if source_schema == "arcc_company_business_coupon_spread":
                record, current_borrower = _sec_bdc_parse_arcc_row(
                    row=row,
                    current_borrower=current_borrower,
                    common_kwargs=common_kwargs,
                )
            elif source_schema == "fsk_portfolio_company_rate_floor":
                record = _sec_bdc_parse_fsk_row(row=row, common_kwargs=common_kwargs)
                if record:
                    current_borrower = record["borrower_or_issuer_name"]
            elif source_schema == "gsbd_investment_interest_rate":
                record = _sec_bdc_parse_gsbd_row(row=row, common_kwargs=common_kwargs)
                if record:
                    current_borrower = record["borrower_or_issuer_name"]
            elif source_schema == "obdc_company_ref_cash_pik":
                record = _sec_bdc_parse_obdc_row(row=row, common_kwargs=common_kwargs)
                if record:
                    current_borrower = record["borrower_or_issuer_name"]
            else:
                record = {}
            if record:
                records.append(record)
    if not records:
        raise ValueError(
            f"SEC BDC filing produced no normalized investment-term rows: {cik}"
        )
    return records


def _sec_bdc_portfolio_investment_terms_snapshot(
    *, registry: SourceRegistry, source_dir: Path
) -> SourceSnapshot:
    series = registry.series[SEC_BDC_PORTFOLIO_INVESTMENT_TERMS_SERIES_ID]
    source_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    html_hashes: dict[str, str] = {}
    per_ticker_counts: dict[str, int] = {}
    for cik, ticker in SEC_BDC_REVIEW_CIKS.items():
        submissions_path = source_dir / f"CIK{cik}_submissions.json"
        submissions_url = f"{series.endpoint}CIK{cik}.json"
        if not submissions_path.exists():
            _download_source(submissions_url, submissions_path)
        submissions_json = submissions_path.read_text(encoding="utf-8")
        filing = _sec_bdc_latest_periodic_filing(json.loads(submissions_json))
        filing_url = _sec_archive_document_url(
            cik=cik,
            accession_number=filing["accession_number"],
            primary_document=filing["primary_document"],
        )
        filing_path = (
            source_dir / f"CIK{cik}_{filing['accession_number'].replace('-', '')}_"
            f"{filing['primary_document']}"
        )
        if not filing_path.exists():
            _download_source(filing_url, filing_path)
        filing_html = filing_path.read_text(encoding="utf-8", errors="replace")
        ticker_records = _sec_bdc_portfolio_investment_terms_records(
            cik=cik,
            expected_ticker=ticker,
            submissions_json=submissions_json,
            filing_html=filing_html,
        )
        records.extend(ticker_records)
        per_ticker_counts[ticker] = len(ticker_records)
        html_hashes[cik] = hashlib.sha256(filing_html.encode("utf-8")).hexdigest()

    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    note = (
        "sec_edgar_bdc_portfolio_investment_terms_panel;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "reviewed_tickers="
        f"{','.join(SEC_BDC_REVIEW_CIKS.values())};"
        "per_ticker_row_count="
        f"{','.join(f'{ticker}:{count}' for ticker, count in per_ticker_counts.items())};"
        "source_html_sha256_summary="
        f"{','.join(f'{cik}:{value}' for cik, value in html_hashes.items())};"
        "public_reusable_normalized_investment_terms_panel_available=true;"
        "borrower_pass_through_context_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="live_sec_edgar_normalized_filing_table_panel",
            note=note,
        ),
        records=records,
    )


def _sec_bdc_portfolio_performance_status_snapshot(
    *, registry: SourceRegistry, source_dir: Path
) -> SourceSnapshot:
    series = registry.series[SEC_BDC_PORTFOLIO_PERFORMANCE_STATUS_SERIES_ID]
    source_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    html_hashes: dict[str, str] = {}
    per_ticker_counts: dict[str, int] = {}
    for cik, ticker in SEC_BDC_REVIEW_CIKS.items():
        submissions_path = source_dir / f"CIK{cik}_submissions.json"
        submissions_url = f"{series.endpoint}CIK{cik}.json"
        if not submissions_path.exists():
            _download_source(submissions_url, submissions_path)
        submissions_json = submissions_path.read_text(encoding="utf-8")
        filing = _sec_bdc_latest_periodic_filing(json.loads(submissions_json))
        filing_url = _sec_archive_document_url(
            cik=cik,
            accession_number=filing["accession_number"],
            primary_document=filing["primary_document"],
        )
        filing_path = (
            source_dir / f"CIK{cik}_{filing['accession_number'].replace('-', '')}_"
            f"{filing['primary_document']}"
        )
        if not filing_path.exists():
            _download_source(filing_url, filing_path)
        filing_html = filing_path.read_text(encoding="utf-8", errors="replace")
        footnote_context = _sec_bdc_footnote_context(filing_html)
        ticker_terms_records = _sec_bdc_portfolio_investment_terms_records(
            cik=cik,
            expected_ticker=ticker,
            submissions_json=submissions_json,
            filing_html=filing_html,
        )
        ticker_records = [
            _sec_bdc_performance_status_record(record, footnote_context)
            for record in ticker_terms_records
        ]
        records.extend(ticker_records)
        per_ticker_counts[ticker] = len(ticker_records)
        html_hashes[cik] = hashlib.sha256(filing_html.encode("utf-8")).hexdigest()

    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    non_accrual_rows = sum(
        record["non_accrual_status_marker"] == "true" for record in records
    )
    non_income_rows = sum(
        record["non_income_producing_marker"] == "true" for record in records
    )
    maturity_extension_rows = sum(
        record["maturity_extension_discussion_marker"] == "true" for record in records
    )
    pik_rows = sum(record["pik_status_marker"] == "true" for record in records)
    valuation_gap_rows = sum(
        record["valuation_gap_context_available"] == "true" for record in records
    )
    fair_value_below_par_rows = sum(
        record["fair_value_less_than_principal_or_par_marker"] == "true"
        for record in records
    )
    note = (
        "sec_edgar_bdc_portfolio_performance_status_panel;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "reviewed_tickers="
        f"{','.join(SEC_BDC_REVIEW_CIKS.values())};"
        "per_ticker_row_count="
        f"{','.join(f'{ticker}:{count}' for ticker, count in per_ticker_counts.items())};"
        f"non_accrual_marker_rows={non_accrual_rows};"
        f"non_income_producing_marker_rows={non_income_rows};"
        f"maturity_extension_discussion_rows={maturity_extension_rows};"
        f"pik_marker_rows={pik_rows};"
        f"valuation_gap_context_rows={valuation_gap_rows};"
        f"fair_value_below_par_rows={fair_value_below_par_rows};"
        "source_html_sha256_summary="
        f"{','.join(f'{cik}:{value}' for cik, value in html_hashes.items())};"
        "public_reusable_borrower_level_performance_marker_available=true;"
        "public_reusable_loan_level_pass_through_artifact_available=false;"
        "borrower_pass_through_context_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="live_sec_edgar_bdc_performance_status_panel",
            note=note,
        ),
        records=records,
    )


def _sec_bdc_portfolio_terms_status_join_snapshot(
    *, registry: SourceRegistry, source_dir: Path
) -> SourceSnapshot:
    series = registry.series[SEC_BDC_PORTFOLIO_TERMS_STATUS_JOIN_SERIES_ID]
    source_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    html_hashes: dict[str, str] = {}
    per_ticker_counts: dict[str, int] = {}
    for cik, ticker in SEC_BDC_REVIEW_CIKS.items():
        submissions_path = source_dir / f"CIK{cik}_submissions.json"
        submissions_url = f"{series.endpoint}CIK{cik}.json"
        if not submissions_path.exists():
            _download_source(submissions_url, submissions_path)
        submissions_json = submissions_path.read_text(encoding="utf-8")
        filing = _sec_bdc_latest_periodic_filing(json.loads(submissions_json))
        filing_url = _sec_archive_document_url(
            cik=cik,
            accession_number=filing["accession_number"],
            primary_document=filing["primary_document"],
        )
        filing_path = (
            source_dir / f"CIK{cik}_{filing['accession_number'].replace('-', '')}_"
            f"{filing['primary_document']}"
        )
        if not filing_path.exists():
            _download_source(filing_url, filing_path)
        filing_html = filing_path.read_text(encoding="utf-8", errors="replace")
        footnote_context = _sec_bdc_footnote_context(filing_html)
        ticker_terms_records = _sec_bdc_portfolio_investment_terms_records(
            cik=cik,
            expected_ticker=ticker,
            submissions_json=submissions_json,
            filing_html=filing_html,
        )
        ticker_records = [
            _sec_bdc_terms_status_join_record(record, footnote_context)
            for record in ticker_terms_records
        ]
        records.extend(ticker_records)
        per_ticker_counts[ticker] = len(ticker_records)
        html_hashes[cik] = hashlib.sha256(filing_html.encode("utf-8")).hexdigest()

    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    full_terms_rows = sum(
        record["terms_row_support_status"] == "full_terms_support" for record in records
    )
    performance_context_rows = sum(
        record["portfolio_performance_status_context_available"] == "true"
        for record in records
    )
    full_terms_and_status_rows = sum(
        record["row_support_status"] == "full_terms_and_performance_status_support"
        for record in records
    )
    non_accrual_rows = sum(
        record["non_accrual_status_marker"] == "true" for record in records
    )
    pik_rows = sum(record["pik_status_marker"] == "true" for record in records)
    valuation_gap_rows = sum(
        record["valuation_gap_context_available"] == "true" for record in records
    )
    fair_value_below_par_rows = sum(
        record["fair_value_less_than_principal_or_par_marker"] == "true"
        for record in records
    )
    note = (
        "sec_edgar_bdc_portfolio_terms_status_join_panel;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "reviewed_tickers="
        f"{','.join(SEC_BDC_REVIEW_CIKS.values())};"
        "per_ticker_row_count="
        f"{','.join(f'{ticker}:{count}' for ticker, count in per_ticker_counts.items())};"
        f"full_terms_rows={full_terms_rows};"
        f"performance_status_context_rows={performance_context_rows};"
        f"full_terms_and_performance_status_rows={full_terms_and_status_rows};"
        f"non_accrual_marker_rows={non_accrual_rows};"
        f"pik_marker_rows={pik_rows};"
        f"valuation_gap_context_rows={valuation_gap_rows};"
        f"fair_value_below_par_rows={fair_value_below_par_rows};"
        "source_html_sha256_summary="
        f"{','.join(f'{cik}:{value}' for cik, value in html_hashes.items())};"
        "public_reusable_borrower_investment_terms_status_panel_available=true;"
        "borrower_level_repayment_or_performance_status_context_available=true;"
        "monetary_pass_through_design_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="live_sec_edgar_bdc_terms_status_join_panel",
            note=note,
        ),
        records=records,
    )


def _sec_bdc_time_dimension_record(record: Mapping[str, str]) -> dict[str, str]:
    enriched = dict(record)
    blockers = [
        blocker
        for blocker in (
            enriched.get("missing_cell_blocker", ""),
            "no_stable_public_borrower_identifier_for_cross_filing_matching",
            "no_repayment_schedule_panel",
            "no_monetary_pass_through_design",
            "no_nonbank_real_activity_bridge",
        )
        if blocker
    ]
    enriched.update(
        {
            "public_reusable_borrower_investment_time_dimension_available": "true",
            "public_reusable_periodic_filing_performance_time_context_available": "true",
            "stable_public_borrower_identifier_available": "false",
            "public_reusable_repayment_schedule_panel_available": "false",
            "monetary_pass_through_design_available": "false",
            "nonbank_to_real_activity_context_available": "false",
            "row_support_status": (
                "filing_period_terms_status_time_context_fail_closed"
                if enriched.get(
                    "borrower_level_repayment_or_performance_status_context_available"
                )
                == "true"
                else "partial_filing_period_time_context_fail_closed"
            ),
            "missing_cell_blocker": ";".join(blockers),
            "method_blocker": (
                "public_bdc_terms_status_time_rows_are_admitted_across_recent_"
                "periodic_filings_but_no_stable_public_borrower_identifier_"
                "repayment_schedule_panel_monetary_pass_through_design_or_"
                "nonbank_real_activity_bridge_is_admitted"
            ),
            "denominator_prior_narrowing_allowed": "false",
            "split_denominator_promotion_allowed": "false",
            "formula_replacement_allowed": "false",
            "main_ratio_admission_allowed": "false",
            "incidence_output_enabled": "false",
            "welfare_tax_mpc_output_enabled": "false",
            "policy_failure_output_enabled": "false",
            "pricing_output_enabled": "false",
        }
    )
    return enriched


def _sec_bdc_portfolio_terms_status_time_snapshot(
    *, registry: SourceRegistry, source_dir: Path
) -> SourceSnapshot:
    series = registry.series[SEC_BDC_PORTFOLIO_TERMS_STATUS_TIME_SERIES_ID]
    source_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    html_hashes: dict[str, str] = {}
    per_ticker_counts: dict[str, int] = {}
    per_ticker_filing_counts: dict[str, int] = {}
    for cik, ticker in SEC_BDC_REVIEW_CIKS.items():
        submissions_path = source_dir / f"CIK{cik}_submissions.json"
        submissions_url = f"{series.endpoint}CIK{cik}.json"
        if not submissions_path.exists():
            _download_source(submissions_url, submissions_path)
        submissions_json = submissions_path.read_text(encoding="utf-8")
        submissions = json.loads(submissions_json)
        filings = _sec_bdc_recent_periodic_filings(submissions, max_filings=4)
        ticker_count = 0
        for filing in filings:
            filing_url = _sec_archive_document_url(
                cik=cik,
                accession_number=filing["accession_number"],
                primary_document=filing["primary_document"],
            )
            filing_path = (
                source_dir / f"CIK{cik}_{filing['accession_number'].replace('-', '')}_"
                f"{filing['primary_document']}"
            )
            if not filing_path.exists():
                _download_source(filing_url, filing_path)
            filing_html = filing_path.read_text(encoding="utf-8", errors="replace")
            single_filing_submissions = _sec_bdc_submissions_for_single_filing(
                submissions, filing
            )
            footnote_context = _sec_bdc_footnote_context(filing_html)
            terms_records = _sec_bdc_portfolio_investment_terms_records(
                cik=cik,
                expected_ticker=ticker,
                submissions_json=single_filing_submissions,
                filing_html=filing_html,
            )
            filing_records = [
                _sec_bdc_time_dimension_record(
                    _sec_bdc_terms_status_join_record(record, footnote_context)
                )
                for record in terms_records
            ]
            records.extend(filing_records)
            ticker_count += len(filing_records)
            html_hashes[f"{cik}:{filing['report_date']}"] = hashlib.sha256(
                filing_html.encode("utf-8")
            ).hexdigest()
        per_ticker_counts[ticker] = ticker_count
        per_ticker_filing_counts[ticker] = len(filings)

    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    first_report_date = min(record["report_date"] for record in records)
    latest_report_date = max(record["report_date"] for record in records)
    filing_count = len({record["accession_number"] for record in records})
    report_date_count = len({record["report_date"] for record in records})
    performance_context_rows = sum(
        record["portfolio_performance_status_context_available"] == "true"
        for record in records
    )
    full_terms_and_status_rows = sum(
        record["terms_row_support_status"] == "full_terms_support"
        and record["portfolio_performance_status_context_available"] == "true"
        for record in records
    )
    non_accrual_rows = sum(
        record["non_accrual_status_marker"] == "true" for record in records
    )
    pik_rows = sum(record["pik_status_marker"] == "true" for record in records)
    valuation_gap_rows = sum(
        record["valuation_gap_context_available"] == "true" for record in records
    )
    fair_value_below_par_rows = sum(
        record["fair_value_less_than_principal_or_par_marker"] == "true"
        for record in records
    )
    note = (
        "sec_edgar_bdc_portfolio_terms_status_time_panel;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"first_report_date={first_report_date};"
        f"latest_report_date={latest_report_date};"
        f"periodic_filing_count={filing_count};"
        f"report_date_count={report_date_count};"
        "reviewed_tickers="
        f"{','.join(SEC_BDC_REVIEW_CIKS.values())};"
        "per_ticker_row_count="
        f"{','.join(f'{ticker}:{count}' for ticker, count in per_ticker_counts.items())};"
        "per_ticker_periodic_filing_count="
        f"{','.join(f'{ticker}:{count}' for ticker, count in per_ticker_filing_counts.items())};"
        f"performance_status_context_rows={performance_context_rows};"
        f"full_terms_and_performance_status_rows={full_terms_and_status_rows};"
        f"non_accrual_marker_rows={non_accrual_rows};"
        f"pik_marker_rows={pik_rows};"
        f"valuation_gap_context_rows={valuation_gap_rows};"
        f"fair_value_below_par_rows={fair_value_below_par_rows};"
        "source_html_sha256_summary="
        f"{','.join(f'{key}:{value}' for key, value in html_hashes.items())};"
        "public_reusable_borrower_investment_time_dimension_available=true;"
        "public_reusable_periodic_filing_performance_time_context_available=true;"
        "stable_public_borrower_identifier_available=false;"
        "public_reusable_repayment_schedule_panel_available=false;"
        "monetary_pass_through_design_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="live_sec_edgar_bdc_terms_status_time_panel",
            note=note,
        ),
        records=records,
    )


def _sec_bdc_reference_rate_category(record: Mapping[str, str]) -> str:
    reference_rate = str(record.get("reference_rate", "")).strip()
    if not reference_rate:
        return "missing_reference_rate"
    reference_lower = reference_rate.lower()
    if "sofr" in reference_lower:
        return "explicit_sofr_reference_rate"
    if "libor" in reference_lower:
        return "legacy_libor_reference_rate"
    if any(term in reference_lower for term in ("corra", "euribor", "sonia")):
        return "other_named_benchmark_reference_rate"
    if "prime" in reference_lower or "base rate" in reference_lower:
        return "prime_or_base_rate_reference"
    if re.search(r"(^|[^a-z])s\s*\+", reference_lower) or reference_lower in {
        "s",
        "sf",
        "s+",
    }:
        return "source_abbreviated_reference_rate"
    return "other_source_reference_rate"


def _sec_bdc_floating_rate_pass_through_design_records(
    records: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, str]]] = {}
    for record in records:
        category = _sec_bdc_reference_rate_category(record)
        if category in {
            "missing_reference_rate",
            "other_source_reference_rate",
        }:
            continue
        key = (
            str(record.get("ticker", "")).strip(),
            str(record.get("report_date", "")).strip(),
            category,
        )
        grouped.setdefault(key, []).append(record)

    summary_rows: list[dict[str, str]] = []
    for (ticker, report_date, category), group_records in sorted(grouped.items()):
        if not ticker or not report_date:
            continue
        reference_counts: dict[str, int] = {}
        borrower_names: set[str] = set()
        for record in group_records:
            reference_rate = str(record.get("reference_rate", "")).strip()
            if reference_rate:
                reference_counts[reference_rate] = (
                    reference_counts.get(reference_rate, 0) + 1
                )
            borrower_name = str(record.get("borrower_or_issuer_name", "")).strip()
            if borrower_name:
                borrower_names.add(borrower_name)
        reference_examples = ",".join(
            value
            for value, _count in sorted(
                reference_counts.items(), key=lambda item: (-item[1], item[0])
            )[:5]
        )
        row_count = len(group_records)
        spread_or_cash_pik_rows = sum(
            any(str(record.get(field, "")).strip() for field in fields)
            for record in group_records
            for fields in [("spread", "cash_component", "pik_component")]
        )
        full_terms_rows = sum(
            record.get("terms_row_support_status") == "full_terms_support"
            for record in group_records
        )
        summary_rows.append(
            {
                "date": max(str(record.get("date", "")) for record in group_records),
                "report_date": report_date,
                "ticker": ticker,
                "reference_rate_category": category,
                "reference_rate_examples": reference_examples,
                "source_row_count": str(row_count),
                "unique_source_borrower_name_count": str(len(borrower_names)),
                "full_terms_support_rows": str(full_terms_rows),
                "spread_or_cash_pik_term_rows": str(spread_or_cash_pik_rows),
                "floor_term_rows": str(
                    sum(
                        bool(str(record.get("floor", "")).strip())
                        for record in group_records
                    )
                ),
                "maturity_term_rows": str(
                    sum(
                        bool(str(record.get("maturity_date", "")).strip())
                        for record in group_records
                    )
                ),
                "principal_or_par_rows": str(
                    sum(
                        bool(str(record.get("principal_or_par_value", "")).strip())
                        for record in group_records
                    )
                ),
                "fair_value_rows": str(
                    sum(
                        bool(str(record.get("fair_value", "")).strip())
                        for record in group_records
                    )
                ),
                "non_accrual_marker_rows": str(
                    sum(
                        record.get("non_accrual_status_marker") == "true"
                        for record in group_records
                    )
                ),
                "pik_marker_rows": str(
                    sum(
                        record.get("pik_status_marker") == "true"
                        for record in group_records
                    )
                ),
                "valuation_gap_context_rows": str(
                    sum(
                        record.get("valuation_gap_context_available") == "true"
                        for record in group_records
                    )
                ),
                "public_contractual_reference_rate_terms_available": "true",
                "contractual_floating_rate_pass_through_context_available": "true",
                "promotion_grade_monetary_pass_through_design_available": "false",
                "stable_public_borrower_identifier_available": "false",
                "public_reusable_repayment_schedule_panel_available": "false",
                "nonbank_to_real_activity_context_available": "false",
                "row_support_status": (
                    "contractual_reference_rate_terms_context_fail_closed"
                ),
                "method_blocker": (
                    "public_bdc_contractual_reference_rate_spread_floor_and_"
                    "maturity_terms_support_a_pass_through_context_review_but_"
                    "do_not_provide_stable_borrower_ids_repayment_schedules_"
                    "borrower_cashflow_effects_or_nonbank_real_activity_mapping"
                ),
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return summary_rows


def _sec_bdc_floating_rate_pass_through_design_snapshot(
    *,
    registry: SourceRegistry,
    terms_status_time_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[SEC_BDC_FLOATING_RATE_PASS_THROUGH_DESIGN_SERIES_ID]
    records = _sec_bdc_floating_rate_pass_through_design_records(
        terms_status_time_snapshot.records
    )
    if not records:
        raise ValueError("SEC BDC floating-rate pass-through design records are empty")
    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    first_report_date = min(record["report_date"] for record in records)
    latest_report_date = max(record["report_date"] for record in records)
    source_row_count = sum(int(record["source_row_count"]) for record in records)
    explicit_sofr_rows = sum(
        int(record["source_row_count"])
        for record in records
        if record["reference_rate_category"] == "explicit_sofr_reference_rate"
    )
    abbreviated_reference_rows = sum(
        int(record["source_row_count"])
        for record in records
        if record["reference_rate_category"] == "source_abbreviated_reference_rate"
    )
    spread_or_cash_pik_rows = sum(
        int(record["spread_or_cash_pik_term_rows"]) for record in records
    )
    note = (
        "sec_edgar_bdc_floating_rate_pass_through_design_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"underlying_terms_status_source_row_count={source_row_count};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"first_report_date={first_report_date};"
        f"latest_report_date={latest_report_date};"
        f"explicit_sofr_source_rows={explicit_sofr_rows};"
        f"source_abbreviated_reference_rate_rows={abbreviated_reference_rows};"
        f"spread_or_cash_pik_term_rows={spread_or_cash_pik_rows};"
        "derived_from_series_id="
        f"{terms_status_time_snapshot.metadata.series_id};"
        "public_contractual_reference_rate_terms_available=true;"
        "contractual_floating_rate_pass_through_context_available=true;"
        "promotion_grade_monetary_pass_through_design_available=false;"
        "stable_public_borrower_identifier_available=false;"
        "public_reusable_repayment_schedule_panel_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="derived_sec_edgar_bdc_floating_rate_pass_through_context",
            note=note,
        ),
        records=records,
    )


def _sec_bdc_normalized_borrower_name(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    return normalized


def _sec_bdc_normalized_signature_part(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _sec_bdc_borrower_name_continuity_records(
    records: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str], list[Mapping[str, str]]] = {}
    for record in records:
        ticker = str(record.get("ticker", "")).strip()
        borrower_name = str(record.get("borrower_or_issuer_name", "")).strip()
        normalized_name = _sec_bdc_normalized_borrower_name(borrower_name)
        if not ticker or not normalized_name:
            continue
        grouped.setdefault((ticker, normalized_name), []).append(record)

    rows: list[dict[str, str]] = []
    for (ticker, normalized_name), group_records in sorted(grouped.items()):
        report_dates = sorted(
            {
                str(record.get("report_date", "")).strip()
                for record in group_records
                if str(record.get("report_date", "")).strip()
            }
        )
        if len(report_dates) < 2:
            continue
        observation_dates = sorted(
            {
                str(record.get("date", "")).strip()
                for record in group_records
                if str(record.get("date", "")).strip()
            }
        )
        source_name_counts: dict[str, int] = {}
        investment_type_counts: dict[str, int] = {}
        accessions = {
            str(record.get("accession_number", "")).strip()
            for record in group_records
            if str(record.get("accession_number", "")).strip()
        }
        for record in group_records:
            source_name = str(record.get("borrower_or_issuer_name", "")).strip()
            if source_name:
                source_name_counts[source_name] = (
                    source_name_counts.get(source_name, 0) + 1
                )
            investment_type = str(record.get("investment_type", "")).strip()
            if investment_type:
                investment_type_counts[investment_type] = (
                    investment_type_counts.get(investment_type, 0) + 1
                )
        source_name_examples = "|".join(
            value
            for value, _count in sorted(
                source_name_counts.items(), key=lambda item: (-item[1], item[0])
            )[:3]
        )
        investment_type_examples = "|".join(
            value
            for value, _count in sorted(
                investment_type_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:5]
        )
        spread_or_cash_pik_rows = sum(
            any(str(record.get(field, "")).strip() for field in fields)
            for record in group_records
            for fields in [("spread", "cash_component", "pik_component")]
        )
        rows.append(
            {
                "date": observation_dates[-1],
                "ticker": ticker,
                "normalized_source_borrower_name": normalized_name,
                "source_borrower_name_examples": source_name_examples,
                "investment_type_examples": investment_type_examples,
                "source_row_count": str(len(group_records)),
                "report_date_count": str(len(report_dates)),
                "first_report_date": report_dates[0],
                "latest_report_date": report_dates[-1],
                "first_observation_date": observation_dates[0],
                "latest_observation_date": observation_dates[-1],
                "accession_count": str(len(accessions)),
                "full_terms_support_rows": str(
                    sum(
                        record.get("terms_row_support_status") == "full_terms_support"
                        for record in group_records
                    )
                ),
                "reference_rate_term_rows": str(
                    sum(
                        bool(str(record.get("reference_rate", "")).strip())
                        for record in group_records
                    )
                ),
                "spread_or_cash_pik_term_rows": str(spread_or_cash_pik_rows),
                "maturity_term_rows": str(
                    sum(
                        bool(str(record.get("maturity_date", "")).strip())
                        for record in group_records
                    )
                ),
                "principal_or_par_rows": str(
                    sum(
                        bool(str(record.get("principal_or_par_value", "")).strip())
                        for record in group_records
                    )
                ),
                "fair_value_rows": str(
                    sum(
                        bool(str(record.get("fair_value", "")).strip())
                        for record in group_records
                    )
                ),
                "non_accrual_marker_rows": str(
                    sum(
                        record.get("non_accrual_status_marker") == "true"
                        for record in group_records
                    )
                ),
                "pik_marker_rows": str(
                    sum(
                        record.get("pik_status_marker") == "true"
                        for record in group_records
                    )
                ),
                "fair_value_below_par_rows": str(
                    sum(
                        record.get("fair_value_less_than_principal_or_par_marker")
                        == "true"
                        for record in group_records
                    )
                ),
                "exact_public_borrower_name_continuity_context_available": "true",
                "stable_public_borrower_identifier_available": "false",
                "public_reusable_loan_identifier_available": "false",
                "public_reusable_repayment_schedule_panel_available": "false",
                "borrower_cashflow_pass_through_available": "false",
                "monetary_pass_through_design_available": "false",
                "nonbank_to_real_activity_context_available": "false",
                "row_support_status": "exact_source_name_continuity_context_fail_closed",
                "method_blocker": (
                    "public_bdc_rows_match_exact_normalized_source_borrower_names_"
                    "across_recent_filings_but_names_are_not_stable_legal_entity_"
                    "or_loan_identifiers_and_do_not_supply_repayment_schedules_"
                    "borrower_cashflow_effects_or_real_activity_mapping"
                ),
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return rows


def _sec_bdc_borrower_name_continuity_snapshot(
    *,
    registry: SourceRegistry,
    terms_status_time_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[SEC_BDC_BORROWER_NAME_CONTINUITY_SERIES_ID]
    records = _sec_bdc_borrower_name_continuity_records(
        terms_status_time_snapshot.records
    )
    if not records:
        raise ValueError("SEC BDC borrower-name continuity records are empty")
    records_hash = _records_sha256(records)
    first_date = min(record["first_observation_date"] for record in records)
    latest_date = max(record["latest_observation_date"] for record in records)
    first_report_date = min(record["first_report_date"] for record in records)
    latest_report_date = max(record["latest_report_date"] for record in records)
    source_row_count = sum(int(record["source_row_count"]) for record in records)
    names_with_four_report_dates = sum(
        int(record["report_date_count"]) >= 4 for record in records
    )
    note = (
        "sec_edgar_bdc_borrower_name_continuity_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"underlying_terms_status_source_row_count={source_row_count};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"first_report_date={first_report_date};"
        f"latest_report_date={latest_report_date};"
        f"exact_normalized_name_continuity_rows={len(records)};"
        f"names_with_four_report_dates={names_with_four_report_dates};"
        "derived_from_series_id="
        f"{terms_status_time_snapshot.metadata.series_id};"
        "exact_public_borrower_name_continuity_context_available=true;"
        "stable_public_borrower_identifier_available=false;"
        "public_reusable_loan_identifier_available=false;"
        "public_reusable_repayment_schedule_panel_available=false;"
        "borrower_cashflow_pass_through_available=false;"
        "monetary_pass_through_design_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="derived_sec_edgar_bdc_borrower_name_continuity_context",
            note=note,
        ),
        records=records,
    )


def _sec_bdc_investment_signature_continuity_records(
    records: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str, str, str], list[Mapping[str, str]]] = {}
    for record in records:
        ticker = str(record.get("ticker", "")).strip()
        borrower_name = str(record.get("borrower_or_issuer_name", "")).strip()
        normalized_name = _sec_bdc_normalized_borrower_name(borrower_name)
        investment_type = _sec_bdc_normalized_signature_part(
            str(record.get("investment_type", ""))
        )
        maturity_date = _sec_bdc_normalized_signature_part(
            str(record.get("maturity_date", ""))
        )
        reference_rate_category = _sec_bdc_reference_rate_category(record)
        if not all((ticker, normalized_name, investment_type, maturity_date)):
            continue
        if reference_rate_category in {
            "missing_reference_rate",
            "other_source_reference_rate",
        }:
            continue
        key = (
            ticker,
            normalized_name,
            investment_type,
            maturity_date,
            reference_rate_category,
        )
        grouped.setdefault(key, []).append(record)

    rows: list[dict[str, str]] = []
    for (
        ticker,
        normalized_name,
        investment_type,
        maturity_date,
        reference_rate_category,
    ), group_records in sorted(grouped.items()):
        report_dates = sorted(
            {
                str(record.get("report_date", "")).strip()
                for record in group_records
                if str(record.get("report_date", "")).strip()
            }
        )
        if len(report_dates) < 2:
            continue
        observation_dates = sorted(
            {
                str(record.get("date", "")).strip()
                for record in group_records
                if str(record.get("date", "")).strip()
            }
        )
        accessions = {
            str(record.get("accession_number", "")).strip()
            for record in group_records
            if str(record.get("accession_number", "")).strip()
        }
        source_name_counts: dict[str, int] = {}
        investment_type_counts: dict[str, int] = {}
        maturity_counts: dict[str, int] = {}
        for record in group_records:
            source_name = str(record.get("borrower_or_issuer_name", "")).strip()
            if source_name:
                source_name_counts[source_name] = (
                    source_name_counts.get(source_name, 0) + 1
                )
            source_investment_type = str(record.get("investment_type", "")).strip()
            if source_investment_type:
                investment_type_counts[source_investment_type] = (
                    investment_type_counts.get(source_investment_type, 0) + 1
                )
            source_maturity = str(record.get("maturity_date", "")).strip()
            if source_maturity:
                maturity_counts[source_maturity] = (
                    maturity_counts.get(source_maturity, 0) + 1
                )
        source_name_examples = "|".join(
            value
            for value, _count in sorted(
                source_name_counts.items(), key=lambda item: (-item[1], item[0])
            )[:3]
        )
        investment_type_examples = "|".join(
            value
            for value, _count in sorted(
                investment_type_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        )
        maturity_date_examples = "|".join(
            value
            for value, _count in sorted(
                maturity_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[:3]
        )
        spread_or_cash_pik_rows = sum(
            any(str(record.get(field, "")).strip() for field in fields)
            for record in group_records
            for fields in [("spread", "cash_component", "pik_component")]
        )
        signature_key = "::".join(
            (
                ticker,
                normalized_name,
                investment_type,
                maturity_date,
                reference_rate_category,
            )
        )
        rows.append(
            {
                "date": observation_dates[-1],
                "ticker": ticker,
                "public_investment_signature_key": signature_key,
                "normalized_source_borrower_name": normalized_name,
                "normalized_investment_type": investment_type,
                "normalized_maturity_date": maturity_date,
                "reference_rate_category": reference_rate_category,
                "source_borrower_name_examples": source_name_examples,
                "investment_type_examples": investment_type_examples,
                "maturity_date_examples": maturity_date_examples,
                "source_row_count": str(len(group_records)),
                "report_date_count": str(len(report_dates)),
                "first_report_date": report_dates[0],
                "latest_report_date": report_dates[-1],
                "first_observation_date": observation_dates[0],
                "latest_observation_date": observation_dates[-1],
                "accession_count": str(len(accessions)),
                "full_terms_support_rows": str(
                    sum(
                        record.get("terms_row_support_status") == "full_terms_support"
                        for record in group_records
                    )
                ),
                "reference_rate_term_rows": str(
                    sum(
                        bool(str(record.get("reference_rate", "")).strip())
                        for record in group_records
                    )
                ),
                "spread_or_cash_pik_term_rows": str(spread_or_cash_pik_rows),
                "maturity_term_rows": str(
                    sum(
                        bool(str(record.get("maturity_date", "")).strip())
                        for record in group_records
                    )
                ),
                "principal_or_par_rows": str(
                    sum(
                        bool(str(record.get("principal_or_par_value", "")).strip())
                        for record in group_records
                    )
                ),
                "fair_value_rows": str(
                    sum(
                        bool(str(record.get("fair_value", "")).strip())
                        for record in group_records
                    )
                ),
                "non_accrual_marker_rows": str(
                    sum(
                        record.get("non_accrual_status_marker") == "true"
                        for record in group_records
                    )
                ),
                "pik_marker_rows": str(
                    sum(
                        record.get("pik_status_marker") == "true"
                        for record in group_records
                    )
                ),
                "fair_value_below_par_rows": str(
                    sum(
                        record.get("fair_value_less_than_principal_or_par_marker")
                        == "true"
                        for record in group_records
                    )
                ),
                "public_investment_signature_continuity_context_available": "true",
                "stable_public_borrower_identifier_available": "false",
                "public_reusable_loan_identifier_available": "false",
                "public_reusable_repayment_schedule_panel_available": "false",
                "borrower_cashflow_pass_through_available": "false",
                "monetary_pass_through_design_available": "false",
                "nonbank_to_real_activity_context_available": "false",
                "row_support_status": (
                    "public_investment_signature_continuity_context_fail_closed"
                ),
                "method_blocker": (
                    "public_bdc_rows_match_exact_normalized_source_borrower_"
                    "name_investment_type_maturity_and_reference_rate_category_"
                    "across_recent_filings_but_the_signature_is_not_a_stable_"
                    "legal_entity_or_loan_identifier_and_does_not_supply_"
                    "repayment_schedules_borrower_cashflow_effects_or_real_"
                    "activity_mapping"
                ),
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return rows


def _sec_bdc_investment_signature_continuity_snapshot(
    *,
    registry: SourceRegistry,
    terms_status_time_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[SEC_BDC_INVESTMENT_SIGNATURE_CONTINUITY_SERIES_ID]
    records = _sec_bdc_investment_signature_continuity_records(
        terms_status_time_snapshot.records
    )
    if not records:
        raise ValueError("SEC BDC investment-signature continuity records are empty")
    records_hash = _records_sha256(records)
    first_date = min(record["first_observation_date"] for record in records)
    latest_date = max(record["latest_observation_date"] for record in records)
    first_report_date = min(record["first_report_date"] for record in records)
    latest_report_date = max(record["latest_report_date"] for record in records)
    source_row_count = sum(int(record["source_row_count"]) for record in records)
    signatures_with_four_report_dates = sum(
        int(record["report_date_count"]) >= 4 for record in records
    )
    note = (
        "sec_edgar_bdc_investment_signature_continuity_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"underlying_terms_status_source_row_count={source_row_count};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"first_report_date={first_report_date};"
        f"latest_report_date={latest_report_date};"
        f"public_investment_signature_continuity_rows={len(records)};"
        f"signatures_with_four_report_dates={signatures_with_four_report_dates};"
        "signature_fields=ticker,normalized_source_borrower_name,"
        "normalized_investment_type,normalized_maturity_date,"
        "reference_rate_category;"
        "derived_from_series_id="
        f"{terms_status_time_snapshot.metadata.series_id};"
        "public_investment_signature_continuity_context_available=true;"
        "stable_public_borrower_identifier_available=false;"
        "public_reusable_loan_identifier_available=false;"
        "public_reusable_repayment_schedule_panel_available=false;"
        "borrower_cashflow_pass_through_available=false;"
        "monetary_pass_through_design_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind=(
                "derived_sec_edgar_bdc_investment_signature_continuity_context"
            ),
            note=note,
        ),
        records=records,
    )


def _sec_bdc_bool_changed(records: Sequence[Mapping[str, str]], field: str) -> bool:
    values = {
        str(record.get(field, "")).strip().lower()
        for record in records
        if str(record.get(field, "")).strip()
    }
    return len(values) > 1


def _sec_bdc_numeric_values(
    records: Sequence[Mapping[str, str]], field: str
) -> list[float]:
    values: list[float] = []
    for record in records:
        parsed = _sec_bdc_number(str(record.get(field, "")))
        if parsed is not None:
            values.append(parsed)
    return values


def _sec_bdc_numeric_changed(records: Sequence[Mapping[str, str]], field: str) -> bool:
    values = _sec_bdc_numeric_values(records, field)
    if len(values) < 2:
        return False
    return max(values) != min(values)


def _sec_bdc_recurring_investment_value_status_records(
    records: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    signature_rows = _sec_bdc_investment_signature_continuity_records(records)
    grouped: dict[str, list[Mapping[str, str]]] = {}
    for record in records:
        ticker = str(record.get("ticker", "")).strip()
        borrower_name = str(record.get("borrower_or_issuer_name", "")).strip()
        normalized_name = _sec_bdc_normalized_borrower_name(borrower_name)
        investment_type = _sec_bdc_normalized_signature_part(
            str(record.get("investment_type", ""))
        )
        maturity_date = _sec_bdc_normalized_signature_part(
            str(record.get("maturity_date", ""))
        )
        reference_rate_category = _sec_bdc_reference_rate_category(record)
        if not all((ticker, normalized_name, investment_type, maturity_date)):
            continue
        if reference_rate_category in {
            "missing_reference_rate",
            "other_source_reference_rate",
        }:
            continue
        signature_key = "::".join(
            (
                ticker,
                normalized_name,
                investment_type,
                maturity_date,
                reference_rate_category,
            )
        )
        grouped.setdefault(signature_key, []).append(record)

    rows: list[dict[str, str]] = []
    for signature in signature_rows:
        signature_key = signature["public_investment_signature_key"]
        group_records = grouped.get(signature_key, [])
        if not group_records:
            continue
        report_dates = sorted(
            {
                str(record.get("report_date", "")).strip()
                for record in group_records
                if str(record.get("report_date", "")).strip()
            }
        )
        observation_dates = sorted(
            {
                str(record.get("date", "")).strip()
                for record in group_records
                if str(record.get("date", "")).strip()
            }
        )
        principal_values = _sec_bdc_numeric_values(
            group_records, "principal_or_par_value"
        )
        fair_values = _sec_bdc_numeric_values(group_records, "fair_value")
        cost_values = _sec_bdc_numeric_values(group_records, "amortized_cost")
        principal_changed = _sec_bdc_numeric_changed(
            group_records, "principal_or_par_value"
        )
        fair_value_changed = _sec_bdc_numeric_changed(group_records, "fair_value")
        cost_changed = _sec_bdc_numeric_changed(group_records, "amortized_cost")
        non_accrual_changed = _sec_bdc_bool_changed(
            group_records, "non_accrual_status_marker"
        )
        pik_changed = _sec_bdc_bool_changed(group_records, "pik_status_marker")
        below_par_changed = _sec_bdc_bool_changed(
            group_records, "fair_value_less_than_principal_or_par_marker"
        )
        value_or_status_variation = any(
            (
                principal_changed,
                fair_value_changed,
                cost_changed,
                non_accrual_changed,
                pik_changed,
                below_par_changed,
            )
        )
        row = {
            "date": observation_dates[-1],
            "ticker": signature["ticker"],
            "public_investment_signature_key": signature_key,
            "normalized_source_borrower_name": signature[
                "normalized_source_borrower_name"
            ],
            "normalized_investment_type": signature["normalized_investment_type"],
            "normalized_maturity_date": signature["normalized_maturity_date"],
            "reference_rate_category": signature["reference_rate_category"],
            "source_row_count": signature["source_row_count"],
            "report_date_count": signature["report_date_count"],
            "first_report_date": report_dates[0],
            "latest_report_date": report_dates[-1],
            "first_observation_date": observation_dates[0],
            "latest_observation_date": observation_dates[-1],
            "principal_or_par_observation_count": str(len(principal_values)),
            "fair_value_observation_count": str(len(fair_values)),
            "amortized_cost_observation_count": str(len(cost_values)),
            "principal_or_par_changed_across_reports": str(principal_changed).lower(),
            "fair_value_changed_across_reports": str(fair_value_changed).lower(),
            "amortized_cost_changed_across_reports": str(cost_changed).lower(),
            "non_accrual_marker_seen": str(
                any(
                    record.get("non_accrual_status_marker") == "true"
                    for record in group_records
                )
            ).lower(),
            "non_accrual_marker_changed_across_reports": str(
                non_accrual_changed
            ).lower(),
            "pik_marker_seen": str(
                any(
                    record.get("pik_status_marker") == "true"
                    for record in group_records
                )
            ).lower(),
            "pik_marker_changed_across_reports": str(pik_changed).lower(),
            "fair_value_below_par_seen": str(
                any(
                    record.get("fair_value_less_than_principal_or_par_marker") == "true"
                    for record in group_records
                )
            ).lower(),
            "fair_value_below_par_changed_across_reports": str(
                below_par_changed
            ).lower(),
            "public_recurring_investment_value_status_context_available": "true",
            "value_or_status_variation_context_available": str(
                value_or_status_variation
            ).lower(),
            "stable_public_borrower_identifier_available": "false",
            "public_reusable_loan_identifier_available": "false",
            "public_reusable_repayment_schedule_panel_available": "false",
            "borrower_cashflow_pass_through_available": "false",
            "monetary_pass_through_design_available": "false",
            "nonbank_to_real_activity_context_available": "false",
            "row_support_status": (
                "public_recurring_investment_value_status_context_fail_closed"
            ),
            "method_blocker": (
                "public_bdc_recurring_investment_signatures_show_filing_table_"
                "principal_par_fair_value_cost_or_status_marker_variation_"
                "where_available_but_they_are_not_repayment_schedules_stable_"
                "legal_entity_or_loan_identifiers_borrower_cashflow_evidence_"
                "monetary_pass_through_designs_or_nonbank_real_activity_bridges"
            ),
            "denominator_prior_narrowing_allowed": "false",
            "split_denominator_promotion_allowed": "false",
            "formula_replacement_allowed": "false",
            "main_ratio_admission_allowed": "false",
            "incidence_output_enabled": "false",
            "welfare_tax_mpc_output_enabled": "false",
            "policy_failure_output_enabled": "false",
            "pricing_output_enabled": "false",
        }
        rows.append(row)
    return rows


def _sec_bdc_recurring_investment_value_status_snapshot(
    *,
    registry: SourceRegistry,
    terms_status_time_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[SEC_BDC_RECURRING_INVESTMENT_VALUE_STATUS_SERIES_ID]
    records = _sec_bdc_recurring_investment_value_status_records(
        terms_status_time_snapshot.records
    )
    if not records:
        raise ValueError("SEC BDC recurring investment value/status records are empty")
    records_hash = _records_sha256(records)
    first_date = min(record["first_observation_date"] for record in records)
    latest_date = max(record["latest_observation_date"] for record in records)
    first_report_date = min(record["first_report_date"] for record in records)
    latest_report_date = max(record["latest_report_date"] for record in records)
    source_row_count = sum(int(record["source_row_count"]) for record in records)
    principal_changed_rows = sum(
        record["principal_or_par_changed_across_reports"] == "true"
        for record in records
    )
    fair_value_changed_rows = sum(
        record["fair_value_changed_across_reports"] == "true" for record in records
    )
    status_changed_rows = sum(
        record["non_accrual_marker_changed_across_reports"] == "true"
        or record["pik_marker_changed_across_reports"] == "true"
        or record["fair_value_below_par_changed_across_reports"] == "true"
        for record in records
    )
    variation_context_rows = sum(
        record["value_or_status_variation_context_available"] == "true"
        for record in records
    )
    note = (
        "sec_edgar_bdc_recurring_investment_value_status_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"underlying_terms_status_source_row_count={source_row_count};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"first_report_date={first_report_date};"
        f"latest_report_date={latest_report_date};"
        f"principal_or_par_changed_rows={principal_changed_rows};"
        f"fair_value_changed_rows={fair_value_changed_rows};"
        f"status_marker_changed_rows={status_changed_rows};"
        f"value_or_status_variation_context_rows={variation_context_rows};"
        "derived_from_series_id="
        f"{terms_status_time_snapshot.metadata.series_id};"
        "public_recurring_investment_value_status_context_available=true;"
        "stable_public_borrower_identifier_available=false;"
        "public_reusable_loan_identifier_available=false;"
        "public_reusable_repayment_schedule_panel_available=false;"
        "borrower_cashflow_pass_through_available=false;"
        "monetary_pass_through_design_available=false;"
        "nonbank_to_real_activity_context_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind=(
                "derived_sec_edgar_bdc_recurring_investment_value_status_context"
            ),
            note=note,
        ),
        records=records,
    )


def _sec_archive_base_url(*, cik: str, accession_number: str) -> str:
    return (
        "https://www.sec.gov/Archives/edgar/data/"
        f"{int(cik)}/{accession_number.replace('-', '')}/"
    )


def _xml_local_name(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _xml_child_text(node: ET.Element, tag: str) -> str:
    for child in node:
        if _xml_local_name(child.tag) == tag:
            return (child.text or "").strip()
    return ""


def _sec_abs_ee_bool(value: str) -> str:
    return str(value.strip().lower() == "true").lower()


def _sec_abs_ee_number(value: str) -> float | None:
    cleaned = _clean_published_number(value)
    if not cleaned:
        return None
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = cleaned.strip("() ")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", cleaned):
        return None
    parsed = float(cleaned)
    return -parsed if negative else parsed


def _sec_abs_ee_recent_cmbs_filings(
    submissions: Mapping[str, object],
    *,
    trust_name: str,
    cik: str,
    max_filings: int,
) -> list[dict[str, str]]:
    recent = submissions["filings"]["recent"]  # type: ignore[index]
    rows: list[dict[str, str]] = []
    for index, form in enumerate(recent["form"]):  # type: ignore[index]
        if form != "ABS-EE":
            continue
        accession = recent["accessionNumber"][index]  # type: ignore[index]
        rows.append(
            {
                "trust_name": trust_name,
                "cik": cik,
                "accession_number": accession,
                "filing_date": recent["filingDate"][index],  # type: ignore[index]
                "period_of_report": (
                    recent["reportDate"][index]  # type: ignore[index]
                    or recent["filingDate"][index]  # type: ignore[index]
                ),
                "primary_document": recent["primaryDocument"][index],  # type: ignore[index]
            }
        )
        if len(rows) >= max_filings:
            break
    return rows


def _sec_abs_ee_xml_document_for_filing(
    *, filing: Mapping[str, str], source_dir: Path
) -> tuple[str, str]:
    accession = filing["accession_number"]
    cik = filing["cik"]
    index_url = (
        f"{_sec_archive_base_url(cik=cik, accession_number=accession)}index.json"
    )
    index_path = source_dir / f"CIK{cik}_{accession.replace('-', '')}_index.json"
    if not index_path.exists():
        _download_source(index_url, index_path)
    index_json = index_path.read_text(encoding="utf-8", errors="replace")
    data = json.loads(index_json)
    names = [
        str(item.get("name", "")) for item in data.get("directory", {}).get("item", [])
    ]
    for preferred in ("exh_102.xml", "ex102.xml"):
        if preferred in names:
            return preferred, hashlib.sha256(index_json.encode("utf-8")).hexdigest()
    xml_names = [
        name
        for name in names
        if name.lower().endswith(".xml") and "103" not in name.lower()
    ]
    if not xml_names:
        raise ValueError(f"No Exhibit 102 XML document found for {accession}")
    return sorted(xml_names)[0], hashlib.sha256(index_json.encode("utf-8")).hexdigest()


def _sec_abs_ee_cmbs_asset_property_records(
    *, filing: Mapping[str, str], source_xml: str
) -> list[dict[str, str]]:
    root = ET.fromstring(source_xml.encode("utf-8"))
    if _xml_local_name(root.tag) != "assetData":
        raise ValueError("SEC ABS-EE CMBS payload root is not assetData")
    assets = [node for node in root if _xml_local_name(node.tag) == "assets"]
    if not assets:
        raise ValueError("SEC ABS-EE CMBS payload has no assets nodes")

    accession = filing["accession_number"]
    cik = filing["cik"]
    filing_base_url = _sec_archive_base_url(cik=cik, accession_number=accession)
    xml_url = f"{filing_base_url}{filing['xml_document']}"
    records: list[dict[str, str]] = []
    for asset_index, asset in enumerate(assets, start=1):
        asset_fields = {
            key: _xml_child_text(asset, key)
            for key in (
                "assetTypeNumber",
                "assetNumber",
                "GroupID",
                "reportingPeriodBeginningDate",
                "reportingPeriodEndDate",
                "originatorName",
                "originationDate",
                "originalLoanAmount",
                "originalTermLoanNumber",
                "maturityDate",
                "originalInterestRatePercentage",
                "interestRateSecuritizationPercentage",
                "originalInterestRateTypeCode",
                "interestOnlyIndicator",
                "balloonIndicator",
                "modifiedIndicator",
                "scheduledPrincipalBalanceSecuritizationAmount",
                "reportPeriodBeginningScheduleLoanBalanceAmount",
                "totalScheduledPrincipalInterestDueAmount",
                "reportPeriodInterestRatePercentage",
                "scheduledInterestAmount",
                "scheduledPrincipalAmount",
                "otherPrincipalAdjustmentAmount",
                "reportPeriodEndActualBalanceAmount",
                "reportPeriodEndScheduledLoanBalanceAmount",
                "paidThroughDate",
                "paymentStatusLoanCode",
                "primaryServicerName",
                "nonRecoverabilityIndicator",
                "totalPrincipalInterestAdvancedOutstandingAmount",
                "totalTaxesInsuranceAdvancesOutstandingAmount",
                "otherExpensesAdvancedOutstandingAmount",
                "prepaymentPremiumYieldMaintenanceReceivedAmount",
            )
        }
        properties = [
            node for node in asset if _xml_local_name(node.tag) == "property"
        ] or [ET.Element("property")]
        for property_index, property_node in enumerate(properties, start=1):
            property_fields = {
                key: _xml_child_text(property_node, key)
                for key in (
                    "propertyName",
                    "propertyCity",
                    "propertyState",
                    "propertyZip",
                    "propertyCounty",
                    "propertyTypeCode",
                    "unitsBedsRoomsNumber",
                    "netRentableSquareFeetNumber",
                    "valuationSecuritizationAmount",
                    "valuationSecuritizationDate",
                    "mostRecentValuationAmount",
                    "mostRecentValuationDate",
                    "physicalOccupancySecuritizationPercentage",
                    "mostRecentPhysicalOccupancyPercentage",
                    "propertyStatusCode",
                    "mostRecentSpecialServicerTransferDate",
                    "workoutStrategyCode",
                    "financialsSecuritizationDate",
                    "mostRecentFinancialsStartDate",
                    "mostRecentFinancialsEndDate",
                    "revenueSecuritizationAmount",
                    "mostRecentRevenueAmount",
                    "operatingExpensesSecuritizationAmount",
                    "operatingExpensesAmount",
                    "netOperatingIncomeSecuritizationAmount",
                    "mostRecentNetOperatingIncomeAmount",
                    "netCashFlowFlowSecuritizationAmount",
                    "mostRecentNetCashFlowAmount",
                    "mostRecentDebtServiceAmount",
                    "debtServiceCoverageNetOperatingIncomeSecuritizationPercentage",
                    "mostRecentDebtServiceCoverageNetOperatingIncomePercentage",
                    "debtServiceCoverageNetCashFlowSecuritizationPercentage",
                    "mostRecentDebtServiceCoverageNetCashFlowpercentage",
                    "debtServiceCoverageSecuritizationCode",
                    "mostRecentDebtServiceCoverageCode",
                )
            }
            report_end = _sec_abs_ee_date(
                asset_fields["reportingPeriodEndDate"] or filing["period_of_report"]
            )
            dscr_available = any(
                property_fields[field]
                for field in (
                    "debtServiceCoverageNetOperatingIncomeSecuritizationPercentage",
                    "mostRecentDebtServiceCoverageNetOperatingIncomePercentage",
                    "debtServiceCoverageNetCashFlowSecuritizationPercentage",
                    "mostRecentDebtServiceCoverageNetCashFlowpercentage",
                )
            )
            noi_available = any(
                property_fields[field]
                for field in (
                    "netOperatingIncomeSecuritizationAmount",
                    "mostRecentNetOperatingIncomeAmount",
                    "netCashFlowFlowSecuritizationAmount",
                    "mostRecentNetCashFlowAmount",
                )
            )
            occupancy_available = any(
                property_fields[field]
                for field in (
                    "physicalOccupancySecuritizationPercentage",
                    "mostRecentPhysicalOccupancyPercentage",
                )
            )
            payment_status_available = bool(
                asset_fields["paymentStatusLoanCode"] or asset_fields["paidThroughDate"]
            )
            full_support = (
                dscr_available
                and noi_available
                and occupancy_available
                and payment_status_available
                and bool(asset_fields["maturityDate"])
            )
            records.append(
                {
                    "date": report_end,
                    "filing_date": filing["filing_date"],
                    "period_of_report": filing["period_of_report"],
                    "trust_name": filing["trust_name"],
                    "cik": cik,
                    "accession_number": accession,
                    "asset_xml_url": xml_url,
                    "asset_index": str(asset_index),
                    "property_index": str(property_index),
                    **asset_fields,
                    **property_fields,
                    "source_schema_reviewed": "true",
                    "source_asset_class": "cmbs_abs_ee_asset_data",
                    "amount_unit": "source_abs_ee_asset_data_units",
                    "public_reusable_asset_level_cre_panel_available": "true",
                    "cre_public_loan_property_level_panel_available": "true",
                    "cre_dscr_context_available": str(dscr_available).lower(),
                    "cre_noi_context_available": str(noi_available).lower(),
                    "cre_occupancy_context_available": str(occupancy_available).lower(),
                    "cre_payment_status_context_available": str(
                        payment_status_available
                    ).lower(),
                    "cre_refinancing_outcome_available": "false",
                    "cre_real_activity_mapping_available": "false",
                    "modified_asset_marker": _sec_abs_ee_bool(
                        asset_fields["modifiedIndicator"]
                    ),
                    "special_servicer_or_workout_marker": str(
                        bool(
                            property_fields["mostRecentSpecialServicerTransferDate"]
                            or property_fields["workoutStrategyCode"]
                        )
                    ).lower(),
                    "row_support_status": (
                        "public_asset_property_dscr_noi_payment_context"
                        if full_support
                        else "partial_asset_property_context_fail_closed"
                    ),
                    "missing_cell_blocker": ";".join(
                        blocker
                        for blocker, missing in (
                            ("missing_dscr_field", not dscr_available),
                            ("missing_noi_or_ncf_field", not noi_available),
                            ("missing_occupancy_field", not occupancy_available),
                            (
                                "missing_payment_status_or_paid_through_field",
                                not payment_status_available,
                            ),
                            ("missing_maturity_date", not asset_fields["maturityDate"]),
                        )
                        if missing
                    ),
                    "method_blocker": (
                        "public_sec_abs_ee_cmbs_asset_level_dscr_noi_payment_"
                        "context_is_admitted_but_no_refinancing_outcome_panel_"
                        "representativeness_design_or_real_activity_bridge_is_"
                        "admitted"
                    ),
                    "denominator_prior_narrowing_allowed": "false",
                    "split_denominator_promotion_allowed": "false",
                    "formula_replacement_allowed": "false",
                    "main_ratio_admission_allowed": "false",
                    "incidence_output_enabled": "false",
                    "welfare_tax_mpc_output_enabled": "false",
                    "policy_failure_output_enabled": "false",
                    "pricing_output_enabled": "false",
                }
            )
    return records


def _sec_abs_ee_date_sort_key(value: str) -> str:
    parsed = _sec_abs_ee_date(value)
    return parsed if parsed else "0000-00-00"


def _sec_abs_ee_changed(records: Sequence[Mapping[str, str]], field: str) -> bool:
    values = {
        str(record.get(field, "")).strip()
        for record in records
        if str(record.get(field, "")).strip()
    }
    return len(values) > 1


def _sec_abs_ee_numeric_changed(
    records: Sequence[Mapping[str, str]], field: str
) -> bool:
    values = [
        parsed
        for record in records
        if (parsed := _sec_abs_ee_number(str(record.get(field, "")))) is not None
    ]
    return len(values) >= 2 and max(values) != min(values)


def _sec_abs_ee_cmbs_time_dimension_records(
    records: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    grouped: dict[tuple[str, str, str], list[Mapping[str, str]]] = {}
    for record in records:
        cik = str(record.get("cik", "")).strip()
        asset_number = str(record.get("assetNumber", "")).strip()
        property_index = str(record.get("property_index", "")).strip()
        if not cik or not asset_number:
            continue
        grouped.setdefault((cik, asset_number, property_index), []).append(record)

    rows: list[dict[str, str]] = []
    for (cik, asset_number, property_index), group_records in sorted(grouped.items()):
        report_dates = sorted(
            {
                _sec_abs_ee_date_sort_key(str(record.get("date", "")))
                for record in group_records
                if str(record.get("date", "")).strip()
            }
        )
        if len(report_dates) < 2:
            continue
        actual_balance_changed = _sec_abs_ee_numeric_changed(
            group_records, "reportPeriodEndActualBalanceAmount"
        )
        scheduled_balance_changed = _sec_abs_ee_numeric_changed(
            group_records, "reportPeriodEndScheduledLoanBalanceAmount"
        )
        payment_status_changed = _sec_abs_ee_changed(
            group_records, "paymentStatusLoanCode"
        )
        paid_through_changed = _sec_abs_ee_changed(group_records, "paidThroughDate")
        dscr_changed = any(
            _sec_abs_ee_numeric_changed(group_records, field)
            for field in (
                "mostRecentDebtServiceCoverageNetOperatingIncomePercentage",
                "mostRecentDebtServiceCoverageNetCashFlowpercentage",
            )
        )
        occupancy_changed = _sec_abs_ee_numeric_changed(
            group_records, "mostRecentPhysicalOccupancyPercentage"
        )
        trust_name = str(group_records[0].get("trust_name", "")).strip()
        time_key = f"{cik}::{asset_number}::{property_index}"
        for record in sorted(
            group_records,
            key=lambda row: (
                _sec_abs_ee_date_sort_key(str(row.get("date", ""))),
                str(row.get("accession_number", "")),
            ),
        ):
            enriched = dict(record)
            blockers = [
                blocker
                for blocker in (
                    enriched.get("missing_cell_blocker", ""),
                    "no_representativeness_design_for_reviewed_cmbs_trusts",
                    "no_refinancing_outcome_panel",
                    "no_real_activity_bridge",
                )
                if blocker
            ]
            enriched.update(
                {
                    "asset_time_dimension_key": time_key,
                    "public_trust_asset_number_key": f"{cik}::{asset_number}",
                    "asset_report_period_count": str(len(report_dates)),
                    "asset_first_report_period": report_dates[0],
                    "asset_latest_report_period": report_dates[-1],
                    "public_reusable_trust_asset_number_available": "true",
                    "public_asset_time_dimension_context_available": "true",
                    "actual_balance_variation_context_available": str(
                        actual_balance_changed
                    ).lower(),
                    "scheduled_balance_variation_context_available": str(
                        scheduled_balance_changed
                    ).lower(),
                    "payment_status_variation_context_available": str(
                        payment_status_changed
                    ).lower(),
                    "paid_through_variation_context_available": str(
                        paid_through_changed
                    ).lower(),
                    "dscr_variation_context_available": str(dscr_changed).lower(),
                    "occupancy_variation_context_available": str(
                        occupancy_changed
                    ).lower(),
                    "modified_asset_marker_seen": str(
                        any(
                            item.get("modified_asset_marker") == "true"
                            for item in group_records
                        )
                    ).lower(),
                    "special_servicer_or_workout_marker_seen": str(
                        any(
                            item.get("special_servicer_or_workout_marker") == "true"
                            for item in group_records
                        )
                    ).lower(),
                    "public_representativeness_design_available": "false",
                    "cre_refinancing_outcome_available": "false",
                    "cre_real_activity_mapping_available": "false",
                    "row_support_status": (
                        "public_asset_property_time_dimension_context_fail_closed"
                    ),
                    "missing_cell_blocker": ";".join(blockers),
                    "method_blocker": (
                        "public_sec_abs_ee_cmbs_asset_time_dimension_context_"
                        "is_admitted_for_reviewed_trusts_but_no_"
                        "representativeness_design_refinancing_outcome_panel_"
                        "or_real_activity_bridge_is_admitted"
                    ),
                    "denominator_prior_narrowing_allowed": "false",
                    "split_denominator_promotion_allowed": "false",
                    "formula_replacement_allowed": "false",
                    "main_ratio_admission_allowed": "false",
                    "incidence_output_enabled": "false",
                    "welfare_tax_mpc_output_enabled": "false",
                    "policy_failure_output_enabled": "false",
                    "pricing_output_enabled": "false",
                }
            )
            if trust_name:
                enriched["trust_name"] = trust_name
            rows.append(enriched)
    return rows


def _sec_abs_ee_cmbs_asset_level_snapshot(
    *, registry: SourceRegistry, source_dir: Path
) -> SourceSnapshot:
    series = registry.series[SEC_ABS_EE_CMBS_ASSET_LEVEL_SERIES_ID]
    source_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    xml_hashes: dict[str, str] = {}
    per_filing_counts: dict[str, int] = {}
    asset_counts: dict[str, int] = {}
    for filing in SEC_ABS_EE_CMBS_REVIEWED_FILINGS:
        accession = filing["accession_number"]
        cik = filing["cik"]
        xml_url = (
            f"{_sec_archive_base_url(cik=cik, accession_number=accession)}"
            f"{filing['xml_document']}"
        )
        xml_path = (
            source_dir
            / f"CIK{cik}_{accession.replace('-', '')}_{filing['xml_document']}"
        )
        if not xml_path.exists():
            _download_source(xml_url, xml_path)
        source_xml = xml_path.read_text(encoding="utf-8", errors="replace")
        filing_records = _sec_abs_ee_cmbs_asset_property_records(
            filing=filing,
            source_xml=source_xml,
        )
        records.extend(filing_records)
        per_filing_counts[accession] = len(filing_records)
        asset_counts[accession] = len(
            {record["assetNumber"] for record in filing_records}
        )
        xml_hashes[accession] = hashlib.sha256(source_xml.encode("utf-8")).hexdigest()

    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    dscr_rows = sum(
        record["cre_dscr_context_available"] == "true" for record in records
    )
    noi_rows = sum(record["cre_noi_context_available"] == "true" for record in records)
    occupancy_rows = sum(
        record["cre_occupancy_context_available"] == "true" for record in records
    )
    payment_status_rows = sum(
        record["cre_payment_status_context_available"] == "true" for record in records
    )
    modified_rows = sum(record["modified_asset_marker"] == "true" for record in records)
    special_servicer_rows = sum(
        record["special_servicer_or_workout_marker"] == "true" for record in records
    )
    full_support_rows = sum(
        record["row_support_status"] == "public_asset_property_dscr_noi_payment_context"
        for record in records
    )
    note = (
        "sec_abs_ee_cmbs_asset_level_performance_panel;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"reviewed_filing_count={len(SEC_ABS_EE_CMBS_REVIEWED_FILINGS)};"
        f"reviewed_asset_count={sum(asset_counts.values())};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "per_filing_property_row_count="
        f"{','.join(f'{accession}:{count}' for accession, count in per_filing_counts.items())};"
        "per_filing_asset_count="
        f"{','.join(f'{accession}:{count}' for accession, count in asset_counts.items())};"
        f"dscr_context_rows={dscr_rows};"
        f"noi_or_ncf_context_rows={noi_rows};"
        f"occupancy_context_rows={occupancy_rows};"
        f"payment_status_context_rows={payment_status_rows};"
        f"modified_asset_marker_rows={modified_rows};"
        f"special_servicer_or_workout_marker_rows={special_servicer_rows};"
        f"full_support_rows={full_support_rows};"
        "source_xml_sha256_summary="
        f"{','.join(f'{accession}:{value}' for accession, value in xml_hashes.items())};"
        "public_reusable_asset_level_cre_panel_available=true;"
        "cre_dscr_context_available=true;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="live_sec_abs_ee_cmbs_asset_level_performance_panel",
            note=note,
        ),
        records=records,
    )


def _sec_abs_ee_cmbs_time_dimension_snapshot(
    *, registry: SourceRegistry, source_dir: Path
) -> SourceSnapshot:
    series = registry.series[SEC_ABS_EE_CMBS_TIME_DIMENSION_SERIES_ID]
    source_dir.mkdir(parents=True, exist_ok=True)
    base_records: list[dict[str, str]] = []
    xml_hashes: dict[str, str] = {}
    index_hashes: dict[str, str] = {}
    submissions_hashes: dict[str, str] = {}
    per_trust_filing_counts: dict[str, int] = {}
    for reviewed in SEC_ABS_EE_CMBS_REVIEWED_FILINGS:
        cik = reviewed["cik"]
        trust_name = reviewed["trust_name"]
        submissions_path = source_dir / f"CIK{cik}_submissions.json"
        submissions_url = f"https://data.sec.gov/submissions/CIK{int(cik):010d}.json"
        if not submissions_path.exists():
            _download_source(submissions_url, submissions_path)
        submissions_json = submissions_path.read_text(
            encoding="utf-8", errors="replace"
        )
        submissions_hashes[cik] = hashlib.sha256(
            submissions_json.encode("utf-8")
        ).hexdigest()
        submissions = json.loads(submissions_json)
        filings = _sec_abs_ee_recent_cmbs_filings(
            submissions, trust_name=trust_name, cik=cik, max_filings=4
        )
        per_trust_filing_counts[trust_name] = len(filings)
        for filing in filings:
            xml_document, index_hash = _sec_abs_ee_xml_document_for_filing(
                filing=filing, source_dir=source_dir
            )
            filing = {**filing, "xml_document": xml_document}
            accession = filing["accession_number"]
            xml_url = (
                f"{_sec_archive_base_url(cik=cik, accession_number=accession)}"
                f"{xml_document}"
            )
            xml_path = source_dir / (
                f"CIK{cik}_{accession.replace('-', '')}_{xml_document}"
            )
            if not xml_path.exists():
                _download_source(xml_url, xml_path)
            source_xml = xml_path.read_text(encoding="utf-8", errors="replace")
            xml_hashes[accession] = hashlib.sha256(
                source_xml.encode("utf-8")
            ).hexdigest()
            index_hashes[accession] = index_hash
            base_records.extend(
                _sec_abs_ee_cmbs_asset_property_records(
                    filing=filing,
                    source_xml=source_xml,
                )
            )

    records = _sec_abs_ee_cmbs_time_dimension_records(base_records)
    if not records:
        raise ValueError("SEC ABS-EE CMBS time-dimension records are empty")
    records_hash = _records_sha256(records)
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    filing_count = len({record["accession_number"] for record in records})
    asset_time_key_count = len(
        {record["asset_time_dimension_key"] for record in records}
    )
    assets_with_four_periods = len(
        {
            record["asset_time_dimension_key"]
            for record in records
            if int(record["asset_report_period_count"]) >= 4
        }
    )
    actual_balance_variation_rows = sum(
        record["actual_balance_variation_context_available"] == "true"
        for record in records
    )
    payment_status_variation_rows = sum(
        record["payment_status_variation_context_available"] == "true"
        for record in records
    )
    paid_through_variation_rows = sum(
        record["paid_through_variation_context_available"] == "true"
        for record in records
    )
    dscr_variation_rows = sum(
        record["dscr_variation_context_available"] == "true" for record in records
    )
    note = (
        "sec_abs_ee_cmbs_asset_time_dimension_panel;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"reviewed_trust_count={len(SEC_ABS_EE_CMBS_REVIEWED_FILINGS)};"
        f"reviewed_abs_ee_filing_count={filing_count};"
        f"asset_time_key_count={asset_time_key_count};"
        f"assets_with_four_report_periods={assets_with_four_periods};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "per_trust_abs_ee_filing_count="
        f"{','.join(f'{trust}:{count}' for trust, count in per_trust_filing_counts.items())};"
        f"actual_balance_variation_rows={actual_balance_variation_rows};"
        f"payment_status_variation_rows={payment_status_variation_rows};"
        f"paid_through_variation_rows={paid_through_variation_rows};"
        f"dscr_variation_rows={dscr_variation_rows};"
        "source_xml_sha256_summary="
        f"{','.join(f'{accession}:{value}' for accession, value in xml_hashes.items())};"
        "source_index_json_sha256_summary="
        f"{','.join(f'{accession}:{value}' for accession, value in index_hashes.items())};"
        "source_submissions_json_sha256_summary="
        f"{','.join(f'{cik}:{value}' for cik, value in submissions_hashes.items())};"
        "public_asset_time_dimension_context_available=true;"
        "public_reusable_trust_asset_number_available=true;"
        "public_representativeness_design_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="live_sec_abs_ee_cmbs_asset_time_dimension_panel",
            note=note,
        ),
        records=records,
    )


def _sec_abs_ee_index_accession(filename: str) -> str:
    stem = Path(filename).name.removesuffix(".txt")
    if re.fullmatch(r"\d{18}", stem):
        return f"{stem[:10]}-{stem[10:12]}-{stem[12:]}"
    return stem


def _sec_abs_ee_candidate_cmbs_name_match(company_name: str) -> bool:
    normalized = company_name.upper()
    return any(
        token in normalized
        for token in (
            "COMMERCIAL MORTGAGE",
            "CMBS",
            "MORTGAGE TRUST",
            "MORTGAGE SECURITIES",
            "MORTGAGE & ASSET",
            "CFCRE",
            "JPMCC",
            "JPMBB",
            "BBCMS",
            "BMO ",
            "CD 20",
            "CSMC ",
            "WFCM ",
        )
    )


def _sec_abs_ee_recent_index_records(
    *,
    master_index_text: str,
    year: int,
    quarter: int,
    index_url: str,
) -> list[dict[str, str]]:
    reviewed_ciks = {filing["cik"] for filing in SEC_ABS_EE_CMBS_REVIEWED_FILINGS}
    reviewed_accessions = {
        filing["accession_number"] for filing in SEC_ABS_EE_CMBS_REVIEWED_FILINGS
    }
    rows: list[dict[str, str]] = []
    in_table = False
    for line in master_index_text.splitlines():
        if line.startswith("CIK|Company Name|Form Type|Date Filed|Filename"):
            in_table = True
            continue
        if not in_table or "|" not in line:
            continue
        parts = line.split("|")
        if len(parts) != 5:
            continue
        cik, company_name, form_type, filing_date, filename = parts
        if form_type != "ABS-EE":
            continue
        accession = _sec_abs_ee_index_accession(filename)
        candidate_cmbs = _sec_abs_ee_candidate_cmbs_name_match(company_name)
        reviewed_cik = cik in reviewed_ciks
        reviewed_accession = accession in reviewed_accessions
        blockers = [
            "index_frame_does_not_verify_asset_class_without_filing_xml_review",
            "candidate_cmbs_name_match_is_not_cre_market_representativeness_design",
            "no_refinancing_outcome_panel",
            "no_real_activity_bridge",
        ]
        rows.append(
            {
                "date": filing_date,
                "index_year": str(year),
                "index_quarter": f"QTR{quarter}",
                "cik": cik,
                "company_name": company_name,
                "form_type": form_type,
                "filing_date": filing_date,
                "filename": filename,
                "accession_number": accession,
                "filing_url": f"https://www.sec.gov/Archives/{filename}",
                "index_url": index_url,
                "public_abs_ee_filing_index_frame_available": "true",
                "candidate_cmbs_name_match": str(candidate_cmbs).lower(),
                "reviewed_cmbs_trust_cik_marker": str(reviewed_cik).lower(),
                "reviewed_cmbs_accession_marker": str(reviewed_accession).lower(),
                "asset_level_xml_verified": "false",
                "public_representativeness_frame_for_abs_ee_index_available": "true",
                "cre_market_representativeness_design_available": "false",
                "cre_refinancing_outcome_available": "false",
                "cre_real_activity_mapping_available": "false",
                "row_support_status": "public_abs_ee_filing_index_frame_fail_closed",
                "method_blocker": (
                    "sec_master_index_abs_ee_filing_frame_is_admitted_but_"
                    "company_name_candidate_matching_is_not_asset_class_xml_"
                    "verification_or_cre_market_representativeness_design"
                ),
                "missing_cell_blocker": ";".join(blockers),
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return rows


def _sec_abs_ee_recent_filing_index_snapshot(
    *, registry: SourceRegistry, source_dir: Path
) -> SourceSnapshot:
    series = registry.series[SEC_ABS_EE_RECENT_FILING_INDEX_SERIES_ID]
    source_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, str]] = []
    index_hashes: dict[str, str] = {}
    quarter_counts: dict[str, int] = {}
    quarter_candidate_counts: dict[str, int] = {}
    for year, quarter in SEC_ABS_EE_RECENT_INDEX_QUARTERS:
        quarter_label = f"{year}Q{quarter}"
        index_url = (
            f"https://www.sec.gov/Archives/edgar/full-index/{year}/"
            f"QTR{quarter}/master.idx"
        )
        index_path = source_dir / f"sec_master_index_{year}_q{quarter}.idx"
        if not index_path.exists():
            _download_source(index_url, index_path)
        index_text = index_path.read_text(encoding="latin-1", errors="replace")
        index_hashes[quarter_label] = hashlib.sha256(
            index_text.encode("latin-1", errors="replace")
        ).hexdigest()
        quarter_records = _sec_abs_ee_recent_index_records(
            master_index_text=index_text,
            year=year,
            quarter=quarter,
            index_url=index_url,
        )
        records.extend(quarter_records)
        quarter_counts[quarter_label] = len(quarter_records)
        quarter_candidate_counts[quarter_label] = sum(
            row["candidate_cmbs_name_match"] == "true" for row in quarter_records
        )

    if not records:
        raise ValueError("SEC ABS-EE recent filing index records are empty")
    records_hash = _records_sha256(records)
    first_date = min(row["filing_date"] for row in records)
    latest_date = max(row["filing_date"] for row in records)
    candidate_count = sum(row["candidate_cmbs_name_match"] == "true" for row in records)
    reviewed_cik_count = sum(
        row["reviewed_cmbs_trust_cik_marker"] == "true" for row in records
    )
    reviewed_accession_count = sum(
        row["reviewed_cmbs_accession_marker"] == "true" for row in records
    )
    unique_cik_count = len({row["cik"] for row in records})
    note = (
        "sec_abs_ee_recent_filing_index_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"unique_cik_count={unique_cik_count};"
        f"candidate_cmbs_name_match_rows={candidate_count};"
        f"reviewed_cmbs_trust_cik_rows={reviewed_cik_count};"
        f"reviewed_cmbs_accession_rows={reviewed_accession_count};"
        "quarter_abs_ee_row_count="
        f"{','.join(f'{quarter}:{count}' for quarter, count in quarter_counts.items())};"
        "quarter_candidate_cmbs_name_match_count="
        f"{','.join(f'{quarter}:{count}' for quarter, count in quarter_candidate_counts.items())};"
        "source_master_index_sha256_summary="
        f"{','.join(f'{quarter}:{value}' for quarter, value in index_hashes.items())};"
        "public_abs_ee_filing_index_frame_available=true;"
        "candidate_cmbs_name_match_available=true;"
        "public_representativeness_frame_for_abs_ee_index_available=true;"
        "cre_market_representativeness_design_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="live_sec_abs_ee_recent_filing_index_context",
            note=note,
        ),
        records=records,
    )


def _sec_abs_ee_xml_namespace(root_tag: str) -> str:
    if root_tag.startswith("{") and "}" in root_tag:
        return root_tag[1:].split("}", 1)[0]
    return ""


def _sec_abs_ee_xml_verification_candidate_rows(
    records: Sequence[Mapping[str, str]],
    *,
    per_quarter: int = SEC_ABS_EE_XML_VERIFICATION_PER_QUARTER,
) -> list[Mapping[str, str]]:
    grouped: dict[tuple[str, str], list[Mapping[str, str]]] = {}
    for record in records:
        if str(record.get("candidate_cmbs_name_match", "")).lower() != "true":
            continue
        key = (
            str(record.get("index_year", "")).strip(),
            str(record.get("index_quarter", "")).strip(),
        )
        grouped.setdefault(key, []).append(record)

    selected: list[Mapping[str, str]] = []
    for key in sorted(grouped):
        selected.extend(
            sorted(
                grouped[key],
                key=lambda row: (
                    str(row.get("filing_date", "")),
                    str(row.get("cik", "")),
                    str(row.get("accession_number", "")),
                ),
            )[:per_quarter]
        )
    return selected


def _sec_abs_ee_xml_payload_verification_fields(source_xml: str) -> dict[str, str]:
    root = ET.fromstring(source_xml.encode("utf-8"))
    root_local_name = _xml_local_name(root.tag)
    namespace = _sec_abs_ee_xml_namespace(root.tag)
    asset_node_count = sum(1 for node in root if _xml_local_name(node.tag) == "assets")
    asset_data_verified = root_local_name == "assetData" and asset_node_count > 0
    cmbs_namespace_verified = "cmbs" in namespace.lower()
    return {
        "xml_root_local_name": root_local_name,
        "xml_namespace": namespace,
        "asset_node_count": str(asset_node_count),
        "asset_data_xml_verified": str(asset_data_verified).lower(),
        "cmbs_asset_xml_verified": str(
            asset_data_verified and cmbs_namespace_verified
        ).lower(),
    }


def _sec_abs_ee_candidate_cmbs_xml_verification_records(
    *, index_records: Sequence[Mapping[str, str]], source_dir: Path
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for record in _sec_abs_ee_xml_verification_candidate_rows(index_records):
        accession = str(record.get("accession_number", "")).strip()
        cik = str(record.get("cik", "")).strip()
        filing_base_url = _sec_archive_base_url(cik=cik, accession_number=accession)
        filing = {
            "trust_name": str(record.get("company_name", "")).strip(),
            "cik": cik,
            "accession_number": accession,
            "filing_date": str(record.get("filing_date", "")).strip(),
            "period_of_report": str(record.get("filing_date", "")).strip(),
        }
        xml_document = ""
        source_index_json_sha256 = ""
        source_xml_sha256 = ""
        xml_fields = {
            "xml_root_local_name": "",
            "xml_namespace": "",
            "asset_node_count": "0",
            "asset_data_xml_verified": "false",
            "cmbs_asset_xml_verified": "false",
        }
        xml_error = ""
        try:
            xml_document, source_index_json_sha256 = (
                _sec_abs_ee_xml_document_for_filing(
                    filing=filing,
                    source_dir=source_dir,
                )
            )
            xml_url = f"{filing_base_url}{xml_document}"
            xml_path = (
                source_dir / f"CIK{cik}_{accession.replace('-', '')}_{xml_document}"
            )
            if not xml_path.exists():
                _download_source(xml_url, xml_path)
            source_xml = xml_path.read_text(encoding="utf-8", errors="replace")
            source_xml_sha256 = hashlib.sha256(source_xml.encode("utf-8")).hexdigest()
            xml_fields = _sec_abs_ee_xml_payload_verification_fields(source_xml)
        except Exception as exc:  # noqa: BLE001 - source gate stays fail-closed.
            xml_error = f"{type(exc).__name__}:{exc}"
            xml_url = f"{filing_base_url}{xml_document}" if xml_document else ""

        xml_verified = xml_fields["cmbs_asset_xml_verified"] == "true"
        blockers = [
            "bounded_xml_verification_sample_not_cre_market_representativeness_design",
            "no_refinancing_outcome_panel",
            "no_real_activity_bridge",
        ]
        if xml_error:
            blockers.insert(0, "xml_verification_error")
        rows.append(
            {
                "date": str(record.get("filing_date", "")).strip(),
                "index_year": str(record.get("index_year", "")).strip(),
                "index_quarter": str(record.get("index_quarter", "")).strip(),
                "cik": cik,
                "company_name": str(record.get("company_name", "")).strip(),
                "form_type": str(record.get("form_type", "")).strip(),
                "filing_date": str(record.get("filing_date", "")).strip(),
                "filename": str(record.get("filename", "")).strip(),
                "accession_number": accession,
                "filing_url": str(record.get("filing_url", "")).strip(),
                "filing_index_json_url": f"{filing_base_url}index.json",
                "xml_document": xml_document,
                "xml_url": xml_url,
                "source_index_json_sha256": source_index_json_sha256,
                "source_xml_sha256": source_xml_sha256,
                **xml_fields,
                "candidate_cmbs_name_match": "true",
                "public_abs_ee_filing_index_frame_available": "true",
                "public_xml_verification_context_available": str(
                    bool(source_xml_sha256)
                ).lower(),
                "public_bounded_xml_verification_sample_available": "true",
                "asset_class_xml_verified": xml_fields["asset_data_xml_verified"],
                "cre_market_representativeness_design_available": "false",
                "cre_refinancing_outcome_available": "false",
                "cre_real_activity_mapping_available": "false",
                "row_support_status": (
                    "public_abs_ee_candidate_cmbs_xml_verified_fail_closed"
                    if xml_verified
                    else "public_abs_ee_candidate_xml_verification_blocked_fail_closed"
                ),
                "method_blocker": (
                    "bounded_public_sec_abs_ee_candidate_xml_verification_sample_"
                    "is_admitted_but_not_cre_market_representativeness_design_"
                    "refinancing_outcome_panel_or_real_activity_bridge"
                ),
                "missing_cell_blocker": ";".join(blockers),
                "xml_verification_error": xml_error,
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return rows


def _sec_abs_ee_candidate_cmbs_xml_verification_snapshot(
    *,
    registry: SourceRegistry,
    source_dir: Path,
    filing_index_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[SEC_ABS_EE_CMBS_XML_VERIFICATION_SERIES_ID]
    records = _sec_abs_ee_candidate_cmbs_xml_verification_records(
        index_records=filing_index_snapshot.records,
        source_dir=source_dir,
    )
    if not records:
        raise ValueError("SEC ABS-EE candidate CMBS XML verification records are empty")
    records_hash = _records_sha256(records)
    first_date = min(row["filing_date"] for row in records)
    latest_date = max(row["filing_date"] for row in records)
    asset_data_rows = sum(row["asset_data_xml_verified"] == "true" for row in records)
    cmbs_asset_rows = sum(row["cmbs_asset_xml_verified"] == "true" for row in records)
    xml_context_rows = sum(
        row["public_xml_verification_context_available"] == "true" for row in records
    )
    note = (
        "sec_abs_ee_candidate_cmbs_xml_verification_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"derived_from_series_id={filing_index_snapshot.metadata.series_id};"
        f"candidate_rows_reviewed={len(records)};"
        f"asset_data_xml_verified_rows={asset_data_rows};"
        f"cmbs_asset_xml_verified_rows={cmbs_asset_rows};"
        f"public_xml_verification_context_rows={xml_context_rows};"
        "source_index_json_sha256_summary="
        f"{','.join(sorted({row['source_index_json_sha256'] for row in records if row['source_index_json_sha256']}))};"
        "source_xml_sha256_summary="
        f"{','.join(sorted({row['source_xml_sha256'] for row in records if row['source_xml_sha256']}))};"
        "public_abs_ee_filing_index_frame_available=true;"
        "public_xml_verification_context_available=true;"
        "public_bounded_xml_verification_sample_available=true;"
        "cre_market_representativeness_design_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind="live_sec_abs_ee_candidate_cmbs_xml_verification_context",
            note=note,
        ),
        records=records,
    )


def _sec_abs_ee_cmbs_representativeness_design_records(
    *,
    filing_index_records: Sequence[Mapping[str, str]],
    xml_verification_records: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    index_groups: dict[tuple[str, str], list[Mapping[str, str]]] = {}
    xml_groups: dict[tuple[str, str], list[Mapping[str, str]]] = {}
    for record in filing_index_records:
        key = (
            str(record.get("index_year", "")).strip(),
            str(record.get("index_quarter", "")).strip(),
        )
        index_groups.setdefault(key, []).append(record)
    for record in xml_verification_records:
        key = (
            str(record.get("index_year", "")).strip(),
            str(record.get("index_quarter", "")).strip(),
        )
        xml_groups.setdefault(key, []).append(record)

    rows: list[dict[str, str]] = []
    for key in sorted(index_groups):
        index_records = index_groups[key]
        xml_records = xml_groups.get(key, [])
        abs_ee_count = len(index_records)
        candidate_records = [
            record
            for record in index_records
            if str(record.get("candidate_cmbs_name_match", "")).lower() == "true"
        ]
        candidate_count = len(candidate_records)
        xml_sample_count = len(xml_records)
        asset_xml_count = sum(
            row.get("asset_data_xml_verified") == "true" for row in xml_records
        )
        cmbs_xml_count = sum(
            row.get("cmbs_asset_xml_verified") == "true" for row in xml_records
        )
        latest_date = max(
            str(record.get("filing_date", "")) for record in index_records
        )
        rows.append(
            {
                "date": latest_date,
                "index_year": key[0],
                "index_quarter": key[1],
                "abs_ee_filing_row_count": str(abs_ee_count),
                "candidate_cmbs_name_match_row_count": str(candidate_count),
                "candidate_cmbs_name_match_share_of_abs_ee": _summary_number(
                    candidate_count / abs_ee_count if abs_ee_count else math.nan
                ),
                "unique_abs_ee_cik_count": str(
                    len({str(record.get("cik", "")) for record in index_records})
                ),
                "unique_candidate_cmbs_cik_count": str(
                    len({str(record.get("cik", "")) for record in candidate_records})
                ),
                "xml_verification_sample_row_count": str(xml_sample_count),
                "asset_data_xml_verified_row_count": str(asset_xml_count),
                "cmbs_asset_xml_verified_row_count": str(cmbs_xml_count),
                "xml_verified_share_of_candidate_name_rows": _summary_number(
                    cmbs_xml_count / candidate_count if candidate_count else math.nan
                ),
                "public_abs_ee_filing_frame_available": "true",
                "candidate_name_frame_available": "true",
                "asset_class_xml_verification_sample_available": str(
                    cmbs_xml_count > 0
                ).lower(),
                "public_representativeness_frame_for_abs_ee_index_available": "true",
                "public_cre_market_population_denominator_available": "false",
                "representative_sampling_weights_available": "false",
                "cre_market_representativeness_design_available": "false",
                "cre_refinancing_outcome_available": "false",
                "cre_real_activity_mapping_available": "false",
                "row_support_status": (
                    "public_abs_ee_frame_and_xml_sample_design_review_fail_closed"
                ),
                "method_blocker": (
                    "sec_abs_ee_filing_frame_and_bounded_xml_sample_are_"
                    "admitted_but_no_public_cre_market_population_denominator_"
                    "representative_weights_refinancing_outcome_panel_or_"
                    "real_activity_bridge_is_admitted"
                ),
                "missing_cell_blocker": (
                    "no_public_cre_market_population_denominator;"
                    "no_representative_sampling_weights;"
                    "no_refinancing_outcome_panel;"
                    "no_real_activity_bridge"
                ),
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return rows


def _sec_abs_ee_cmbs_representativeness_design_snapshot(
    *,
    registry: SourceRegistry,
    filing_index_snapshot: SourceSnapshot,
    xml_verification_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[SEC_ABS_EE_CMBS_REPRESENTATIVENESS_DESIGN_SERIES_ID]
    records = _sec_abs_ee_cmbs_representativeness_design_records(
        filing_index_records=filing_index_snapshot.records,
        xml_verification_records=xml_verification_snapshot.records,
    )
    if not records:
        raise ValueError("SEC ABS-EE CMBS representativeness design rows are empty")
    records_hash = _records_sha256(records)
    first_date = min(row["date"] for row in records)
    latest_date = max(row["date"] for row in records)
    abs_ee_count = sum(int(row["abs_ee_filing_row_count"]) for row in records)
    candidate_count = sum(
        int(row["candidate_cmbs_name_match_row_count"]) for row in records
    )
    xml_sample_count = sum(
        int(row["xml_verification_sample_row_count"]) for row in records
    )
    cmbs_xml_count = sum(
        int(row["cmbs_asset_xml_verified_row_count"]) for row in records
    )
    note = (
        "sec_abs_ee_cmbs_representativeness_design_review_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"derived_from_series_ids={filing_index_snapshot.metadata.series_id},"
        f"{xml_verification_snapshot.metadata.series_id};"
        f"abs_ee_filing_row_count={abs_ee_count};"
        f"candidate_cmbs_name_match_row_count={candidate_count};"
        f"xml_verification_sample_row_count={xml_sample_count};"
        f"cmbs_asset_xml_verified_row_count={cmbs_xml_count};"
        "public_abs_ee_filing_frame_available=true;"
        "candidate_name_frame_available=true;"
        "asset_class_xml_verification_sample_available=true;"
        "public_representativeness_frame_for_abs_ee_index_available=true;"
        "public_cre_market_population_denominator_available=false;"
        "representative_sampling_weights_available=false;"
        "cre_market_representativeness_design_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind=(
                "derived_sec_abs_ee_cmbs_representativeness_design_review_context"
            ),
            note=note,
        ),
        records=records,
    )


def _latest_fred_numeric_record(
    records: Sequence[Mapping[str, object]],
) -> tuple[str, float]:
    dated_values: list[tuple[str, float]] = []
    for record in records:
        value = _source_float(str(record.get("value", "") or ""))
        date_value = str(record.get("date", "")).strip()
        if date_value and math.isfinite(value):
            dated_values.append((date_value, value))
    if not dated_values:
        raise ValueError("FRED source records contained no numeric observations")
    return max(dated_values, key=lambda item: item[0])


def _fed_z1_cmbs_abs_population_denominator_records(
    *,
    z1_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
) -> list[dict[str, str]]:
    latest_z1_date, latest_z1_mil = _latest_fred_numeric_record(z1_snapshot.records)
    latest_z1_bil = latest_z1_mil / 1000.0
    rows: list[dict[str, str]] = []
    for record in representativeness_snapshot.records:
        abs_ee_count = int(str(record.get("abs_ee_filing_row_count", "0") or "0"))
        candidate_count = int(
            str(record.get("candidate_cmbs_name_match_row_count", "0") or "0")
        )
        xml_sample_count = int(
            str(record.get("xml_verification_sample_row_count", "0") or "0")
        )
        cmbs_xml_count = int(
            str(record.get("cmbs_asset_xml_verified_row_count", "0") or "0")
        )
        rows.append(
            {
                "date": str(record.get("date", "")).strip(),
                "index_year": str(record.get("index_year", "")).strip(),
                "index_quarter": str(record.get("index_quarter", "")).strip(),
                "z1_population_denominator_series_id": z1_snapshot.metadata.series_id,
                "z1_population_denominator_observation_date": latest_z1_date,
                "z1_population_denominator_millions_of_dollars": _summary_number(
                    latest_z1_mil
                ),
                "z1_population_denominator_billions_of_dollars": _summary_number(
                    latest_z1_bil
                ),
                "z1_population_denominator_scope": (
                    "issuers_of_asset_backed_securities_commercial_mortgages_asset"
                ),
                "abs_ee_filing_row_count": str(abs_ee_count),
                "candidate_cmbs_name_match_row_count": str(candidate_count),
                "xml_verification_sample_row_count": str(xml_sample_count),
                "cmbs_asset_xml_verified_row_count": str(cmbs_xml_count),
                "candidate_name_rows_per_billion_z1_denominator": _summary_number(
                    candidate_count / latest_z1_bil if latest_z1_bil else math.nan
                ),
                "verified_xml_rows_per_billion_z1_denominator": _summary_number(
                    cmbs_xml_count / latest_z1_bil if latest_z1_bil else math.nan
                ),
                "public_cmbs_abs_segment_population_denominator_available": "true",
                "public_cre_market_population_denominator_available": "false",
                "population_denominator_is_full_cre_market": "false",
                "filing_count_to_balance_weight_available": "false",
                "representative_sampling_weights_available": "false",
                "cre_market_representativeness_design_available": "false",
                "cre_refinancing_outcome_available": "false",
                "cre_real_activity_mapping_available": "false",
                "row_support_status": (
                    "public_z1_cmbs_abs_segment_denominator_admitted_fail_closed"
                ),
                "method_blocker": (
                    "z1_abs_issuer_commercial_mortgage_stock_is_public_segment_"
                    "denominator_but_not_full_cre_market_population_not_filing_"
                    "balance_weights_not_refinancing_outcome_panel_and_not_real_"
                    "activity_bridge"
                ),
                "missing_cell_blocker": (
                    "no_full_cre_market_population_denominator;"
                    "no_filing_count_to_balance_weight;"
                    "no_representative_sampling_weights;"
                    "no_refinancing_outcome_panel;"
                    "no_real_activity_bridge"
                ),
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return rows


def _fed_z1_cmbs_abs_population_denominator_snapshot(
    *,
    registry: SourceRegistry,
    z1_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[FED_Z1_CMBS_ABS_POPULATION_DENOMINATOR_SERIES_ID]
    records = _fed_z1_cmbs_abs_population_denominator_records(
        z1_snapshot=z1_snapshot,
        representativeness_snapshot=representativeness_snapshot,
    )
    if not records:
        raise ValueError("Fed Z.1 CMBS/ABS population denominator rows are empty")
    records_hash = _records_sha256(records)
    first_date = min(row["date"] for row in records)
    latest_date = max(row["date"] for row in records)
    latest_z1_date = records[0]["z1_population_denominator_observation_date"]
    latest_z1_bil = records[0]["z1_population_denominator_billions_of_dollars"]
    note = (
        "fed_z1_cmbs_abs_commercial_mortgage_population_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"derived_from_series_ids={z1_snapshot.metadata.series_id},"
        f"{representativeness_snapshot.metadata.series_id};"
        f"z1_population_denominator_observation_date={latest_z1_date};"
        f"z1_population_denominator_billions_of_dollars={latest_z1_bil};"
        "public_cmbs_abs_segment_population_denominator_available=true;"
        "public_cre_market_population_denominator_available=false;"
        "population_denominator_is_full_cre_market=false;"
        "filing_count_to_balance_weight_available=false;"
        "representative_sampling_weights_available=false;"
        "cre_market_representativeness_design_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_z1_date,
            snapshot_kind="derived_fred_z1_cmbs_abs_population_denominator_context",
            note=note,
        ),
        records=records,
    )


def _fed_z1_total_commercial_mortgage_population_records(
    *,
    total_z1_snapshot: SourceSnapshot,
    cmbs_abs_z1_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
) -> list[dict[str, str]]:
    latest_total_date, latest_total_mil = _latest_fred_numeric_record(
        total_z1_snapshot.records
    )
    latest_cmbs_date, latest_cmbs_mil = _latest_fred_numeric_record(
        cmbs_abs_z1_snapshot.records
    )
    latest_total_bil = latest_total_mil / 1000.0
    latest_cmbs_bil = latest_cmbs_mil / 1000.0
    rows: list[dict[str, str]] = []
    for record in representativeness_snapshot.records:
        abs_ee_count = int(str(record.get("abs_ee_filing_row_count", "0") or "0"))
        candidate_count = int(
            str(record.get("candidate_cmbs_name_match_row_count", "0") or "0")
        )
        xml_sample_count = int(
            str(record.get("xml_verification_sample_row_count", "0") or "0")
        )
        cmbs_xml_count = int(
            str(record.get("cmbs_asset_xml_verified_row_count", "0") or "0")
        )
        rows.append(
            {
                "date": str(record.get("date", "")).strip(),
                "index_year": str(record.get("index_year", "")).strip(),
                "index_quarter": str(record.get("index_quarter", "")).strip(),
                "z1_total_population_denominator_series_id": (
                    total_z1_snapshot.metadata.series_id
                ),
                "z1_total_population_denominator_observation_date": (latest_total_date),
                "z1_total_population_denominator_millions_of_dollars": (
                    _summary_number(latest_total_mil)
                ),
                "z1_total_population_denominator_billions_of_dollars": (
                    _summary_number(latest_total_bil)
                ),
                "z1_total_population_denominator_scope": (
                    "all_sectors_commercial_mortgages_asset_level"
                ),
                "z1_cmbs_abs_segment_denominator_series_id": (
                    cmbs_abs_z1_snapshot.metadata.series_id
                ),
                "z1_cmbs_abs_segment_denominator_observation_date": (latest_cmbs_date),
                "z1_cmbs_abs_segment_denominator_millions_of_dollars": (
                    _summary_number(latest_cmbs_mil)
                ),
                "z1_cmbs_abs_segment_denominator_billions_of_dollars": (
                    _summary_number(latest_cmbs_bil)
                ),
                "cmbs_abs_segment_share_of_total_commercial_mortgages": (
                    _summary_number(
                        latest_cmbs_mil / latest_total_mil
                        if latest_total_mil
                        else math.nan
                    )
                ),
                "abs_ee_filing_row_count": str(abs_ee_count),
                "candidate_cmbs_name_match_row_count": str(candidate_count),
                "xml_verification_sample_row_count": str(xml_sample_count),
                "cmbs_asset_xml_verified_row_count": str(cmbs_xml_count),
                "candidate_name_rows_per_billion_total_denominator": (
                    _summary_number(
                        candidate_count / latest_total_bil
                        if latest_total_bil
                        else math.nan
                    )
                ),
                "verified_xml_rows_per_billion_total_denominator": _summary_number(
                    cmbs_xml_count / latest_total_bil if latest_total_bil else math.nan
                ),
                "public_total_commercial_mortgage_population_denominator_available": (
                    "true"
                ),
                "public_cre_market_population_denominator_available": "true",
                "population_denominator_is_full_cre_market": "true",
                "public_cmbs_abs_segment_population_denominator_available": "true",
                "filing_count_to_balance_weight_available": "false",
                "representative_sampling_weights_available": "false",
                "cre_market_representativeness_design_available": "false",
                "cre_refinancing_outcome_available": "false",
                "cre_real_activity_mapping_available": "false",
                "row_support_status": (
                    "public_z1_total_commercial_mortgage_denominator_admitted_"
                    "fail_closed"
                ),
                "method_blocker": (
                    "z1_all_sectors_commercial_mortgage_stock_is_public_total_"
                    "market_stock_denominator_but_not_filing_balance_weights_not_"
                    "representative_sampling_weights_not_refinancing_outcome_panel_"
                    "and_not_real_activity_bridge"
                ),
                "missing_cell_blocker": (
                    "no_filing_count_to_balance_weight;"
                    "no_representative_sampling_weights;"
                    "no_refinancing_outcome_panel;"
                    "no_real_activity_bridge"
                ),
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return rows


def _fed_z1_total_commercial_mortgage_population_snapshot(
    *,
    registry: SourceRegistry,
    total_z1_snapshot: SourceSnapshot,
    cmbs_abs_z1_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[FED_Z1_TOTAL_COMMERCIAL_MORTGAGE_POPULATION_SERIES_ID]
    records = _fed_z1_total_commercial_mortgage_population_records(
        total_z1_snapshot=total_z1_snapshot,
        cmbs_abs_z1_snapshot=cmbs_abs_z1_snapshot,
        representativeness_snapshot=representativeness_snapshot,
    )
    if not records:
        raise ValueError("Fed Z.1 total commercial mortgage denominator rows are empty")
    records_hash = _records_sha256(records)
    first_date = min(row["date"] for row in records)
    latest_date = max(row["date"] for row in records)
    latest_z1_date = records[0]["z1_total_population_denominator_observation_date"]
    latest_z1_bil = records[0]["z1_total_population_denominator_billions_of_dollars"]
    latest_cmbs_share = records[0][
        "cmbs_abs_segment_share_of_total_commercial_mortgages"
    ]
    note = (
        "fed_z1_total_commercial_mortgage_population_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"derived_from_series_ids={total_z1_snapshot.metadata.series_id},"
        f"{cmbs_abs_z1_snapshot.metadata.series_id},"
        f"{representativeness_snapshot.metadata.series_id};"
        f"z1_total_population_denominator_observation_date={latest_z1_date};"
        f"z1_total_population_denominator_billions_of_dollars={latest_z1_bil};"
        f"cmbs_abs_segment_share_of_total_commercial_mortgages={latest_cmbs_share};"
        "public_total_commercial_mortgage_population_denominator_available=true;"
        "public_cre_market_population_denominator_available=true;"
        "population_denominator_is_full_cre_market=true;"
        "filing_count_to_balance_weight_available=false;"
        "representative_sampling_weights_available=false;"
        "cre_market_representativeness_design_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_z1_date,
            snapshot_kind="derived_fred_z1_total_cre_population_denominator_context",
            note=note,
        ),
        records=records,
    )


def _calendar_quarter_label(date_text: str) -> tuple[str, str]:
    value = str(date_text).strip()
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid ISO date for quarter label: {value}") from exc
    quarter = (parsed.month - 1) // 3 + 1
    return str(parsed.year), f"QTR{quarter}"


def _sec_abs_ee_cmbs_reviewed_balance_coverage_records(
    *,
    asset_time_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
    cmbs_abs_z1_snapshot: SourceSnapshot,
    total_z1_snapshot: SourceSnapshot,
) -> list[dict[str, str]]:
    latest_cmbs_date, latest_cmbs_mil = _latest_fred_numeric_record(
        cmbs_abs_z1_snapshot.records
    )
    latest_total_date, latest_total_mil = _latest_fred_numeric_record(
        total_z1_snapshot.records
    )

    time_groups: dict[tuple[str, str], list[Mapping[str, object]]] = {}
    for record in asset_time_snapshot.records:
        filing_date = str(record.get("filing_date", "")).strip()
        if not filing_date:
            continue
        key = _calendar_quarter_label(filing_date)
        time_groups.setdefault(key, []).append(record)

    rows: list[dict[str, str]] = []
    for record in representativeness_snapshot.records:
        key = (
            str(record.get("index_year", "")).strip(),
            str(record.get("index_quarter", "")).strip(),
        )
        quarter_records = time_groups.get(key, [])
        latest_by_asset: dict[str, Mapping[str, object]] = {}
        balance_row_count = 0
        for asset_record in quarter_records:
            balance = _source_float(
                str(asset_record.get("reportPeriodEndActualBalanceAmount", "") or "")
            )
            if not math.isfinite(balance):
                continue
            balance_row_count += 1
            trust_asset_key = str(
                asset_record.get("public_trust_asset_number_key", "")
            ).strip()
            if not trust_asset_key:
                trust_asset_key = "::".join(
                    [
                        str(asset_record.get("cik", "")).strip(),
                        str(asset_record.get("assetNumber", "")).strip(),
                    ]
                )
            existing = latest_by_asset.get(trust_asset_key)
            if existing is None or (
                str(asset_record.get("date", "")).strip(),
                str(asset_record.get("filing_date", "")).strip(),
            ) > (
                str(existing.get("date", "")).strip(),
                str(existing.get("filing_date", "")).strip(),
            ):
                latest_by_asset[trust_asset_key] = asset_record

        latest_balance_dollars = sum(
            _source_float(
                str(asset_record.get("reportPeriodEndActualBalanceAmount", "") or "")
            )
            for asset_record in latest_by_asset.values()
        )
        latest_balance_mil = latest_balance_dollars / 1_000_000.0
        latest_balance_bil = latest_balance_dollars / 1_000_000_000.0
        trust_count = len(
            {
                str(asset_record.get("cik", "")).strip()
                for asset_record in quarter_records
                if str(asset_record.get("cik", "")).strip()
            }
        )
        accession_count = len(
            {
                str(asset_record.get("accession_number", "")).strip()
                for asset_record in quarter_records
                if str(asset_record.get("accession_number", "")).strip()
            }
        )
        rows.append(
            {
                "date": str(record.get("date", "")).strip(),
                "index_year": key[0],
                "index_quarter": key[1],
                "asset_time_dimension_source_series_id": (
                    asset_time_snapshot.metadata.series_id
                ),
                "asset_time_dimension_row_count": str(len(quarter_records)),
                "balance_observation_row_count": str(balance_row_count),
                "unique_reviewed_trust_count": str(trust_count),
                "unique_reviewed_accession_count": str(accession_count),
                "unique_reviewed_public_trust_asset_key_count": str(
                    len(latest_by_asset)
                ),
                "reviewed_latest_actual_balance_millions_of_dollars": (
                    _summary_number(latest_balance_mil)
                ),
                "reviewed_latest_actual_balance_billions_of_dollars": (
                    _summary_number(latest_balance_bil)
                ),
                "balance_metric_used": "reportPeriodEndActualBalanceAmount",
                "balance_deduplication_key": "public_trust_asset_number_key",
                "z1_cmbs_abs_segment_denominator_series_id": (
                    cmbs_abs_z1_snapshot.metadata.series_id
                ),
                "z1_cmbs_abs_segment_denominator_observation_date": latest_cmbs_date,
                "z1_cmbs_abs_segment_denominator_millions_of_dollars": (
                    _summary_number(latest_cmbs_mil)
                ),
                "reviewed_balance_share_of_cmbs_abs_segment_denominator": (
                    _summary_number(
                        latest_balance_mil / latest_cmbs_mil
                        if latest_cmbs_mil
                        else math.nan
                    )
                ),
                "z1_total_commercial_mortgage_denominator_series_id": (
                    total_z1_snapshot.metadata.series_id
                ),
                "z1_total_commercial_mortgage_denominator_observation_date": (
                    latest_total_date
                ),
                "z1_total_commercial_mortgage_denominator_millions_of_dollars": (
                    _summary_number(latest_total_mil)
                ),
                "reviewed_balance_share_of_total_commercial_mortgages": (
                    _summary_number(
                        latest_balance_mil / latest_total_mil
                        if latest_total_mil
                        else math.nan
                    )
                ),
                "public_reviewed_cmbs_balance_coverage_available": "true",
                "public_cmbs_abs_segment_population_denominator_available": "true",
                "public_cre_market_population_denominator_available": "true",
                "population_denominator_is_full_cre_market": "true",
                "filing_count_to_balance_weight_context_available": "true",
                "filing_count_to_balance_weight_available": "false",
                "representative_sampling_weights_available": "false",
                "cre_market_representativeness_design_available": "false",
                "cre_refinancing_outcome_available": "false",
                "cre_real_activity_mapping_available": "false",
                "row_support_status": (
                    "public_reviewed_cmbs_balance_coverage_context_admitted_fail_closed"
                ),
                "method_blocker": (
                    "sec_abs_ee_reviewed_trust_actual_balances_are_public_"
                    "partial_balance_coverage_context_against_z1_denominators_"
                    "but_not_representative_sampling_weights_not_filing_count_"
                    "to_balance_weights_for_the_abs_ee_frame_not_refinancing_"
                    "outcomes_and_not_cre_debt_repricing_to_real_activity_mapping"
                ),
                "missing_cell_blocker": (
                    "no_full_abs_ee_filing_count_to_balance_weight;"
                    "no_representative_sampling_weights;"
                    "no_refinancing_outcome_panel;"
                    "no_cre_debt_repricing_to_real_activity_mapping"
                ),
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return rows


def _sec_abs_ee_cmbs_reviewed_balance_coverage_snapshot(
    *,
    registry: SourceRegistry,
    asset_time_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
    cmbs_abs_z1_snapshot: SourceSnapshot,
    total_z1_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[SEC_ABS_EE_CMBS_REVIEWED_BALANCE_COVERAGE_SERIES_ID]
    records = _sec_abs_ee_cmbs_reviewed_balance_coverage_records(
        asset_time_snapshot=asset_time_snapshot,
        representativeness_snapshot=representativeness_snapshot,
        cmbs_abs_z1_snapshot=cmbs_abs_z1_snapshot,
        total_z1_snapshot=total_z1_snapshot,
    )
    if not records:
        raise ValueError("SEC ABS-EE CMBS reviewed balance coverage rows are empty")
    records_hash = _records_sha256(records)
    first_date = min(row["date"] for row in records)
    latest_date = max(row["date"] for row in records)
    source_row_count = sum(
        int(row["asset_time_dimension_row_count"]) for row in records
    )
    balance_row_count = sum(
        int(row["balance_observation_row_count"]) for row in records
    )
    latest_reviewed_balance = records[-1][
        "reviewed_latest_actual_balance_billions_of_dollars"
    ]
    latest_cmbs_share = records[-1][
        "reviewed_balance_share_of_cmbs_abs_segment_denominator"
    ]
    latest_total_share = records[-1][
        "reviewed_balance_share_of_total_commercial_mortgages"
    ]
    note = (
        "sec_abs_ee_cmbs_reviewed_balance_coverage_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"derived_from_series_ids={asset_time_snapshot.metadata.series_id},"
        f"{representativeness_snapshot.metadata.series_id},"
        f"{cmbs_abs_z1_snapshot.metadata.series_id},"
        f"{total_z1_snapshot.metadata.series_id};"
        f"asset_time_dimension_row_count={source_row_count};"
        f"balance_observation_row_count={balance_row_count};"
        f"latest_reviewed_actual_balance_billions_of_dollars={latest_reviewed_balance};"
        f"latest_reviewed_balance_share_of_cmbs_abs_segment_denominator={latest_cmbs_share};"
        f"latest_reviewed_balance_share_of_total_commercial_mortgages={latest_total_share};"
        "public_reviewed_cmbs_balance_coverage_available=true;"
        "filing_count_to_balance_weight_context_available=true;"
        "filing_count_to_balance_weight_available=false;"
        "representative_sampling_weights_available=false;"
        "cre_market_representativeness_design_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind=("derived_sec_abs_ee_cmbs_reviewed_balance_coverage_context"),
            note=note,
        ),
        records=records,
    )


def _maturity_window_bucket(*, report_date: str, maturity_date: str) -> str:
    if not report_date or not maturity_date:
        return "missing_maturity_or_report_date"
    days_to_maturity = (
        date.fromisoformat(maturity_date) - date.fromisoformat(report_date)
    ).days
    if days_to_maturity < 0:
        return "past_maturity"
    if days_to_maturity <= 90:
        return "matures_0_90_days"
    if days_to_maturity <= 365:
        return "matures_91_365_days"
    if days_to_maturity <= 730:
        return "matures_366_730_days"
    return "matures_after_730_days"


def _sec_abs_ee_cmbs_maturity_status_outcome_records(
    *,
    asset_time_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
) -> list[dict[str, str]]:
    quarter_groups: dict[tuple[str, str], list[Mapping[str, object]]] = {}
    for record in asset_time_snapshot.records:
        filing_date = str(record.get("filing_date", "")).strip()
        if not filing_date:
            continue
        key = _calendar_quarter_label(filing_date)
        quarter_groups.setdefault(key, []).append(record)

    bucket_order = (
        "past_maturity",
        "matures_0_90_days",
        "matures_91_365_days",
        "matures_366_730_days",
        "matures_after_730_days",
    )
    rows: list[dict[str, str]] = []
    for record in representativeness_snapshot.records:
        key = (
            str(record.get("index_year", "")).strip(),
            str(record.get("index_quarter", "")).strip(),
        )
        quarter_records = quarter_groups.get(key, [])
        latest_by_loan: dict[str, Mapping[str, object]] = {}
        for asset_record in quarter_records:
            loan_key = str(
                asset_record.get("public_trust_asset_number_key", "")
            ).strip()
            if not loan_key:
                loan_key = "::".join(
                    [
                        str(asset_record.get("cik", "")).strip(),
                        str(asset_record.get("assetNumber", "")).strip(),
                    ]
                )
            if not loan_key.strip(":"):
                continue
            existing = latest_by_loan.get(loan_key)
            if existing is None or (
                str(asset_record.get("date", "")).strip(),
                str(asset_record.get("filing_date", "")).strip(),
                str(asset_record.get("property_index", "")).strip(),
            ) > (
                str(existing.get("date", "")).strip(),
                str(existing.get("filing_date", "")).strip(),
                str(existing.get("property_index", "")).strip(),
            ):
                latest_by_loan[loan_key] = asset_record

        grouped: dict[str, list[Mapping[str, object]]] = {
            bucket: [] for bucket in bucket_order
        }
        for loan_record in latest_by_loan.values():
            report_date = str(loan_record.get("date", "")).strip()
            maturity_raw = str(loan_record.get("maturityDate", "")).strip()
            maturity_date = _sec_abs_ee_date(maturity_raw) if maturity_raw else ""
            bucket = _maturity_window_bucket(
                report_date=report_date,
                maturity_date=maturity_date,
            )
            if bucket in grouped:
                grouped[bucket].append(loan_record)

        for bucket in bucket_order:
            bucket_records = grouped[bucket]
            actual_balances = [
                parsed
                for item in bucket_records
                if math.isfinite(
                    parsed := _source_float(
                        str(item.get("reportPeriodEndActualBalanceAmount", "") or "")
                    )
                )
            ]
            balance_dollars = sum(actual_balances)
            payment_status_values = [
                str(item.get("paymentStatusLoanCode", "")).strip()
                for item in bucket_records
                if str(item.get("paymentStatusLoanCode", "")).strip()
            ]
            rows.append(
                {
                    "date": str(record.get("date", "")).strip(),
                    "index_year": key[0],
                    "index_quarter": key[1],
                    "maturity_window_bucket": bucket,
                    "asset_time_dimension_source_series_id": (
                        asset_time_snapshot.metadata.series_id
                    ),
                    "asset_time_dimension_row_count": str(len(quarter_records)),
                    "unique_reviewed_public_trust_loan_key_count": str(
                        len(latest_by_loan)
                    ),
                    "bucket_reviewed_loan_count": str(len(bucket_records)),
                    "bucket_actual_balance_observation_count": str(
                        len(actual_balances)
                    ),
                    "bucket_actual_balance_millions_of_dollars": _summary_number(
                        balance_dollars / 1_000_000.0
                    ),
                    "bucket_actual_balance_billions_of_dollars": _summary_number(
                        balance_dollars / 1_000_000_000.0
                    ),
                    "maturity_date_available_count": str(
                        sum(
                            bool(str(item.get("maturityDate", "")).strip())
                            for item in bucket_records
                        )
                    ),
                    "paid_through_date_available_count": str(
                        sum(
                            bool(str(item.get("paidThroughDate", "")).strip())
                            for item in bucket_records
                        )
                    ),
                    "payment_status_code_available_count": str(
                        len(payment_status_values)
                    ),
                    "payment_status_code_0_count": str(
                        sum(value == "0" for value in payment_status_values)
                    ),
                    "payment_status_nonzero_code_count": str(
                        sum(value != "0" for value in payment_status_values)
                    ),
                    "payment_status_blank_count": str(
                        len(bucket_records) - len(payment_status_values)
                    ),
                    "modified_indicator_true_count": str(
                        sum(
                            str(item.get("modifiedIndicator", "")).lower() == "true"
                            for item in bucket_records
                        )
                    ),
                    "special_servicer_or_workout_marker_seen_count": str(
                        sum(
                            str(
                                item.get("special_servicer_or_workout_marker_seen", "")
                            ).lower()
                            == "true"
                            for item in bucket_records
                        )
                    ),
                    "public_maturity_window_status_context_available": "true",
                    "public_paid_through_payment_status_context_available": "true",
                    "explicit_refinancing_outcome_field_available": "false",
                    "cre_refinancing_outcome_available": "false",
                    "cre_real_activity_mapping_available": "false",
                    "filing_count_to_balance_weight_available": "false",
                    "representative_sampling_weights_available": "false",
                    "row_support_status": (
                        "public_cmbs_maturity_status_outcome_review_fail_closed"
                    ),
                    "method_blocker": (
                        "sec_abs_ee_reviewed_trust_maturity_dates_payment_status_"
                        "paid_through_and_balance_fields_are_public_outcome_"
                        "availability_context_but_not_explicit_refinancing_"
                        "outcomes_not_representative_sampling_weights_and_not_cre_"
                        "debt_repricing_to_real_activity_mapping"
                    ),
                    "missing_cell_blocker": (
                        "no_explicit_refinancing_outcome_field;"
                        "no_representative_sampling_weights;"
                        "no_full_abs_ee_filing_count_to_balance_weight;"
                        "no_cre_debt_repricing_to_real_activity_mapping"
                    ),
                    "denominator_prior_narrowing_allowed": "false",
                    "split_denominator_promotion_allowed": "false",
                    "formula_replacement_allowed": "false",
                    "main_ratio_admission_allowed": "false",
                    "incidence_output_enabled": "false",
                    "welfare_tax_mpc_output_enabled": "false",
                    "policy_failure_output_enabled": "false",
                    "pricing_output_enabled": "false",
                }
            )
    return rows


def _sec_abs_ee_cmbs_maturity_status_outcome_snapshot(
    *,
    registry: SourceRegistry,
    asset_time_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[SEC_ABS_EE_CMBS_MATURITY_STATUS_OUTCOME_SERIES_ID]
    records = _sec_abs_ee_cmbs_maturity_status_outcome_records(
        asset_time_snapshot=asset_time_snapshot,
        representativeness_snapshot=representativeness_snapshot,
    )
    if not records:
        raise ValueError("SEC ABS-EE CMBS maturity/status outcome rows are empty")
    records_hash = _records_sha256(records)
    first_date = min(row["date"] for row in records)
    latest_date = max(row["date"] for row in records)
    underlying_rows = sum(
        int(row["asset_time_dimension_row_count"])
        for row in records
        if row["maturity_window_bucket"] == "past_maturity"
    )
    reviewed_loans_latest = records[-1]["unique_reviewed_public_trust_loan_key_count"]
    latest_records = [row for row in records if row["date"] == latest_date]
    near_term_loan_count = sum(
        int(row["bucket_reviewed_loan_count"])
        for row in latest_records
        if row["maturity_window_bucket"]
        in {
            "past_maturity",
            "matures_0_90_days",
            "matures_91_365_days",
            "matures_366_730_days",
        }
    )
    near_term_balance_bil = sum(
        _source_float(row["bucket_actual_balance_billions_of_dollars"])
        for row in latest_records
        if row["maturity_window_bucket"]
        in {
            "past_maturity",
            "matures_0_90_days",
            "matures_91_365_days",
            "matures_366_730_days",
        }
    )
    note = (
        "sec_abs_ee_cmbs_maturity_status_outcome_review_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"derived_from_series_ids={asset_time_snapshot.metadata.series_id},"
        f"{representativeness_snapshot.metadata.series_id};"
        f"asset_time_dimension_row_count={underlying_rows};"
        f"latest_unique_reviewed_public_trust_loan_key_count={reviewed_loans_latest};"
        f"near_term_or_past_maturity_reviewed_loan_count={near_term_loan_count};"
        f"near_term_or_past_maturity_actual_balance_billions_of_dollars={_summary_number(near_term_balance_bil)};"
        "public_maturity_window_status_context_available=true;"
        "public_paid_through_payment_status_context_available=true;"
        "explicit_refinancing_outcome_field_available=false;"
        "cre_refinancing_outcome_available=false;"
        "filing_count_to_balance_weight_available=false;"
        "representative_sampling_weights_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_date,
            snapshot_kind=(
                "derived_sec_abs_ee_cmbs_maturity_status_outcome_review_context"
            ),
            note=note,
        ),
        records=records,
    )


def _fred_nonres_construction_real_activity_bridge_records(
    *,
    construction_snapshot: SourceSnapshot,
    total_z1_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
) -> list[dict[str, str]]:
    latest_construction_date, latest_construction_mil = _latest_fred_numeric_record(
        construction_snapshot.records
    )
    latest_total_date, latest_total_mil = _latest_fred_numeric_record(
        total_z1_snapshot.records
    )
    latest_construction_bil = latest_construction_mil / 1000.0
    latest_total_bil = latest_total_mil / 1000.0
    flow_stock_ratio = (
        latest_construction_mil / latest_total_mil if latest_total_mil else math.nan
    )
    rows: list[dict[str, str]] = []
    for record in representativeness_snapshot.records:
        rows.append(
            {
                "date": str(record.get("date", "")).strip(),
                "index_year": str(record.get("index_year", "")).strip(),
                "index_quarter": str(record.get("index_quarter", "")).strip(),
                "real_activity_series_id": construction_snapshot.metadata.series_id,
                "real_activity_observation_date": latest_construction_date,
                "real_activity_millions_of_dollars_saar": _summary_number(
                    latest_construction_mil
                ),
                "real_activity_billions_of_dollars_saar": _summary_number(
                    latest_construction_bil
                ),
                "real_activity_scope": (
                    "total_construction_spending_nonresidential_united_states"
                ),
                "commercial_mortgage_stock_series_id": (
                    total_z1_snapshot.metadata.series_id
                ),
                "commercial_mortgage_stock_observation_date": latest_total_date,
                "commercial_mortgage_stock_millions_of_dollars": _summary_number(
                    latest_total_mil
                ),
                "commercial_mortgage_stock_billions_of_dollars": _summary_number(
                    latest_total_bil
                ),
                "nonres_construction_saar_to_commercial_mortgage_stock_ratio": (
                    _summary_number(flow_stock_ratio)
                ),
                "flow_stock_ratio_is_not_elasticity": "true",
                "public_nonresidential_construction_real_activity_series_available": (
                    "true"
                ),
                "public_cre_market_population_denominator_available": "true",
                "population_denominator_is_full_cre_market": "true",
                "public_real_activity_bridge_review_available": "true",
                "filing_count_to_balance_weight_available": "false",
                "representative_sampling_weights_available": "false",
                "cre_market_representativeness_design_available": "false",
                "cre_refinancing_outcome_available": "false",
                "cre_real_activity_mapping_available": "false",
                "row_support_status": (
                    "public_nonres_construction_real_activity_context_admitted_"
                    "fail_closed"
                ),
                "method_blocker": (
                    "fred_census_nonresidential_construction_spending_is_public_"
                    "real_activity_context_but_not_a_cre_refinancing_outcome_"
                    "panel_not_abs_ee_filing_balance_weights_not_representative_"
                    "sampling_weights_and_not_a_causal_or_accounting_mapping_"
                    "from_cre_debt_repricing_to_real_activity"
                ),
                "missing_cell_blocker": (
                    "no_filing_count_to_balance_weight;"
                    "no_representative_sampling_weights;"
                    "no_refinancing_outcome_panel;"
                    "no_cre_debt_repricing_to_real_activity_mapping"
                ),
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "policy_failure_output_enabled": "false",
                "pricing_output_enabled": "false",
            }
        )
    return rows


def _fred_nonres_construction_real_activity_bridge_snapshot(
    *,
    registry: SourceRegistry,
    construction_snapshot: SourceSnapshot,
    total_z1_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[FRED_NONRES_CONSTRUCTION_REAL_ACTIVITY_BRIDGE_SERIES_ID]
    records = _fred_nonres_construction_real_activity_bridge_records(
        construction_snapshot=construction_snapshot,
        total_z1_snapshot=total_z1_snapshot,
        representativeness_snapshot=representativeness_snapshot,
    )
    if not records:
        raise ValueError(
            "FRED nonresidential construction real-activity bridge rows are empty"
        )
    records_hash = _records_sha256(records)
    first_date = min(row["date"] for row in records)
    latest_date = max(row["date"] for row in records)
    latest_activity_date = records[0]["real_activity_observation_date"]
    latest_activity_bil = records[0]["real_activity_billions_of_dollars_saar"]
    latest_stock_date = records[0]["commercial_mortgage_stock_observation_date"]
    latest_stock_bil = records[0]["commercial_mortgage_stock_billions_of_dollars"]
    latest_ratio = records[0][
        "nonres_construction_saar_to_commercial_mortgage_stock_ratio"
    ]
    note = (
        "fred_nonres_construction_real_activity_bridge_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"derived_from_series_ids={construction_snapshot.metadata.series_id},"
        f"{total_z1_snapshot.metadata.series_id},"
        f"{representativeness_snapshot.metadata.series_id};"
        f"real_activity_observation_date={latest_activity_date};"
        f"real_activity_billions_of_dollars_saar={latest_activity_bil};"
        f"commercial_mortgage_stock_observation_date={latest_stock_date};"
        f"commercial_mortgage_stock_billions_of_dollars={latest_stock_bil};"
        f"nonres_construction_saar_to_commercial_mortgage_stock_ratio={latest_ratio};"
        "flow_stock_ratio_is_not_elasticity=true;"
        "public_nonresidential_construction_real_activity_series_available=true;"
        "public_cre_market_population_denominator_available=true;"
        "public_real_activity_bridge_review_available=true;"
        "filing_count_to_balance_weight_available=false;"
        "representative_sampling_weights_available=false;"
        "cre_market_representativeness_design_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_activity_date,
            snapshot_kind=(
                "derived_fred_nonres_construction_real_activity_bridge_context"
            ),
            note=note,
        ),
        records=records,
    )


def _fred_cre_property_type_construction_bridge_records(
    *,
    construction_snapshots: Mapping[str, SourceSnapshot],
    total_nonres_snapshot: SourceSnapshot,
    total_private_nonres_snapshot: SourceSnapshot,
    total_z1_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
) -> list[dict[str, str]]:
    latest_total_nonres_date, latest_total_nonres_mil = _latest_fred_numeric_record(
        total_nonres_snapshot.records
    )
    latest_private_nonres_date, latest_private_nonres_mil = _latest_fred_numeric_record(
        total_private_nonres_snapshot.records
    )
    latest_stock_date, latest_stock_mil = _latest_fred_numeric_record(
        total_z1_snapshot.records
    )
    latest_stock_bil = latest_stock_mil / 1000.0
    latest_by_series = {
        series_id: _latest_fred_numeric_record(snapshot.records)
        for series_id, snapshot in construction_snapshots.items()
    }

    rows: list[dict[str, str]] = []
    for record in representativeness_snapshot.records:
        for series_id, (
            category,
            bridge_role,
        ) in CRE_PROPERTY_CONSTRUCTION_SERIES.items():
            snapshot = construction_snapshots[series_id]
            latest_date, latest_mil = latest_by_series[series_id]
            latest_bil = latest_mil / 1000.0
            rows.append(
                {
                    "date": str(record.get("date", "")).strip(),
                    "index_year": str(record.get("index_year", "")).strip(),
                    "index_quarter": str(record.get("index_quarter", "")).strip(),
                    "construction_series_id": snapshot.metadata.series_id,
                    "construction_category": category,
                    "construction_bridge_role": bridge_role,
                    "construction_scope": (
                        "census_value_of_construction_put_in_place_nonresidential"
                    ),
                    "construction_observation_date": latest_date,
                    "construction_millions_of_dollars_saar": _summary_number(
                        latest_mil
                    ),
                    "construction_billions_of_dollars_saar": _summary_number(
                        latest_bil
                    ),
                    "total_nonres_construction_series_id": (
                        total_nonres_snapshot.metadata.series_id
                    ),
                    "total_nonres_construction_observation_date": (
                        latest_total_nonres_date
                    ),
                    "total_nonres_construction_millions_of_dollars_saar": (
                        _summary_number(latest_total_nonres_mil)
                    ),
                    "total_private_nonres_construction_series_id": (
                        total_private_nonres_snapshot.metadata.series_id
                    ),
                    "total_private_nonres_construction_observation_date": (
                        latest_private_nonres_date
                    ),
                    "total_private_nonres_construction_millions_of_dollars_saar": (
                        _summary_number(latest_private_nonres_mil)
                    ),
                    "commercial_mortgage_stock_series_id": (
                        total_z1_snapshot.metadata.series_id
                    ),
                    "commercial_mortgage_stock_observation_date": latest_stock_date,
                    "commercial_mortgage_stock_millions_of_dollars": (
                        _summary_number(latest_stock_mil)
                    ),
                    "commercial_mortgage_stock_billions_of_dollars": (
                        _summary_number(latest_stock_bil)
                    ),
                    "category_share_of_total_nonres_construction": _summary_number(
                        latest_mil / latest_total_nonres_mil
                        if latest_total_nonres_mil
                        else math.nan
                    ),
                    "category_share_of_private_nonres_construction": _summary_number(
                        latest_mil / latest_private_nonres_mil
                        if latest_private_nonres_mil
                        else math.nan
                    ),
                    "category_saar_to_commercial_mortgage_stock_ratio": (
                        _summary_number(
                            latest_mil / latest_stock_mil
                            if latest_stock_mil
                            else math.nan
                        )
                    ),
                    "public_property_type_construction_series_available": "true",
                    "public_property_type_real_activity_context_available": "true",
                    "property_type_mapping_is_construction_spending_not_debt_exposure": (
                        "true"
                    ),
                    "property_type_flow_stock_ratio_is_not_elasticity": "true",
                    "public_cre_market_population_denominator_available": "true",
                    "population_denominator_is_full_cre_market": "true",
                    "filing_count_to_balance_weight_available": "false",
                    "representative_sampling_weights_available": "false",
                    "cre_market_representativeness_design_available": "false",
                    "cre_refinancing_outcome_available": "false",
                    "cre_debt_repricing_to_real_activity_mapping_available": "false",
                    "cre_real_activity_mapping_available": "false",
                    "row_support_status": (
                        "public_property_type_construction_context_admitted_fail_closed"
                    ),
                    "method_blocker": (
                        "fred_census_property_type_construction_spending_series_"
                        "are_public_real_activity_context_but_not_cre_debt_"
                        "exposure_weights_not_abs_ee_filing_balance_weights_not_"
                        "representative_sampling_weights_not_refinancing_outcomes_"
                        "and_not_a_mapping_from_cre_debt_repricing_to_real_activity"
                    ),
                    "missing_cell_blocker": (
                        "no_filing_count_to_balance_weight;"
                        "no_representative_sampling_weights;"
                        "no_refinancing_outcome_panel;"
                        "no_cre_debt_repricing_to_real_activity_mapping"
                    ),
                    "denominator_prior_narrowing_allowed": "false",
                    "split_denominator_promotion_allowed": "false",
                    "formula_replacement_allowed": "false",
                    "main_ratio_admission_allowed": "false",
                    "incidence_output_enabled": "false",
                    "welfare_tax_mpc_output_enabled": "false",
                    "policy_failure_output_enabled": "false",
                    "pricing_output_enabled": "false",
                }
            )
    return rows


def _fred_cre_property_type_construction_bridge_snapshot(
    *,
    registry: SourceRegistry,
    construction_snapshots: Mapping[str, SourceSnapshot],
    total_nonres_snapshot: SourceSnapshot,
    total_private_nonres_snapshot: SourceSnapshot,
    total_z1_snapshot: SourceSnapshot,
    representativeness_snapshot: SourceSnapshot,
) -> SourceSnapshot:
    series = registry.series[FRED_CRE_PROPERTY_TYPE_CONSTRUCTION_BRIDGE_SERIES_ID]
    records = _fred_cre_property_type_construction_bridge_records(
        construction_snapshots=construction_snapshots,
        total_nonres_snapshot=total_nonres_snapshot,
        total_private_nonres_snapshot=total_private_nonres_snapshot,
        total_z1_snapshot=total_z1_snapshot,
        representativeness_snapshot=representativeness_snapshot,
    )
    if not records:
        raise ValueError("FRED CRE property-type construction bridge rows are empty")
    records_hash = _records_sha256(records)
    first_date = min(row["date"] for row in records)
    latest_date = max(row["date"] for row in records)
    latest_activity_date = records[0]["construction_observation_date"]
    category_count = len(CRE_PROPERTY_CONSTRUCTION_SERIES)
    derived_ids = ",".join(
        [
            *CRE_PROPERTY_CONSTRUCTION_SERIES.keys(),
            total_nonres_snapshot.metadata.series_id,
            total_z1_snapshot.metadata.series_id,
            representativeness_snapshot.metadata.series_id,
        ]
    )
    note = (
        "fred_cre_property_type_construction_bridge_context;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        f"latest_construction_observation_date={latest_activity_date};"
        f"construction_category_count={category_count};"
        f"derived_from_series_ids={derived_ids};"
        "public_property_type_construction_series_available=true;"
        "public_property_type_real_activity_context_available=true;"
        "property_type_mapping_is_construction_spending_not_debt_exposure=true;"
        "property_type_flow_stock_ratio_is_not_elasticity=true;"
        "filing_count_to_balance_weight_available=false;"
        "representative_sampling_weights_available=false;"
        "cre_market_representativeness_design_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_debt_repricing_to_real_activity_mapping_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false;"
        "policy_failure_output_enabled=false;"
        "pricing_output_enabled=false"
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
            source_release_at=latest_activity_date,
            snapshot_kind=(
                "derived_fred_cre_property_type_construction_bridge_context"
            ),
            note=note,
        ),
        records=records,
    )


def _dta_tag_range(blob: bytes, tag: str) -> tuple[int, int]:
    start_marker = f"<{tag}>".encode("ascii")
    end_marker = f"</{tag}>".encode("ascii")
    start = blob.index(start_marker) + len(start_marker)
    end = blob.index(end_marker)
    return start, end


def _fed_scf_replicate_weight_dta_metadata(
    source_zip: Path,
) -> dict[str, str | list[str]]:
    with zipfile.ZipFile(source_zip) as archive:
        names = archive.namelist()
        if FED_SCF_REPLICATE_WEIGHT_FILE not in names:
            raise ValueError(f"{source_zip} missing {FED_SCF_REPLICATE_WEIGHT_FILE}")
        dta_blob = archive.read(FED_SCF_REPLICATE_WEIGHT_FILE)
    header_start, header_end = _dta_tag_range(dta_blob, "header")
    header = dta_blob[header_start:header_end]
    release_start = header.index(b"<release>") + len(b"<release>")
    release_end = header.index(b"</release>")
    byteorder_start = header.index(b"<byteorder>") + len(b"<byteorder>")
    byteorder_end = header.index(b"</byteorder>")
    k_start = header.index(b"<K>") + len(b"<K>")
    k_end = header.index(b"</K>")
    n_start = header.index(b"<N>") + len(b"<N>")
    n_end = header.index(b"</N>")
    timestamp_start = header.index(b"<timestamp>") + len(b"<timestamp>") + 1
    timestamp_end = header.index(b"</timestamp>")
    release = header[release_start:release_end].decode("ascii")
    byteorder = header[byteorder_start:byteorder_end].decode("ascii")
    if byteorder != "LSF":
        raise ValueError(f"Unsupported Fed SCF DTA byteorder: {byteorder}")
    variable_count = struct.unpack("<H", header[k_start:k_end])[0]
    observation_count = struct.unpack("<Q", header[n_start:n_end])[0]
    timestamp = header[timestamp_start:timestamp_end].decode("ascii", errors="replace")
    names_start, names_end = _dta_tag_range(dta_blob, "varnames")
    varnames_blob = dta_blob[names_start:names_end]
    if len(varnames_blob) != variable_count * 129:
        raise ValueError(
            "Fed SCF replicate DTA varname block does not match expected "
            f"Stata 118 width: {len(varnames_blob)} for {variable_count} vars"
        )
    varnames = [
        varnames_blob[index * 129 : (index + 1) * 129]
        .split(b"\x00", 1)[0]
        .decode("ascii", errors="replace")
        for index in range(variable_count)
    ]
    replicate_weight_names = [
        name for name in varnames if re.fullmatch(r"wt1b\d+", name)
    ]
    multiplier_names = [name for name in varnames if re.fullmatch(r"mm\d+", name)]
    required_keys = {"y1", "yy1"}
    missing_keys = sorted(required_keys - set(varnames))
    if missing_keys:
        raise ValueError(
            "Fed SCF replicate DTA missing required family keys: "
            + ",".join(missing_keys)
        )
    if len(replicate_weight_names) != 999:
        raise ValueError(
            "Fed SCF replicate DTA expected 999 wt1b replicate weights; "
            f"found {len(replicate_weight_names)}"
        )
    return {
        "stata_release": release,
        "stata_byteorder": byteorder,
        "source_dta_timestamp": timestamp,
        "source_dta_observation_count": str(observation_count),
        "source_dta_variable_count": str(variable_count),
        "replicate_weight_variable_count": str(len(replicate_weight_names)),
        "replicate_weight_variable_prefix": "wt1b",
        "replicate_weight_first_variable": replicate_weight_names[0],
        "replicate_weight_last_variable": replicate_weight_names[-1],
        "replicate_multiplier_variable_count": str(len(multiplier_names)),
        "family_join_keys_available": "y1;yy1",
        "schema_preview": ";".join(varnames[:8] + varnames[-3:]),
    }


def _fed_scf_replicate_weight_method_snapshot(
    *, registry: SourceRegistry, source_zip: Path
) -> SourceSnapshot:
    series = registry.series[FED_SCF_REPLICATE_WEIGHT_METHOD_SERIES_ID]
    if not source_zip.exists():
        _download_source(series.endpoint, source_zip)
    metadata = _fed_scf_replicate_weight_dta_metadata(source_zip)
    index_html = _fetch_text(FED_SCF_INDEX_PAGE_URL)
    missing_markers = [
        marker
        for marker in FED_SCF_REPLICATE_REQUIRED_INDEX_MARKERS
        if marker not in index_html
    ]
    if missing_markers:
        raise ValueError(
            "Fed SCF index page missing replicate-weight methodology markers: "
            + ",".join(missing_markers)
        )
    source_zip_hash = _file_sha256(source_zip)
    source_index_hash = hashlib.sha256(index_html.encode("utf-8")).hexdigest()
    record = {
        "date": "2022-01-01",
        "survey_year": "2022",
        "source_file": FED_SCF_REPLICATE_WEIGHT_FILE,
        "source_zip_url": series.endpoint,
        "source_zip_sha256": source_zip_hash,
        "source_index_page_url": FED_SCF_INDEX_PAGE_URL,
        "source_index_page_sha256": source_index_hash,
        "standard_error_documentation_url": FED_SCF_STANDARD_ERROR_DOCUMENTATION_URL,
        "replicate_weight_artifact_admitted": "true",
        "standard_error_methodology_context_admitted": "true",
        "replicate_weight_uncertainty_source_available": "true",
        "replicate_weight_uncertainty_executed": "false",
        "summary_extract_join_executed": "false",
        "survey_design_estimate_promoted": "false",
        "current_demand_conversion_available": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "method_blocker": (
            "replicate_weights_source_admitted_but_no_executable_joined_"
            "survey_design_uncertainty_runner_or_current_demand_response"
        ),
    }
    record.update({key: str(value) for key, value in metadata.items()})
    records = [record]
    records_hash = _records_sha256(records)
    note = (
        "fed_scf_replicate_weight_schema_and_standard_error_methodology_"
        "context_only;"
        f"source_zip_sha256={source_zip_hash};"
        f"source_index_page_sha256={source_index_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"source_dta_observation_count={metadata['source_dta_observation_count']};"
        f"source_dta_variable_count={metadata['source_dta_variable_count']};"
        "replicate_weight_variable_count=999;"
        "replicate_weight_uncertainty_source_available=true;"
        "replicate_weight_uncertainty_executed=false;"
        "summary_extract_join_executed=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2024-04-03",
            snapshot_kind="live_zip_dta_methodology_context",
            note=note,
        ),
        records=records,
    )


def _fed_cre_high_growth_deposit_records(html_text: str) -> list[dict[str, str]]:
    text = _plain_text(html_text)
    missing = [
        marker
        for marker in (
            *FED_CRE_HIGH_GROWTH_EXPECTED_FIGURES,
            *FED_CRE_HIGH_GROWTH_EXPECTED_MARKERS,
        )
        if marker not in text
    ]
    if missing:
        raise ValueError(
            "Fed CRE high-growth/deposit page missing expected markers: "
            + "; ".join(missing)
        )
    figure_specs = [
        {
            "metric": "cre_origination_index_high_growth_bank_context",
            "figure": "Figure 1. CRE Origination Index",
            "metric_label": "high_growth_regional_small_bank_cre_origination_index",
            "metric_value": "9.5_peak_2022_about_7.5_by_2024",
            "metric_unit": "index_average_2015_2016_equals_1_accessible_approximation",
            "evidence_family": "cre_origination_growth_context",
            "source_marker": "Source: CRE Public Records and FR Y-14Q",
        },
        {
            "metric": "cre_high_growth_bank_origination_share_context",
            "figure": "Figure 2. Relative Importance of High-Growth Banks",
            "metric_label": "cre_origination_share_by_high_growth_banks",
            "metric_value": "about_39_by_2024",
            "metric_unit": "percent_accessible_approximation",
            "evidence_family": "cre_lender_exposure_context",
            "source_marker": "Source: CRE Public Records, FR Y-9C, and Call Reports",
        },
        {
            "metric": "cre_high_growth_bank_construction_share_context",
            "figure": "Figure 3. Portfolio Composition of CRE Loan Types",
            "metric_label": "construction_share_high_growth_banks",
            "metric_value": "about_40_by_2024",
            "metric_unit": "percent_of_originations_accessible_approximation",
            "evidence_family": "cre_property_type_exposure_context",
            "source_marker": "Source: CRE Public Records",
        },
        {
            "metric": "cre_bank_cbsa_loan_growth_other_high_local_deposit_share",
            "figure": "Figure 4. CRE Loan Growth and Deposit Funding Share in the Same CBSA",
            "metric_label": "other_banks_high_local_deposit_share",
            "metric_value": "12",
            "metric_unit": "percent_accessible_bar_label",
            "evidence_family": "cre_local_deposit_funding_context",
            "source_marker": "Source: Summary of Deposits and CRE Public Records",
        },
        {
            "metric": "cre_bank_cbsa_loan_growth_other_low_local_deposit_share",
            "figure": "Figure 4. CRE Loan Growth and Deposit Funding Share in the Same CBSA",
            "metric_label": "other_banks_low_local_deposit_share",
            "metric_value": "17",
            "metric_unit": "percent_accessible_bar_label",
            "evidence_family": "cre_local_deposit_funding_context",
            "source_marker": "Source: Summary of Deposits and CRE Public Records",
        },
        {
            "metric": "cre_bank_cbsa_loan_growth_other_zero_local_deposit_share",
            "figure": "Figure 4. CRE Loan Growth and Deposit Funding Share in the Same CBSA",
            "metric_label": "other_banks_zero_local_deposit_share",
            "metric_value": "14",
            "metric_unit": "percent_accessible_bar_label",
            "evidence_family": "cre_local_deposit_funding_context",
            "source_marker": "Source: Summary of Deposits and CRE Public Records",
        },
        {
            "metric": "cre_bank_cbsa_loan_growth_high_growth_high_local_deposit_share",
            "figure": "Figure 4. CRE Loan Growth and Deposit Funding Share in the Same CBSA",
            "metric_label": "high_growth_banks_high_local_deposit_share",
            "metric_value": "33",
            "metric_unit": "percent_accessible_bar_label",
            "evidence_family": "cre_local_deposit_funding_context",
            "source_marker": "Source: Summary of Deposits and CRE Public Records",
        },
        {
            "metric": "cre_bank_cbsa_loan_growth_high_growth_low_local_deposit_share",
            "figure": "Figure 4. CRE Loan Growth and Deposit Funding Share in the Same CBSA",
            "metric_label": "high_growth_banks_low_local_deposit_share",
            "metric_value": "25",
            "metric_unit": "percent_accessible_bar_label",
            "evidence_family": "cre_local_deposit_funding_context",
            "source_marker": "Source: Summary of Deposits and CRE Public Records",
        },
        {
            "metric": "cre_bank_cbsa_loan_growth_high_growth_zero_local_deposit_share",
            "figure": "Figure 4. CRE Loan Growth and Deposit Funding Share in the Same CBSA",
            "metric_label": "high_growth_banks_zero_local_deposit_share",
            "metric_value": "11",
            "metric_unit": "percent_accessible_bar_label",
            "evidence_family": "cre_local_deposit_funding_context",
            "source_marker": "Source: Summary of Deposits and CRE Public Records",
        },
    ]
    records: list[dict[str, str]] = []
    for source_index, spec in enumerate(figure_specs, start=1):
        records.append(
            {
                "date": "2026-05-01",
                "publication_date": "2026-05-01",
                "source_figure": spec["figure"],
                "source_record_index_one_based": str(source_index),
                "metric": spec["metric"],
                "metric_label": spec["metric_label"],
                "metric_value": spec["metric_value"],
                "metric_unit": spec["metric_unit"],
                "evidence_family": spec["evidence_family"],
                "source_marker": spec["source_marker"],
                "source_page_schema_reviewed": "true",
                "cre_lender_exposure_context_available": str(
                    spec["evidence_family"]
                    in {
                        "cre_lender_exposure_context",
                        "cre_origination_growth_context",
                    }
                ).lower(),
                "cre_public_records_context_available": "true",
                "call_report_or_y14_context_available": str(
                    spec["source_marker"]
                    in {
                        "Source: CRE Public Records and FR Y-14Q",
                        "Source: CRE Public Records, FR Y-9C, and Call Reports",
                    }
                ).lower(),
                "local_deposit_funding_context_available": str(
                    spec["evidence_family"] == "cre_local_deposit_funding_context"
                ).lower(),
                "cre_dscr_noi_cap_rate_context_available": "false",
                "cre_refinancing_outcome_available": "false",
                "cre_real_activity_mapping_available": "false",
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    return records


def _fed_cre_high_growth_deposit_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[FED_CRE_HIGH_GROWTH_DEPOSIT_SERIES_ID]
    html_text = _fetch_text(series.endpoint)
    records = _fed_cre_high_growth_deposit_records(html_text)
    html_hash = hashlib.sha256(html_text.encode("utf-8")).hexdigest()
    records_hash = _records_sha256(records)
    note = (
        "fed_cre_high_growth_deposit_accessible_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "source_figures=Figure 1-Figure 4 accessible descriptions;"
        "cre_lender_exposure_context_available=true;"
        "cre_public_records_context_available=true;"
        "call_report_or_y14_context_available=true;"
        "local_deposit_funding_context_available=true;"
        "cre_dscr_noi_cap_rate_context_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2026-05-01",
            snapshot_kind="live_accessible_text_context",
            note=note,
        ),
        records=records,
    )


def _atlanta_fed_cremi_longweights_records(
    csv_text: str, page_html: str
) -> list[dict[str, str]]:
    page_text = _plain_text(page_html)
    missing_markers = [
        marker
        for marker in ATLANTA_FED_CREMI_REQUIRED_PAGE_MARKERS
        if marker not in page_text
    ]
    if missing_markers:
        raise ValueError(
            "Atlanta Fed CREMI page missing expected markers: "
            + "; ".join(missing_markers)
        )
    reader = csv.DictReader(io.StringIO(csv_text))
    required_columns = {
        "Geography.Name",
        "CBSA.Code",
        "Asset_Type",
        "variable",
        "value",
    }
    if reader.fieldnames is None:
        raise ValueError("Atlanta Fed CREMI long-weight CSV had no header")
    missing_columns = required_columns - set(reader.fieldnames)
    if missing_columns:
        raise ValueError(
            "Atlanta Fed CREMI long-weight CSV missing required columns: "
            + ",".join(sorted(missing_columns))
        )
    records: list[dict[str, str]] = []
    for row_index, row in enumerate(reader, start=1):
        variable = row["variable"].strip()
        weight = row["value"].strip()
        try:
            float(weight)
        except ValueError as exc:
            raise ValueError(
                f"Atlanta Fed CREMI long-weight row {row_index} has "
                f"non-numeric value: {weight!r}"
            ) from exc
        evidence_family = {
            "NOI.Index": "cre_noi_context",
            "Market.Cap.Rate": "cre_cap_rate_context",
            "Asset.Value": "cre_asset_value_context",
            "Occupancy.Rate": "cre_occupancy_context",
        }.get(variable, "cremi_input_weight_context")
        records.append(
            {
                "date": "2025-12-31",
                "source_record_index_one_based": str(row_index),
                "cbsa_name": row["Geography.Name"].strip(),
                "cbsa_code": row["CBSA.Code"].strip(),
                "asset_type": row["Asset_Type"].strip(),
                "cremi_input_variable": variable,
                "long_weight_percent": weight,
                "metric_unit": "percent_of_total_squared_coefficients",
                "evidence_family": evidence_family,
                "source_csv_schema_reviewed": "true",
                "source_page_marker_reviewed": "true",
                "cre_noi_context_available": str(variable == "NOI.Index").lower(),
                "cre_cap_rate_context_available": str(
                    variable == "Market.Cap.Rate"
                ).lower(),
                "cre_asset_value_context_available": str(
                    variable == "Asset.Value"
                ).lower(),
                "cre_occupancy_context_available": str(
                    variable == "Occupancy.Rate"
                ).lower(),
                "raw_noi_cap_rate_asset_value_source_publicly_shareable": "false",
                "cre_dscr_context_available": "false",
                "cre_refinancing_outcome_available": "false",
                "cre_real_activity_mapping_available": "false",
                "denominator_prior_narrowing_allowed": "false",
                "split_denominator_promotion_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
                "method_blocker": (
                    "atlanta_fed_cremi_long_weights_identify_noi_cap_rate_"
                    "asset_value_input_roles_but_raw_cre_input_data_are_not_"
                    "publicly_shareable_and_no_dscr_refinancing_outcome_or_"
                    "real_activity_bridge_is_admitted"
                ),
            }
        )
    variables = {record["cremi_input_variable"] for record in records}
    required_variables = {"NOI.Index", "Market.Cap.Rate", "Asset.Value"}
    missing_variables = required_variables - variables
    if missing_variables:
        raise ValueError(
            "Atlanta Fed CREMI long-weight CSV missing required variables: "
            + ",".join(sorted(missing_variables))
        )
    return records


def _atlanta_fed_cremi_longweights_snapshot(
    *,
    registry: SourceRegistry,
    source_csv: Path,
    source_page: Path,
) -> SourceSnapshot:
    series = registry.series[ATLANTA_FED_CREMI_LONGWEIGHTS_SERIES_ID]
    if not source_csv.exists():
        _download_source(series.endpoint, source_csv)
    if not source_page.exists():
        _download_source(ATLANTA_FED_CREMI_PAGE_URL, source_page)
    csv_text = source_csv.read_text(encoding="utf-8-sig")
    page_html = source_page.read_text(encoding="utf-8", errors="replace")
    records = _atlanta_fed_cremi_longweights_records(csv_text, page_html)
    csv_hash = _file_sha256(source_csv)
    page_hash = _file_sha256(source_page)
    records_hash = _records_sha256(records)
    variables = sorted({record["cremi_input_variable"] for record in records})
    asset_types = sorted({record["asset_type"] for record in records})
    note = (
        "atlanta_fed_cremi_longweights_context_only;"
        f"source_csv_sha256={csv_hash};"
        f"source_page_html_sha256={page_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "first_observation_date=2025-12-31;"
        "latest_observation_date=2025-12-31;"
        f"asset_type_count={len(asset_types)};"
        f"cremi_input_variable_count={len(variables)};"
        "noi_cap_rate_asset_value_input_roles_available=true;"
        "raw_noi_cap_rate_asset_value_source_publicly_shareable=false;"
        "cre_dscr_context_available=false;"
        "cre_refinancing_outcome_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2025-12-31",
            snapshot_kind="live_csv_and_html_context",
            note=note,
        ),
        records=records,
    )


def _fed_cre_evergreening_extension_terms_records(
    html_text: str, pdf_text: str
) -> list[dict[str, str]]:
    source_text = re.sub(
        r"\s+",
        " ",
        f"{_plain_text(html_text)} {pdf_text}",
    ).strip()
    source_text_lower = source_text.lower()
    marker_checks = {
        "title": "pretend or amend? on evergreening in cre",
        "supervisory_data": "detailed supervisory data",
        "debt_yield": "debt yield",
        "net_operating_income": "net operating income",
        "principal_paydown": "principal paydown",
        "maturity_extensions": "maturity extensions",
        "higher_spreads": "higher loan spreads",
    }
    missing_markers = [
        name
        for name, marker in marker_checks.items()
        if marker not in source_text_lower
    ]
    if missing_markers:
        raise ValueError(
            "Fed CRE evergreening paper missing expected markers: "
            + "; ".join(missing_markers)
        )
    base_record = {
        "date": "2026-05-01",
        "source_html_schema_reviewed": "true",
        "source_pdf_text_reviewed": "true",
        "underlying_supervisory_data_publicly_reusable": "false",
        "cre_dscr_context_available": "false",
        "cre_real_activity_mapping_available": "false",
        "denominator_prior_narrowing_allowed": "false",
        "split_denominator_promotion_allowed": "false",
        "formula_replacement_allowed": "false",
        "main_ratio_admission_allowed": "false",
        "incidence_output_enabled": "false",
        "welfare_tax_mpc_output_enabled": "false",
        "method_blocker": (
            "fed_feds_2026_025_cre_extension_terms_use_detailed_supervisory_"
            "data_not_public_reusable_and_no_public_dscr_or_real_activity_"
            "bridge_is_admitted"
        ),
    }
    rows = [
        {
            "metric": "cre_supervisory_data_refinancing_context",
            "metric_unit": "research_context_marker",
            "evidence_family": "cre_supervisory_refinancing_context",
            "source_marker": "detailed_supervisory_data",
            "cre_refinancing_extension_outcome_context_available": "true",
            "cre_noi_debt_yield_context_available": "false",
            "cre_principal_paydown_extension_terms_context_available": "false",
            "cre_higher_spread_guarantee_extension_terms_context_available": "false",
        },
        {
            "metric": "cre_debt_yield_noi_extension_context",
            "metric_unit": "research_context_marker",
            "evidence_family": "cre_noi_debt_yield_context",
            "source_marker": "debt_yield_net_operating_income",
            "cre_refinancing_extension_outcome_context_available": "true",
            "cre_noi_debt_yield_context_available": "true",
            "cre_principal_paydown_extension_terms_context_available": "false",
            "cre_higher_spread_guarantee_extension_terms_context_available": "false",
        },
        {
            "metric": "cre_maturity_extension_context",
            "metric_unit": "research_context_marker",
            "evidence_family": "cre_refinancing_extension_context",
            "source_marker": "maturity_extensions",
            "cre_refinancing_extension_outcome_context_available": "true",
            "cre_noi_debt_yield_context_available": "false",
            "cre_principal_paydown_extension_terms_context_available": "false",
            "cre_higher_spread_guarantee_extension_terms_context_available": "false",
        },
        {
            "metric": "cre_principal_paydown_extension_terms_context",
            "metric_unit": "research_context_marker",
            "evidence_family": "cre_extension_terms_context",
            "source_marker": "principal_paydown",
            "cre_refinancing_extension_outcome_context_available": "true",
            "cre_noi_debt_yield_context_available": "false",
            "cre_principal_paydown_extension_terms_context_available": "true",
            "cre_higher_spread_guarantee_extension_terms_context_available": "false",
        },
        {
            "metric": "cre_higher_spread_guarantee_extension_terms_context",
            "metric_unit": "research_context_marker",
            "evidence_family": "cre_extension_terms_context",
            "source_marker": "higher_spreads_and_guarantees",
            "cre_refinancing_extension_outcome_context_available": "true",
            "cre_noi_debt_yield_context_available": "false",
            "cre_principal_paydown_extension_terms_context_available": "false",
            "cre_higher_spread_guarantee_extension_terms_context_available": "true",
        },
        {
            "metric": "cre_public_reuse_and_real_activity_blocker",
            "metric_unit": "method_blocker",
            "evidence_family": "cre_promotion_blocker",
            "source_marker": "underlying_supervisory_data_not_public_reusable",
            "cre_refinancing_extension_outcome_context_available": "false",
            "cre_noi_debt_yield_context_available": "false",
            "cre_principal_paydown_extension_terms_context_available": "false",
            "cre_higher_spread_guarantee_extension_terms_context_available": "false",
        },
    ]
    return [
        {
            **base_record,
            **row,
            "source_record_index_one_based": str(row_index),
        }
        for row_index, row in enumerate(rows, start=1)
    ]


def _fed_cre_evergreening_extension_terms_snapshot(
    *,
    registry: SourceRegistry,
    source_html: Path,
    source_pdf: Path,
) -> SourceSnapshot:
    series = registry.series[FED_CRE_EVERGREENING_EXTENSION_TERMS_SERIES_ID]
    if not source_html.exists():
        _download_source(series.endpoint, source_html)
    if not source_pdf.exists():
        _download_source(FED_CRE_EVERGREENING_EXTENSION_TERMS_PDF_URL, source_pdf)
    html_text = source_html.read_text(encoding="utf-8", errors="replace")
    pdf_text = _pdf_text(source_pdf)
    records = _fed_cre_evergreening_extension_terms_records(html_text, pdf_text)
    html_hash = _file_sha256(source_html)
    pdf_hash = _file_sha256(source_pdf)
    records_hash = _records_sha256(records)
    note = (
        "fed_cre_evergreening_extension_terms_context_only;"
        f"source_html_sha256={html_hash};"
        f"source_pdf_sha256={pdf_hash};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        "first_observation_date=2026-05-01;"
        "latest_observation_date=2026-05-01;"
        "cre_extension_terms_context_available=true;"
        "cre_noi_debt_yield_context_available=true;"
        "cre_principal_paydown_extension_terms_context_available=true;"
        "cre_higher_spread_guarantee_extension_terms_context_available=true;"
        "underlying_supervisory_data_publicly_reusable=false;"
        "cre_dscr_context_available=false;"
        "cre_real_activity_mapping_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2026-05-01",
            snapshot_kind="live_html_pdf_research_context",
            note=note,
        ),
        records=records,
    )


def _cfpb_mem_sample1_public_use_records(path: Path) -> list[dict[str, str]]:
    required_members = {
        CFPB_MEM_SAMPLE1_CSV,
        CFPB_MEM_SAMPLE1_CODEBOOK,
        CFPB_MEM_SAMPLE1_README,
        CFPB_MEM_SAMPLE1_USER_GUIDE,
    }
    required_columns = {
        "ID",
        "w1weight",
        "w2weight",
        "w3weight",
        "w321weight",
        "w1q9",
        "w1q15",
        "w1q21",
        "w1q25",
        "w1q29",
        "w1q30",
        "w1q38",
        "w1q39",
        "w1q40a",
        "w1q53",
        "w1q55",
        "w1q58",
        "w1q60",
        "w1q67c",
        "w1q67d",
        "w1q67j",
    }
    with zipfile.ZipFile(path) as archive:
        members = set(archive.namelist())
        missing_members = required_members - members
        if missing_members:
            raise ValueError(
                f"{path} missing CFPB MEM files: {', '.join(sorted(missing_members))}"
            )
        codebook = archive.read(CFPB_MEM_SAMPLE1_CODEBOOK).decode(
            "utf-8", errors="replace"
        )
        with archive.open(CFPB_MEM_SAMPLE1_CSV) as handle:
            reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8-sig"))
            if not reader.fieldnames:
                raise ValueError(f"{path} missing CFPB MEM CSV header")
            columns = set(reader.fieldnames)
            missing_columns = required_columns - columns
            if missing_columns:
                raise ValueError(
                    f"{path} missing CFPB MEM columns: "
                    f"{', '.join(sorted(missing_columns))}"
                )
            row_count = sum(1 for _ in reader)
        csv_hash = hashlib.sha256(archive.read(CFPB_MEM_SAMPLE1_CSV)).hexdigest()
        codebook_hash = hashlib.sha256(
            archive.read(CFPB_MEM_SAMPLE1_CODEBOOK)
        ).hexdigest()
    marker_status = {
        category: all(marker in codebook for marker in markers)
        for category, markers in CFPB_MEM_SAMPLE1_REQUIRED_MARKERS.items()
    }
    missing_marker_categories = [
        category for category, passed in marker_status.items() if not passed
    ]
    if missing_marker_categories:
        raise ValueError(
            f"{path} missing CFPB MEM codebook markers for: "
            f"{', '.join(sorted(missing_marker_categories))}"
        )
    return [
        {
            "date": "2021-02-01",
            "sample_id": "sample_1_waves_1_2_3",
            "survey_wave_start": "2019-05-01",
            "survey_wave_latest": "2021-02-01",
            "survey_wave_count": "3",
            "source_csv_row_count": str(row_count),
            "source_csv_column_count": str(len(columns)),
            "source_zip_member_count": str(len(members)),
            "source_csv_sha256": csv_hash,
            "source_codebook_sha256": codebook_hash,
            "source_csv_member": CFPB_MEM_SAMPLE1_CSV,
            "source_codebook_member": CFPB_MEM_SAMPLE1_CODEBOOK,
            "source_schema_reviewed": "true",
            "required_columns_present": "true",
            "codebook_marker_reviewed": "true",
            "borrower_level_public_survey_microdata_available": "true",
            "borrower_level_credit_bureau_microdata_available": "false",
            "credit_card_payment_behavior_context_available": "true",
            "liquidity_context_available": "true",
            "bill_payment_stress_context_available": "true",
            "income_context_available": "true",
            "credit_score_self_report_context_available": "true",
            "minimum_payment_behavior_context_available": "false",
            "rate_sensitive_payment_drag_transmission_available": "false",
            "current_demand_conversion_available": "false",
            "denominator_prior_narrowing_allowed": "false",
            "split_denominator_promotion_allowed": "false",
            "formula_replacement_allowed": "false",
            "main_ratio_admission_allowed": "false",
            "incidence_output_enabled": "false",
            "welfare_tax_mpc_output_enabled": "false",
        }
    ]


def _cfpb_mem_sample1_public_use_snapshot(
    *, registry: SourceRegistry, source_zip: Path
) -> SourceSnapshot:
    series = registry.series[CFPB_MEM_SAMPLE1_SERIES_ID]
    if not source_zip.exists():
        _download_source(series.endpoint, source_zip)
    records = _cfpb_mem_sample1_public_use_records(source_zip)
    zip_hash = _file_sha256(source_zip)
    records_hash = _records_sha256(records)
    record = records[0]
    note = (
        "cfpb_mem_public_use_borrower_liquidity_payment_context_only;"
        f"source_zip_sha256={zip_hash};"
        f"source_csv_sha256={record['source_csv_sha256']};"
        f"source_codebook_sha256={record['source_codebook_sha256']};"
        f"source_records_sha256={records_hash};"
        f"source_record_count={record['source_csv_row_count']};"
        f"source_column_count={record['source_csv_column_count']};"
        "survey_wave_start=2019-05-01;"
        "survey_wave_latest=2021-02-01;"
        "survey_wave_count=3;"
        "schema=public_use_respondent_rows_with_weights_credit_card_balance_"
        "liquidity_bill_stress_income_and_credit_score_self_report_fields;"
        "borrower_level_public_survey_microdata_available=true;"
        "borrower_level_credit_bureau_microdata_available=false;"
        "credit_card_payment_behavior_context_available=true;"
        "liquidity_context_available=true;"
        "bill_payment_stress_context_available=true;"
        "minimum_payment_behavior_context_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2021-02-01",
            snapshot_kind="live_zip_csv_public_use_context",
            note=note,
        ),
        records=records,
    )


def _cfpb_mem_multisample_members(sample: int) -> dict[str, str]:
    prefix = f"Sample{sample}/"
    codebook = {
        3: "MEM_S3W1W2_PUF_codebook.txt",
        4: "MEM_S4W1W2_PUF_codebook.txt",
        5: "MEM_S5W1W2PUF_codebook.txt",
        6: "MEM_S6W1PUF_codebook.txt",
    }[sample]
    csv_name = {
        3: "MEM_S3W1W2_PUF.csv",
        4: "MEM_S4W1W2_PUF.csv",
        5: "MEM_S5W1W2_PUF.csv",
        6: "MEM_S6W_PUF.csv",
    }[sample]
    return {
        "csv": f"{prefix}{csv_name}",
        "codebook": f"{prefix}{codebook}",
        "readme": f"{prefix}README.txt",
        "user_guide": f"{prefix}MEM PUF User Guide.pdf",
    }


def _cfpb_mem_multisample_wave_window(sample: int) -> tuple[str, str, str]:
    return {
        3: ("2022-01-01", "2023-01-01", "2"),
        4: ("2023-01-01", "2024-01-01", "2"),
        5: ("2024-01-01", "2025-01-01", "2"),
        6: ("2025-01-01", "2025-01-01", "1"),
    }[sample]


def _cfpb_mem_multisample_public_use_records(
    sample_zips: Mapping[int, Path],
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for sample in sorted(sample_zips):
        path = sample_zips[sample]
        members = _cfpb_mem_multisample_members(sample)
        required_members = set(members.values())
        with zipfile.ZipFile(path) as archive:
            archive_members = set(archive.namelist())
            missing_members = required_members - archive_members
            if missing_members:
                raise ValueError(
                    f"{path} missing CFPB MEM sample {sample} files: "
                    f"{', '.join(sorted(missing_members))}"
                )
            csv_bytes = archive.read(members["csv"])
            codebook_bytes = archive.read(members["codebook"])
            codebook = codebook_bytes.decode("utf-8", errors="replace")
            with archive.open(members["csv"]) as handle:
                reader = csv.DictReader(io.TextIOWrapper(handle, encoding="utf-8-sig"))
                if not reader.fieldnames:
                    raise ValueError(f"{path} missing CFPB MEM sample CSV header")
                columns = set(reader.fieldnames)
                if "ID" not in columns:
                    raise ValueError(f"{path} missing CFPB MEM sample ID column")
                weight_columns = sorted(
                    column for column in columns if "weight" in column.lower()
                )
                if not weight_columns:
                    raise ValueError(f"{path} missing CFPB MEM sample weight columns")
                row_count = sum(1 for _ in reader)
        codebook_lower = codebook.lower()
        category_status = {
            category: all(marker in codebook_lower for marker in markers)
            for category, markers in CFPB_MEM_MULTISAMPLE_CATEGORY_MARKERS.items()
        }
        required_categories = {
            "credit_card_payment_behavior",
            "liquidity",
            "bill_payment_stress",
            "income_context",
        }
        missing_categories = [
            category
            for category in sorted(required_categories)
            if not category_status.get(category)
        ]
        if missing_categories:
            raise ValueError(
                f"{path} missing CFPB MEM sample {sample} harmonized categories: "
                f"{', '.join(missing_categories)}"
            )
        wave_start, wave_latest, wave_count = _cfpb_mem_multisample_wave_window(sample)
        records.append(
            {
                "date": wave_latest,
                "sample_id": f"sample_{sample}",
                "survey_wave_start": wave_start,
                "survey_wave_latest": wave_latest,
                "survey_wave_count": wave_count,
                "source_csv_row_count": str(row_count),
                "source_csv_column_count": str(len(columns)),
                "source_zip_member_count": str(len(archive_members)),
                "source_zip_sha256": _file_sha256(path),
                "source_csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
                "source_codebook_sha256": hashlib.sha256(codebook_bytes).hexdigest(),
                "source_csv_member": members["csv"],
                "source_codebook_member": members["codebook"],
                "source_schema_reviewed": "true",
                "id_column_present": "true",
                "weight_columns_present": "true",
                "weight_columns": ";".join(weight_columns),
                "harmonized_context_reviewed": "true",
                "borrower_level_public_survey_microdata_available": "true",
                "borrower_level_credit_bureau_microdata_available": "false",
                "credit_card_payment_behavior_context_available": str(
                    category_status["credit_card_payment_behavior"]
                ).lower(),
                "liquidity_context_available": str(
                    category_status["liquidity"]
                ).lower(),
                "bill_payment_stress_context_available": str(
                    category_status["bill_payment_stress"]
                ).lower(),
                "income_context_available": str(
                    category_status["income_context"]
                ).lower(),
                "unexpected_expense_context_available": str(
                    category_status["unexpected_expense_context"]
                ).lower(),
                "credit_score_self_report_context_available": str(
                    "credit score" in codebook_lower
                ).lower(),
                "minimum_payment_behavior_context_available": "false",
                "rate_sensitive_payment_drag_transmission_available": "false",
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


def _cfpb_mem_samples_3_6_public_use_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[CFPB_MEM_SAMPLES_3_6_SERIES_ID]
    source_zips: dict[int, Path] = {}
    sample_urls: dict[int, str] = {}
    for sample, (url, path) in CFPB_MEM_SAMPLES_3_6_DEFAULTS.items():
        if not path.exists():
            _download_source(url, path)
        source_zips[sample] = path
        sample_urls[sample] = url
    records = _cfpb_mem_multisample_public_use_records(source_zips)
    records_hash = _records_sha256(records)
    total_rows = sum(int(record["source_csv_row_count"]) for record in records)
    first_wave = min(record["survey_wave_start"] for record in records)
    latest_wave = max(record["survey_wave_latest"] for record in records)
    sample_ids = ",".join(record["sample_id"] for record in records)
    zip_hashes = ";".join(
        f"{record['sample_id']}:{record['source_zip_sha256']}" for record in records
    )
    row_counts = ";".join(
        f"{record['sample_id']}:{record['source_csv_row_count']}" for record in records
    )
    column_counts = ";".join(
        f"{record['sample_id']}:{record['source_csv_column_count']}"
        for record in records
    )
    urls = ";".join(
        f"sample_{sample}:{url}" for sample, url in sorted(sample_urls.items())
    )
    note = (
        "cfpb_mem_samples_3_6_public_use_multisample_harmonized_context_only;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"underlying_public_use_row_count={total_rows};"
        f"sample_ids={sample_ids};"
        f"sample_source_urls={urls};"
        f"sample_zip_sha256={zip_hashes};"
        f"sample_row_counts={row_counts};"
        f"sample_column_counts={column_counts};"
        f"survey_wave_start={first_wave};"
        f"survey_wave_latest={latest_wave};"
        "schema=sample_level_public_use_csv_with_id_weights_codebook_and_"
        "harmonized_credit_card_liquidity_bill_stress_income_context_flags;"
        "borrower_level_public_survey_microdata_available=true;"
        "borrower_level_credit_bureau_microdata_available=false;"
        "credit_card_payment_behavior_context_available=true;"
        "liquidity_context_available=true;"
        "bill_payment_stress_context_available=true;"
        "minimum_payment_behavior_context_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at=latest_wave,
            snapshot_kind="live_zip_csv_multisample_public_use_context",
            note=note,
        ),
        records=records,
    )


def _philadelphia_fed_y14_credit_card_records(
    *,
    balances_csv: Path,
    originations_csv: Path,
) -> list[dict[str, str]]:
    balances_hash = _file_sha256(balances_csv)
    originations_hash = _file_sha256(originations_csv)
    records: list[dict[str, str]] = []

    with balances_csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = tuple(reader.fieldnames or ())
        missing = [
            column
            for column in PHILLY_FED_Y14_BALANCES_REQUIRED_COLUMNS
            if column not in headers
        ]
        if missing:
            raise ValueError(
                "Philadelphia Fed Y-14 credit-card balances CSV missing "
                "required columns: " + "; ".join(missing)
            )
        balance_rows = [row for row in reader if _is_quarter_label(row.get("YRQTR"))]
    with originations_csv.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = tuple(reader.fieldnames or ())
        missing = [
            column
            for column in PHILLY_FED_Y14_ORIGINATION_REQUIRED_COLUMNS
            if column not in headers
        ]
        if missing:
            raise ValueError(
                "Philadelphia Fed Y-14 credit-card origination CSV missing "
                "required columns: " + "; ".join(missing)
            )
        origination_rows = [
            row for row in reader if _is_quarter_label(row.get("YRQTR"))
        ]

    for row in balance_rows:
        records.append(
            {
                "date": _quarter_end_date(row["YRQTR"]),
                "quarter": row["YRQTR"],
                "source_table": "credit_card_balances",
                "source_csv_sha256": balances_hash,
                "source_csv_row_count": str(len(balance_rows)),
                "source_csv_column_count": str(len(row)),
                "total_balances_bil": _clean_published_number(
                    row["Total Balances ($Billions)"]
                ),
                "number_of_accounts_mil": _clean_published_number(
                    row["Number of Accounts (Millions)"]
                ),
                "share_accounts_minimum_payment_pct": _clean_published_number(
                    row["Share of Accounts Making the Minimum Payment"]
                ),
                "share_accounts_above_min_below_full_pct": (
                    _clean_published_number(
                        row[
                            "Share of Accounts Making Greater Than the Minimum "
                            "Payment but Less Than the Full Balance"
                        ]
                    )
                ),
                "share_accounts_full_balance_payment_pct": (
                    _clean_published_number(
                        row["Share of Accounts Making the Full Balance Payment"]
                    )
                ),
                "revolving_balances_bil": _clean_published_number(
                    row["Revolving Balances Only ($Billions)"]
                ),
                "average_purchase_apr_general_purpose_pct": (
                    _clean_published_number(
                        row["Average Purchase APR: General Purpose"]
                    )
                ),
                "average_purchase_apr_private_label_pct": _clean_published_number(
                    row["Average Purchase APR: Private Label"]
                ),
                "total_purchase_volume_bil": _clean_published_number(
                    row["Total Purchase Volume ($Billions)"]
                ),
                "average_purchase_volume_credit_score_lt660": (
                    _clean_published_number(
                        row[
                            "Average Purchase Volume by Credit Score Group: "
                            "<660 Credit Score"
                        ]
                    )
                ),
                "average_purchase_volume_credit_score_660_719": (
                    _clean_published_number(
                        row[
                            "Average Purchase Volume by Credit Score Group: "
                            "660-719 Credit Score"
                        ]
                    )
                ),
                "average_purchase_volume_credit_score_ge720": (
                    _clean_published_number(
                        row[
                            "Average Purchase Volume by Credit Score Group: "
                            ">=720 Credit Score"
                        ]
                    )
                ),
                "public_aggregate_large_bank_y14m_context_available": "true",
                "payment_behavior_context_available": "true",
                "purchase_volume_context_available": "true",
                "purchase_apr_context_available": "true",
                "borrower_level_credit_bureau_microdata_available": "false",
                "rate_sensitive_payment_drag_transmission_available": "false",
                "current_demand_response_available": "false",
                "split_denominator_promotion_allowed": "false",
                "denominator_prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    for row in origination_rows:
        records.append(
            {
                "date": _quarter_end_date(row["YRQTR"]),
                "quarter": row["YRQTR"],
                "source_table": "credit_card_originations",
                "source_csv_sha256": originations_hash,
                "source_csv_row_count": str(len(origination_rows)),
                "source_csv_column_count": str(len(row)),
                "new_originations_bil": _clean_published_number(
                    row["New Originations ($Billions)"]
                ),
                "number_of_new_accounts_mil": _clean_published_number(
                    row["Number of New Accounts (Millions)"]
                ),
                "original_credit_score_p50": _clean_published_number(
                    row["Original Credit Score (50th percentile)"]
                ),
                "average_original_purchase_apr_general_purpose_pct": (
                    _clean_published_number(
                        row["Average Original Purchase APR: General Purpose"]
                    )
                ),
                "average_original_purchase_apr_private_label_pct": (
                    _clean_published_number(
                        row["Average Original Purchase APR: Private Label"]
                    )
                ),
                "new_accounts_credit_score_lt660_pct": _clean_published_number(
                    row["Percentage of New Accounts with <660 Credit Score"]
                ),
                "new_commitments_credit_score_lt660_pct": _clean_published_number(
                    row["Percentage of New Commitments with <660 Credit Score"]
                ),
                "public_aggregate_large_bank_y14m_context_available": "true",
                "payment_behavior_context_available": "false",
                "purchase_volume_context_available": "false",
                "purchase_apr_context_available": "true",
                "origination_context_available": "true",
                "borrower_level_credit_bureau_microdata_available": "false",
                "rate_sensitive_payment_drag_transmission_available": "false",
                "current_demand_response_available": "false",
                "split_denominator_promotion_allowed": "false",
                "denominator_prior_narrowing_allowed": "false",
                "formula_replacement_allowed": "false",
                "main_ratio_admission_allowed": "false",
                "incidence_output_enabled": "false",
                "welfare_tax_mpc_output_enabled": "false",
            }
        )
    return records


def _philadelphia_fed_y14_credit_card_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[PHILLY_FED_Y14_CREDIT_CARD_SERIES_ID]
    for url, path in (
        (
            PHILLY_FED_Y14_CREDIT_CARD_BALANCES_URL,
            PHILLY_FED_Y14_CREDIT_CARD_BALANCES_DEFAULT,
        ),
        (
            PHILLY_FED_Y14_CREDIT_CARD_ORIGINATION_URL,
            PHILLY_FED_Y14_CREDIT_CARD_ORIGINATION_DEFAULT,
        ),
    ):
        if not path.exists():
            _download_source(url, path)
    definitions_html = _fetch_text(PHILLY_FED_Y14_DEFINITIONS_URL)
    methodology_html = _fetch_text(PHILLY_FED_Y14_METHODOLOGY_URL)
    methodology_text = _plain_text(methodology_html)
    for marker in (
        "FR Y-14M",
        "credit card data",
        "roughly four-fifths of total U.S. bank card balances",
    ):
        if marker not in methodology_text:
            raise ValueError(f"Philadelphia Fed Y-14 methodology missing {marker!r}")
    definitions_text = _plain_text(definitions_html)
    for marker in (
        "Credit Card Balances: Payment Behavior",
        "Credit Card Balances: Total Purchase Volume",
        "Credit Card Originations",
    ):
        if marker not in definitions_text:
            raise ValueError(f"Philadelphia Fed Y-14 definitions missing {marker!r}")

    records = _philadelphia_fed_y14_credit_card_records(
        balances_csv=PHILLY_FED_Y14_CREDIT_CARD_BALANCES_DEFAULT,
        originations_csv=PHILLY_FED_Y14_CREDIT_CARD_ORIGINATION_DEFAULT,
    )
    first_date = min(record["date"] for record in records)
    latest_date = max(record["date"] for record in records)
    balance_rows = [
        record for record in records if record["source_table"] == "credit_card_balances"
    ]
    origination_rows = [
        record
        for record in records
        if record["source_table"] == "credit_card_originations"
    ]
    records_hash = _records_sha256(records)
    balance_hash = _file_sha256(PHILLY_FED_Y14_CREDIT_CARD_BALANCES_DEFAULT)
    origination_hash = _file_sha256(PHILLY_FED_Y14_CREDIT_CARD_ORIGINATION_DEFAULT)
    definitions_hash = hashlib.sha256(definitions_html.encode("utf-8")).hexdigest()
    methodology_hash = hashlib.sha256(methodology_html.encode("utf-8")).hexdigest()
    note = (
        "philadelphia_fed_y14_large_bank_credit_card_aggregate_context_only;"
        f"source_records_sha256={records_hash};"
        f"source_record_count={len(records)};"
        f"balances_csv_sha256={balance_hash};"
        f"originations_csv_sha256={origination_hash};"
        f"definitions_html_sha256={definitions_hash};"
        f"methodology_html_sha256={methodology_hash};"
        f"balances_row_count={len(balance_rows)};"
        f"originations_row_count={len(origination_rows)};"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "data_scope=public_aggregate_fr_y14m_large_bank_credit_card_data;"
        "estimated_coverage=roughly_four_fifths_total_us_bank_card_balances;"
        "payment_behavior_context_available=true;"
        "minimum_payment_context_available=true;"
        "purchase_volume_context_available=true;"
        "purchase_apr_context_available=true;"
        "origination_context_available=true;"
        "borrower_level_credit_bureau_microdata_available=false;"
        "rate_sensitive_payment_drag_transmission_available=false;"
        "current_demand_response_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2025Q4",
            snapshot_kind="live_csv_context",
            note=note,
        ),
        records=records,
    )


def _nyfed_consumer_credit_panel_faq_snapshot(
    *, registry: SourceRegistry
) -> SourceSnapshot:
    series = registry.series[NYFED_CONSUMER_CREDIT_PANEL_FAQ_SERIES_ID]
    html = _fetch_text(series.endpoint)
    text = _plain_text(html)
    missing = [
        marker
        for marker in NYFED_CONSUMER_CREDIT_PANEL_FAQ_MARKERS
        if marker not in text
    ]
    if missing:
        raise ValueError(
            "NY Fed Consumer Credit Panel FAQ missing expected markers: "
            + "; ".join(missing)
        )
    html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
    posted_date = _posted_date(text)
    records = [
        {
            "date": "guidance_page_current",
            "evidence_role": "consumer_credit_panel_access_scope_context",
            "ccp_microdata_access_limited": "true",
            "ccp_access_limitation_reason": "contractual_limitations_with_data_provider",
            "aggregate_data_bank_available": "true",
            "custom_cuts_available": "false",
            "smaller_geographic_area_available": "false",
            "transactor_revolver_split_available": "false",
            "statement_balance_scope_verified": "true",
            "source_page_posted_date": posted_date,
            "borrower_level_microdata_admitted": "false",
            "current_demand_conversion_available": "false",
            "split_denominator_promotion_allowed": "false",
            "denominator_prior_narrowing_allowed": "false",
            "formula_replacement_allowed": "false",
            "main_ratio_admission_allowed": "false",
            "incidence_output_enabled": "false",
            "welfare_tax_mpc_output_enabled": "false",
        }
    ]
    note = (
        "nyfed_consumer_credit_panel_access_scope_context_only;"
        f"source_html_sha256={html_sha};"
        f"source_record_count={len(records)};"
        f"source_page_posted_date={posted_date};"
        "ccp_microdata_access_limited=true;"
        "aggregate_data_bank_available=true;"
        "custom_cuts_available=false;"
        "transactor_revolver_split_available=false;"
        "borrower_level_microdata_admitted=false;"
        "current_demand_conversion_available=false;"
        "split_denominator_promotion_allowed=false;"
        "denominator_prior_narrowing_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at=posted_date or None,
            snapshot_kind="live_text_context",
            note=note,
        ),
        records=records,
    )


def _nyfed_household_debt_credit_report_snapshot(
    *, registry: SourceRegistry, source_workbook: Path
) -> SourceSnapshot:
    series = registry.series[NYFED_HOUSEHOLD_DEBT_CREDIT_REPORT_SERIES_ID]
    if not source_workbook.exists():
        _download_source(series.endpoint, source_workbook)
    records = _nyfed_hhdc_records(source_workbook)
    workbook_hash = _file_sha256(source_workbook)
    record_hash = _records_sha256(records)
    first_date, latest_date = _date_range(
        SourceSnapshot(
            metadata=RetrievalMetadata(
                source_id=series.source,
                series_id=series.series_id,
                source_url=series.endpoint,
                units=series.units,
                frequency=series.frequency,
                transform=series.transform,
                retrieved_at=utc_now_iso(),
                source_release_at="2026:Q1",
                snapshot_kind="live_workbook_context",
            ),
            records=records,
        )
    )
    note = (
        "nyfed_household_debt_credit_product_age_state_delinquency_context_only;"
        f"source_workbook_sha256={workbook_hash};"
        f"source_records_sha256={record_hash};"
        f"source_record_count={len(records)};"
        "source_data_sheet_count=36;"
        f"first_observation_date={first_date};"
        f"latest_observation_date={latest_date};"
        "product_balance_context_available=true;"
        "age_distribution_context_available=true;"
        "state_distribution_context_available=true;"
        "delinquency_transition_context_available=true;"
        "borrower_level_microdata_available=false;"
        "income_distribution_available=false;"
        "current_demand_conversion_available=false;"
        "denominator_prior_narrowing_allowed=false;"
        "split_denominator_promotion_allowed=false;"
        "formula_replacement_allowed=false;"
        "main_ratio_admission_allowed=false;"
        "incidence_output_enabled=false;"
        "welfare_tax_mpc_output_enabled=false"
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
            source_release_at="2026:Q1",
            snapshot_kind="live_workbook_context",
            note=note,
        ),
        records=records,
    )


def materialize(
    *,
    config: Path,
    snapshot_bundle: Path,
    output: Path,
    cfpb_credit_card_workbook: Path,
    cfpb_credit_card_market_report_pdf: Path,
    cfpb_credit_card_interest_payment_mechanics_html: Path,
    cfpb_credit_card_payment_allocation_regz_html: Path,
    cfpb_consumer_credit_trends_csv: Path,
    cfpb_consumer_credit_trends_codebook: Path,
    cfpb_tccp_survey_workbook: Path,
    cfpb_payment_amount_furnishing_pdf: Path,
    cfpb_credit_card_revolvers_pdf: Path,
    cfpb_mem_sample1_zip: Path,
    nyfed_household_debt_credit_workbook: Path,
    fed_indirect_credit_accessible_materials_zip: Path,
    fed_credit_bureau_household_dsr_accessible_html: Path,
    fed_credit_bureau_household_dsr_article_html: Path,
    fed_student_loan_payment_restart_spending_html: Path,
    fed_student_loan_payment_restart_spending_accessible_html: Path,
    fed_credit_card_limit_increase_debt_html: Path,
    fed_credit_card_limit_increase_debt_accessible_html: Path,
    fed_credit_card_profitability_html: Path,
    fed_credit_card_delinquency_prediction_html: Path,
    fed_credit_card_delinquency_prediction_accessible_html: Path,
    fed_consumer_delinquency_dynamics_html: Path,
    fed_consumer_delinquency_dynamics_accessible_html: Path,
    fed_credit_card_rewards_limit_spending_zip: Path,
    fed_auto_loan_payment_delinquency_html: Path,
    fed_auto_loan_payment_delinquency_accessible_html: Path,
    fed_auto_loan_prepayment_maturity_zip: Path,
    boston_fed_credit_card_interest_spending_html: Path,
    boston_fed_credit_card_spending_channel_wp_pdf: Path,
    atlanta_fed_cremi_longweights_csv: Path,
    atlanta_fed_cremi_page_html: Path,
    fed_cre_evergreening_extension_terms_html: Path,
    fed_cre_evergreening_extension_terms_pdf: Path,
    sec_private_fund_aggregate_assets_json: Path,
    sec_bdc_public_filing_dir: Path,
    sec_abs_ee_cmbs_filing_dir: Path,
    fed_scf_summary_extract_zip: Path,
    fed_scf_replicate_weight_zip: Path,
    fed_scf_standard_error_documentation_pdf: Path,
    fed_scf_codebook: Path,
    fed_shed_public_use_zip: Path,
    fed_shed_codebook: Path,
) -> Path:
    registry = SourceRegistry.from_path(config)
    adapter = FredAdapter(registry)
    dfa_adapter = FedDfaAdapter(registry)
    existing = read_snapshot_bundle(snapshot_bundle)
    by_series = {snapshot.metadata.series_id: snapshot for snapshot in existing}
    for series_id, context_status in HIGHER_RATE_FRED_SERIES.items():
        by_series[series_id] = _annotated_context_snapshot(
            adapter.pull_series(series_id),
            context_status=context_status,
        )
    by_series[CFPB_CREDIT_CARD_FIGURE_DATA_SERIES_ID] = (
        _cfpb_credit_card_payment_behavior_snapshot(
            registry=registry,
            source_workbook=cfpb_credit_card_workbook,
        )
    )
    by_series[CFPB_CREDIT_CARD_MARKET_REPORT_SERIES_ID] = (
        _cfpb_credit_card_market_report_snapshot(
            registry=registry,
            source_pdf=cfpb_credit_card_market_report_pdf,
        )
    )
    by_series[CFPB_CREDIT_CARD_INTEREST_PAYMENT_MECHANICS_SERIES_ID] = (
        _cfpb_credit_card_interest_payment_mechanics_snapshot(
            registry=registry,
            source_html=cfpb_credit_card_interest_payment_mechanics_html,
            regulation_html=cfpb_credit_card_payment_allocation_regz_html,
        )
    )
    by_series[CFPB_CONSUMER_CREDIT_TRENDS_ALL_DATA_SERIES_ID] = (
        _cfpb_consumer_credit_trends_snapshot(
            registry=registry,
            source_csv=cfpb_consumer_credit_trends_csv,
            codebook=cfpb_consumer_credit_trends_codebook,
        )
    )
    by_series[CFPB_CONSUMER_CREDIT_TRENDS_CODEBOOK_SERIES_ID] = (
        _cfpb_consumer_credit_trends_codebook_snapshot(
            registry=registry,
            source_workbook=cfpb_consumer_credit_trends_codebook,
        )
    )
    by_series[CFPB_TCCP_SURVEY_SERIES_ID] = _cfpb_tccp_survey_snapshot(
        registry=registry,
        source_workbook=cfpb_tccp_survey_workbook,
    )
    by_series[CFPB_PAYMENT_AMOUNT_FURNISHING_SERIES_ID] = (
        _cfpb_payment_amount_furnishing_snapshot(
            registry=registry,
            source_pdf=cfpb_payment_amount_furnishing_pdf,
        )
    )
    by_series[CFPB_CREDIT_CARD_REVOLVERS_SERIES_ID] = (
        _cfpb_credit_card_revolvers_snapshot(
            registry=registry,
            source_pdf=cfpb_credit_card_revolvers_pdf,
        )
    )
    by_series[CFPB_MEM_SAMPLE1_SERIES_ID] = _cfpb_mem_sample1_public_use_snapshot(
        registry=registry,
        source_zip=cfpb_mem_sample1_zip,
    )
    by_series[CFPB_MEM_SAMPLES_3_6_SERIES_ID] = (
        _cfpb_mem_samples_3_6_public_use_snapshot(registry=registry)
    )
    by_series[PHILLY_FED_Y14_CREDIT_CARD_SERIES_ID] = (
        _philadelphia_fed_y14_credit_card_snapshot(registry=registry)
    )
    by_series[FED_PRIVATE_CREDIT_CHARACTERISTICS_SERIES_ID] = (
        _fed_private_credit_characteristics_snapshot(registry=registry)
    )
    by_series[FED_BANK_LENDING_PRIVATE_CREDIT_SERIES_ID] = (
        _fed_bank_lending_private_credit_snapshot(registry=registry)
    )
    by_series[FED_INDIRECT_CREDIT_ACCESSIBLE_MATERIALS_SERIES_ID] = (
        _fed_indirect_credit_accessible_materials_snapshot(
            registry=registry,
            source_zip=fed_indirect_credit_accessible_materials_zip,
        )
    )
    by_series[FED_CREDIT_BUREAU_HOUSEHOLD_DSR_SERIES_ID] = (
        _fed_credit_bureau_household_dsr_snapshot(
            registry=registry,
            source_html=fed_credit_bureau_household_dsr_accessible_html,
            article_html=fed_credit_bureau_household_dsr_article_html,
        )
    )
    by_series[FED_STUDENT_LOAN_PAYMENT_RESTART_SPENDING_SERIES_ID] = (
        _fed_student_loan_payment_restart_spending_snapshot(
            registry=registry,
            source_html=fed_student_loan_payment_restart_spending_html,
            source_accessible_html=(
                fed_student_loan_payment_restart_spending_accessible_html
            ),
        )
    )
    by_series[FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_SERIES_ID] = (
        _fed_credit_card_limit_increase_debt_snapshot(
            registry=registry,
            source_html=fed_credit_card_limit_increase_debt_html,
            source_accessible_html=fed_credit_card_limit_increase_debt_accessible_html,
        )
    )
    by_series[FED_CREDIT_CARD_PROFITABILITY_REVOLVER_SERIES_ID] = (
        _fed_credit_card_profitability_revolver_snapshot(
            registry=registry,
            source_html=fed_credit_card_profitability_html,
        )
    )
    by_series[FED_CREDIT_CARD_DELINQUENCY_PREDICTION_SERIES_ID] = (
        _fed_credit_card_delinquency_prediction_snapshot(
            registry=registry,
            source_html=fed_credit_card_delinquency_prediction_html,
            source_accessible_html=(
                fed_credit_card_delinquency_prediction_accessible_html
            ),
        )
    )
    by_series[FED_CONSUMER_DELINQUENCY_DYNAMICS_SERIES_ID] = (
        _fed_consumer_delinquency_dynamics_snapshot(
            registry=registry,
            source_html=fed_consumer_delinquency_dynamics_html,
            source_accessible_html=fed_consumer_delinquency_dynamics_accessible_html,
        )
    )
    by_series[FED_CREDIT_CARD_REWARDS_LIMIT_SPENDING_SERIES_ID] = (
        _fed_credit_card_rewards_limit_spending_snapshot(
            registry=registry,
            source_zip=fed_credit_card_rewards_limit_spending_zip,
        )
    )
    by_series[FED_AUTO_LOAN_PAYMENT_DELINQUENCY_SERIES_ID] = (
        _fed_auto_loan_payment_delinquency_snapshot(
            registry=registry,
            source_html=fed_auto_loan_payment_delinquency_html,
            source_accessible_html=fed_auto_loan_payment_delinquency_accessible_html,
        )
    )
    by_series[FED_AUTO_LOAN_PREPAYMENT_MATURITY_SERIES_ID] = (
        _fed_auto_loan_prepayment_maturity_snapshot(
            registry=registry,
            source_zip=fed_auto_loan_prepayment_maturity_zip,
        )
    )
    by_series[BOSTON_FED_CREDIT_CARD_INTEREST_SPENDING_SERIES_ID] = (
        _boston_fed_credit_card_interest_spending_snapshot(
            registry=registry,
            source_html=boston_fed_credit_card_interest_spending_html,
        )
    )
    by_series[BOSTON_FED_CREDIT_CARD_SPENDING_CHANNEL_WP_SERIES_ID] = (
        _boston_fed_credit_card_spending_channel_wp_snapshot(
            registry=registry,
            source_pdf=boston_fed_credit_card_spending_channel_wp_pdf,
        )
    )
    by_series[ATLANTA_FED_CREMI_LONGWEIGHTS_SERIES_ID] = (
        _atlanta_fed_cremi_longweights_snapshot(
            registry=registry,
            source_csv=atlanta_fed_cremi_longweights_csv,
            source_page=atlanta_fed_cremi_page_html,
        )
    )
    by_series[FED_CRE_EVERGREENING_EXTENSION_TERMS_SERIES_ID] = (
        _fed_cre_evergreening_extension_terms_snapshot(
            registry=registry,
            source_html=fed_cre_evergreening_extension_terms_html,
            source_pdf=fed_cre_evergreening_extension_terms_pdf,
        )
    )
    by_series[SEC_PRIVATE_FUND_AGGREGATE_ASSETS_SERIES_ID] = (
        _sec_private_fund_aggregate_assets_snapshot(
            registry=registry,
            source_json_path=sec_private_fund_aggregate_assets_json,
        )
    )
    by_series[SEC_BDC_PUBLIC_FILING_AVAILABILITY_SERIES_ID] = (
        _sec_bdc_public_filing_availability_snapshot(
            registry=registry,
            source_dir=sec_bdc_public_filing_dir,
        )
    )
    by_series[SEC_BDC_PORTFOLIO_INVESTMENT_TERMS_SERIES_ID] = (
        _sec_bdc_portfolio_investment_terms_snapshot(
            registry=registry,
            source_dir=sec_bdc_public_filing_dir,
        )
    )
    by_series[SEC_BDC_PORTFOLIO_PERFORMANCE_STATUS_SERIES_ID] = (
        _sec_bdc_portfolio_performance_status_snapshot(
            registry=registry,
            source_dir=sec_bdc_public_filing_dir,
        )
    )
    by_series[SEC_BDC_PORTFOLIO_TERMS_STATUS_JOIN_SERIES_ID] = (
        _sec_bdc_portfolio_terms_status_join_snapshot(
            registry=registry,
            source_dir=sec_bdc_public_filing_dir,
        )
    )
    by_series[SEC_BDC_PORTFOLIO_TERMS_STATUS_TIME_SERIES_ID] = (
        _sec_bdc_portfolio_terms_status_time_snapshot(
            registry=registry,
            source_dir=sec_bdc_public_filing_dir,
        )
    )
    by_series[SEC_BDC_FLOATING_RATE_PASS_THROUGH_DESIGN_SERIES_ID] = (
        _sec_bdc_floating_rate_pass_through_design_snapshot(
            registry=registry,
            terms_status_time_snapshot=(
                by_series[SEC_BDC_PORTFOLIO_TERMS_STATUS_TIME_SERIES_ID]
            ),
        )
    )
    by_series[SEC_BDC_BORROWER_NAME_CONTINUITY_SERIES_ID] = (
        _sec_bdc_borrower_name_continuity_snapshot(
            registry=registry,
            terms_status_time_snapshot=(
                by_series[SEC_BDC_PORTFOLIO_TERMS_STATUS_TIME_SERIES_ID]
            ),
        )
    )
    by_series[SEC_BDC_INVESTMENT_SIGNATURE_CONTINUITY_SERIES_ID] = (
        _sec_bdc_investment_signature_continuity_snapshot(
            registry=registry,
            terms_status_time_snapshot=(
                by_series[SEC_BDC_PORTFOLIO_TERMS_STATUS_TIME_SERIES_ID]
            ),
        )
    )
    by_series[SEC_BDC_RECURRING_INVESTMENT_VALUE_STATUS_SERIES_ID] = (
        _sec_bdc_recurring_investment_value_status_snapshot(
            registry=registry,
            terms_status_time_snapshot=(
                by_series[SEC_BDC_PORTFOLIO_TERMS_STATUS_TIME_SERIES_ID]
            ),
        )
    )
    by_series[SEC_ABS_EE_CMBS_ASSET_LEVEL_SERIES_ID] = (
        _sec_abs_ee_cmbs_asset_level_snapshot(
            registry=registry,
            source_dir=sec_abs_ee_cmbs_filing_dir,
        )
    )
    by_series[SEC_ABS_EE_CMBS_TIME_DIMENSION_SERIES_ID] = (
        _sec_abs_ee_cmbs_time_dimension_snapshot(
            registry=registry,
            source_dir=sec_abs_ee_cmbs_filing_dir,
        )
    )
    by_series[SEC_ABS_EE_RECENT_FILING_INDEX_SERIES_ID] = (
        _sec_abs_ee_recent_filing_index_snapshot(
            registry=registry,
            source_dir=sec_abs_ee_cmbs_filing_dir,
        )
    )
    by_series[SEC_ABS_EE_CMBS_XML_VERIFICATION_SERIES_ID] = (
        _sec_abs_ee_candidate_cmbs_xml_verification_snapshot(
            registry=registry,
            source_dir=sec_abs_ee_cmbs_filing_dir,
            filing_index_snapshot=by_series[SEC_ABS_EE_RECENT_FILING_INDEX_SERIES_ID],
        )
    )
    by_series[SEC_ABS_EE_CMBS_REPRESENTATIVENESS_DESIGN_SERIES_ID] = (
        _sec_abs_ee_cmbs_representativeness_design_snapshot(
            registry=registry,
            filing_index_snapshot=by_series[SEC_ABS_EE_RECENT_FILING_INDEX_SERIES_ID],
            xml_verification_snapshot=by_series[
                SEC_ABS_EE_CMBS_XML_VERIFICATION_SERIES_ID
            ],
        )
    )
    by_series[FED_Z1_CMBS_ABS_POPULATION_DENOMINATOR_SERIES_ID] = (
        _fed_z1_cmbs_abs_population_denominator_snapshot(
            registry=registry,
            z1_snapshot=by_series["BOGZ1FL673065505Q"],
            representativeness_snapshot=by_series[
                SEC_ABS_EE_CMBS_REPRESENTATIVENESS_DESIGN_SERIES_ID
            ],
        )
    )
    by_series[FED_Z1_TOTAL_COMMERCIAL_MORTGAGE_POPULATION_SERIES_ID] = (
        _fed_z1_total_commercial_mortgage_population_snapshot(
            registry=registry,
            total_z1_snapshot=by_series["ASCMA"],
            cmbs_abs_z1_snapshot=by_series["BOGZ1FL673065505Q"],
            representativeness_snapshot=by_series[
                SEC_ABS_EE_CMBS_REPRESENTATIVENESS_DESIGN_SERIES_ID
            ],
        )
    )
    by_series[SEC_ABS_EE_CMBS_REVIEWED_BALANCE_COVERAGE_SERIES_ID] = (
        _sec_abs_ee_cmbs_reviewed_balance_coverage_snapshot(
            registry=registry,
            asset_time_snapshot=by_series[SEC_ABS_EE_CMBS_TIME_DIMENSION_SERIES_ID],
            representativeness_snapshot=by_series[
                SEC_ABS_EE_CMBS_REPRESENTATIVENESS_DESIGN_SERIES_ID
            ],
            cmbs_abs_z1_snapshot=by_series["BOGZ1FL673065505Q"],
            total_z1_snapshot=by_series["ASCMA"],
        )
    )
    by_series[SEC_ABS_EE_CMBS_MATURITY_STATUS_OUTCOME_SERIES_ID] = (
        _sec_abs_ee_cmbs_maturity_status_outcome_snapshot(
            registry=registry,
            asset_time_snapshot=by_series[SEC_ABS_EE_CMBS_TIME_DIMENSION_SERIES_ID],
            representativeness_snapshot=by_series[
                SEC_ABS_EE_CMBS_REPRESENTATIVENESS_DESIGN_SERIES_ID
            ],
        )
    )
    by_series[FRED_NONRES_CONSTRUCTION_REAL_ACTIVITY_BRIDGE_SERIES_ID] = (
        _fred_nonres_construction_real_activity_bridge_snapshot(
            registry=registry,
            construction_snapshot=by_series["TLNRESCONS"],
            total_z1_snapshot=by_series["ASCMA"],
            representativeness_snapshot=by_series[
                SEC_ABS_EE_CMBS_REPRESENTATIVENESS_DESIGN_SERIES_ID
            ],
        )
    )
    by_series[FRED_CRE_PROPERTY_TYPE_CONSTRUCTION_BRIDGE_SERIES_ID] = (
        _fred_cre_property_type_construction_bridge_snapshot(
            registry=registry,
            construction_snapshots={
                series_id: by_series[series_id]
                for series_id in CRE_PROPERTY_CONSTRUCTION_SERIES
            },
            total_nonres_snapshot=by_series["TLNRESCONS"],
            total_private_nonres_snapshot=by_series["PNRESCONS"],
            total_z1_snapshot=by_series["ASCMA"],
            representativeness_snapshot=by_series[
                SEC_ABS_EE_CMBS_REPRESENTATIVENESS_DESIGN_SERIES_ID
            ],
        )
    )
    by_series[FED_DFA_HOUSEHOLD_LIABILITY_SERIES_ID] = (
        dfa_adapter.pull_distributional_exposure(FED_DFA_HOUSEHOLD_LIABILITY_SERIES_ID)
    )
    by_series[FED_SCF_SUMMARY_EXTRACT_SERIES_ID] = _fed_scf_summary_extract_snapshot(
        registry=registry,
        source_zip=fed_scf_summary_extract_zip,
    )
    by_series[FED_SCF_WEIGHTED_SUMMARY_SERIES_ID] = _fed_scf_weighted_summary_snapshot(
        registry=registry,
        source_zip=fed_scf_summary_extract_zip,
    )
    by_series[FED_SCF_REPLICATE_WEIGHT_METHOD_SERIES_ID] = (
        _fed_scf_replicate_weight_method_snapshot(
            registry=registry,
            source_zip=fed_scf_replicate_weight_zip,
        )
    )
    by_series[FED_SCF_UNCERTAINTY_SERIES_ID] = _fed_scf_uncertainty_snapshot(
        registry=registry,
        summary_zip=fed_scf_summary_extract_zip,
        replicate_zip=fed_scf_replicate_weight_zip,
        standard_error_pdf=fed_scf_standard_error_documentation_pdf,
        codebook=fed_scf_codebook,
    )
    by_series[FED_SHED_FINANCIAL_FRAGILITY_SERIES_ID] = (
        _fed_shed_financial_fragility_snapshot(
            registry=registry,
            source_zip=fed_shed_public_use_zip,
            codebook=fed_shed_codebook,
        )
    )
    by_series[FED_CRE_HIGH_GROWTH_DEPOSIT_SERIES_ID] = (
        _fed_cre_high_growth_deposit_snapshot(registry=registry)
    )
    by_series[NYFED_CONSUMER_CREDIT_PANEL_FAQ_SERIES_ID] = (
        _nyfed_consumer_credit_panel_faq_snapshot(registry=registry)
    )
    by_series[NYFED_HOUSEHOLD_DEBT_CREDIT_REPORT_SERIES_ID] = (
        _nyfed_household_debt_credit_report_snapshot(
            registry=registry,
            source_workbook=nyfed_household_debt_credit_workbook,
        )
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
    parser.add_argument(
        "--cfpb-credit-card-workbook",
        type=Path,
        default=CFPB_CREDIT_CARD_FIGURE_DATA_DEFAULT,
    )
    parser.add_argument(
        "--cfpb-credit-card-market-report-pdf",
        type=Path,
        default=CFPB_CREDIT_CARD_MARKET_REPORT_DEFAULT,
    )
    parser.add_argument(
        "--cfpb-credit-card-interest-payment-mechanics-html",
        type=Path,
        default=CFPB_CREDIT_CARD_INTEREST_PAYMENT_MECHANICS_DEFAULT,
    )
    parser.add_argument(
        "--cfpb-credit-card-payment-allocation-regz-html",
        type=Path,
        default=CFPB_CREDIT_CARD_PAYMENT_ALLOCATION_REGZ_DEFAULT,
    )
    parser.add_argument(
        "--cfpb-consumer-credit-trends-csv",
        type=Path,
        default=CFPB_CONSUMER_CREDIT_TRENDS_ALL_DATA_DEFAULT,
    )
    parser.add_argument(
        "--cfpb-consumer-credit-trends-codebook",
        type=Path,
        default=CFPB_CONSUMER_CREDIT_TRENDS_CODEBOOK_DEFAULT,
    )
    parser.add_argument(
        "--cfpb-tccp-survey-workbook",
        type=Path,
        default=CFPB_TCCP_SURVEY_DEFAULT,
    )
    parser.add_argument(
        "--cfpb-payment-amount-furnishing-pdf",
        type=Path,
        default=CFPB_PAYMENT_AMOUNT_FURNISHING_DEFAULT,
    )
    parser.add_argument(
        "--cfpb-credit-card-revolvers-pdf",
        type=Path,
        default=CFPB_CREDIT_CARD_REVOLVERS_DEFAULT,
    )
    parser.add_argument(
        "--cfpb-mem-sample1-zip",
        type=Path,
        default=CFPB_MEM_SAMPLE1_DEFAULT,
    )
    parser.add_argument(
        "--nyfed-household-debt-credit-workbook",
        type=Path,
        default=NYFED_HOUSEHOLD_DEBT_CREDIT_REPORT_DEFAULT,
    )
    parser.add_argument(
        "--fed-indirect-credit-accessible-materials-zip",
        type=Path,
        default=FED_INDIRECT_CREDIT_ACCESSIBLE_MATERIALS_DEFAULT,
    )
    parser.add_argument(
        "--fed-credit-bureau-household-dsr-accessible-html",
        type=Path,
        default=FED_CREDIT_BUREAU_HOUSEHOLD_DSR_ACCESSIBLE_DEFAULT,
    )
    parser.add_argument(
        "--fed-credit-bureau-household-dsr-article-html",
        type=Path,
        default=FED_CREDIT_BUREAU_HOUSEHOLD_DSR_ARTICLE_DEFAULT,
    )
    parser.add_argument(
        "--fed-student-loan-payment-restart-spending-html",
        type=Path,
        default=FED_STUDENT_LOAN_PAYMENT_RESTART_SPENDING_HTML_DEFAULT,
    )
    parser.add_argument(
        "--fed-student-loan-payment-restart-spending-accessible-html",
        type=Path,
        default=FED_STUDENT_LOAN_PAYMENT_RESTART_SPENDING_ACCESSIBLE_DEFAULT,
    )
    parser.add_argument(
        "--fed-credit-card-limit-increase-debt-html",
        type=Path,
        default=FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_HTML_DEFAULT,
    )
    parser.add_argument(
        "--fed-credit-card-limit-increase-debt-accessible-html",
        type=Path,
        default=FED_CREDIT_CARD_LIMIT_INCREASE_DEBT_ACCESSIBLE_DEFAULT,
    )
    parser.add_argument(
        "--fed-credit-card-profitability-html",
        type=Path,
        default=FED_CREDIT_CARD_PROFITABILITY_HTML_DEFAULT,
    )
    parser.add_argument(
        "--fed-credit-card-delinquency-prediction-html",
        type=Path,
        default=FED_CREDIT_CARD_DELINQUENCY_PREDICTION_HTML_DEFAULT,
    )
    parser.add_argument(
        "--fed-credit-card-delinquency-prediction-accessible-html",
        type=Path,
        default=FED_CREDIT_CARD_DELINQUENCY_PREDICTION_ACCESSIBLE_DEFAULT,
    )
    parser.add_argument(
        "--fed-consumer-delinquency-dynamics-html",
        type=Path,
        default=FED_CONSUMER_DELINQUENCY_DYNAMICS_HTML_DEFAULT,
    )
    parser.add_argument(
        "--fed-consumer-delinquency-dynamics-accessible-html",
        type=Path,
        default=FED_CONSUMER_DELINQUENCY_DYNAMICS_ACCESSIBLE_DEFAULT,
    )
    parser.add_argument(
        "--fed-credit-card-rewards-limit-spending-zip",
        type=Path,
        default=FED_CREDIT_CARD_REWARDS_LIMIT_SPENDING_DEFAULT,
    )
    parser.add_argument(
        "--fed-auto-loan-payment-delinquency-html",
        type=Path,
        default=FED_AUTO_LOAN_PAYMENT_DELINQUENCY_HTML_DEFAULT,
    )
    parser.add_argument(
        "--fed-auto-loan-payment-delinquency-accessible-html",
        type=Path,
        default=FED_AUTO_LOAN_PAYMENT_DELINQUENCY_ACCESSIBLE_DEFAULT,
    )
    parser.add_argument(
        "--fed-auto-loan-prepayment-maturity-zip",
        type=Path,
        default=FED_AUTO_LOAN_PREPAYMENT_MATURITY_DEFAULT,
    )
    parser.add_argument(
        "--boston-fed-credit-card-interest-spending-html",
        type=Path,
        default=BOSTON_FED_CREDIT_CARD_INTEREST_SPENDING_DEFAULT,
    )
    parser.add_argument(
        "--boston-fed-credit-card-spending-channel-wp-pdf",
        type=Path,
        default=BOSTON_FED_CREDIT_CARD_SPENDING_CHANNEL_WP_DEFAULT,
    )
    parser.add_argument(
        "--atlanta-fed-cremi-longweights-csv",
        type=Path,
        default=ATLANTA_FED_CREMI_LONGWEIGHTS_DEFAULT,
    )
    parser.add_argument(
        "--atlanta-fed-cremi-page-html",
        type=Path,
        default=ATLANTA_FED_CREMI_PAGE_DEFAULT,
    )
    parser.add_argument(
        "--fed-cre-evergreening-extension-terms-html",
        type=Path,
        default=FED_CRE_EVERGREENING_EXTENSION_TERMS_HTML_DEFAULT,
    )
    parser.add_argument(
        "--fed-cre-evergreening-extension-terms-pdf",
        type=Path,
        default=FED_CRE_EVERGREENING_EXTENSION_TERMS_PDF_DEFAULT,
    )
    parser.add_argument(
        "--sec-private-fund-aggregate-assets-json",
        type=Path,
        default=SEC_PRIVATE_FUND_AGGREGATE_ASSETS_DEFAULT,
    )
    parser.add_argument(
        "--sec-bdc-public-filing-dir",
        type=Path,
        default=SEC_BDC_PUBLIC_FILING_DIR_DEFAULT,
    )
    parser.add_argument(
        "--sec-abs-ee-cmbs-filing-dir",
        type=Path,
        default=SEC_ABS_EE_CMBS_DIR_DEFAULT,
    )
    parser.add_argument(
        "--fed-scf-summary-extract-zip",
        type=Path,
        default=FED_SCF_SUMMARY_EXTRACT_DEFAULT,
    )
    parser.add_argument(
        "--fed-scf-replicate-weight-zip",
        type=Path,
        default=FED_SCF_REPLICATE_WEIGHT_DEFAULT,
    )
    parser.add_argument(
        "--fed-scf-standard-error-documentation-pdf",
        type=Path,
        default=FED_SCF_STANDARD_ERROR_DOCUMENTATION_DEFAULT,
    )
    parser.add_argument(
        "--fed-scf-codebook",
        type=Path,
        default=FED_SCF_CODEBOOK_DEFAULT,
    )
    parser.add_argument(
        "--fed-shed-public-use-zip",
        type=Path,
        default=FED_SHED_PUBLIC_USE_DATA_DEFAULT,
    )
    parser.add_argument(
        "--fed-shed-codebook",
        type=Path,
        default=FED_SHED_CODEBOOK_DEFAULT,
    )
    args = parser.parse_args()
    output = materialize(
        config=args.config,
        snapshot_bundle=args.snapshot_bundle,
        output=args.output,
        cfpb_credit_card_workbook=args.cfpb_credit_card_workbook,
        cfpb_credit_card_market_report_pdf=(args.cfpb_credit_card_market_report_pdf),
        cfpb_credit_card_interest_payment_mechanics_html=(
            args.cfpb_credit_card_interest_payment_mechanics_html
        ),
        cfpb_credit_card_payment_allocation_regz_html=(
            args.cfpb_credit_card_payment_allocation_regz_html
        ),
        cfpb_consumer_credit_trends_csv=args.cfpb_consumer_credit_trends_csv,
        cfpb_consumer_credit_trends_codebook=(
            args.cfpb_consumer_credit_trends_codebook
        ),
        cfpb_tccp_survey_workbook=args.cfpb_tccp_survey_workbook,
        cfpb_payment_amount_furnishing_pdf=(args.cfpb_payment_amount_furnishing_pdf),
        cfpb_credit_card_revolvers_pdf=args.cfpb_credit_card_revolvers_pdf,
        cfpb_mem_sample1_zip=args.cfpb_mem_sample1_zip,
        nyfed_household_debt_credit_workbook=(
            args.nyfed_household_debt_credit_workbook
        ),
        fed_indirect_credit_accessible_materials_zip=(
            args.fed_indirect_credit_accessible_materials_zip
        ),
        fed_credit_bureau_household_dsr_accessible_html=(
            args.fed_credit_bureau_household_dsr_accessible_html
        ),
        fed_credit_bureau_household_dsr_article_html=(
            args.fed_credit_bureau_household_dsr_article_html
        ),
        fed_student_loan_payment_restart_spending_html=(
            args.fed_student_loan_payment_restart_spending_html
        ),
        fed_student_loan_payment_restart_spending_accessible_html=(
            args.fed_student_loan_payment_restart_spending_accessible_html
        ),
        fed_credit_card_limit_increase_debt_html=(
            args.fed_credit_card_limit_increase_debt_html
        ),
        fed_credit_card_limit_increase_debt_accessible_html=(
            args.fed_credit_card_limit_increase_debt_accessible_html
        ),
        fed_credit_card_profitability_html=(args.fed_credit_card_profitability_html),
        fed_credit_card_delinquency_prediction_html=(
            args.fed_credit_card_delinquency_prediction_html
        ),
        fed_credit_card_delinquency_prediction_accessible_html=(
            args.fed_credit_card_delinquency_prediction_accessible_html
        ),
        fed_consumer_delinquency_dynamics_html=(
            args.fed_consumer_delinquency_dynamics_html
        ),
        fed_consumer_delinquency_dynamics_accessible_html=(
            args.fed_consumer_delinquency_dynamics_accessible_html
        ),
        fed_credit_card_rewards_limit_spending_zip=(
            args.fed_credit_card_rewards_limit_spending_zip
        ),
        fed_auto_loan_payment_delinquency_html=(
            args.fed_auto_loan_payment_delinquency_html
        ),
        fed_auto_loan_payment_delinquency_accessible_html=(
            args.fed_auto_loan_payment_delinquency_accessible_html
        ),
        fed_auto_loan_prepayment_maturity_zip=(
            args.fed_auto_loan_prepayment_maturity_zip
        ),
        boston_fed_credit_card_interest_spending_html=(
            args.boston_fed_credit_card_interest_spending_html
        ),
        boston_fed_credit_card_spending_channel_wp_pdf=(
            args.boston_fed_credit_card_spending_channel_wp_pdf
        ),
        atlanta_fed_cremi_longweights_csv=(args.atlanta_fed_cremi_longweights_csv),
        atlanta_fed_cremi_page_html=args.atlanta_fed_cremi_page_html,
        fed_cre_evergreening_extension_terms_html=(
            args.fed_cre_evergreening_extension_terms_html
        ),
        fed_cre_evergreening_extension_terms_pdf=(
            args.fed_cre_evergreening_extension_terms_pdf
        ),
        sec_private_fund_aggregate_assets_json=(
            args.sec_private_fund_aggregate_assets_json
        ),
        sec_bdc_public_filing_dir=args.sec_bdc_public_filing_dir,
        sec_abs_ee_cmbs_filing_dir=args.sec_abs_ee_cmbs_filing_dir,
        fed_scf_summary_extract_zip=args.fed_scf_summary_extract_zip,
        fed_scf_replicate_weight_zip=args.fed_scf_replicate_weight_zip,
        fed_scf_standard_error_documentation_pdf=(
            args.fed_scf_standard_error_documentation_pdf
        ),
        fed_scf_codebook=args.fed_scf_codebook,
        fed_shed_public_use_zip=args.fed_shed_public_use_zip,
        fed_shed_codebook=args.fed_shed_codebook,
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
