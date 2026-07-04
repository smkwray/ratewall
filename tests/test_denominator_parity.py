from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.denominator_parity import (
    DENOMINATOR_PARITY_BRIDGE_FIELDS,
    DENOMINATOR_SCENARIO_DELTA_AUDIT_FIELDS,
    DENOMINATOR_VARIANT_SURFACE_FIELDS,
    denominator_parity_bridge_rows,
    denominator_scenario_delta_audit_rows,
    denominator_variant_surface_rows,
    write_denominator_parity_outputs,
)
from ratewall.databook.denominator_response_coefficient import (
    FRBUS_STRUCTURAL_COEFFICIENT,
    FRBUS_STRUCTURAL_PROFILE_ID,
)


def test_denominator_bridge_selects_moving_d_for_rate_scenarios(
    tmp_path: Path,
) -> None:
    root = _write_forecast_fixture(tmp_path)

    rows = denominator_parity_bridge_rows(forecast_readout_dir=root)
    variants = denominator_variant_surface_rows(rows)
    audit_rows = denominator_scenario_delta_audit_rows(rows)

    assert {field for row in rows for field in row} == set(
        DENOMINATOR_PARITY_BRIDGE_FIELDS
    )
    assert {field for row in variants for field in row} == set(
        DENOMINATOR_VARIANT_SURFACE_FIELDS
    )
    assert {field for row in audit_rows for field in row} == set(
        DENOMINATOR_SCENARIO_DELTA_AUDIT_FIELDS
    )
    by_scenario = {row["scenario_id"]: row for row in rows}
    baseline = by_scenario["baseline"]
    assert baseline["fixed_runtime_D_bil"] == "100"
    assert baseline["path_D_bil"] == "100"
    assert baseline["selected_D_bil"] == "100"
    assert baseline["rate_changing_scenario_flag"] == "false"
    assert baseline["c_D_object_id"] == FRBUS_STRUCTURAL_PROFILE_ID
    assert baseline["c_D"] == FRBUS_STRUCTURAL_COEFFICIENT

    rate_down = by_scenario["rate_down_25bp"]
    assert rate_down["path_D_bil"] == "100"
    assert rate_down["moving_D_bil"] == "90"
    assert rate_down["selected_D_bil"] == "90"
    assert rate_down["rate_changing_scenario_flag"] == "true"
    assert rate_down["selected_denominator_variant_role"] == (
        "selected_moving_D_for_rate_changing_forecast_scenario"
    )

    holder = by_scenario["private_holder_high"]
    assert holder["moving_D_bil"] == "100"
    assert holder["selected_denominator_variant_role"] == (
        "selected_path_D_for_nonrate_forecast_scenario"
    )
    assert {row["check_status"] for row in audit_rows} == {"pass"}


def test_denominator_bridge_outputs_are_written(tmp_path: Path) -> None:
    root = _write_forecast_fixture(tmp_path)
    rows = denominator_parity_bridge_rows(forecast_readout_dir=root)
    variants = denominator_variant_surface_rows(rows)
    audit_rows = denominator_scenario_delta_audit_rows(rows)

    outputs = write_denominator_parity_outputs(
        tmp_path / "out",
        bridge_rows=rows,
        variant_rows=variants,
        audit_rows=audit_rows,
    )

    assert outputs["bridge_csv"].read_text(encoding="utf-8").startswith(
        "denominator_parity_bridge_row_id,"
    )
    assert outputs["variant_csv"].read_text(encoding="utf-8").startswith(
        "denominator_variant_surface_row_id,"
    )
    assert outputs["audit_csv"].read_text(encoding="utf-8").startswith(
        "denominator_scenario_delta_audit_row_id,"
    )


def _write_forecast_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "forecast"
    root.mkdir()
    _write_csv(
        root / "ratewall_forecast_central_scenario_surface.csv",
        [
            _central("baseline", "baseline", "100"),
            _central("rate_down_25bp", "baseline", "90"),
            _central("private_holder_high", "baseline", "100"),
        ],
    )
    return root


def _central(scenario_id: str, baseline: str, d_value: str) -> dict[str, str]:
    return {
        "fiscal_year": "2036",
        "scenario_id": scenario_id,
        "baseline_scenario_id": baseline,
        "central_moving_denominator_bil": d_value,
    }


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = sorted({field for row in rows for field in row})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
