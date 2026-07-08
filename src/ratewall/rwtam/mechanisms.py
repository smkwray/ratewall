"""Scenario-only mechanism wave for placeholder-first RWTAM builds."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.scenarios import (
    SCENARIOS,
    STATIC_SWEEP_SHOCKS,
    ScenarioResult,
    _load_distress_pack,
    _scenario_state_from_profile,
    _shock_path,
)
from ratewall.rwtam.v1 import (
    BANDS,
    CURRENT_DEFAULT_OBJECT_STAMP,
    START_YEAR,
    _conversion,
    _d,
    _effective_pack,
    _fmt,
    _load_pack,
    _month_index_from_label,
    _opening_by_family,
    _read_csv_rows,
    _treasury_yield_delta_bp,
    _write_rows,
    build_v1,
)


MECHANISM_SCENARIO_ID = "mechanism_wave_placeholder"
GDP_BIL = Decimal("31866")
HOLDER_STRESS_CLASSES = ("banks", "dealers", "pensions_insurers", "open_end_bond_funds")
DSR_BUCKETS = (
    ("p10", Decimal("0.40"), Decimal("0.10")),
    ("p25", Decimal("0.70"), Decimal("0.15")),
    ("p50", Decimal("1.00"), Decimal("0.50")),
    ("p75", Decimal("1.30"), Decimal("0.15")),
    ("p90", Decimal("1.60"), Decimal("0.10")),
)
MIGRATION_BANDS = {
    "low": {"elasticity": Decimal("0.02"), "activation": Decimal("3"), "cap": Decimal("0.30")},
    "base": {"elasticity": Decimal("0.05"), "activation": Decimal("2"), "cap": Decimal("0.50")},
    "high": {"elasticity": Decimal("0.10"), "activation": Decimal("1"), "cap": Decimal("0.70")},
}
INFLATION_SLOPES = {"slack": Decimal("0.05"), "balanced": Decimal("0.10"), "tight": Decimal("0.20")}
PRICE_SHARES = {"slack": Decimal("0.30"), "balanced": Decimal("0.50"), "tight": Decimal("0.70")}


@dataclass(frozen=True)
class MechanismWaveResult:
    """CSV-ready mechanism-wave tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


def build_mechanism_wave(pack_dir: Path = Path("configs/rwtam/packs")) -> MechanismWaveResult:
    raw_pack = _load_pack(pack_dir)
    pack = _effective_pack(raw_pack, True, True)
    base_v1 = build_v1(pack_dir)
    distress = _load_distress_pack(pack_dir / "distress")
    bond_rows = base_v1.rows("out_bond_mtm_diagnostic")

    holder = _holder_stress_ledger(pack, bond_rows)
    dsr_distribution = _dsr_distribution_rows(distress)
    dsr_crossing = _dsr_crossing_profile(distress, dsr_distribution)
    response_config, response_comparison = _episode_response_rows(pack_dir)
    migration = _migration_path(pack)
    inflation = _inflation_overlay(base_v1)
    slot_map = _slot_map_rows()
    placeholders = _placeholder_rows(
        holder,
        dsr_distribution,
        response_config,
        migration,
        inflation,
        slot_map,
    )
    invariants = _mechanism_invariants(
        base_v1,
        holder,
        bond_rows,
        placeholders,
    )
    return MechanismWaveResult(
        {
            "out_holder_stress_ledger": holder,
            "out_dsr_distribution_support": dsr_distribution,
            "out_dsr_dispersion_crossing_profile": dsr_crossing,
            "out_episode_response_form_config": response_config,
            "out_episode_response_form_comparison": response_comparison,
            "out_endogenous_financialization_migration_path": migration,
            "out_inflation_overlay_diagnostic": inflation,
            "out_mechanism_placeholder_rows": placeholders,
            "out_mechanism_slot_map": slot_map,
            "out_mechanism_invariant_check": invariants,
        }
    )


def write_mechanism_wave_outputs(
    result: MechanismWaveResult,
    output_dir: Path = Path("var/rwtam/scenarios/mechanism_wave"),
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_mechanism_wave_report(
    result: MechanismWaveResult,
    output_path: Path = Path("do/rwtam_mechanism_wave_report_20260702.md"),
) -> Path:
    invariants = {row["check_id"]: row["status"] for row in result.rows("out_mechanism_invariant_check")}
    placeholders = result.rows("out_mechanism_placeholder_rows")
    crossing = result.rows("out_dsr_dispersion_crossing_profile")
    response = result.rows("out_episode_response_form_comparison")
    migration = result.rows("out_endogenous_financialization_migration_path")
    inflation = result.rows("out_inflation_overlay_diagnostic")
    slot_map = result.rows("out_mechanism_slot_map")
    holder = result.rows("out_holder_stress_ledger")

    lines = [
        "# RWTAM mechanism-first wave",
        "",
        "Date: 2026-07-02.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Policy: build-first, calibrate-later. All values in this wave are scenario/diagnostic placeholders and carry `owner_assumption_mode` plus `include_flag=0` where applicable.",
        "",
        "## Gates",
        "",
        "| check | status |",
        "| --- | --- |",
    ]
    for check_id, status in invariants.items():
        lines.append(f"| {check_id} | {status} |")
    lines.extend(
        [
            "",
            "## M1 holder stress wiring",
            "",
            "| holder class | MTM/buffer | runnable metric | forced-sale flow | credit hook |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in holder:
        lines.append(
            "| {holder_class} | {mtm_loss_share_of_buffer} | {runnable_funding_metric} | {forced_sale_flow_bil} | {credit_supply_contraction_hook_bil} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## M2 de-synchronized crossing profile",
            "",
            "| family | cell | transition | first bucket | any-bucket shock | majority shock | p50 shock |",
            "| --- | --- | --- | --- | ---: | ---: | ---: |",
        ]
    )
    for row in crossing[:24]:
        lines.append(
            "| {family} | {cell_or_sector} | {transition} | {first_crossing_bucket} | {minimum_static_hold_shock_bp_any_bucket} | {minimum_static_hold_shock_bp_share_ge_50} | {minimum_static_hold_shock_bp_p50} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## M3 response-form comparison",
            "",
            "| layer | shock | linear | selected form | capped/saturating | difference |",
            "| --- | ---: | ---: | --- | ---: | ---: |",
        ]
    )
    for row in response:
        lines.append(
            "| {layer_id} | {shock_bp} | {linear_response_bil} | {functional_form} | {selected_response_bil} | {selected_minus_linear_bil} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## M4 endogenous migration path",
            "",
            "| month | shock bp | base migration share | checkable migrated | base N effect |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in migration[::6]:
        lines.append(
            "| {month} | {shock_bp} | {migration_share_base} | {migrated_stock_base_bil} | {N_effect_base_bil} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## M5 inflation effectiveness",
            "",
            "| shock | slack state | no-wall inflation reduction per 100bp | with-wall reduction per 100bp | attenuation |",
            "| ---: | --- | ---: | ---: | ---: |",
        ]
    )
    for row in inflation:
        lines.append(
            "| {shock_bp} | {slack_state} | {inflation_reduction_no_wall_pp_per_100bp} | {inflation_reduction_with_wall_pp_per_100bp} | {wall_attenuation_pp_per_100bp} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Placeholder count and slot map",
            "",
            f"- New placeholder rows emitted by this wave: `{len(placeholders)}`.",
            "- Existing V1 flagged-assumption rows remain separate; this wave does not mutate `out_flagged_assumptions.csv`.",
            "",
            "| pack | fills rows | output slot |",
            "| --- | --- | --- |",
        ]
    )
    for row in slot_map:
        lines.append(f"| {row['in_flight_pack']} | {row['placeholder_row_selector']} | {row['output_table']} |")
    lines.extend(
        [
            "",
            "## Output locations",
            "",
            "- `var/rwtam/scenarios/mechanism_wave/out_holder_stress_ledger.csv`",
            "- `var/rwtam/scenarios/mechanism_wave/out_dsr_dispersion_crossing_profile.csv`",
            "- `var/rwtam/scenarios/mechanism_wave/out_episode_response_form_comparison.csv`",
            "- `var/rwtam/scenarios/mechanism_wave/out_endogenous_financialization_migration_path.csv`",
            "- `var/rwtam/scenarios/mechanism_wave/out_inflation_overlay_diagnostic.csv`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def validate_holder_stress_overlap_rows(
    holder_rows: list[dict[str, str]],
    bond_rows: list[dict[str, str]],
) -> list[str]:
    bond_keys = {
        row.get("overlap_key", "") for row in bond_rows
    } | {row.get("exposure_id", "") for row in bond_rows}
    errors: list[str] = []
    for row in holder_rows:
        key = row.get("mtm_overlap_key", "")
        if key in bond_keys:
            errors.append(f"holder stress reuses bond-MTM overlap key {key}")
        if row.get("include_flag") not in {"0", "false", "False"}:
            errors.append(f"holder stress row {row.get('holder_class')} is not include_flag=0")
    return errors


def _holder_stress_ledger(
    pack: dict[str, list[dict[str, str]]],
    bond_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    calibrated_dir = Path("configs/rwtam/packs/holder_balance_sheet_stress")
    if calibrated_dir.exists():
        return _calibrated_holder_stress_ledger(calibrated_dir, bond_rows, pack)

    opening = _opening_by_family(pack)
    bond_mtm_base = sum(_d(row["diagnostic_D_base_bil"]) for row in bond_rows)
    params = {
        "banks": {
            "duration": Decimal("4.5"),
            "htm": Decimal("0.5"),
            "buffer": Decimal("0.10"),
            "runnable": Decimal("0.30"),
            "asset_base": opening.get("treasury_notes_bonds_tips", Decimal("0")) * Decimal("0.08"),
            "threshold": Decimal("0.35"),
            "slope": Decimal("0.20"),
        },
        "dealers": {
            "duration": Decimal("2.0"),
            "htm": Decimal("0"),
            "buffer": Decimal("0.06"),
            "runnable": Decimal("0.55"),
            "asset_base": opening.get("treasury_bills", Decimal("0")) * Decimal("0.05"),
            "threshold": Decimal("0.25"),
            "slope": Decimal("0.35"),
        },
        "pensions_insurers": {
            "duration": Decimal("7.0"),
            "htm": Decimal("0.25"),
            "buffer": Decimal("0.12"),
            "runnable": Decimal("0.10"),
            "asset_base": opening.get("treasury_notes_bonds_tips", Decimal("0")) * Decimal("0.06"),
            "threshold": Decimal("0.50"),
            "slope": Decimal("0.10"),
        },
        "open_end_bond_funds": {
            "duration": Decimal("5.5"),
            "htm": Decimal("0"),
            "buffer": Decimal("0.08"),
            "runnable": Decimal("0.40"),
            "asset_base": opening.get("treasury_notes_bonds_tips", Decimal("0")) * Decimal("0.04"),
            "threshold": Decimal("0.30"),
            "slope": Decimal("0.30"),
        },
    }
    rows: list[dict[str, str]] = []
    for holder in HOLDER_STRESS_CLASSES:
        p = params[holder]
        mtm_loss = p["asset_base"] * p["duration"] * Decimal("0.03") * (Decimal("1") - p["htm"])
        buffer = p["asset_base"] * p["buffer"]
        loss_share = Decimal("0") if buffer == 0 else mtm_loss / buffer
        trigger = max(Decimal("0"), loss_share - p["threshold"])
        forced_sale = p["asset_base"] * trigger * p["slope"]
        funding_flight = p["asset_base"] * p["runnable"] * trigger * Decimal("0.15")
        credit_hook = (forced_sale + funding_flight) * (Decimal("0.35") if holder in {"banks", "dealers"} else Decimal("0.10"))
        rows.append(
            {
                "scenario_id": "stress_300bp",
                "holder_class": holder,
                "mtm_source_channel": "bond_mtm_diagnostic_linked_not_added",
                "holder_asset_base_bil": _fmt(p["asset_base"]),
                "duration_placeholder_years": _fmt(p["duration"]),
                "htm_share_low": "0.4" if holder == "banks" else _fmt(max(Decimal("0"), p["htm"] - Decimal("0.10"))),
                "htm_share_base": _fmt(p["htm"]),
                "htm_share_high": "0.6" if holder == "banks" else _fmt(min(Decimal("0.90"), p["htm"] + Decimal("0.10"))),
                "capital_or_collateral_buffer_bil": _fmt(buffer),
                "buffer_share_of_assets_low": "0.08",
                "buffer_share_of_assets_base": _fmt(p["buffer"]),
                "buffer_share_of_assets_high": "0.12",
                "runnable_share_low": "0.2",
                "runnable_share_base": _fmt(p["runnable"]),
                "runnable_share_high": "0.4",
                "mtm_loss_bil": _fmt(mtm_loss),
                "mtm_loss_share_of_buffer": _fmt(loss_share),
                "runnable_funding_metric": _fmt(p["runnable"] * loss_share),
                "stress_threshold": _fmt(p["threshold"]),
                "stress_slope": _fmt(p["slope"]),
                "forced_sale_flow_bil": _fmt(forced_sale),
                "fire_sale_price_impact_placeholder_bil": _fmt(forced_sale * Decimal("0.03")),
                "funding_flight_flow_bil": _fmt(funding_flight),
                "credit_supply_contraction_hook_bil": _fmt(credit_hook),
                "related_bond_mtm_diagnostic_D_base_bil": _fmt(bond_mtm_base),
                "mtm_overlap_key": f"holder_stress|{holder}|stress_300bp",
                "overlap_rule_key": "same_MTM_dollar_count_once_vs_bond_mtm_6C_6D_borrower_distress",
                "owner_assumption_mode": "true",
                "placeholder_flag": "OWNER_PLACEHOLDER_holder_stress_pack_pending",
                "include_flag": "0",
                "headline_entry_flag": "false",
            }
        )
    return rows


def _calibrated_holder_stress_ledger(
    pack_dir: Path,
    bond_rows: list[dict[str, str]],
    pack: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    parameters = _read_csv_rows(pack_dir / "parameters_holder_stress.csv")
    shock_rows = _read_csv_rows(pack_dir / "shock_size_profile.csv")
    anatomy = _read_csv_rows(pack_dir / "exposure_anatomy.csv")
    amplification = _read_csv_rows(pack_dir / "amplification_map.csv")
    overlap = _read_csv_rows(pack_dir / "overlap_rules.csv")
    bond_mtm_base = sum(_d(row["diagnostic_D_base_bil"]) for row in bond_rows)
    shock_start_index = _month_index_from_label("2026-01")
    derived_policy_300_yield_bp = (
        _treasury_yield_delta_bp(
            pack,
            "10y",
            "base",
            1,
            shock_start_index,
            "persistent_level",
        )
        * Decimal("3")
    )
    yield_scale = derived_policy_300_yield_bp / Decimal("300")
    fire_sale_elasticity = next(
        _d(row["base"])
        for row in amplification
        if row["parameter_id"] == "fire_sale_elasticity_bp_per_10bn"
        and row["instrument_family"] == "treasury_agency_mbs"
    )
    credit_multiplier = next(
        _d(row["base"])
        for row in amplification
        if row["parameter_id"] == "bank_credit_supply_contraction_per_capital_loss"
    )
    rows: list[dict[str, str]] = []
    for holder in ["banks", "broker_dealers", "pensions_LDI", "insurers", "open_end_bond_funds"]:
        holder_shock = [
            row for row in shock_rows if row["holder_class"] == holder and row["shock_bp"] == "300"
        ]
        scaled_holder_shock = [
            _scale_holder_stress_shock_row(row, yield_scale, parameters)
            for row in holder_shock
        ]
        metrics = "; ".join(f"{row['metric']}={row['base']}" for row in scaled_holder_shock)
        anatomy_row = next((row for row in anatomy if row["holder_class"] == holder), {})
        forced_sale = _holder_forced_sale_base(holder, scaled_holder_shock, anatomy)
        price_impact = forced_sale * fire_sale_elasticity / Decimal("10")
        credit_hook = (
            forced_sale * credit_multiplier
            if holder == "banks"
            else Decimal("0")
        )
        rows.append(
            {
                "scenario_id": "stress_300bp",
                "policy_shock_bp": "300",
                "derived_10y_yield_move_bp": _fmt(derived_policy_300_yield_bp),
                "curve_construction": "expectations_consistent_term_premium",
                "holder_class": holder,
                "mtm_source_channel": "holder_stress_pack_trigger_state_not_added",
                "holder_asset_base_bil": _first_numeric(anatomy_row.get("base", "")),
                "duration_placeholder_years": "",
                "htm_share_low": "",
                "htm_share_base": "",
                "htm_share_high": "",
                "capital_or_collateral_buffer_bil": "",
                "buffer_share_of_assets_low": "",
                "buffer_share_of_assets_base": "",
                "buffer_share_of_assets_high": "",
                "runnable_share_low": "",
                "runnable_share_base": "",
                "runnable_share_high": "",
                "mtm_loss_bil": _holder_mtm_loss_base(scaled_holder_shock),
                "mtm_loss_share_of_buffer": "",
                "runnable_funding_metric": metrics,
                "stress_threshold": "; ".join(row["trigger_status"] for row in holder_shock),
                "stress_slope": "pack_trigger_rules_verbatim",
                "forced_sale_flow_bil": _fmt(forced_sale),
                "fire_sale_price_impact_placeholder_bil": _fmt(price_impact),
                "funding_flight_flow_bil": "",
                "credit_supply_contraction_hook_bil": _fmt(credit_hook),
                "related_bond_mtm_diagnostic_D_base_bil": _fmt(bond_mtm_base),
                "mtm_overlap_key": f"holder_stress_pack|{holder}|stress_300bp",
                "overlap_rule_key": ";".join(row["rule_id"] for row in overlap),
                "owner_assumption_mode": "false",
                "placeholder_flag": "CALIBRATED_holder_stress_pack_20260702",
                "include_flag": "0",
                "headline_entry_flag": "false",
            }
        )
    return rows


def _holder_forced_sale_base(
    holder: str,
    shock_rows: list[dict[str, str]],
    anatomy_rows: list[dict[str, str]],
) -> Decimal:
    if holder == "open_end_bond_funds":
        aum = _first_decimal(
            row["base"]
            for row in anatomy_rows
            if row["holder_class"] == holder and "bond mutual funds" in row["metric"]
        )
        outflow = _first_decimal(
            row["base"]
            for row in shock_rows
            if "outflow" in row["metric"]
        ) / Decimal("100")
        buffer = Decimal("0.05")
        return max(Decimal("0"), outflow - buffer) * aum
    if holder == "pensions_LDI":
        exposure = _first_decimal(
            row["base"].split("/")[0]
            for row in anatomy_rows
            if row["holder_class"] == holder and "project Treasuries" in row["metric"]
        )
        sleeve = Decimal("0.05")
        consumed = _first_decimal(row["base"] for row in shock_rows)
        return max(Decimal("0"), consumed - Decimal("1")) * exposure * sleeve * Decimal("0.5")
    return Decimal("0")


def _scale_holder_stress_shock_row(
    row: dict[str, str],
    yield_scale: Decimal,
    parameters: list[dict[str, str]],
) -> dict[str, str]:
    scaled = dict(row)
    if row["holder_class"] == "banks" and row["metric"] == "current+incremental MTM loss / Tier1 RBC":
        current_ratio = _holder_stress_parameter(
            parameters,
            "holder_stress_ratio",
            "holder=banks|regulatory=FDIC_insured",
            "current_unrealized_loss_to_tier1",
            "base",
        )
        for band in BANDS:
            value = _d(row[band])
            scaled[band] = _fmt(current_ratio + (value - current_ratio) * yield_scale)
        return scaled
    for band in BANDS:
        try:
            value = _d(row[band])
        except Exception:
            continue
        scaled[band] = _fmt(value * yield_scale)
    return scaled


def _holder_stress_parameter(
    rows: list[dict[str, str]],
    parameter_id: str,
    cell_or_sector: str,
    instrument_family: str,
    band: str,
) -> Decimal:
    for row in rows:
        if (
            row.get("parameter_id") == parameter_id
            and row.get("cell_or_sector") == cell_or_sector
            and row.get("instrument_family") == instrument_family
        ):
            return _d(row[band])
    raise ValueError(
        "missing holder-stress parameter "
        f"{parameter_id}/{cell_or_sector}/{instrument_family}"
    )


def _holder_mtm_loss_base(shock_rows: list[dict[str, str]]) -> str:
    row = next((item for item in shock_rows if "$bn" in item["units"]), None)
    return "" if row is None else row["base"]


def _first_numeric(text: str) -> str:
    if not text:
        return ""
    return text.split("/")[0]


def _first_decimal(values: object) -> Decimal:
    for value in values:  # type: ignore[union-attr]
        text = str(value).split("/")[0]
        try:
            return _d(text)
        except Exception:
            continue
    return Decimal("0")


def _dsr_distribution_rows(distress: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    support_rows = _pack_dsr_distribution_support()
    if support_rows:
        return support_rows

    profiles = {
        (row["instrument_family"], row["transition"]): row
        for row in distress["distress_nonlinearity_profile"]
    }
    cells = _distress_cells(distress)
    rows: list[dict[str, str]] = []
    for (family, transition), _profile in sorted(profiles.items()):
        p50, _payment = _scenario_state_from_profile(profiles, family, transition, Decimal("0"))
        for cell in cells[family]:
            values = {bucket: max(Decimal("0"), p50 * multiplier) for bucket, multiplier, _share in DSR_BUCKETS}
            rows.append(
                {
                    "family": family,
                    "cell_or_sector": cell,
                    "transition": transition,
                    "p10_dsr": _fmt(values["p10"]),
                    "p25_dsr": _fmt(values["p25"]),
                    "p50_dsr": _fmt(values["p50"]),
                    "p75_dsr": _fmt(values["p75"]),
                    "p90_dsr": _fmt(values["p90"]),
                    "distribution_basis": "p50_from_current_point_value_spreads_placeholder",
                    "owner_assumption_mode": "true",
                    "placeholder_flag": "OWNER_PLACEHOLDER_D2_DSR_distribution_pending",
                    "include_flag": "0",
                    "headline_entry_flag": "false",
                }
            )
    return rows


def _pack_dsr_distribution_support() -> list[dict[str, str]]:
    path = _find_pack_file(
        Path("configs/rwtam/packs/cre_maturity_dsr_dispersion"),
        "dsr_dscr_percentile_inputs_by_cell_family.csv",
    )
    if path is None:
        return []
    grouped: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in _read_csv_rows(path):
        transition = (
            "performing_to_default"
            if "default" in row.get("threshold_parameter_id", "")
            else "performing_to_distressed"
        )
        key = (row["instrument_family"], row["rwtam_parent_cell_or_sector"], transition)
        target = grouped.setdefault(
            key,
            {
                "family": row["instrument_family"],
                "cell_or_sector": row["rwtam_parent_cell_or_sector"],
                "transition": transition,
                "distribution_basis": row.get("input_basis_label", row.get("evidence_quality", "")),
                "owner_assumption_mode": "false",
                "placeholder_flag": "CALIBRATED_D2_DSR_distribution_20260702",
                "include_flag": "0",
                "headline_entry_flag": "false",
            },
        )
        target[f"{row['percentile']}_dsr"] = row["base"]
    rows: list[dict[str, str]] = []
    for row in grouped.values():
        for bucket in ("p10", "p25", "p50", "p75", "p90"):
            row.setdefault(f"{bucket}_dsr", "")
        rows.append(row)
    return sorted(rows, key=lambda row: (row["family"], row["cell_or_sector"], row["transition"]))


def _dsr_crossing_profile(
    distress: dict[str, list[dict[str, str]]],
    distribution_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    grid_rows = _pack_dsr_crossing_profile()
    if grid_rows:
        return grid_rows

    pd_params = _pd_params(distress["distress_pd_parameters"])
    profiles = {
        (row["instrument_family"], row["transition"]): row
        for row in distress["distress_nonlinearity_profile"]
    }
    rows: list[dict[str, str]] = []
    for dist in distribution_rows:
        family = dist["family"]
        transition = dist["transition"]
        label = "P_to_X" if transition == "performing_to_distressed" else "P_to_N"
        threshold = pd_params[family][f"{transition}_dsr_threshold"]
        first_bucket = ""
        any_shock = ""
        majority_shock = ""
        p50_shock = ""
        for shock_bp in STATIC_SWEEP_SHOCKS:
            p50, _payment = _scenario_state_from_profile(profiles, family, transition, shock_bp)
            crossed_share = Decimal("0")
            shock_first_bucket = ""
            for bucket, multiplier, share in DSR_BUCKETS:
                value = p50 * multiplier
                if value >= threshold:
                    crossed_share += share
                    if not shock_first_bucket:
                        shock_first_bucket = bucket
            if shock_first_bucket and not any_shock:
                any_shock = _fmt(shock_bp)
                first_bucket = shock_first_bucket
            if p50 >= threshold and not p50_shock:
                p50_shock = _fmt(shock_bp)
            if crossed_share >= Decimal("0.50") and not majority_shock:
                majority_shock = _fmt(shock_bp)
        rows.append(
            {
                "family": family,
                "cell_or_sector": dist["cell_or_sector"],
                "transition": label,
                "threshold_dsr": _fmt(threshold),
                "baseline_share_above_threshold": "",
                "shocked_share": "",
                "incremental_share": "",
                "distribution_bucket": "placeholder_percentile_buckets",
                "first_crossing_bucket": first_bucket,
                "minimum_static_hold_shock_bp_any_bucket": any_shock,
                "minimum_static_hold_shock_bp_share_ge_50": majority_shock,
                "minimum_static_hold_shock_bp_p50": p50_shock,
                "crossing_profile": "de_synchronized_by_placeholder_distribution",
                "owner_assumption_mode": "true",
                "placeholder_flag": "OWNER_PLACEHOLDER_D2_DSR_distribution_pending",
                "include_flag": "0",
                "headline_entry_flag": "false",
            }
        )
    return rows


def _pack_dsr_crossing_profile() -> list[dict[str, str]]:
    path = _find_pack_file(
        Path("configs/rwtam/packs/cre_maturity_dsr_dispersion"),
        "distress_threshold_exceedance_share_grid.csv",
    )
    if path is None:
        return []
    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in _read_csv_rows(path):
        grouped.setdefault(
            (row["instrument_family"], row["rwtam_parent_cell_or_sector"], row["transition"]),
            [],
        ).append(row)
    rows: list[dict[str, str]] = []
    for (family, cell, transition), group in sorted(grouped.items()):
        group = sorted(group, key=lambda row: _d(row["shock_delta_metric_ratio"]))
        base_share = _d(group[0]["share_above_threshold_base_distribution"])
        any_shock = ""
        majority_shock = ""
        first_bucket = "distribution_grid"
        shocked_share = base_share
        for row in group:
            shock = _fmt(_d(row["shock_delta_metric_ratio"]) * Decimal("1000"))
            share = _d(row["share_above_threshold_base_distribution"])
            if share > base_share and not any_shock:
                any_shock = shock
                shocked_share = share
            if share >= Decimal("0.50") and not majority_shock:
                majority_shock = shock
        rows.append(
            {
                "family": family,
                "cell_or_sector": cell,
                "transition": transition,
                "threshold_dsr": group[0]["threshold_base"],
                "baseline_share_above_threshold": _fmt(base_share),
                "shocked_share": _fmt(shocked_share),
                "incremental_share": _fmt(shocked_share - base_share),
                "distribution_bucket": "percentile_bucket_grid",
                "first_crossing_bucket": first_bucket,
                "minimum_static_hold_shock_bp_any_bucket": any_shock,
                "minimum_static_hold_shock_bp_share_ge_50": majority_shock,
                "minimum_static_hold_shock_bp_p50": "",
                "crossing_profile": "threshold_exceedance_share_grid_pack",
                "owner_assumption_mode": "false",
                "placeholder_flag": "CALIBRATED_D2_DSR_distribution_20260702",
                "include_flag": "0",
                "headline_entry_flag": "false",
            }
        )
    return rows


def _episode_response_rows(pack_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    episode_dir = Path("configs/rwtam/packs/phase6_episode_elasticities")
    parameter_path = _find_pack_file(episode_dir, "episode_phase6_parameter_pack.csv")
    verdict_path = _find_pack_file(episode_dir, "episode_phase6_layer_verdicts.csv")
    if parameter_path is not None and verdict_path is not None:
        return _pack_episode_response_rows(parameter_path, verdict_path)

    phase6 = _read_csv_rows(pack_dir / "phase6" / "conversion_parameters.csv")
    sales_row = next(row for row in phase6 if row["parameter_id"] == "home_sales_lost_semielasticity_per_pp_frm")
    configs = [
        ("6A_housing_quantity", "linear_to_cap", _d(sales_row["base"]) * Decimal("5"), Decimal("0.45"), Decimal("5000")),
        ("6B_user_cost_investment", "log", Decimal("0.08"), Decimal("0.30"), Decimal("3500")),
        ("6C_wealth_valuation", "two_piece_slope", Decimal("0.06"), Decimal("0.35"), Decimal("4200")),
    ]
    config_rows: list[dict[str, str]] = []
    comparison: list[dict[str, str]] = []
    for layer_id, form, slope, cap, exposure in configs:
        config_rows.append(
            {
                "layer_id": layer_id,
                "functional_form": form,
                "linear_slope_per_pp": _fmt(slope),
                "saturation_cap_low": "0.35",
                "saturation_cap_base": _fmt(cap),
                "saturation_cap_high": "0.55",
                "owner_assumption_mode": "true",
                "placeholder_flag": "OWNER_PLACEHOLDER_D5_episode_response_form_pending",
                "include_flag": "0",
                "headline_entry_flag": "false",
            }
        )
        for shock_bp in (Decimal("300"), Decimal("500")):
            shock_pp = shock_bp / Decimal("100")
            linear_share = slope * shock_pp
            selected_share = _selected_response_share(form, linear_share, slope, shock_pp, cap)
            comparison.append(
                {
                    "layer_id": layer_id,
                    "shock_bp": _fmt(shock_bp),
                    "functional_form": form,
                    "exposure_base_bil": _fmt(exposure),
                    "linear_response_bil": _fmt(exposure * linear_share),
                    "selected_response_bil": _fmt(exposure * selected_share),
                    "selected_minus_linear_bil": _fmt(exposure * (selected_share - linear_share)),
                    "saturation_cap_base": _fmt(cap),
                    "family_label": "episode_response_placeholder_not_plus100_headline",
                    "owner_assumption_mode": "true",
                    "placeholder_flag": "OWNER_PLACEHOLDER_D5_episode_response_form_pending",
                    "include_flag": "0",
                    "headline_entry_flag": "false",
                }
            )
    return config_rows, comparison


def _pack_episode_response_rows(
    parameter_path: Path,
    verdict_path: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    params = _read_csv_rows(parameter_path)
    verdicts = _read_csv_rows(verdict_path)
    config_rows = [
        {
            "layer_id": row["layer"],
            "functional_form": row["episode_waterfall_status"],
            "linear_slope_per_pp": "",
            "saturation_cap_low": "",
            "saturation_cap_base": "",
            "saturation_cap_high": "",
            "owner_assumption_mode": "false",
            "placeholder_flag": "CALIBRATED_D5_episode_response_form_20260702",
            "include_flag": "0",
            "headline_entry_flag": "false",
        }
        for row in verdicts
    ]
    p = {row["parameter_id"]: row for row in params}
    comparison: list[dict[str, str]] = []
    for shock_bp in (Decimal("300"), Decimal("500")):
        selected_share = _piecewise_episode_housing_share(p, shock_bp)
        linear_share = _d(p["episode_housing_existing_sales_slope_0_200bp"]["base"]) * shock_bp / Decimal("100") / Decimal("-100")
        exposure = Decimal("5000")
        comparison.append(
            {
                "layer_id": "housing_quantity",
                "shock_bp": _fmt(shock_bp),
                "functional_form": "piecewise_saturating_housing_only",
                "exposure_base_bil": _fmt(exposure),
                "linear_response_bil": _fmt(exposure * linear_share),
                "selected_response_bil": _fmt(exposure * selected_share),
                "selected_minus_linear_bil": _fmt(exposure * (selected_share - linear_share)),
                "saturation_cap_base": p["episode_housing_existing_sales_decline_cap"]["base"],
                "family_label": "episode_waterfall_housing_cash_only",
                "owner_assumption_mode": "false",
                "placeholder_flag": "CALIBRATED_D5_episode_response_form_20260702",
                "include_flag": "0",
                "headline_entry_flag": "false",
            }
        )
    for verdict in verdicts:
        if verdict["layer"] == "housing_quantity":
            continue
        comparison.append(
            {
                "layer_id": verdict["layer"],
                "shock_bp": "300",
                "functional_form": verdict["episode_waterfall_status"],
                "exposure_base_bil": "0",
                "linear_response_bil": "0",
                "selected_response_bil": "0",
                "selected_minus_linear_bil": "0",
                "saturation_cap_base": "",
                "family_label": "episode_exclusion_include_flag_0",
                "owner_assumption_mode": "false",
                "placeholder_flag": "CALIBRATED_D5_episode_response_form_20260702",
                "include_flag": "0",
                "headline_entry_flag": "false",
            }
        )
    return config_rows, comparison


def _piecewise_episode_housing_share(
    params: dict[str, dict[str, str]],
    shock_bp: Decimal,
) -> Decimal:
    shock = min(shock_bp, Decimal("500"))
    segments = [
        (Decimal("200"), _d(params["episode_housing_existing_sales_slope_0_200bp"]["base"])),
        (Decimal("150"), _d(params["episode_housing_existing_sales_slope_200_350bp"]["base"])),
        (Decimal("150"), _d(params["episode_housing_existing_sales_slope_350_500bp"]["base"])),
    ]
    remaining = shock
    pct = Decimal("0")
    for width, slope in segments:
        used = min(width, remaining)
        pct += used / Decimal("100") * slope
        remaining -= used
        if remaining <= 0:
            break
    cap = abs(_d(params["episode_housing_existing_sales_decline_cap"]["base"]))
    return min(abs(pct), cap) / Decimal("100")


def _find_pack_file(root: Path, filename: str) -> Path | None:
    if not root.exists():
        return None
    matches = sorted(root.rglob(filename))
    return matches[0] if matches else None


def _selected_response_share(
    form: str,
    linear_share: Decimal,
    slope: Decimal,
    shock_pp: Decimal,
    cap: Decimal,
) -> Decimal:
    if form == "linear_to_cap":
        return min(cap, linear_share)
    if form == "log":
        return min(cap, slope * _decimal_ln(Decimal("1") + shock_pp))
    if form == "two_piece_slope":
        first = min(shock_pp, Decimal("3")) * slope
        second = max(Decimal("0"), shock_pp - Decimal("3")) * slope * Decimal("0.35")
        return min(cap, first + second)
    return linear_share


def _migration_path(pack: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    opening = _opening_by_family(pack)
    checkable = opening.get("deposits_checkable", Decimal("0"))
    conversion = _conversion(pack)
    mpc = sum(conversion.get(cell, Decimal("0")) for cell in conversion) / Decimal(len(conversion))
    cumulative = {band: Decimal("0") for band in BANDS}
    rows: list[dict[str, str]] = []
    for month_index, shock_bp in enumerate(_shock_path(SCENARIOS["stress_300bp"]), start=1):
        gap_pp = shock_bp / Decimal("100")
        row = {
            "scenario_id": "endogenous_financialization",
            "month_index": str(month_index),
            "month": _month_label(month_index),
            "shock_bp": _fmt(shock_bp),
            "rate_gap_pp": _fmt(gap_pp),
            "checkable_opening_stock_bil": _fmt(checkable),
            "owner_assumption_mode": "true",
            "placeholder_flag": "OWNER_PLACEHOLDER_2022_2024_ICI_H6_deposit_migration_pending",
            "include_flag": "0",
            "headline_entry_flag": "false",
        }
        for band in BANDS:
            params = MIGRATION_BANDS[band]
            cumulative[band] = min(
                params["cap"],
                cumulative[band] + params["elasticity"] * max(Decimal("0"), gap_pp - params["activation"]) / Decimal("12"),
            )
            migrated = checkable * cumulative[band]
            gross_income = migrated * Decimal("0.90") * (shock_bp / Decimal("10000"))
            n_effect = gross_income * mpc / Decimal("12")
            row[f"migration_share_{band}"] = _fmt(cumulative[band])
            row[f"migrated_stock_{band}_bil"] = _fmt(migrated)
            row[f"N_effect_{band}_bil"] = _fmt(n_effect)
        rows.append(row)
    return rows


def _inflation_overlay(base_v1: ScenarioResult) -> list[dict[str, str]]:
    base = [
        row for row in base_v1.rows("out_ratewall_rollup")
        if row["period_type"] == "annual"
        and row["period"] == str(START_YEAR)
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]
    base_n = _d(base["N_bil"])
    base_d = _d(base["D_bil"])
    rows: list[dict[str, str]] = []
    for shock_bp in (Decimal("100"), Decimal("300")):
        scale = shock_bp / Decimal("100")
        no_wall_drag = base_d * scale
        with_wall_drag = (base_d - base_n) * scale
        for state, slope in INFLATION_SLOPES.items():
            price_share = PRICE_SHARES[state]
            no_wall = slope * (no_wall_drag / GDP_BIL * Decimal("100"))
            with_wall = slope * (with_wall_drag / GDP_BIL * Decimal("100"))
            rows.append(
                {
                    "shock_bp": _fmt(shock_bp),
                    "slack_state": state,
                    "slope_pp_inflation_per_1pct_gdp_gap": _fmt(slope),
                    "price_share": _fmt(price_share),
                    "real_output_share": _fmt(Decimal("1") - price_share),
                    "net_demand_gap_no_wall_bil": _fmt(-no_wall_drag),
                    "net_demand_gap_with_wall_bil": _fmt(-with_wall_drag),
                    "inflation_reduction_no_wall_pp": _fmt(no_wall),
                    "inflation_reduction_with_wall_pp": _fmt(with_wall),
                    "inflation_reduction_no_wall_pp_per_100bp": _fmt(no_wall / scale),
                    "inflation_reduction_with_wall_pp_per_100bp": _fmt(with_wall / scale),
                    "wall_attenuation_pp_per_100bp": _fmt((no_wall - with_wall) / scale),
                    "owner_assumption_mode": "true",
                    "placeholder_flag": "OWNER_PLACEHOLDER_inflation_overlay_slope_pending",
                    "include_flag": "0",
                    "headline_entry_flag": "false",
                }
            )
    return rows


def _slot_map_rows() -> list[dict[str, str]]:
    return [
        {
            "mechanism": "M1_holder_stress",
            "in_flight_pack": "20260702T134556Z_holder_balance_sheet_stress_pack",
            "output_table": "out_holder_stress_ledger",
            "placeholder_row_selector": "placeholder_flag=OWNER_PLACEHOLDER_holder_stress_pack_pending",
            "replacement_mode": "value_swap_preserve_schema",
        },
        {
            "mechanism": "M2_DSR_dispersion",
            "in_flight_pack": "D2_CRE_maturity_wall_plus_DSR_distribution_pack",
            "output_table": "out_dsr_distribution_support;out_dsr_dispersion_crossing_profile",
            "placeholder_row_selector": "placeholder_flag=OWNER_PLACEHOLDER_D2_DSR_distribution_pending",
            "replacement_mode": "value_swap_preserve_schema",
        },
        {
            "mechanism": "M3_episode_response_forms",
            "in_flight_pack": "D5_episode_grade_Phase6_elasticities_pack",
            "output_table": "out_episode_response_form_config;out_episode_response_form_comparison",
            "placeholder_row_selector": "placeholder_flag=OWNER_PLACEHOLDER_D5_episode_response_form_pending",
            "replacement_mode": "value_swap_preserve_schema",
        },
        {
            "mechanism": "M4_endogenous_financialization",
            "in_flight_pack": "future_2022_2024_ICI_H6_deposit_migration_pack",
            "output_table": "out_endogenous_financialization_migration_path",
            "placeholder_row_selector": "placeholder_flag=OWNER_PLACEHOLDER_2022_2024_ICI_H6_deposit_migration_pending",
            "replacement_mode": "value_swap_preserve_schema",
        },
        {
            "mechanism": "M5_inflation_overlay",
            "in_flight_pack": "future_inflation_output_split_design",
            "output_table": "out_inflation_overlay_diagnostic",
            "placeholder_row_selector": "placeholder_flag=OWNER_PLACEHOLDER_inflation_overlay_slope_pending",
            "replacement_mode": "value_swap_preserve_schema",
        },
    ]


def _placeholder_rows(*tables: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for table_index, table in enumerate(tables, start=1):
        for row_index, row in enumerate(table, start=1):
            flag = row.get("placeholder_flag", "")
            if not flag:
                continue
            rows.append(
                {
                    "table_index": str(table_index),
                    "row_index": str(row_index),
                    "placeholder_flag": flag,
                    "owner_assumption_mode": row.get("owner_assumption_mode", "true"),
                    "include_flag": row.get("include_flag", "0"),
                    "headline_entry_flag": row.get("headline_entry_flag", "false"),
                }
            )
    return rows


def _mechanism_invariants(
    base_v1: ScenarioResult,
    holder_rows: list[dict[str, str]],
    bond_rows: list[dict[str, str]],
    placeholders: list[dict[str, str]],
) -> list[dict[str, str]]:
    base_again = build_v1(Path("configs/rwtam/packs"))
    diagnostic_rows = all(row["headline_entry_flag"] in {"false", "False", "0"} for row in placeholders)
    include_zero = all(row["include_flag"] in {"0", "false", "False"} for row in placeholders)
    overlap_errors = validate_holder_stress_overlap_rows(holder_rows, bond_rows)
    probe = [dict(holder_rows[0], mtm_overlap_key=bond_rows[0]["exposure_id"])]
    probe_errors = validate_holder_stress_overlap_rows(probe, bond_rows)
    headline_unchanged = base_v1.rows("out_ratewall_rollup") == base_again.rows("out_ratewall_rollup")
    return [
        _check("T55_mechanism_outputs_isolated", diagnostic_rows and include_zero, "all mechanism rows are diagnostic/scenario-only with include_flag=0"),
        _check("T45_base_headline_byte_unchanged", headline_unchanged, "mechanism wave does not mutate default V1 headline"),
        _check("M1_holder_mtm_overlap_actual_rows", not overlap_errors, ";".join(overlap_errors) or "holder stress uses distinct overlap keys"),
        _check("M1_holder_mtm_overlap_probe_fails", bool(probe_errors), ";".join(probe_errors) or "probe did not fail"),
    ]


def _check(check_id: str, ok: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": "pass" if ok else "fail", "message": message}


def _pd_params(rows: list[dict[str, str]]) -> dict[str, dict[str, Decimal]]:
    out: dict[str, dict[str, Decimal]] = {}
    for row in rows:
        out.setdefault(row["instrument_family"], {})[row["parameter_id"]] = _d(row["base"])
    return out


def _distress_cells(distress: dict[str, list[dict[str, str]]]) -> dict[str, list[str]]:
    out: dict[str, set[str]] = {}
    for row in distress["distress_pd_parameters"]:
        out.setdefault(row["instrument_family"], set())
        for cell in row["cell_or_sector"].split(";"):
            out[row["instrument_family"]].add(cell)
    return {family: sorted(cells) for family, cells in out.items()}


def _month_label(month_index: int) -> str:
    month = ((month_index - 1) % 12) + 1
    year = START_YEAR + (month_index - 1) // 12
    return f"{year}-{month:02d}"


def _decimal_ln(value: Decimal) -> Decimal:
    return Decimal(str(float(value).real)).ln()
