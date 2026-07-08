from __future__ import annotations

import csv
import shutil
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.rwtam import RwtamConfigError, load_config, run_rwtam
from ratewall.rwtam.contract import OUTPUT_TABLES


CONFIG_DIR = Path("configs/rwtam")


def test_rwtam_v0_fixture_headline_and_leg_gross_diagnostic() -> None:
    result = run_rwtam(load_config(CONFIG_DIR))

    monthly = result.rows("out_ratewall_monthly")[0]
    assert_close(Decimal(monthly["N_bil"]), Decimal("0.465000"))
    assert_close(Decimal(monthly["D_bil"]), Decimal("0.940000"))
    assert_close(Decimal(monthly["net_bil"]), Decimal("-0.475000"))
    assert_close(Decimal(monthly["RW_ratio"]), Decimal("0.494681"), Decimal("0.000001"))
    assert_close(Decimal(monthly["leg_gross_N_bil"]), Decimal("0.535000"))
    assert_close(Decimal(monthly["leg_gross_D_bil"]), Decimal("1.010000"))
    assert_close(Decimal(monthly["leg_gross_net_bil"]), Decimal("-0.475000"))
    assert monthly["leg_gross_net_equals_headline_net"] == "true"


def test_rwtam_outputs_include_required_tables() -> None:
    result = run_rwtam(load_config(CONFIG_DIR))

    assert set(result.tables) == set(OUTPUT_TABLES)
    for table_name in OUTPUT_TABLES:
        assert result.rows(table_name), table_name


def test_rwtam_t01_to_t21_invariant_matrix_passes_without_skips() -> None:
    result = run_rwtam(load_config(CONFIG_DIR))

    checks = result.rows("out_invariant_check")
    assert {row["check_id"] for row in checks} == {f"T{i:02d}" for i in range(1, 22)}
    assert {row["status"] for row in checks} == {"pass"}
    assert "skip" not in {row["status"] for row in checks}


def test_t22_fungibility_reward_and_avoided_interest_variants_match(
    tmp_path: Path,
) -> None:
    reward_config = copy_config(tmp_path / "reward")
    avoided_config = copy_config(tmp_path / "avoided")

    append_flow_term(
        reward_config,
        {
            "term_rule_id": "reward_to_hh_borrower",
            "claim_id": "C3",
            "flow_kind": "reward_payment",
            "payer_sector": "banks_depositories",
            "payer_cell": "banks_depositories",
            "receiver_sector": "households",
            "receiver_cell": "hh_borrower",
            "baseline_amount_bil": "0",
            "shock_amount_bil": "1",
            "cash_flag": "cash",
            "stock_effect": "none",
            "report_group_id": "private_debt_service_report",
            "real_conversion_eligible": "true",
        },
    )
    append_flow_term(
        avoided_config,
        {
            "term_rule_id": "avoided_c3_interest",
            "claim_id": "C3",
            "flow_kind": "interest_cash_payment",
            "payer_sector": "households",
            "payer_cell": "hh_borrower",
            "receiver_sector": "banks_depositories",
            "receiver_cell": "banks_depositories",
            "baseline_amount_bil": "1",
            "shock_amount_bil": "0",
            "cash_flag": "cash",
            "stock_effect": "none",
            "report_group_id": "private_debt_service_report",
            "real_conversion_eligible": "true",
        },
    )

    reward = run_rwtam(load_config(reward_config))
    avoided = run_rwtam(load_config(avoided_config))

    for cell_id in ["hh_borrower", "banks_depositories"]:
        reward_cell = cell_row(reward, cell_id)
        avoided_cell = cell_row(avoided, cell_id)
        for field in [
            "net_flow_delta_bil",
            "activity_effect_bil",
            "support_bil",
            "drag_bil",
        ]:
            assert Decimal(reward_cell[field]) == Decimal(avoided_cell[field])

    for field in ["N_bil", "D_bil", "net_bil", "RW_ratio"]:
        assert Decimal(reward.rows("out_ratewall_monthly")[0][field]) == Decimal(
            avoided.rows("out_ratewall_monthly")[0][field]
        )


def test_t23_conversion_rules_reject_leg_role_or_flow_type_magnitudes(
    tmp_path: Path,
) -> None:
    config_dir = copy_config(tmp_path / "bad_conversion")
    write_csv(
        config_dir / "cfg_real_conversion_rule.csv",
        [
            {
                "conversion_rule_id": "bad_hh_receiver",
                "cell_id": "hh_saver",
                "sector_id": "households",
                "leg_role": "receiver",
                "flow_type": "interest_cash_payment",
                "instrument_class": "treasury_debt",
                "effect_family": "real_demand",
                "activity_component": "consumption",
                "conversion_coeff": "0.40",
                "domestic_eligibility_weight": "1",
                "input_basis_label": "assumption",
                "valid_from": "2026-01",
                "valid_to": "",
            },
            {
                "conversion_rule_id": "bad_hh_payer",
                "cell_id": "hh_saver",
                "sector_id": "households",
                "leg_role": "payer",
                "flow_type": "reward_payment",
                "instrument_class": "household_credit",
                "effect_family": "real_demand",
                "activity_component": "consumption",
                "conversion_coeff": "0.80",
                "domestic_eligibility_weight": "1",
                "input_basis_label": "assumption",
                "valid_from": "2026-01",
                "valid_to": "",
            },
        ],
    )

    with pytest.raises(RwtamConfigError, match="cell only"):
        load_config(config_dir)


def test_t24_ricardian_offset_is_named_generated_and_reported(
    tmp_path: Path,
) -> None:
    config_dir = copy_config(tmp_path / "ricardian")
    update_parameter(config_dir, "ricardian_offset", "0.5")

    base_config = load_config(CONFIG_DIR)
    offset_config = load_config(config_dir)
    base = run_rwtam(base_config)
    offset = run_rwtam(offset_config)

    generated_cells = {rule.payer_cell for rule in offset_config.ricardian_counterfactual_rules}
    assert generated_cells.isdisjoint(
        {rule.cell_id for rule in offset_config.base_conversion_rules}
    )
    assert {rule.cell_id for rule in offset_config.conversion_rules}.issuperset(
        generated_cells
    )
    assert offset.rows("out_run_manifest")[0]["ricardian_offset"] == "0.5"
    assert offset.rows("out_ratewall_monthly")[0]["ricardian_offset"] == "0.5"

    expected_extra_drag = expected_ricardian_drag(base_config, base, Decimal("0.5"))
    assert expected_extra_drag > 0
    base_monthly = base.rows("out_ratewall_monthly")[0]
    offset_monthly = offset.rows("out_ratewall_monthly")[0]
    assert Decimal(offset_monthly["N_bil"]) == Decimal(base_monthly["N_bil"])
    assert Decimal(offset_monthly["D_bil"]) == (
        Decimal(base_monthly["D_bil"]) + expected_extra_drag
    )
    assert Decimal(offset_monthly["RW_ratio"]) != Decimal(base_monthly["RW_ratio"])


def test_t20_row_receiver_support_zero_and_domestic_payer_drag_counts(
    tmp_path: Path,
) -> None:
    config_dir = copy_config(tmp_path / "row")
    append_claim(
        config_dir,
        {
            "state_id": "current_state_2026_01",
            "opening_month": "2026-01",
            "claim_id": "CROW",
            "holder_sector": "rest_of_world",
            "holder_cell": "rest_of_world",
            "issuer_sector": "households",
            "issuer_cell": "hh_borrower",
            "instrument": "rest_of_world_claim",
            "incidence_mode": "direct",
            "principal_begin_bil": "120",
            "book_value_begin_bil": "120",
            "market_value_begin_bil": "120",
            "currency": "USD",
            "valuation_basis": "par",
            "report_group_id": "rest_of_world_report",
        },
    )
    append_term(config_dir, "CROW", "floating", "treasury_safe")
    append_exposure(config_dir, "CROW", "120")

    result = run_rwtam(load_config(config_dir))
    row_receiver = [
        row
        for row in result.rows("out_real_effect_leg_monthly")
        if row["claim_id"] == "CROW"
        and row["leg_role"] == "receiver"
        and row["sector_id"] == "rest_of_world"
    ][0]
    domestic_payer = [
        row
        for row in result.rows("out_real_effect_leg_monthly")
        if row["claim_id"] == "CROW"
        and row["leg_role"] == "payer"
        and row["sector_id"] == "households"
    ][0]

    assert Decimal(row_receiver["support_bil"]) == 0
    assert Decimal(domestic_payer["drag_bil"]) > 0
    assert check_status(result, "T20") == "pass"


def test_t21_zero_denominator_sets_null_ratio(tmp_path: Path) -> None:
    config_dir = copy_config(tmp_path / "zero_d")
    filter_csv_rows(config_dir / "in_claim_opening_stock.csv", lambda row: row["claim_id"] == "C1")
    filter_csv_rows(config_dir / "in_claim_terms.csv", lambda row: row["claim_id"] == "C1")
    filter_csv_rows(config_dir / "in_exposure_state_opening.csv", lambda row: row["claim_id"] == "C1")

    result = run_rwtam(load_config(config_dir))
    monthly = result.rows("out_ratewall_monthly")[0]

    assert Decimal(monthly["N_bil"]) > 0
    assert Decimal(monthly["D_bil"]) == 0
    assert monthly["zero_D_flag"] == "true"
    assert monthly["RW_ratio"] == ""
    assert check_status(result, "T21") == "pass"


def test_fixed_and_zero_rate_claims_do_not_reprice(tmp_path: Path) -> None:
    config_dir = copy_config(tmp_path / "fixed_zero")
    append_claim(
        config_dir,
        {
            "state_id": "current_state_2026_01",
            "opening_month": "2026-01",
            "claim_id": "CFIX",
            "holder_sector": "households",
            "holder_cell": "hh_saver",
            "issuer_sector": "banks_depositories",
            "issuer_cell": "banks_depositories",
            "instrument": "fixed_test_claim",
            "incidence_mode": "direct",
            "principal_begin_bil": "120",
            "book_value_begin_bil": "120",
            "market_value_begin_bil": "120",
            "currency": "USD",
            "valuation_basis": "par",
            "report_group_id": "private_debt_service_report",
        },
    )
    append_term(config_dir, "CFIX", "fixed", "fixed_contract", contract_fixed_rate="0.05")
    append_exposure(config_dir, "CFIX", "120")
    append_claim(
        config_dir,
        {
            "state_id": "current_state_2026_01",
            "opening_month": "2026-01",
            "claim_id": "CZERO",
            "holder_sector": "households",
            "holder_cell": "hh_saver",
            "issuer_sector": "banks_depositories",
            "issuer_cell": "banks_depositories",
            "instrument": "zero_test_claim",
            "incidence_mode": "direct",
            "principal_begin_bil": "100",
            "book_value_begin_bil": "100",
            "market_value_begin_bil": "100",
            "currency": "USD",
            "valuation_basis": "par",
            "report_group_id": "private_debt_service_report",
        },
    )
    append_term(config_dir, "CZERO", "zero", "zero", zero_rate_flag="true")
    append_exposure(config_dir, "CZERO", "100")

    result = run_rwtam(load_config(config_dir))
    fixed_delta = [
        row
        for row in result.rows("out_flow_delta_monthly")
        if row["claim_id"] == "CFIX"
    ][0]
    zero_delta = [
        row
        for row in result.rows("out_flow_delta_monthly")
        if row["claim_id"] == "CZERO"
    ][0]

    assert Decimal(fixed_delta["delta_amount_bil"]) == 0
    assert Decimal(zero_delta["delta_amount_bil"]) == 0
    assert check_status(result, "T11") == "pass"


def assert_close(
    actual: Decimal,
    expected: Decimal,
    tolerance: Decimal = Decimal("1e-9"),
) -> None:
    assert abs(actual - expected) <= tolerance


def copy_config(target: Path) -> Path:
    shutil.copytree(CONFIG_DIR, target)
    return target


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def append_csv(path: Path, row: dict[str, str]) -> None:
    rows = read_csv(path)
    if rows:
        fieldnames = list(rows[0])
    else:
        with path.open(encoding="utf-8", newline="") as handle:
            fieldnames = csv.DictReader(handle).fieldnames or list(row)
    rows.append(row)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def append_flow_term(config_dir: Path, row: dict[str, str]) -> None:
    append_csv(config_dir / "cfg_flow_term_rule.csv", row)


def append_claim(config_dir: Path, row: dict[str, str]) -> None:
    append_csv(config_dir / "in_claim_opening_stock.csv", row)


def append_term(
    config_dir: Path,
    claim_id: str,
    rate_type: str,
    reference_rate_id: str,
    contract_fixed_rate: str = "0",
    zero_rate_flag: str = "false",
) -> None:
    append_csv(
        config_dir / "in_claim_terms.csv",
        {
            "claim_id": claim_id,
            "rate_type": rate_type,
            "reference_rate_id": reference_rate_id,
            "spread": "0",
            "contract_adjustment": "0",
            "contract_fixed_rate": contract_fixed_rate,
            "administered_rate": "0",
            "zero_rate_flag": zero_rate_flag,
            "reset_frequency_months": "1",
            "next_reset_month": "2026-01",
            "reset_lag": "0",
            "maturity_month": "perpetual",
            "maturity_bucket_id": "overnight_or_demand",
            "repricing_share": "1",
            "interest_payment_frequency": "monthly",
            "amortization_type": "interest_only",
            "cashflow_schedule_id": "none",
            "default_rule_id": "v0_all_performing",
            "fee_reward_subsidy_rule_id": "none",
        },
    )


def append_exposure(config_dir: Path, claim_id: str, principal: str) -> None:
    append_csv(
        config_dir / "in_exposure_state_opening.csv",
        {
            "state_id": "current_state_2026_01",
            "month": "2026-01",
            "claim_id": claim_id,
            "performing_principal_bil": principal,
            "distressed_paying_principal_bil": "0",
            "defaulted_nonperforming_principal_bil": "0",
            "cumulative_writeoff_bil": "0",
        },
    )


def update_parameter(config_dir: Path, parameter_id: str, value: str) -> None:
    path = config_dir / "cfg_assumption_parameter.csv"
    rows = read_csv(path)
    for row in rows:
        if row["parameter_id"] == parameter_id:
            row["parameter_value"] = value
            break
    write_csv(path, rows)


def filter_csv_rows(path: Path, keep) -> None:
    rows = [row for row in read_csv(path) if keep(row)]
    write_csv(path, rows)


def cell_row(result, cell_id: str) -> dict[str, str]:
    return [
        row
        for row in result.rows("out_real_effect_cell_monthly")
        if row["cell_id"] == cell_id
    ][0]


def check_status(result, check_id: str) -> str:
    return [
        row
        for row in result.rows("out_invariant_check")
        if row["check_id"] == check_id
    ][0]["status"]


def expected_ricardian_drag(config, result, offset: Decimal) -> Decimal:
    base_conversion_by_cell = {
        rule.cell_id: rule for rule in config.base_conversion_rules
    }
    expected = Decimal("0")
    for rule in config.ricardian_counterfactual_rules:
        reference_coeff = base_conversion_by_cell[rule.reference_cell].conversion_coeff
        for flow in result.rows("out_flow_delta_monthly"):
            if flow["payer_cell"] == rule.payer_cell:
                expected += Decimal(flow["delta_amount_bil"]) * offset * reference_coeff
    return expected
