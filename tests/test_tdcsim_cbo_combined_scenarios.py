from __future__ import annotations

import pytest

from ratewall.databook.tdcsim_cbo_combined_scenarios import (
    CombinedScenarioSpec,
    combined_scenario_payload,
)


def _base() -> dict[str, object]:
    return {
        "schema_version": "tdcsim_cbo_scenario_v1",
        "scenario_id": "cbo_baseline_noop_v1",
        "title": "Baseline",
        "baseline": {"package_id": "pkg"},
        "simulation": {"start_date": "2026-06-21", "end_date": "2027-09-30"},
        "coupling": {
            "frn_benchmark": "independent_explicit_path",
            "operating_cash_inflation": "baseline_cpi",
            "primary_deficit_to_debt_target": "independent_no_plug",
            "tips_real_yield": "independent_explicit_path",
        },
        "output": {"profile": "compact"},
        "overrides": {},
    }


def _component(
    scenario_id: str,
    *,
    overrides: dict[str, object],
    coupling: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "title": scenario_id,
        "coupling": coupling or _base()["coupling"],
        "overrides": overrides,
    }


def test_combined_scenario_payload_merges_non_overlapping_levers() -> None:
    payload = combined_scenario_payload(
        base_scenario=_base(),
        component_scenarios=[
            _component(
                "primary_up",
                overrides={"primary_deficit": {"mode": "scale_path", "scale": 1.01}},
            ),
            _component(
                "holder_mix",
                overrides={"holder_preferences": {"mode": "dated_static_shares"}},
            ),
            _component(
                "issuance_rate",
                overrides={
                    "issuance_mix": {"mode": "replace_shares"},
                    "nominal_yield_curve": {"mode": "key_rate_bp"},
                    "frn_benchmark": {"mode": "linked_to_nominal_curve"},
                },
                coupling={
                    **_base()["coupling"],
                    "frn_benchmark": "derive_from_scenario_nominal_curve",
                },
            ),
        ],
        spec=CombinedScenarioSpec(
            output_scenario_id="combined",
            title="Combined",
            label="Combined label",
            component_scenario_ids=("primary_up", "holder_mix", "issuance_rate"),
            notes="composite_not_one_factor",
        ),
    )

    assert payload["scenario_id"] == "combined"
    assert set(payload["overrides"]) == {
        "primary_deficit",
        "holder_preferences",
        "issuance_mix",
        "nominal_yield_curve",
        "frn_benchmark",
    }
    assert payload["coupling"]["frn_benchmark"] == (
        "derive_from_scenario_nominal_curve"
    )
    assert "composite_not_one_factor" in payload["provenance"]["notes"]


def test_combined_scenario_payload_fails_on_duplicate_override_key() -> None:
    with pytest.raises(ValueError, match="duplicate override key"):
        combined_scenario_payload(
            base_scenario=_base(),
            component_scenarios=[
                _component("one", overrides={"primary_deficit": {"scale": 1.01}}),
                _component("two", overrides={"primary_deficit": {"scale": 0.99}}),
            ],
            spec=CombinedScenarioSpec(
                output_scenario_id="combined",
                title="Combined",
                label="Combined label",
                component_scenario_ids=("one", "two"),
                notes="duplicate",
            ),
        )


def test_combined_scenario_payload_requires_all_named_components() -> None:
    with pytest.raises(ValueError, match="missing component scenarios"):
        combined_scenario_payload(
            base_scenario=_base(),
            component_scenarios=[
                _component("one", overrides={"primary_deficit": {"scale": 1.01}}),
                _component("other", overrides={"holder_preferences": {"mode": "x"}}),
            ],
            spec=CombinedScenarioSpec(
                output_scenario_id="combined",
                title="Combined",
                label="Combined label",
                component_scenario_ids=("one", "missing"),
                notes="missing",
            ),
        )
