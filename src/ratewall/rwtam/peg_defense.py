"""Scenario-only peg-defense exhibit for RWTAM."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from ratewall.rwtam.hysteresis import (
    _deadweight,
    _distress_result_for_shock,
    _write_opening,
    _write_distress_outputs,
)
from ratewall.rwtam.illustrative_states import (
    _amounts_from_shares,
    _fresh_copy,
    _holder_shares,
    _pure_fiscal_pack,
    _replace_family,
    _set_deposit_regime,
    _set_tdc_created_deposit_rate,
    _set_treasury_matrix,
)
from ratewall.rwtam.scenarios import ScenarioResult
from ratewall.rwtam.slr_conditions import _markdown_table, _textbook_pack
from ratewall.rwtam.v1 import (
    CURRENT_DEFAULT_OBJECT_STAMP,
    _d,
    _fmt,
    _read_csv_rows,
    _write_rows,
    build_v1,
)


EXPERIMENT_ID = "rwtam_peg_defense_20260707"
OUTPUT_DIR = Path("var/rwtam/scenarios/peg_defense")
REPORT_PATH = Path("do/rwtam_peg_exhibits_report_20260707.md")
PACK_DIR = Path("configs/rwtam/packs")
DEFAULT_GOLDEN_ROLLUP = Path("tests/fixtures/rwtam/golden_wave8/out_ratewall_rollup.csv")
CLAIM_LABEL = "hypothetical_illustration;scenario_only"
PEG_PACK_LABEL = "peg_regimes_fact_pack_20260707;assumption_mode"
SPIKES_BP = (Decimal("200"), Decimal("500"), Decimal("1000"))
PEG_DOSE_MODE = "transient_12m"
HELD_STANCE_DOSE_MODE = "persistent_level"
SCALE_GDP_BIL = Decimal("31500")
P4_SPIKES_BP = (Decimal("200"), Decimal("500"))
P5_SPIKES_BP = (Decimal("300"), Decimal("1500"))
P6_SPIKES_BP = (Decimal("200"), Decimal("500"))
DEPOSIT_FAMILIES = {"deposits_checkable", "deposits_savings_mmda", "deposits_time_cds"}


@dataclass(frozen=True)
class PegState:
    """A scenario-local opening pack used for one peg-defense state."""

    state_id: str
    state_label: str
    pack_dir: Path
    state_note: str
    lineage_note: str
    spikes_bp: tuple[Decimal, ...]
    exhibit_claim: str
    slot_summary: str
    fact_pack_section: str
    compression_channel_memo: str
    dollarization_share: Decimal = Decimal("0")
    dollarization_source_state_id: str = ""
    engine_off_n_override: bool = False


def build_peg_defense_exhibit(
    pack_dir: Path = PACK_DIR,
    *,
    output_root: Path = OUTPUT_DIR,
) -> ScenarioResult:
    """Build peg-defense states crossed with their defense-spike sweeps."""

    with localcontext() as context:
        context.prec = 28
        _prepare_output_root(output_root)
        states = _peg_states(pack_dir, output_root)
        grid_rows: list[dict[str, str]] = []
        for state in states:
            starting = _headline(
                build_v1(
                    state.pack_dir,
                    dose_mode=PEG_DOSE_MODE,
                    include_impulse_beta_comparator=False,
                ).rows("out_ratewall_rollup")
            )
            for spike_bp in state.spikes_bp:
                grid_rows.append(_measure_cell(state, starting, spike_bp, output_root))
        tables = {
            "out_peg_defense_exhibit": grid_rows,
            "out_peg_defense_p2_bridge": _p2_bridge_rows(pack_dir, output_root),
            "out_peg_defense_notes": _note_rows(),
            "out_peg_defense_slot_inputs": _slot_input_rows(states),
            "out_peg_defense_lineage": _lineage_rows(states, output_root),
            "out_peg_defense_disposition": _disposition_rows(),
            "out_peg_defense_invariant_check": _invariant_rows(grid_rows, pack_dir),
        }
        return ScenarioResult(scenario_id=EXPERIMENT_ID, tables=tables)


def write_peg_defense_outputs(
    result: ScenarioResult,
    output_dir: Path = OUTPUT_DIR,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in result.tables.items():
        path = output_dir / f"{table_name}.csv"
        _write_rows(path, rows)
        paths[table_name] = path
    return paths


def write_peg_defense_report(
    result: ScenarioResult,
    output_path: Path = REPORT_PATH,
) -> Path:
    rows = result.rows("out_peg_defense_exhibit")
    lines = [
        "# RWTAM peg-defense exhibits report",
        "",
        "Date: 2026-07-07.",
        f"Object stamp: `{CURRENT_DEFAULT_OBJECT_STAMP}`.",
        "Frame: fixed-peg defense-spike exhibit; all main grid cells use `transient_12m`; `held_stance_comparison` preserves the persistent-level contrast. All new values come from `do/research/peg_regimes_fact_pack_20260707.md` or are labeled engine-closure assumptions where the pack marks a gap. All cells are hypothetical illustrations and scenario-only. No headline or golden promotion.",
        "",
        "## Dispositions",
        "",
        "| item | disposition |",
        "| --- | --- |",
    ]
    for row in result.rows("out_peg_defense_disposition"):
        lines.append(f"| {row['item']} | {row['disposition']} |")
    lines.extend(_markdown_table("Peg Defense Grid", rows, max_rows=18))
    lines.extend(_markdown_table("Effectiveness Trends", _effectiveness_trends(rows), max_rows=10))
    lines.extend(_markdown_table("P2 FX Bridge", result.rows("out_peg_defense_p2_bridge"), max_rows=10))
    lines.extend(_markdown_table("Sign Structure", _sign_structure(rows)))
    lines.extend(_markdown_table("Slot Inputs", result.rows("out_peg_defense_slot_inputs"), max_rows=20))
    lines.extend(_markdown_table("Notes And Caveats", result.rows("out_peg_defense_notes"), max_rows=20))
    lines.extend(_markdown_table("Invariants", result.rows("out_peg_defense_invariant_check")))
    lines.extend(_markdown_table("Lineage", result.rows("out_peg_defense_lineage"), max_rows=20))
    lines.extend(
        [
            "",
            "## Output Locations",
            "",
            f"- `{OUTPUT_DIR / 'out_peg_defense_exhibit.csv'}`",
            f"- `{OUTPUT_DIR / 'out_peg_defense_p2_bridge.csv'}`",
            f"- `{OUTPUT_DIR / 'out_peg_defense_notes.csv'}`",
            f"- `{OUTPUT_DIR / 'out_peg_defense_slot_inputs.csv'}`",
            f"- `{OUTPUT_DIR / 'out_peg_defense_invariant_check.csv'}`",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def _prepare_output_root(output_root: Path) -> None:
    for name in ("packs", "measurements", "distress"):
        path = output_root / name
        if path.exists():
            shutil.rmtree(path)
    output_root.mkdir(parents=True, exist_ok=True)


def _peg_states(pack_dir: Path, output_root: Path) -> list[PegState]:
    p1_pack = output_root / "packs" / "P1_modern_financialized"
    shutil.copytree(pack_dir, p1_pack)
    _write_rows(
        p1_pack / "peg_defense_state_inputs.csv",
        [
            {
                "state_id": "P1_modern_financialized",
                "state_label": "modern financialized",
                "inputs": "current US default opening pack",
                "claim_grade_label": CLAIM_LABEL,
            }
        ],
    )
    p2_pack, _p2_inputs = _pure_fiscal_pack(
        pack_dir,
        output_root / "packs" / "P2_italy_1992_configuration",
        state_id="P2_italy_1992_configuration",
        restore_today_betas=False,
    )
    p3_pack, _p3_inputs = _textbook_pack(
        pack_dir,
        output_root / "packs" / "P3_textbook_small_open_economy",
    )
    states = [
        PegState(
            "P1_modern_financialized",
            "modern financialized",
            p1_pack,
            "current US default state used counterfactually as a peg defender",
            "copied current default opening pack",
            SPIKES_BP,
            "Baseline existing peg-defense pole: current US balance sheet treated as a hypothetical peg defender.",
            "current default opening pack; no peg-regime fact-pack calibration",
            "existing_P1",
            "existing clean-compression/deadweight comparator",
        ),
        PegState(
            "P2_italy_1992_configuration",
            "Italy-1992 configuration",
            p2_pack,
            "stylized-not-calibrated-to-Italy pure-fiscal wall state",
            "existing illustrative pure-fiscal Reg-Q pack: bill-heavy, household-held debt above 100% GDP, deposit beta approximately zero",
            SPIKES_BP,
            "Baseline existing peg-defense pole: pure-fiscal Reg-Q wall state.",
            "existing pure-fiscal pack; not calibrated Italy",
            "existing_P2",
            "existing pure-fiscal clean-compression/deadweight comparator",
        ),
        PegState(
            "P3_textbook_small_open_economy",
            "textbook small open economy",
            p3_pack,
            "existing textbook-limit state with low debt and thin financialization",
            "existing SLR textbook-limit fiat state pack",
            SPIKES_BP,
            "Baseline existing peg-defense pole: thin-finance textbook state.",
            "existing textbook-limit pack",
            "existing_P3",
            "existing textbook clean-compression/deadweight comparator",
        ),
    ]
    p4_pack = _uk_1992_pack(pack_dir, output_root / "packs" / "P4_uk_1992_variable_rate_defender")
    p5_1997_pack = _hk_currency_board_pack(
        pack_dir,
        output_root / "packs" / "P5_hk_currency_board_1997",
        state_id="P5_hk_currency_board_1997",
        deposit_gdp=Decimal("1.60"),
    )
    p5_now_pack = _hk_currency_board_pack(
        pack_dir,
        output_root / "packs" / "P5_hk_currency_board_now_deposits_400pct",
        state_id="P5_hk_currency_board_now_deposits_400pct",
        deposit_gdp=Decimal("4.00"),
    )
    p6_peg_pack = _postwar_us_pack(
        pack_dir,
        output_root / "packs" / "P6_postwar_us_pegged_engine_off",
        state_id="P6_postwar_us_pegged_engine_off",
        deposit_regime="zero_by_rule",
    )
    p6_free_pack = _postwar_us_pack(
        pack_dir,
        output_root / "packs" / "P6_postwar_us_freed_beta_counterfactual",
        state_id="P6_postwar_us_freed_beta_counterfactual",
        deposit_regime="market",
    )
    states.extend(
        [
            PegState(
                "P4_uk_1992_variable_rate_defender",
                "UK 1992 variable-rate defender",
                p4_pack,
                "UK-1992 pack: 43% GDP ARM, 4% fixed mortgages, 57% deposits beta 0.7/0.8/0.9, gilts 20% GDP long-duration with 55/24/12 holder split",
                "peg fact pack Section A and Recommended design; values carry [obs]/[lit]/[a-r] labels in slot table",
                P4_SPIKES_BP,
                "Almost no wall; hike is nearly pure drag, which is why the announced 15% defense died in hours.",
                "mortgages_arm 43% GDP-equiv [a-r anchored]; fixed 4% [a-r]; deposits 57% [obs] with beta 0.7/0.8/0.9 [a-r] plus 3pp level-wedge memo [obs]; gilts 20% [obs] with pensions+insurers/RoW/HH 55/24/12 [obs-reconstruction caveat]",
                "Recommended P4",
                "transient_12m overstates realized N because the historical defense lasted hours, not twelve months",
            ),
            PegState(
                "P5_hk_currency_board_1997",
                "HK currency board 1997",
                p5_1997_pack,
                "HK-1997 pack: deposits 160% GDP, HH debt 50% all floating, high deposit beta, deadweight layer active",
                "peg fact pack Section B and Recommended design; deposit stock observed GFDD, HH debt assumption-recommended",
                P5_SPIKES_BP,
                "Deposit-rich board has a high wall; defense recycles income, while compression relies on deadweight collateral destruction.",
                "deposits 160% GDP [obs]; HH debt 50% GDP all floating [a-r]; deposit beta high [obs/a-r]; +300 sustained and +1500 extreme cells",
                "Recommended P5",
                "distress/deadweight layer active; memo: historical compression channel was collateral destruction",
            ),
            PegState(
                "P5_hk_currency_board_now_deposits_400pct",
                "HK currency board now deposit-rich variant",
                p5_now_pack,
                "HK now-variant pack: deposits 400% GDP, HH debt 50% all floating, high deposit beta, deadweight layer active",
                "peg fact pack Section B now-variant recommendation; 400% deposit cell",
                P5_SPIKES_BP,
                "The now-deposit stock raises the wall mechanically relative to the 1997 calibration.",
                "deposits 400% GDP [obs/a-r now variant]; HH debt 50% GDP all floating [a-r]; deposit beta high [obs/a-r]",
                "Recommended P5 now",
                "distress/deadweight layer active; historical compression channel was collateral destruction",
            ),
            PegState(
                "P5_argentina_motivated_dollarization_60pct",
                "Argentina-motivated dollarization switch 60%",
                p5_1997_pack,
                "P5 plumbing with 60% deposit-side N rerouted out of domestic flow while D remains local",
                "peg fact pack Section B Argentina moral and Recommended dollarization switch",
                P5_SPIKES_BP,
                "Dollarization severs the numerator: the same local-debtor drag buys less domestic compression.",
                "dollarization share 60% [lit/a-r anchor]; applies to deposit-family N only; D unchanged",
                "Recommended dollarization switch",
                "Argentina-motivated switch reroutes deposit-side N out of domestic flows",
                Decimal("0.6"),
                "P5_hk_currency_board_1997",
            ),
            PegState(
                "P5_argentina_motivated_dollarization_80pct",
                "Argentina-motivated dollarization switch 80%",
                p5_1997_pack,
                "P5 plumbing with 80% deposit-side N rerouted out of domestic flow while D remains local",
                "peg fact pack Section B Argentina moral and Recommended dollarization switch",
                P5_SPIKES_BP,
                "Dollarization severs the numerator: the same local-debtor drag buys less domestic compression.",
                "dollarization share 80% [lit/a-r anchor]; applies to deposit-family N only; D unchanged",
                "Recommended dollarization switch",
                "Argentina-motivated switch reroutes deposit-side N out of domestic flows",
                Decimal("0.8"),
                "P5_hk_currency_board_1997",
            ),
            PegState(
                "P6_postwar_us_pegged_engine_off",
                "Postwar US peg engine off",
                p6_peg_pack,
                "Postwar US pack: HH direct Treasuries 29% GDP with savings-bond memo, deposits 59%, HH debt 14.5%, public debt 106%, beta zero by peg rule",
                "peg fact pack Section C and Recommended design; beta zero by decree",
                P6_SPIKES_BP,
                "The US had the balance sheet for a substantial wall but the peg held the engine off; repression ran it in reverse.",
                "HH direct Treasuries 29% GDP [obs], savings bonds 21% within [obs memo]; deposits 59% [obs]; HH debt 14.5% [obs]; public debt 106% [obs]; beta approximately zero in peg state",
                "Recommended P6 peg",
                "beta zero by peg rule; repression-liquidation 3-4% GDP/yr memo stays outside the RW spike arithmetic",
                Decimal("0"),
                "",
                True,
            ),
            PegState(
                "P6_postwar_us_freed_beta_counterfactual",
                "Postwar US freed-beta counterfactual",
                p6_free_pack,
                "Postwar US pack with the same stocks but the engine's market/private-driver beta rule freed for the spike counterfactual",
                "peg fact pack Section C and Recommended counterfactual; freed beta uses existing engine market rule rather than an invented numeric beta",
                P6_SPIKES_BP,
                "Freed beta reveals the latent wall that the postwar peg suppressed.",
                "same P6 stocks; beta freed via existing engine market/private-driver rule [a-r counterfactual]",
                "Recommended P6 counterfactual",
                "counterfactual frees beta and applies the defense spike",
            ),
        ]
    )
    for state in states:
        _zero_fx_layer(state.pack_dir)
    return states


def _uk_1992_pack(pack_dir: Path, out_dir: Path) -> Path:
    state_id = "P4_uk_1992_variable_rate_defender"
    _fresh_copy(pack_dir, out_dir)
    gdp = SCALE_GDP_BIL
    gilt_stock = gdp * Decimal("0.20")
    holder_shares = _holder_shares(
        fed_share=Decimal("0"),
        foreign_share=Decimal("0.24"),
        household_direct_share=Decimal("0.12"),
        mmf_share=Decimal("0"),
        banks_share=Decimal("0"),
        mutual_funds_share=Decimal("0"),
        pensions_share=Decimal("0.55"),
        insurers_share=Decimal("0"),
        state_local_share=Decimal("0"),
        nonfinancial_share=Decimal("0"),
        other_nonbank_share=Decimal("0"),
    )
    opening = _read_csv_rows(out_dir / "opening_stocks.csv")
    _replace_family(opening, "treasury_bills", {}, "treasury_federal", state_id)
    _replace_family(opening, "treasury_notes_bonds_tips", _amounts_from_shares(gilt_stock, holder_shares), "treasury_federal", state_id)
    _replace_family(opening, "reserves_iorb", {}, "federal_reserve", state_id)
    _replace_family(opening, "on_rrp_mmfs", {}, "federal_reserve", state_id)
    _replace_family(opening, "foreign_official_reverse_repos", {}, "federal_reserve", state_id)
    _replace_family(opening, "deposits_checkable", {}, "banks", state_id)
    _replace_family(opening, "deposits_savings_mmda", {"households": gdp * Decimal("0.57")}, "banks", state_id)
    _replace_family(opening, "deposits_time_cds", {}, "banks", state_id)
    _replace_family(opening, "mortgages_arm", {"banks_nonbank_finance": gdp * Decimal("0.43")}, "households", state_id)
    _replace_family(opening, "mortgages_fixed", {"banks_nonbank_finance": gdp * Decimal("0.04")}, "households", state_id)
    _replace_family(opening, "heloc", {}, "households", state_id)
    _write_opening(out_dir / "opening_stocks.csv", opening)
    _set_treasury_matrix(out_dir / "treasury_holder_matrix.csv", holder_shares, state_id)
    _set_peg_mortgage_holder_decomposition(out_dir / "mortgage_holder_decomposition.csv", gdp * Decimal("0.47"), state_id)
    _set_deposit_regime(out_dir / "claim_processor_rules.csv", "custom_beta", state_id, Decimal("0.8"))
    _set_custom_deposit_beta_band(out_dir / "claim_processor_rules.csv", state_id, Decimal("0.7"), Decimal("0.8"), Decimal("0.9"), "uk_1992_retail_beta_0p7_0p9_and_3pp_level_wedge_memo")
    _set_tdc_created_deposit_rate(out_dir / "structural_assumptions.csv", Decimal("0"), state_id)
    _write_rows(out_dir / "peg_exhibit_slot_inputs.csv", _pack_slot_rows(state_id, "P4"))
    return out_dir


def _hk_currency_board_pack(pack_dir: Path, out_dir: Path, *, state_id: str, deposit_gdp: Decimal) -> Path:
    _fresh_copy(pack_dir, out_dir)
    gdp = SCALE_GDP_BIL
    opening = _read_csv_rows(out_dir / "opening_stocks.csv")
    _replace_family(opening, "treasury_bills", {}, "treasury_federal", state_id)
    _replace_family(opening, "treasury_notes_bonds_tips", {}, "treasury_federal", state_id)
    _replace_family(opening, "reserves_iorb", {}, "federal_reserve", state_id)
    _replace_family(opening, "on_rrp_mmfs", {}, "federal_reserve", state_id)
    _replace_family(opening, "foreign_official_reverse_repos", {}, "federal_reserve", state_id)
    _replace_family(opening, "deposits_checkable", {}, "banks", state_id)
    _replace_family(opening, "deposits_savings_mmda", {"households": gdp * deposit_gdp}, "banks", state_id)
    _replace_family(opening, "deposits_time_cds", {}, "banks", state_id)
    _replace_family(opening, "mortgages_arm", {"banks_nonbank_finance": gdp * Decimal("0.50")}, "households", state_id)
    _replace_family(opening, "mortgages_fixed", {}, "households", state_id)
    _replace_family(opening, "heloc", {}, "households", state_id)
    _write_opening(out_dir / "opening_stocks.csv", opening)
    _set_peg_mortgage_holder_decomposition(out_dir / "mortgage_holder_decomposition.csv", gdp * Decimal("0.50"), state_id)
    _set_deposit_regime(out_dir / "claim_processor_rules.csv", "custom_beta", state_id, Decimal("0.8"))
    _set_custom_deposit_beta_band(out_dir / "claim_processor_rules.csv", state_id, Decimal("0.7"), Decimal("0.8"), Decimal("0.9"), "hk_currency_board_high_deposit_beta_same_day_savings_move")
    _set_tdc_created_deposit_rate(out_dir / "structural_assumptions.csv", Decimal("0"), state_id)
    _write_rows(out_dir / "peg_exhibit_slot_inputs.csv", _pack_slot_rows(state_id, "P5"))
    return out_dir


def _postwar_us_pack(pack_dir: Path, out_dir: Path, *, state_id: str, deposit_regime: str) -> Path:
    _fresh_copy(pack_dir, out_dir)
    gdp = SCALE_GDP_BIL
    debt = gdp * Decimal("1.06")
    holder_shares = _holder_shares(
        fed_share=Decimal("0"),
        foreign_share=Decimal("0"),
        household_direct_share=Decimal("0.27"),
        mmf_share=Decimal("0"),
        banks_share=Decimal("0.30"),
        mutual_funds_share=Decimal("0"),
        pensions_share=Decimal("0.08"),
        insurers_share=Decimal("0.08"),
        state_local_share=Decimal("0.05"),
        nonfinancial_share=Decimal("0"),
        other_nonbank_share=Decimal("0.04"),
    )
    opening = _read_csv_rows(out_dir / "opening_stocks.csv")
    _replace_family(opening, "treasury_bills", _amounts_from_shares(debt * Decimal("0.20"), holder_shares), "treasury_federal", state_id)
    _replace_family(opening, "treasury_notes_bonds_tips", _amounts_from_shares(debt * Decimal("0.80"), holder_shares), "treasury_federal", state_id)
    _replace_family(opening, "reserves_iorb", {}, "federal_reserve", state_id)
    _replace_family(opening, "on_rrp_mmfs", {}, "federal_reserve", state_id)
    _replace_family(opening, "foreign_official_reverse_repos", {}, "federal_reserve", state_id)
    _replace_family(opening, "deposits_checkable", {"households": gdp * Decimal("0.59")}, "banks", state_id)
    _replace_family(opening, "deposits_savings_mmda", {}, "banks", state_id)
    _replace_family(opening, "deposits_time_cds", {}, "banks", state_id)
    hh_debt = gdp * Decimal("0.145")
    mortgage = hh_debt * (Decimal("23.1") / Decimal("32.9"))
    consumer = hh_debt - mortgage
    _replace_family(opening, "mortgages_fixed", {"banks_nonbank_finance": mortgage}, "households", state_id)
    _replace_family(opening, "mortgages_arm", {}, "households", state_id)
    _replace_family(opening, "heloc", {}, "households", state_id)
    _replace_family(opening, "credit_card_revolving", {}, "households", state_id)
    _replace_family(opening, "auto_installment_debt", {}, "households", state_id)
    _replace_family(opening, "personal_installment_debt", {"banks_nonbank_finance": consumer}, "households", state_id)
    _replace_family(opening, "student_loans_private", {}, "households", state_id)
    _write_opening(out_dir / "opening_stocks.csv", opening)
    _set_treasury_matrix(out_dir / "treasury_holder_matrix.csv", holder_shares, state_id)
    _set_peg_mortgage_holder_decomposition(out_dir / "mortgage_holder_decomposition.csv", mortgage, state_id)
    _set_deposit_regime(out_dir / "claim_processor_rules.csv", deposit_regime, state_id)
    _set_tdc_created_deposit_rate(out_dir / "structural_assumptions.csv", Decimal("0"), state_id)
    _write_rows(out_dir / "peg_exhibit_slot_inputs.csv", _pack_slot_rows(state_id, "P6"))
    return out_dir


def _set_peg_mortgage_holder_decomposition(path: Path, mortgage_stock: Decimal, state_id: str) -> None:
    rows = []
    for holder, amount in {
        "banks_nonbanks_whole_loans": mortgage_stock,
        "federal_reserve_agency_mbs": Decimal("0"),
        "nonbank_finance_agency_mbs_investors": Decimal("0"),
    }.items():
        rows.append(
            {
                "parameter_id": "mortgage_holder_stock_bn",
                "holder": holder,
                "instrument_family": "mortgage_holder_decomposition",
                "low": _fmt(amount),
                "base": _fmt(amount),
                "high": _fmt(amount),
                "units": "$bn_current",
                "source_id": f"{PEG_PACK_LABEL}:{state_id}",
                "input_basis_label": f"{state_id};scenario_local_holder_decomposition;engine_closure_assumption",
                "rationale": "Peg exhibit fact pack supplies the mortgage stock, not a securitization holder split; holder closure keeps the stock in whole-loan banks/nonbanks and emits zero rows for engine-required MBS holders.",
            }
        )
    _write_rows(path, rows)


def _set_custom_deposit_beta_band(
    path: Path,
    state_id: str,
    low_beta: Decimal,
    base_beta: Decimal,
    high_beta: Decimal,
    label: str,
) -> None:
    rows = _read_csv_rows(path)
    for row in rows:
        if row["instrument_family"] not in DEPOSIT_FAMILIES:
            continue
        row["constant_level_delta"] = _fmt(base_beta / Decimal("100"))
        row["input_basis_label"] = f"{row['input_basis_label']};{state_id};{label};low={_fmt(low_beta)};base={_fmt(base_beta)};high={_fmt(high_beta)}"
        row["basis"] = f"{row['basis']};deposit_beta_band_recorded_in_label"
    _write_rows(path, rows)


def _pack_slot_rows(state_id: str, exhibit: str) -> list[dict[str, str]]:
    return [{"state_id": state_id, "exhibit": exhibit, "source": "do/research/peg_regimes_fact_pack_20260707.md"}]


def _zero_fx_layer(pack_dir: Path) -> None:
    path = pack_dir / "phase6" / "conversion_parameters.csv"
    rows = _read_csv_rows(path)
    fx_ids = {
        "broad_dollar_appreciation_policy_pack",
        "fx_net_export_drag_year1",
        "fx_net_export_drag_year2_incremental",
        "fx_net_export_drag_two_year_cumulative",
    }
    for row in rows:
        if row["parameter_id"] in fx_ids:
            for band in ("low", "base", "high"):
                row[band] = "0"
            row["input_basis_label"] = f"{row['input_basis_label']};peg_defense_fx_channel_excluded"
            row["rationale"] = f"{row['rationale']} Peg-defense credible-peg exhibit sets FX/import appreciation route off."
    _write_rows(path, rows)
    _write_rows(
        pack_dir / "peg_defense_fx_off_assertion.csv",
        [
            {
                "scenario_id": EXPERIMENT_ID,
                "fx_net_exports": "off",
                "fx_import_price_relief": "excluded_parallel_real_income_object",
                "source": "phase6/conversion_parameters.csv",
                "claim_grade_label": CLAIM_LABEL,
            }
        ],
    )


def _measure_cell(
    state: PegState,
    starting: dict[str, str],
    spike_bp: Decimal,
    output_root: Path,
) -> dict[str, str]:
    result = build_v1(
        state.pack_dir,
        dose_mode=PEG_DOSE_MODE,
        shock_size_bp=spike_bp,
        include_impulse_beta_comparator=False,
    )
    held_stance = build_v1(
        state.pack_dir,
        dose_mode=HELD_STANCE_DOSE_MODE,
        shock_size_bp=spike_bp,
        include_impulse_beta_comparator=False,
    )
    rollup = result.rows("out_ratewall_rollup")
    headline = _headline(rollup)
    held_headline = _headline(held_stance.rows("out_ratewall_rollup"))
    measurement_dir = output_root / "measurements" / state.state_id / f"spike_{_fmt(spike_bp)}bp"
    measurement_dir.mkdir(parents=True, exist_ok=True)
    rollup_path = measurement_dir / "out_ratewall_rollup.csv"
    _write_rows(rollup_path, rollup)
    held_stance_path = measurement_dir / "held_stance_comparison_out_ratewall_rollup.csv"
    _write_rows(held_stance_path, held_stance.rows("out_ratewall_rollup"))

    distress = _distress_result_for_shock(state.pack_dir, spike_bp)
    distress_paths = _write_distress_outputs(
        distress,
        output_root / "distress" / state.state_id / f"spike_{_fmt(spike_bp)}bp",
    )
    deadweight = _deadweight(distress, "2026")
    n_before_dollarization = _d(headline["N_bil"])
    d_value = _d(headline["D_bil"])
    deposit_side_n = _deposit_side_n(result)
    deposit_n_rerouted = deposit_side_n * state.dollarization_share
    n_value = n_before_dollarization - deposit_n_rerouted
    engine_off_n_rerouted = Decimal("0")
    if state.engine_off_n_override:
        engine_off_n_rerouted = n_value
        n_value = Decimal("0")
    rw_ratio = Decimal("0") if d_value == 0 else n_value / d_value
    net_domestic_demand = n_value - d_value - deadweight
    clean_compression = abs(n_value - d_value)
    clean_compression_per_100bp = clean_compression / (spike_bp / Decimal("100"))
    total_compression = clean_compression + deadweight
    deadweight_share = Decimal("0") if total_compression == 0 else deadweight / total_compression
    distress_activated = _distress_activated(distress)
    return {
        "experiment_id": EXPERIMENT_ID,
        "state_id": state.state_id,
        "state_label": state.state_label,
        "state_note": state.state_note,
        "dose_mode": PEG_DOSE_MODE,
        "defense_spike_bp": _fmt(spike_bp),
        "starting_RW_ratio": starting["RW_ratio"],
        "RW_ratio_at_spike": _fmt(rw_ratio),
        "N_bil": _fmt(n_value),
        "D_bil": headline["D_bil"],
        "N_before_dollarization_bil": _fmt(n_before_dollarization),
        "deposit_side_N_bil": _fmt(deposit_side_n),
        "dollarization_share": _fmt(state.dollarization_share),
        "deposit_N_rerouted_out_of_domestic_flow_bil": _fmt(deposit_n_rerouted),
        "engine_off_N_rerouted_by_decree_bil": _fmt(engine_off_n_rerouted),
        "dollarization_status": "active" if state.dollarization_share else "off",
        "deadweight_bil": _fmt(deadweight),
        "clean_compression_bil": _fmt(clean_compression),
        "net_domestic_demand_effect_bil": _fmt(net_domestic_demand),
        "clean_compression_per_100bp": _fmt(clean_compression_per_100bp),
        "deadweight_share_of_compression": _fmt(deadweight_share),
        "held_stance_comparison": _held_stance_comparison(held_headline, held_stance_path),
        "distress_activated": str(distress_activated).lower(),
        "deadweight_activated": str(deadweight > 0).lower(),
        "exhibit_claim": state.exhibit_claim,
        "slot_summary": state.slot_summary,
        "fact_pack_section": state.fact_pack_section,
        "compression_channel_memo": state.compression_channel_memo,
        "dollarization_source_state_id": state.dollarization_source_state_id,
        "fx_channel_status": "off",
        "fx_net_export_drag_year1_base": _fx_param_base(state.pack_dir, "fx_net_export_drag_year1"),
        "fx_import_price_relief_status": "excluded_parallel_real_income_object",
        "build_v1_rollup_path": str(rollup_path),
        "distress_deadweight_source_path": str(distress_paths["out_distress_deadweight_drag_by_year"]),
        "claim_grade_label": CLAIM_LABEL,
    }


def _deposit_side_n(result: ScenarioResult) -> Decimal:
    total = Decimal("0")
    for row in result.rows("out_cashflow_family_contributions"):
        if (
            row["period_type"] == "annual"
            and row["period"] == "2026"
            and row["band"] == "base"
            and row["ricardian_offset"] == "0"
            and row["instrument_family"] in DEPOSIT_FAMILIES
        ):
            total += _d(row["N_bil"])
    return total


def _held_stance_comparison(headline: dict[str, str], rollup_path: Path) -> str:
    return (
        f"{HELD_STANCE_DOSE_MODE}:RW_ratio={headline['RW_ratio']};"
        f"N_bil={headline['N_bil']};"
        f"D_bil={headline['D_bil']};"
        f"rollup_path={rollup_path}"
    )


def _p2_bridge_rows(pack_dir: Path, output_root: Path) -> list[dict[str, str]]:
    fx_on_pack, _inputs = _pure_fiscal_pack(
        pack_dir,
        output_root / "packs" / "P2_italy_1992_configuration_fx_on_bridge",
        state_id="P2_italy_1992_configuration_fx_on_bridge",
        restore_today_betas=False,
    )
    fx_off_pack = output_root / "packs" / "P2_italy_1992_configuration"
    rows: list[dict[str, str]] = []
    for dose_mode in (PEG_DOSE_MODE, HELD_STANCE_DOSE_MODE):
        fx_on = _headline(
            build_v1(
                fx_on_pack,
                dose_mode=dose_mode,
                include_impulse_beta_comparator=False,
            ).rows("out_ratewall_rollup")
        )
        fx_off = _headline(
            build_v1(
                fx_off_pack,
                dose_mode=dose_mode,
                include_impulse_beta_comparator=False,
            ).rows("out_ratewall_rollup")
        )
        rows.append(_p2_bridge_row(dose_mode, fx_on, fx_off, fx_on_pack, fx_off_pack))
    return rows


def _p2_bridge_row(
    dose_mode: str,
    fx_on: dict[str, str],
    fx_off: dict[str, str],
    fx_on_pack: Path,
    fx_off_pack: Path,
) -> dict[str, str]:
    rw_gap = _d(fx_off["RW_ratio"]) - _d(fx_on["RW_ratio"])
    d_gap = _d(fx_on["D_bil"]) - _d(fx_off["D_bil"])
    expected_drag_gap = _d(_fx_param_base(fx_on_pack, "fx_net_export_drag_year1")) - _d(
        _fx_param_base(fx_off_pack, "fx_net_export_drag_year1")
    )
    bridge_residual = d_gap - expected_drag_gap
    return {
        "bridge_id": f"P2_fx_on_to_fx_off_{dose_mode}",
        "state_id": "P2_italy_1992_configuration",
        "dose_mode": dose_mode,
        "shock_size_bp": "100",
        "fx_on_RW_ratio": fx_on["RW_ratio"],
        "fx_on_N_bil": fx_on["N_bil"],
        "fx_on_D_bil": fx_on["D_bil"],
        "fx_on_fx_net_export_drag_year1_base": _fx_param_base(fx_on_pack, "fx_net_export_drag_year1"),
        "fx_off_RW_ratio": fx_off["RW_ratio"],
        "fx_off_N_bil": fx_off["N_bil"],
        "fx_off_D_bil": fx_off["D_bil"],
        "fx_off_fx_net_export_drag_year1_base": _fx_param_base(fx_off_pack, "fx_net_export_drag_year1"),
        "RW_ratio_gap_fx_off_minus_on": _fmt(rw_gap),
        "D_gap_fx_on_minus_off_bil": _fmt(d_gap),
        "expected_removed_fx_drag_bil": _fmt(expected_drag_gap),
        "bridge_residual_bil": _fmt(bridge_residual),
        "diagnosis": "gap_closes_to_removed_fx_drag_in_D" if bridge_residual == 0 else "review_non_fx_residual",
        "claim_grade_label": CLAIM_LABEL,
    }


def _distress_activated(result: ScenarioResult) -> bool:
    return any(
        _d(row["incremental_default_principal_bil"]) > 0
        for row in result.rows("out_distress_ledger_monthly")
    )


def _fx_param_base(pack_dir: Path, parameter_id: str) -> str:
    rows = _read_csv_rows(pack_dir / "phase6" / "conversion_parameters.csv")
    return next(row["base"] for row in rows if row["parameter_id"] == parameter_id)


def _headline(rows: list[dict[str, str]]) -> dict[str, str]:
    return [
        row
        for row in rows
        if row["period_type"] == "annual"
        and row["period"] == "2026"
        and row["band"] == "base"
        and row["ricardian_offset"] == "0"
    ][0]


def _invariant_rows(rows: list[dict[str, str]], pack_dir: Path) -> list[dict[str, str]]:
    default_rows = build_v1(pack_dir, include_impulse_beta_comparator=False).rows("out_ratewall_rollup")
    golden_rows = _read_csv_rows(DEFAULT_GOLDEN_ROLLUP) if DEFAULT_GOLDEN_ROLLUP.exists() else []
    fx_off = all(
        row["fx_channel_status"] == "off"
        and _d(row["fx_net_export_drag_year1_base"]) == 0
        and row["fx_import_price_relief_status"] == "excluded_parallel_real_income_object"
        for row in rows
    )
    clean_compression_recomputes = all(
        _d(row["clean_compression_per_100bp"])
        == abs(_d(row["N_bil"]) - _d(row["D_bil"])) / (_d(row["defense_spike_bp"]) / Decimal("100"))
        for row in rows
    )
    deadweight_share_recomputes = all(
        _d(row["deadweight_share_of_compression"])
        == _d(row["deadweight_bil"]) / (_d(row["clean_compression_bil"]) + _d(row["deadweight_bil"]))
        for row in rows
    )
    flags_emitted = all(
        row["distress_activated"] in {"true", "false"}
        and row["deadweight_activated"] in {"true", "false"}
        and row["distress_deadweight_source_path"]
        for row in rows
    )
    p6_peg_zero = all(
        abs(_d(row["N_bil"])) <= Decimal("1e-18")
        for row in rows
        if row["state_id"] == "P6_postwar_us_pegged_engine_off"
    )
    dollarization_rows = [
        row
        for row in rows
        if row["state_id"].startswith("P5_argentina_motivated_dollarization_")
    ]
    dollarization_recomputes = all(
        _d(row["N_bil"])
        == _d(row["N_before_dollarization_bil"])
        - _d(row["deposit_N_rerouted_out_of_domestic_flow_bil"])
        for row in dollarization_rows
    )
    dollarization_monotone = True
    for spike in sorted({row["defense_spike_bp"] for row in dollarization_rows}):
        spike_rows = sorted(
            [row for row in dollarization_rows if row["defense_spike_bp"] == spike],
            key=lambda row: _d(row["dollarization_share"]),
        )
        if len(spike_rows) >= 2:
            dollarization_monotone = dollarization_monotone and all(
                _d(left["N_bil"]) >= _d(right["N_bil"])
                for left, right in zip(spike_rows, spike_rows[1:], strict=False)
            )
    return [
        {
            "check_id": "PG1_fx_off_every_peg_cell",
            "status": "pass" if fx_off else "fail",
            "message": "FX net-export drag is zero and import-price relief remains excluded in every peg-defense pack",
        },
        {
            "check_id": "PG2_clean_compression_recomputed",
            "status": "pass" if clean_compression_recomputes else "fail",
            "message": "clean compression equals abs(N-D) divided by spike size in 100bp units",
        },
        {
            "check_id": "PG3_deadweight_share_recomputed",
            "status": "pass" if deadweight_share_recomputes else "fail",
            "message": "deadweight share equals deadweight/(abs(N-D)+deadweight)",
        },
        {
            "check_id": "PG4_distress_flags_emitted_not_assumed",
            "status": "pass" if flags_emitted else "fail",
            "message": "distress and deadweight activation flags are explicit cell fields with source paths",
        },
        {
            "check_id": "PG5_default_rollup_matches_golden_after_scenario_build",
            "status": "pass" if default_rows == golden_rows else "fail",
            "message": f"fresh default build_v1 rollup compared with {DEFAULT_GOLDEN_ROLLUP}",
        },
        {
            "check_id": "PG6_p6_peg_state_N_zero_by_construction",
            "status": "pass" if p6_peg_zero else "fail",
            "message": "P6 peg-state deposit beta is zero and N is approximately zero by construction",
        },
        {
            "check_id": "PG7_dollarization_reduces_domestic_N_monotonically",
            "status": "pass" if dollarization_recomputes and dollarization_monotone else "fail",
            "message": "Argentina-motivated 0.6/0.8 dollarization cells reroute deposit-side N out of domestic flows and monotonically reduce N",
        },
    ]


def _note_rows() -> list[dict[str, str]]:
    return [
        {
            "note_id": "policy_moral",
            "note_text": "Under a float a high wall attenuates stabilization; under a peg it attenuates clean defense compression, while larger spikes increasingly rely on explicit deadweight destruction. Same object, opposite moral.",
            "claim_grade_label": CLAIM_LABEL,
        },
        {
            "note_id": "no_reserve_drain_bop_dynamics",
            "note_text": "No reserve-drain or balance-of-payments dynamics are modeled; the defense requirement is exogenous and the exhibit measures only what the hike delivers domestically.",
            "claim_grade_label": CLAIM_LABEL,
        },
        {
            "note_id": "no_sovereign_risk_premium",
            "note_text": "No sovereign risk premium channel is modeled; hard-peg or currency-union debt can carry default premia outside this model.",
            "claim_grade_label": CLAIM_LABEL,
        },
        {
            "note_id": "no_rstar_wedge",
            "note_text": "The r-star wedge is not applicable under a peg because the anchor pins the external rate condition.",
            "claim_grade_label": CLAIM_LABEL,
        },
        {
            "note_id": "p2_not_calibrated_italy",
            "note_text": "P2 is stylized, not calibrated Italy; the Banca d'Italia worry is a motivating referent, not a validation target.",
            "claim_grade_label": CLAIM_LABEL,
        },
        {
            "note_id": "p4_uk_1992_claim",
            "note_text": "P4 claim: almost no wall; the hike is nearly pure drag, which is why the announced 15% defense died in hours; transient_12m overstates N versus the historical transient-hours defense.",
            "claim_grade_label": PEG_PACK_LABEL,
        },
        {
            "note_id": "p5_hk_currency_board_claim",
            "note_text": "P5 claim: a deposit-rich board has a high wall; defense recycles income, while realized compression historically came through collateral destruction.",
            "claim_grade_label": PEG_PACK_LABEL,
        },
        {
            "note_id": "p6_postwar_us_claim",
            "note_text": "P6 claim: postwar US had the balance sheet for a substantial wall but the engine was held off by decree; repression ran it in reverse at 3-4% GDP/yr.",
            "claim_grade_label": PEG_PACK_LABEL,
        },
        {
            "note_id": "dollarization_switch_claim",
            "note_text": "Dollarization switch claim: anchor-currency deposits reroute deposit-side N out of domestic demand while local debtor D remains, so N falls monotonically with the dollarized share.",
            "claim_grade_label": PEG_PACK_LABEL,
        },
        {
            "note_id": "obstfeld_rogoff_uk_mortgage_verify_before_quote",
            "note_text": "Obstfeld-Rogoff 1995 UK-mortgage passage is UNVERIFIED in the pack; verify before quote.",
            "claim_grade_label": PEG_PACK_LABEL,
        },
    ]


def _slot_input_rows(states: list[PegState]) -> list[dict[str, str]]:
    return [
        {
            "state_id": state.state_id,
            "state_label": state.state_label,
            "fact_pack_section": state.fact_pack_section,
            "spike_cells_bp": "/".join(_fmt(spike) for spike in state.spikes_bp),
            "slot_summary": state.slot_summary,
            "exhibit_claim": state.exhibit_claim,
            "compression_channel_memo": state.compression_channel_memo,
            "dollarization_share": _fmt(state.dollarization_share),
            "claim_grade_label": PEG_PACK_LABEL if state.fact_pack_section.startswith("Recommended") else CLAIM_LABEL,
        }
        for state in states
    ]


def _lineage_rows(states: list[PegState], output_root: Path) -> list[dict[str, str]]:
    rows = [
        {
            "deliverable_column": "out_peg_defense_exhibit.RW_ratio_at_spike",
            "source_file": str(output_root / "measurements"),
            "lineage_note": "fresh build_v1 rollups from scenario-local opening packs with requested shock_size_bp defense spikes",
        },
        {
            "deliverable_column": "out_peg_defense_exhibit.deadweight_bil",
            "source_file": str(output_root / "distress"),
            "lineage_note": "existing distress PD/LGD/deadweight machinery measured at each defense spike",
        },
        {
            "deliverable_column": "out_peg_defense_exhibit.fx_channel_status",
            "source_file": "configs/rwtam/packs/phase6/conversion_parameters.csv",
            "lineage_note": "existing import-price relief exclusion retained; FX net-export drag zeroed in scenario-local packs for credible-peg assumption",
        },
        {
            "deliverable_column": "out_peg_defense_p2_bridge",
            "source_file": str(output_root / "packs" / "P2_italy_1992_configuration_fx_on_bridge"),
            "lineage_note": "P2 bridge compares the same pure-fiscal state with the FX layer on versus the peg-defense FX-off pack",
        },
        {
            "deliverable_column": "out_peg_defense_exhibit.dollarization_share",
            "source_file": "do/research/peg_regimes_fact_pack_20260707.md",
            "lineage_note": "Argentina-motivated 0.6/0.8 share switch reroutes deposit-family N out of domestic flows on P5 plumbing; D is unchanged",
        },
    ]
    for state in states:
        rows.append(
            {
                "deliverable_column": f"state_pack.{state.state_id}",
                "source_file": str(state.pack_dir),
                "lineage_note": state.lineage_note,
            }
        )
    return rows


def _disposition_rows() -> list[dict[str, str]]:
    return [
        {"item": "P1_modern_financialized", "disposition": "built from current US default opening pack as counterfactual peg defender"},
        {"item": "P2_italy_1992_configuration", "disposition": "built from existing pure-fiscal Reg-Q illustrative machinery; stylized-not-calibrated-to-Italy label emitted"},
        {"item": "P3_textbook_small_open_economy", "disposition": "built from existing textbook-limit fiat state machinery"},
        {"item": "defense_spike_sweep", "disposition": "rebuilt +200/+500/+1000bp cells with transient_12m dose through build_v1 shock_size_bp"},
        {"item": "held_stance_comparison", "disposition": "persistent_level cells retained as a labeled comparison column rather than headline grid values"},
        {"item": "effectiveness_metric", "disposition": "split into clean_compression_per_100bp and deadweight_share_of_compression; no tuning"},
        {"item": "P2_fx_bridge", "disposition": "emits FX-on versus FX-off P2 bridge and residual diagnostic"},
        {"item": "P4_uk_1992_variable_rate_defender", "disposition": "built from peg fact pack recommended UK-1992 slots; +200/+500bp cells; transient-hours caveat emitted"},
        {"item": "P5_hk_currency_board", "disposition": "built from peg fact pack 1997 and now deposit-stock variants; +300/+1500bp cells; deadweight/collateral-destruction memo emitted"},
        {"item": "P6_postwar_us_pegged_engine_off", "disposition": "built from peg fact pack postwar US slots; peg-state beta zero and freed-beta counterfactual emitted"},
        {"item": "dollarization_switch", "disposition": "0.6/0.8 Argentina-motivated P5-plumbing cells reroute deposit-side N out of domestic flow while leaving D unchanged"},
        {"item": "fx_import_channels", "disposition": "FX net-export drag zeroed in scenario-local packs; import-price relief remains excluded"},
        {"item": "headline_goldens", "disposition": "scenario-local outputs only; default-vs-golden invariant emitted"},
    ]


def _sign_structure(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for state_id in sorted({row["state_id"] for row in rows}):
        state_rows = [row for row in rows if row["state_id"] == state_id]
        signs = []
        for row in state_rows:
            value = _d(row["net_domestic_demand_effect_bil"])
            signs.append("negative" if value < 0 else "positive" if value > 0 else "zero")
        out.append(
            {
                "state_id": state_id,
                "net_domestic_demand_signs": ";".join(
                    f"{row['defense_spike_bp']}bp={sign}"
                    for row, sign in zip(state_rows, signs, strict=True)
                ),
                "all_negative": str(all(sign == "negative" for sign in signs)).lower(),
                "claim_grade_label": CLAIM_LABEL,
            }
        )
    return out


def _effectiveness_trends(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for state_id in sorted({row["state_id"] for row in rows}):
        state_rows = sorted(
            [row for row in rows if row["state_id"] == state_id],
            key=lambda row: _d(row["defense_spike_bp"]),
        )
        clean_values = [_d(row["clean_compression_per_100bp"]) for row in state_rows]
        deadweight_values = [_d(row["deadweight_share_of_compression"]) for row in state_rows]
        out.append(
            {
                "state_id": state_id,
                "clean_compression_per_100bp_trend": _trend_label(clean_values),
                "deadweight_share_trend": _trend_label(deadweight_values),
                "clean_values_200_500_1000": "/".join(_fmt(value) for value in clean_values),
                "deadweight_share_200_500_1000": "/".join(_fmt(value) for value in deadweight_values),
                "claim_grade_label": CLAIM_LABEL,
            }
        )
    return out


def _trend_label(values: list[Decimal]) -> str:
    if all(left < right for left, right in zip(values, values[1:], strict=False)):
        return "rising_as_found"
    if all(left > right for left, right in zip(values, values[1:], strict=False)):
        return "falling_as_found"
    if all(left == right for left, right in zip(values, values[1:], strict=False)):
        return "flat_as_found"
    return "mixed_as_found"
