"""Quarantined illustrative-state exhibits for RWTAM final-deliverable figures."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtam.data_upgrades import (
    HISTORICAL_UPGRADE_PACK_DIR,
    historical_bank_perimeter_rows,
    historical_upgrade_disposition_rows,
    settlement_class_invariant_rows,
    settlement_class_map_rows,
    upgraded_decade_configs,
)
from ratewall.rwtam.hysteresis import _write_opening
from ratewall.rwtam.slr_conditions import _headline, _rollup_only, _markdown_table
from ratewall.rwtam.v1 import (
    BANDS,
    CURRENT_DEFAULT_OBJECT_STAMP,
    _d,
    _fmt,
    _read_csv_rows,
    _write_rows,
)


EXPERIMENT_ID = "rwtam_illustrative_states_20260703"
OUTPUT_DIR = Path("var/rwtam/scenarios/illustrative_states")
REPORT_PATH = Path("do/rwtam_illustrative_states_report_20260703.md")
DATA_UPGRADE_REPORT_PATH = Path("do/rwtam_data_upgrades_wire_report_20260703.md")
PACK_DIR = Path("configs/rwtam/packs")
SLR_SPECTRUM_PATH = Path("var/rwtam/scenarios/slr_conditions/out_slr_spectrum.csv")
DECADE_LABEL = "semi_evidence_grade_illustration"
FIAT_LABEL = "hypothetical_illustration;shape_only"
EMERGENCE_CAPTION_NOTE = (
    "Decade emergence is non-monotonic inside pre-2008 states; 1965 remains "
    "above 1985 because household-held Treasuries were larger relative to GDP. "
    "Use as emergence shape, not a monotone backtest."
)
SHAPE_ONLY_CAPTION_NOTE = (
    "Shape-only illustration: use for mechanism and comparative shape, not as a "
    "country calibration, fitted level, or backtest."
)
JAPAN_CALIBRATION_LABEL = "japan_calibration_fact_pack_20260707"
JAPAN_POST_EXIT_LABEL = "calibrated_japan_post_exit_2026;assumption_mode"
JAPAN_NIRP_LABEL = "calibrated_japan_nirp_2019_zero_wall_pole;assumption_mode"
JAPAN_SCALE_GDP = Decimal("31500")
JAPAN_FACT_PACK_PATH = "do/research/japan_calibration_fact_pack_20260707.md"
BRAZIL_FACT_PACK_PATH = "do/research/brazil_euroarea_fact_pack_20260707.md"
BRAZIL_LABEL = "brazil_euroarea_fact_pack_20260707_section_A;assumption_mode"
BRAZIL_STATE_ID = "brazil_2025"
BRAZIL_SCALE_GDP = Decimal("31500")
BYTE_ASSERT_PATHS = (
    Path("var/rwtam/v1/dose_modes/persistent_level/out_ratewall_rollup.csv"),
    Path("tests/fixtures/rwtam/golden_wave8/out_ratewall_rollup.csv"),
    Path("tests/fixtures/rwtam/golden_wave8_tax_off/out_ratewall_rollup.csv"),
)


@dataclass(frozen=True)
class IllustrativeStateResult:
    """CSV-ready output tables for the illustrative-state exhibit pack."""

    tables: dict[str, list[dict[str, str]]]

    def rows(self, table_name: str) -> list[dict[str, str]]:
        return self.tables[table_name]


LEGACY_DECADE_CONFIGS = {
    "historical_1965": {
        "display_year": "1965",
        "gdp_bil": Decimal("743.7"),
        "debt_public_bil": Decimal("260.8"),
        "debt_pct_gdp_verbatim": "37.9% [B]",
        "bill_share": Decimal("0.275"),
        "bill_share_verbatim": "~25-30% [C]",
        "fed_share": Decimal("0.150"),
        "fed_share_verbatim": "15.0% [A/arith]",
        "foreign_share": Decimal("0.060"),
        "foreign_share_verbatim": "~6% [C]",
        "banks_rate_sensitive_share": Decimal("0"),
        "mutual_funds_rate_sensitive_share": Decimal("0"),
        "pensions_rate_sensitive_share": Decimal("0.01"),
        "insurers_rate_sensitive_share": Decimal("0.01"),
        "state_local_rate_sensitive_share": Decimal("0.02"),
        "nonfinancial_rate_sensitive_share": Decimal("0"),
        "other_nonbank_rate_sensitive_share": Decimal("0"),
        "hh_direct_treasury_bil": Decimal("74.8"),
        "hh_marketable_treasury_bil": Decimal("25.1"),
        "hh_direct_treasury_verbatim": "74.8 (10.1%) [A]",
        "checkable_currency_bil": Decimal("86.5"),
        "time_savings_bil": Decimal("286.8"),
        "deposit_regime": "Reg Q binding; beta approximately 0 by law",
        "deposit_beta_regime": "zero_by_rule",
        "tdc_created_deposit_rate": Decimal("0"),
        "mmf_total_bil": Decimal("0"),
        "hh_mmf_bil": Decimal("0"),
        "mortgage_bil": Decimal("213"),
        "arm_share": Decimal("0"),
        "consumer_credit_bil": Decimal("95.95"),
        "consumer_credit_verbatim": "95.95 (12.9%) [A]",
        "claim_grade_label": DECADE_LABEL,
    },
    "historical_1985": {
        "display_year": "1985",
        "gdp_bil": Decimal("4346.7"),
        "debt_public_bil": Decimal("1507.3"),
        "debt_pct_gdp_verbatim": "36.3-36.4% [B]",
        "bill_share": Decimal("0.375"),
        "bill_share_verbatim": "~35-40% [C]",
        "fed_share": Decimal("0.113"),
        "fed_share_verbatim": "11.3% [A/arith]",
        "foreign_share": Decimal("0.170"),
        "foreign_share_verbatim": "~17% [C]",
        "hh_direct_treasury_bil": Decimal("250.9"),
        "hh_marketable_treasury_bil": Decimal("171.2"),
        "hh_direct_treasury_verbatim": "250.9 (5.8%) [A]",
        "checkable_currency_bil": Decimal("342.4"),
        "time_savings_bil": Decimal("1940.9"),
        "deposit_regime": "mixed: MMDA free / passbook capped",
        "deposit_beta_regime": "bifurcated",
        "tdc_created_deposit_rate": Decimal("0.012"),
        "mmf_total_bil": Decimal("242.4"),
        "hh_mmf_bil": Decimal("193.3"),
        "mortgage_bil": Decimal("1447"),
        "arm_share": Decimal("0.55"),
        "consumer_credit_bil": Decimal("599.7"),
        "consumer_credit_verbatim": "599.7 (13.8%) [A]",
        "claim_grade_label": DECADE_LABEL,
    },
    "historical_2005": {
        "display_year": "2005",
        "gdp_bil": Decimal("13095.4"),
        "debt_public_bil": Decimal("4592"),
        "debt_pct_gdp_verbatim": "35.6-36.9% [B]",
        "bill_share": Decimal("0.21"),
        "bill_share_verbatim": "~20-22% [C]",
        "fed_share": Decimal("0.160"),
        "fed_share_verbatim": "~16% [C]",
        "foreign_share": Decimal("0.370"),
        "foreign_share_verbatim": "~37% [B/C]",
        "hh_direct_treasury_bil": Decimal("425.7"),
        "hh_marketable_treasury_bil": Decimal("425.7"),
        "hh_direct_treasury_verbatim": "425.7 (3.3%) [A]",
        "checkable_currency_bil": Decimal("285.9"),
        "time_savings_bil": Decimal("4965.0"),
        "deposit_regime": "fully deregulated; market betas",
        "deposit_beta_regime": "market",
        "tdc_created_deposit_rate": Decimal("0.028"),
        "mmf_total_bil": Decimal("1993.1"),
        "hh_mmf_bil": Decimal("942.7"),
        "mortgage_bil": Decimal("8900"),
        "arm_share": Decimal("0.33"),
        "consumer_credit_bil": Decimal("2320"),
        "consumer_credit_verbatim": "~2,320 (17.7%) [B]",
        "claim_grade_label": DECADE_LABEL,
    },
}
DECADE_CONFIGS = upgraded_decade_configs(LEGACY_DECADE_CONFIGS)


JAPAN_CONFIGS: dict[str, dict[str, object]] = {
    "japan_nirp_2019": {
        "state_id": "japan_nirp_2019",
        "label": JAPAN_NIRP_LABEL,
        "policy_rate": Decimal("-0.001"),
        "policy_rate_label": "-0.1% NIRP policy rate",
        "debt_gdp": Decimal("1.74"),
        "bill_share": Decimal("0.119"),
        "fed_share": Decimal("0.5386"),
        "fed_share_label": "near-peak BOJ share; fact-pack peak 53.86% Sep 2023",
        "banks_share": Decimal("0.136"),
        "insurers_share": Decimal("0.137"),
        "pensions_share": Decimal("0.092"),
        "household_direct_share": Decimal("0.020"),
        "foreign_share": Decimal("0.081"),
        "mmf_share": Decimal("0"),
        "state_local_share": Decimal("0.015"),
        "nonfinancial_share": Decimal("0.008"),
        "other_nonbank_share": Decimal("0.011"),
        "mutual_funds_share": Decimal("0"),
        "household_deposit_gdp": Decimal("1.70"),
        "deposit_demand_share": Decimal("0.72"),
        "deposit_time_share": Decimal("0.28"),
        "deposit_beta": Decimal("0"),
        "deposit_beta_label": "NIRP-era zero-wall pole; beta approximately 0",
        "tdc_created_deposit_rate": Decimal("0"),
        "mortgage_stock_gdp": Decimal("225") / Decimal("662.8"),
        "floating_mortgage_share": Decimal("0.78"),
        "household_debt_gdp": Decimal("392") / Decimal("662.8"),
        "mpc_low": Decimal("0.10"),
        "mpc_base": Decimal("0.15"),
        "mpc_high": Decimal("0.20"),
    },
    "japan_post_exit_2026": {
        "state_id": "japan_post_exit_2026",
        "label": JAPAN_POST_EXIT_LABEL,
        "policy_rate": Decimal("0.01"),
        "policy_rate_label": "Jun 16 2026 policy rate 1.00%",
        "debt_gdp": Decimal("1.74"),
        "bill_share": Decimal("0.119"),
        "fed_share": Decimal("0.48"),
        "fed_share_label": "BOJ 47.88% JGB-only; combined JGB+T-bill share 42.21%, declining",
        "banks_share": Decimal("0.136"),
        "insurers_share": Decimal("0.137"),
        "pensions_share": Decimal("0.092"),
        "household_direct_share": Decimal("0.020"),
        "foreign_share": Decimal("0.081"),
        "mmf_share": Decimal("0"),
        "state_local_share": Decimal("0.015"),
        "nonfinancial_share": Decimal("0.008"),
        "other_nonbank_share": Decimal("0.011"),
        "mutual_funds_share": Decimal("0"),
        "household_deposit_gdp": Decimal("1.70"),
        "deposit_demand_share": Decimal("0.72"),
        "deposit_time_share": Decimal("0.28"),
        "deposit_beta": Decimal("0.40"),
        "deposit_beta_label": "realized posted-rate beta, megabanks, 2024-26 episode",
        "tdc_created_deposit_rate": Decimal("0.0025"),
        "mortgage_stock_gdp": Decimal("225") / Decimal("662.8"),
        "floating_mortgage_share": Decimal("0.78"),
        "household_debt_gdp": Decimal("392") / Decimal("662.8"),
        "mpc_low": Decimal("0.10"),
        "mpc_base": Decimal("0.15"),
        "mpc_high": Decimal("0.20"),
    },
}


BRAZIL_CONFIG: dict[str, object] = {
    "state_id": BRAZIL_STATE_ID,
    "label": BRAZIL_LABEL,
    "dpmfi_gdp": Decimal("0.61"),
    "dpmfi_brl_bn": Decimal("7845"),
    "lft_share": Decimal("0.5117"),
    "fixed_share": Decimal("0.217"),
    "ipca_share": Decimal("0.271"),
    "fx_share": Decimal("0.0005"),
    "matures_12m_share": Decimal("0.1980"),
    "avg_maturity_years": Decimal("3.98"),
    "holder_financial_institutions": Decimal("0.318"),
    "holder_pensions": Decimal("0.235"),
    "holder_investment_funds": Decimal("0.213"),
    "holder_nonresidents": Decimal("0.098"),
    "holder_insurers": Decimal("0.038"),
    "holder_government": Decimal("0.029"),
    "funds_floating_share": Decimal("0.756"),
    "nonresidents_fixed_share": Decimal("0.753"),
    "pensions_ipca_share": Decimal("0.524"),
    "tesouro_direto_brl_bn": Decimal("213.2"),
    "tesouro_direto_selic_share": Decimal("0.372"),
    "poupanca_brl_bn": Decimal("1005"),
    "private_credit_gdp": Decimal("0.551"),
    "free_credit_share": Decimal("0.58"),
    "earmarked_credit_share": Decimal("0.42"),
    "free_pass_through": Decimal("1.0"),
    "earmarked_pass_through": Decimal("0.2"),
    "weighted_credit_pass_through": Decimal("0.67"),
    "poupanca_beta": Decimal("0"),
    "cdi_beta": Decimal("1.0"),
    "spendout_low": Decimal("0.10"),
    "spendout_base": Decimal("0.20"),
    "spendout_high": Decimal("0.35"),
}


def build_illustrative_states(
    pack_dir: Path = PACK_DIR,
    *,
    output_root: Path = OUTPUT_DIR,
    include_byte_assertions: bool = False,
) -> IllustrativeStateResult:
    """Build the quarantined decade/Japan/pure-fiscal exhibit tables."""

    with localcontext() as context:
        context.prec = 28
        state_rows: list[dict[str, str]] = []
        input_rows: list[dict[str, str]] = []
        lineage_rows: list[dict[str, str]] = []
        channel_rows: list[dict[str, str]] = []
        legacy_state_rows: list[dict[str, str]] = []

        for state_id, legacy_config in LEGACY_DECADE_CONFIGS.items():
            legacy_pack_path, _ = _decade_pack(
                pack_dir,
                output_root / "legacy_packs" / state_id,
                state_id,
                legacy_config,
            )
            legacy_state_rows.append(
                _measure_state(
                    legacy_pack_path,
                    output_root / "legacy_measurements",
                    state_id,
                    f"{DECADE_LABEL};legacy_pre_upgrade",
                )
            )

        for state_id, config in DECADE_CONFIGS.items():
            pack_path, state_inputs = _decade_pack(pack_dir, output_root / "packs" / state_id, state_id, config)
            measurement = _measure_state(pack_path, output_root, state_id, config["claim_grade_label"])
            state_rows.append(measurement)
            input_rows.extend(state_inputs)
            lineage_rows.append(
                _lineage_row(
                    "out_decade_emergence_series.RW_ratio",
                    str(output_root / "measurements" / state_id / "out_ratewall_rollup.csv"),
                    f"{state_id} measured from memo aggregates wired into scenario-local opening pack",
                )
            )
            channel_rows.extend(_decade_channel_rows(state_id, config))

        japan_rows: list[dict[str, str]] = []
        for state_id, japan_config in JAPAN_CONFIGS.items():
            japan_pack, japan_inputs = _japan_pack(pack_dir, output_root / "packs" / state_id, japan_config)
            japan_measurement = _measure_state(
                japan_pack,
                output_root,
                state_id,
                str(japan_config["label"]),
            )
            japan_rows.append(japan_measurement)
            input_rows.extend(japan_inputs)
            lineage_rows.append(
                _lineage_row(
                    f"out_japan_comparison.{state_id}_RW_ratio",
                    str(output_root / "measurements" / state_id / "out_ratewall_rollup.csv"),
                    f"{state_id} measured from {JAPAN_CALIBRATION_LABEL} scenario-local calibrated pack",
                )
            )

        brazil_pack, brazil_inputs = _brazil_pack(pack_dir, output_root / "packs" / BRAZIL_STATE_ID, BRAZIL_CONFIG)
        brazil_measurement = _measure_state(
            brazil_pack,
            output_root,
            BRAZIL_STATE_ID,
            str(BRAZIL_CONFIG["label"]),
        )
        input_rows.extend(brazil_inputs)
        lineage_rows.append(
            _lineage_row(
                f"out_brazil_comparison.{BRAZIL_STATE_ID}_RW_ratio",
                str(output_root / "measurements" / BRAZIL_STATE_ID / "out_ratewall_rollup.csv"),
                f"{BRAZIL_STATE_ID} measured from {BRAZIL_FACT_PACK_PATH} Section A scenario-local calibrated pack",
            )
        )

        fiscal_zero_pack, fiscal_zero_inputs = _pure_fiscal_pack(
            pack_dir,
            output_root / "packs" / "pure_fiscal_reg_q",
            state_id="pure_fiscal_reg_q",
            restore_today_betas=False,
        )
        fiscal_today_pack, fiscal_today_inputs = _pure_fiscal_pack(
            pack_dir,
            output_root / "packs" / "pure_fiscal_today_betas",
            state_id="pure_fiscal_today_betas",
            restore_today_betas=True,
        )
        fiscal_zero = _measure_state(fiscal_zero_pack, output_root, "pure_fiscal_reg_q", FIAT_LABEL)
        fiscal_today = _measure_state(fiscal_today_pack, output_root, "pure_fiscal_today_betas", FIAT_LABEL)
        input_rows.extend(fiscal_zero_inputs)
        input_rows.extend(fiscal_today_inputs)
        lineage_rows.extend(
            [
                _lineage_row(
                    "out_pure_fiscal_two_engines.zero_deposit_beta_RW_ratio",
                    str(output_root / "measurements" / "pure_fiscal_reg_q" / "out_ratewall_rollup.csv"),
                    "fiat 1946-scale bill-heavy household-held debt pack with Reg-Q zero deposit pass-through",
                ),
                _lineage_row(
                    "out_pure_fiscal_two_engines.today_beta_RW_ratio",
                    str(output_root / "measurements" / "pure_fiscal_today_betas" / "out_ratewall_rollup.csv"),
                    "same pure-fiscal pack with current deposit pass-through restored",
                ),
            ]
        )

        us_default = _us_default_row(pack_dir)
        decade_series = _decade_series_rows(state_rows, us_default)
        old_vs_new = _decade_old_vs_new_rows(legacy_state_rows, state_rows)
        japan_comparison = _japan_comparison_rows(japan_rows, us_default)
        brazil_comparison = _brazil_comparison_rows(brazil_measurement, japan_comparison, us_default)
        fiscal_comparison = _pure_fiscal_rows(fiscal_zero, fiscal_today)
        spectrum = _grand_spectrum_rows(
            state_rows,
            japan_rows,
            brazil_measurement,
            fiscal_zero,
            fiscal_today,
            us_default,
            slr_spectrum_path=SLR_SPECTRUM_PATH,
        )
        lineage_rows.extend(_base_lineage_rows(output_root))
        settlement_map = settlement_class_map_rows(pack_dir)
        tables = {
            "out_illustrative_state_inputs": input_rows,
            "out_decade_emergence_series": decade_series,
            "out_decade_emergence_old_vs_new": old_vs_new,
            "out_channel_existence": channel_rows,
            "out_japan_comparison": japan_comparison,
            "out_pure_fiscal_two_engines": fiscal_comparison,
            "out_grand_spectrum": spectrum,
            "out_shape_check": _shape_check_rows(decade_series, japan_comparison, fiscal_comparison, brazil_comparison),
            "out_lineage": lineage_rows,
            "out_disposition": _disposition_rows(),
            "out_historical_upgrade_disposition": historical_upgrade_disposition_rows(HISTORICAL_UPGRADE_PACK_DIR),
            "out_historical_bank_perimeter": historical_bank_perimeter_rows(HISTORICAL_UPGRADE_PACK_DIR),
            "out_settlement_class_map": settlement_map,
            "out_settlement_class_invariant": settlement_class_invariant_rows(
                pack_dir, settlement_map
            ),
            "out_brazil_slot_table": _brazil_slot_rows(BRAZIL_CONFIG),
            "out_brazil_comparison": brazil_comparison,
            "out_brazil_absent_with_reason": _brazil_absent_with_reason_rows(),
        }
        if include_byte_assertions:
            tables["out_byte_stability_assert"] = _byte_assertion_rows()
        return IllustrativeStateResult(tables=tables)


def write_illustrative_state_outputs(
    result: IllustrativeStateResult,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_illustrative_state_report(
    result: IllustrativeStateResult,
    output_path: Path = REPORT_PATH,
) -> Path:
    lines = [
        "# RWTAM illustrative states exhibit pack",
        "",
        "Date: 2026-07-03.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: final-deliverable illustrative exhibits only. Decade rows are semi-evidence-grade illustrations; fiat rows are hypothetical shape-only illustrations. No headline or golden change.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
    ]
    for row in result.rows("out_disposition"):
        lines.append(f"| {row['item']} | {row['disposition']} |")
    lines.extend(_markdown_table("Historical Emergence Series", result.rows("out_decade_emergence_series")))
    lines.extend(_markdown_table("Old Vs New Decade RWs", result.rows("out_decade_emergence_old_vs_new")))
    lines.extend(_markdown_table("Decade Channel Existence", result.rows("out_channel_existence"), max_rows=80))
    lines.extend(_markdown_table("Historical Upgrade Dispositions", result.rows("out_historical_upgrade_disposition"), max_rows=80))
    lines.extend(_markdown_table("Bank Perimeter", result.rows("out_historical_bank_perimeter"), max_rows=80))
    lines.extend(_markdown_table("Settlement Class Map", result.rows("out_settlement_class_map"), max_rows=80))
    lines.extend(_markdown_table("Settlement Class Invariant", result.rows("out_settlement_class_invariant")))
    lines.extend(_markdown_table("Japan Comparison", result.rows("out_japan_comparison")))
    lines.extend(_markdown_table("Brazil Slot Table", result.rows("out_brazil_slot_table"), max_rows=80))
    lines.extend(_markdown_table("Brazil Comparison", result.rows("out_brazil_comparison"), max_rows=20))
    lines.extend(_markdown_table("Brazil Absent With Reason", result.rows("out_brazil_absent_with_reason"), max_rows=80))
    lines.extend(_markdown_table("Pure Fiscal Two Engines", result.rows("out_pure_fiscal_two_engines")))
    lines.extend(_markdown_table("Grand Spectrum", result.rows("out_grand_spectrum"), max_rows=80))
    lines.extend(_markdown_table("Shape Check", result.rows("out_shape_check")))
    if "out_byte_stability_assert" in result.tables:
        lines.extend(_markdown_table("Byte Stability Assert", result.rows("out_byte_stability_assert")))
    lines.extend(_markdown_table("Lineage", result.rows("out_lineage"), max_rows=80))
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Italy early 1990s is the real-world approximation for the pure-fiscal configuration: BOT bills, household-held debt, and debt above 100% of GDP. It remains a note, not a measured row.",
            "- US history did not align the pure-fiscal conditions: debt was large when rates were pegged/frozen, and free-rate conditions arrived after the debt ratio had shrunk.",
            "- S4/S4b endpoints are cited from `var/rwtam/scenarios/slr_conditions/out_slr_spectrum.csv`; they are not rebuilt here.",
            "",
            "## Output Locations",
            "",
            f"- `{OUTPUT_DIR / 'out_illustrative_state_inputs.csv'}`",
            f"- `{OUTPUT_DIR / 'out_decade_emergence_series.csv'}`",
            f"- `{OUTPUT_DIR / 'out_decade_emergence_old_vs_new.csv'}`",
            f"- `{OUTPUT_DIR / 'out_historical_upgrade_disposition.csv'}`",
            f"- `{OUTPUT_DIR / 'out_historical_bank_perimeter.csv'}`",
            f"- `{OUTPUT_DIR / 'out_settlement_class_map.csv'}`",
            f"- `{OUTPUT_DIR / 'out_japan_comparison.csv'}`",
            f"- `{OUTPUT_DIR / 'out_brazil_slot_table.csv'}`",
            f"- `{OUTPUT_DIR / 'out_brazil_comparison.csv'}`",
            f"- `{OUTPUT_DIR / 'out_brazil_absent_with_reason.csv'}`",
            f"- `{OUTPUT_DIR / 'out_pure_fiscal_two_engines.csv'}`",
            f"- `{OUTPUT_DIR / 'out_grand_spectrum.csv'}`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def write_data_upgrade_report(
    result: IllustrativeStateResult,
    output_path: Path = DATA_UPGRADE_REPORT_PATH,
) -> Path:
    lines = [
        "# RWTAM data-upgrades wire report",
        "",
        "Date: 2026-07-03.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: scenario-local data upgrade wire only. Headline/goldens remain untouched.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
        "| historical pack copy | copied path-preserving to `configs/rwtam/packs/historical_upgrades/`; README neutralized; CSV values unchanged |",
        "| 1985 bill share | wired exact `28.247752685492127%` from `historical_upgrades.csv` |",
        "| 2005 foreign holder share | wired exact `43.212094737786494%` from `historical_upgrades.csv` |",
        "| 1985 household direct level | wired exact `282.24bn` from `historical_upgrades.csv` |",
        "| holder/split/mortgage/remittance rows | emitted dispositions for every delivered delta row; grades now A/B except retained private-depository proxy caveat |",
        "| allocation exact pulls | emitted F.100/L.103/NCBCEBA027N/MMF holder-share rows as `grade_A_exact_pull` allocation evidence |",
        "| bank perimeter | emitted `tdcest_tier0_three_sector` default and `banks_incl_credit_unions` mode-B-confirmed variant; historical private-depository proxy retained as Grade-B contrast |",
        "| settlement-class map | emitted `out_settlement_class_map.csv`; line-mapping residual is mapped, and `other_residual` is zero |",
        "| headline/goldens | not changed |",
    ]
    lines.extend(_markdown_table("Old Vs New Decade RWs", result.rows("out_decade_emergence_old_vs_new")))
    lines.extend(_markdown_table("Monotonicity / Shape Checks", result.rows("out_shape_check")))
    lines.extend(_markdown_table("Historical Upgrade Dispositions", result.rows("out_historical_upgrade_disposition"), max_rows=120))
    lines.extend(_markdown_table("Bank Perimeter", result.rows("out_historical_bank_perimeter"), max_rows=80))
    lines.extend(_markdown_table("Settlement Class Map", result.rows("out_settlement_class_map"), max_rows=80))
    lines.extend(_markdown_table("Settlement Class Invariant", result.rows("out_settlement_class_invariant")))
    lines.extend(
        [
            "",
            "## Output Locations",
            "",
            f"- `{OUTPUT_DIR / 'out_decade_emergence_old_vs_new.csv'}`",
            f"- `{OUTPUT_DIR / 'out_historical_upgrade_disposition.csv'}`",
            f"- `{OUTPUT_DIR / 'out_historical_bank_perimeter.csv'}`",
            f"- `{OUTPUT_DIR / 'out_settlement_class_map.csv'}`",
            f"- `{OUTPUT_DIR / 'out_settlement_class_invariant.csv'}`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _decade_pack(
    pack_dir: Path,
    out_dir: Path,
    state_id: str,
    config: dict[str, Decimal | str],
) -> tuple[Path, list[dict[str, str]]]:
    _fresh_copy(pack_dir, out_dir)
    opening = _read_csv_rows(out_dir / "opening_stocks.csv")
    debt = _d(config["debt_public_bil"])
    bills = debt * _d(config["bill_share"])
    coupons = debt - bills
    holder_shares = _holder_shares(
        fed_share=_d(config["fed_share"]),
        foreign_share=_d(config["foreign_share"]),
        household_direct_share=min(Decimal("0.60"), _d(config["hh_marketable_treasury_bil"]) / debt),
        mmf_share=(Decimal("0") if _d(config["mmf_total_bil"]) == 0 else min(Decimal("0.12"), _d(config["mmf_total_bil"]) / debt * Decimal("0.20"))),
        banks_share=_d(config.get("banks_rate_sensitive_share", Decimal("0.08"))),
        mutual_funds_share=_d(config.get("mutual_funds_rate_sensitive_share", Decimal("0.05"))),
        pensions_share=_d(config.get("pensions_rate_sensitive_share", Decimal("0.04"))),
        insurers_share=_d(config.get("insurers_rate_sensitive_share", Decimal("0.02"))),
        state_local_share=_d(config.get("state_local_rate_sensitive_share", Decimal("0.03"))),
        nonfinancial_share=_d(config.get("nonfinancial_rate_sensitive_share", Decimal("0.01"))),
        other_nonbank_share=_d(config.get("other_nonbank_rate_sensitive_share", Decimal("0.03"))),
    )
    _replace_family(opening, "treasury_bills", _amounts_from_shares(bills, holder_shares), "treasury_federal", state_id)
    _replace_family(opening, "treasury_notes_bonds_tips", _amounts_from_shares(coupons, holder_shares), "treasury_federal", state_id)
    _replace_family(opening, "reserves_iorb", {}, "federal_reserve", state_id)
    _replace_family(opening, "on_rrp_mmfs", {}, "federal_reserve", state_id)
    _replace_family(opening, "foreign_official_reverse_repos", {}, "federal_reserve", state_id)
    _replace_family(opening, "deposits_checkable", {"households": _d(config["checkable_currency_bil"])}, "banks", state_id)
    _replace_family(opening, "deposits_savings_mmda", {"households": _d(config["time_savings_bil"]) * Decimal("0.70")}, "banks", state_id)
    _replace_family(opening, "deposits_time_cds", {"households": _d(config["time_savings_bil"]) * Decimal("0.30")}, "banks", state_id)
    _replace_family(opening, "mmf_shares", {"households": _d(config["hh_mmf_bil"])}, "nonbank_finance_mmfs", state_id)
    _replace_family(opening, "mmf_short_funding_assets", {"nonbank_finance_mmfs": _d(config["mmf_total_bil"])}, "short_funding_payers", state_id)
    _replace_family(opening, "mortgages_fixed", {"banks_nonbank_finance": _d(config["mortgage_bil"]) * (Decimal("1") - _d(config["arm_share"]))}, "households", state_id)
    _replace_family(opening, "mortgages_arm", {"banks_nonbank_finance": _d(config["mortgage_bil"]) * _d(config["arm_share"])}, "households", state_id)
    _replace_family(opening, "heloc", {}, "households", state_id)
    consumer = _d(config["consumer_credit_bil"])
    _replace_family(opening, "credit_card_revolving", {"banks_nonbank_finance": consumer * Decimal("0.15")}, "households", state_id)
    _replace_family(opening, "auto_installment_debt", {"banks_nonbank_finance": consumer * Decimal("0.50")}, "households", state_id)
    _replace_family(opening, "personal_installment_debt", {"banks_nonbank_finance": consumer * Decimal("0.35")}, "households", state_id)
    _replace_family(opening, "student_loans_private", {}, "households", state_id)
    _write_opening(out_dir / "opening_stocks.csv", opening)
    _set_treasury_matrix(out_dir / "treasury_holder_matrix.csv", holder_shares, state_id)
    _set_deposit_regime(out_dir / "claim_processor_rules.csv", str(config["deposit_beta_regime"]), state_id)
    _set_tdc_created_deposit_rate(out_dir / "structural_assumptions.csv", _d(config["tdc_created_deposit_rate"]), state_id)
    _write_rows(out_dir / "fiat_illustration_inputs.csv", [{"scenario_id": state_id, "inputs": f"decade_state_from_memo_year={config['display_year']}"}])
    return out_dir, _decade_input_rows(state_id, config)


def _japan_pack(
    pack_dir: Path,
    out_dir: Path,
    config: dict[str, object],
) -> tuple[Path, list[dict[str, str]]]:
    _fresh_copy(pack_dir, out_dir)
    state_id = str(config["state_id"])
    gdp = JAPAN_SCALE_GDP
    debt = gdp * _d(config["debt_gdp"])
    holder_shares = _holder_shares(
        fed_share=_d(config["fed_share"]),
        foreign_share=_d(config["foreign_share"]),
        household_direct_share=_d(config["household_direct_share"]),
        mmf_share=_d(config["mmf_share"]),
        banks_share=_d(config["banks_share"]),
        mutual_funds_share=_d(config["mutual_funds_share"]),
        pensions_share=_d(config["pensions_share"]),
        insurers_share=_d(config["insurers_share"]),
        state_local_share=_d(config["state_local_share"]),
        nonfinancial_share=_d(config["nonfinancial_share"]),
        other_nonbank_share=_d(config["other_nonbank_share"]),
    )
    opening = _read_csv_rows(out_dir / "opening_stocks.csv")
    bill_share = _d(config["bill_share"])
    _replace_family(opening, "treasury_bills", _amounts_from_shares(debt * bill_share, holder_shares), "treasury_federal", state_id)
    _replace_family(opening, "treasury_notes_bonds_tips", _amounts_from_shares(debt * (Decimal("1") - bill_share), holder_shares), "treasury_federal", state_id)
    _replace_family(opening, "reserves_iorb", {}, "federal_reserve", state_id)
    _replace_family(opening, "on_rrp_mmfs", {}, "federal_reserve", state_id)
    _replace_family(opening, "foreign_official_reverse_repos", {}, "federal_reserve", state_id)
    household_deposits = gdp * _d(config["household_deposit_gdp"])
    _replace_family(
        opening,
        "deposits_checkable",
        {"households": household_deposits * _d(config["deposit_demand_share"])},
        "banks",
        state_id,
    )
    _replace_family(opening, "deposits_savings_mmda", {}, "banks", state_id)
    _replace_family(
        opening,
        "deposits_time_cds",
        {"households": household_deposits * _d(config["deposit_time_share"])},
        "banks",
        state_id,
    )
    _replace_family(opening, "mmf_shares", {}, "nonbank_finance_mmfs", state_id)
    _replace_family(opening, "mmf_short_funding_assets", {}, "short_funding_payers", state_id)
    mortgage_stock = gdp * _d(config["mortgage_stock_gdp"])
    floating_mortgage = mortgage_stock * _d(config["floating_mortgage_share"])
    _replace_family(opening, "mortgages_fixed", {"banks_nonbank_finance": mortgage_stock - floating_mortgage}, "households", state_id)
    _replace_family(opening, "mortgages_arm", {"banks_nonbank_finance": floating_mortgage}, "households", state_id)
    _write_opening(out_dir / "opening_stocks.csv", opening)
    _set_mortgage_holder_decomposition(out_dir / "mortgage_holder_decomposition.csv", mortgage_stock, state_id)
    _set_treasury_matrix(out_dir / "treasury_holder_matrix.csv", holder_shares, state_id)
    _set_deposit_regime(out_dir / "claim_processor_rules.csv", "custom_beta", state_id, _d(config["deposit_beta"]))
    _set_tdc_created_deposit_rate(out_dir / "structural_assumptions.csv", _d(config["tdc_created_deposit_rate"]), state_id)
    _set_household_mpc_band(
        out_dir / "conversion_coefficients.csv",
        state_id,
        _d(config["mpc_low"]),
        _d(config["mpc_base"]),
        _d(config["mpc_high"]),
    )
    lineage = _japan_lineage_rows(config, debt, household_deposits, mortgage_stock)
    _write_rows(out_dir / "japan_calibration_lineage.csv", lineage)
    inputs = (
        f"{JAPAN_CALIBRATION_LABEL}:"
        f"debt_gdp={_fmt(_d(config['debt_gdp']))};"
        f"bill_share={_fmt(_d(config['bill_share']))};"
        f"central_bank_share={_fmt(_d(config['fed_share']))};"
        f"deposit_beta={_fmt(_d(config['deposit_beta']))};"
        f"household_deposits_gdp={_fmt(_d(config['household_deposit_gdp']))};"
        f"floating_mortgage_share={_fmt(_d(config['floating_mortgage_share']))}"
    )
    _write_rows(out_dir / "fiat_illustration_inputs.csv", [{"scenario_id": state_id, "inputs": inputs}])
    return out_dir, _japan_input_rows(config)


def _brazil_pack(
    pack_dir: Path,
    out_dir: Path,
    config: dict[str, object],
) -> tuple[Path, list[dict[str, str]]]:
    _fresh_copy(pack_dir, out_dir)
    state_id = str(config["state_id"])
    gdp = BRAZIL_SCALE_GDP
    debt = gdp * _d(config["dpmfi_gdp"])
    lft_stock = debt * _d(config["lft_share"])
    fixed_stock = debt * _d(config["fixed_share"])
    ipca_stock = debt * _d(config["ipca_share"])
    coupon_stock = fixed_stock + ipca_stock
    private_credit = gdp * _d(config["private_credit_gdp"])
    free_credit = private_credit * _d(config["free_credit_share"])
    earmarked_credit = private_credit * _d(config["earmarked_credit_share"])
    dpmfi_brl = _d(config["dpmfi_brl_bn"])
    scale_from_brl = debt / dpmfi_brl
    poupanca_stock = _d(config["poupanca_brl_bn"]) * scale_from_brl
    fund_wrapper_stock = dpmfi_brl * _d(config["holder_investment_funds"]) * scale_from_brl
    tesouro_direto_stock = _d(config["tesouro_direto_brl_bn"]) * scale_from_brl

    opening = _read_csv_rows(out_dir / "opening_stocks.csv")
    holder_amounts = _brazil_treasury_holder_amounts(config, debt, lft_stock, coupon_stock)
    _replace_family(opening, "treasury_bills", holder_amounts["treasury_bills"], "treasury_federal", state_id)
    _replace_family(
        opening,
        "treasury_notes_bonds_tips",
        holder_amounts["treasury_notes_bonds_tips"],
        "treasury_federal",
        state_id,
    )
    _replace_family(opening, "reserves_iorb", {}, "federal_reserve", state_id)
    _replace_family(opening, "on_rrp_mmfs", {}, "federal_reserve", state_id)
    _replace_family(opening, "foreign_official_reverse_repos", {}, "federal_reserve", state_id)
    _replace_family(opening, "deposits_checkable", {}, "banks", state_id)
    _replace_family(opening, "deposits_savings_mmda", {"households": poupanca_stock}, "banks", state_id)
    _replace_family(opening, "deposits_time_cds", {}, "banks", state_id)
    _replace_family(
        opening,
        "mmf_shares",
        {
            "households": fund_wrapper_stock * Decimal("0.75"),
            "nonfinancial_firms": fund_wrapper_stock * Decimal("0.25"),
        },
        "nonbank_finance_mmfs",
        state_id,
    )
    _replace_family(opening, "mmf_short_funding_assets", {"nonbank_finance_mmfs": fund_wrapper_stock}, "short_funding_payers", state_id)
    _replace_family(opening, "mortgages_fixed", {}, "households", state_id)
    _replace_family(opening, "mortgages_arm", {}, "households", state_id)
    _replace_family(opening, "heloc", {}, "households", state_id)
    _replace_family(opening, "credit_card_revolving", {}, "households", state_id)
    _replace_family(opening, "auto_installment_debt", {}, "households", state_id)
    _replace_family(opening, "student_loans_private", {}, "households", state_id)
    _replace_family(opening, "personal_installment_debt", {}, "households", state_id)
    _replace_family(opening, "c_and_i_depository_loans", {"banks": free_credit}, "nonfinancial_firms", state_id)
    _replace_family(opening, "syndicated_loans", {}, "nonfinancial_firms", state_id)
    _replace_family(opening, "corporate_bonds", {"banks": earmarked_credit}, "nonfinancial_firms", state_id)
    _replace_family(opening, "municipal_securities", {}, "state_local", state_id)
    _replace_family(opening, "cre_mortgages_floating", {}, "nonfinancial_firms_cre_owners", state_id)
    _replace_family(opening, "cre_mortgages_fixed", {}, "nonfinancial_firms_cre_owners", state_id)
    _write_opening(out_dir / "opening_stocks.csv", opening)

    _set_treasury_matrix_by_family(out_dir / "treasury_holder_matrix.csv", holder_amounts, state_id)
    _set_brazil_claim_rules(out_dir / "claim_processor_rules.csv", state_id)
    _set_brazil_coupon_schedule(out_dir / "tdcsim_export" / "coupon_roll_schedule.csv", coupon_stock, config)
    _set_brazil_nominal_gdp(out_dir / "structural_assumptions.csv", gdp, state_id)
    _set_household_mpc_band(
        out_dir / "conversion_coefficients.csv",
        state_id,
        _d(config["spendout_low"]),
        _d(config["spendout_base"]),
        _d(config["spendout_high"]),
    )
    lineage = _brazil_lineage_rows(
        config,
        debt=debt,
        lft_stock=lft_stock,
        fixed_stock=fixed_stock,
        ipca_stock=ipca_stock,
        private_credit=private_credit,
        free_credit=free_credit,
        earmarked_credit=earmarked_credit,
        poupanca_stock=poupanca_stock,
        fund_wrapper_stock=fund_wrapper_stock,
        tesouro_direto_stock=tesouro_direto_stock,
    )
    _write_rows(out_dir / "brazil_calibration_lineage.csv", lineage)
    inputs = (
        f"{BRAZIL_LABEL}:"
        f"dpmfi_gdp={_fmt(_d(config['dpmfi_gdp']))};"
        f"lft_share={_fmt(_d(config['lft_share']))};"
        f"fixed_share={_fmt(_d(config['fixed_share']))};"
        f"ipca_share={_fmt(_d(config['ipca_share']))};"
        f"private_credit_gdp={_fmt(_d(config['private_credit_gdp']))};"
        f"free_credit_share={_fmt(_d(config['free_credit_share']))};"
        f"earmarked_credit_share={_fmt(_d(config['earmarked_credit_share']))}"
    )
    _write_rows(out_dir / "fiat_illustration_inputs.csv", [{"scenario_id": state_id, "inputs": inputs}])
    return out_dir, _brazil_input_rows(config)


def _pure_fiscal_pack(
    pack_dir: Path,
    out_dir: Path,
    *,
    state_id: str,
    restore_today_betas: bool,
) -> tuple[Path, list[dict[str, str]]]:
    _fresh_copy(pack_dir, out_dir)
    gdp = Decimal("31500")
    debt = gdp * Decimal("1.10")
    holder_shares = _holder_shares(
        fed_share=Decimal("0.05"),
        foreign_share=Decimal("0.03"),
        household_direct_share=Decimal("0.60"),
        mmf_share=Decimal("0.02"),
        banks_share=Decimal("0.12"),
    )
    opening = _read_csv_rows(out_dir / "opening_stocks.csv")
    _replace_family(opening, "treasury_bills", _amounts_from_shares(debt * Decimal("0.50"), holder_shares), "treasury_federal", state_id)
    _replace_family(opening, "treasury_notes_bonds_tips", _amounts_from_shares(debt * Decimal("0.50"), holder_shares), "treasury_federal", state_id)
    _replace_family(opening, "reserves_iorb", {}, "federal_reserve", state_id)
    _replace_family(opening, "on_rrp_mmfs", {}, "federal_reserve", state_id)
    _replace_family(opening, "foreign_official_reverse_repos", {}, "federal_reserve", state_id)
    _write_opening(out_dir / "opening_stocks.csv", opening)
    _set_treasury_matrix(out_dir / "treasury_holder_matrix.csv", holder_shares, state_id)
    _set_deposit_regime(out_dir / "claim_processor_rules.csv", "market" if restore_today_betas else "zero_by_rule", state_id)
    _set_tdc_created_deposit_rate(out_dir / "structural_assumptions.csv", Decimal("0.035") if restore_today_betas else Decimal("0"), state_id)
    inputs = (
        "fiat_illustration_inputs:debt_gdp=110%;bill_share=50%;"
        f"household_direct_holder_share=60%;deposit_betas={'today_restored' if restore_today_betas else 'zero_reg_q'}"
    )
    _write_rows(out_dir / "fiat_illustration_inputs.csv", [{"scenario_id": state_id, "inputs": inputs}])
    return out_dir, [_input_row(state_id, "fiat_state", "state_definition", inputs, "owner_approved_hypothetical", FIAT_LABEL)]


def _measure_state(pack_path: Path, output_root: Path, state_id: str, label: str) -> dict[str, str]:
    rollup = _rollup_only(pack_path, qt_supply_stress=False, include_cumulative=False)
    out_dir = output_root / "measurements" / state_id
    out_dir.mkdir(parents=True, exist_ok=True)
    rollup_path = out_dir / "out_ratewall_rollup.csv"
    _write_rows(rollup_path, rollup)
    row = _headline(rollup, "annual")
    return {
        "experiment_id": EXPERIMENT_ID,
        "state_id": state_id,
        "RW_ratio": row["RW_ratio"],
        "N_bil": row["N_bil"],
        "D_bil": row["D_bil"],
        "build_v1_rollup_path": str(rollup_path),
        "pack_dir": str(pack_path),
        "claim_grade_label": label,
    }


def _us_default_row(pack_dir: Path) -> dict[str, str]:
    row = _headline(_rollup_only(pack_dir, qt_supply_stress=False, include_cumulative=False), "annual")
    return {
        "experiment_id": EXPERIMENT_ID,
        "state_id": "calibrated_US_2026_default",
        "RW_ratio": row["RW_ratio"],
        "N_bil": row["N_bil"],
        "D_bil": row["D_bil"],
        "build_v1_rollup_path": "cited_current_default_rollup_only_measurement",
        "pack_dir": str(pack_dir),
        "claim_grade_label": "claim_grade_default_surface;cited_default",
    }


def _decade_series_rows(state_rows: list[dict[str, str]], us_default: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    order = ["historical_1965", "historical_1985", "historical_2005"]
    by_id = {row["state_id"]: row for row in state_rows}
    for state_id in order:
        source = by_id[state_id]
        rows.append(
            {
                "series_order": str(len(rows) + 1),
                "state_id": state_id,
                "display_year": state_id.removeprefix("historical_"),
                "RW_ratio": source["RW_ratio"],
                "N_bil": source["N_bil"],
                "D_bil": source["D_bil"],
                "claim_grade_label": DECADE_LABEL,
                "caption_note": EMERGENCE_CAPTION_NOTE,
            }
        )
    rows.append(
        {
            "series_order": "4",
            "state_id": "calibrated_US_2026_default",
            "display_year": "2026",
            "RW_ratio": us_default["RW_ratio"],
            "N_bil": us_default["N_bil"],
            "D_bil": us_default["D_bil"],
            "claim_grade_label": "claim_grade_default_surface;cited_default",
            "caption_note": EMERGENCE_CAPTION_NOTE,
        }
    )
    return rows


def _decade_old_vs_new_rows(
    legacy_state_rows: list[dict[str, str]],
    upgraded_state_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    old_by_state = {row["state_id"]: row for row in legacy_state_rows}
    new_by_state = {row["state_id"]: row for row in upgraded_state_rows}
    rows: list[dict[str, str]] = []
    for state_id in ["historical_1965", "historical_1985", "historical_2005"]:
        old = old_by_state[state_id]
        new = new_by_state[state_id]
        rows.append(
            {
                "state_id": state_id,
                "display_year": state_id.removeprefix("historical_"),
                "old_RW_ratio": old["RW_ratio"],
                "new_RW_ratio": new["RW_ratio"],
                "delta_RW_ratio": _fmt(_d(new["RW_ratio"]) - _d(old["RW_ratio"])),
                "old_N_bil": old["N_bil"],
                "new_N_bil": new["N_bil"],
                "old_D_bil": old["D_bil"],
                "new_D_bil": new["D_bil"],
                "claim_grade_label": DECADE_LABEL,
                "caption_note": EMERGENCE_CAPTION_NOTE,
            }
        )
    return rows


def _japan_comparison_rows(japan_rows: list[dict[str, str]], us_default: dict[str, str]) -> list[dict[str, str]]:
    by_state = {row["state_id"]: row for row in japan_rows}
    rows = [
        {
            "comparison_id": "japan_vintage_comparison",
            "state_id": "calibrated_US_2026_default",
            "RW_ratio": us_default["RW_ratio"],
            "N_bil": us_default["N_bil"],
            "D_bil": us_default["D_bil"],
            "US_default_RW_ratio": us_default["RW_ratio"],
            "debt_gdp_ratio": "default_pack",
            "US_debt_gdp_ratio": "default_pack",
            "deposit_beta": "default_pack",
            "central_bank_holder_share": "default_pack",
            "floating_mortgage_share": "default_pack",
            "external_direction_check": "not_applicable",
            "interpretation": "US default comparison anchor",
            "claim_grade_label": us_default["claim_grade_label"],
            "caption_note": SHAPE_ONLY_CAPTION_NOTE,
        }
    ]
    for state_id in ["japan_nirp_2019", "japan_post_exit_2026"]:
        japan = by_state[state_id]
        config = JAPAN_CONFIGS[state_id]
        rows.append(
            {
                "comparison_id": "japan_vintage_comparison",
                "state_id": state_id,
                "RW_ratio": japan["RW_ratio"],
                "N_bil": japan["N_bil"],
                "D_bil": japan["D_bil"],
                "US_default_RW_ratio": us_default["RW_ratio"],
                "debt_gdp_ratio": _fmt(_d(config["debt_gdp"])),
                "US_debt_gdp_ratio": "default_pack",
                "deposit_beta": _fmt(_d(config["deposit_beta"])),
                "central_bank_holder_share": _fmt(_d(config["fed_share"])),
                "floating_mortgage_share": _fmt(_d(config["floating_mortgage_share"])),
                "external_direction_check": "Bloomberg Dec-2025 net +$5bn/yr households; direction_check_only",
                "interpretation": "vintage_dependent_wall_mechanism;post_exit_relation_engine_pinned_not_targeted",
                "claim_grade_label": str(config["label"]),
                "caption_note": SHAPE_ONLY_CAPTION_NOTE,
            }
        )
    return rows


def _brazil_comparison_rows(
    brazil: dict[str, str],
    japan_comparison: list[dict[str, str]],
    us_default: dict[str, str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    memo = (
        "direction_check: Selic 15%, public interest bill 8.48% GDP, "
        "GDP +2.3-2.5%, unemployment 5.2%; literature debate: Barboza, "
        "Serrano-Summa, Lara Resende/LFT-jabuticaba line, IMF 2025"
    )
    for source in japan_comparison:
        rows.append(
            {
                "comparison_id": "maximal_wall_brazil_comparison",
                "state_id": source["state_id"],
                "RW_year1": source["RW_ratio"],
                "N_bil": source["N_bil"],
                "D_bil": source["D_bil"],
                "floating_sovereign_share": "default_pack" if source["state_id"] == "calibrated_US_2026_default" else "not_reported_in_japan_table",
                "deposit_beta": source["deposit_beta"],
                "earmarked_credit_share": "default_pack",
                "foreign_leak": "default_pack",
                "memo": "comparison anchor",
                "claim_grade_label": source["claim_grade_label"],
                "caption_note": SHAPE_ONLY_CAPTION_NOTE,
            }
        )
    rows.append(
        {
            "comparison_id": "maximal_wall_brazil_comparison",
            "state_id": BRAZIL_STATE_ID,
            "RW_year1": brazil["RW_ratio"],
            "N_bil": brazil["N_bil"],
            "D_bil": brazil["D_bil"],
            "floating_sovereign_share": _fmt(_d(BRAZIL_CONFIG["lft_share"])),
            "deposit_beta": "poupanca=0;CDI_DI_wrapper=1",
            "earmarked_credit_share": _fmt(_d(BRAZIL_CONFIG["earmarked_credit_share"])),
            "foreign_leak": _fmt(_d(BRAZIL_CONFIG["holder_nonresidents"])),
            "memo": memo,
            "claim_grade_label": str(BRAZIL_CONFIG["label"]),
            "caption_note": SHAPE_ONLY_CAPTION_NOTE,
        }
    )
    return rows


def _pure_fiscal_rows(fiscal_zero: dict[str, str], fiscal_today: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "comparison_id": "pure_fiscal_wall_zero_deposit_beta",
            "state_id": fiscal_zero["state_id"],
            "RW_ratio": fiscal_zero["RW_ratio"],
            "N_bil": fiscal_zero["N_bil"],
            "D_bil": fiscal_zero["D_bil"],
            "deposit_pass_through_engine": "off_reg_q_zero",
            "fiscal_interest_engine": "on_bill_heavy_household_held_debt",
            "claim_grade_label": FIAT_LABEL,
            "caption_note": SHAPE_ONLY_CAPTION_NOTE,
        },
        {
            "comparison_id": "pure_fiscal_wall_today_betas",
            "state_id": fiscal_today["state_id"],
            "RW_ratio": fiscal_today["RW_ratio"],
            "N_bil": fiscal_today["N_bil"],
            "D_bil": fiscal_today["D_bil"],
            "deposit_pass_through_engine": "on_today_betas",
            "fiscal_interest_engine": "on_bill_heavy_household_held_debt",
            "claim_grade_label": FIAT_LABEL,
            "caption_note": SHAPE_ONLY_CAPTION_NOTE,
        },
        {
            "comparison_id": "real_world_approximation_note",
            "state_id": "italy_early_1990s_note",
            "RW_ratio": "",
            "N_bil": "",
            "D_bil": "",
            "deposit_pass_through_engine": "not_measured",
            "fiscal_interest_engine": "BOT_bills_household_held_debt_over_100pct_GDP",
            "claim_grade_label": "historical_analogy_note_not_measured",
            "caption_note": SHAPE_ONLY_CAPTION_NOTE,
        },
    ]


def _shape_check_rows(
    decade_series: list[dict[str, str]],
    japan_comparison: list[dict[str, str]],
    fiscal_comparison: list[dict[str, str]],
    brazil_comparison: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    by_state = {row["state_id"]: row for row in decade_series}
    pre_2008 = [
        _d(by_state["historical_1965"]["RW_ratio"]),
        _d(by_state["historical_1985"]["RW_ratio"]),
        _d(by_state["historical_2005"]["RW_ratio"]),
    ]
    us = _d(by_state["calibrated_US_2026_default"]["RW_ratio"])
    japan_by_state = {row["state_id"]: row for row in japan_comparison}
    japan_nirp = japan_by_state["japan_nirp_2019"]
    japan_post_exit = japan_by_state["japan_post_exit_2026"]
    fiscal = {row["state_id"]: row for row in fiscal_comparison if row["RW_ratio"]}
    monotone = pre_2008[0] <= pre_2008[1] <= pre_2008[2]
    post_exit_relation = (
        "above_us"
        if _d(japan_post_exit["RW_ratio"]) > us
        else "equal_to_us"
        if _d(japan_post_exit["RW_ratio"]) == us
        else "below_us"
    )
    rows = [
        {
            "check_id": "E2_pre_2008_near_zero_band",
            "status": "pass" if max(pre_2008) < Decimal("0.01") else "fail",
            "observed": f"1965={by_state['historical_1965']['RW_ratio']};1985={by_state['historical_1985']['RW_ratio']};2005={by_state['historical_2005']['RW_ratio']}",
            "check_against": "all pre-2008 illustrative states below 0.01",
            "claim_grade_label": DECADE_LABEL,
            "caption_note": EMERGENCE_CAPTION_NOTE,
        },
        {
            "check_id": "E2_strict_decade_monotonicity",
            "status": "pass" if monotone else "caveat",
            "observed": f"1965={by_state['historical_1965']['RW_ratio']};1985={by_state['historical_1985']['RW_ratio']};2005={by_state['historical_2005']['RW_ratio']}",
            "check_against": "expected visual shape near-zero to small to moderate to 2026",
            "claim_grade_label": f"{DECADE_LABEL};strict_internal_order_reported_not_targeted",
            "caption_note": EMERGENCE_CAPTION_NOTE,
        },
        {
            "check_id": "E2_2026_step_up",
            "status": "pass" if us > max(pre_2008) else "fail",
            "observed": f"2026={by_state['calibrated_US_2026_default']['RW_ratio']};max_pre_2008={_fmt(max(pre_2008))}",
            "check_against": "2026 calibrated default materially above pre-2008 illustrative decade states",
            "claim_grade_label": "claim_grade_default_surface;cited_default",
            "caption_note": EMERGENCE_CAPTION_NOTE,
        },
        {
            "check_id": "E3_japan_nirp_below_us_despite_debt",
            "status": "pass" if _d(japan_nirp["RW_ratio"]) < _d(japan_nirp["US_default_RW_ratio"]) else "fail",
            "observed": f"japan_nirp_2019={japan_nirp['RW_ratio']};US={japan_nirp['US_default_RW_ratio']};debt_gdp={japan_nirp['debt_gdp_ratio']}",
            "check_against": "NIRP vintage remains below US default despite high debt/GDP",
            "claim_grade_label": JAPAN_NIRP_LABEL,
            "caption_note": SHAPE_ONLY_CAPTION_NOTE,
        },
        {
            "check_id": "E3_japan_post_exit_relation_to_us_regression_pin",
            "status": "pass",
            "observed": f"japan_post_exit_2026={japan_post_exit['RW_ratio']};US={japan_post_exit['US_default_RW_ratio']};relation={post_exit_relation}",
            "check_against": "engine-computed post-exit relation; sign pinned after computation, not targeted",
            "claim_grade_label": JAPAN_POST_EXIT_LABEL,
            "caption_note": SHAPE_ONLY_CAPTION_NOTE,
        },
        {
            "check_id": "E5_zero_beta_fiscal_wall_substantial",
            "status": "pass" if _d(fiscal["pure_fiscal_reg_q"]["RW_ratio"]) > us else "fail",
            "observed": f"zero_beta={fiscal['pure_fiscal_reg_q']['RW_ratio']};US={_fmt(us)}",
            "check_against": "pure fiscal wall substantial despite zero deposit pass-through",
            "claim_grade_label": FIAT_LABEL,
            "caption_note": SHAPE_ONLY_CAPTION_NOTE,
        },
    ]
    if brazil_comparison:
        measured = [
            row for row in brazil_comparison if row["RW_year1"] and row["state_id"] != "calibrated_US_2026_default"
        ]
        brazil = next(row for row in brazil_comparison if row["state_id"] == BRAZIL_STATE_ID)
        max_peer = max(_d(row["RW_year1"]) for row in measured if row["state_id"] != BRAZIL_STATE_ID)
        rows.append(
            {
                "check_id": "E6_brazil_largest_engine_result_reported_not_targeted",
                "status": "pass" if _d(brazil["RW_year1"]) > max_peer and _d(brazil["RW_year1"]) > us else "finding_not_largest",
                "observed": f"brazil_2025={brazil['RW_year1']};US={_fmt(us)};max_non_brazil_peer={_fmt(max_peer)}",
                "check_against": "qualitative expectation only: Brazil maximal-wall configuration should be largest; do not tune if false",
                "claim_grade_label": str(BRAZIL_CONFIG["label"]),
                "caption_note": SHAPE_ONLY_CAPTION_NOTE,
            }
        )
    return rows


def _grand_spectrum_rows(
    state_rows: list[dict[str, str]],
    japan_rows: list[dict[str, str]],
    brazil_row: dict[str, str],
    fiscal_zero: dict[str, str],
    fiscal_today: dict[str, str],
    us_default: dict[str, str],
    *,
    slr_spectrum_path: Path,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    slr_rows = {row["state_id"]: row for row in _read_csv_rows(slr_spectrum_path)}
    for state_id, exhibit_id, source_path in [
        ("textbook_limit_fiat_state", "E1_S4_textbook_endpoint", str(slr_spectrum_path)),
        ("hypothetical_ratio_one_illustration", "E1_S4b_ratio_one_endpoint", str(slr_spectrum_path)),
    ]:
        row = slr_rows[state_id]
        rows.append(
            _spectrum_row(
                exhibit_id,
                state_id,
                row["RW_ratio"],
                row.get("N_bil", ""),
                row.get("D_bil", ""),
                source_path,
                row["claim_grade_label"] + ";cited_not_rebuilt",
            )
        )
    for row in state_rows:
        rows.append(_spectrum_row("E2_historical_emergence", row["state_id"], row["RW_ratio"], row["N_bil"], row["D_bil"], row["build_v1_rollup_path"], DECADE_LABEL))
    for japan in japan_rows:
        rows.append(_spectrum_row("E3_not_debt_gdp", japan["state_id"], japan["RW_ratio"], japan["N_bil"], japan["D_bil"], japan["build_v1_rollup_path"], japan["claim_grade_label"]))
    rows.append(
        _spectrum_row(
            "E6_brazil_maximal_wall",
            brazil_row["state_id"],
            brazil_row["RW_ratio"],
            brazil_row["N_bil"],
            brazil_row["D_bil"],
            brazil_row["build_v1_rollup_path"],
            brazil_row["claim_grade_label"],
        )
    )
    rows.append(_spectrum_row("E5_pure_fiscal_zero_beta", fiscal_zero["state_id"], fiscal_zero["RW_ratio"], fiscal_zero["N_bil"], fiscal_zero["D_bil"], fiscal_zero["build_v1_rollup_path"], FIAT_LABEL))
    rows.append(_spectrum_row("E5_pure_fiscal_both_engines", fiscal_today["state_id"], fiscal_today["RW_ratio"], fiscal_today["N_bil"], fiscal_today["D_bil"], fiscal_today["build_v1_rollup_path"], FIAT_LABEL))
    rows.append(_spectrum_row("E1_calibrated_US_default", us_default["state_id"], us_default["RW_ratio"], us_default["N_bil"], us_default["D_bil"], us_default["build_v1_rollup_path"], us_default["claim_grade_label"]))
    return rows


def _spectrum_row(
    exhibit_id: str,
    state_id: str,
    rw: str,
    n: str,
    d: str,
    source_path: str,
    label: str,
) -> dict[str, str]:
    if exhibit_id == "E2_historical_emergence" or state_id == "calibrated_US_2026_default":
        caption = EMERGENCE_CAPTION_NOTE
    else:
        caption = SHAPE_ONLY_CAPTION_NOTE
    return {
        "experiment_id": EXPERIMENT_ID,
        "exhibit_id": exhibit_id,
        "state_id": state_id,
        "RW_ratio": rw,
        "N_bil": n,
        "D_bil": d,
        "source_path": source_path,
        "claim_grade_label": label,
        "caption_note": caption,
    }


def _holder_shares(
    *,
    fed_share: Decimal,
    foreign_share: Decimal,
    household_direct_share: Decimal,
    mmf_share: Decimal,
    banks_share: Decimal = Decimal("0.08"),
    mutual_funds_share: Decimal = Decimal("0.05"),
    pensions_share: Decimal = Decimal("0.04"),
    insurers_share: Decimal = Decimal("0.02"),
    state_local_share: Decimal = Decimal("0.03"),
    nonfinancial_share: Decimal = Decimal("0.01"),
    other_nonbank_share: Decimal = Decimal("0.03"),
) -> dict[str, Decimal]:
    base = {
        "federal_reserve": fed_share,
        "rest_of_world": foreign_share,
        "households_direct": household_direct_share,
        "mmfs": mmf_share,
        "banks": banks_share,
        "mutual_funds_etfs": mutual_funds_share,
        "pensions": pensions_share,
        "insurers": insurers_share,
        "state_local": state_local_share,
        "nonfinancial_firms": nonfinancial_share,
        "other_nonbank_finance": other_nonbank_share,
    }
    total = sum(base.values(), Decimal("0"))
    base["unallocated_line_mapping_residual"] = max(Decimal("0"), Decimal("1") - total)
    if total > 1:
        scale = Decimal("1") / total
        return {holder: share * scale for holder, share in base.items() if holder != "unallocated_line_mapping_residual"} | {"unallocated_line_mapping_residual": Decimal("0")}
    return base


def _amounts_from_shares(total: Decimal, shares: dict[str, Decimal]) -> dict[str, Decimal]:
    return {holder: total * share for holder, share in shares.items() if share != 0}


def _replace_family(
    rows: list[dict[str, str]],
    family: str,
    holder_amounts: dict[str, Decimal],
    issuer: str,
    state_id: str,
) -> None:
    rows[:] = [row for row in rows if row["instrument_family"] != family]
    emitted = False
    items = holder_amounts.items() if holder_amounts else [("unallocated_line_mapping_residual", Decimal("0"))]
    for holder, amount in items:
        if amount == 0:
            holder = "unallocated_line_mapping_residual"
        rows.append(
            {
                "parameter_id": "illustrative_state_opening_stock",
                "cell_or_sector": f"holder={holder}|issuer={issuer}",
                "instrument_family": family,
                "low": _fmt(amount),
                "base": _fmt(amount),
                "high": _fmt(amount),
                "units": "$bn_current",
                "source_id": f"{EXPERIMENT_ID}:{state_id}",
                "input_basis_label": "illustrative_state_scenario_local_opening_stock",
                "rationale": f"{state_id} quarantined illustrative-state opening stock.",
            }
        )
        emitted = True
    if not emitted:
        raise RuntimeError(f"failed to emit opening row for {family}")


def _scale_existing_family(rows: list[dict[str, str]], family: str, scale: Decimal, state_id: str) -> None:
    for row in rows:
        if row["instrument_family"] != family:
            continue
        for band in BANDS:
            row[band] = _fmt(_d(row[band]) * scale)
        row["source_id"] = f"{row['source_id']};{EXPERIMENT_ID}:{state_id}"
        row["input_basis_label"] = f"{row['input_basis_label']};illustrative_state_scaled"


def _set_treasury_matrix(path: Path, shares: dict[str, Decimal], state_id: str) -> None:
    rows = _read_csv_rows(path)
    rows = [row for row in rows if row["instrument_family"] not in {"all_marketable_treasuries", "treasury_bills", "treasury_notes_bonds_tips"}]
    for family in ["all_marketable_treasuries", "treasury_bills", "treasury_notes_bonds_tips"]:
        for holder, share in shares.items():
            rows.append(
                {
                    "parameter_id": f"illustrative_{family}_holder_share",
                    "cell_or_sector": holder,
                    "instrument_family": family,
                    "low": _fmt(share),
                    "base": _fmt(share),
                    "high": _fmt(share),
                    "units": "share_of_treasury_debt",
                    "source_id": f"{EXPERIMENT_ID}:{state_id}",
                    "input_basis_label": "illustrative_state_holder_matrix",
                    "rationale": f"{state_id} scenario-local Treasury holder shares.",
                }
            )
    _write_rows(path, rows)


def _set_deposit_regime(
    path: Path,
    regime: str,
    state_id: str,
    explicit_beta: Decimal | None = None,
) -> None:
    rows = _read_csv_rows(path)
    deposit_rules = {"deposits_checkable", "deposits_savings_mmda", "deposits_time_cds"}
    for row in rows:
        family = row["instrument_family"]
        if family not in deposit_rules:
            continue
        if regime == "zero_by_rule":
            row["rate_rule"] = "zero"
            row["base_driver"] = ""
        elif regime == "bifurcated":
            if family == "deposits_checkable":
                row["rate_rule"] = "zero"
                row["base_driver"] = ""
            else:
                row["rate_rule"] = "private_driver"
                row["base_driver"] = ""
        elif regime == "low_beta":
            row["rate_rule"] = "driver_curve"
            row["base_driver"] = "deposits_checkable"
        elif regime == "market":
            row["rate_rule"] = "private_driver"
            row["base_driver"] = ""
        elif regime == "custom_beta":
            beta = explicit_beta if explicit_beta is not None else Decimal("0")
            row["rate_rule"] = "zero" if beta == 0 else "private_driver"
            row["base_driver"] = ""
            row["constant_level_delta"] = _fmt(beta / Decimal("100"))
        else:
            raise ValueError(f"unknown deposit regime {regime}")
        row["input_basis_label"] = f"{row['input_basis_label']};{state_id}_{regime}"
        if regime == "custom_beta":
            row["input_basis_label"] = f"{row['input_basis_label']};{JAPAN_CALIBRATION_LABEL}"
    _write_rows(path, rows)


def _set_tdc_created_deposit_rate(path: Path, rate: Decimal, state_id: str) -> None:
    rows = _read_csv_rows(path)
    for row in rows:
        row.pop(None, None)
    for row in rows:
        if row["assumption_id"] != "tdc_created_deposit_full_level_rate":
            continue
        for band in BANDS:
            row[band] = _fmt(rate)
        row["input_basis_label"] = f"{row['input_basis_label']};{state_id}_deposit_regime"
        row["rationale"] = f"Scenario-local TDC deposit income rate for {state_id}; quarantine only."
    _write_rows(path, rows)


def _set_mortgage_holder_decomposition(path: Path, mortgage_stock: Decimal, state_id: str) -> None:
    _write_rows(
        path,
        [
            {
                "parameter_id": "mortgage_holder_stock_bn",
                "holder": "banks_nonbanks_whole_loans",
                "instrument_family": "mortgage_holder_decomposition",
                "low": _fmt(mortgage_stock),
                "base": _fmt(mortgage_stock),
                "high": _fmt(mortgage_stock),
                "units": "$bn_current",
                "source_id": f"{JAPAN_CALIBRATION_LABEL}:housing_loans_225T_literature",
                "input_basis_label": f"{state_id};scenario_local_holder_decomposition;assumption_required_for_engine_closure",
                "rationale": "Japan housing-loan stock scaled from fact pack; holder split not separately sourced, so whole-loan holder closure is labeled as an engine assumption.",
            }
        ],
    )


def _set_household_mpc_band(
    path: Path,
    state_id: str,
    low: Decimal,
    base: Decimal,
    high: Decimal,
) -> None:
    rows = _read_csv_rows(path)
    for row in rows:
        if row["parameter_id"] != "annual_mps_interest_flow":
            continue
        if not row["cell_or_sector"].startswith("hh_"):
            continue
        row["low"] = _fmt(low)
        row["base"] = _fmt(base)
        row["high"] = _fmt(high)
        if state_id == BRAZIL_STATE_ID:
            row["source_id"] = f"{BRAZIL_LABEL}:spendout_assumption_band"
            row["input_basis_label"] = f"{state_id};assumption_recommended_no_brazil_interest_mpc_source"
            row["rationale"] = "Brazil fact pack found no Brazilian MPC-on-interest-income estimates; assumption-labeled spend-out band is used only for the illustrative exhibit."
        else:
            row["source_id"] = f"{JAPAN_CALIBRATION_LABEL}:transfer_mpc_0p10_0p20"
            row["input_basis_label"] = f"{state_id};assumption_recommended_japan_transfer_mpc_band"
            row["rationale"] = "Japanese transfer-MPC studies support 0.10-0.20 band; no interest-income-specific spend-out study found in fact pack."
    _write_rows(path, rows)


def _brazil_treasury_holder_amounts(
    config: dict[str, object],
    debt: Decimal,
    lft_stock: Decimal,
    coupon_stock: Decimal,
) -> dict[str, dict[str, Decimal]]:
    household_direct_share = _d(config["tesouro_direto_brl_bn"]) / _d(config["dpmfi_brl_bn"])
    holder_total_shares = {
        "banks": _d(config["holder_financial_institutions"]),
        "pensions": _d(config["holder_pensions"]),
        "mutual_funds_etfs": _d(config["holder_investment_funds"]),
        "rest_of_world": _d(config["holder_nonresidents"]),
        "insurers": _d(config["holder_insurers"]),
        "treasury_federal": _d(config["holder_government"]),
        "households_direct": household_direct_share,
    }
    holder_total_shares["unallocated_line_mapping_residual"] = max(
        Decimal("0"),
        Decimal("1") - sum(holder_total_shares.values(), Decimal("0")),
    )
    lft_shares = {
        "mutual_funds_etfs": holder_total_shares["mutual_funds_etfs"] * _d(config["funds_floating_share"]),
        "rest_of_world": holder_total_shares["rest_of_world"] * (Decimal("1") - _d(config["nonresidents_fixed_share"])),
        "households_direct": holder_total_shares["households_direct"] * _d(config["tesouro_direto_selic_share"]),
    }
    remaining_lft_share = _d(config["lft_share"]) - sum(lft_shares.values(), Decimal("0"))
    for holder in ["banks", "unallocated_line_mapping_residual", "treasury_federal", "insurers"]:
        if remaining_lft_share <= 0:
            lft_shares.setdefault(holder, Decimal("0"))
            continue
        allocation = min(holder_total_shares[holder], remaining_lft_share)
        lft_shares[holder] = allocation
        remaining_lft_share -= allocation
    for holder in holder_total_shares:
        lft_shares.setdefault(holder, Decimal("0"))
    coupon_shares = {
        holder: max(Decimal("0"), holder_total_shares[holder] - lft_shares[holder])
        for holder in holder_total_shares
    }
    return {
        "all_marketable_treasuries": {
            holder: debt * share for holder, share in holder_total_shares.items()
        },
        "treasury_bills": {
            holder: lft_stock * (Decimal("0") if _d(config["lft_share"]) == 0 else lft_shares[holder] / _d(config["lft_share"]))
            for holder in holder_total_shares
        },
        "treasury_notes_bonds_tips": {
            holder: coupon_stock * (Decimal("0") if (Decimal("1") - _d(config["lft_share"])) == 0 else coupon_shares[holder] / (Decimal("1") - _d(config["lft_share"])))
            for holder in holder_total_shares
        },
    }


def _set_treasury_matrix_by_family(
    path: Path,
    family_amounts: dict[str, dict[str, Decimal]],
    state_id: str,
) -> None:
    rows = _read_csv_rows(path)
    families = {"all_marketable_treasuries", "treasury_bills", "treasury_notes_bonds_tips"}
    rows = [row for row in rows if row["instrument_family"] not in families]
    for family in ["all_marketable_treasuries", "treasury_bills", "treasury_notes_bonds_tips"]:
        total = sum(family_amounts[family].values(), Decimal("0"))
        for holder, amount in family_amounts[family].items():
            share = Decimal("0") if total == 0 else amount / total
            rows.append(
                {
                    "parameter_id": f"illustrative_{family}_holder_share",
                    "cell_or_sector": holder,
                    "instrument_family": family,
                    "low": _fmt(share),
                    "base": _fmt(share),
                    "high": _fmt(share),
                    "units": "share_of_treasury_debt",
                    "source_id": f"{BRAZIL_LABEL}:{state_id}",
                    "input_basis_label": "brazil_rmd_2_4_holder_matrix_with_indexation_lookthrough_closure",
                    "rationale": "Brazil scenario-local family-specific holder shares; observed aggregate holder shares plus pack-provided fund/nonresident/pension indexation details, with explicit arithmetic closure.",
                }
            )
    _write_rows(path, rows)


def _set_brazil_claim_rules(path: Path, state_id: str) -> None:
    rows = _read_csv_rows(path)
    beta_by_family = {
        "deposits_checkable": Decimal("0"),
        "deposits_savings_mmda": Decimal("0"),
        "deposits_time_cds": Decimal("0"),
        "mmf_short_funding_assets": Decimal("0.01"),
        "c_and_i_depository_loans": Decimal("0.01"),
        "corporate_bonds": Decimal("0.002"),
    }
    for row in rows:
        family = row["instrument_family"]
        if family not in beta_by_family:
            continue
        beta = beta_by_family[family]
        row["rate_rule"] = "zero" if beta == 0 else "private_driver"
        row["base_driver"] = ""
        row["constant_level_delta"] = _fmt(beta)
        row["input_basis_label"] = f"{row['input_basis_label']};{state_id}_brazil_fact_pack_section_A"
        if family == "deposits_savings_mmda":
            row["basis"] = f"{row['basis']};brazil_poupanca_beta_zero_capped_rule"
        elif family == "mmf_short_funding_assets":
            row["basis"] = f"{row['basis']};brazil_cdi_di_wrapper_beta_one_stock_proxy_labeled"
        elif family == "c_and_i_depository_loans":
            row["basis"] = f"{row['basis']};brazil_free_credit_58pct_beta_one"
        elif family == "corporate_bonds":
            row["basis"] = f"{row['basis']};brazil_earmarked_credit_42pct_beta_0p2_literature_caveat"
    _write_rows(path, rows)


def _set_brazil_coupon_schedule(path: Path, coupon_stock: Decimal, config: dict[str, object]) -> None:
    rows: list[dict[str, str]] = []
    year1_share = _d(config["matures_12m_share"])
    monthly_principal = coupon_stock * year1_share / Decimal("12")
    for month_index in range(1, 13):
        month = f"2026-{month_index:02d}"
        cumulative_share = year1_share * Decimal(month_index) / Decimal("12")
        rows.append(
            {
                "month": month,
                "maturing_principal_bil": _fmt(monthly_principal),
                "cumulative_share_of_current_stock": _fmt(cumulative_share),
                "source_vintage": "Brazil RMD Aug/2025 Section A: 19.80% of DPMFi matures within 12m; spread evenly by month for engine schedule approximation",
            }
        )
    _write_rows(path, rows)


def _set_brazil_nominal_gdp(path: Path, gdp: Decimal, state_id: str) -> None:
    rows = _read_csv_rows(path)
    for row in rows:
        row.pop(None, None)
    for row in rows:
        if row["assumption_id"] == "nominal_gdp_bil":
            for band in BANDS:
                row[band] = _fmt(gdp)
            row["input_basis_label"] = f"{state_id};brazil_scale_units_from_dpmfi_61pct_gdp"
            row["rationale"] = "Illustrative Brazil state uses the existing 31500 scale with DPMFi fixed at 61% of GDP from the fact pack."
        if row["assumption_id"] == "tdc_created_deposit_full_level_rate":
            for band in BANDS:
                row[band] = "0"
            row["input_basis_label"] = f"{state_id};absent_with_reason_no_brazil_tdc_channel_in_pack"
            row["rationale"] = "Brazil exhibit pack does not authorize a TDC-created-deposit channel; kept zero in the quarantined pack copy."
    _write_rows(path, rows)


def _fresh_copy(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)


def _decade_input_rows(state_id: str, config: dict[str, Decimal | str]) -> list[dict[str, str]]:
    values = [
        ("nominal_gdp_bil", str(config["gdp_bil"]), "A" if state_id != "historical_2026" else "B", "memo bottom-line nominal GDP"),
        ("federal_debt_held_by_public_bil", str(config["debt_public_bil"]), "A", "upgraded OMB debt held by public"),
        ("debt_pct_gdp", str(config["debt_pct_gdp_verbatim"]), "B", "memo FY-basis ratio"),
        ("bill_share", str(config["bill_share_verbatim"]), "A", "upgraded Treasury bill split"),
        ("fed_holder_share", str(config["fed_share_verbatim"]), "A", "upgraded Fed holder share"),
        ("foreign_holder_share", str(config["foreign_share_verbatim"]), "A", "upgraded foreign holder share"),
        ("hh_checkable_deposits_currency_bil", str(config["checkable_currency_bil"]), "A", "memo Z.1 household checkable plus currency"),
        ("hh_time_savings_deposits_bil", str(config["time_savings_bil"]), "A", "memo Z.1 household time and savings deposits"),
        ("deposit_pass_through_regime", str(config["deposit_regime"]), "A", "memo regime history"),
        ("mmf_industry_assets_bil", str(config["mmf_total_bil"]), "A", "memo MMF industry assets"),
        ("hh_mmf_bil", str(config["hh_mmf_bil"]), "A", "memo household-held MMF line"),
        ("hh_direct_treasury_bil", str(config["hh_direct_treasury_verbatim"]), "B", "upgraded household direct Treasuries"),
        ("hh_home_mortgage_debt_bil", str(config["mortgage_bil"]), "A", "upgraded household mortgage scale"),
        ("consumer_credit_bil", str(config["consumer_credit_verbatim"]), "A" if state_id != "historical_2005" else "B", "memo consumer credit"),
        ("iorb", "none (0%) [A]", "A", "memo IORB absent in all three decade states"),
    ]
    return [_input_row(state_id, "decade_state", item, value, grade, DECADE_LABEL, note) for item, value, grade, note in values]


def _japan_input_rows(config: dict[str, object]) -> list[dict[str, str]]:
    state_id = str(config["state_id"])
    label = str(config["label"])
    values = [
        ("nominal_gdp_scale", f"{_fmt(JAPAN_SCALE_GDP)} shape units; sourced ratio uses JPY 662.8T GDP", "observed", "Cabinet Office via fact pack; scale follows existing illustrative-state unit convention"),
        ("marketable_jgb_tbill_stock_gdp", f"{_fmt(_d(config['debt_gdp']))} GDP", "observed", "MOF holdings01 JGB+T-bill stock approximately 174% GDP"),
        ("bill_share", _fmt(_d(config["bill_share"])), "observed", "MOF holdings01: 136.3 / 1150.1"),
        ("central_bank_holder_share", _fmt(_d(config["fed_share"])), "observed", str(config["fed_share_label"])),
        ("banks_holder_share", _fmt(_d(config["banks_share"])), "observed", "MOF end-Mar-2026 depository corps share"),
        ("insurers_holder_share", _fmt(_d(config["insurers_share"])), "observed", "MOF end-Mar-2026 insurers share"),
        ("pensions_holder_share", _fmt(_d(config["pensions_share"])), "observed", "MOF pension funds plus public pensions"),
        ("household_direct_holder_share", _fmt(_d(config["household_direct_share"])), "observed", "JGB-only household direct share from fact pack"),
        ("foreign_holder_share", _fmt(_d(config["foreign_share"])), "observed", "JGB-only foreign share from fact pack"),
        ("mmf_holder_share", _fmt(_d(config["mmf_share"])), "assumption-recommended", "No separate Japanese MMF category; fact pack recommends 0"),
        ("mutual_funds_etfs_share", _fmt(_d(config["mutual_funds_share"])), "absent-with-reason", "Standalone investment-trust JGB share not sourced; folded into MOF Banks grouping"),
        ("household_deposits_gdp", _fmt(_d(config["household_deposit_gdp"])), "observed", "BOJ FoF household currency and deposits JPY 1,126T on JPY 662.8T GDP"),
        ("deposit_demand_time_split", f"{_fmt(_d(config['deposit_demand_share']))}/{_fmt(_d(config['deposit_time_share']))}", "proxy", "All-depositor ex-Japan-Post split from FSA Analytical Notes; household-only split not sourced"),
        ("deposit_beta", _fmt(_d(config["deposit_beta"])), "observed" if _d(config["deposit_beta"]) != 0 else "assumption-recommended", str(config["deposit_beta_label"])),
        ("policy_rate", str(config["policy_rate_label"]), "observed", "BOJ policy path in fact pack"),
        ("tdc_created_deposit_rate", _fmt(_d(config["tdc_created_deposit_rate"])), "observed" if _d(config["tdc_created_deposit_rate"]) != 0 else "assumption-recommended", "Fact-pack 2025 deposit-rate range is 0.002-0.003; NIRP pole keeps zero"),
        ("household_debt_total_gdp", _fmt(_d(config["household_debt_gdp"])), "observed", "BOJ FoF household borrowings JPY 392T scaled by JPY 662.8T GDP"),
        ("housing_loan_stock_gdp", _fmt(_d(config["mortgage_stock_gdp"])), "literature", "Fact pack gives housing loans approximately JPY 225T"),
        ("floating_mortgage_share", _fmt(_d(config["floating_mortgage_share"])), "literature", "Fact pack range 75-80%; config uses 0.78"),
        ("nonmortgage_household_debt_split", "absent-with-reason", "absent-with-reason", "Fact pack does not source a residual household-debt family split; not allocated into consumer-debt families"),
        ("japan_transfer_mpc_band", f"{_fmt(_d(config['mpc_low']))}-{_fmt(_d(config['mpc_high']))}", "assumption-recommended", "Transfer-MPC literature supports 0.1-0.2; no interest-income-specific spend-out study found"),
    ]
    return [_input_row(state_id, "japan_calibrated_state", item, value, confidence, label, note) for item, value, confidence, note in values]


def _japan_lineage_rows(
    config: dict[str, object],
    debt: Decimal,
    household_deposits: Decimal,
    mortgage_stock: Decimal,
) -> list[dict[str, str]]:
    state_id = str(config["state_id"])
    rows = []
    for input_item, value, confidence, note in [
        ("scaled_marketable_jgb_tbill_stock_bil", _fmt(debt), "observed", "174% GDP scaled onto 31500 illustrative units"),
        ("scaled_household_deposits_bil", _fmt(household_deposits), "observed", "170% GDP scaled onto 31500 illustrative units"),
        ("scaled_housing_loan_stock_bil", _fmt(mortgage_stock), "literature", "JPY 225T housing loans scaled by JPY 662.8T GDP"),
        ("deposit_beta_engine_delta", _fmt(_d(config["deposit_beta"]) / Decimal("100")), "observed" if _d(config["deposit_beta"]) != 0 else "assumption-recommended", "Annual rate delta for a +100bp shock written into claim_processor_rules.constant_level_delta"),
        ("external_direction_check", "Bloomberg Dec-2025 net +$5bn/yr households", "memo", "Direction check only; not used as a target or calibration input"),
    ]:
        rows.append(
            {
                "scenario_id": state_id,
                "input_item": input_item,
                "scaled_or_config_value": value,
                "source_pack": JAPAN_FACT_PACK_PATH,
                "confidence": confidence,
                "provenance_note": note,
            }
        )
    return rows


def _brazil_input_rows(config: dict[str, object]) -> list[dict[str, str]]:
    state_id = str(config["state_id"])
    label = str(config["label"])
    values = [
        ("gov_debt_stock", "DPMFi approximately 61% GDP; FPD R$8,145bn Aug/2025 and DPMFi R$7,845bn", "observed", "Tesouro RMD Aug/2025; own arithmetic in fact pack"),
        ("sovereign_lft_share", "0.5117", "observed", "RMD Table 2.3; LFT Selic-floating share"),
        ("sovereign_fixed_share", "0.217", "observed", "LTN 15.31% plus NTN-F 6.37%"),
        ("sovereign_ipca_share", "0.271", "observed", "NTN-B IPCA-linked share; engine maps to coupon ladder with absent inflation-index treatment noted"),
        ("repricing_speed_lft", "daily accrual; repricing_share=1.0; engine monthly persistent approximation", "observed", "RMD 2.1 and 3.1-3.3"),
        ("matures_12m_share", "0.1980", "observed", "RMD maturity statement; used as first-year coupon schedule for non-LFT stock"),
        ("holder_financial_institutions", "0.318", "observed", "RMD 2.4"),
        ("holder_pensions", "0.235", "observed", "RMD 2.4; pensions 52.4% IPCA"),
        ("holder_investment_funds", "0.213", "observed", "RMD 2.4; funds 75.6% floating"),
        ("holder_nonresidents", "0.098", "observed", "RMD 2.4; non-residents 75.3% fixed and near-zero conversion leak"),
        ("holder_insurers", "0.038", "observed", "RMD 2.4; absorbed insurance cell"),
        ("holder_government", "0.029", "observed", "RMD 2.4; no near-term conversion"),
        ("tesouro_direto", "R$213.2bn; 37.2% Tesouro Selic", "observed", "Tesouro/CNN Jan/2026"),
        ("poupanca_stock_beta", "R$1.005tn; beta approximately 0", "observed stocks/rules; beta values assumption-recommended", "Investidor10; MP 567/2012 capped rule"),
        ("cdi_di_fund_beta", "beta approximately 1; stock proxied from RMD investment-fund DPMFi holder stock", "assumption-recommended", "CDBs/DI funds stock not separately sourced in pack; proxy is labeled"),
        ("private_credit_stock", "55.1% GDP", "observed", "BCB Jan/2026"),
        ("credit_free_share", "0.58 at pass-through approximately 1.0", "observed/literature-with-caveat", "Free credit share from pack split; pass-through from IMF WP/25/152 search rendering"),
        ("credit_earmarked_share", "0.42 at pass-through approximately 0.2", "observed/literature-with-caveat", "Directed credit split; IMF tables unreachable"),
        ("weighted_lending_pass_through", "0.67", "literature (tables 403-blocked; coefficients from search renderings)", "Pack arithmetic"),
        ("spendout_band", "0.10/0.20/0.35", "assumption-recommended", "No Brazilian MPC-on-interest-income estimates found; band is labeled and not tuned"),
        ("natural_experiment_direction_check", "Selic 15%; interest bill 8.48% GDP; GDP +2.3-2.5%; unemployment 5.2%", "observed", "Direction-check memo context only; not a calibration target"),
    ]
    return [_input_row(state_id, "brazil_2025_state", item, value, confidence, label, note) for item, value, confidence, note in values]


def _brazil_lineage_rows(
    config: dict[str, object],
    *,
    debt: Decimal,
    lft_stock: Decimal,
    fixed_stock: Decimal,
    ipca_stock: Decimal,
    private_credit: Decimal,
    free_credit: Decimal,
    earmarked_credit: Decimal,
    poupanca_stock: Decimal,
    fund_wrapper_stock: Decimal,
    tesouro_direto_stock: Decimal,
) -> list[dict[str, str]]:
    rows = []
    for input_item, value, confidence, note in [
        ("scaled_dpmfi_stock_bil", _fmt(debt), "observed", "DPMFi 61% of illustrative GDP scale"),
        ("scaled_lft_stock_bil", _fmt(lft_stock), "observed", "51.17% LFT stock mapped to treasury_bills/full short-rate repricing approximation"),
        ("scaled_fixed_stock_bil", _fmt(fixed_stock), "observed", "21.7% fixed stock mapped to coupon ladder"),
        ("scaled_ipca_stock_bil", _fmt(ipca_stock), "observed;absent_engine_treatment", "27.1% IPCA stock mapped to coupon ladder; no inflation-indexed principal treatment in engine"),
        ("scaled_private_credit_bil", _fmt(private_credit), "observed", "55.1% GDP total private credit"),
        ("scaled_free_credit_bil", _fmt(free_credit), "observed/literature-with-caveat", "58% free credit at pass-through approximately 1"),
        ("scaled_earmarked_credit_bil", _fmt(earmarked_credit), "observed/literature-with-caveat", "42% earmarked credit at pass-through approximately 0.2"),
        ("scaled_poupanca_stock_bil", _fmt(poupanca_stock), "observed stocks/rules; beta values assumption-recommended", "R$1.005tn scaled by DPMFi-to-GDP arithmetic"),
        ("scaled_cdi_di_fund_wrapper_stock_bil", _fmt(fund_wrapper_stock), "assumption-recommended", "RMD investment-fund DPMFi holder stock used as CDI/DI wrapper proxy because standalone CDB/DI stock is absent"),
        ("scaled_tesouro_direto_stock_bil", _fmt(tesouro_direto_stock), "observed", "R$213.2bn Tesouro Direto stock scaled by DPMFi-to-GDP arithmetic"),
    ]:
        rows.append(
            {
                "scenario_id": BRAZIL_STATE_ID,
                "input_item": input_item,
                "scaled_or_config_value": value,
                "source_pack": BRAZIL_FACT_PACK_PATH,
                "confidence": confidence,
                "provenance_note": note,
            }
        )
    return rows


def _brazil_slot_rows(config: dict[str, object]) -> list[dict[str, str]]:
    state_id = str(config["state_id"])
    slots = [
        ("Gov debt stock", "DPMFi approximately 61% GDP; FPD R$8,145bn Aug/2025; DPMFi R$7,845bn", "Tesouro RMD Aug/2025; gov.br Jan/2026", "observed", "scaled to illustrative GDP"),
        ("Sovereign claim terms", "LFT 51.17%; fixed 21.7%; IPCA 27.10%; FX 0.05%", "RMD Table 2.3", "observed", "LFT mapped to treasury_bills; fixed/IPCA mapped to coupon stock"),
        ("Repricing speed", "LFT accrues Selic daily; 19.80% of DPMFi matures <=12m; avg maturity 3.98y", "RMD 2.1, 3.1-3.3", "observed", "daily reset approximated by monthly persistent engine; first-year coupon schedule uses 19.8%"),
        ("Public interest bill", "8.48% GDP 12m-to-May-2026 at Selic 15%; DPMFi avg cost 12.06%; LFT 13.07%", "BCB fiscal stats; RMD 4.1", "observed", "memo direction-check only"),
        ("Holder matrix", "financial institutions 31.8%; pensions 23.5%; investment funds 21.3%; non-residents 9.8%; insurers 3.8%; gov 2.9%", "RMD 2.4", "observed", "family-specific matrix carries fund/nonresident/pension indexation details"),
        ("HH direct", "Tesouro Direto R$213.2bn; 37.2% Tesouro Selic", "Tesouro/CNN Jan/2026", "observed", "added as households_direct holder share by DPMFi arithmetic"),
        ("Private credit drag", "total R$7.1tn approximately 55.1% GDP", "BCB Jan/2026", "observed", "split into free and earmarked credit stocks"),
        ("Earmarked split", "directed approximately 42% of total", "IMF Art IV 2025 CR 25/194; BCB", "observed", "mapped to low-pass-through credit stock"),
        ("Lending pass-through", "free approximately 1.0; earmarked approximately 0.2; weighted approximately 0.67", "IMF WP/25/152", "literature (tables 403-blocked; coefficients from search renderings)", "coefficients carried with caveat"),
        ("Deposit side", "poupanca R$1.005tn beta approximately 0; CDBs/DI funds beta approximately 1 in days", "Investidor10; MP 567/2012 rule", "observed stocks/rules; beta values assumption-recommended", "CDI/DI stock proxied from investment-fund holder stock and labeled"),
        ("Natural experiment", "Selic 15%; interest bill 8.48% GDP; GDP +2.3-2.5%; unemployment 5.2%", "BCB Copom; IBGE", "observed", "direction-check context only, not target"),
        ("Spend-out", "no Brazilian MPC-on-interest-income estimates found", "-", "assumption-recommended", "assumption band flagged prominently"),
    ]
    return [
        {
            "state_id": state_id,
            "slot": slot,
            "pack_value": value,
            "source": source,
            "confidence": confidence,
            "config_mapping_note": note,
            "claim_grade_label": str(config["label"]),
        }
        for slot, value, source, confidence, note in slots
    ]


def _brazil_absent_with_reason_rows() -> list[dict[str, str]]:
    rows = [
        ("IPCA-linked engine treatment", "no inflation-indexed principal or real-indexed coupon channel in RWTAM illustrative pack", "Mapped NTN-B/IPCA 27.1% stock to coupon ladder; metered consequence is no immediate inflation-index principal support."),
        ("IMF WP/25/152 direct tables", "tables were unreachable/403-blocked in fact pack", "Used literature-with-caveat coefficients from search renderings: free approximately 1.0, earmarked approximately 0.2."),
        ("Brazilian MPC-on-interest-income", "no Brazilian estimates found", "Used visibly assumption-labeled spend-out band; not tuned to make Brazil large."),
        ("floating share of private credit stock", "BCB open data may have it but was not sourced in the pack", "Used pack split free 58% / earmarked 42% with pass-through labels."),
        ("Dec/2025 RMD full tables", "Aug/2025 is latest verified Tesouro vintage in pack", "Configuration is calibrated to Aug/2025 Tesouro vintage."),
        ("BCB WP on LFT-share transmission", "not sourced in pack", "Literature line is kept as debate context, not as a coefficient."),
        ("standalone CDB/DI funds stock", "pack gives beta/rule but no standalone stock", "Used RMD investment-fund DPMFi holder stock as labeled CDI/DI wrapper proxy."),
    ]
    return [
        {
            "state_id": BRAZIL_STATE_ID,
            "item": item,
            "absent_reason": reason,
            "metered_consequence": consequence,
            "claim_grade_label": f"{BRAZIL_LABEL};absent_with_reason",
        }
        for item, reason, consequence in rows
    ]


def _input_row(
    state_id: str,
    exhibit_scope: str,
    item: str,
    value: str,
    grade: str,
    label: str,
    note: str = "",
) -> dict[str, str]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "state_id": state_id,
        "exhibit_scope": exhibit_scope,
        "input_item": item,
        "source_value_verbatim": value,
        "grade": grade,
        "note": note,
        "claim_grade_label": label if grade != "C" else f"{label};C_grade_visible",
    }


def _decade_channel_rows(state_id: str, config: dict[str, Decimal | str]) -> list[dict[str, str]]:
    regime = str(config["deposit_beta_regime"])
    return [
        _channel_row(state_id, "treasury_interest_to_domestic_holders", "true", "federal debt and household direct Treasury holdings present"),
        _channel_row(state_id, "deposit_pass_through", "false" if regime == "zero_by_rule" else ("partial" if regime == "bifurcated" else "true"), str(config["deposit_regime"])),
        _channel_row(state_id, "mmf_pass_through", "false" if _d(config["mmf_total_bil"]) == 0 else "true", f"MMF industry assets {config['mmf_total_bil']}bn"),
        _channel_row(state_id, "fed_iorb", "false", "IORB nonexistent before October 2008"),
        _channel_row(state_id, "fed_on_rrp", "false", "no modern ON RRP facility in the decade state"),
        _channel_row(state_id, "tdc_created_deposit_income", "false" if _d(config["tdc_created_deposit_rate"]) == 0 else ("partial" if regime == "bifurcated" else "true"), "scenario-local TDC rate follows deposit pass-through regime"),
    ]


def _channel_row(state_id: str, channel_id: str, present: str, rationale: str) -> dict[str, str]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "state_id": state_id,
        "channel_id": channel_id,
        "structurally_present": present,
        "rationale": rationale,
        "claim_grade_label": DECADE_LABEL,
    }


def _lineage_row(column: str, source: str, note: str) -> dict[str, str]:
    return {
        "deliverable_column": column,
        "source_file": source,
        "lineage_note": note,
    }


def _base_lineage_rows(output_root: Path) -> list[dict[str, str]]:
    return [
        _lineage_row("out_illustrative_state_inputs", "do/rwtam_decade_aggregates_evidence_20260703.md", "decade aggregates and grades copied into input rows; C-grade rows carry C_grade_visible label"),
        _lineage_row("out_grand_spectrum.E1_endpoints", str(SLR_SPECTRUM_PATH), "textbook and ratio-1 endpoints cited from S4/S4b output, not rebuilt"),
        _lineage_row("scenario_local_packs", str(output_root / "packs"), "all state mutations are quarantined pack copies"),
    ]


def _disposition_rows() -> list[dict[str, str]]:
    return [
        {"item": "E2_historical_emergence", "disposition": "built 1965/1985/2005 scenario-local opening packs from evidence memo aggregates; emitted emergence series through cited 2026 default"},
        {"item": "E2_channel_existence", "disposition": "emitted per-decade structural N-channel table"},
        {"item": "E3_not_debt_gdp", "disposition": "built stylized Japan fiat state and comparison row against US default"},
        {"item": "E5_pure_fiscal_wall", "disposition": "built zero-deposit-beta and today's-beta companion states plus Italy/US-history note row"},
        {"item": "S4_S4b_endpoints", "disposition": "cited existing SLR spectrum endpoint rows; not rebuilt"},
        {"item": "lineage", "disposition": "emitted mandatory lineage table covering memo inputs, scenario packs, rollup measurements, and endpoint citation"},
        {"item": "headline_goldens", "disposition": "scenario-local outputs only; byte-stability assertion emitted by script"},
    ]


def _byte_assertion_rows(paths: tuple[Path, ...] = BYTE_ASSERT_PATHS) -> list[dict[str, str]]:
    return [
        {
            "path": str(path),
            "sha256": _sha256(path) if path.exists() else "",
            "status": "present" if path.exists() else "missing",
            "claim_grade_label": "byte_stability_assertion",
        }
        for path in paths
    ]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
