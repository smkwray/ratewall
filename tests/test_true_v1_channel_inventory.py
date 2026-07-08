from __future__ import annotations

import pytest

from ratewall.databook.marginal_object_ledger import (
    MarginalObjectLedgerError,
    load_channel_registry,
    load_true_v1_channel_inventory,
    validate_true_v1_channel_inventory,
)


def test_true_v1_inventory_covers_all_required_period_objects() -> None:
    inventory = load_true_v1_channel_inventory()
    by_id = {row["channel_id"]: row for row in inventory["channels"]}

    required = {
        "public_interest_net_block",
        "direct_treasury_interest",
        "bank_treasury_interest",
        "iorb_ioer_reserves",
        "on_rrp",
        "remittances_deferred_asset",
        "taxes",
        "tga_liquidity_absorbers",
        "foreign_leakage",
        "tdc_ex_overlap_beta_chi",
        "d1_safe_yield_payer_flow",
        "residual_mmf_tbill_sidecars",
        "credit_zero_low_apr_insulation",
        "denominator_conventional_drag",
    }
    assert required <= set(by_id)
    for channel_id in required:
        assert set(by_id[channel_id]["period_scope"]) == {
            "historical",
            "current",
            "forecast",
        }


def test_true_v1_inventory_slots_match_theoretical_object() -> None:
    inventory = load_true_v1_channel_inventory()
    by_id = {row["channel_id"]: row for row in inventory["channels"]}

    assert by_id["tdc_ex_overlap_beta_chi"]["selected_slot"] == "Delta_N_selected"
    assert by_id["tdc_ex_overlap_beta_chi"]["overlap_policy"] == (
        "park_income_addendum_when_tdcsim_ex_overlap_collides_with_direct_interest"
    )
    assert by_id["d1_safe_yield_payer_flow"]["selected_slot"] == "Delta_N_selected"
    assert by_id["residual_mmf_tbill_sidecars"]["selected_slot"] == (
        "Delta_N_selected_only_if_admitted_disjoint"
    )
    assert by_id["credit_zero_low_apr_insulation"]["selected_slot"] == "none_in_v1"
    assert by_id["denominator_conventional_drag"]["selected_slot"] == "Delta_D_conv"


def test_channel_registry_keeps_historical_tdc_present_but_blocked() -> None:
    registry = load_channel_registry()
    by_id = {row["channel_id"]: row for row in registry["channels"]}

    tdc = by_id["tdc_ex_overlap_beta_chi"]
    assert tdc["period_scope"] == "historical,current,forecast"
    assert "historical_blocked_until_same_state_replay_pair" in tdc["source_status"]


def test_true_v1_inventory_rejects_credit_as_selected_n() -> None:
    inventory = load_true_v1_channel_inventory()
    mutated = {
        **inventory,
        "channels": [dict(row) for row in inventory["channels"]],
    }
    for row in mutated["channels"]:
        if row["channel_id"] == "credit_zero_low_apr_insulation":
            row["selected_slot"] = "Delta_N_selected"

    with pytest.raises(MarginalObjectLedgerError, match="credit sidecar"):
        validate_true_v1_channel_inventory(mutated)
