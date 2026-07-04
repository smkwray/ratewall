from scripts.materialize_recipient_leakage_sources import (
    _fed_cross_border_treasury_basis_trade_records,
)


def test_fed_cross_border_treasury_basis_trade_records_keep_gate_fail_closed():
    html = """
    <html><body>
    <h1>The Cross-Border Trail of the Treasury Basis Trade</h1>
    <p>around $1.4 trillion as of the end of 2024</p>
    <p>reaching $1.85 trillion by the end of 2024</p>
    <p>TIC data are collected for the Financial Accounts of the United States.</p>
    <h2>Appendix A - Estimating Cayman Islands' Holdings</h2>
    <p>confidential fund-level data from Form PF</p>
    <p>publicly available data from the Financial Accounts</p>
    <p>Enhanced Financial Accounts</p>
    <p>ultimate nationality basis</p>
    </body></html>
    """
    accessible_html = """
    <html><body>
    <h1>The Cross-Border Trail of the Treasury Basis Trade, Accessible Data</h1>
    <h2>Adjusted TIC data for Estimated Holdings of Treasury Securities</h2>
    <h2>Figure A1. Estimating Cayman Islands Hedge Funds</h2>
    <p>Estimate using Z.1</p>
    <p>Cayman Hedge Funds</p>
    </body></html>
    """

    rows = _fed_cross_border_treasury_basis_trade_records(html, accessible_html)

    assert len(rows) == 5
    assert rows[0]["metric"] == "tic_undercount_estimate_end_2024"
    assert rows[0]["metric_value"] == "1400"
    assert rows[1]["metric"] == "cayman_hedge_fund_treasury_holdings_end_2024"
    assert rows[1]["metric_value"] == "1850"
    assert rows[2]["metric"] == "public_z1_efa_proxy_available"
    assert rows[3]["metric"] == "ultimate_nationality_caveat_available"
    assert {row["public_proxy_available"] for row in rows} == {"true"}
    assert {row["confidential_dependency"] for row in rows} == {
        "form_pf_fund_level_data_not_public"
    }
    assert {row["domestic_demand_timing_bridge"] for row in rows} == {"false"}
    assert {row["recycling_to_current_us_demand"] for row in rows} == {"false"}
    assert {row["holder_allocation_enabled"] for row in rows} == {"false"}
    assert {row["promotion_gate_passed"] for row in rows} == {"false"}
    assert {row["main_ratio_admission_allowed"] for row in rows} == {"false"}
