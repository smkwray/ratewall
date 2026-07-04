"""Contract constants for the RWTAS V0 monthly engine."""

from __future__ import annotations

from decimal import Decimal

SECTOR_IDS: tuple[str, ...] = (
    "households",
    "nonfinancial_firms",
    "banks_depositories",
    "nonbank_financial",
    "federal_reserve",
    "treasury_federal_government",
    "state_local_public_authorities",
    "rest_of_world",
)

SECTOR_CODES: dict[str, str] = {
    "households": "HH",
    "nonfinancial_firms": "NFC",
    "banks_depositories": "BANK",
    "nonbank_financial": "NBFI",
    "federal_reserve": "FRB",
    "treasury_federal_government": "TREAS",
    "state_local_public_authorities": "SLG",
    "rest_of_world": "ROW",
}

BANNED_COLLAPSED_LABELS: frozenset[str] = frozenset(
    {
        "government",
        "public_sector",
        "financial_sector",
        "private_finance",
    }
)

TAU_MONTH = Decimal("0.08333333333333333333333333333")
BASELINE_SCENARIO_ROLE = "baseline"
SHOCK_SCENARIO_ROLE = "shock"
PASS_TOLERANCE = Decimal("1e-9")
RW_TOLERANCE = Decimal("0.000001")

SIGN_CONVENTIONS: dict[str, str] = {
    "claim_principal": "positive_holder_asset_and_issuer_liability",
    "flow_amount": "positive_payer_to_receiver",
    "sector_net_flow": "receipts_minus_payments",
    "activity_effect_bil": "positive_expansionary_negative_drag",
}

OUTPUT_TABLES: tuple[str, ...] = (
    "out_run_manifest",
    "out_reference_rate_monthly",
    "out_claim_state_monthly",
    "out_claim_rate_monthly",
    "out_flow_ledger_monthly",
    "out_flow_delta_monthly",
    "out_sector_flow_monthly",
    "out_default_state_monthly",
    "out_real_effect_leg_monthly",
    "out_real_effect_cell_monthly",
    "out_ratewall_monthly",
    "out_ratewall_rollup",
    "out_report_channel_monthly",
    "out_report_channel_rollup",
    "out_invariant_check",
)
