from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
ASSUMPTION_SETS = ROOT / "configs" / "ratewall_assumption_sets.yml"
PARAMETER_PACKS = ROOT / "configs" / "ratewall_parameter_packs.yml"
ASSUMPTION_ENGINE = ROOT / "src" / "ratewall" / "accounting" / "assumption_engine.py"
SPINE_SCENARIOS = ROOT / "src" / "ratewall" / "databook" / "spine_scenarios.py"
CALIBRATED_SCENARIOS = {
    "base_current_100bps",
    "literature_calibrated_low",
    "literature_calibrated_base",
    "literature_calibrated_high",
}
ZERO_FIRM_CASH_ROBUSTNESS_ROW = "literature_calibrated_base_zero_firm_cash_robustness"
CALIBRATED_DENOMINATOR_COMPOSITION = {
    "literature_calibrated_low": {
        "borrowing_cost_drag_share": Decimal("0.30"),
        "credit_supply_drag_share": Decimal("0.15"),
        "asset_price_drag_share": Decimal("0.25"),
        "expectations_drag_share": Decimal("0.15"),
        "exchange_rate_external_drag_share": Decimal("0.15"),
    },
    "literature_calibrated_base": {
        "borrowing_cost_drag_share": Decimal("0.35"),
        "credit_supply_drag_share": Decimal("0.20"),
        "asset_price_drag_share": Decimal("0.20"),
        "expectations_drag_share": Decimal("0.15"),
        "exchange_rate_external_drag_share": Decimal("0.10"),
    },
    "literature_calibrated_high": {
        "borrowing_cost_drag_share": Decimal("0.40"),
        "credit_supply_drag_share": Decimal("0.25"),
        "asset_price_drag_share": Decimal("0.25"),
        "expectations_drag_share": Decimal("0.05"),
        "exchange_rate_external_drag_share": Decimal("0.05"),
    },
}
DENOMINATOR_SHARE_PARAMETERS = tuple(
    next(iter(CALIBRATED_DENOMINATOR_COMPOSITION.values())).keys()
)
LIVE_PACK_BOUND_PARAMETERS = [
    "treasury_repricing_speed_share",
    "treasury_interest_demand_share",
    "iorb_recipient_demand_share",
    "on_rrp_recipient_demand_share",
    "current_remittance_demand_share",
    "future_remittance_drag_demand_share",
    "fiscal_offset_share",
    "tga_liquidity_offset_share",
    "firm_cash_attenuation_share",
    "safe_asset_allocation_offset_share",
    "safe_asset_allocation_drag_share",
    "foreign_treasury_holder_leakage_share",
    "interest_income_tax_timing_leakage_share",
    "contractionary_drag_gdp_share",
    "borrowing_cost_drag_share",
    "credit_supply_drag_share",
    "asset_price_drag_share",
    "expectations_drag_share",
    "exchange_rate_external_drag_share",
    "firm_liquid_asset_stock_share_gdp",
]
EVIDENCE1_NUMERATOR_PARAMETERS = {
    "treasury_interest_demand_share",
    "interest_income_tax_timing_leakage_share",
}
EVIDENCE_A_HEADLINE_PARAMETERS = {
    "iorb_recipient_demand_share",
    "on_rrp_recipient_demand_share",
    "fiscal_offset_share",
    "tga_liquidity_offset_share",
    "firm_cash_attenuation_share",
    "safe_asset_allocation_offset_share",
    "safe_asset_allocation_drag_share",
}
EXP4_DEBT_STATE_DRAG_MULTIPLIER_BY_SCENARIO = {
    "base_current_100bps": Decimal("1.00"),
    "literature_calibrated_low": Decimal("1.00"),
    "literature_calibrated_base": Decimal("1.00"),
    "literature_calibrated_high": Decimal("1.00"),
}
EXP4_DEBT_STATE_DRAG_MULTIPLIER_BAND = {
    "low": Decimal("0.95"),
    "base": Decimal("0.85"),
    "high": Decimal("0.70"),
}
TREASURY_REPRICING_SPEED_BY_SCENARIO = {
    "base_current_100bps": Decimal("0.55"),
    "literature_calibrated_low": Decimal("0.35"),
    "literature_calibrated_base": Decimal("0.55"),
    "literature_calibrated_high": Decimal("0.75"),
}
TREASURY_REPRICING_SPEED_BAND = {
    "low": Decimal("0.35"),
    "base": Decimal("0.55"),
    "high": Decimal("0.75"),
}
EXP7_REMITTANCE_VALUES_BY_SCENARIO = {
    "base_current_100bps": {
        "current_remittance_demand_share": Decimal("0.01"),
        "future_remittance_drag_demand_share": Decimal("0.05"),
    },
    "literature_calibrated_low": {
        "current_remittance_demand_share": Decimal("0.00"),
        "future_remittance_drag_demand_share": Decimal("0.02"),
    },
    "literature_calibrated_base": {
        "current_remittance_demand_share": Decimal("0.01"),
        "future_remittance_drag_demand_share": Decimal("0.05"),
    },
    "literature_calibrated_high": {
        "current_remittance_demand_share": Decimal("0.03"),
        "future_remittance_drag_demand_share": Decimal("0.10"),
    },
}
EXP7_REMITTANCE_BANDS = {
    "current_remittance_demand_share": {
        "low": Decimal("0.00"),
        "base": Decimal("0.01"),
        "high": Decimal("0.03"),
    },
    "future_remittance_drag_demand_share": {
        "low": Decimal("0.02"),
        "base": Decimal("0.05"),
        "high": Decimal("0.10"),
    },
}
EXP1_EVIDENCE_C_BANDS = {
    "household_safe_asset_stock_share": (Decimal("0.30"), Decimal("0.45"), Decimal("0.60")),
    "household_safe_asset_access_conditioner": (
        Decimal("0.45"),
        Decimal("0.65"),
        Decimal("0.80"),
    ),
    "retail_safe_yield_pass_through_beta": (
        Decimal("0.20"),
        Decimal("0.40"),
        Decimal("0.65"),
    ),
    "household_safe_yield_current_spend_share": (
        Decimal("0.04"),
        Decimal("0.08"),
        Decimal("0.13"),
    ),
    "deposit_mmf_substitution_conditioner": (
        Decimal("0.10"),
        Decimal("0.25"),
        Decimal("0.45"),
    ),
    "deposit_mmf_substitution_drag_share": (
        Decimal("0.05"),
        Decimal("0.10"),
        Decimal("0.20"),
    ),
}
EXP1_ACTIVE_ROWS = {
    "assumption_mode_safe_yield_capture_entry": {
        "status": "evidence_c_exp1_household_safe_yield_capture_in_band_assumption_mode",
        "active_fields": {
            "household_safe_asset_stock_share",
            "household_safe_asset_access_conditioner",
            "retail_safe_yield_pass_through_beta",
            "household_safe_yield_current_spend_share",
        },
        "zero_fields": {
            "safe_asset_allocation_offset_share",
            "safe_asset_allocation_drag_share",
            "deposit_mmf_substitution_conditioner",
            "deposit_mmf_substitution_drag_share",
        },
    },
    "assumption_mode_deposit_mmf_paired_entry": {
        "status": "evidence_c_exp1_deposit_mmf_paired_in_band_assumption_mode",
        "active_fields": set(EXP1_EVIDENCE_C_BANDS),
        "zero_fields": {
            "safe_asset_allocation_offset_share",
            "safe_asset_allocation_drag_share",
        },
    },
}
EXP8_EVIDENCE_C_BANDS = {
    "firm_liquid_asset_cushion_share": (
        Decimal("0.02"),
        Decimal("0.05"),
        Decimal("0.10"),
    ),
    "firm_rollover_pressure_share": (
        Decimal("0.05"),
        Decimal("0.12"),
        Decimal("0.25"),
    ),
}
EXP8_DIAGNOSTIC_ROWS = {
    "assumption_mode_firm_cushion_rollover_entry": {
        "status": "evidence_c_exp8_firm_cushion_rollover_diagnostic_only_non_promoted",
        "active_fields": set(EXP8_EVIDENCE_C_BANDS),
        "zero_fields": {"firm_cash_attenuation_share"},
    },
}
STALE_OPTIONAL_HOLD_ROWS = {
    "assumption_mode_consumer_credit_denominator_sidecar": {
        "status": (
            "documented_hold_consumer_credit_sidecar_stale_out_of_band_"
            "keep_zero_for_closure_non_promoted"
        ),
        "zero_fields": {
            "rate_sensitive_consumer_credit_stock_share_gdp",
            "consumer_credit_reprice_beta",
            "consumer_credit_cashflow_drag_conversion",
        },
    },
    "assumption_mode_combined_denominator_sidecar_overlap_discounted": {
        "status": (
            "documented_hold_consumer_credit_sidecar_stale_out_of_band_"
            "keep_zero_for_closure_non_promoted"
        ),
        "zero_fields": {
            "rate_sensitive_consumer_credit_stock_share_gdp",
            "consumer_credit_reprice_beta",
            "consumer_credit_cashflow_drag_conversion",
        },
    },
}
STALE_OPTIONAL_PACK_HOLDS = {
    "rate_sensitive_consumer_credit_stock_share_gdp": (
        "documented_hold_consumer_credit_sidecar_not_activated"
    ),
    "consumer_credit_reprice_beta": (
        "documented_hold_consumer_credit_sidecar_not_activated"
    ),
    "consumer_credit_cashflow_drag_conversion": (
        "documented_hold_consumer_credit_sidecar_not_activated"
    ),
}
PART2_HOLD_NOTES = {
    "pension_insurance": (
        "Lagged institutional pass-through is defensible as zero in a one-year "
        "static/current-demand closure surface; activating it would add a dynamic "
        "timing claim."
    ),
    "fixed_mortgage": (
        "Evidence round C's mortgage shield requires a household-borrowing component; "
        "the current formula applies to generic borrowing drag "
        "(`assumption_engine.py:808-810`), so zero is safer than activating a "
        "mis-scoped attenuation."
    ),
    "tax_timing": (
        "The canonical timing haircut is already calibrated; a recipient-weight "
        "diagnostic adds transparency only and is not needed for closure."
    ),
    "foreign_recycling": (
        "Existing foreign leakage (0.28 base) already removes non-U.S. demand; "
        "recycling is second-order and too close to holder-allocation/incidence "
        "for closure."
    ),
    "consumer_credit": (
        "Even with EXP-6 satisfied, current consumer-credit sidecar rows are "
        "stale/out-of-band (β 0.90 vs Evidence round C high 0.80); keep zero for "
        "closure rather than introduce a last-minute D-side feature."
    ),
}
PART2_HOLD_PACK_PARAMETERS = {
    "foreign_treasury_holder_leakage_share": "foreign_recycling",
    "interest_income_tax_timing_leakage_share": "tax_timing",
    "rate_sensitive_consumer_credit_stock_share_gdp": "consumer_credit",
    "consumer_credit_reprice_beta": "consumer_credit",
    "consumer_credit_cashflow_drag_conversion": "consumer_credit",
    "fixed_mortgage_payment_shield_share_of_household_borrowing_drag": (
        "fixed_mortgage"
    ),
    "pension_contribution_relief_gdp_share_per_100bp_year": "pension_insurance",
    "retirement_insurance_yield_spend_conversion_share": "pension_insurance",
    "pension_insurance_pass_through_lag_years": "pension_insurance",
}


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _assumption_sets() -> list[dict[str, object]]:
    payload = yaml.safe_load(ASSUMPTION_SETS.read_text(encoding="utf-8"))
    return [
        row
        for row in payload["assumption_sets"]
        if row["name"] in CALIBRATED_SCENARIOS
    ]


def _all_assumption_sets() -> dict[str, dict[str, object]]:
    payload = yaml.safe_load(ASSUMPTION_SETS.read_text(encoding="utf-8"))
    return {row["name"]: row for row in payload["assumption_sets"]}


def _parameter_packs() -> dict[str, dict[str, object]]:
    payload = yaml.safe_load(PARAMETER_PACKS.read_text(encoding="utf-8"))
    return {row["parameter"]: row for row in payload["parameter_packs"]}


@pytest.mark.parametrize("parameter", LIVE_PACK_BOUND_PARAMETERS)
def test_calibrated_live_values_are_inside_parameter_pack_bands(parameter: str) -> None:
    packs = _parameter_packs()
    assert parameter in packs
    pack = packs[parameter]
    distribution = pack.get("calibration_distribution", pack)
    low = _decimal(distribution["low"])
    high = _decimal(distribution["high"])

    assert not (low == Decimal("0") and high == Decimal("1"))
    for scenario in _assumption_sets():
        assert parameter in scenario
        value = _decimal(scenario[parameter])
        assert low <= value <= high, (scenario["name"], parameter, value, low, high)


def test_stale_optional_closure_rows_are_documented_holds() -> None:
    assumptions = _all_assumption_sets()
    packs = _parameter_packs()

    assert "promoted_not_source_backed" not in ASSUMPTION_SETS.read_text(
        encoding="utf-8"
    )
    assert "promoted_not_source_backed" not in PARAMETER_PACKS.read_text(
        encoding="utf-8"
    )

    for row_name, expectation in STALE_OPTIONAL_HOLD_ROWS.items():
        row = assumptions[row_name]
        assert row["source_status"] == expectation["status"]
        assert row["assumption_status"].endswith("optional_extension")
        for field in expectation["zero_fields"]:
            assert _decimal(row[field]) == Decimal("0"), (row_name, field)

    for parameter, status in STALE_OPTIONAL_PACK_HOLDS.items():
        assert packs[parameter]["plausibility_status"] == status


def test_part2_documented_holds_are_quoted_and_zero_in_rows() -> None:
    assumptions = _all_assumption_sets()
    packs = _parameter_packs()

    for parameter, note_key in PART2_HOLD_PACK_PARAMETERS.items():
        assert packs[parameter]["hold_note"] == PART2_HOLD_NOTES[note_key]

    consumer_row = assumptions["assumption_mode_consumer_credit_denominator_sidecar"]
    assert consumer_row["hold_note"] == PART2_HOLD_NOTES["consumer_credit"]
    for field in STALE_OPTIONAL_HOLD_ROWS[
        "assumption_mode_consumer_credit_denominator_sidecar"
    ]["zero_fields"]:
        assert _decimal(consumer_row[field]) == Decimal("0")

    combined_row = assumptions["assumption_mode_combined_denominator_sidecar_overlap_discounted"]
    assert combined_row["consumer_credit_hold_note"] == PART2_HOLD_NOTES[
        "consumer_credit"
    ]
    assert combined_row["fixed_mortgage_hold_note"] == PART2_HOLD_NOTES[
        "fixed_mortgage"
    ]
    for field in STALE_OPTIONAL_HOLD_ROWS[
        "assumption_mode_combined_denominator_sidecar_overlap_discounted"
    ]["zero_fields"]:
        assert _decimal(combined_row[field]) == Decimal("0")
    assert _decimal(
        combined_row["fixed_mortgage_payment_shield_share_of_household_borrowing_drag"]
    ) == Decimal("0")

    mortgage_row = assumptions["assumption_mode_housing_lockin_payment_shield_sidecar"]
    assert mortgage_row["hold_note"] == PART2_HOLD_NOTES["fixed_mortgage"]
    assert mortgage_row["source_status"] == (
        "documented_hold_fixed_mortgage_shield_mis_scoped_"
        "keep_zero_for_closure_non_promoted"
    )
    assert _decimal(
        mortgage_row["fixed_mortgage_payment_shield_share_of_household_borrowing_drag"]
    ) == Decimal("0")

    pension_row = assumptions["assumption_mode_dynamic_pension_insurance_lag_sidecar"]
    assert pension_row["hold_note"] == PART2_HOLD_NOTES["pension_insurance"]
    assert pension_row["source_status"] == (
        "documented_hold_pension_insurance_dynamic_timing_"
        "keep_zero_for_closure_non_promoted"
    )
    assert _decimal(
        pension_row["pension_contribution_relief_gdp_share_per_100bp_year"]
    ) == Decimal("0")
    assert _decimal(
        pension_row["retirement_insurance_yield_spend_conversion_share"]
    ) == Decimal("0")
    assert _decimal(pension_row["pension_insurance_pass_through_lag_years"]) == Decimal(
        "0"
    )


def test_exp1_safe_yield_rows_are_active_in_band_without_legacy_overlap() -> None:
    assumptions = _all_assumption_sets()
    packs = _parameter_packs()

    for row_name, expectation in EXP1_ACTIVE_ROWS.items():
        row = assumptions[row_name]
        assert row["source_status"] == expectation["status"]
        for field in expectation["active_fields"]:
            low, base, high = EXP1_EVIDENCE_C_BANDS[field]
            assert _decimal(row[field]) == base
            assert low <= _decimal(row[field]) <= high
        for field in expectation["zero_fields"]:
            assert _decimal(row[field]) == Decimal("0"), (row_name, field)

    for field, (low, base, high) in EXP1_EVIDENCE_C_BANDS.items():
        pack = packs[field]
        assert _decimal(pack["low"]) == low
        assert _decimal(pack["base"]) == base
        assert _decimal(pack["high"]) == high
        if field == "household_safe_yield_current_spend_share":
            assert pack["plausibility_status"] == (
                "proxy_grounded_measurement_weak_link_not_us_evidence_mode"
            )
        else:
            assert (
                pack["plausibility_status"]
                == "evidence_c_exp1_literature_calibrated_assumption_mode"
            )

    chi_pack = packs["household_safe_yield_current_spend_share"]
    joined = " ".join(
        str(chi_pack.get(field, ""))
        for field in (
            "source_status",
            "source_note",
            "literature_context",
            "plausibility_status",
        )
    )
    assert "measurement_weak_link" in joined
    assert "not_us_evidence_mode" in joined
    assert "BoE NMG proxy" in joined
    assert "incidence" in joined


def test_exp8_firm_cushion_rollover_row_is_diagnostic_only_in_band() -> None:
    assumptions = _all_assumption_sets()
    packs = _parameter_packs()

    for row_name, expectation in EXP8_DIAGNOSTIC_ROWS.items():
        row = assumptions[row_name]
        assert row["source_status"] == expectation["status"]
        for field in expectation["active_fields"]:
            low, base, high = EXP8_EVIDENCE_C_BANDS[field]
            assert _decimal(row[field]) == base
            assert low <= _decimal(row[field]) <= high
        for field in expectation["zero_fields"]:
            assert _decimal(row[field]) == Decimal("0"), (row_name, field)

    for field, (low, base, high) in EXP8_EVIDENCE_C_BANDS.items():
        pack = packs[field]
        assert _decimal(pack["low"]) == low
        assert _decimal(pack["base"]) == base
        assert _decimal(pack["high"]) == high
        assert (
            pack["plausibility_status"]
            == "evidence_c_exp8_diagnostic_only_non_promoted"
        )


def test_exp1_beta_namespace_uses_safe_yield_name() -> None:
    for path in (ASSUMPTION_SETS, PARAMETER_PACKS, ASSUMPTION_ENGINE, SPINE_SCENARIOS):
        text = path.read_text(encoding="utf-8")
        assert "retail_deposit_pass_through_beta" not in text
        assert "retail_safe_yield_pass_through_beta" in text


@pytest.mark.parametrize("parameter", sorted(EVIDENCE1_NUMERATOR_PARAMETERS))
def test_evidence1_numerator_parameters_are_headline_admissible(parameter: str) -> None:
    pack = _parameter_packs()[parameter]
    joined = " ".join(
        str(pack.get(field, ""))
        for field in (
            "source_status",
            "source_note",
            "citation_handle",
            "calibration_status",
            "allowed_model_use",
            "forbidden_claim_risk",
            "plausibility_status",
        )
    )

    assert "evidence1" in joined
    assert "blocked_context_only" not in joined
    assert pack["allowed_model_use"] != "sensitivity_only"
    assert pack["forbidden_claim_risk"] != "very_high"


@pytest.mark.parametrize("parameter", sorted(EVIDENCE_A_HEADLINE_PARAMETERS))
def test_evidence_a_live_parameters_are_headline_admissible(parameter: str) -> None:
    pack = _parameter_packs()[parameter]
    joined = " ".join(
        str(pack.get(field, ""))
        for field in (
            "source_status",
            "source_note",
            "candidate_source_literature",
            "citation_handle",
            "calibration_status",
            "allowed_model_use",
            "forbidden_claim_risk",
            "plausibility_status",
        )
    )

    if parameter == "firm_cash_attenuation_share":
        assert "direction_only_weakest_link" in joined
    else:
        assert "evidenceA" in joined
    assert "blocked_context_only" not in joined
    assert "blocked_until" not in joined
    assert pack["allowed_model_use"] != "sensitivity_only"
    assert pack["forbidden_claim_risk"] != "very_high"


def test_evidence_a_tdc_total_deposit_beta_pack_is_memo_only() -> None:
    pack = _parameter_packs()["tdc_total_deposit_beta"]
    distribution = pack["calibration_distribution"]

    assert {
        "low": _decimal(distribution["low"]),
        "base": _decimal(distribution["base"]),
        "high": _decimal(distribution["high"]),
    } == {
        "low": Decimal("0.2479"),
        "base": Decimal("0.3249"),
        "high": Decimal("0.6163"),
    }
    assert "evidenceA" in pack["citation_handle"]
    assert pack["source_status"] == (
        "evidence_g_internal_estimator_prior_pending_regression_artifacts_not_literature_grounded"
    )
    assert pack["calibration_status"] == (
        "internal_estimator_prior_pending_regression_reproduction_not_consumed"
    )
    assert pack["allowed_model_use"] == "memo_only_not_live_parameter"
    assert "threshold math" in distribution["formula"]
    assert "pending regression artifact, vintages, and import contract" in distribution[
        "formula"
    ]
    assert pack["forbidden_claim_risk"] != "very_high"


def test_evidence_g_grounding_rulings_are_applied_to_demoted_bands() -> None:
    assumptions = _all_assumption_sets()
    packs = _parameter_packs()

    denominator = packs["contractionary_drag_gdp_share"]
    denominator_distribution = denominator["calibration_distribution"]
    assert {
        "low": _decimal(denominator_distribution["low"]),
        "base": _decimal(denominator_distribution["base"]),
        "high": _decimal(denominator_distribution["high"]),
    } == {
        "low": Decimal("0.0035"),
        "base": Decimal("0.00776"),
        "high": Decimal("0.0130"),
    }
    assert denominator["source_status"] == (
        "assumption_irf_normalized_literature_prior; contractionary_drag_gdp_share "
        "low/base/high = 0.0035/0.00776/0.0130, representing the h≈12-month "
        "real-GDP-level drag per +100bp US monetary tightening; normalized from "
        "GK2015/BRW2019-21/RR2004/Coibion2012/JK2020/MAR2021; IP rows use "
        "IP→GDP scalar 0.40; labeled prior only, not a project re-estimation "
        "or identification claim."
    )
    assert "IP→GDP scalar 0.40" in denominator_distribution["formula"]

    firm_cash = packs["firm_cash_attenuation_share"]
    assert firm_cash["source_status"] == (
        "evidence_g_direction_only_firm_cash_weakest_link_not_magnitude_grounded"
    )
    assert firm_cash["calibration_status"] == (
        "evidence_g_direction_only_weakest_link_labeled_prior"
    )
    assert firm_cash["plausibility_status"] == (
        "direction_only_weakest_link_not_magnitude_grounded"
    )
    assert "not magnitude-grounded literature calibration" in firm_cash[
        "calibration_distribution"
    ]["formula"]
    assert firm_cash["robustness_run"] == ZERO_FIRM_CASH_ROBUSTNESS_ROW

    robustness = assumptions[ZERO_FIRM_CASH_ROBUSTNESS_ROW]
    assert robustness["source_status"] == (
        "evidence_g_zero_firm_cash_robustness_direction_only_weakest_link"
    )
    assert robustness["assumption_status"] == "robustness_firm_cash_zero_weakest_link"
    assert _decimal(robustness["firm_cash_attenuation_share"]) == Decimal("0")
    assert _decimal(robustness["contractionary_drag_gdp_share"]) == Decimal("0.00776")


def test_calibrated_denominator_shares_sum_to_one_in_config() -> None:
    for scenario in _assumption_sets():
        share_sum = sum(
            _decimal(scenario[parameter])
            for parameter in DENOMINATOR_SHARE_PARAMETERS
        )
        assert share_sum == Decimal("1.00"), (scenario["name"], share_sum)


def test_literature_calibrated_denominator_composition_is_coherent() -> None:
    scenarios = {row["name"]: row for row in _assumption_sets()}

    for scenario_name, expected in CALIBRATED_DENOMINATOR_COMPOSITION.items():
        scenario = scenarios[scenario_name]
        assert {
            parameter: _decimal(scenario[parameter])
            for parameter in DENOMINATOR_SHARE_PARAMETERS
        } == expected


def test_debt_state_drag_multiplier_is_sensitivity_only_and_admissible() -> None:
    scenarios = {row["name"]: row for row in _assumption_sets()}
    pack = _parameter_packs()["debt_state_drag_multiplier"]

    assert {
        "low": _decimal(pack["low"]),
        "base": _decimal(pack["base"]),
        "high": _decimal(pack["high"]),
    } == EXP4_DEBT_STATE_DRAG_MULTIPLIER_BAND
    assert pack["source_status"] == (
        "evidence_g_direction_only_debt_state_sensitivity_not_headline"
    )
    assert pack["plausibility_status"] == (
        "direction_only_sensitivity_not_magnitude_grounded"
    )
    assert pack["allowed_model_use"] == (
        "debt_state_sensitivity_table_not_canonical_headline"
    )
    assert pack["calibration_order"] == "descending_attenuation"
    assert "canonical headline uses 1.00 state-neutral denominator" in (
        pack["calibration_distribution"]["formula"]
    )
    assert pack["forbidden_claim_risk"] != "very_high"

    for scenario_name, expected in EXP4_DEBT_STATE_DRAG_MULTIPLIER_BY_SCENARIO.items():
        scenario = scenarios[scenario_name]
        assert _decimal(scenario["debt_state_drag_multiplier"]) == expected


def test_treasury_repricing_speed_evidence_c_band_is_headline_live() -> None:
    scenarios = {row["name"]: row for row in _assumption_sets()}
    pack = _parameter_packs()["treasury_repricing_speed_share"]
    distribution = pack["calibration_distribution"]

    assert {
        "low": _decimal(pack["low"]),
        "base": _decimal(pack["base"]),
        "high": _decimal(pack["high"]),
    } == TREASURY_REPRICING_SPEED_BAND
    assert {
        "low": _decimal(distribution["low"]),
        "base": _decimal(distribution["base"]),
        "high": _decimal(distribution["high"]),
    } == TREASURY_REPRICING_SPEED_BAND
    assert pack["source_status"] == (
        "evidence_c_part2_treasury_cash_interest_accrual_speed_assumption_mode"
    )
    assert pack["calibration_status"] == (
        "evidence_c_part2_literature_calibrated_assumption_mode"
    )
    assert pack["allowed_model_use"] == (
        "assumption_mode_headline_treasury_cashflow_timing_factor"
    )
    assert "speed and pass-through are distinct single-pass factors" in distribution[
        "formula"
    ]

    for scenario_name, expected in TREASURY_REPRICING_SPEED_BY_SCENARIO.items():
        assert _decimal(scenarios[scenario_name]["treasury_repricing_speed_share"]) == expected


def test_exp7_remittance_bands_are_active_signed_and_xor_metadata_only() -> None:
    scenarios = {row["name"]: row for row in _assumption_sets()}
    packs = _parameter_packs()

    for parameter, expected_band in EXP7_REMITTANCE_BANDS.items():
        pack = packs[parameter]
        assert {
            "low": _decimal(pack["low"]),
            "base": _decimal(pack["base"]),
            "high": _decimal(pack["high"]),
        } == expected_band
        assert pack["source_status"].startswith("evidence_c_exp7")
        assert pack["plausibility_status"] == (
            "evidence_c_exp7_literature_calibrated_assumption_mode"
        )
        assert pack["forbidden_claim_risk"] != "very_high"
        assert "Evidence" not in pack["allowed_model_use"]

    for scenario_name, expected in EXP7_REMITTANCE_VALUES_BY_SCENARIO.items():
        scenario = scenarios[scenario_name]
        assert {
            parameter: _decimal(scenario[parameter])
            for parameter in EXP7_REMITTANCE_BANDS
        } == expected

    xor_pack = packs["tdcsim_remittance_overlap_exclusion_share"]
    assert {
        "low": _decimal(xor_pack["low"]),
        "base": _decimal(xor_pack["base"]),
        "high": _decimal(xor_pack["high"]),
    } == {
        "low": Decimal("1.00"),
        "base": Decimal("1.00"),
        "high": Decimal("1.00"),
    }
    assert xor_pack["allowed_model_use"] == (
        "tdcsim_static_remittance_xor_invariant_only"
    )
    assert xor_pack["plausibility_status"] == (
        "tdcsim_remittance_component_xor_verified"
    )
    assert "not consumed by assumption_engine.py" in xor_pack[
        "calibration_distribution"
    ]["formula"]
