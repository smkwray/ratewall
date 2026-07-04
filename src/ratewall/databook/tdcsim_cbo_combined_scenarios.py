"""Build TDCSim CBO combined narrative scenarios from verified lever specs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CombinedScenarioSpec:
    """A scenario made from non-overlapping TDCSim lever scenarios."""

    output_scenario_id: str
    title: str
    label: str
    component_scenario_ids: tuple[str, ...]
    notes: str
    as_of_date: str = "2026-06-27"


def combined_scenario_payload(
    *,
    base_scenario: Mapping[str, Any],
    component_scenarios: Sequence[Mapping[str, Any]],
    spec: CombinedScenarioSpec,
) -> dict[str, Any]:
    """Return a TDCSim scenario JSON payload combining existing lever overrides."""

    if len(component_scenarios) != len(spec.component_scenario_ids):
        raise ValueError("component_scenarios must match component_scenario_ids")
    by_id = {str(payload["scenario_id"]): payload for payload in component_scenarios}
    missing = [
        scenario_id
        for scenario_id in spec.component_scenario_ids
        if scenario_id not in by_id
    ]
    if missing:
        raise ValueError(f"missing component scenarios: {missing}")

    overrides: dict[str, Any] = {}
    coupling = dict(base_scenario["coupling"])
    component_titles: list[str] = []
    for scenario_id in spec.component_scenario_ids:
        payload = by_id[scenario_id]
        component_titles.append(str(payload.get("title", scenario_id)))
        for key, value in dict(payload.get("overrides", {})).items():
            if key in overrides:
                raise ValueError(f"duplicate override key in combined scenario: {key}")
            overrides[key] = value
        for key, value in dict(payload.get("coupling", {})).items():
            baseline_value = base_scenario["coupling"].get(key)
            if value != baseline_value:
                coupling[key] = value

    return {
        "schema_version": base_scenario["schema_version"],
        "scenario_id": spec.output_scenario_id,
        "title": spec.title,
        "baseline": dict(base_scenario["baseline"]),
        "simulation": dict(base_scenario["simulation"]),
        "coupling": coupling,
        "output": dict(base_scenario["output"]),
        "overrides": overrides,
        "provenance": {
            "kind": "external_source_assumption",
            "label": spec.label,
            "prepared_by": "RateWall combined scenario builder",
            "as_of_date": spec.as_of_date,
            "notes": (
                f"combined_component_scenarios={','.join(spec.component_scenario_ids)};"
                f"component_titles={' | '.join(component_titles)};"
                f"{spec.notes}"
            ),
        },
    }
