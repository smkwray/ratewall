"""Scenario-only Fed P&L and deferred-asset dynamics for RWTAM."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtam.v1 import (
    BANDS,
    DOSE_MODES,
    MONTHS,
    _d,
    _effective_pack,
    _fmt,
    _load_pack,
    _month_label,
    _month_index_from_label,
    _monthly_records,
    _opening_by_family,
    _qt_runoff_bil,
    _read_csv_rows,
    _ricardian_offsets,
    _ricardian_suffix,
    _shock_multiplier,
    _treasury_yield_delta,
    _write_rows,
    build_v1,
)


EXPERIMENT_ID = "rwtam_fed_pnl_dynamic_20260705"
OUTPUT_DIR = Path("var/rwtam/scenarios/fed_pnl_dynamic")
REPORT_PATH = Path("do/rwtam_fed_pnl_fix_report_20260705.md")
TREASURY_FUNDED_REPORT_PATH = Path("do/rwtam_treasury_funded_report_20260705.md")

OWNER_SOURCE_ID = "H41_FRED_20260701_OWNER_SUPPLIED"
BACKCAST_OWNER_SOURCE_ID = "FRED_QAVG_20260705_OWNER_SUPPLIED"
GOVERNMENT_REVENUE_DOCTRINE = (
    "private_counterpart_plus_financing_closure; "
    "intra_government_transfers_zero_direct_demand_weight; "
    "deficit_effects_via_issuance_loop"
)
GOVERNMENT_REVENUE_DOCTRINE_LINEAGE = "public_revenue_closure_rule_20260705"
OPENING_DEFERRED_ASSET_BASE_BIL = Decimal("235.615")
PLACEHOLDER_HALF_SPREAD_BIL = Decimal("190")
SOMA_TREASURY_BIL = Decimal("4492.235")
SOMA_MBS_BIL = Decimal("1948.398")
BASELINE_PAYDOWN_PACE_BIL_PER_WEEK = Decimal("0.6")
BACKCAST_OWNER_YIELD_BANDS = {
    "low": Decimal("0.020"),
    "base": Decimal("0.0215"),
    "high": Decimal("0.023"),
}
BACKCAST_QUARTERLY_AVERAGES = {
    "2022Q1": {
        "soma_treasury_bil": Decimal("5728.9"),
        "soma_mbs_bil": Decimal("2683.8"),
        "reserves_bil": Decimal("3853.1"),
        "on_rrp_bil": Decimal("1600"),
    },
    "2022Q2": {
        "soma_treasury_bil": Decimal("5765.5"),
        "soma_mbs_bil": Decimal("2719.5"),
        "reserves_bil": Decimal("3393.2"),
        "on_rrp_bil": Decimal("2000"),
    },
    "2022Q3": {
        "soma_treasury_bil": Decimal("5708.9"),
        "soma_mbs_bil": Decimal("2715.5"),
        "reserves_bil": Decimal("3238.5"),
        "on_rrp_bil": Decimal("2200"),
    },
    "2022Q4": {
        "soma_treasury_bil": Decimal("5557.8"),
        "soma_mbs_bil": Decimal("2673.1"),
        "reserves_bil": Decimal("3098.3"),
        "on_rrp_bil": Decimal("2200"),
    },
    "2023Q1": {
        "soma_treasury_bil": Decimal("5382.2"),
        "soma_mbs_bil": Decimal("2620.7"),
        "reserves_bil": Decimal("3101.0"),
        "on_rrp_bil": Decimal("2100"),
    },
    "2023Q2": {
        "soma_treasury_bil": Decimal("5208.0"),
        "soma_mbs_bil": Decimal("2570.8"),
        "reserves_bil": Decimal("3256.0"),
        "on_rrp_bil": Decimal("2200"),
    },
    "2023Q3": {
        "soma_treasury_bil": Decimal("5029.3"),
        "soma_mbs_bil": Decimal("2513.0"),
        "reserves_bil": Decimal("3216.3"),
        "on_rrp_bil": Decimal("1700"),
    },
    "2023Q4": {
        "soma_treasury_bil": Decimal("4858.8"),
        "soma_mbs_bil": Decimal("2459.0"),
        "reserves_bil": Decimal("3382.3"),
        "on_rrp_bil": Decimal("1000"),
    },
    "2024Q1": {
        "soma_treasury_bil": Decimal("4680.8"),
        "soma_mbs_bil": Decimal("2414.4"),
        "reserves_bil": Decimal("3538.5"),
        "on_rrp_bil": Decimal("500"),
    },
    "2024Q2": {
        "soma_treasury_bil": Decimal("4504.8"),
        "soma_mbs_bil": Decimal("2368.4"),
        "reserves_bil": Decimal("3400.2"),
        "on_rrp_bil": Decimal("400"),
    },
    "2024Q3": {
        "soma_treasury_bil": Decimal("4408.3"),
        "soma_mbs_bil": Decimal("2314.6"),
        "reserves_bil": Decimal("3297.9"),
        "on_rrp_bil": Decimal("400"),
    },
    "2024Q4": {
        "soma_treasury_bil": Decimal("4336.7"),
        "soma_mbs_bil": Decimal("2263.6"),
        "reserves_bil": Decimal("3231.1"),
        "on_rrp_bil": Decimal("200"),
    },
}
OPS_COST_ANNUAL_BANDS = {
    "low": Decimal("7"),
    "base": Decimal("9"),
    "high": Decimal("11"),
}
CAVEAT = (
    "MBS prepayment behavior is not modeled beyond the runoff dial; no "
    "mark-to-market is included. This is income accounting, matching the Fed "
    "remittance basis."
)
TREASURY_FUNDED_SET_DATE = "2026-01"
TREASURY_FUNDED_DEFAULT_OPENING_DA_BIL = Decimal("0")
OVERDRAFT_INDEMNITY_MEMO = (
    "Counterfactual only: funded regime financed by central-bank money, so there is "
    "no marketable-issuance loop for the funded flow; the residual delta versus "
    "self-cure is the negative of self-cure's own issuance-loop effect. The US has "
    "no Treasury overdraft authority at the Fed; direct-purchase authority lapsed "
    "in 1981. Reserves/IORB second-round effects are out of perimeter."
)


@dataclass(frozen=True)
class FedPnlResult:
    """CSV-ready Fed P&L scenario tables."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


@dataclass(frozen=True)
class _PathState:
    deferred_asset_bil: Decimal


def build_fed_pnl_dynamic_experiment(
    pack_dir: Path = Path("configs/rwtam/packs"),
    backcast_dir: Path = Path("do/backcast"),
    *,
    output_root: Path = OUTPUT_DIR,
    shock_size_bp: Decimal = Decimal("100"),
) -> FedPnlResult:
    """Build default-OFF static-gate versus dynamic Fed P&L scenario rows."""

    with localcontext() as context:
        context.prec = 28
        output_root.mkdir(parents=True, exist_ok=True)
        base_pack = _effective_pack(
            _load_pack(pack_dir),
            include_scenario_adjustments=True,
            include_tdc_settlement=True,
        )
        paths: dict[tuple[str, str], list[dict[str, Decimal | str]]] = {}
        funded_paths: dict[tuple[str, str], list[dict[str, Decimal | str]]] = {}
        monthly_off: dict[tuple[str, str], list[dict[str, Decimal | str]]] = {}
        monthly_loop_on: dict[tuple[str, str], list[dict[str, Decimal | str]]] = {}
        funded_monthly_loop_on: dict[tuple[str, str], list[dict[str, Decimal | str]]] = {}
        builds = {}
        for dose_mode in DOSE_MODES:
            builds[dose_mode] = build_v1(
                pack_dir,
                dose_mode=dose_mode,
                shock_size_bp=shock_size_bp,
                include_impulse_beta_comparator=False,
            )
            records = _monthly_records(
                base_pack,
                include_tdc_settlement=True,
                shock_start_month="2026-01",
                dose_mode=dose_mode,
                include_tax_layer=True,
                shock_size_bp=shock_size_bp,
            )
            for band in BANDS:
                monthly_off[(band, dose_mode)] = [
                    row
                    for row in records
                    if row["band"] == band
                ]
                paths[(band, dose_mode)] = simulate_forward_paired_path(
                    base_pack,
                    band=band,
                    dose_mode=dose_mode,
                    shock_size_bp=shock_size_bp,
                )
                funded_paths[(band, dose_mode)] = simulate_treasury_funded_paired_path(
                    base_pack,
                    band=band,
                    dose_mode=dose_mode,
                    shock_size_bp=shock_size_bp,
                )
            loop_inputs = _issuance_loop_inputs_from_paths(paths, dose_mode)
            loop_records = _monthly_records(
                base_pack,
                include_tdc_settlement=True,
                shock_start_month="2026-01",
                dose_mode=dose_mode,
                include_tax_layer=True,
                shock_size_bp=shock_size_bp,
                issuance_loop_extra_public_net_by_month=loop_inputs,
            )
            for band in BANDS:
                monthly_loop_on[(band, dose_mode)] = [
                    row for row in loop_records if row["band"] == band
                ]
            funded_loop_inputs = _issuance_loop_inputs_from_paths(funded_paths, dose_mode)
            funded_loop_records = _monthly_records(
                base_pack,
                include_tdc_settlement=True,
                shock_start_month="2026-01",
                dose_mode=dose_mode,
                include_tax_layer=True,
                shock_size_bp=shock_size_bp,
                issuance_loop_extra_public_net_by_month=funded_loop_inputs,
            )
            for band in BANDS:
                funded_monthly_loop_on[(band, dose_mode)] = [
                    row for row in funded_loop_records if row["band"] == band
                ]

        rows = _experiment_rows(builds, monthly_off, monthly_loop_on, paths)
        funding_regime_rows = _funding_regime_rows(
            builds,
            monthly_off,
            monthly_loop_on,
            funded_monthly_loop_on,
            paths,
            funded_paths,
        )
        funding_invariants = _funding_regime_invariant_rows(funding_regime_rows)
        backcast_monthly, backcast_scores = build_backcast_fed_pnl_tables(
            pack_dir=pack_dir,
            backcast_dir=backcast_dir,
        )
        structural_rows = _structural_non_identifiability_rows(rows, paths)
        tables = {
            "out_fed_pnl_dynamic": rows + structural_rows + backcast_scores + _lineage_rows() + _caveat_rows(),
            "out_fed_pnl_dynamic_monthly_path": _stringify_rows(
                row
                for rows_for_path in paths.values()
                for row in rows_for_path
            ),
            "out_fed_pnl_backcast_monthly": backcast_monthly,
            "out_fed_pnl_invariant_check": _invariant_rows(rows, paths),
            "out_fed_pnl_funding_regime_delta": funding_regime_rows,
            "out_fed_pnl_funding_regime_monthly_path": _funding_regime_monthly_rows(
                paths,
                funded_paths,
            ),
            "out_fed_pnl_funding_regime_invariant_check": funding_invariants,
        }
        return FedPnlResult(tables=tables)


def write_fed_pnl_outputs(
    result: FedPnlResult,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def simulate_forward_paired_path(
    pack: dict[str, list[dict[str, str]]],
    *,
    band: str,
    dose_mode: str,
    shock_size_bp: Decimal = Decimal("100"),
    opening_deferred_asset_bil: Decimal | None = None,
) -> list[dict[str, Decimal | str]]:
    """Simulate paired baseline/shocked Fed P&L paths for one band and dose."""

    opening = _opening_by_family(pack)
    avg_yield = _assumption(pack, "soma_avg_yield", band)
    deferred_open = (
        opening_deferred_asset_bil
        if opening_deferred_asset_bil is not None
        else _opening_deferred_asset_band(band)
    )
    runoff_annual = _qt_runoff_bil(pack, band)
    runoff_monthly = runoff_annual / Decimal("12")
    baseline_positive_income_monthly = (
        BASELINE_PAYDOWN_PACE_BIL_PER_WEEK * Decimal("52") / Decimal("12")
    )
    soma_total = SOMA_TREASURY_BIL + SOMA_MBS_BIL
    baseline_soma_income_monthly = soma_total * avg_yield / Decimal("12")
    implied_baseline_expense_monthly = (
        baseline_soma_income_monthly
        - OPS_COST_ANNUAL_BANDS[band] / Decimal("12")
        - baseline_positive_income_monthly
    )
    baseline = _PathState(deferred_asset_bil=deferred_open)
    shocked = _PathState(deferred_asset_bil=deferred_open)
    shock_start_index = _month_index_from_label("2026-01")
    repriced_stock = Decimal("0")
    rows: list[dict[str, Decimal | str]] = []
    for month_index in range(1, MONTHS + 1):
        month = _month_label(month_index)
        shock_multiplier = _shock_multiplier(month_index, shock_start_index, dose_mode)
        shock_scale = shock_size_bp / Decimal("100")
        expense_delta = (
            opening["reserves_iorb"]
            + opening["on_rrp_mmfs"]
            + opening["foreign_official_reverse_repos"]
        ) * Decimal("0.01") * shock_multiplier * shock_scale / Decimal("12")
        curve_delta = _treasury_yield_delta(
            pack,
            "10y",
            band,
            month_index,
            shock_start_index,
            dose_mode,
            shock_size_bp=shock_size_bp,
        )
        repriced_stock = min(soma_total, repriced_stock + runoff_monthly)
        soma_income_delta = repriced_stock * curve_delta / Decimal("12")
        baseline_step = _advance_deferred_asset(
            baseline.deferred_asset_bil,
            baseline_positive_income_monthly,
        )
        shocked_step = _advance_deferred_asset(
            shocked.deferred_asset_bil,
            baseline_positive_income_monthly + soma_income_delta - expense_delta,
        )
        baseline = _PathState(deferred_asset_bil=baseline_step["deferred_asset_end_bil"])
        shocked = _PathState(deferred_asset_bil=shocked_step["deferred_asset_end_bil"])
        rows.append(
            {
                "experiment_id": EXPERIMENT_ID,
                "row_type": "monthly_forward_path",
                "month_index": Decimal(month_index),
                "month": month,
                "year": month[:4],
                "band": band,
                "dose_mode": dose_mode,
                "shock_size_bp": shock_size_bp,
                "opening_deferred_asset_bil": deferred_open,
                "soma_treasury_open_bil": SOMA_TREASURY_BIL,
                "soma_mbs_open_bil": SOMA_MBS_BIL,
                "soma_avg_yield": avg_yield,
                "ops_cost_annual_bil": OPS_COST_ANNUAL_BANDS[band],
                "baseline_soma_income_bil": baseline_soma_income_monthly,
                "implied_baseline_expense_bil": implied_baseline_expense_monthly,
                "baseline_net_income_bil": baseline_step["net_income_bil"],
                "baseline_deferred_asset_begin_bil": baseline_step["deferred_asset_begin_bil"],
                "baseline_paydown_bil": baseline_step["paydown_bil"],
                "baseline_loss_addition_bil": baseline_step["loss_addition_bil"],
                "baseline_remittance_bil": baseline_step["remittance_bil"],
                "baseline_deferred_asset_end_bil": baseline_step["deferred_asset_end_bil"],
                "shocked_expense_delta_bil": expense_delta,
                "shocked_soma_income_delta_bil": soma_income_delta,
                "shocked_net_income_bil": shocked_step["net_income_bil"],
                "shocked_deferred_asset_begin_bil": shocked_step["deferred_asset_begin_bil"],
                "shocked_paydown_bil": shocked_step["paydown_bil"],
                "shocked_loss_addition_bil": shocked_step["loss_addition_bil"],
                "shocked_remittance_bil": shocked_step["remittance_bil"],
                "shocked_deferred_asset_end_bil": shocked_step["deferred_asset_end_bil"],
                "dynamic_remittance_delta_bil": (
                    shocked_step["remittance_bil"] - baseline_step["remittance_bil"]
                ),
                "public_effect_bil": (
                    shocked_step["remittance_bil"] - baseline_step["remittance_bil"]
                ),
                "repriced_soma_stock_bil": repriced_stock,
                "qt_runoff_annual_bil": runoff_annual,
                "lineage": OWNER_SOURCE_ID,
            }
        )
    return rows


def simulate_treasury_funded_paired_path(
    pack: dict[str, list[dict[str, str]]],
    *,
    band: str,
    dose_mode: str,
    shock_size_bp: Decimal = Decimal("100"),
    opening_deferred_asset_bil: Decimal = TREASURY_FUNDED_DEFAULT_OPENING_DA_BIL,
) -> list[dict[str, Decimal | str]]:
    """Simulate paired paths where Treasury covers Fed losses as cash transfers."""

    opening = _opening_by_family(pack)
    avg_yield = _assumption(pack, "soma_avg_yield", band)
    runoff_annual = _qt_runoff_bil(pack, band)
    runoff_monthly = runoff_annual / Decimal("12")
    baseline_positive_income_monthly = (
        BASELINE_PAYDOWN_PACE_BIL_PER_WEEK * Decimal("52") / Decimal("12")
    )
    soma_total = SOMA_TREASURY_BIL + SOMA_MBS_BIL
    baseline_soma_income_monthly = soma_total * avg_yield / Decimal("12")
    implied_baseline_expense_monthly = (
        baseline_soma_income_monthly
        - OPS_COST_ANNUAL_BANDS[band] / Decimal("12")
        - baseline_positive_income_monthly
    )
    shock_start_index = _month_index_from_label(TREASURY_FUNDED_SET_DATE)
    repriced_stock = Decimal("0")
    rows: list[dict[str, Decimal | str]] = []
    for month_index in range(1, MONTHS + 1):
        month = _month_label(month_index)
        shock_multiplier = _shock_multiplier(month_index, shock_start_index, dose_mode)
        shock_scale = shock_size_bp / Decimal("100")
        expense_delta = (
            opening["reserves_iorb"]
            + opening["on_rrp_mmfs"]
            + opening["foreign_official_reverse_repos"]
        ) * Decimal("0.01") * shock_multiplier * shock_scale / Decimal("12")
        curve_delta = _treasury_yield_delta(
            pack,
            "10y",
            band,
            month_index,
            shock_start_index,
            dose_mode,
            shock_size_bp=shock_size_bp,
        )
        repriced_stock = min(soma_total, repriced_stock + runoff_monthly)
        soma_income_delta = repriced_stock * curve_delta / Decimal("12")
        baseline_step = _advance_treasury_funded(
            baseline_positive_income_monthly,
            opening_deferred_asset_bil if month_index == 1 else Decimal("0"),
        )
        shocked_step = _advance_treasury_funded(
            baseline_positive_income_monthly + soma_income_delta - expense_delta,
            opening_deferred_asset_bil if month_index == 1 else Decimal("0"),
        )
        baseline_flow = (
            baseline_step["remittance_bil"] - baseline_step["treasury_transfer_paid_bil"]
        )
        shocked_flow = (
            shocked_step["remittance_bil"] - shocked_step["treasury_transfer_paid_bil"]
        )
        rows.append(
            {
                "experiment_id": EXPERIMENT_ID,
                "row_type": "monthly_forward_path",
                "funding_regime": "treasury_funded",
                "financing_mode": "marketable_issuance",
                "month_index": Decimal(month_index),
                "month": month,
                "year": month[:4],
                "band": band,
                "dose_mode": dose_mode,
                "shock_size_bp": shock_size_bp,
                "opening_deferred_asset_bil": opening_deferred_asset_bil,
                "opening_da_settlement_bil": opening_deferred_asset_bil if month_index == 1 else Decimal("0"),
                "soma_treasury_open_bil": SOMA_TREASURY_BIL,
                "soma_mbs_open_bil": SOMA_MBS_BIL,
                "soma_avg_yield": avg_yield,
                "ops_cost_annual_bil": OPS_COST_ANNUAL_BANDS[band],
                "baseline_soma_income_bil": baseline_soma_income_monthly,
                "implied_baseline_expense_bil": implied_baseline_expense_monthly,
                "baseline_net_income_bil": baseline_step["net_income_bil"],
                "baseline_deferred_asset_begin_bil": Decimal("0"),
                "baseline_paydown_bil": Decimal("0"),
                "baseline_loss_addition_bil": Decimal("0"),
                "baseline_remittance_bil": baseline_step["remittance_bil"],
                "baseline_treasury_transfer_paid_bil": baseline_step["treasury_transfer_paid_bil"],
                "baseline_public_fiscal_flow_bil": baseline_flow,
                "baseline_deferred_asset_end_bil": Decimal("0"),
                "shocked_expense_delta_bil": expense_delta,
                "shocked_soma_income_delta_bil": soma_income_delta,
                "shocked_net_income_bil": shocked_step["net_income_bil"],
                "shocked_deferred_asset_begin_bil": Decimal("0"),
                "shocked_paydown_bil": Decimal("0"),
                "shocked_loss_addition_bil": Decimal("0"),
                "shocked_remittance_bil": shocked_step["remittance_bil"],
                "shocked_treasury_transfer_paid_bil": shocked_step["treasury_transfer_paid_bil"],
                "shocked_public_fiscal_flow_bil": shocked_flow,
                "shocked_deferred_asset_end_bil": Decimal("0"),
                "dynamic_remittance_delta_bil": (
                    shocked_step["remittance_bil"] - baseline_step["remittance_bil"]
                ),
                "treasury_transfer_delta_bil": (
                    shocked_step["treasury_transfer_paid_bil"]
                    - baseline_step["treasury_transfer_paid_bil"]
                ),
                "public_effect_bil": shocked_flow - baseline_flow,
                "repriced_soma_stock_bil": repriced_stock,
                "qt_runoff_annual_bil": runoff_annual,
                "lineage": OWNER_SOURCE_ID,
            }
        )
    return rows


def build_backcast_fed_pnl_tables(
    *,
    pack_dir: Path = Path("configs/rwtam/packs"),
    backcast_dir: Path = Path("do/backcast"),
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    pack = _effective_pack(
        _load_pack(pack_dir),
        include_scenario_adjustments=False,
        include_tdc_settlement=True,
    )
    state_rows = _read_csv_rows(backcast_dir / "historical_opening_state_2022Q1.csv")
    rate_rows = [
        row
        for row in _read_csv_rows(backcast_dir / "historical_rate_paths.csv")
        if "2022-01" <= row["month"] <= "2024-12"
    ]
    monthly = simulate_backcast_actual_path(
        pack
        | {
            "opening_stocks": state_rows,
            "realized_flow_targets": _read_csv_rows(backcast_dir / "realized_flow_targets.csv"),
        },
        rate_rows,
    )
    targets = _read_csv_rows(backcast_dir / "fed_remittances_deferred_path.csv")
    scores = _backcast_score_rows(monthly, targets)
    return _stringify_rows(monthly), scores


def simulate_backcast_actual_path(
    pack: dict[str, list[dict[str, str]]],
    rate_rows: list[dict[str, str]],
    *,
    band: str = "base",
    opening_deferred_asset_bil: Decimal = Decimal("0"),
) -> list[dict[str, Decimal | str]]:
    avg_yield, yield_source = _backcast_soma_avg_yield(pack, band)
    initial_10y = _d(rate_rows[0]["treasury_note_10yr_rate_pct"]) / Decimal("100")
    repriced_stock = Decimal("0")
    state = _PathState(deferred_asset_bil=opening_deferred_asset_bil)
    rows: list[dict[str, Decimal | str]] = []
    for month_index, row in enumerate(rate_rows, start=1):
        balance = _backcast_balance_for_month(row["month"])
        soma_treasury = balance["soma_treasury_bil"]
        soma_mbs = balance["soma_mbs_bil"]
        soma_total = soma_treasury + soma_mbs
        iorb_rate = _d(row["iorb_rate_pct"]) / Decimal("100")
        fed_rate = _d(row["fed_funds_rate_pct"]) / Decimal("100")
        ten_year = _d(row["treasury_note_10yr_rate_pct"]) / Decimal("100")
        repriced_stock = min(soma_total, repriced_stock + _qt_runoff_bil(pack, band) / Decimal("12"))
        income = (
            soma_total * avg_yield / Decimal("12")
            + repriced_stock * (ten_year - initial_10y) / Decimal("12")
        )
        expense = (
            balance["reserves_bil"] * iorb_rate
            + balance["on_rrp_bil"] * fed_rate
        ) / Decimal("12")
        net_income = income - expense - OPS_COST_ANNUAL_BANDS[band] / Decimal("12")
        step = _advance_deferred_asset(state.deferred_asset_bil, net_income)
        state = _PathState(deferred_asset_bil=step["deferred_asset_end_bil"])
        deferred_change = (
            step["deferred_asset_end_bil"] - step["deferred_asset_begin_bil"]
        )
        rows.append(
            {
                "experiment_id": EXPERIMENT_ID,
                "row_type": "monthly_backcast_path",
                "month_index": Decimal(month_index),
                "month": row["month"],
                "year": row["month"][:4],
                "quarter_source": row.get("quarter_source", _quarter_from_month(row["month"])),
                "soma_treasury_open_bil": soma_treasury,
                "soma_mbs_open_bil": soma_mbs,
                "reserves_open_bil": balance["reserves_bil"],
                "on_rrp_open_bil": balance["on_rrp_bil"],
                "soma_avg_yield": avg_yield,
                "soma_yield_source": yield_source,
                "soma_income_bil": income,
                "fed_interest_expense_bil": expense,
                "ops_cost_bil": OPS_COST_ANNUAL_BANDS[band] / Decimal("12"),
                "net_income_bil": net_income,
                "deferred_asset_begin_bil": step["deferred_asset_begin_bil"],
                "deferred_asset_end_bil": step["deferred_asset_end_bil"],
                "deferred_asset_change_bil": deferred_change,
                "paydown_bil": step["paydown_bil"],
                "loss_addition_bil": step["loss_addition_bil"],
                "cash_remittance_bil": step["remittance_bil"],
                "public_cost_deferred_minus_cash_remit_bil": (
                    deferred_change - step["remittance_bil"]
                ),
                "no_fit_policy": "no_coefficients_or_mixes_adjusted_to_targets",
                "lineage": (
                    "do/backcast/historical_rate_paths.csv;"
                    f"{BACKCAST_OWNER_SOURCE_ID};monthly_quarter_average_interpolation"
                ),
            }
        )
    return rows


def _advance_deferred_asset(
    deferred_asset_begin_bil: Decimal,
    net_income_bil: Decimal,
) -> dict[str, Decimal]:
    positive_income = max(Decimal("0"), net_income_bil)
    paydown = min(deferred_asset_begin_bil, positive_income)
    remittance = positive_income - paydown
    loss = max(Decimal("0"), -net_income_bil)
    deferred_asset_end = max(Decimal("0"), deferred_asset_begin_bil - paydown) + loss
    return {
        "deferred_asset_begin_bil": deferred_asset_begin_bil,
        "net_income_bil": net_income_bil,
        "paydown_bil": paydown,
        "remittance_bil": remittance,
        "loss_addition_bil": loss,
        "deferred_asset_end_bil": deferred_asset_end,
    }


def _advance_treasury_funded(
    net_income_bil: Decimal,
    opening_da_settlement_bil: Decimal,
) -> dict[str, Decimal]:
    loss_transfer = max(Decimal("0"), -net_income_bil)
    remittance = max(Decimal("0"), net_income_bil)
    return {
        "net_income_bil": net_income_bil,
        "remittance_bil": remittance,
        "treasury_transfer_paid_bil": loss_transfer + opening_da_settlement_bil,
    }


def _experiment_rows(
    builds: dict[str, object],
    monthly_off: dict[tuple[str, str], list[dict[str, Decimal | str]]],
    monthly_loop_on: dict[tuple[str, str], list[dict[str, Decimal | str]]],
    paths: dict[tuple[str, str], list[dict[str, Decimal | str]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    ricardian_offsets = _ricardian_offsets(
        _effective_pack(_load_pack(Path("configs/rwtam/packs")), True, True)
    )
    for dose_mode in DOSE_MODES:
        for band in BANDS:
            path = paths[(band, dose_mode)]
            annual_effect = _annual_public_effects(path)
            for horizon_id, period_type, period in (
                ("year1_2026", "annual", "2026"),
                ("persistent_120m", "cumulative_120_month", "2026-2035"),
            ):
                if horizon_id == "persistent_120m" and dose_mode != "persistent_level":
                    continue
                effect = sum(
                    annual_effect[year]
                    for year in annual_effect
                    if horizon_id != "year1_2026" or year == "2026"
                )
                issuance_loop_input = -effect
                public_effect_by_ricardian: dict[Decimal, dict[str, Decimal]] = {}
                for ricardian in ricardian_offsets:
                    off_n, off_d = _rollup_nd(builds[dose_mode], band, horizon_id, ricardian)
                    loop_delta_n, loop_delta_d = _horizon_delta_for_ricardian(
                        monthly_off[(band, dose_mode)],
                        monthly_loop_on[(band, dose_mode)],
                        horizon_id,
                        ricardian,
                    )
                    loop_n = off_n + loop_delta_n
                    loop_d = off_d + loop_delta_d
                    converted_effect = effect * ricardian
                    effect_n = max(Decimal("0"), converted_effect)
                    effect_d = max(Decimal("0"), -converted_effect)
                    on_n = loop_n + effect_n
                    on_d = loop_d + effect_d
                    off_rw = Decimal("0") if off_d == 0 else off_n / off_d
                    on_rw = Decimal("0") if on_d == 0 else on_n / on_d
                    public_effect_by_ricardian[ricardian] = {
                        "off_n": off_n,
                        "off_d": off_d,
                        "loop_n": loop_n,
                        "loop_d": loop_d,
                        "on_n": on_n,
                        "on_d": on_d,
                        "off_rw": off_rw,
                        "on_rw": on_rw,
                        "delta_rw": on_rw - off_rw,
                        "loop_delta_n": loop_n - off_n,
                        "loop_delta_d": loop_d - off_d,
                        "converted_effect": converted_effect,
                    }
                timing = _independent_timing_effect(path, horizon_id)
                assertion_pass = abs(effect - timing) <= Decimal("0.000001")
                headline = public_effect_by_ricardian[Decimal("0")]
                ricardian_columns = {}
                for ricardian, values in sorted(public_effect_by_ricardian.items()):
                    suffix = _ricardian_suffix(ricardian)
                    ricardian_columns[f"ricardian_{suffix}_off_RW"] = _fmt(values["off_rw"])
                    ricardian_columns[f"ricardian_{suffix}_on_RW"] = _fmt(values["on_rw"])
                    ricardian_columns[f"ricardian_{suffix}_delta_RW"] = _fmt(values["delta_rw"])
                    ricardian_columns[f"ricardian_{suffix}_converted_public_effect_bil"] = _fmt(
                        values["converted_effect"]
                    )
                    ricardian_columns[
                        f"public_budget_anticipation_sensitivity_{suffix}_off_RW"
                    ] = _fmt(values["off_rw"])
                    ricardian_columns[
                        f"public_budget_anticipation_sensitivity_{suffix}_on_RW"
                    ] = _fmt(values["on_rw"])
                    ricardian_columns[
                        f"public_budget_anticipation_sensitivity_{suffix}_delta_RW"
                    ] = _fmt(values["delta_rw"])
                    ricardian_columns[
                        f"public_budget_anticipation_sensitivity_{suffix}_converted_public_effect_bil"
                    ] = _fmt(values["converted_effect"])
                rows.append(
                    _base_output_row(
                        row_type="delta_rw",
                        band=band,
                        dose_mode=dose_mode,
                        horizon_id=horizon_id,
                        period_type=period_type,
                        period=period,
                    )
                    | {
                        "ricardian_offset": "0",
                        "off_RW_ratio": _fmt(headline["off_rw"]),
                        "on_RW_ratio": _fmt(headline["on_rw"]),
                        "delta_RW_ratio": _fmt(headline["delta_rw"]),
                        "off_N_bil": _fmt(headline["off_n"]),
                        "off_D_bil": _fmt(headline["off_d"]),
                        "on_N_bil": _fmt(headline["on_n"]),
                        "on_D_bil": _fmt(headline["on_d"]),
                        "dynamic_public_effect_bil": _fmt(effect),
                        "issuance_loop_input_bil": _fmt(issuance_loop_input),
                        "issuance_loop_delta_N_bil": _fmt(headline["loop_delta_n"]),
                        "issuance_loop_delta_D_bil": _fmt(headline["loop_delta_d"]),
                        "loop_on_N_bil": _fmt(headline["loop_n"]),
                        "loop_on_D_bil": _fmt(headline["loop_d"]),
                        "converted_public_effect_bil": _fmt(headline["converted_effect"]),
                        "resumption_timing_effect_bil": _fmt(timing),
                        "decomposition_disposition": (
                            "timing_assertion_pass_independent_monthly_path"
                            if assertion_pass
                            else "timing_assertion_fail_independent_monthly_path"
                        ),
                        "baseline_resumption_month": _resumption_month(path, "baseline"),
                        "shocked_resumption_month": _resumption_month(path, "shocked"),
                        "value_assertion": "pass" if assertion_pass else "fail",
                        "public_budget_anticipation_sensitivity": "0",
                        "government_revenue_doctrine": GOVERNMENT_REVENUE_DOCTRINE,
                        "doctrine_lineage": GOVERNMENT_REVENUE_DOCTRINE_LINEAGE,
                    }
                    | ricardian_columns
                )
            for year, effect in annual_effect.items():
                static = _annual_static_remittance(monthly_off[(band, dose_mode)], year)
                rows.append(
                    _base_output_row(
                        row_type="annual_remittance_delta_path",
                        band=band,
                        dose_mode=dose_mode,
                        horizon_id=f"annual_{year}",
                        period_type="annual",
                        period=year,
                    )
                    | {
                        "static_gate_off_remittance_delta_bil": _fmt(static),
                        "dynamic_on_remittance_delta_bil": _fmt(effect),
                        "issuance_loop_input_bil": _fmt(-effect),
                        "government_revenue_doctrine": GOVERNMENT_REVENUE_DOCTRINE,
                        "doctrine_lineage": GOVERNMENT_REVENUE_DOCTRINE_LINEAGE,
                        "decomposition_disposition": "annual_path_context_not_delta_rw_row",
                        "baseline_deferred_asset_eoy_bil": _fmt(
                            _last_year_value(path, year, "baseline_deferred_asset_end_bil")
                        ),
                        "shocked_deferred_asset_eoy_bil": _fmt(
                            _last_year_value(path, year, "shocked_deferred_asset_end_bil")
                        ),
                        "baseline_remittance_bil": _fmt(
                            sum(_d(row["baseline_remittance_bil"]) for row in path if row["year"] == year)
                        ),
                        "shocked_remittance_bil": _fmt(
                            sum(_d(row["shocked_remittance_bil"]) for row in path if row["year"] == year)
                        ),
                    }
                )
    return rows


def _funding_regime_rows(
    builds: dict[str, object],
    monthly_off: dict[tuple[str, str], list[dict[str, Decimal | str]]],
    self_monthly_loop_on: dict[tuple[str, str], list[dict[str, Decimal | str]]],
    funded_monthly_loop_on: dict[tuple[str, str], list[dict[str, Decimal | str]]],
    self_paths: dict[tuple[str, str], list[dict[str, Decimal | str]]],
    funded_paths: dict[tuple[str, str], list[dict[str, Decimal | str]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    ricardian_offsets = _ricardian_offsets(
        _effective_pack(_load_pack(Path("configs/rwtam/packs")), True, True)
    )
    for dose_mode in DOSE_MODES:
        for band in BANDS:
            for horizon_id, period_type, period in (
                ("year1_2026", "annual", "2026"),
                ("persistent_120m", "cumulative_120_month", "2026-2035"),
            ):
                if horizon_id == "persistent_120m" and dose_mode != "persistent_level":
                    continue
                self_path = self_paths[(band, dose_mode)]
                funded_path = funded_paths[(band, dose_mode)]
                split = _funded_vs_self_timing_level_split(
                    self_path,
                    funded_path,
                    horizon_id,
                )
                for ricardian in ricardian_offsets:
                    self_values = _funding_regime_values(
                        builds[dose_mode],
                        monthly_off[(band, dose_mode)],
                        self_monthly_loop_on[(band, dose_mode)],
                        self_path,
                        band,
                        horizon_id,
                        ricardian,
                    )
                    funded_values = _funding_regime_values(
                        builds[dose_mode],
                        monthly_off[(band, dose_mode)],
                        funded_monthly_loop_on[(band, dose_mode)],
                        funded_path,
                        band,
                        horizon_id,
                        ricardian,
                    )
                    rows.append(
                        _funding_regime_output_row(
                            row_type="funding_regime_delta",
                            band=band,
                            dose_mode=dose_mode,
                            horizon_id=horizon_id,
                            period_type=period_type,
                            period=period,
                            funding_regime="self_cure",
                            financing_mode="marketable_issuance",
                            ricardian=ricardian,
                        )
                        | _format_funding_values(self_values)
                        | _format_path_sums(_horizon_path_sums(self_path, horizon_id))
                    )
                    rows.append(
                        _funding_regime_output_row(
                            row_type="funding_regime_delta",
                            band=band,
                            dose_mode=dose_mode,
                            horizon_id=horizon_id,
                            period_type=period_type,
                            period=period,
                            funding_regime="treasury_funded",
                            financing_mode="marketable_issuance",
                            ricardian=ricardian,
                        )
                        | _format_funding_values(funded_values)
                        | _format_path_sums(_horizon_path_sums(funded_path, horizon_id))
                    )
                    rows.append(
                        _funding_regime_output_row(
                            row_type="funded_minus_self_cure_delta",
                            band=band,
                            dose_mode=dose_mode,
                            horizon_id=horizon_id,
                            period_type=period_type,
                            period=period,
                            funding_regime="treasury_funded_minus_self_cure",
                            financing_mode="marketable_issuance",
                            ricardian=ricardian,
                        )
                        | {
                            "self_cure_on_RW_ratio": _fmt(self_values["on_rw"]),
                            "treasury_funded_on_RW_ratio": _fmt(funded_values["on_rw"]),
                            "funded_minus_self_cure_delta_RW_ratio": _fmt(
                                funded_values["on_rw"] - self_values["on_rw"]
                            ),
                            "loop_only_delta_N_bil": _fmt(funded_values["loop_delta_n"]),
                            "loop_only_delta_D_bil": _fmt(funded_values["loop_delta_d"]),
                            "dynamic_public_effect_bil": _fmt(funded_values["effect"]),
                            "self_cure_public_effect_bil": _fmt(self_values["effect"]),
                            "treasury_funded_public_effect_bil": _fmt(funded_values["effect"]),
                            "issuance_loop_input_bil": _fmt(-funded_values["effect"]),
                            "converted_public_effect_bil": _fmt(funded_values["converted_effect"]),
                            "resumption_timing_effect_bil": split["timing_effect_bil"],
                            "level_effect_bil": split["level_effect_bil"],
                            "residual_effect_bil": split["residual_effect_bil"],
                            "decomposition_disposition": split["decomposition_disposition"],
                            "baseline_resumption_month": _resumption_month(funded_path, "baseline"),
                            "shocked_resumption_month": _resumption_month(funded_path, "shocked"),
                            "self_cure_baseline_resumption_month": _resumption_month(
                                self_path, "baseline"
                            ),
                            "self_cure_shocked_resumption_month": _resumption_month(
                                self_path, "shocked"
                            ),
                            "value_assertion": split["value_assertion"],
                        }
                    )
                    if ricardian == Decimal("0"):
                        funded_overdraft_values = _funding_regime_values(
                            builds[dose_mode],
                            monthly_off[(band, dose_mode)],
                            monthly_off[(band, dose_mode)],
                            funded_path,
                            band,
                            horizon_id,
                            ricardian,
                        )
                        rows.append(
                            _funding_regime_output_row(
                                row_type="financing_variant",
                                band=band,
                                dose_mode=dose_mode,
                                horizon_id=horizon_id,
                                period_type=period_type,
                                period=period,
                                funding_regime="treasury_funded_minus_self_cure",
                                financing_mode="overdraft_indemnity",
                                ricardian=ricardian,
                            )
                            | {
                                "off_RW_ratio": _fmt(funded_overdraft_values["off_rw"]),
                                "loop_on_RW_ratio": _fmt(funded_overdraft_values["loop_rw"]),
                                "on_RW_ratio": _fmt(funded_overdraft_values["on_rw"]),
                                "delta_RW_ratio": _fmt(funded_overdraft_values["delta_rw"]),
                                "self_cure_on_RW_ratio": _fmt(self_values["on_rw"]),
                                "treasury_funded_on_RW_ratio": _fmt(
                                    funded_overdraft_values["on_rw"]
                                ),
                                "funded_minus_self_cure_delta_RW_ratio": _fmt(
                                    funded_overdraft_values["on_rw"] - self_values["on_rw"]
                                ),
                                "off_N_bil": _fmt(funded_overdraft_values["off_n"]),
                                "off_D_bil": _fmt(funded_overdraft_values["off_d"]),
                                "loop_on_N_bil": _fmt(funded_overdraft_values["loop_n"]),
                                "loop_on_D_bil": _fmt(funded_overdraft_values["loop_d"]),
                                "on_N_bil": _fmt(funded_overdraft_values["on_n"]),
                                "on_D_bil": _fmt(funded_overdraft_values["on_d"]),
                                "loop_only_delta_N_bil": _fmt(
                                    funded_overdraft_values["loop_delta_n"]
                                ),
                                "loop_only_delta_D_bil": _fmt(
                                    funded_overdraft_values["loop_delta_d"]
                                ),
                                "dynamic_public_effect_bil": _fmt(
                                    funded_overdraft_values["effect"]
                                ),
                                "self_cure_public_effect_bil": _fmt(self_values["effect"]),
                                "treasury_funded_public_effect_bil": _fmt(
                                    funded_overdraft_values["effect"]
                                ),
                                "issuance_loop_input_bil": _fmt(Decimal("0")),
                                "issuance_loop_delta_N_bil": _fmt(
                                    funded_overdraft_values["loop_delta_n"]
                                ),
                                "issuance_loop_delta_D_bil": _fmt(
                                    funded_overdraft_values["loop_delta_d"]
                                ),
                                "converted_public_effect_bil": _fmt(
                                    funded_overdraft_values["converted_effect"]
                                ),
                                "decomposition_disposition": (
                                    "overdraft_indemnity_zeroes_funded_market_issuance_loop; "
                                    "delta_equals_negative_self_cure_loop_effect"
                                ),
                                "value_assertion": "pass",
                                "memo": OVERDRAFT_INDEMNITY_MEMO,
                            }
                        )
    return rows


def _funding_regime_values(
    build: object,
    off_rows: list[dict[str, Decimal | str]],
    loop_rows: list[dict[str, Decimal | str]],
    path: list[dict[str, Decimal | str]],
    band: str,
    horizon_id: str,
    ricardian: Decimal,
) -> dict[str, Decimal]:
    off_n, off_d = _rollup_nd(build, band, horizon_id, ricardian)
    loop_delta_n, loop_delta_d = _horizon_delta_for_ricardian(
        off_rows,
        loop_rows,
        horizon_id,
        ricardian,
    )
    loop_n = off_n + loop_delta_n
    loop_d = off_d + loop_delta_d
    effect = _horizon_public_effect(path, horizon_id)
    converted_effect = effect * ricardian
    effect_n = max(Decimal("0"), converted_effect)
    effect_d = max(Decimal("0"), -converted_effect)
    on_n = loop_n + effect_n
    on_d = loop_d + effect_d
    off_rw = Decimal("0") if off_d == 0 else off_n / off_d
    loop_rw = Decimal("0") if loop_d == 0 else loop_n / loop_d
    on_rw = Decimal("0") if on_d == 0 else on_n / on_d
    return {
        "off_n": off_n,
        "off_d": off_d,
        "loop_n": loop_n,
        "loop_d": loop_d,
        "on_n": on_n,
        "on_d": on_d,
        "off_rw": off_rw,
        "loop_rw": loop_rw,
        "on_rw": on_rw,
        "delta_rw": on_rw - off_rw,
        "loop_delta_n": loop_delta_n,
        "loop_delta_d": loop_delta_d,
        "effect": effect,
        "converted_effect": converted_effect,
    }


def _horizon_public_effect(
    path: list[dict[str, Decimal | str]],
    horizon_id: str,
) -> Decimal:
    return sum(_d(row["public_effect_bil"]) for row in _horizon_path(path, horizon_id))


def _horizon_path(
    path: list[dict[str, Decimal | str]],
    horizon_id: str,
) -> list[dict[str, Decimal | str]]:
    if horizon_id == "year1_2026":
        return [row for row in path if row["year"] == "2026"]
    return path


def _horizon_path_sums(
    path: list[dict[str, Decimal | str]],
    horizon_id: str,
) -> dict[str, Decimal]:
    selected = _horizon_path(path, horizon_id)
    return {
        "baseline_public_fiscal_flow_bil": sum(
            _public_fiscal_flow(row, "baseline") for row in selected
        ),
        "shocked_public_fiscal_flow_bil": sum(
            _public_fiscal_flow(row, "shocked") for row in selected
        ),
        "baseline_remittance_bil": sum(_d(row["baseline_remittance_bil"]) for row in selected),
        "shocked_remittance_bil": sum(_d(row["shocked_remittance_bil"]) for row in selected),
        "baseline_treasury_transfer_paid_bil": sum(
            _optional_path_decimal(row, "baseline_treasury_transfer_paid_bil")
            for row in selected
        ),
        "shocked_treasury_transfer_paid_bil": sum(
            _optional_path_decimal(row, "shocked_treasury_transfer_paid_bil")
            for row in selected
        ),
        "opening_da_settlement_bil": sum(
            _optional_path_decimal(row, "opening_da_settlement_bil")
            for row in selected
        ),
    }


def _public_fiscal_flow(row: dict[str, Decimal | str], prefix: str) -> Decimal:
    flow_key = f"{prefix}_public_fiscal_flow_bil"
    if flow_key in row:
        return _d(row[flow_key])
    return _d(row[f"{prefix}_remittance_bil"])


def _optional_path_decimal(row: dict[str, Decimal | str], key: str) -> Decimal:
    return _d(row[key]) if key in row else Decimal("0")


def _funded_vs_self_timing_level_split(
    self_path: list[dict[str, Decimal | str]],
    funded_path: list[dict[str, Decimal | str]],
    horizon_id: str,
) -> dict[str, str]:
    self_effect = _horizon_public_effect(self_path, horizon_id)
    funded_effect = _horizon_public_effect(funded_path, horizon_id)
    level_effect = funded_effect - self_effect
    selected_self = _horizon_path(self_path, horizon_id)
    both_resumed_months = sum(
        1
        for row in selected_self
        if _d(row["baseline_remittance_bil"]) > 0 and _d(row["shocked_remittance_bil"]) > 0
    )
    if both_resumed_months == 0:
        return {
            "timing_effect_bil": "",
            "level_effect_bil": _fmt(level_effect),
            "residual_effect_bil": "",
            "decomposition_disposition": (
                "structural_non_identifiability_self_cure_shocked_never_resumes_in_horizon"
            ),
            "value_assertion": "pass",
        }
    timing_effect = sum(
        _d(funded_row["public_effect_bil"]) - _d(self_row["public_effect_bil"])
        for funded_row, self_row in zip(
            _horizon_path(funded_path, horizon_id),
            _horizon_path(self_path, horizon_id),
            strict=True,
        )
        if _public_fiscal_flow(funded_row, "shocked")
        != _public_fiscal_flow(self_row, "shocked")
    )
    return {
        "timing_effect_bil": _fmt(timing_effect),
        "level_effect_bil": _fmt(level_effect),
        "residual_effect_bil": "",
        "decomposition_disposition": "timing_and_level_observable_in_horizon",
        "value_assertion": "review",
    }


def _format_funding_values(values: dict[str, Decimal]) -> dict[str, str]:
    return {
        "off_RW_ratio": _fmt(values["off_rw"]),
        "loop_on_RW_ratio": _fmt(values["loop_rw"]),
        "on_RW_ratio": _fmt(values["on_rw"]),
        "delta_RW_ratio": _fmt(values["delta_rw"]),
        "off_N_bil": _fmt(values["off_n"]),
        "off_D_bil": _fmt(values["off_d"]),
        "loop_on_N_bil": _fmt(values["loop_n"]),
        "loop_on_D_bil": _fmt(values["loop_d"]),
        "on_N_bil": _fmt(values["on_n"]),
        "on_D_bil": _fmt(values["on_d"]),
        "dynamic_public_effect_bil": _fmt(values["effect"]),
        "issuance_loop_input_bil": _fmt(-values["effect"]),
        "issuance_loop_delta_N_bil": _fmt(values["loop_delta_n"]),
        "issuance_loop_delta_D_bil": _fmt(values["loop_delta_d"]),
        "loop_only_delta_N_bil": _fmt(values["loop_delta_n"]),
        "loop_only_delta_D_bil": _fmt(values["loop_delta_d"]),
        "converted_public_effect_bil": _fmt(values["converted_effect"]),
    }


def _format_path_sums(values: dict[str, Decimal]) -> dict[str, str]:
    return {key: _fmt(value) for key, value in values.items()}


def _funding_regime_output_row(
    *,
    row_type: str,
    band: str,
    dose_mode: str,
    horizon_id: str,
    period_type: str,
    period: str,
    funding_regime: str,
    financing_mode: str,
    ricardian: Decimal,
) -> dict[str, str]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "row_type": row_type,
        "band": band,
        "dose_mode": dose_mode,
        "horizon_id": horizon_id,
        "period_type": period_type,
        "period": period,
        "funding_regime": funding_regime,
        "financing_mode": financing_mode,
        "public_budget_anticipation_sensitivity": _fmt(ricardian),
        "off_RW_ratio": "",
        "loop_on_RW_ratio": "",
        "on_RW_ratio": "",
        "delta_RW_ratio": "",
        "self_cure_on_RW_ratio": "",
        "treasury_funded_on_RW_ratio": "",
        "funded_minus_self_cure_delta_RW_ratio": "",
        "off_N_bil": "",
        "off_D_bil": "",
        "loop_on_N_bil": "",
        "loop_on_D_bil": "",
        "on_N_bil": "",
        "on_D_bil": "",
        "dynamic_public_effect_bil": "",
        "self_cure_public_effect_bil": "",
        "treasury_funded_public_effect_bil": "",
        "issuance_loop_input_bil": "",
        "issuance_loop_delta_N_bil": "",
        "issuance_loop_delta_D_bil": "",
        "loop_only_delta_N_bil": "",
        "loop_only_delta_D_bil": "",
        "converted_public_effect_bil": "",
        "baseline_public_fiscal_flow_bil": "",
        "shocked_public_fiscal_flow_bil": "",
        "baseline_remittance_bil": "",
        "shocked_remittance_bil": "",
        "baseline_treasury_transfer_paid_bil": "",
        "shocked_treasury_transfer_paid_bil": "",
        "opening_da_settlement_bil": "",
        "resumption_timing_effect_bil": "",
        "level_effect_bil": "",
        "residual_effect_bil": "",
        "decomposition_disposition": "",
        "baseline_resumption_month": "",
        "shocked_resumption_month": "",
        "self_cure_baseline_resumption_month": "",
        "self_cure_shocked_resumption_month": "",
        "value_assertion": "",
        "memo": "",
        "government_revenue_doctrine": GOVERNMENT_REVENUE_DOCTRINE,
        "doctrine_lineage": GOVERNMENT_REVENUE_DOCTRINE_LINEAGE,
    }


def _funding_regime_monthly_rows(
    self_paths: dict[tuple[str, str], list[dict[str, Decimal | str]]],
    funded_paths: dict[tuple[str, str], list[dict[str, Decimal | str]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for dose_mode in DOSE_MODES:
        for band in BANDS:
            rows.extend(
                _funding_regime_monthly_row(row, "self_cure")
                for row in self_paths[(band, dose_mode)]
            )
            rows.extend(
                _funding_regime_monthly_row(row, "treasury_funded")
                for row in funded_paths[(band, dose_mode)]
            )
    return rows


def _funding_regime_monthly_row(
    row: dict[str, Decimal | str],
    funding_regime: str,
) -> dict[str, str]:
    return {
        "experiment_id": str(row["experiment_id"]),
        "row_type": str(row["row_type"]),
        "funding_regime": funding_regime,
        "financing_mode": str(row.get("financing_mode", "marketable_issuance")),
        "month_index": _fmt(row["month_index"]) if isinstance(row["month_index"], Decimal) else str(row["month_index"]),
        "month": str(row["month"]),
        "year": str(row["year"]),
        "band": str(row["band"]),
        "dose_mode": str(row["dose_mode"]),
        "shock_size_bp": _fmt(row["shock_size_bp"]) if isinstance(row["shock_size_bp"], Decimal) else str(row["shock_size_bp"]),
        "opening_deferred_asset_bil": _fmt(row["opening_deferred_asset_bil"]) if isinstance(row["opening_deferred_asset_bil"], Decimal) else str(row["opening_deferred_asset_bil"]),
        "opening_da_settlement_bil": _fmt(_optional_path_decimal(row, "opening_da_settlement_bil")),
        "baseline_net_income_bil": _fmt(row["baseline_net_income_bil"]) if isinstance(row["baseline_net_income_bil"], Decimal) else str(row["baseline_net_income_bil"]),
        "baseline_deferred_asset_begin_bil": _fmt(row["baseline_deferred_asset_begin_bil"]) if isinstance(row["baseline_deferred_asset_begin_bil"], Decimal) else str(row["baseline_deferred_asset_begin_bil"]),
        "baseline_paydown_bil": _fmt(row["baseline_paydown_bil"]) if isinstance(row["baseline_paydown_bil"], Decimal) else str(row["baseline_paydown_bil"]),
        "baseline_loss_addition_bil": _fmt(row["baseline_loss_addition_bil"]) if isinstance(row["baseline_loss_addition_bil"], Decimal) else str(row["baseline_loss_addition_bil"]),
        "baseline_remittance_bil": _fmt(row["baseline_remittance_bil"]) if isinstance(row["baseline_remittance_bil"], Decimal) else str(row["baseline_remittance_bil"]),
        "baseline_treasury_transfer_paid_bil": _fmt(_optional_path_decimal(row, "baseline_treasury_transfer_paid_bil")),
        "baseline_public_fiscal_flow_bil": _fmt(_public_fiscal_flow(row, "baseline")),
        "baseline_deferred_asset_end_bil": _fmt(row["baseline_deferred_asset_end_bil"]) if isinstance(row["baseline_deferred_asset_end_bil"], Decimal) else str(row["baseline_deferred_asset_end_bil"]),
        "shocked_expense_delta_bil": _fmt(row["shocked_expense_delta_bil"]) if isinstance(row["shocked_expense_delta_bil"], Decimal) else str(row["shocked_expense_delta_bil"]),
        "shocked_soma_income_delta_bil": _fmt(row["shocked_soma_income_delta_bil"]) if isinstance(row["shocked_soma_income_delta_bil"], Decimal) else str(row["shocked_soma_income_delta_bil"]),
        "shocked_net_income_bil": _fmt(row["shocked_net_income_bil"]) if isinstance(row["shocked_net_income_bil"], Decimal) else str(row["shocked_net_income_bil"]),
        "shocked_deferred_asset_begin_bil": _fmt(row["shocked_deferred_asset_begin_bil"]) if isinstance(row["shocked_deferred_asset_begin_bil"], Decimal) else str(row["shocked_deferred_asset_begin_bil"]),
        "shocked_paydown_bil": _fmt(row["shocked_paydown_bil"]) if isinstance(row["shocked_paydown_bil"], Decimal) else str(row["shocked_paydown_bil"]),
        "shocked_loss_addition_bil": _fmt(row["shocked_loss_addition_bil"]) if isinstance(row["shocked_loss_addition_bil"], Decimal) else str(row["shocked_loss_addition_bil"]),
        "shocked_remittance_bil": _fmt(row["shocked_remittance_bil"]) if isinstance(row["shocked_remittance_bil"], Decimal) else str(row["shocked_remittance_bil"]),
        "shocked_treasury_transfer_paid_bil": _fmt(_optional_path_decimal(row, "shocked_treasury_transfer_paid_bil")),
        "shocked_public_fiscal_flow_bil": _fmt(_public_fiscal_flow(row, "shocked")),
        "shocked_deferred_asset_end_bil": _fmt(row["shocked_deferred_asset_end_bil"]) if isinstance(row["shocked_deferred_asset_end_bil"], Decimal) else str(row["shocked_deferred_asset_end_bil"]),
        "dynamic_remittance_delta_bil": _fmt(row["dynamic_remittance_delta_bil"]) if isinstance(row["dynamic_remittance_delta_bil"], Decimal) else str(row["dynamic_remittance_delta_bil"]),
        "treasury_transfer_delta_bil": _fmt(_optional_path_decimal(row, "treasury_transfer_delta_bil")),
        "public_effect_bil": _fmt(row["public_effect_bil"]) if isinstance(row["public_effect_bil"], Decimal) else str(row["public_effect_bil"]),
        "repriced_soma_stock_bil": _fmt(row["repriced_soma_stock_bil"]) if isinstance(row["repriced_soma_stock_bil"], Decimal) else str(row["repriced_soma_stock_bil"]),
        "qt_runoff_annual_bil": _fmt(row["qt_runoff_annual_bil"]) if isinstance(row["qt_runoff_annual_bil"], Decimal) else str(row["qt_runoff_annual_bil"]),
        "lineage": str(row["lineage"]),
        "government_revenue_doctrine": GOVERNMENT_REVENUE_DOCTRINE,
        "doctrine_lineage": GOVERNMENT_REVENUE_DOCTRINE_LINEAGE,
    }


def _funding_regime_invariant_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    doctrine_ok = all(
        row["government_revenue_doctrine"] == GOVERNMENT_REVENUE_DOCTRINE
        and row["doctrine_lineage"] == GOVERNMENT_REVENUE_DOCTRINE_LINEAGE
        for row in rows
    )
    funded_sensitivity_zero_rows = [
        row
        for row in rows
        if row["row_type"] == "funding_regime_delta"
        and row["funding_regime"] == "treasury_funded"
        and row["public_budget_anticipation_sensitivity"] == "0"
    ]
    direct_zero_ok = all(
        _d(row["converted_public_effect_bil"]) == 0
        and _d(row["delta_RW_ratio"])
        == _d(row["loop_on_RW_ratio"]) - _d(row["off_RW_ratio"])
        for row in funded_sensitivity_zero_rows
    )
    overdraft_rows = [
        row
        for row in rows
        if row["row_type"] == "financing_variant"
        and row["financing_mode"] == "overdraft_indemnity"
        and row["public_budget_anticipation_sensitivity"] == "0"
    ]
    self_cure_rows = [
        row
        for row in rows
        if row["row_type"] == "funding_regime_delta"
        and row["funding_regime"] == "self_cure"
        and row["financing_mode"] == "marketable_issuance"
        and row["public_budget_anticipation_sensitivity"] == "0"
    ]
    self_cure_by_key = {
        (row["band"], row["dose_mode"], row["horizon_id"]): row
        for row in self_cure_rows
    }
    overdraft_loop_off_ok = bool(overdraft_rows) and all(
        _d(row["treasury_funded_on_RW_ratio"]) == _d(row["off_RW_ratio"])
        and _d(row["loop_on_RW_ratio"]) == _d(row["off_RW_ratio"])
        and _d(row["issuance_loop_input_bil"]) == 0
        and _d(row["issuance_loop_delta_N_bil"]) == 0
        and _d(row["issuance_loop_delta_D_bil"]) == 0
        and (
            _d(row["funded_minus_self_cure_delta_RW_ratio"])
            == -_d(
                self_cure_by_key[
                    (row["band"], row["dose_mode"], row["horizon_id"])
                ]["delta_RW_ratio"]
            )
        )
        for row in overdraft_rows
    )
    base_funded = next(
        row
        for row in funded_sensitivity_zero_rows
        if row["band"] == "base"
        and row["dose_mode"] == "persistent_level"
        and row["horizon_id"] == "persistent_120m"
    )
    sign_ok = (
        _d(base_funded["issuance_loop_input_bil"]) > 0
        and _d(base_funded["issuance_loop_delta_N_bil"]) > 0
        and _d(base_funded["issuance_loop_delta_D_bil"]) < 0
    )
    return [
        _check_row(
            "FPNL_TF1",
            doctrine_ok,
            "doctrine row present on all funding-regime rows",
        ),
        _check_row(
            "FPNL_TF2",
            direct_zero_ok,
            "treasury_funded sensitivity 0 has zero direct N/D leg",
        ),
        _check_row(
            "FPNL_TF3",
            overdraft_loop_off_ok,
            "overdraft_indemnity loop-off funded on_RW equals off_RW and delta equals negative self-cure loop effect",
        ),
        _check_row(
            "FPNL_TF4",
            sign_ok,
            "base persistent funded loop pulls fiscal hit forward: loop input and N positive, D negative",
        ),
    ]


def _horizon_delta_for_ricardian(
    off_rows: list[dict[str, Decimal | str]],
    rows: list[dict[str, Decimal | str]],
    horizon_id: str,
    ricardian_offset: Decimal,
) -> tuple[Decimal, Decimal]:
    if horizon_id == "year1_2026":
        selected = [
            row
            for row in rows
            if row["year"] == "2026" and row["ricardian_offset"] == ricardian_offset
        ]
    else:
        selected = [row for row in rows if row["ricardian_offset"] == ricardian_offset]
    if horizon_id == "year1_2026":
        off_selected = [
            row
            for row in off_rows
            if row["year"] == "2026" and row["ricardian_offset"] == ricardian_offset
        ]
    else:
        off_selected = [row for row in off_rows if row["ricardian_offset"] == ricardian_offset]
    loop_n = sum(_d(row["N"]) for row in selected)
    loop_d = sum(_d(row["D"]) for row in selected)
    off_n = sum(_d(row["N"]) for row in off_selected)
    off_d = sum(_d(row["D"]) for row in off_selected)
    return (
        loop_n - off_n,
        loop_d - off_d,
    )


def _rollup_nd(
    build: object,
    band: str,
    horizon_id: str,
    ricardian_offset: Decimal = Decimal("0"),
) -> tuple[Decimal, Decimal]:
    period_type = "annual" if horizon_id == "year1_2026" else "cumulative_120_month"
    period = "2026" if horizon_id == "year1_2026" else "2026-2035"
    row = next(
        item
        for item in build.rows("out_ratewall_rollup")  # type: ignore[attr-defined]
        if item["period_type"] == period_type
        and item["period"] == period
        and item["band"] == band
        and item["ricardian_offset"] == _fmt(ricardian_offset)
    )
    return _d(row["N_bil"]), _d(row["D_bil"])


def _annual_public_effects(path: list[dict[str, Decimal | str]]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {}
    for row in path:
        year = str(row["year"])
        out[year] = out.get(year, Decimal("0")) + _d(row["public_effect_bil"])
    return out


def _issuance_loop_inputs_from_paths(
    paths: dict[tuple[str, str], list[dict[str, Decimal | str]]],
    dose_mode: str,
) -> dict[tuple[str, str], Decimal]:
    inputs: dict[tuple[str, str], Decimal] = {}
    for band in BANDS:
        for row in paths[(band, dose_mode)]:
            inputs[(band, str(row["month"]))] = -_d(row["public_effect_bil"])
    return inputs


def _annual_static_remittance(
    rows: list[dict[str, Decimal | str]],
    year: str,
) -> Decimal:
    return sum(
        _d(row["remittance_delta"])
        for row in rows
        if row["year"] == year and row["ricardian_offset"] == Decimal("0")
    )


def _independent_timing_effect(
    path: list[dict[str, Decimal | str]],
    horizon_id: str,
) -> Decimal:
    selected = path if horizon_id != "year1_2026" else [row for row in path if row["year"] == "2026"]
    timing = Decimal("0")
    for row in selected:
        baseline_remit = _d(row["baseline_remittance_bil"])
        shocked_remit = _d(row["shocked_remittance_bil"])
        if baseline_remit > 0 and shocked_remit <= 0:
            timing -= baseline_remit
    return timing


def _structural_non_identifiability_rows(
    delta_rows: list[dict[str, str]],
    paths: dict[tuple[str, str], list[dict[str, Decimal | str]]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in delta_rows:
        if row["row_type"] != "delta_rw":
            continue
        path = paths[(row["band"], row["dose_mode"])]
        selected = path if row["horizon_id"] != "year1_2026" else [
            item for item in path if item["year"] == "2026"
        ]
        both_resumed_months = sum(
            1
            for item in selected
            if _d(item["baseline_remittance_bil"]) > 0
            and _d(item["shocked_remittance_bil"]) > 0
        )
        disposition = (
            "structural_non_identifiability_shocked_never_resumes_in_horizon"
            if both_resumed_months == 0
            else "level_leg_observable_both_paths_resume_in_horizon"
        )
        rows.append(
            _base_output_row(
                row_type="structural_non_identifiability",
                band=row["band"],
                dose_mode=row["dose_mode"],
                horizon_id=row["horizon_id"],
                period_type=row["period_type"],
                period=row["period"],
            )
            | {
                "baseline_resumption_month": row["baseline_resumption_month"],
                "shocked_resumption_month": row["shocked_resumption_month"],
                "decomposition_disposition": disposition,
                "level_identifiable_month_count": str(both_resumed_months),
                "value_assertion": "pass" if both_resumed_months == 0 else "review",
                "government_revenue_doctrine": GOVERNMENT_REVENUE_DOCTRINE,
                "doctrine_lineage": GOVERNMENT_REVENUE_DOCTRINE_LINEAGE,
            }
        )
    return rows


def _resumption_month(path: list[dict[str, Decimal | str]], prefix: str) -> str:
    field = f"{prefix}_remittance_bil"
    for row in path:
        if _d(row[field]) > 0:
            return str(row["month"])
    return "not_within_120m"


def _last_year_value(path: list[dict[str, Decimal | str]], year: str, field: str) -> Decimal:
    rows = [row for row in path if row["year"] == year]
    return _d(rows[-1][field]) if rows else Decimal("0")


def _backcast_score_rows(
    monthly: list[dict[str, Decimal | str]],
    targets: list[dict[str, str]],
) -> list[dict[str, str]]:
    annual = {}
    for year in ("2022", "2023", "2024"):
        rows = [row for row in monthly if row["year"] == year]
        annual[year] = {
            "cash_remit": sum(_d(row["cash_remittance_bil"]) for row in rows),
            "da_change": sum(_d(row["deferred_asset_change_bil"]) for row in rows),
            "public_cost": sum(_d(row["public_cost_deferred_minus_cash_remit_bil"]) for row in rows),
            "net_statement": sum(_d(row["cash_remittance_bil"]) - _d(row["deferred_asset_change_bil"]) for row in rows),
            "da_eoy": _d(rows[-1]["deferred_asset_end_bil"]),
        }
    target_by_year = {row["year"]: row for row in targets}
    out: list[dict[str, str]] = []
    suspension = next((row["month"] for row in monthly if _d(row["cash_remittance_bil"]) == 0), "")
    for year, values in annual.items():
        target = target_by_year.get(year, {})
        mapping = (
            ("cash_remittances_transferred_to_treasury_bil", "cash_remit"),
            ("deferred_asset_increase_bil", "da_change"),
            ("earnings_remittances_to_treasury_net_statement_sign_bil", "net_statement"),
            ("deferred_asset_eoy_balance_bil", "da_eoy"),
            ("fed_public_cost_deferred_minus_cash_remit_bil", "public_cost"),
        )
        for target_field, predicted_key in mapping:
            predicted = values[predicted_key]
            realized_text = target.get(target_field, "")
            realized = _d(realized_text) if realized_text else None
            out.append(
                _base_output_row(
                    row_type="backcast_score",
                    band="base",
                    dose_mode="realized_rate_path",
                    horizon_id=f"backcast_{year}_{predicted_key}",
                    period_type="annual",
                    period=year,
                )
                | {
                    "backcast_metric": predicted_key,
                    "predicted_value_bil": _fmt(predicted),
                    "realized_value_bil": realized_text,
                    "error_bil": "" if realized is None else _fmt(predicted - realized),
                    "predicted_remittance_suspension_month": str(suspension),
                    "no_fit_policy": "no_coefficients_or_mixes_adjusted_to_targets",
                }
            )
    anchor_error = annual["2024"]["da_eoy"] - OPENING_DEFERRED_ASSET_BASE_BIL
    out.append(
        _base_output_row(
            row_type="backcast_anchor_check",
            band="base",
            dose_mode="realized_rate_path",
            horizon_id="out_of_window_20260701_da_anchor",
            period_type="anchor_check",
            period="2026-07-01",
        )
        | {
            "backcast_metric": "deferred_asset_eoy_vs_20260701_anchor",
            "predicted_value_bil": _fmt(annual["2024"]["da_eoy"]),
            "realized_value_bil": _fmt(OPENING_DEFERRED_ASSET_BASE_BIL),
            "error_bil": _fmt(anchor_error),
            "lineage": OWNER_SOURCE_ID,
            "no_fit_policy": "no_coefficients_or_mixes_adjusted_to_targets",
        }
    )
    return out


def _backcast_soma_avg_yield(
    pack: dict[str, list[dict[str, str]]],
    band: str,
) -> tuple[Decimal, str]:
    target_rows = pack.get("realized_flow_targets", [])
    income_rows = [
        row
        for row in target_rows
        if "fed" in row.get("channel", "")
        and "income" in row.get("channel", "")
        and row.get("realized_value_bil")
    ]
    if income_rows:
        total_income = sum(_d(row["realized_value_bil"]) for row in income_rows)
        years = sorted({row["year"] for row in income_rows})
        soma_total = sum(
            balances["soma_treasury_bil"] + balances["soma_mbs_bil"]
            for quarter, balances in BACKCAST_QUARTERLY_AVERAGES.items()
            if quarter[:4] in years
        )
        return (
            total_income / soma_total * Decimal("4"),
            "derived_from_realized_fed_interest_income_rows",
        )
    return (
        BACKCAST_OWNER_YIELD_BANDS[band],
        "owner_assumption_mode_no_realized_fed_interest_income_rows_2_0_2_15_2_3_pct",
    )


def _backcast_balance_for_month(month: str) -> dict[str, Decimal]:
    return BACKCAST_QUARTERLY_AVERAGES[_quarter_from_month(month)]


def _quarter_from_month(month: str) -> str:
    year, month_text = month.split("-")
    quarter = (int(month_text) - 1) // 3 + 1
    return f"{year}Q{quarter}"


def _base_output_row(
    *,
    row_type: str,
    band: str,
    dose_mode: str,
    horizon_id: str,
    period_type: str,
    period: str,
) -> dict[str, str]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "row_type": row_type,
        "band": band,
        "dose_mode": dose_mode,
        "horizon_id": horizon_id,
        "period_type": period_type,
        "period": period,
        "ricardian_offset": "",
        "off_RW_ratio": "",
        "on_RW_ratio": "",
        "delta_RW_ratio": "",
        "off_N_bil": "",
        "off_D_bil": "",
        "on_N_bil": "",
        "on_D_bil": "",
        "dynamic_public_effect_bil": "",
        "issuance_loop_input_bil": "",
        "issuance_loop_delta_N_bil": "",
        "issuance_loop_delta_D_bil": "",
        "loop_on_N_bil": "",
        "loop_on_D_bil": "",
        "converted_public_effect_bil": "",
        "resumption_timing_effect_bil": "",
        "level_effect_bil": "",
        "residual_effect_bil": "",
        "decomposition_disposition": "",
        "level_identifiable_month_count": "",
        "ricardian_0_off_RW": "",
        "ricardian_0_on_RW": "",
        "ricardian_0_delta_RW": "",
        "ricardian_0_converted_public_effect_bil": "",
        "ricardian_0_2_off_RW": "",
        "ricardian_0_2_on_RW": "",
        "ricardian_0_2_delta_RW": "",
        "ricardian_0_2_converted_public_effect_bil": "",
        "ricardian_0_5_off_RW": "",
        "ricardian_0_5_on_RW": "",
        "ricardian_0_5_delta_RW": "",
        "ricardian_0_5_converted_public_effect_bil": "",
        "public_budget_anticipation_sensitivity": "",
        "public_budget_anticipation_sensitivity_0_off_RW": "",
        "public_budget_anticipation_sensitivity_0_on_RW": "",
        "public_budget_anticipation_sensitivity_0_delta_RW": "",
        "public_budget_anticipation_sensitivity_0_converted_public_effect_bil": "",
        "public_budget_anticipation_sensitivity_0_2_off_RW": "",
        "public_budget_anticipation_sensitivity_0_2_on_RW": "",
        "public_budget_anticipation_sensitivity_0_2_delta_RW": "",
        "public_budget_anticipation_sensitivity_0_2_converted_public_effect_bil": "",
        "public_budget_anticipation_sensitivity_0_5_off_RW": "",
        "public_budget_anticipation_sensitivity_0_5_on_RW": "",
        "public_budget_anticipation_sensitivity_0_5_delta_RW": "",
        "public_budget_anticipation_sensitivity_0_5_converted_public_effect_bil": "",
        "static_gate_off_remittance_delta_bil": "",
        "dynamic_on_remittance_delta_bil": "",
        "baseline_deferred_asset_eoy_bil": "",
        "shocked_deferred_asset_eoy_bil": "",
        "baseline_remittance_bil": "",
        "shocked_remittance_bil": "",
        "baseline_resumption_month": "",
        "shocked_resumption_month": "",
        "backcast_metric": "",
        "predicted_value_bil": "",
        "realized_value_bil": "",
        "error_bil": "",
        "predicted_remittance_suspension_month": "",
        "value_assertion": "",
        "no_fit_policy": "",
        "lineage": "",
        "caveat": "",
        "government_revenue_doctrine": "",
        "doctrine_lineage": "",
    }


def _invariant_rows(
    rows: list[dict[str, str]],
    paths: dict[tuple[str, str], list[dict[str, Decimal | str]]],
) -> list[dict[str, str]]:
    identity_ok = True
    nonnegative_ok = True
    for path in paths.values():
        for row in path:
            for prefix in ("baseline", "shocked"):
                positive = max(Decimal("0"), _d(row[f"{prefix}_net_income_bil"]))
                lhs = _d(row[f"{prefix}_paydown_bil"]) + _d(row[f"{prefix}_remittance_bil"])
                if abs(lhs - positive) > Decimal("0.000001"):
                    identity_ok = False
                if _d(row[f"{prefix}_deferred_asset_end_bil"]) < 0:
                    nonnegative_ok = False
    base = simulate_forward_paired_path(
        _effective_pack(_load_pack(Path("configs/rwtam/packs")), True, True),
        band="base",
        dose_mode="persistent_level",
        opening_deferred_asset_bil=OPENING_DEFERRED_ASSET_BASE_BIL,
    )
    mutated = simulate_forward_paired_path(
        _effective_pack(_load_pack(Path("configs/rwtam/packs")), True, True),
        band="base",
        dose_mode="persistent_level",
        opening_deferred_asset_bil=Decimal("25"),
    )
    return [
        _check_row("FPNL1", nonnegative_ok, "deferred asset path remains nonnegative"),
        _check_row("FPNL2", identity_ok, "remittances plus paydown equals positive income"),
        _check_row(
            "FPNL3",
            _resumption_month(base, "baseline") != _resumption_month(mutated, "baseline"),
            "opening deferred asset mutation moves resumption month",
        ),
        _check_row(
            "FPNL4",
            all(row.get("value_assertion") != "fail" for row in rows),
            "independent timing effect equals raw public remittance effect",
        ),
        _check_row(
            "FPNL5",
            all(
                row["row_type"] != "delta_rw"
                or _d(row["issuance_loop_input_bil"]) == -_d(row["dynamic_public_effect_bil"])
                for row in rows
            ),
            "remittance public effect feeds issuance loop with opposite sign",
        ),
    ]


def _check_row(check_id: str, ok: bool, message: str) -> dict[str, str]:
    return {"check_id": check_id, "status": "pass" if ok else "fail", "message": message}


def _lineage_rows() -> list[dict[str, str]]:
    return [
        _base_output_row(
            row_type="lineage",
            band="all",
            dose_mode="all",
            horizon_id="owner_supplied_h41_anchors",
            period_type="anchor",
            period="2026-07-01",
        )
        | {
            "lineage": (
                "deferred_asset=235.615bn;SOMA_Treasury=4492.235bn;"
                "SOMA_MBS=1948.398bn;source=H41_FRED_20260701_OWNER_SUPPLIED"
            )
        },
        _base_output_row(
            row_type="lineage",
            band="all",
            dose_mode="all",
            horizon_id="owner_assumption_parameters",
            period_type="assumption",
            period="2026-2035",
        )
        | {
            "lineage": (
                "ops_cost_LBH=7/9/11bn_per_year;opening_DA_bands=235.615 +/- "
                "190bn placeholder half-spread floored at zero;soma_avg_yield from "
                "structural_assumptions owner_assumption_mode"
            )
        },
        _base_output_row(
            row_type="lineage",
            band="base",
            dose_mode="realized_rate_path",
            horizon_id="backcast_owner_supplied_quarterly_averages",
            period_type="backcast_construction",
            period="2022-2024",
        )
        | {
            "lineage": (
                "FRED_QAVG_20260705_OWNER_SUPPLIED full SOMA Treasury+MBS, "
                "reserves, and ON RRP quarterly averages; each month in a quarter "
                "uses that quarter average so quarterly means are preserved; no "
                "repricing-base subset is used"
            )
        },
        _base_output_row(
            row_type="lineage",
            band="base",
            dose_mode="realized_rate_path",
            horizon_id="backcast_soma_yield_construction",
            period_type="backcast_construction",
            period="2022-2024",
        )
        | {
            "lineage": (
                "no realized Fed interest-income rows found in "
                "do/backcast/realized_flow_targets.csv; used owner_assumption_mode "
                "era band low/base/high=2.0/2.15/2.3 pct per year"
            )
        },
    ]


def _caveat_rows() -> list[dict[str, str]]:
    return [
        _base_output_row(
            row_type="caveat",
            band="all",
            dose_mode="all",
            horizon_id="government_revenue_doctrine",
            period_type="caveat",
            period="all",
        )
        | {
            "caveat": CAVEAT,
            "government_revenue_doctrine": GOVERNMENT_REVENUE_DOCTRINE,
            "doctrine_lineage": GOVERNMENT_REVENUE_DOCTRINE_LINEAGE,
        }
    ]


def _opening_deferred_asset_band(band: str) -> Decimal:
    if band == "base":
        return OPENING_DEFERRED_ASSET_BASE_BIL
    if band == "low":
        return max(Decimal("0"), OPENING_DEFERRED_ASSET_BASE_BIL - PLACEHOLDER_HALF_SPREAD_BIL)
    return OPENING_DEFERRED_ASSET_BASE_BIL + PLACEHOLDER_HALF_SPREAD_BIL


def _assumption(
    pack: dict[str, list[dict[str, str]]],
    assumption_id: str,
    band: str,
) -> Decimal:
    row = next(row for row in pack["structural_assumptions"] if row["assumption_id"] == assumption_id)
    return _d(row[band])


def _fed_held_stock(pack: dict[str, list[dict[str, str]]], family: str) -> Decimal:
    total = Decimal("0")
    for row in pack["opening_stocks"]:
        if row["instrument_family"] != family:
            continue
        if _holder_from_cell(row["cell_or_sector"]) == "federal_reserve":
            total += _d(row["base"])
    return total


def _holder_from_cell(cell_or_sector: str) -> str:
    for part in cell_or_sector.split("|"):
        if part.startswith("holder="):
            return part.removeprefix("holder=")
    return cell_or_sector


def _stringify_rows(rows: object) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in rows:  # type: ignore[union-attr]
        out.append({key: _fmt(value) if isinstance(value, Decimal) else str(value) for key, value in row.items()})
    return out
