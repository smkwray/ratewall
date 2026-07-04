import csv
import io
import json
import zipfile
from array import array
from types import SimpleNamespace

from scripts.materialize_higher_rate_channel_sources import (
    PHILLY_FED_Y14_BALANCES_REQUIRED_COLUMNS,
    PHILLY_FED_Y14_ORIGINATION_REQUIRED_COLUMNS,
    _atlanta_fed_cremi_longweights_records,
    _boston_fed_credit_card_spending_channel_wp_records,
    _boston_fed_credit_card_interest_spending_records,
    _cfpb_consumer_credit_trends_codebook_records,
    _cfpb_consumer_credit_trends_records,
    _cfpb_credit_card_interest_payment_mechanics_records,
    _cfpb_credit_card_market_report_records,
    _cfpb_credit_card_revolvers_records,
    _cfpb_mem_sample1_public_use_records,
    _cfpb_mem_multisample_public_use_records,
    _cfpb_payment_amount_furnishing_records,
    _cfpb_tccp_survey_records,
    _fed_cre_high_growth_deposit_records,
    _fed_auto_loan_prepayment_maturity_records,
    _fed_auto_loan_payment_delinquency_records,
    _fed_credit_bureau_household_dsr_records,
    _fed_credit_card_delinquency_prediction_records,
    _fed_credit_card_limit_increase_debt_records,
    _fed_credit_card_profitability_revolver_records,
    _fed_credit_card_rewards_limit_spending_records,
    _fed_consumer_delinquency_dynamics_records,
    _fed_cre_evergreening_extension_terms_records,
    _fed_bank_lending_private_credit_records,
    _fed_indirect_credit_accessible_material_records,
    _fed_private_credit_accessible_table_records,
    _fed_scf_uncertainty_records,
    _fed_shed_financial_fragility_records,
    _fed_student_loan_payment_restart_spending_records,
    _philadelphia_fed_y14_credit_card_records,
    _sec_private_fund_aggregate_asset_records,
    _sec_bdc_public_filing_availability_record,
    _sec_bdc_portfolio_investment_terms_records,
    _sec_bdc_footnote_context,
    _sec_bdc_borrower_name_continuity_records,
    _sec_bdc_floating_rate_pass_through_design_records,
    _sec_bdc_investment_signature_continuity_records,
    _sec_bdc_performance_status_record,
    _sec_bdc_recent_periodic_filings,
    _sec_bdc_recurring_investment_value_status_records,
    _sec_bdc_submissions_for_single_filing,
    _sec_bdc_terms_status_join_record,
    _sec_bdc_time_dimension_record,
    _sec_abs_ee_cmbs_asset_property_records,
    _sec_abs_ee_cmbs_maturity_status_outcome_records,
    _fred_cre_property_type_construction_bridge_records,
    _sec_abs_ee_cmbs_reviewed_balance_coverage_records,
    _fed_z1_cmbs_abs_population_denominator_records,
    _fed_z1_total_commercial_mortgage_population_records,
    _fred_nonres_construction_real_activity_bridge_records,
    _sec_abs_ee_cmbs_representativeness_design_records,
    _sec_abs_ee_cmbs_time_dimension_records,
    _sec_abs_ee_recent_index_records,
    _sec_abs_ee_xml_payload_verification_fields,
    _sec_abs_ee_xml_verification_candidate_rows,
)


def test_boston_fed_credit_card_interest_spending_parser_keeps_gate_fail_closed():
    html = """
    <html><body>
    <h1>How Interest Rate Changes Affect Credit Card Spending</h1>
    <p>when credit card interest rates increase by 1 percentage point,
    consumers reduce their credit card spending by 8.7 percent</p>
    <p>These data cover nearly 80 percent of all US credit card accounts that
    were active during the 2016&ndash;2025 period.</p>
    <p>We describe the regression kink design.</p>
    <p>consumer spending more broadly may be smaller than our estimates.</p>
    </body></html>
    """

    rows = _boston_fed_credit_card_interest_spending_records(html)

    assert len(rows) == 10
    assert rows[0]["metric"] == ("credit_card_spending_response_per_1pp_apr_increase")
    assert rows[0]["metric_value"] == "-8.7"
    assert {row["credit_card_spending_response_context_available"] for row in rows} == {
        "true"
    }
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"true"}
    assert {
        row["monetary_rate_shock_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_conversion_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_boston_fed_credit_card_spending_wp_parser_keeps_gate_fail_closed():
    text = """
    No. 25-10
    The Credit Card Spending Channel of Monetary Policy:
    Micro Evidence from Account-level Data
    regression kink design
    nearly 80 percent of all US credit cards
    Table 2: RKD Estimates of Interest-rate Elasticity
    Table 6: Response of Spending Growth at h = 2
    Jarocinski and Karadi monetary policy shocks
    Anderson-Rubin confidence intervals
    """

    rows = _boston_fed_credit_card_spending_channel_wp_records(text)

    assert len(rows) == 15
    assert any(
        row["metric"] == "rkd_spending_elasticity_col4"
        and row["metric_value"] == "-8.66"
        and row["metric_standard_error"] == "2.91"
        for row in rows
    )
    assert any(
        row["metric"] == "aggregate_lp_iv_total_spending_growth_h2"
        and row["metric_lower_ci"] == "-0.188"
        and row["metric_upper_ci"] == "0.044"
        for row in rows
    )
    assert {
        row["promotion_grade_monetary_rate_shock_bridge_available"] for row in rows
    } == {"false"}
    assert {row["public_borrower_level_microdata_available"] for row in rows} == {
        "false"
    }
    assert {row["current_demand_conversion_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def _xlsx_col(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(ord("A") + remainder) + letters
    return letters


def test_sec_bdc_floating_rate_pass_through_context_stays_fail_closed():
    records = [
        {
            "date": "2026-05-01",
            "report_date": "2026-03-31",
            "ticker": "ARCC",
            "reference_rate": "SOFR (Q)",
            "spread": "5.00 %",
            "floor": "",
            "maturity_date": "10/2029",
            "principal_or_par_value": "13.1",
            "fair_value": "13.1",
            "borrower_or_issuer_name": "Example Borrower LLC",
            "terms_row_support_status": "full_terms_support",
            "non_accrual_status_marker": "false",
            "pik_status_marker": "false",
            "valuation_gap_context_available": "true",
        },
        {
            "date": "2026-05-01",
            "report_date": "2026-03-31",
            "ticker": "ARCC",
            "reference_rate": "S + 5.00 %",
            "cash_component": "5.00 %",
            "floor": "1.0 %",
            "maturity_date": "08/2029",
            "principal_or_par_value": "2.0",
            "fair_value": "1.9",
            "borrower_or_issuer_name": "Second Borrower LLC",
            "terms_row_support_status": "full_terms_support",
            "non_accrual_status_marker": "true",
            "pik_status_marker": "true",
            "valuation_gap_context_available": "true",
        },
        {
            "date": "2026-05-01",
            "report_date": "2026-03-31",
            "ticker": "ARCC",
            "reference_rate": "",
            "borrower_or_issuer_name": "Fixed Borrower LLC",
        },
    ]

    rows = _sec_bdc_floating_rate_pass_through_design_records(records)

    assert len(rows) == 2
    categories = {row["reference_rate_category"] for row in rows}
    assert categories == {
        "explicit_sofr_reference_rate",
        "source_abbreviated_reference_rate",
    }
    assert {
        row["public_contractual_reference_rate_terms_available"] for row in rows
    } == {"true"}
    assert {
        row["contractual_floating_rate_pass_through_context_available"] for row in rows
    } == {"true"}
    assert {
        row["promotion_grade_monetary_pass_through_design_available"] for row in rows
    } == {"false"}
    assert {
        row["public_reusable_repayment_schedule_panel_available"] for row in rows
    } == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}


def test_sec_bdc_borrower_name_continuity_context_stays_fail_closed():
    records = [
        {
            "date": "2026-02-01",
            "report_date": "2025-12-31",
            "ticker": "ARCC",
            "accession_number": "0001",
            "borrower_or_issuer_name": "Example Borrower LLC",
            "investment_type": "First Lien Senior Secured Loan",
            "reference_rate": "SOFR",
            "spread": "5.00 %",
            "maturity_date": "10/2029",
            "principal_or_par_value": "13.1",
            "fair_value": "13.1",
            "terms_row_support_status": "full_terms_support",
            "non_accrual_status_marker": "false",
            "pik_status_marker": "false",
            "fair_value_less_than_principal_or_par_marker": "false",
        },
        {
            "date": "2026-05-01",
            "report_date": "2026-03-31",
            "ticker": "ARCC",
            "accession_number": "0002",
            "borrower_or_issuer_name": "Example  Borrower LLC",
            "investment_type": "First Lien Senior Secured Loan",
            "reference_rate": "SOFR",
            "cash_component": "5.00 %",
            "maturity_date": "10/2029",
            "principal_or_par_value": "13.1",
            "fair_value": "12.9",
            "terms_row_support_status": "full_terms_support",
            "non_accrual_status_marker": "false",
            "pik_status_marker": "true",
            "fair_value_less_than_principal_or_par_marker": "true",
        },
        {
            "date": "2026-05-01",
            "report_date": "2026-03-31",
            "ticker": "ARCC",
            "accession_number": "0002",
            "borrower_or_issuer_name": "One-Off Borrower LLC",
        },
    ]

    rows = _sec_bdc_borrower_name_continuity_records(records)

    assert len(rows) == 1
    row = rows[0]
    assert row["normalized_source_borrower_name"] == "example borrower llc"
    assert row["report_date_count"] == "2"
    assert row["source_row_count"] == "2"
    assert row["accession_count"] == "2"
    assert row["exact_public_borrower_name_continuity_context_available"] == "true"
    assert row["stable_public_borrower_identifier_available"] == "false"
    assert row["public_reusable_loan_identifier_available"] == "false"
    assert row["borrower_cashflow_pass_through_available"] == "false"
    assert row["nonbank_to_real_activity_context_available"] == "false"
    assert row["split_denominator_promotion_allowed"] == "false"


def test_sec_bdc_investment_signature_continuity_context_stays_fail_closed():
    records = [
        {
            "date": "2026-02-01",
            "report_date": "2025-12-31",
            "ticker": "ARCC",
            "accession_number": "0001",
            "borrower_or_issuer_name": "Example Borrower LLC",
            "investment_type": "First Lien Senior Secured Loan",
            "reference_rate": "SOFR",
            "spread": "5.00 %",
            "maturity_date": "10/2029",
            "principal_or_par_value": "13.1",
            "fair_value": "13.1",
            "terms_row_support_status": "full_terms_support",
            "non_accrual_status_marker": "false",
            "pik_status_marker": "false",
            "fair_value_less_than_principal_or_par_marker": "false",
        },
        {
            "date": "2026-05-01",
            "report_date": "2026-03-31",
            "ticker": "ARCC",
            "accession_number": "0002",
            "borrower_or_issuer_name": "Example  Borrower LLC",
            "investment_type": "First Lien Senior Secured Loan",
            "reference_rate": "SOFR",
            "cash_component": "5.00 %",
            "maturity_date": "10/2029",
            "principal_or_par_value": "13.1",
            "fair_value": "12.9",
            "terms_row_support_status": "full_terms_support",
            "non_accrual_status_marker": "false",
            "pik_status_marker": "true",
            "fair_value_less_than_principal_or_par_marker": "true",
        },
        {
            "date": "2026-05-01",
            "report_date": "2026-03-31",
            "ticker": "ARCC",
            "accession_number": "0002",
            "borrower_or_issuer_name": "Example Borrower LLC",
            "investment_type": "Second Lien Senior Secured Loan",
            "reference_rate": "SOFR",
            "maturity_date": "10/2029",
        },
    ]

    rows = _sec_bdc_investment_signature_continuity_records(records)

    assert len(rows) == 1
    row = rows[0]
    assert row["normalized_source_borrower_name"] == "example borrower llc"
    assert row["normalized_investment_type"] == "first lien senior secured loan"
    assert row["normalized_maturity_date"] == "10/2029"
    assert row["reference_rate_category"] == "explicit_sofr_reference_rate"
    assert row["report_date_count"] == "2"
    assert row["source_row_count"] == "2"
    assert row["public_investment_signature_continuity_context_available"] == "true"
    assert row["stable_public_borrower_identifier_available"] == "false"
    assert row["public_reusable_loan_identifier_available"] == "false"
    assert row["public_reusable_repayment_schedule_panel_available"] == "false"
    assert row["borrower_cashflow_pass_through_available"] == "false"
    assert row["nonbank_to_real_activity_context_available"] == "false"
    assert row["split_denominator_promotion_allowed"] == "false"


def test_sec_bdc_recurring_investment_value_status_context_stays_fail_closed():
    records = [
        {
            "date": "2026-02-01",
            "report_date": "2025-12-31",
            "ticker": "ARCC",
            "accession_number": "0001",
            "borrower_or_issuer_name": "Example Borrower LLC",
            "investment_type": "First Lien Senior Secured Loan",
            "reference_rate": "SOFR",
            "spread": "5.00 %",
            "maturity_date": "10/2029",
            "principal_or_par_value": "13.1",
            "fair_value": "13.1",
            "amortized_cost": "13.0",
            "terms_row_support_status": "full_terms_support",
            "non_accrual_status_marker": "false",
            "pik_status_marker": "false",
            "fair_value_less_than_principal_or_par_marker": "false",
        },
        {
            "date": "2026-05-01",
            "report_date": "2026-03-31",
            "ticker": "ARCC",
            "accession_number": "0002",
            "borrower_or_issuer_name": "Example  Borrower LLC",
            "investment_type": "First Lien Senior Secured Loan",
            "reference_rate": "SOFR",
            "cash_component": "5.00 %",
            "maturity_date": "10/2029",
            "principal_or_par_value": "12.8",
            "fair_value": "12.5",
            "amortized_cost": "12.9",
            "terms_row_support_status": "full_terms_support",
            "non_accrual_status_marker": "false",
            "pik_status_marker": "true",
            "fair_value_less_than_principal_or_par_marker": "true",
        },
    ]

    rows = _sec_bdc_recurring_investment_value_status_records(records)

    assert len(rows) == 1
    row = rows[0]
    assert row["public_recurring_investment_value_status_context_available"] == "true"
    assert row["value_or_status_variation_context_available"] == "true"
    assert row["principal_or_par_changed_across_reports"] == "true"
    assert row["fair_value_changed_across_reports"] == "true"
    assert row["pik_marker_changed_across_reports"] == "true"
    assert row["fair_value_below_par_changed_across_reports"] == "true"
    assert row["stable_public_borrower_identifier_available"] == "false"
    assert row["public_reusable_loan_identifier_available"] == "false"
    assert row["public_reusable_repayment_schedule_panel_available"] == "false"
    assert row["borrower_cashflow_pass_through_available"] == "false"
    assert row["monetary_pass_through_design_available"] == "false"
    assert row["nonbank_to_real_activity_context_available"] == "false"
    assert row["split_denominator_promotion_allowed"] == "false"


def _write_minimal_shared_string_xlsx(path, rows: dict[int, dict[int, str]]) -> None:
    strings: list[str] = []
    string_index: dict[str, int] = {}

    def intern(value: str) -> int:
        if value not in string_index:
            string_index[value] = len(strings)
            strings.append(value)
        return string_index[value]

    sheet_rows = []
    for row_index, columns in sorted(rows.items()):
        cells = []
        for col_index, value in sorted(columns.items()):
            cells.append(
                f'<c r="{_xlsx_col(col_index)}{row_index}" t="s">'
                f"<v>{intern(value)}</v></c>"
            )
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    shared = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(strings)}" uniqueCount="{len(strings)}">'
        + "".join(f"<si><t>{value}</t></si>" for value in strings)
        + "</sst>"
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", shared)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)


def _write_minimal_multi_sheet_xlsx(path, sheets: dict[str, list[list[str]]]) -> None:
    strings: list[str] = []
    string_index: dict[str, int] = {}

    def intern(value: str) -> int:
        if value not in string_index:
            string_index[value] = len(strings)
            strings.append(value)
        return string_index[value]

    workbook_sheets: list[str] = []
    rels: list[str] = []
    sheet_payloads: dict[str, str] = {}
    for sheet_index, (sheet_name, rows) in enumerate(sheets.items(), start=1):
        workbook_sheets.append(
            f'<sheet name="{sheet_name}" sheetId="{sheet_index}" '
            f'r:id="rId{sheet_index}"/>'
        )
        rels.append(
            f'<Relationship Id="rId{sheet_index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
            f'relationships/worksheet" Target="worksheets/sheet{sheet_index}.xml"/>'
        )
        sheet_rows = []
        for row_index, row in enumerate(rows, start=1):
            cells = []
            for col_index, value in enumerate(row, start=1):
                cells.append(
                    f'<c r="{_xlsx_col(col_index)}{row_index}" t="s">'
                    f"<v>{intern(value)}</v></c>"
                )
            sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
        sheet_payloads[f"xl/worksheets/sheet{sheet_index}.xml"] = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f"<sheetData>{''.join(sheet_rows)}</sheetData></worksheet>"
        )
    shared = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(strings)}" uniqueCount="{len(strings)}">'
        + "".join(f"<si><t>{value}</t></si>" for value in strings)
        + "</sst>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{''.join(workbook_sheets)}</sheets></workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{''.join(rels)}</Relationships>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", shared)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        for sheet_path, sheet_xml in sheet_payloads.items():
            archive.writestr(sheet_path, sheet_xml)


def test_cfpb_consumer_credit_trends_parser_keeps_gate_fail_closed(tmp_path):
    source_csv = tmp_path / "all_data.csv"
    source_csv.write_text(
        "\n".join(
            [
                "month,date,series,subgroup,subgroup_level,loan_type,value_type,value,value_yoy",
                "72,2006-01,Originations,score,Prime,CRC,Unadjusted,123.45,",
                "73,2006-02,Dollar Volume,income,Low,MTG,Seasonally Adjusted,678.9,0.12",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rows = _cfpb_consumer_credit_trends_records(source_csv)

    assert len(rows) == 2
    assert rows[0]["date"] == "2006-01-01"
    assert rows[0]["credit_score_distribution_context_available"] == "true"
    assert rows[1]["income_distribution_context_available"] == "true"
    assert {row["borrower_level_microdata_available"] for row in rows} == {"false"}
    assert {row["current_demand_conversion_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_cfpb_consumer_credit_trends_codebook_parser_keeps_gate_fail_closed(tmp_path):
    source_workbook = tmp_path / "CCT_dd_cb_all_files.xlsx"
    _write_minimal_multi_sheet_xlsx(
        source_workbook,
        {
            "data dict for all_data.csv": [
                ["field_name", "field_description", "valid_values"],
                ["date", "Month and year", "Date, format YYYY-MM"],
                ["loan_type", "Name of consumer credit market", "CRC = Credit cards"],
            ],
            "data dict for indiv CSV files": [
                ["field_name", "field_description", "valid_values"],
                ["num", "Number of new loans originated", "Numeric"],
            ],
            "codebook": [
                ["subgroup", "subgroup_level", "definition"],
                ["score", "Prime", "Consumers with FICO Score 660-719"],
                ["income", "Low", "Census tract relative income less than 50"],
            ],
        },
    )

    rows = _cfpb_consumer_credit_trends_codebook_records(source_workbook)

    assert len(rows) == 5
    assert {row["source_workbook_schema_reviewed"] for row in rows} == {"true"}
    assert {row["borrower_level_microdata_available"] for row in rows} == {"false"}
    assert {row["current_demand_conversion_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}
    assert {row["row_kind"] for row in rows} == {
        "all_data_csv_field",
        "individual_csv_field",
        "subgroup_level",
    }


def test_fed_credit_bureau_household_dsr_parser_keeps_gate_fail_closed():
    html = """
    <html><body>
    <h1>Introducing a Credit Bureau-Based Measure of U.S. Household Debt Service</h1>
    <p>These data include monthly scheduled payments.</p>
    <p>monthly scheduled payments for each open tradeline</p>
    <p>The scheduled payment reported for credit cards is the minimum required payment.</p>
    <table>
      <tr><th>Quarter</th><th>Old Methodology</th><th>Credit Bureau Methodology</th></tr>
      <tr><td>2005q1</td><td>12.62</td><td>14.80</td></tr>
      <tr><td>2024q1</td><td>9.80</td><td>11.38</td></tr>
    </table>
    <table>
      <tr><th>Quarter</th><th>Old Methodology</th><th>Credit Bureau Methodology</th></tr>
      <tr><td>2005q1</td><td>6.27</td><td>7.50</td></tr>
      <tr><td>2024q1</td><td>4.02</td><td>5.84</td></tr>
    </table>
    <table>
      <tr><th>Quarter</th><th>Old Methodology</th><th>Credit Bureau Methodology</th></tr>
      <tr><td>2005q1</td><td>6.35</td><td>7.30</td></tr>
      <tr><td>2024q1</td><td>5.78</td><td>5.55</td></tr>
    </table>
    </body></html>
    """

    rows = _fed_credit_bureau_household_dsr_records(html)

    assert len(rows) == 6
    assert rows[0]["date"] == "2005-03-31"
    assert rows[0]["component"] == "total_household_dsr"
    assert rows[-1]["component"] == "consumer_debt_dsr"
    assert rows[-1]["credit_bureau_methodology_dsr_pct_dpi"] == "5.55"
    assert {row["direct_required_payment_context_available"] for row in rows} == {
        "true"
    }
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_student_loan_payment_restart_parser_keeps_gate_fail_closed():
    html = """
    <html><body>
    <h1>Debt Payments and Spending: Evidence from the 2023 Student Loan Payment Restart</h1>
    <p>This unique natural experiment uses the Verisk Commerce Signals Spend Tracker.</p>
    <p>The data cover 55 million individuals and 89 million credit and debit cards.</p>
    <p>We combine it with Federal Reserve Bank of New York/Equifax Consumer Credit Panel data.</p>
    <p>The sample includes 18,178 ZIP codes and roughly $80 billion at an annual rate.</p>
    <p>The estimated effect is 0.3 percent of GDP.</p>
    <p>student loan payments began at different times.</p>
    </body></html>
    """
    accessible = """
    <html><body>
    <p>Post-Announcement and Payment Resumption estimates are reported.</p>
    <p>The post-announcement coefficient is estimated at -$6.20.</p>
    <p>The payment-resumption coefficient is estimated at -$12.20.</p>
    <p>95 percent confidence bands ranging from -$11 to -$2.</p>
    <p>95 percent confidence bands ranging from -$17 to -$7.</p>
    </body></html>
    """

    rows = _fed_student_loan_payment_restart_spending_records(html, accessible)

    assert len(rows) == 6
    assert rows[0]["date"] == "2025-09-05"
    assert rows[2]["metric"] == "post_announcement_spending_response_per_10000_debt"
    assert rows[2]["metric_value"] == "-6.20"
    assert rows[3]["metric"] == "payment_resumption_spending_response_per_10000_debt"
    assert rows[3]["metric_value"] == "-12.20"
    assert {
        row["debt_payment_spending_response_context_available"] for row in rows
    } == {"true"}
    assert {row["current_demand_response_context_available"] for row in rows} == {
        "false",
        "true",
    }
    assert {
        row["monetary_rate_shock_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {
        row["fast_repricing_credit_card_auto_context_available"] for row in rows
    } == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_credit_card_limit_increase_debt_parser_keeps_gate_fail_closed():
    html = """
    <html><body>
    <h1>More Credit, More Debt: New Evidence on Automated Credit Decisions</h1>
    <p>automated credit decisions are studied using Federal Reserve Y-14M regulatory data.</p>
    <p>The data cover more than 70 percent of the U.S. credit card market.</p>
    <p>About 12 percent of credit cards receive limit increases annually.</p>
    <p>They total about $160 billion dollars of new available credit each year.</p>
    <p>approximately 80 percent are bank initiated.</p>
    <p>revolving borrowers who carry balances month-to-month are targeted.</p>
    </body></html>
    """
    accessible = """
    <html><body>
    <h5>Figure 1. Credit limits over time, by credit score</h5>
    <p>subprime borrowers with credit scores below 600 are only $700.</p>
    <p>a 285 percent increase.</p>
    <p>superprime borrowers with credit scores above 760.</p>
    <h5>Figure 2. Limit increases among revolving and transacting accounts</h5>
    <p>roughly 2 percent of transactors and almost 4 percent of revolvers.</p>
    <h5>Figure 3. Revolving utilization around limit increases</h5>
    <p>within about 6 months, comprising about 30 percent of the credit limit increase.</p>
    </body></html>
    """

    rows = _fed_credit_card_limit_increase_debt_records(html, accessible)

    assert len(rows) == 8
    assert rows[0]["date"] == "2026-01-16"
    assert rows[1]["metric"] == "annual_limit_increase_incidence_context"
    assert rows[1]["metric_value"] == "12"
    assert rows[5]["metric"] == "six_month_debt_response_after_limit_increase_context"
    assert rows[5]["metric_value"] == "30"
    assert {row["fr_y14m_regulatory_data_context_available"] for row in rows} == {
        "true"
    }
    assert {row["credit_card_debt_response_context_available"] for row in rows} == {
        "true"
    }
    assert {row["underlying_account_microdata_publicly_reusable"] for row in rows} == {
        "false"
    }
    assert {
        row["monetary_rate_shock_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_credit_card_profitability_parser_keeps_gate_fail_closed():
    html = """
    <html><body>
    <h1>Credit Card Profitability</h1>
    <p>Measuring Credit Card Profitability Using the FR Y-14M Data</p>
    <p>We use a constant sample of 13 banks.</p>
    <p>covers about 80 percent of credit card balances.</p>
    <p>accounts with a revolving balance every month are heavy revolvers.</p>
    <p>accounts with a revolving balance in 1 to 11 months are light revolvers.</p>
    <p>accounts that did not have a revolving balance are transactors.</p>
    <h5>Table 1. Costs of Using a Credit Card</h5>
    <table>
      <tr><th></th><th>Heavy Revolvers</th><th></th><th>Light Revolvers</th><th></th><th>Transactors</th><th></th><th>Other</th><th></th></tr>
      <tr><th>Mean</th><th>Mean</th><th>Share (%)</th><th>Mean</th><th>Share (%)</th><th>Mean</th><th>Share (%)</th><th>Mean</th><th>Share (%)</th></tr>
      <tr><th>Number of Accounts (in millions)</th><td>63.1</td><td>20.33</td><td>79.02</td><td>25.47</td><td>66.62</td><td>21.47</td><td>97.72</td><td>32.73</td></tr>
      <tr><th>Purchase Volume</th><td>205.7</td><td>9.25</td><td>636.81</td><td>35.68</td><td>825.59</td><td>39.11</td><td>241.07</td><td>15.96</td></tr>
      <tr><th>Revolving Balance</th><td>4121</td><td>67.18</td><td>1072.72</td><td>21.85</td><td>27.27</td><td>0.47</td><td>459.58</td><td>10.55</td></tr>
      <tr><th>Spread</th><td>14.97</td><td>---</td><td>14.1</td><td>---</td><td>12.3</td><td>---</td><td>14.33</td><td>---</td></tr>
      <tr><th>Interest Charge</th><td>60.5</td><td>72.18</td><td>14.09</td><td>20.81</td><td>0.55</td><td>0.7</td><td>3.98</td><td>6.31</td></tr>
      <tr><th>Late Fee</th><td>3.05</td><td>47.59</td><td>1.47</td><td>28.83</td><td>0.32</td><td>5.19</td><td>0.79</td><td>18.39</td></tr>
    </table>
    </body></html>
    """

    rows = _fed_credit_card_profitability_revolver_records(html)

    assert len(rows) == 44
    heavy_interest = next(
        row
        for row in rows
        if row["metric"]
        == "credit_card_profitability_interest_charge_heavy_revolver_mean"
    )
    assert heavy_interest["metric_value"] == "60.5"
    assert heavy_interest["metric_unit"] == "monthly_dollars_per_account_or_share"
    heavy_interest_share = next(
        row
        for row in rows
        if row["metric"]
        == "credit_card_profitability_interest_charge_heavy_revolver_share"
    )
    assert heavy_interest_share["metric_value"] == "72.18"
    assert heavy_interest_share["metric_unit"] == "percent_share"
    assert {
        row["revolver_transactor_payment_burden_context_available"] for row in rows
    } == {"true"}
    assert {
        row["credit_card_payment_drag_magnitude_context_available"] for row in rows
    } == {"true"}
    assert {
        row["monetary_rate_shock_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_credit_card_delinquency_prediction_parser_keeps_gate_fail_closed():
    html = """
    <html><body>
    <h1>Predicting Credit Card Delinquency Rates</h1>
    <p>using as explanatory variables factors commonly believed to affect household credit performance</p>
    <p>interest rates, the unemployment rate, the level of indebtedness</p>
    <p>We estimate the model over the period from 2000:Q1</p>
    <p>The model shows an increase in delinquencies of about 120 basis points</p>
    <p>we cannot make causal inferences</p>
    </body></html>
    """
    accessible = """
    <html><body>
    <table>
      <tr><th>Date</th><th>Seasonally Adjusted Credit Card Delinquency Rate</th></tr>
      <tr><td>2000 Q1</td><td>4.42</td></tr>
    </table>
    <table>
      <tr><th>Date</th><th>Observed Seasonally Adjusted Credit Card Delinquency Rate</th><th>Predicted Seasonally Adjusted Credit Card Delinquency Rate</th><th>Lower 95% Confidence Bound on Prediction</th><th>Upper 95% Confidence Bound on Prediction</th></tr>
      <tr><td>2000 Q1</td><td>4.42</td><td>4.29</td><td>4.10</td><td>4.48</td></tr>
    </table>
    <table>
      <tr><th>Date</th><th>Prime Rate Contribution</th><th>Unemployment Rate Contribution</th><th>Real Revolving Credit Contribution</th><th>SLOOS Contribution</th><th>Nonprime Balance Share Contribution</th></tr>
      <tr><td>3/31/2000</td><td>-0.04</td><td>0.47</td><td>1.86</td><td>0.01</td><td>1.99</td></tr>
    </table>
    <table>
      <tr><th>Date</th><th>Observed Seasonally Adjusted Credit Card Delinquency Rate</th><th>Predicted Seasonally Adjusted Credit Card Delinquency Rate no Counterfactual</th><th>Predicted Seasonally Adjusted Credit Card Delinquency Rate with Counterfactual</th></tr>
      <tr><td>2016 Q1</td><td>2.46</td><td>2.47</td><td>2.47</td></tr>
    </table>
    </body></html>
    """

    rows = _fed_credit_card_delinquency_prediction_records(
        html_text=html,
        accessible_html=accessible,
    )

    assert len(rows) == 12
    first_table = next(
        row
        for row in rows
        if row["metric"]
        == (
            "credit_card_delinquency_prediction_"
            "seasonally_adjusted_credit_card_delinquency_rate"
        )
    )
    assert first_table["date"] == "2000-03-31"
    assert json.loads(first_table["metric_value"]) == {
        "seasonally_adjusted_credit_card_delinquency_rate": "4.42"
    }
    model_summary = next(
        row
        for row in rows
        if row["metric"] == "preferred_model_adjusted_r_squared_context"
    )
    assert model_summary["metric_value"] == "0.97"
    assert {row["rate_sensitive_model_context_available"] for row in rows} == {"true"}
    assert {
        row["monetary_rate_shock_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_consumer_delinquency_dynamics_parser_keeps_gate_fail_closed():
    html = """
    <html><body>
    <h1>A Note on Recent Dynamics of Consumer Delinquency Rates</h1>
    <p>Federal Reserve Bank of New York Consumer Credit Panel/Equifax</p>
    <p>nationally representative random sample of anonymized Equifax credit bureau data</p>
    <p>credit card and auto loan delinquency rates</p>
    <p>across credit scores, income groups, and by homeownership status</p>
    </body></html>
    """
    table_templates = [
        (
            "Date",
            ["Credit Card Delinquency Rate", "Auto Loan Delinquency Rate"],
            "3/31/2000",
            ["4.42", "3.27"],
        ),
        (
            "Date",
            ["Share of Subprime Borrowers", "Share of Nearprime Borrowers"],
            "3/31/2003",
            ["27.97", "26.84"],
        ),
        (
            "Date",
            ["Year-Over-Year Change in the Credit Card Delinquency Rate"],
            "3/31/2001",
            ["0.71"],
        ),
        (
            "Date",
            ["Year-Over-Year Change in the Auto Loan Delinquency Rate"],
            "3/31/2001",
            ["0.42"],
        ),
        (
            "Quarters since origination",
            ["2011-2019 Vintage Average", "2020 Vintage"],
            "0",
            ["0.1", "0.0"],
        ),
        (
            "Date",
            ["Subprime Credit Card Delinquency Rate"],
            "3/31/2000",
            ["14.56"],
        ),
        (
            "Date",
            ["Subprime Auto Loan Delinquency Rate"],
            "3/31/2000",
            ["9.11"],
        ),
        (
            "Date",
            ["Credit Card Delinquency Rate in Low-Income Census Tracts"],
            "6/30/2014",
            ["3.82"],
        ),
        (
            "Date",
            ["Auto Loan Delinquency Rate in Low-Income Census Tracts"],
            "6/30/2014",
            ["5.76"],
        ),
        (
            "Date",
            ["Credit Card Delinquency Rate for Mortgage Borrowers"],
            "3/31/2000",
            ["3.32"],
        ),
        (
            "Date",
            ["Auto Loan Delinquency Rate for Mortgage Borrowers"],
            "3/31/2000",
            ["2.08"],
        ),
    ]
    tables = []
    for first_header, headers, row_label, values in table_templates:
        header_html = "".join(
            f"<th>{header}</th>" for header in [first_header, *headers]
        )
        row_html = "".join(f"<td>{value}</td>" for value in [row_label, *values])
        tables.append(f"<table><tr>{header_html}</tr><tr>{row_html}</tr></table>")
    accessible = "<html><body>" + "".join(tables) + "</body></html>"

    rows = _fed_consumer_delinquency_dynamics_records(
        html_text=html,
        accessible_html=accessible,
    )

    assert len(rows) == 11
    aggregate = rows[0]
    assert aggregate["date"] == "2000-03-31"
    assert json.loads(aggregate["metric_value"]) == {
        "auto_loan_delinquency_rate": "3.27",
        "credit_card_delinquency_rate": "4.42",
    }
    vintage = next(
        row for row in rows if row["source_row_axis"] == "quarters_since_origination"
    )
    assert vintage["date"] == "2025-11-24"
    assert {row["ccp_equifax_context_available"] for row in rows} == {"true"}
    assert {
        row["monetary_rate_shock_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_credit_card_rewards_limit_spending_parser_keeps_gate_fail_closed():
    index_html = """
    <html><body>
    <h1>Who Pays For Your Rewards? Redistribution in the Credit Card Market</h1>
    <p>credit card data from the Federal Reserve Board's Y-14M reports are used.</p>
    <p>We study a bank-initiated credit limit increase.</p>
    <p>The dependent variable is the change in average spending, repayments, or unpaid balances between the 6-month period before and the 6-month period after the credit limit increase.</p>
    <p><strong>Table 6:  Overindebtedness: Difference-in-Differences Analysis</strong></p>
    <table>
      <tr><th></th><th>Delta Spending(1)</th><th>Delta Spending(2)</th><th>Delta Payments(3)</th><th>Delta Payments(4)</th><th>Delta Unpaid Balances(5)</th><th>Delta Unpaid Balances (6)</th></tr>
      <tr><td>Reward Card</td><td>75.77*** (6.83)</td><td></td><td>31.96*** (3.72)</td><td></td><td>19.17** (8.79)</td><td></td></tr>
      <tr><td>Reward Card x Sub-Prime</td><td></td><td>59.75*** (6.43)</td><td></td><td>5.06 (3.12)</td><td></td><td>33.82*** (11.24)</td></tr>
      <tr><td>Reward Card x Near-Prime</td><td></td><td>62.88*** (7.18)</td><td></td><td>4.53 (4.29)</td><td></td><td>25.25* (13.53)</td></tr>
      <tr><td>Reward Card x Prime</td><td></td><td>89.03*** (7.98)</td><td></td><td>73.19*** (6.17)</td><td></td><td>4.83 (12.16)</td></tr>
      <tr><td>Reward Card x Super-Prime</td><td></td><td>164.85*** (14.14)</td><td></td><td>153.22*** (13.22)</td><td></td><td>-28.20 (25.26)</td></tr>
      <tr><td>* Observations</td><td>1,236,604</td><td>1,236,604</td><td>1,236,604</td><td>1,236,604</td><td>1,236,604</td><td>1,236,604</td></tr>
    </table>
    </body></html>
    """
    accessible_figures_html = "<html><body>Accessible version of figures</body></html>"

    rows = _fed_credit_card_rewards_limit_spending_records(
        index_html=index_html,
        accessible_figures_html=accessible_figures_html,
    )

    assert len(rows) == 21
    assert rows[0]["metric_value"] == "75.77"
    assert rows[0]["standard_error"] == "6.83"
    assert rows[0]["significance_stars"] == "***"
    assert rows[0]["evidence_family"] == "current_demand_response_context"
    assert any(
        row["source_row_label"] == "Reward Card x Sub-Prime"
        and row["source_column_label"] == "Delta Unpaid Balances (6)"
        and row["metric_value"] == "33.82"
        for row in rows
    )
    assert {row["fr_y14m_regulatory_data_context_available"] for row in rows} == {
        "true"
    }
    assert {row["current_demand_conversion_available"] for row in rows} == {"false"}
    assert {
        row["monetary_rate_shock_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {
        row["underlying_y14m_account_microdata_publicly_reusable"] for row in rows
    } == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_auto_loan_payment_delinquency_parser_keeps_gate_fail_closed():
    html = """
    <html><body>
    <h1>Rising Auto Loan Delinquencies and High Monthly Payments</h1>
    <p>auto loans are an important sector in consumer credit, accounting for about 25 percent of nonmortgage consumer credit.</p>
    <p>We use the New York Federal Reserve Consumer Credit Panel data and Experian AutoCount.</p>
    <p>one percent random sample of all auto loans originated between 2017 and 2022.</p>
    <p>average required monthly payments increased from $470 to about $600.</p>
    <p>larger auto loan amount at origination, rather than the increases in interest rates.</p>
    <p>around 37 percent of auto loan balances comprise loans originated in the previous 12 months.</p>
    <p>Table 1 reports log monthly payment.</p>
    </body></html>
    """
    accessible = """
    <html><body>
    <h5>Figure 1. Auto Loan Delinquency Rates</h5>
    <h5>Figure 2. Cumulative Delinquency</h5>
    <h5>Figure 3. Average Monthly Payment</h5>
    <h5>Figure 4. Average Loan Size and Interest Rate</h5>
    </body></html>
    """

    rows = _fed_auto_loan_payment_delinquency_records(html, accessible)

    assert len(rows) == 10
    assert rows[0]["date"] == "2024-09-26"
    assert rows[0]["metric"] == "auto_share_of_nonmortgage_consumer_credit_context"
    assert rows[4]["metric"] == "average_required_monthly_payment_increase_context"
    assert rows[4]["metric_value"] == "470_to_600"
    assert rows[5]["metric"] == "log_payment_delinquency_lpm_spec3_context"
    assert rows[5]["metric_value"] == "0.029"
    assert {row["auto_loan_payment_context_available"] for row in rows} == {"true"}
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {
        row["monetary_rate_shock_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {
        row["underlying_ccp_experian_microdata_publicly_reusable"] for row in rows
    } == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_auto_loan_prepayment_maturity_parser_keeps_gate_fail_closed():
    index_html = """
    <html><body>
    <h1>One Month Longer, One Month Later? Prepayments in the Auto Loan Market</h1>
    <p>Analyzing more than half of the auto loans originated during the past 16 years.</p>
    <p>longer-maturity new car loans have significantly higher interest rates.</p>
    <p>the majority of auto loans were prepaid.</p>
    <p>liquidity constraints, uncertainty about future income, and monthly payment targeting.</p>
    </body></html>
    """
    figure1_rows = "\n".join(
        f"{year} {64 + year - 2008:.2f} {60 + year - 2008:.2f}"
        for year in range(2008, 2024)
    )
    figure7_rows = "\n".join(
        f"{year} {0.70 - ((year - 2002) * 0.01):.2f} "
        f"{0.60 - ((year - 2002) * 0.01):.2f}"
        if year <= 2017
        else f"{year} {0.50 - ((year - 2018) * 0.01):.2f}"
        for year in range(2002, 2024)
    )
    paid_rows = "\n".join(
        f"{43101 + month} {101 + (month / 100):.2f}%" for month in range(72)
    )
    accessible_figures_html = f"""
    <html><body>
    <h5>Figure 1: Recent Trend of Average Auto Loan Maturity</h5>
    <p>year New car loans Used car loans
    {figure1_rows}
    Return to text</p>
    <h5>Figure 7: Trends of Prepayments of Auto Loans</h5>
    <p>year By year of payoff By year of origination
    {figure7_rows}
    Return to text</p>
    <p>Month paid_over_scheduled
    {paid_rows}
    Return to text</p>
    </body></html>
    """

    rows = _fed_auto_loan_prepayment_maturity_records(
        index_html=index_html,
        accessible_figures_html=accessible_figures_html,
    )

    assert len(rows) == 145
    assert rows[0]["date"] == "2008-12-31"
    assert rows[0]["metric"] == "auto_loan_average_maturity_new_car_loans"
    assert rows[0]["metric_value"] == "64"
    assert rows[32]["metric"] == "auto_loan_prepayment_share_by_payoff_year"
    assert rows[70]["metric"] == "auto_loan_actual_paid_over_scheduled_payment"
    assert rows[-1]["metric"] == "promotion_blocker_context"
    assert {row["auto_loan_maturity_context_available"] for row in rows} == {"true"}
    assert {row["auto_loan_prepayment_context_available"] for row in rows} == {"true"}
    assert {row["auto_loan_payment_behavior_context_available"] for row in rows} == {
        "true"
    }
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {
        row["monetary_rate_shock_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {row["public_borrower_level_microdata_available"] for row in rows} == {
        "false"
    }
    assert {
        row["underlying_auto_loan_microdata_publicly_reusable"] for row in rows
    } == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_cfpb_tccp_survey_parser_keeps_gate_fail_closed(tmp_path):
    headers = [
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
    ]
    source_xlsx = tmp_path / "tccp.xlsx"
    _write_minimal_shared_string_xlsx(
        source_xlsx,
        {
            10: {index: header for index, header in enumerate(headers, start=2)},
            11: {
                2: "Example Bank",
                3: "1",
                4: "Variable Rewards",
                5: "Data as of June 30",
                6: "National",
                7: "No",
                8: "Credit scores from 620 to 719",
                9: "Yes",
                10: "Yes",
                11: "Prime",
                12: "V",
                13: "Yes",
                14: "",
                15: "",
                16: "0.2299",
                17: "",
                18: "0.1999",
                19: "0.2199",
                20: "0.2499",
                21: "Yes",
                22: "25",
            },
        },
    )

    rows = _cfpb_tccp_survey_records(source_xlsx)

    assert len(rows) == 1
    assert rows[0]["date"] == "2025-06-30"
    assert rows[0]["purchase_apr_good_pct"] == "22.99"
    assert rows[0]["purchase_apr_min_pct"] == "19.99"
    assert rows[0]["variable_rate_index_context_available"] == "true"
    assert rows[0]["rate_sensitive_pricing_terms_context_available"] == "true"
    assert rows[0]["rate_sensitive_payment_drag_transmission_available"] == "false"
    assert rows[0]["current_demand_conversion_available"] == "false"
    assert rows[0]["split_denominator_promotion_allowed"] == "false"
    assert rows[0]["main_ratio_admission_allowed"] == "false"


def test_philadelphia_fed_y14_parser_keeps_gate_fail_closed(tmp_path):
    balances_csv = tmp_path / "balances.csv"
    originations_csv = tmp_path / "originations.csv"
    balance_values = {
        "YRQTR": "2012Q3",
        "Total Balances ($Billions)": "$571.03",
        "Number of Accounts (Millions)": "513.95",
        "Share of Accounts Making the Minimum Payment": "8.78 %",
        "Share of Accounts Making Greater Than the Minimum Payment but Less Than the Full Balance": "32.32 %",
        "Share of Accounts Making the Full Balance Payment": "26.37 %",
        "Revolving Balances Only ($Billions)": "$412.26",
        "Average Purchase APR: General Purpose": "16.80 %",
        "Average Purchase APR: Private Label": "23.84 %",
        "Total Purchase Volume ($Billions)": "$316.89",
        "Average Purchase Volume by Credit Score Group: <660 Credit Score": "$242.19",
        "Average Purchase Volume by Credit Score Group: 660-719 Credit Score": "$579.52",
        "Average Purchase Volume by Credit Score Group: >=720 Credit Score": "$1,216.93",
    }
    origination_values = {
        "YRQTR": "2012Q3",
        "New Originations ($Billions)": "$57.91",
        "Number of New Accounts (Millions)": "15.06",
        "Original Credit Score (50th percentile)": "730",
        "Average Original Purchase APR: General Purpose": "18.97 %",
        "Average Original Purchase APR: Private Label": "25.51 %",
        "Percentage of New Accounts with <660 Credit Score": "20.49 %",
        "Percentage of New Commitments with <660 Credit Score": "5.85 %",
    }
    with balances_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(PHILLY_FED_Y14_BALANCES_REQUIRED_COLUMNS)
        )
        writer.writeheader()
        writer.writerow(balance_values)
    with originations_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(PHILLY_FED_Y14_ORIGINATION_REQUIRED_COLUMNS)
        )
        writer.writeheader()
        writer.writerow(origination_values)

    rows = _philadelphia_fed_y14_credit_card_records(
        balances_csv=balances_csv,
        originations_csv=originations_csv,
    )

    assert len(rows) == 2
    assert rows[0]["date"] == "2012-09-30"
    assert rows[0]["total_balances_bil"] == "571.03"
    assert rows[0]["share_accounts_minimum_payment_pct"] == "8.78"
    assert rows[0]["payment_behavior_context_available"] == "true"
    assert rows[0]["purchase_volume_context_available"] == "true"
    assert rows[0]["current_demand_response_available"] == "false"
    assert rows[0]["rate_sensitive_payment_drag_transmission_available"] == "false"
    assert rows[0]["main_ratio_admission_allowed"] == "false"
    assert rows[1]["source_table"] == "credit_card_originations"
    assert rows[1]["new_originations_bil"] == "57.91"
    assert rows[1]["origination_context_available"] == "true"
    assert rows[1]["split_denominator_promotion_allowed"] == "false"


def test_cfpb_payment_amount_furnishing_parser_keeps_gate_fail_closed():
    report_text = """
    Payment Amount Furnishing & Consumer Reporting
    approximately five million de-identified credit records
    borrowers' actual payment
    TABLE 1:
    current tradelines with actual payment information
    actual payment amount furnished
    Credit card 464 285 40%
    Retail revolving 212 80 71%
    Student loan 112 50 91%
    Auto 94 84 91%
    Mortgage 70 66 95%
    Other 60 48 93%
    All loan types 1,011 613 65%
    """

    rows = _cfpb_payment_amount_furnishing_records(report_text)

    assert len(rows) == 7
    credit_card = next(row for row in rows if row["loan_type"] == "credit_card")
    assert credit_card["date"] == "2020-03-31"
    assert credit_card["actual_payment_amount_furnished_pct"] == "40"
    assert credit_card["actual_payment_furnishing_context_available"] == "true"
    assert credit_card["revolving_credit_payment_gap_context_available"] == "true"
    assert {row["borrower_level_microdata_available"] for row in rows} == {"false"}
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {row["denominator_prior_narrowing_allowed"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_cfpb_credit_card_revolvers_parser_keeps_gate_fail_closed():
    report_text = """
    DATA POINT: CREDIT CARD REVOLVERS
    The data used in this analysis comprise a panel of de-identified
    account-level information from a sample of large banks' credit card
    portfolios between April 2008 and April 2016. The database covers
    approximately 85 percent of all credit card accounts. For every account-month
    pair, the data contain information on the balance at the end of cycle balance,
    total payments made, and the associated cardholders' credit score.
    Figure 2 illustrates the duration of continuous revolving on an account,
    and defines a revolving episode. Figure 3 shows patterns of repayment.
    Among active accounts, two of every three are revolvers. Transitions in and
    out of credit card debt are rare, occurring in 1 in 10 accounts each month.
    Among accounts held by Deep-Subprime borrowers, about 85 percent revolve,
    with only 1 in 20 accounts transitioning in any given month.
    The likelihood that a prime episode will last 6 months or more is 40 percent.
    About 12 percent of prime and 20 percent of subprime episodes last for more
    than 2 years. On average, revolving episodes for prime and subprime accounts
    last for 9 and 13 months, respectively. In an average month, nearly
    82 percent of outstanding balances are revolved. Approximately 70 percent
    revolved balances, or 70 cents of each dollar borrowed, accrue to accounts
    revolving continuously for a year or more.
    """

    rows = _cfpb_credit_card_revolvers_records(report_text)

    assert len(rows) == 12
    by_metric = {row["metric"]: row for row in rows}
    assert by_metric["ccdb_credit_card_account_coverage"]["metric_value"] == "85"
    assert by_metric["mean_prime_revolving_episode_duration"]["metric_unit"] == "months"
    assert by_metric["outstanding_balance_revolved_share"]["metric_value"] == "82"
    assert {row["payment_behavior_context_available"] for row in rows} == {"true"}
    assert {row["revolving_duration_context_available"] for row in rows} == {"true"}
    assert {row["public_borrower_level_microdata_available"] for row in rows} == {
        "false"
    }
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {row["denominator_prior_narrowing_allowed"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_cfpb_credit_card_market_report_parser_keeps_gate_fail_closed():
    report_text = """
    In 2024, the average annual percentage rate (APR) reached 25.2 percent
    for consumer credit cards. Average APR for new general purpose accounts
    opened in 2024 was 27.5 percent. The share of cardholders making only the
    minimum payment in 2024 was at 14 percent; made only the minimum payment,
    up from 13 percent in our last report. Consumers were assessed $160 billion
    in interest charges. The prime rate, the benchmark commercial banks use to
    set APRs, increased a total of 5.1 percentage points, driving most of the
    increase in APRs because almost all general purpose account interest rates
    are tied to a variable rate index. Increases to APR margin are typically
    reflected on new accounts and less frequently on existing accounts. The
    timing of these changes is open-ended and at the discretion of the lender.
    This report does not attribute a specific factor or group of factors to
    explain an issuer's motivation for changes to the APR margin.
    """

    rows = _cfpb_credit_card_market_report_records(report_text)

    assert len(rows) == 8
    by_metric = {row["metric"]: row for row in rows}
    assert by_metric["average_apr_2024_all_cards"]["metric_value"] == "25.2"
    assert by_metric["interest_charges_assessed_2024"]["metric_value"] == "160"
    assert by_metric["prime_rate_increase_2022_2023"]["metric_unit"] == (
        "percentage_points"
    )
    assert {row["apr_repricing_context_available"] for row in rows} == {"true"}
    assert {row["variable_index_rate_context_available"] for row in rows} == {"true"}
    assert {row["issuer_margin_attribution_available"] for row in rows} == {"false"}
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {row["denominator_prior_narrowing_allowed"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_cfpb_credit_card_interest_payment_mechanics_keeps_gate_fail_closed():
    guidance_html = """
    <html><body>
    <h1>How does my credit card company calculate the amount of interest I owe?</h1>
    <p>Many credit card companies calculate the interest you owe daily, based
    on your average daily balance.</p>
    <p>The interest charged daily is called the daily periodic rate.</p>
    <p>If your card has a grace period, you can avoid paying interest.</p>
    <p>When you pay less than the full balance but more than the minimum
    required, the card issuer must generally apply the amount you pay over the
    minimum first to the balance with the highest interest rate.</p>
    </body></html>
    """
    regulation_html = """
    <html><body>
    <h1>Allocation of payments</h1>
    <p>Payment in excess of the required minimum periodic payment for a credit
    card account under an open-end consumer credit plan must be allocated first
    to the balance with the highest annual percentage rate.</p>
    <p>Required minimum periodic payment context remains source-gated.</p>
    </body></html>
    """

    rows = _cfpb_credit_card_interest_payment_mechanics_records(
        guidance_html, regulation_html
    )

    assert len(rows) == 6
    assert any(
        row["metric"] == "excess_payment_high_apr_allocation_context" for row in rows
    )
    assert {row["source_schema_reviewed"] for row in rows} == {"true"}
    assert {
        row["rate_sensitive_payment_mechanics_context_available"] for row in rows
    } == {"true"}
    assert {row["apr_to_finance_charge_mechanics_available"] for row in rows} == {
        "true"
    }
    assert {row["payment_allocation_mechanics_available"] for row in rows} == {"true"}
    assert {
        row["monetary_rate_shock_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_response_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_cfpb_mem_sample1_parser_keeps_gate_fail_closed(tmp_path):
    source_zip = tmp_path / "mem_sample1.zip"
    header = [
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
    ]
    codebook_markers = "\n".join(
        [
            "Has a credit card",
            "Unpaid credit card balance after last payment",
            "Expected change in credit card balance carried",
            "Used a credit card",
            "HH balance in checking/savings accounts",
            "Amount of $2,000 expense HH could pay within a week",
            "How long HH could cover expenses if HH lost main income source",
            "Expect to have difficulty paying for a bill/expense",
            "Past 12 months: Had difficulty with a bill/expense",
            "Paid another bill late or skipped a payment",
            "Cut back on other expenses",
            "HH annual income in 2018",
            "HH income variability",
            "Expectation for HH income in next year",
            "Last time checked credit score or report",
            "Source of credit score or report",
            "Credit score change since last time checked",
        ]
    )
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr(
            "Sample1/MEM_S1W1W2W3_PUF.csv",
            ",".join(header) + "\n" + ",".join(["1"] * len(header)) + "\n",
        )
        archive.writestr("Sample1/MEM_S1W1W2W3_PUF_codebook.txt", codebook_markers)
        archive.writestr("Sample1/README.txt", "readme")
        archive.writestr("Sample1/MEM PUF User Guide.pdf", b"%PDF-1.4\n")

    rows = _cfpb_mem_sample1_public_use_records(source_zip)

    assert len(rows) == 1
    assert rows[0]["source_csv_row_count"] == "1"
    assert rows[0]["source_csv_column_count"] == str(len(header))
    assert rows[0]["borrower_level_public_survey_microdata_available"] == "true"
    assert rows[0]["credit_card_payment_behavior_context_available"] == "true"
    assert rows[0]["liquidity_context_available"] == "true"
    assert rows[0]["bill_payment_stress_context_available"] == "true"
    assert rows[0]["borrower_level_credit_bureau_microdata_available"] == "false"
    assert rows[0]["minimum_payment_behavior_context_available"] == "false"
    assert rows[0]["rate_sensitive_payment_drag_transmission_available"] == "false"
    assert rows[0]["current_demand_conversion_available"] == "false"
    assert rows[0]["split_denominator_promotion_allowed"] == "false"
    assert rows[0]["main_ratio_admission_allowed"] == "false"


def test_cfpb_mem_multisample_parser_keeps_gate_fail_closed(tmp_path):
    sample_zips = {}
    for sample in (3, 4, 5, 6):
        prefix = f"Sample{sample}"
        csv_name = {
            3: "MEM_S3W1W2_PUF.csv",
            4: "MEM_S4W1W2_PUF.csv",
            5: "MEM_S5W1W2_PUF.csv",
            6: "MEM_S6W_PUF.csv",
        }[sample]
        codebook_name = {
            3: "MEM_S3W1W2_PUF_codebook.txt",
            4: "MEM_S4W1W2_PUF_codebook.txt",
            5: "MEM_S5W1W2PUF_codebook.txt",
            6: "MEM_S6W1PUF_codebook.txt",
        }[sample]
        source_zip = tmp_path / f"mem_sample{sample}.zip"
        with zipfile.ZipFile(source_zip, "w") as archive:
            archive.writestr(
                f"{prefix}/{csv_name}",
                "ID,weight,q1\n1,1,1\n",
            )
            archive.writestr(
                f"{prefix}/{codebook_name}",
                "\n".join(
                    [
                        "credit card",
                        "balance",
                        "savings",
                        "checking",
                        "difficulty",
                        "expense",
                        "income",
                        "unexpected",
                    ]
                ),
            )
            archive.writestr(f"{prefix}/README.txt", "readme")
            archive.writestr(f"{prefix}/MEM PUF User Guide.pdf", b"%PDF-1.4\n")
        sample_zips[sample] = source_zip

    rows = _cfpb_mem_multisample_public_use_records(sample_zips)

    assert [row["sample_id"] for row in rows] == [
        "sample_3",
        "sample_4",
        "sample_5",
        "sample_6",
    ]
    assert {row["source_csv_row_count"] for row in rows} == {"1"}
    assert {row["id_column_present"] for row in rows} == {"true"}
    assert {row["weight_columns_present"] for row in rows} == {"true"}
    assert {
        row["borrower_level_public_survey_microdata_available"] for row in rows
    } == {"true"}
    assert {row["credit_card_payment_behavior_context_available"] for row in rows} == {
        "true"
    }
    assert {row["liquidity_context_available"] for row in rows} == {"true"}
    assert {row["bill_payment_stress_context_available"] for row in rows} == {"true"}
    assert {
        row["borrower_level_credit_bureau_microdata_available"] for row in rows
    } == {"false"}
    assert {
        row["rate_sensitive_payment_drag_transmission_available"] for row in rows
    } == {"false"}
    assert {row["current_demand_conversion_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_cre_high_growth_deposit_parser_keeps_gate_fail_closed():
    html = """
    <h3>Figure 1. CRE Origination Index</h3>
    <p>Source: CRE Public Records and FR Y-14Q.</p>
    <h3>Figure 2. Relative Importance of High-Growth Banks</h3>
    <p>Source: CRE Public Records, FR Y-9C, and Call Reports.</p>
    <h3>Figure 3. Portfolio Composition of CRE Loan Types</h3>
    <p>Source: CRE Public Records.</p>
    <h3>Figure 4. CRE Loan Growth and Deposit Funding Share in the Same CBSA</h3>
    <p>Source: Summary of Deposits and CRE Public Records.</p>
    """

    rows = _fed_cre_high_growth_deposit_records(html)

    assert len(rows) == 9
    assert rows[0]["metric"] == "cre_origination_index_high_growth_bank_context"
    assert rows[1]["cre_lender_exposure_context_available"] == "true"
    assert rows[3]["local_deposit_funding_context_available"] == "true"
    assert {row["cre_refinancing_outcome_available"] for row in rows} == {"false"}
    assert {row["cre_real_activity_mapping_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_atlanta_fed_cremi_longweights_parser_records_context_only_blocker():
    csv_text = "\n".join(
        [
            '"","Geography.Name","CBSA.Code","Asset_Type","variable","value"',
            '"1","Atlanta - GA","12060","Office","NOI.Index","12.5"',
            '"2","Atlanta - GA","12060","Office","Market.Cap.Rate","8.0"',
            '"3","Atlanta - GA","12060","Office","Asset.Value","10.0"',
            '"4","Atlanta - GA","12060","Office","Occupancy.Rate","9.0"',
        ]
    )
    page_html = """
    <p>Net Operating Income Index</p>
    <p>Market Cap Rate</p>
    <p>Asset Value</p>
    <p>the data provider does not allow the Federal Reserve Bank of Atlanta to share them externally</p>
    """

    rows = _atlanta_fed_cremi_longweights_records(csv_text, page_html)

    assert len(rows) == 4
    assert {row["source_csv_schema_reviewed"] for row in rows} == {"true"}
    assert rows[0]["cre_noi_context_available"] == "true"
    assert rows[1]["cre_cap_rate_context_available"] == "true"
    assert rows[2]["cre_asset_value_context_available"] == "true"
    assert {
        row["raw_noi_cap_rate_asset_value_source_publicly_shareable"] for row in rows
    } == {"false"}
    assert {row["cre_refinancing_outcome_available"] for row in rows} == {"false"}
    assert {row["cre_real_activity_mapping_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_cre_evergreening_extension_terms_parser_keeps_gate_fail_closed():
    html_text = """
    <html><body>
    <h1>Pretend or Amend? On Evergreening in CRE</h1>
    </body></html>
    """
    pdf_text = """
    Using detailed supervisory data, the paper studies maturity extensions.
    Debt yield is net operating income as a share of the loan balance.
    Banks increased principal paydown requirements, additional guarantees,
    and higher loan spreads after 2022.
    """

    rows = _fed_cre_evergreening_extension_terms_records(html_text, pdf_text)

    assert len(rows) == 6
    assert {row["source_html_schema_reviewed"] for row in rows} == {"true"}
    assert {row["source_pdf_text_reviewed"] for row in rows} == {"true"}
    assert any(row["cre_noi_debt_yield_context_available"] == "true" for row in rows)
    assert any(
        row["cre_principal_paydown_extension_terms_context_available"] == "true"
        for row in rows
    )
    assert any(
        row["cre_higher_spread_guarantee_extension_terms_context_available"] == "true"
        for row in rows
    )
    assert {row["underlying_supervisory_data_publicly_reusable"] for row in rows} == {
        "false"
    }
    assert {row["cre_dscr_context_available"] for row in rows} == {"false"}
    assert {row["cre_real_activity_mapping_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_sec_abs_ee_cmbs_asset_property_parser_keeps_gate_fail_closed():
    xml = """<?xml version="1.0" encoding="utf-8"?>
    <assetData xmlns="http://www.sec.gov/edgar/document/absee/cmbs/assetdata">
      <assets>
        <assetTypeNumber>Prospectus Loan ID</assetTypeNumber>
        <assetNumber>1</assetNumber>
        <GroupID>1</GroupID>
        <reportingPeriodBeginningDate>02-12-2026</reportingPeriodBeginningDate>
        <reportingPeriodEndDate>03-11-2026</reportingPeriodEndDate>
        <originatorName>Example Originator</originatorName>
        <originationDate>07-15-2024</originationDate>
        <originalLoanAmount>75000000.00000000</originalLoanAmount>
        <originalTermLoanNumber>60</originalTermLoanNumber>
        <maturityDate>08-06-2029</maturityDate>
        <originalInterestRatePercentage>.07380000</originalInterestRatePercentage>
        <interestRateSecuritizationPercentage>.07380000</interestRateSecuritizationPercentage>
        <originalInterestRateTypeCode>1</originalInterestRateTypeCode>
        <interestOnlyIndicator>true</interestOnlyIndicator>
        <balloonIndicator>true</balloonIndicator>
        <modifiedIndicator>false</modifiedIndicator>
        <scheduledPrincipalBalanceSecuritizationAmount>75000000.00000000</scheduledPrincipalBalanceSecuritizationAmount>
        <reportPeriodBeginningScheduleLoanBalanceAmount>75000000.00000000</reportPeriodBeginningScheduleLoanBalanceAmount>
        <totalScheduledPrincipalInterestDueAmount>461250.00000000</totalScheduledPrincipalInterestDueAmount>
        <reportPeriodInterestRatePercentage>.07380000</reportPeriodInterestRatePercentage>
        <scheduledInterestAmount>461250.00000000</scheduledInterestAmount>
        <scheduledPrincipalAmount>.00000000</scheduledPrincipalAmount>
        <reportPeriodEndActualBalanceAmount>75000000.00000000</reportPeriodEndActualBalanceAmount>
        <reportPeriodEndScheduledLoanBalanceAmount>75000000.00000000</reportPeriodEndScheduledLoanBalanceAmount>
        <paidThroughDate>03-06-2026</paidThroughDate>
        <paymentStatusLoanCode>0</paymentStatusLoanCode>
        <primaryServicerName>Example Servicer</primaryServicerName>
        <property>
          <propertyName>Example Hotel</propertyName>
          <propertyCity>New York</propertyCity>
          <propertyState>NY</propertyState>
          <propertyTypeCode>LO</propertyTypeCode>
          <valuationSecuritizationAmount>161000000.00000000</valuationSecuritizationAmount>
          <mostRecentValuationAmount>161000000.00000000</mostRecentValuationAmount>
          <physicalOccupancySecuritizationPercentage>.82000000</physicalOccupancySecuritizationPercentage>
          <mostRecentPhysicalOccupancyPercentage>.85000000</mostRecentPhysicalOccupancyPercentage>
          <propertyStatusCode>0</propertyStatusCode>
          <financialsSecuritizationDate>12-31-2025</financialsSecuritizationDate>
          <mostRecentFinancialsStartDate>01-01-2025</mostRecentFinancialsStartDate>
          <mostRecentFinancialsEndDate>12-31-2025</mostRecentFinancialsEndDate>
          <netOperatingIncomeSecuritizationAmount>10700000.00000000</netOperatingIncomeSecuritizationAmount>
          <mostRecentNetOperatingIncomeAmount>10800000.00000000</mostRecentNetOperatingIncomeAmount>
          <netCashFlowFlowSecuritizationAmount>10000000.00000000</netCashFlowFlowSecuritizationAmount>
          <mostRecentNetCashFlowAmount>10100000.00000000</mostRecentNetCashFlowAmount>
          <mostRecentDebtServiceAmount>5535000.00000000</mostRecentDebtServiceAmount>
          <debtServiceCoverageNetOperatingIncomeSecuritizationPercentage>1.93000000</debtServiceCoverageNetOperatingIncomeSecuritizationPercentage>
          <mostRecentDebtServiceCoverageNetOperatingIncomePercentage>1.95000000</mostRecentDebtServiceCoverageNetOperatingIncomePercentage>
          <debtServiceCoverageNetCashFlowSecuritizationPercentage>1.81000000</debtServiceCoverageNetCashFlowSecuritizationPercentage>
          <mostRecentDebtServiceCoverageNetCashFlowpercentage>1.83000000</mostRecentDebtServiceCoverageNetCashFlowpercentage>
          <mostRecentDebtServiceCoverageCode>0</mostRecentDebtServiceCoverageCode>
        </property>
      </assets>
    </assetData>
    """
    rows = _sec_abs_ee_cmbs_asset_property_records(
        filing={
            "trust_name": "Example CMBS Trust",
            "cik": "2027304",
            "accession_number": "0001888524-26-006627",
            "filing_date": "2026-04-01",
            "period_of_report": "2026-03-17",
            "xml_document": "exh_102.xml",
        },
        source_xml=xml,
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["date"] == "2026-03-11"
    assert row["propertyName"] == "Example Hotel"
    assert row["cre_dscr_context_available"] == "true"
    assert row["cre_noi_context_available"] == "true"
    assert row["cre_occupancy_context_available"] == "true"
    assert row["cre_payment_status_context_available"] == "true"
    assert row["row_support_status"] == "public_asset_property_dscr_noi_payment_context"
    assert row["cre_refinancing_outcome_available"] == "false"
    assert row["cre_real_activity_mapping_available"] == "false"
    assert row["split_denominator_promotion_allowed"] == "false"


def test_sec_abs_ee_cmbs_asset_time_dimension_keeps_gate_fail_closed():
    records = [
        {
            "date": "2026-03-11",
            "trust_name": "Example CMBS Trust",
            "cik": "2027304",
            "accession_number": "0001888524-26-006627",
            "filing_date": "2026-04-01",
            "period_of_report": "2026-03-17",
            "assetNumber": "1",
            "property_index": "1",
            "reportPeriodEndActualBalanceAmount": "75000000.00000000",
            "reportPeriodEndScheduledLoanBalanceAmount": "75000000.00000000",
            "paymentStatusLoanCode": "0",
            "paidThroughDate": "03-06-2026",
            "mostRecentDebtServiceCoverageNetOperatingIncomePercentage": "1.95",
            "mostRecentPhysicalOccupancyPercentage": "0.85",
            "modified_asset_marker": "false",
            "special_servicer_or_workout_marker": "false",
            "missing_cell_blocker": "",
        },
        {
            "date": "2026-04-11",
            "trust_name": "Example CMBS Trust",
            "cik": "2027304",
            "accession_number": "0001888524-26-008538",
            "filing_date": "2026-05-01",
            "period_of_report": "2026-04-17",
            "assetNumber": "1",
            "property_index": "1",
            "reportPeriodEndActualBalanceAmount": "74800000.00000000",
            "reportPeriodEndScheduledLoanBalanceAmount": "74900000.00000000",
            "paymentStatusLoanCode": "1",
            "paidThroughDate": "04-06-2026",
            "mostRecentDebtServiceCoverageNetOperatingIncomePercentage": "1.91",
            "mostRecentPhysicalOccupancyPercentage": "0.83",
            "modified_asset_marker": "true",
            "special_servicer_or_workout_marker": "false",
            "missing_cell_blocker": "",
        },
        {
            "date": "2026-04-11",
            "trust_name": "Example CMBS Trust",
            "cik": "2027304",
            "accession_number": "0001888524-26-008538",
            "filing_date": "2026-05-01",
            "period_of_report": "2026-04-17",
            "assetNumber": "2",
            "property_index": "1",
            "reportPeriodEndActualBalanceAmount": "1000000.00000000",
        },
    ]

    rows = _sec_abs_ee_cmbs_time_dimension_records(records)

    assert len(rows) == 2
    assert {row["asset_time_dimension_key"] for row in rows} == {"2027304::1::1"}
    assert {row["asset_report_period_count"] for row in rows} == {"2"}
    assert {row["asset_first_report_period"] for row in rows} == {"2026-03-11"}
    assert {row["asset_latest_report_period"] for row in rows} == {"2026-04-11"}
    assert {row["public_asset_time_dimension_context_available"] for row in rows} == {
        "true"
    }
    assert {row["actual_balance_variation_context_available"] for row in rows} == {
        "true"
    }
    assert {row["scheduled_balance_variation_context_available"] for row in rows} == {
        "true"
    }
    assert {row["payment_status_variation_context_available"] for row in rows} == {
        "true"
    }
    assert {row["paid_through_variation_context_available"] for row in rows} == {"true"}
    assert {row["dscr_variation_context_available"] for row in rows} == {"true"}
    assert {row["occupancy_variation_context_available"] for row in rows} == {"true"}
    assert {row["modified_asset_marker_seen"] for row in rows} == {"true"}
    assert {row["public_representativeness_design_available"] for row in rows} == {
        "false"
    }
    assert {row["cre_refinancing_outcome_available"] for row in rows} == {"false"}
    assert {row["cre_real_activity_mapping_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_sec_abs_ee_recent_index_records_keep_filing_frame_fail_closed():
    master_index = """
Description: Master Index of EDGAR Dissemination Feed
CIK|Company Name|Form Type|Date Filed|Filename
--------------------------------------------------------------------------------
1013611|JP MORGAN CHASE COMMERCIAL MORTGAGE SECURITIES CORP|ABS-EE|2026-05-18|edgar/data/1013611/0001539497-26-001493.txt
1083199|WORLD OMNI AUTO RECEIVABLES LLC|ABS-EE|2026-04-29|edgar/data/1083199/0001104659-26-050735.txt
1000045|OLD MARKET CAPITAL Corp|10-Q|2026-04-29|edgar/data/1000045/0001437749-26-000015.txt
    """

    rows = _sec_abs_ee_recent_index_records(
        master_index_text=master_index,
        year=2026,
        quarter=2,
        index_url="https://www.sec.gov/Archives/edgar/full-index/2026/QTR2/master.idx",
    )

    assert len(rows) == 2
    assert rows[0]["accession_number"] == "0001539497-26-001493"
    assert rows[0]["candidate_cmbs_name_match"] == "true"
    assert rows[1]["candidate_cmbs_name_match"] == "false"
    assert {row["public_abs_ee_filing_index_frame_available"] for row in rows} == {
        "true"
    }
    assert {
        row["public_representativeness_frame_for_abs_ee_index_available"]
        for row in rows
    } == {"true"}
    assert {row["asset_level_xml_verified"] for row in rows} == {"false"}
    assert {row["cre_market_representativeness_design_available"] for row in rows} == {
        "false"
    }
    assert {row["cre_refinancing_outcome_available"] for row in rows} == {"false"}
    assert {row["cre_real_activity_mapping_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_sec_abs_ee_xml_verification_candidate_rows_are_bounded_by_quarter():
    rows = [
        {
            "index_year": "2026",
            "index_quarter": "QTR1",
            "filing_date": f"2026-01-{day:02d}",
            "cik": str(2000 + day),
            "accession_number": f"0000000000-26-0000{day:02d}",
            "candidate_cmbs_name_match": "true",
        }
        for day in range(1, 5)
    ]
    rows.extend(
        {
            "index_year": "2026",
            "index_quarter": "QTR2",
            "filing_date": f"2026-04-{day:02d}",
            "cik": str(3000 + day),
            "accession_number": f"0000000000-26-0001{day:02d}",
            "candidate_cmbs_name_match": "true",
        }
        for day in range(1, 5)
    )
    rows.append(
        {
            "index_year": "2026",
            "index_quarter": "QTR2",
            "filing_date": "2026-04-01",
            "cik": "9999",
            "accession_number": "0000000000-26-999999",
            "candidate_cmbs_name_match": "false",
        }
    )

    selected = _sec_abs_ee_xml_verification_candidate_rows(rows, per_quarter=2)

    assert len(selected) == 4
    assert {row["candidate_cmbs_name_match"] for row in selected} == {"true"}
    assert [row["filing_date"] for row in selected] == [
        "2026-01-01",
        "2026-01-02",
        "2026-04-01",
        "2026-04-02",
    ]


def test_sec_abs_ee_xml_payload_verification_fields_identify_cmbs_assetdata():
    source_xml = """
    <assetData xmlns="http://www.sec.gov/edgar/document/absee/cmbs/assetdata">
      <assets><assetNumber>1</assetNumber></assets>
      <assets><assetNumber>2</assetNumber></assets>
    </assetData>
    """

    fields = _sec_abs_ee_xml_payload_verification_fields(source_xml)

    assert fields["xml_root_local_name"] == "assetData"
    assert "cmbs" in fields["xml_namespace"]
    assert fields["asset_node_count"] == "2"
    assert fields["asset_data_xml_verified"] == "true"
    assert fields["cmbs_asset_xml_verified"] == "true"


def test_sec_abs_ee_representativeness_design_records_stay_fail_closed():
    filing_index_records = [
        {
            "index_year": "2026",
            "index_quarter": "QTR1",
            "filing_date": "2026-01-02",
            "cik": "1001",
            "candidate_cmbs_name_match": "true",
        },
        {
            "index_year": "2026",
            "index_quarter": "QTR1",
            "filing_date": "2026-01-03",
            "cik": "1002",
            "candidate_cmbs_name_match": "false",
        },
        {
            "index_year": "2026",
            "index_quarter": "QTR1",
            "filing_date": "2026-01-04",
            "cik": "1003",
            "candidate_cmbs_name_match": "true",
        },
    ]
    xml_records = [
        {
            "index_year": "2026",
            "index_quarter": "QTR1",
            "cmbs_asset_xml_verified": "true",
            "asset_data_xml_verified": "true",
        }
    ]

    rows = _sec_abs_ee_cmbs_representativeness_design_records(
        filing_index_records=filing_index_records,
        xml_verification_records=xml_records,
    )

    assert len(rows) == 1
    assert rows[0]["abs_ee_filing_row_count"] == "3"
    assert rows[0]["candidate_cmbs_name_match_row_count"] == "2"
    assert rows[0]["xml_verification_sample_row_count"] == "1"
    assert rows[0]["cmbs_asset_xml_verified_row_count"] == "1"
    assert rows[0]["public_abs_ee_filing_frame_available"] == "true"
    assert rows[0]["asset_class_xml_verification_sample_available"] == "true"
    assert rows[0]["public_cre_market_population_denominator_available"] == "false"
    assert rows[0]["representative_sampling_weights_available"] == "false"
    assert rows[0]["cre_market_representativeness_design_available"] == "false"
    assert rows[0]["cre_refinancing_outcome_available"] == "false"
    assert rows[0]["cre_real_activity_mapping_available"] == "false"
    assert rows[0]["split_denominator_promotion_allowed"] == "false"
    assert rows[0]["main_ratio_admission_allowed"] == "false"


def test_fed_z1_cmbs_abs_population_denominator_records_stay_fail_closed():
    z1_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(series_id="BOGZ1FL673065505Q"),
        records=[
            {"date": "2025-07-01", "value": "429400"},
            {"date": "2025-10-01", "value": "446200"},
        ],
    )
    representativeness_snapshot = SimpleNamespace(
        records=[
            {
                "date": "2026-03-31",
                "index_year": "2026",
                "index_quarter": "QTR1",
                "abs_ee_filing_row_count": "2336",
                "candidate_cmbs_name_match_row_count": "771",
                "xml_verification_sample_row_count": "8",
                "cmbs_asset_xml_verified_row_count": "8",
            }
        ]
    )

    rows = _fed_z1_cmbs_abs_population_denominator_records(
        z1_snapshot=z1_snapshot,
        representativeness_snapshot=representativeness_snapshot,
    )

    assert len(rows) == 1
    assert rows[0]["z1_population_denominator_observation_date"] == "2025-10-01"
    assert rows[0]["z1_population_denominator_millions_of_dollars"] == "446200"
    assert rows[0]["z1_population_denominator_billions_of_dollars"] == "446.2"
    assert rows[0]["public_cmbs_abs_segment_population_denominator_available"] == "true"
    assert rows[0]["public_cre_market_population_denominator_available"] == "false"
    assert rows[0]["population_denominator_is_full_cre_market"] == "false"
    assert rows[0]["filing_count_to_balance_weight_available"] == "false"
    assert rows[0]["representative_sampling_weights_available"] == "false"
    assert rows[0]["cre_market_representativeness_design_available"] == "false"
    assert rows[0]["cre_refinancing_outcome_available"] == "false"
    assert rows[0]["cre_real_activity_mapping_available"] == "false"
    assert rows[0]["split_denominator_promotion_allowed"] == "false"
    assert rows[0]["main_ratio_admission_allowed"] == "false"


def test_fed_z1_total_commercial_mortgage_population_records_stay_fail_closed():
    total_z1_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(series_id="ASCMA"),
        records=[
            {"date": "2025-07-01", "value": "3900000"},
            {"date": "2025-10-01", "value": "4000000"},
        ],
    )
    cmbs_abs_z1_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(series_id="BOGZ1FL673065505Q"),
        records=[
            {"date": "2025-07-01", "value": "400000"},
            {"date": "2025-10-01", "value": "500000"},
        ],
    )
    representativeness_snapshot = SimpleNamespace(
        records=[
            {
                "date": "2026-03-31",
                "index_year": "2026",
                "index_quarter": "QTR1",
                "abs_ee_filing_row_count": "2336",
                "candidate_cmbs_name_match_row_count": "771",
                "xml_verification_sample_row_count": "8",
                "cmbs_asset_xml_verified_row_count": "8",
            }
        ]
    )

    rows = _fed_z1_total_commercial_mortgage_population_records(
        total_z1_snapshot=total_z1_snapshot,
        cmbs_abs_z1_snapshot=cmbs_abs_z1_snapshot,
        representativeness_snapshot=representativeness_snapshot,
    )

    assert len(rows) == 1
    assert rows[0]["z1_total_population_denominator_series_id"] == "ASCMA"
    assert rows[0]["z1_total_population_denominator_observation_date"] == ("2025-10-01")
    assert rows[0]["z1_total_population_denominator_millions_of_dollars"] == ("4000000")
    assert rows[0]["z1_total_population_denominator_billions_of_dollars"] == "4000"
    assert rows[0]["cmbs_abs_segment_share_of_total_commercial_mortgages"] == "0.125"
    assert (
        rows[0]["public_total_commercial_mortgage_population_denominator_available"]
        == "true"
    )
    assert rows[0]["public_cre_market_population_denominator_available"] == "true"
    assert rows[0]["population_denominator_is_full_cre_market"] == "true"
    assert rows[0]["filing_count_to_balance_weight_available"] == "false"
    assert rows[0]["representative_sampling_weights_available"] == "false"
    assert rows[0]["cre_market_representativeness_design_available"] == "false"
    assert rows[0]["cre_refinancing_outcome_available"] == "false"
    assert rows[0]["cre_real_activity_mapping_available"] == "false"
    assert rows[0]["split_denominator_promotion_allowed"] == "false"
    assert rows[0]["main_ratio_admission_allowed"] == "false"


def test_sec_abs_ee_cmbs_reviewed_balance_coverage_records_stay_fail_closed():
    asset_time_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(
            series_id="sec_abs_ee_cmbs_asset_time_dimension_panel"
        ),
        records=[
            {
                "date": "2026-01-06",
                "filing_date": "2026-01-21",
                "cik": "1001",
                "accession_number": "0001001-26-000001",
                "assetNumber": "1",
                "public_trust_asset_number_key": "1001::1",
                "reportPeriodEndActualBalanceAmount": "1000000.00",
            },
            {
                "date": "2026-02-06",
                "filing_date": "2026-02-21",
                "cik": "1001",
                "accession_number": "0001001-26-000002",
                "assetNumber": "1",
                "public_trust_asset_number_key": "1001::1",
                "reportPeriodEndActualBalanceAmount": "900000.00",
            },
            {
                "date": "2026-02-06",
                "filing_date": "2026-02-21",
                "cik": "1001",
                "accession_number": "0001001-26-000002",
                "assetNumber": "2",
                "public_trust_asset_number_key": "1001::2",
                "reportPeriodEndActualBalanceAmount": "2100000.00",
            },
            {
                "date": "2026-04-06",
                "filing_date": "2026-04-20",
                "cik": "1002",
                "accession_number": "0001002-26-000001",
                "assetNumber": "3",
                "public_trust_asset_number_key": "1002::3",
                "reportPeriodEndActualBalanceAmount": "3000000.00",
            },
        ],
    )
    representativeness_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(
            series_id="sec_abs_ee_cmbs_representativeness_design_review_context"
        ),
        records=[
            {"date": "2026-03-31", "index_year": "2026", "index_quarter": "QTR1"},
            {"date": "2026-05-18", "index_year": "2026", "index_quarter": "QTR2"},
        ],
    )
    cmbs_abs_z1_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(series_id="BOGZ1FL673065505Q"),
        records=[{"date": "2025-10-01", "value": "500000"}],
    )
    total_z1_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(series_id="ASCMA"),
        records=[{"date": "2025-10-01", "value": "4000000"}],
    )

    rows = _sec_abs_ee_cmbs_reviewed_balance_coverage_records(
        asset_time_snapshot=asset_time_snapshot,
        representativeness_snapshot=representativeness_snapshot,
        cmbs_abs_z1_snapshot=cmbs_abs_z1_snapshot,
        total_z1_snapshot=total_z1_snapshot,
    )

    assert len(rows) == 2
    assert rows[0]["asset_time_dimension_row_count"] == "3"
    assert rows[0]["balance_observation_row_count"] == "3"
    assert rows[0]["unique_reviewed_public_trust_asset_key_count"] == "2"
    assert rows[0]["reviewed_latest_actual_balance_millions_of_dollars"] == "3"
    assert rows[0]["reviewed_balance_share_of_cmbs_abs_segment_denominator"] == (
        "0.000006"
    )
    assert rows[0]["filing_count_to_balance_weight_context_available"] == "true"
    assert rows[0]["filing_count_to_balance_weight_available"] == "false"
    assert rows[0]["representative_sampling_weights_available"] == "false"
    assert rows[0]["cre_refinancing_outcome_available"] == "false"
    assert rows[0]["cre_real_activity_mapping_available"] == "false"
    assert rows[0]["split_denominator_promotion_allowed"] == "false"
    assert rows[0]["main_ratio_admission_allowed"] == "false"
    assert rows[1]["reviewed_latest_actual_balance_millions_of_dollars"] == "3"


def test_sec_abs_ee_cmbs_maturity_status_outcome_records_stay_fail_closed():
    asset_time_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(
            series_id="sec_abs_ee_cmbs_asset_time_dimension_panel"
        ),
        records=[
            {
                "date": "2026-03-06",
                "filing_date": "2026-03-21",
                "cik": "1001",
                "assetNumber": "1",
                "property_index": "0",
                "public_trust_asset_number_key": "1001::1",
                "reportPeriodEndActualBalanceAmount": "1000000.00",
                "maturityDate": "03-01-2026",
                "paidThroughDate": "02-01-2026",
                "paymentStatusLoanCode": "5",
                "modifiedIndicator": "true",
                "special_servicer_or_workout_marker_seen": "false",
            },
            {
                "date": "2026-03-06",
                "filing_date": "2026-03-21",
                "cik": "1001",
                "assetNumber": "2",
                "property_index": "0",
                "public_trust_asset_number_key": "1001::2",
                "reportPeriodEndActualBalanceAmount": "2000000.00",
                "maturityDate": "06-01-2026",
                "paidThroughDate": "02-01-2026",
                "paymentStatusLoanCode": "0",
                "modifiedIndicator": "false",
                "special_servicer_or_workout_marker_seen": "true",
            },
            {
                "date": "2026-04-06",
                "filing_date": "2026-04-20",
                "cik": "1002",
                "assetNumber": "3",
                "property_index": "0",
                "public_trust_asset_number_key": "1002::3",
                "reportPeriodEndActualBalanceAmount": "3000000.00",
                "maturityDate": "05-01-2027",
                "paidThroughDate": "03-01-2026",
                "paymentStatusLoanCode": "A",
                "modifiedIndicator": "false",
                "special_servicer_or_workout_marker_seen": "false",
            },
        ],
    )
    representativeness_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(
            series_id="sec_abs_ee_cmbs_representativeness_design_review_context"
        ),
        records=[
            {"date": "2026-03-31", "index_year": "2026", "index_quarter": "QTR1"},
            {"date": "2026-05-18", "index_year": "2026", "index_quarter": "QTR2"},
        ],
    )

    rows = _sec_abs_ee_cmbs_maturity_status_outcome_records(
        asset_time_snapshot=asset_time_snapshot,
        representativeness_snapshot=representativeness_snapshot,
    )

    assert len(rows) == 10
    q1 = {
        row["maturity_window_bucket"]: row
        for row in rows
        if row["index_quarter"] == "QTR1"
    }
    assert q1["past_maturity"]["bucket_reviewed_loan_count"] == "1"
    assert q1["past_maturity"]["bucket_actual_balance_millions_of_dollars"] == "1"
    assert q1["past_maturity"]["payment_status_nonzero_code_count"] == "1"
    assert q1["past_maturity"]["modified_indicator_true_count"] == "1"
    assert q1["matures_0_90_days"]["bucket_reviewed_loan_count"] == "1"
    assert q1["matures_0_90_days"]["payment_status_code_0_count"] == "1"
    assert (
        q1["matures_0_90_days"]["special_servicer_or_workout_marker_seen_count"] == "1"
    )
    q2 = {
        row["maturity_window_bucket"]: row
        for row in rows
        if row["index_quarter"] == "QTR2"
    }
    assert q2["matures_366_730_days"]["bucket_reviewed_loan_count"] == "1"
    assert q2["matures_366_730_days"]["payment_status_nonzero_code_count"] == "1"
    assert {row["public_maturity_window_status_context_available"] for row in rows} == {
        "true"
    }
    assert {row["explicit_refinancing_outcome_field_available"] for row in rows} == {
        "false"
    }
    assert {row["cre_refinancing_outcome_available"] for row in rows} == {"false"}
    assert {row["representative_sampling_weights_available"] for row in rows} == {
        "false"
    }
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fred_nonres_construction_real_activity_bridge_records_stay_fail_closed():
    construction_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(series_id="TLNRESCONS"),
        records=[
            {"date": "2026-02-01", "value": "1234000"},
            {"date": "2026-03-01", "value": "1250000"},
        ],
    )
    total_z1_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(series_id="ASCMA"),
        records=[
            {"date": "2025-07-01", "value": "3900000"},
            {"date": "2025-10-01", "value": "4000000"},
        ],
    )
    representativeness_snapshot = SimpleNamespace(
        records=[
            {
                "date": "2026-03-31",
                "index_year": "2026",
                "index_quarter": "QTR1",
            }
        ]
    )

    rows = _fred_nonres_construction_real_activity_bridge_records(
        construction_snapshot=construction_snapshot,
        total_z1_snapshot=total_z1_snapshot,
        representativeness_snapshot=representativeness_snapshot,
    )

    assert len(rows) == 1
    assert rows[0]["real_activity_series_id"] == "TLNRESCONS"
    assert rows[0]["real_activity_observation_date"] == "2026-03-01"
    assert rows[0]["real_activity_millions_of_dollars_saar"] == "1250000"
    assert rows[0]["commercial_mortgage_stock_series_id"] == "ASCMA"
    assert rows[0]["commercial_mortgage_stock_observation_date"] == "2025-10-01"
    assert (
        rows[0]["nonres_construction_saar_to_commercial_mortgage_stock_ratio"]
        == "0.3125"
    )
    assert rows[0]["flow_stock_ratio_is_not_elasticity"] == "true"
    assert (
        rows[0]["public_nonresidential_construction_real_activity_series_available"]
        == "true"
    )
    assert rows[0]["public_real_activity_bridge_review_available"] == "true"
    assert rows[0]["cre_market_representativeness_design_available"] == "false"
    assert rows[0]["cre_refinancing_outcome_available"] == "false"
    assert rows[0]["cre_real_activity_mapping_available"] == "false"
    assert rows[0]["split_denominator_promotion_allowed"] == "false"
    assert rows[0]["main_ratio_admission_allowed"] == "false"


def test_fred_cre_property_type_construction_bridge_records_stay_fail_closed():
    construction_snapshots = {
        "PNRESCONS": SimpleNamespace(
            metadata=SimpleNamespace(series_id="PNRESCONS"),
            records=[{"date": "2026-03-01", "value": "750000"}],
        ),
        "PBNRESCONS": SimpleNamespace(
            metadata=SimpleNamespace(series_id="PBNRESCONS"),
            records=[{"date": "2026-03-01", "value": "500000"}],
        ),
        "PLODGCONS": SimpleNamespace(
            metadata=SimpleNamespace(series_id="PLODGCONS"),
            records=[{"date": "2026-03-01", "value": "25000"}],
        ),
        "PROFCONS": SimpleNamespace(
            metadata=SimpleNamespace(series_id="PROFCONS"),
            records=[{"date": "2026-03-01", "value": "100000"}],
        ),
        "PRCOMCONS": SimpleNamespace(
            metadata=SimpleNamespace(series_id="PRCOMCONS"),
            records=[{"date": "2026-03-01", "value": "120000"}],
        ),
        "PRHLTHCONS": SimpleNamespace(
            metadata=SimpleNamespace(series_id="PRHLTHCONS"),
            records=[{"date": "2026-03-01", "value": "50000"}],
        ),
        "PREDUCONS": SimpleNamespace(
            metadata=SimpleNamespace(series_id="PREDUCONS"),
            records=[{"date": "2026-03-01", "value": "20000"}],
        ),
        "PRAMUSCONS": SimpleNamespace(
            metadata=SimpleNamespace(series_id="PRAMUSCONS"),
            records=[{"date": "2026-03-01", "value": "15000"}],
        ),
        "PRMFGCONS": SimpleNamespace(
            metadata=SimpleNamespace(series_id="PRMFGCONS"),
            records=[{"date": "2026-03-01", "value": "200000"}],
        ),
    }
    total_nonres_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(series_id="TLNRESCONS"),
        records=[{"date": "2026-03-01", "value": "1250000"}],
    )
    total_z1_snapshot = SimpleNamespace(
        metadata=SimpleNamespace(series_id="ASCMA"),
        records=[{"date": "2025-10-01", "value": "4000000"}],
    )
    representativeness_snapshot = SimpleNamespace(
        records=[
            {
                "date": "2026-03-31",
                "index_year": "2026",
                "index_quarter": "QTR1",
            }
        ]
    )

    rows = _fred_cre_property_type_construction_bridge_records(
        construction_snapshots=construction_snapshots,
        total_nonres_snapshot=total_nonres_snapshot,
        total_private_nonres_snapshot=construction_snapshots["PNRESCONS"],
        total_z1_snapshot=total_z1_snapshot,
        representativeness_snapshot=representativeness_snapshot,
    )

    assert len(rows) == 9
    office_row = next(
        row for row in rows if row["construction_series_id"] == "PROFCONS"
    )
    assert office_row["construction_category"] == "private_office"
    assert office_row["construction_millions_of_dollars_saar"] == "100000"
    assert office_row["category_share_of_total_nonres_construction"] == "0.08"
    assert office_row["category_share_of_private_nonres_construction"] == ("0.133333")
    assert office_row["category_saar_to_commercial_mortgage_stock_ratio"] == "0.025"
    assert office_row["public_property_type_construction_series_available"] == "true"
    assert office_row["public_property_type_real_activity_context_available"] == (
        "true"
    )
    assert (
        office_row["property_type_mapping_is_construction_spending_not_debt_exposure"]
        == "true"
    )
    assert office_row["filing_count_to_balance_weight_available"] == "false"
    assert office_row["representative_sampling_weights_available"] == "false"
    assert office_row["cre_refinancing_outcome_available"] == "false"
    assert (
        office_row["cre_debt_repricing_to_real_activity_mapping_available"] == "false"
    )
    assert office_row["cre_real_activity_mapping_available"] == "false"
    assert office_row["split_denominator_promotion_allowed"] == "false"
    assert office_row["main_ratio_admission_allowed"] == "false"


def test_fed_private_credit_accessible_tables_keep_gate_fail_closed():
    html = """
    <table title="Figure 7. Maturity Wall in Private Credit">
      <thead><tr><th class="colhead">Year</th><th class="colhead">Percentage (%)</th></tr></thead>
      <tbody><tr><th>2028</th><td>21.4</td></tr></tbody>
    </table>
    <table title="Figure 8. Average Maturity in Private Credit">
      <thead><tr><th class="colhead">Year</th><th class="colhead">Maturity Date</th></tr></thead>
      <tbody><tr><th>2023</th><td>4.40</td></tr></tbody>
    </table>
    <table title="Figure 9. Deal Types">
      <thead><tr><td class="colhead">&nbsp;</td><th class="colhead">Loan Amount by Deal Type</th></tr></thead>
      <tbody><tr><th>Debt - General</th><td>47.24%</td></tr></tbody>
    </table>
    """

    rows = _fed_private_credit_accessible_table_records(html, require_all_tables=False)

    assert len(rows) == 3
    assert rows[0]["date"] == "2028-12-31"
    assert rows[0]["metric"] == "private_credit_maturity_wall_share"
    assert rows[0]["metric_value"] == "21.4"
    assert rows[2]["metric_label"] == "Debt - General"
    assert {row["private_credit_maturity_context_available"] for row in rows} == {
        "true",
        "false",
    }
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_fed_bank_lending_private_credit_parser_keeps_gate_fail_closed():
    html = """
    <html><body>
    <h1>Bank Lending to Private Credit</h1>
    <p>FR Y-14Q, Bank loans to NBFIs, Default probabilities, and
    Changes in Capital and Liquidity ratios.</p>
    <table title="Table 1: Bank loans to NBFIs in FR Y-14Q, as of 2024-Q4">
      <thead><tr>
        <th class="colhead">Loan Commitment ($ Billion)</th>
        <th class="colhead">Utilization Rate (%)</th>
        <th class="colhead">Average Interest Rate (%)</th>
        <th class="colhead">Time to Maturity (Years)</th>
        <th class="colhead">Average Rating</th>
        <th class="colhead">Delinquency Rate (%)</th>
      </tr></thead>
      <tbody>
        <tr><th>BDCs</th><td>56</td><td>56.8</td><td>6.4</td><td>4.1</td><td>BBB</td><td>0.5</td></tr>
        <tr><th>Private Debt Funds</th><td>40</td><td>55.0</td><td>6.6</td><td>2.6</td><td>BBB</td><td>0.7</td></tr>
        <tr><th>Other NBFIs</th><td>2193</td><td>48.7</td><td>6.2</td><td>3.0</td><td>BBB</td><td>0.7</td></tr>
      </tbody>
    </table>
    <table title="Table 2: BHC loans - Distribution of Default probabilities (%) by Rating, as of 2024-Q4">
      <thead><tr>
        <th class="colhead">Other NBFIs</th><th class="colhead">Private Debt Funds</th><th class="colhead">BDCs</th>
        <th class="colhead">Mean</th><th class="colhead">Median</th><th class="colhead">% Obs</th>
        <th class="colhead">Mean</th><th class="colhead">Median</th><th class="colhead">% Obs</th>
        <th class="colhead">Mean</th><th class="colhead">Median</th><th class="colhead">% Obs</th>
      </tr></thead>
      <tbody>
        <tr><th>All Firms</th><td>1.65</td><td>0.37</td><td>100</td><td>2.07</td><td>0.22</td><td>100</td><td>0.71</td><td>0.30</td><td>100</td></tr>
        <tr><th>Inv. Grade excl. BBB</th><td>0.38</td><td>0.06</td><td>16</td><td>0.06</td><td>0.05</td><td>29</td><td>0.06</td><td>0.07</td><td>10</td></tr>
        <tr><th>BBB</th><td>0.37</td><td>0.23</td><td>37</td><td>0.60</td><td>0.20</td><td>40</td><td>0.44</td><td>0.24</td><td>52</td></tr>
        <tr><th>Non-Inv. Grade</th><td>3.07</td><td>1.03</td><td>47</td><td>5.76</td><td>1.03</td><td>32</td><td>1.26</td><td>0.85</td><td>38</td></tr>
      </tbody>
    </table>
    <table title="Table 3: Private Credit Vehicles: Changes in Capital and Liquidity ratios">
      <thead><tr>
        <th class="colhead">Regulatory Ratio</th>
        <th class="colhead">Current (%)</th>
        <th class="colhead">Drawdown rate assumption</th>
        <th class="colhead">Implied Change in Numerator ($ Bil.)</th>
        <th class="colhead">Implied Change in denominator ($ Bil.)</th>
        <th class="colhead">New ratio (%)</th>
      </tr></thead>
      <tbody>
        <tr><th>CET1 ratio</th><td>13.02</td><td>0.5</td><td>0</td><td>18</td><td>13.0</td></tr>
        <tr><th>LCR</th><td>122</td><td>0.4</td><td>-36</td><td>-14.4</td><td>121</td></tr>
      </tbody>
    </table>
    </body></html>
    """

    rows = _fed_bank_lending_private_credit_records(html)

    assert len(rows) == 64
    assert any(
        row["source_row_label"] == "BDCs"
        and row["metric"] == "loan_commitment_bil"
        and row["metric_value"] == "56"
        for row in rows
    )
    assert any(
        row["source_row_label"] == "Private Debt Funds"
        and row["metric"] == "average_interest_rate_pct"
        and row["metric_value"] == "6.6"
        for row in rows
    )
    assert any(
        row["source_column_label"] == "Private Debt Funds Mean"
        and row["source_row_label"] == "Non-Inv. Grade"
        and row["metric_value"] == "5.76"
        for row in rows
    )
    assert any(
        row["source_row_label"] == "LCR"
        and row["metric"] == "new_ratio_pct"
        and row["metric_value"] == "121"
        for row in rows
    )
    assert {row["public_reusable_loan_level_artifact_available"] for row in rows} == {
        "false"
    }
    assert {row["borrower_pass_through_context_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_sec_private_fund_aggregate_assets_parser_keeps_gate_fail_closed():
    source_json = json.dumps(
        {
            "Section.2_Aggregate_Fund_Assets_Table.2.1": {
                "metadata": {
                    "title": "Aggregate Private Fund Gross Asset Value (USD)",
                    "caption": "As reported on Form PF, Question 8.",
                    "units": "usd",
                },
                "data": [
                    {
                        "name": "Private Equity Fund",
                        "data": [{"name": "2025Q3", "x": 1, "y": 10_000_000}],
                    },
                    {
                        "name": "Liquidity Fund",
                        "data": [{"name": "2025Q3", "x": 1, "y": 5_000_000}],
                    },
                ],
            },
            "Section.2_Aggregate_Fund_Assets_Table.2.3": {
                "metadata": {
                    "title": "Aggregate Private Fund Net Asset Value (USD)",
                    "caption": "As reported on Form PF, Question 9.",
                    "units": "usd",
                },
                "data": [
                    {
                        "name": "Private Equity Fund",
                        "data": [{"name": "2025Q3", "x": 1, "y": 7_000_000}],
                    }
                ],
            },
        }
    )

    rows = _sec_private_fund_aggregate_asset_records(source_json)

    assert len(rows) == 3
    assert rows[0]["date"] == "2025-09-30"
    assert rows[0]["metric"] == "gross_asset_value"
    assert rows[0]["form_pf_question"] == "8"
    assert rows[0]["metric_value_usd"] == "10000000"
    assert rows[1]["private_fund_liquidity_fund_context_available"] == "true"
    assert {row["form_pf_aggregate_statistics_available"] for row in rows} == {"true"}
    assert {row["public_reusable_fund_level_artifact_available"] for row in rows} == {
        "false"
    }
    assert {row["borrower_pass_through_context_available"] for row in rows} == {"false"}
    assert {row["nonbank_to_real_activity_context_available"] for row in rows} == {
        "false"
    }
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_sec_bdc_public_filing_availability_keeps_gate_fail_closed():
    submissions_json = json.dumps(
        {
            "name": "ARES CAPITAL CORP",
            "tickers": ["ARCC"],
            "filings": {
                "recent": {
                    "form": ["8-K", "10-Q"],
                    "accessionNumber": [
                        "0000000000-26-000001",
                        "0001628280-26-027688",
                    ],
                    "primaryDocument": ["current.htm", "arcc-20260331.htm"],
                    "filingDate": ["2026-05-01", "2026-04-28"],
                    "reportDate": ["2026-05-01", "2026-03-31"],
                }
            },
        }
    )
    filing_html = """
    <html><body>
      <table>
        <tr><th>Portfolio Company</th><th>Interest Rate</th>
        <th>Maturity</th><th>Fair Value</th></tr>
        <tr><td>Example Borrower</td><td>SOFR + 5.00%</td>
        <td>2029</td><td>100</td></tr>
      </table>
      <p>First Lien Senior Secured Debt Investments at Fair Value</p>
    </body></html>
    """

    row = _sec_bdc_public_filing_availability_record(
        cik="0001287750",
        expected_ticker="ARCC",
        submissions_json=submissions_json,
        filing_html=filing_html,
    )

    assert row["form_type"] == "10-Q"
    assert row["report_date"] == "2026-03-31"
    assert row["portfolio_disclosure_marker_available"] == "true"
    assert row["rate_term_marker_available"] == "true"
    assert row["maturity_marker_available"] == "true"
    assert row["fair_value_marker_available"] == "true"
    assert row["lien_or_seniority_marker_available"] == "true"
    assert row["public_reusable_company_filing_artifact_available"] == "true"
    assert row["public_reusable_normalized_loan_level_panel_available"] == "false"
    assert row["borrower_pass_through_context_available"] == "false"
    assert row["nonbank_to_real_activity_context_available"] == "false"
    assert row["split_denominator_promotion_allowed"] == "false"
    assert row["main_ratio_admission_allowed"] == "false"


def test_sec_bdc_portfolio_investment_terms_panel_normalizes_fail_closed_rows():
    submissions_json = json.dumps(
        {
            "name": "ARES CAPITAL CORP",
            "tickers": ["ARCC"],
            "filings": {
                "recent": {
                    "form": ["10-Q"],
                    "accessionNumber": ["0001628280-26-027688"],
                    "primaryDocument": ["arcc-20260331.htm"],
                    "filingDate": ["2026-04-28"],
                    "reportDate": ["2026-03-31"],
                }
            },
        }
    )
    filing_html = """
    <html><body>
      <table>
        <tr><th>Company (1)</th><th>Business Description</th>
        <th>Investment</th><th>Coupon (3)</th><th>Reference (7)</th>
        <th>Spread (3)</th><th>Acquisition Date</th><th>Maturity Date</th>
        <th>Shares/Units</th><th>Principal</th><th>Amortized Cost</th>
        <th>Fair Value</th><th>% of Net Assets</th></tr>
        <tr><td>Example Borrower LLC</td><td>Software services</td>
        <td>First lien senior secured loan</td><td>8.66 %</td>
        <td>SOFR (Q)</td><td>5.00 %</td><td>04/2025</td>
        <td>10/2029</td><td>$</td><td>13.1</td><td>$</td>
        <td>13.0</td><td>$</td><td>13.1</td><td>(2)(9)</td></tr>
        <tr><td>First lien senior secured loan</td><td>8.66 %</td>
        <td>SOFR (Q)</td><td>5.00 %</td><td>08/2025</td>
        <td>10/2029</td><td>3.6</td><td>3.5</td><td>3.6</td>
        <td>(2)(9)</td></tr>
      </table>
    </body></html>
    """

    rows = _sec_bdc_portfolio_investment_terms_records(
        cik="0001287750",
        expected_ticker="ARCC",
        submissions_json=submissions_json,
        filing_html=filing_html,
    )

    assert len(rows) == 2
    assert rows[0]["borrower_or_issuer_name"] == "Example Borrower LLC"
    assert rows[0]["investment_type"] == "First lien senior secured loan"
    assert rows[0]["reference_rate"] == "SOFR (Q)"
    assert rows[0]["spread"] == "5.00 %"
    assert rows[0]["maturity_date"] == "10/2029"
    assert rows[0]["principal_or_par_value"] == "13.1"
    assert rows[0]["amortized_cost"] == "13.0"
    assert rows[0]["fair_value"] == "13.1"
    assert rows[0]["row_support_status"] == "full_terms_support"
    assert rows[1]["borrower_or_issuer_name"] == "Example Borrower LLC"
    assert rows[1]["source_schema"] == "arcc_company_business_coupon_spread"
    assert {
        row["public_reusable_normalized_investment_terms_panel_available"]
        for row in rows
    } == {"true"}
    assert {row["borrower_pass_through_context_available"] for row in rows} == {"false"}
    assert {row["nonbank_to_real_activity_context_available"] for row in rows} == {
        "false"
    }
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def test_sec_bdc_performance_status_panel_marks_nonaccrual_fail_closed():
    submissions_json = json.dumps(
        {
            "name": "BLUE OWL CAPITAL CORP",
            "tickers": ["OBDC"],
            "filings": {
                "recent": {
                    "form": ["10-Q"],
                    "accessionNumber": ["0001655888-26-000033"],
                    "primaryDocument": ["obdc-20260331.htm"],
                    "filingDate": ["2026-05-01"],
                    "reportDate": ["2026-03-31"],
                }
            },
        }
    )
    filing_html = """
    <html><body>
      <p>(28) Loan was on non-accrual status as of March 31, 2026.</p>
      <p>(29) Non-income producing.</p>
      <table>
        <tr><th>Company</th><th>Investment</th><th>Ref. Rate</th>
        <th>Cash</th><th>PIK</th><th>Maturity Date</th><th>Par</th>
        <th>Shares/Units</th><th>Amortized Cost</th><th>Fair Value</th></tr>
        <tr><td>Example Credit LLC(28)(29)</td>
        <td>First lien senior secured loan</td><td>S+</td>
        <td>6.75 %</td><td>1.00 % PIK</td><td>5/2028</td>
        <td>100.0</td><td>—</td><td>95.0</td><td>80.0</td></tr>
      </table>
    </body></html>
    """

    term_rows = _sec_bdc_portfolio_investment_terms_records(
        cik="0001655888",
        expected_ticker="OBDC",
        submissions_json=submissions_json,
        filing_html=filing_html,
    )
    context = _sec_bdc_footnote_context(filing_html)
    status_row = _sec_bdc_performance_status_record(term_rows[0], context)

    assert status_row["non_accrual_status_marker"] == "true"
    assert status_row["non_accrual_footnote_codes"] == "28"
    assert status_row["non_income_producing_marker"] == "true"
    assert status_row["pik_status_marker"] == "true"
    assert status_row["fair_value_to_principal_or_par_ratio"] == "0.8"
    assert status_row["fair_value_to_amortized_cost_ratio"] == "0.842105"
    assert status_row["fair_value_less_than_principal_or_par_marker"] == "true"
    assert (
        status_row["public_reusable_borrower_level_performance_marker_available"]
        == "true"
    )
    assert status_row["borrower_pass_through_context_available"] == "false"
    assert status_row["nonbank_to_real_activity_context_available"] == "false"
    assert status_row["split_denominator_promotion_allowed"] == "false"
    assert status_row["main_ratio_admission_allowed"] == "false"


def test_sec_bdc_terms_status_join_keeps_pass_through_fail_closed():
    term_record = {
        "date": "2026-05-01",
        "report_date": "2026-03-31",
        "cik": "0001655888",
        "registrant_name": "BLUE OWL CAPITAL CORP",
        "ticker": "OBDC",
        "form_type": "10-Q",
        "accession_number": "0001655888-26-000033",
        "filing_url": "https://www.sec.gov/Archives/example",
        "source_table_index": "1",
        "source_row_index": "2",
        "source_schema": "obdc_company_ref_cash_pik",
        "borrower_or_issuer_name": "Example Credit LLC(28)",
        "business_description": "",
        "industry": "",
        "investment_type": "First lien senior secured loan",
        "coupon_or_interest_rate": "",
        "reference_rate": "S+",
        "spread": "",
        "floor": "",
        "cash_component": "6.75 %",
        "pik_component": "1.00 % PIK",
        "acquisition_date": "",
        "maturity_date": "5/2028",
        "principal_or_par_value": "100.0",
        "shares_or_units": "",
        "amortized_cost": "95.0",
        "fair_value": "80.0",
        "amount_unit": "source_filing_table_units",
        "footnotes": "(28)",
        "raw_row_text": "Example Credit LLC First lien senior secured loan S+ 6.75 PIK",
        "source_schema_reviewed": "true",
        "public_reusable_company_filing_artifact_available": "true",
        "public_reusable_normalized_investment_terms_panel_available": "true",
        "rate_term_available": "true",
        "maturity_available": "true",
        "principal_or_par_available": "true",
        "fair_value_available": "true",
        "borrower_or_issuer_name_available": "true",
        "row_support_status": "full_terms_support",
        "missing_cell_blocker": "",
        "borrower_pass_through_context_available": "false",
        "nonbank_to_real_activity_context_available": "false",
    }
    footnote_context = {
        "non_accrual": {"28": "Loan was on non-accrual status as of March 31, 2026."},
        "non_income_producing": {},
        "maturity_extension_discussion": {},
    }

    row = _sec_bdc_terms_status_join_record(term_record, footnote_context)

    assert row["terms_row_support_status"] == "full_terms_support"
    assert row["performance_status_row_support_status"] == (
        "explicit_performance_status_marker_support"
    )
    assert row["row_support_status"] == "full_terms_and_performance_status_support"
    assert row["non_accrual_status_marker"] == "true"
    assert row["pik_status_marker"] == "true"
    assert row["fair_value_to_principal_or_par_ratio"] == "0.8"
    assert (
        row["public_reusable_borrower_investment_terms_status_panel_available"]
        == "true"
    )
    assert (
        row["borrower_level_repayment_or_performance_status_context_available"]
        == "true"
    )
    assert row["monetary_pass_through_design_available"] == "false"
    assert row["nonbank_to_real_activity_context_available"] == "false"
    assert row["split_denominator_promotion_allowed"] == "false"
    assert row["main_ratio_admission_allowed"] == "false"


def test_sec_bdc_terms_status_time_dimension_stays_fail_closed():
    submissions = {
        "name": "BLUE OWL CAPITAL CORP",
        "tickers": ["OBDC"],
        "filings": {
            "recent": {
                "form": ["8-K", "10-Q", "10-K", "10-Q", "10-Q", "10-Q"],
                "accessionNumber": [
                    "0000000000-26-000001",
                    "0001655888-26-000033",
                    "0001655888-26-000010",
                    "0001655888-25-000024",
                    "0001655888-25-000020",
                    "0001655888-25-000012",
                ],
                "primaryDocument": [
                    "current.htm",
                    "obdc-20260331.htm",
                    "obdc-20251231.htm",
                    "obdc-20250930.htm",
                    "obdc-20250630.htm",
                    "obdc-20250331.htm",
                ],
                "filingDate": [
                    "2026-05-01",
                    "2026-05-06",
                    "2026-02-18",
                    "2025-11-05",
                    "2025-08-06",
                    "2025-05-07",
                ],
                "reportDate": [
                    "2026-05-01",
                    "2026-03-31",
                    "2025-12-31",
                    "2025-09-30",
                    "2025-06-30",
                    "2025-03-31",
                ],
            }
        },
    }

    filings = _sec_bdc_recent_periodic_filings(submissions, max_filings=4)
    assert [filing["report_date"] for filing in filings] == [
        "2026-03-31",
        "2025-12-31",
        "2025-09-30",
        "2025-06-30",
    ]
    single_filing_submissions = json.loads(
        _sec_bdc_submissions_for_single_filing(submissions, filings[1])
    )
    assert single_filing_submissions["filings"]["recent"]["reportDate"] == [
        "2025-12-31"
    ]

    joined_row = _sec_bdc_terms_status_join_record(
        {
            "date": "2026-02-18",
            "report_date": "2025-12-31",
            "cik": "0001655888",
            "registrant_name": "BLUE OWL CAPITAL CORP",
            "ticker": "OBDC",
            "form_type": "10-K",
            "accession_number": "0001655888-26-000010",
            "filing_url": "https://www.sec.gov/Archives/example",
            "source_table_index": "1",
            "source_row_index": "2",
            "source_schema": "obdc_company_ref_cash_pik",
            "borrower_or_issuer_name": "Example Credit LLC(28)",
            "business_description": "",
            "industry": "",
            "investment_type": "First lien senior secured loan",
            "coupon_or_interest_rate": "",
            "reference_rate": "S+",
            "spread": "",
            "floor": "",
            "cash_component": "6.75 %",
            "pik_component": "1.00 % PIK",
            "acquisition_date": "",
            "maturity_date": "5/2028",
            "principal_or_par_value": "100.0",
            "shares_or_units": "",
            "amortized_cost": "95.0",
            "fair_value": "80.0",
            "amount_unit": "source_filing_table_units",
            "footnotes": "(28)",
            "raw_row_text": (
                "Example Credit LLC First lien senior secured loan S+ 6.75 PIK"
            ),
            "source_schema_reviewed": "true",
            "public_reusable_company_filing_artifact_available": "true",
            "public_reusable_normalized_investment_terms_panel_available": "true",
            "rate_term_available": "true",
            "maturity_available": "true",
            "principal_or_par_available": "true",
            "fair_value_available": "true",
            "borrower_or_issuer_name_available": "true",
            "row_support_status": "full_terms_support",
            "missing_cell_blocker": "",
            "borrower_pass_through_context_available": "false",
            "nonbank_to_real_activity_context_available": "false",
        },
        {
            "non_accrual": {
                "28": "Loan was on non-accrual status as of December 31, 2025."
            },
            "non_income_producing": {},
            "maturity_extension_discussion": {},
        },
    )
    row = _sec_bdc_time_dimension_record(joined_row)

    assert row["public_reusable_borrower_investment_time_dimension_available"] == (
        "true"
    )
    assert row[
        "public_reusable_periodic_filing_performance_time_context_available"
    ] == ("true")
    assert row["stable_public_borrower_identifier_available"] == "false"
    assert row["public_reusable_repayment_schedule_panel_available"] == "false"
    assert row["monetary_pass_through_design_available"] == "false"
    assert row["nonbank_to_real_activity_context_available"] == "false"
    assert row["split_denominator_promotion_allowed"] == "false"
    assert row["main_ratio_admission_allowed"] == "false"


def test_fed_indirect_credit_accessible_materials_keep_gate_fail_closed():
    figures_html = """
    <div id="fig1"><p><strong>Figure 1: The Rise of Bank Credit Line Lending to BDCs </strong></p></div>
    <div id="fig2"><p><strong>Figure 2: Interest Rate on Bank Loans: BDCs versus non-BDCs </strong></p></div>
    <div id="fig5"><p><strong>Figure 5: Aggregate Credit Volume and Borrowing Costs for Nonfinancial Businesses </strong></p></div>
    """
    index_html = """
    <h1>Indirect Credit Supply: How Bank Lending to Private Credit Shapes Monetary Policy Transmission</h1>
    <p><strong>Table 8:  BDCs' Reliance on Bank Financing and Monetary Pass Through</strong></p>
    <table>
      <tr><td>&nbsp;</td><th>Loan Amount (1)</th><th>Interest Rate (3)</th></tr>
      <tr><th><!-- MATH $BankLoanExpenseShare \\times Tightening$ -->$$BankLoanExpenseShare \\times Tightening$$</th><td>0.428*** <br> (0.121)</td><td>0.313*** <br> (0.0735)</td></tr>
      <tr><th>N</th><td>353,559</td><td>341,009</td></tr>
    </table>
    <p><strong>Table 9:  Real Effects of BDC Financing during Tightening</strong></p>
    <table>
      <tr><td>&nbsp;</td><th>Capex/ Total Assets (1)</th><th>Interest Coverage (5)</th></tr>
      <tr><th><!-- MATH $High BDC Reliance \\times Tightening$ -->$$High BDC Reliance \\times Tightening$$</th><td>0.019*** <br> (0.006)</td><td>-1.840** <br> (0.779)</td></tr>
      <tr><th>N</th><td>4,810</td><td>4,830</td></tr>
    </table>
    """

    rows = _fed_indirect_credit_accessible_material_records(
        index_html=index_html,
        accessible_figures_html=figures_html,
    )

    assert len(rows) == 11
    table_rows = [
        row for row in rows if row["source_record_type"] == "regression_table_cell"
    ]
    assert table_rows[0]["coefficient"] == "0.428"
    assert table_rows[0]["standard_error"] == "0.121"
    assert table_rows[0]["significance_stars"] == "***"
    assert any(
        row["nonbank_to_real_activity_context_available"] == "true"
        for row in table_rows
    )
    assert {row["public_reusable_loan_level_artifact_available"] for row in rows} == {
        "false"
    }
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}


def _fake_scf_record(
    *,
    yy1: str,
    implicate: int,
    income_category: str,
    income: str,
    liquid_assets: str,
    credit_card_balance: str,
    debt: str,
    weight: str = "10",
) -> dict[str, str]:
    return {
        "date": "2022-01-01",
        "survey_year": "2022",
        "yy1": yy1,
        "y1": str(int(yy1) * 10 + implicate),
        "wgt": weight,
        "income": income,
        "liq": liquid_assets,
        "hliq": "1" if float(liquid_assets) > 0 else "0",
        "ccbal": credit_card_balance,
        "hccbal": "1" if float(credit_card_balance) > 0 else "0",
        "debt": debt,
        "hdebt": "1" if float(debt) > 0 else "0",
        "debt2inc": "0.5",
        "conspay": "100",
        "revpay": "20",
        "pirrev": "0.02",
        "inccat": income_category,
        "ninccat": income_category,
        "agecl": "2",
    }


def test_fed_scf_uncertainty_records_join_replicates_fail_closed():
    source_records = []
    for implicate in range(1, 6):
        source_records.append(
            _fake_scf_record(
                yy1="1",
                implicate=implicate,
                income_category="1",
                income=str(100 + implicate),
                liquid_assets="50",
                credit_card_balance="25",
                debt="200",
            )
        )
        source_records.append(
            _fake_scf_record(
                yy1="2",
                implicate=implicate,
                income_category="2",
                income=str(200 + implicate),
                liquid_assets="0",
                credit_card_balance="0",
                debt="0",
            )
        )
    replicate_weights = {
        "1": array("d", [9.0 + (index % 2) for index in range(999)]),
        "2": array("d", [11.0 - (index % 2) for index in range(999)]),
    }

    rows = _fed_scf_uncertainty_records(source_records, replicate_weights)

    assert rows
    all_debt = next(
        row
        for row in rows
        if row["group_dimension"] == "all" and row["metric"] == "mean_debt"
    )
    assert all_debt["summary_method"] == (
        "scf_meanit_replicate_weight_uncertainty_review_context_only"
    )
    assert all_debt["replicate_estimate_count"] == "999"
    assert all_debt["implicate_estimate_count"] == "5"
    assert all_debt["schema_support_check_passed"] == "true"
    assert all_debt["replicate_weight_uncertainty_executed"] == "true"
    assert all_debt["combined_standard_error_formula"] == (
        "sqrt((6/5)*imputation_variance+sampling_variance)"
    )
    assert all_debt["current_demand_conversion_available"] == "false"
    assert all_debt["split_denominator_promotion_allowed"] == "false"
    assert all_debt["main_ratio_admission_allowed"] == "false"
    assert all_debt["incidence_output_enabled"] == "false"
    income_debt = next(
        row
        for row in rows
        if row["group_dimension"] == "income_category"
        and row["group_code"] == "1"
        and row["metric"] == "mean_debt"
    )
    assert income_debt["replicate_estimate_count"] == "999"
    assert income_debt["schema_support_check_passed"] == "true"
    assert income_debt["current_demand_conversion_available"] == "false"


def test_fed_shed_financial_fragility_records_keep_gate_fail_closed(tmp_path):
    source_zip = tmp_path / "shed.zip"
    fieldnames = [
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
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerow(
        {
            "shedid": "1",
            "weight": "1.5",
            "B2": "Doing okay",
            "B3": "About the same",
            "B3A_b": "",
            "C3P": "Paid at least the minimum payment on all credit cards",
            "C4A": "Never carried an unpaid balance (always pay in full)",
            "E1_a": "No",
            "E1_b": "No",
            "E1_c": "No",
            "E1_d": "No",
            "E1_e": "No",
            "pay_casheqv": "Yes",
            "ppinc7": "$25,000 to $49,999",
            "ppagect4": "30–44",
        }
    )
    writer.writerow(
        {
            "shedid": "2",
            "weight": "0.5",
            "B2": "Just getting by",
            "B3": "Somewhat worse off",
            "B3A_b": "Yes",
            "C3P": (
                "Did not pay or paid less than the minimum payment on at least one card"
            ),
            "C4A": "Most or all of the time",
            "E1_a": "No",
            "E1_b": "Yes",
            "E1_c": "No",
            "E1_d": "No",
            "E1_e": "No",
            "pay_casheqv": "No",
            "ppinc7": "$25,000 to $49,999",
            "ppagect4": "30–44",
        }
    )
    with zipfile.ZipFile(source_zip, "w") as archive:
        archive.writestr("public2025.csv", buffer.getvalue())

    rows = _fed_shed_financial_fragility_records(source_zip)

    assert rows
    all_cash = next(
        row
        for row in rows
        if row["group_dimension"] == "all"
        and row["metric"] == "can_cover_400_expense_with_cash_equivalent"
    )
    assert all_cash["metric_value"] == "0.75"
    assert all_cash["liquidity_context_available"] == "true"
    all_less_than_minimum = next(
        row
        for row in rows
        if row["group_dimension"] == "all"
        and row["metric"] == "credit_card_paid_less_than_minimum_any_card_last_month"
    )
    assert all_less_than_minimum["metric_value"] == "0.25"
    assert all_less_than_minimum["payment_behavior_context_available"] == "true"
    assert {row["current_demand_conversion_available"] for row in rows} == {"false"}
    assert {row["split_denominator_promotion_allowed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}
