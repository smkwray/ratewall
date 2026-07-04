#!/usr/bin/env python3
"""Build Treasury supply/maturity shock diagnostic outputs."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ratewall.databook.treasury_supply_maturity_shock import (
    official_fspdp_gdp_panel_rows,
    phillot_daily_yield_bridge_rows,
    phillot_package_schema_audit_rows,
    phillot_treasury_auction_instrument_rows,
    treasury_event_window_yield_path_object_rows,
    treasury_supply_maturity_h4_fspdp_response_rows,
    treasury_supply_maturity_path_objects_with_h4_response,
    treasury_supply_maturity_shock_coefficient_admission_rows,
    treasury_supply_maturity_shock_source_inventory_rows,
    write_phillot_daily_yield_bridge_csv,
    write_phillot_package_schema_audit_csv,
    write_phillot_treasury_auction_instrument_csv,
    write_treasury_supply_maturity_h4_fspdp_response_csv,
    write_treasury_supply_maturity_shock_coefficient_admission_csv,
    write_treasury_supply_maturity_shock_path_object_csv,
    write_treasury_supply_maturity_shock_source_inventory_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/treasury_supply_maturity_shock",
        help="Directory for Treasury shock diagnostic CSV outputs.",
    )
    parser.add_argument(
        "--event-window-yield-path-csv",
        default="",
        help=(
            "Optional CSV of event-window 5y/10y/30y yield-bp path candidates. "
            "Rows are admitted only through the Treasury shock path-object gate."
        ),
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    sources = treasury_supply_maturity_shock_source_inventory_rows()
    audit = phillot_package_schema_audit_rows()
    instruments = phillot_treasury_auction_instrument_rows()
    daily_bridge = phillot_daily_yield_bridge_rows()
    event_window_candidates = _read_optional_csv(args.event_window_yield_path_csv)
    initial_path_objects = treasury_event_window_yield_path_object_rows(
        event_window_candidates
    )
    h4_response = treasury_supply_maturity_h4_fspdp_response_rows(
        initial_path_objects,
        official_fspdp_gdp_panel_rows(),
    )
    path_objects = treasury_supply_maturity_path_objects_with_h4_response(
        initial_path_objects,
        h4_response,
    )
    admission = treasury_supply_maturity_shock_coefficient_admission_rows(
        path_objects
    )
    outputs = {
        "source_inventory_csv": write_treasury_supply_maturity_shock_source_inventory_csv(
            output_dir / "ratewall_treasury_supply_maturity_shock_source_inventory.csv",
            sources,
        ),
        "phillot_package_audit_csv": write_phillot_package_schema_audit_csv(
            output_dir / "ratewall_phillot_package_schema_audit.csv",
            audit,
        ),
        "phillot_instrument_csv": write_phillot_treasury_auction_instrument_csv(
            output_dir / "ratewall_phillot_treasury_auction_instrument.csv",
            instruments,
        ),
        "phillot_daily_yield_bridge_csv": write_phillot_daily_yield_bridge_csv(
            output_dir / "ratewall_phillot_daily_yield_bridge.csv",
            daily_bridge,
        ),
        "h4_fspdp_response_csv": write_treasury_supply_maturity_h4_fspdp_response_csv(
            output_dir / "ratewall_treasury_supply_maturity_h4_fspdp_response.csv",
            h4_response,
        ),
        "path_object_csv": write_treasury_supply_maturity_shock_path_object_csv(
            output_dir / "ratewall_treasury_supply_maturity_shock_path_object.csv",
            path_objects,
        ),
        "coefficient_admission_csv": write_treasury_supply_maturity_shock_coefficient_admission_csv(
            output_dir
            / "ratewall_treasury_supply_maturity_shock_coefficient_admission.csv",
            admission,
        ),
    }
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"source_rows: {len(sources)}")
    print(f"package_audit_rows: {len(audit)}")
    print(f"instrument_rows: {len(instruments)}")
    print(f"daily_yield_bridge_rows: {len(daily_bridge)}")
    print(f"event_window_yield_candidate_rows: {len(event_window_candidates)}")
    print(f"h4_fspdp_response_rows: {len(h4_response)}")
    print(f"path_object_rows: {len(path_objects)}")
    print(f"coefficient_admission_rows: {len(admission)}")
    print(
        "admitted_coefficients: "
        f"{sum(row['coefficient_admission_status'] == 'admitted_noncanonical_treasury_supply_maturity_coefficient' for row in admission)}"
    )
    return 0


def _read_optional_csv(path_value: str) -> list[dict[str, str]]:
    if not path_value:
        return []
    path = Path(path_value)
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
