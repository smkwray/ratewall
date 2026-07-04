"""Quarantined illustrative-state exhibits for RWTAS final-deliverable figures."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtas.data_upgrades import (
    HISTORICAL_UPGRADE_PACK_DIR,
    historical_bank_perimeter_rows,
    historical_upgrade_disposition_rows,
    settlement_class_invariant_rows,
    settlement_class_map_rows,
    upgraded_decade_configs,
)
from ratewall.rwtas.hysteresis import _write_opening
from ratewall.rwtas.slr_conditions import _headline, _rollup_only, _markdown_table
from ratewall.rwtas.v1 import (
    BANDS,
    CURRENT_DEFAULT_OBJECT_STAMP,
    _d,
    _fmt,
    _read_csv_rows,
    _write_rows,
)


EXPERIMENT_ID = "rwtas_illustrative_states_20260703"
OUTPUT_DIR = Path("var/rwtas/scenarios/illustrative_states")
REPORT_PATH = Path("do/rwtas_illustrative_states_report_20260703.md")
DATA_UPGRADE_REPORT_PATH = Path("do/rwtas_data_upgrades_wire_report_20260703.md")
PACK_DIR = Path("configs/rwtas/packs")
SLR_SPECTRUM_PATH = Path("var/rwtas/scenarios/slr_conditions/out_slr_spectrum.csv")
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
BYTE_ASSERT_PATHS = (
    Path("var/rwtas/v1/dose_modes/persistent_level/out_ratewall_rollup.csv"),
    Path("tests/fixtures/rwtas/golden_wave6/out_ratewall_rollup.csv"),
    Path("tests/fixtures/rwtas/golden_wave6_tax_off/out_ratewall_rollup.csv"),
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

        japan_pack, japan_inputs = _japan_pack(pack_dir, output_root / "packs" / "stylized_japan")
        japan = _measure_state(japan_pack, output_root, "stylized_japan", FIAT_LABEL)
        input_rows.extend(japan_inputs)
        lineage_rows.append(
            _lineage_row(
                "out_japan_comparison.stylized_japan_RW_ratio",
                str(output_root / "measurements" / "stylized_japan" / "out_ratewall_rollup.csv"),
                "fiat low-beta high-central-bank-holdings pack measured by standard +100bp pair",
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
        japan_comparison = _japan_comparison_rows(japan, us_default)
        fiscal_comparison = _pure_fiscal_rows(fiscal_zero, fiscal_today)
        spectrum = _grand_spectrum_rows(
            state_rows,
            japan,
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
            "out_shape_check": _shape_check_rows(decade_series, japan_comparison, fiscal_comparison),
            "out_lineage": lineage_rows,
            "out_disposition": _disposition_rows(),
            "out_historical_upgrade_disposition": historical_upgrade_disposition_rows(HISTORICAL_UPGRADE_PACK_DIR),
            "out_historical_bank_perimeter": historical_bank_perimeter_rows(HISTORICAL_UPGRADE_PACK_DIR),
            "out_settlement_class_map": settlement_map,
            "out_settlement_class_invariant": settlement_class_invariant_rows(
                pack_dir, settlement_map
            ),
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
        "# RWTAS illustrative states exhibit pack",
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
            "- S4/S4b endpoints are cited from `var/rwtas/scenarios/slr_conditions/out_slr_spectrum.csv`; they are not rebuilt here.",
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
        "# RWTAS data-upgrades wire report",
        "",
        "Date: 2026-07-03.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: scenario-local data upgrade wire only. Headline/goldens remain untouched.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
        "| historical pack copy | copied path-preserving to `configs/rwtas/packs/historical_upgrades/`; README neutralized; CSV values unchanged |",
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


def _japan_pack(pack_dir: Path, out_dir: Path) -> tuple[Path, list[dict[str, str]]]:
    _fresh_copy(pack_dir, out_dir)
    gdp = Decimal("31500")
    debt = gdp * Decimal("2.50")
    holder_shares = _holder_shares(
        fed_share=Decimal("0.50"),
        foreign_share=Decimal("0.05"),
        household_direct_share=Decimal("0.05"),
        mmf_share=Decimal("0.03"),
        banks_share=Decimal("0.12"),
    )
    opening = _read_csv_rows(out_dir / "opening_stocks.csv")
    _replace_family(opening, "treasury_bills", _amounts_from_shares(debt * Decimal("0.15"), holder_shares), "treasury_federal", "stylized_japan")
    _replace_family(opening, "treasury_notes_bonds_tips", _amounts_from_shares(debt * Decimal("0.85"), holder_shares), "treasury_federal", "stylized_japan")
    _replace_family(opening, "reserves_iorb", {}, "federal_reserve", "stylized_japan")
    _replace_family(opening, "on_rrp_mmfs", {}, "federal_reserve", "stylized_japan")
    _replace_family(opening, "foreign_official_reverse_repos", {}, "federal_reserve", "stylized_japan")
    _scale_existing_family(opening, "deposits_checkable", Decimal("0.70"), "stylized_japan")
    _scale_existing_family(opening, "deposits_savings_mmda", Decimal("0.70"), "stylized_japan")
    _scale_existing_family(opening, "deposits_time_cds", Decimal("0.70"), "stylized_japan")
    _write_opening(out_dir / "opening_stocks.csv", opening)
    _set_treasury_matrix(out_dir / "treasury_holder_matrix.csv", holder_shares, "stylized_japan")
    _set_deposit_regime(out_dir / "claim_processor_rules.csv", "low_beta", "stylized_japan")
    _set_tdc_created_deposit_rate(out_dir / "structural_assumptions.csv", Decimal("0.005"), "stylized_japan")
    inputs = "fiat_illustration_inputs:debt_gdp=250%;central_bank_holder_share=50%;deposit_beta_approx=0.05;household_direct_modest;foreign_small"
    _write_rows(out_dir / "fiat_illustration_inputs.csv", [{"scenario_id": "stylized_japan", "inputs": inputs}])
    return out_dir, [_input_row("stylized_japan", "fiat_state", "state_definition", inputs, "owner_approved_hypothetical", FIAT_LABEL)]


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


def _japan_comparison_rows(japan: dict[str, str], us_default: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "comparison_id": "not_debt_gdp_japan_vs_us",
            "state_id": "stylized_japan",
            "RW_ratio": japan["RW_ratio"],
            "US_default_RW_ratio": us_default["RW_ratio"],
            "debt_gdp_ratio": "250",
            "US_debt_gdp_ratio": "100",
            "interpretation": "holder_composition_and_pass_through_gate_wall_not_debt_scale",
            "claim_grade_label": FIAT_LABEL,
            "caption_note": SHAPE_ONLY_CAPTION_NOTE,
        }
    ]


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
) -> list[dict[str, str]]:
    by_state = {row["state_id"]: row for row in decade_series}
    pre_2008 = [
        _d(by_state["historical_1965"]["RW_ratio"]),
        _d(by_state["historical_1985"]["RW_ratio"]),
        _d(by_state["historical_2005"]["RW_ratio"]),
    ]
    us = _d(by_state["calibrated_US_2026_default"]["RW_ratio"])
    japan = japan_comparison[0]
    fiscal = {row["state_id"]: row for row in fiscal_comparison if row["RW_ratio"]}
    monotone = pre_2008[0] <= pre_2008[1] <= pre_2008[2]
    return [
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
            "check_id": "E3_japan_below_us_despite_debt",
            "status": "pass" if _d(japan["RW_ratio"]) < _d(japan["US_default_RW_ratio"]) else "fail",
            "observed": f"japan={japan['RW_ratio']};US={japan['US_default_RW_ratio']};debt_gdp=250_vs_100",
            "check_against": "stylized Japan RW below US default despite higher debt/GDP",
            "claim_grade_label": FIAT_LABEL,
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


def _grand_spectrum_rows(
    state_rows: list[dict[str, str]],
    japan: dict[str, str],
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
    rows.append(_spectrum_row("E3_not_debt_gdp", japan["state_id"], japan["RW_ratio"], japan["N_bil"], japan["D_bil"], japan["build_v1_rollup_path"], FIAT_LABEL))
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


def _set_deposit_regime(path: Path, regime: str, state_id: str) -> None:
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
        else:
            raise ValueError(f"unknown deposit regime {regime}")
        row["input_basis_label"] = f"{row['input_basis_label']};{state_id}_{regime}"
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
        _lineage_row("out_illustrative_state_inputs", "do/rwtas_decade_aggregates_evidence_20260703.md", "decade aggregates and grades copied into input rows; C-grade rows carry C_grade_visible label"),
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
