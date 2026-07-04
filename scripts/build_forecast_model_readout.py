#!/usr/bin/env python3
"""Build the 10-year TDCSim/CBO RateWall forecast readout."""

from __future__ import annotations

import argparse
from pathlib import Path

from ratewall.databook.forecast_model_readout import (
    central_forecast_surface_rows,
    central_scenario_interpretation_rows,
    DEFAULT_FORECAST_READOUT_SUITE_DIR,
    DEFAULT_FED_SOURCE_CACHE_DIR,
    forecast_channel_classification_rows,
    forecast_composition_surface_rows,
    forecast_numerator_channel_plan_rows,
    forecast_public_interest_net_block_rows_from_directory,
    forecast_residual_numerator_sensitivity_rows_from_directory,
    forecast_scenario_sufficiency_rows_from_directory,
    refresh_fed_forecast_source_cache,
    refresh_residual_sensitivity_source_cache,
    timed_beta_path_rows_from_directory,
    write_forecast_model_readout_outputs,
    zero_low_apr_credit_materiality_rows,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite-dir",
        default=str(DEFAULT_FORECAST_READOUT_SUITE_DIR),
        help="Manifest-backed TDCSim/CBO suite directory.",
    )
    parser.add_argument(
        "--output-dir",
        default="var/preliminary_scenario_results/forecast_10y",
        help="Directory for 10-year forecast CSV, PNG, and Markdown outputs.",
    )
    parser.add_argument(
        "--fed-source-cache-dir",
        default=str(DEFAULT_FED_SOURCE_CACHE_DIR),
        help="Directory for cached official FRED CSV source inputs.",
    )
    parser.add_argument(
        "--refresh-fed-sources",
        action="store_true",
        help="Refresh the small official FRED CSV source cache before building.",
    )
    args = parser.parse_args()

    if args.refresh_fed_sources:
        refreshed = refresh_fed_forecast_source_cache(args.fed_source_cache_dir)
        refreshed += refresh_residual_sensitivity_source_cache(
            args.fed_source_cache_dir
        )
        print(f"refreshed_fed_sources: {len(refreshed)}")
    timed_beta_rows = timed_beta_path_rows_from_directory(args.suite_dir)
    public_interest_rows, fed_source_rows = (
        forecast_public_interest_net_block_rows_from_directory(
            args.suite_dir,
            source_cache_dir=args.fed_source_cache_dir,
        )
    )
    residual_sensitivity_rows, residual_source_rows = (
        forecast_residual_numerator_sensitivity_rows_from_directory(
            args.suite_dir,
            source_cache_dir=args.fed_source_cache_dir,
        )
    )
    composition_surface_rows = forecast_composition_surface_rows(
        timed_beta_rows=timed_beta_rows,
        public_interest_rows=public_interest_rows,
        residual_sensitivity_rows=residual_sensitivity_rows,
    )
    central_forecast_rows = central_forecast_surface_rows(composition_surface_rows)
    central_interpretation_rows = central_scenario_interpretation_rows(
        central_forecast_rows
    )
    scenario_sufficiency_rows = forecast_scenario_sufficiency_rows_from_directory(
        args.suite_dir,
        central_interpretation_rows=central_interpretation_rows,
    )
    channel_rows = forecast_channel_classification_rows()
    numerator_channel_plan_rows = forecast_numerator_channel_plan_rows(channel_rows)
    zero_low_apr_credit_rows = zero_low_apr_credit_materiality_rows()
    outputs = write_forecast_model_readout_outputs(
        Path(args.output_dir),
        timed_beta_rows=timed_beta_rows,
        channel_rows=channel_rows,
        numerator_channel_plan_rows=numerator_channel_plan_rows,
        zero_low_apr_credit_rows=zero_low_apr_credit_rows,
        public_interest_rows=public_interest_rows,
        fed_source_rows=fed_source_rows,
        residual_sensitivity_rows=residual_sensitivity_rows,
        residual_source_rows=residual_source_rows,
        composition_surface_rows=composition_surface_rows,
        central_forecast_rows=central_forecast_rows,
        central_interpretation_rows=central_interpretation_rows,
        scenario_sufficiency_rows=scenario_sufficiency_rows,
    )
    for name, path in outputs.items():
        print(f"{name}: {path}")
    print(f"timed_beta_rows: {len(timed_beta_rows)}")
    print(f"public_interest_rows: {len(public_interest_rows)}")
    print(f"fed_source_rows: {len(fed_source_rows)}")
    print(f"residual_sensitivity_rows: {len(residual_sensitivity_rows)}")
    print(f"residual_source_rows: {len(residual_source_rows)}")
    print(f"composition_surface_rows: {len(composition_surface_rows)}")
    print(f"central_forecast_rows: {len(central_forecast_rows)}")
    print(f"central_interpretation_rows: {len(central_interpretation_rows)}")
    print(f"scenario_sufficiency_rows: {len(scenario_sufficiency_rows)}")
    print(f"channel_rows: {len(channel_rows)}")
    print(f"numerator_channel_plan_rows: {len(numerator_channel_plan_rows)}")
    print(f"zero_low_apr_credit_rows: {len(zero_low_apr_credit_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
