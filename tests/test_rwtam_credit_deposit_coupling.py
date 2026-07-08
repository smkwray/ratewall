from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.rwtam.credit_deposit_coupling import (
    BANDS,
    DEPOSIT_FAMILIES,
    LEAKAGE_SHARE_BANDS,
    build_credit_deposit_coupling_experiment,
    export_credit_deposit_off_pack,
    export_credit_deposit_pack,
)
from ratewall.rwtam.v1 import _d, _load_pack, _read_csv_rows, build_v1


PACK_DIR = Path("configs/rwtam/packs")


@pytest.fixture(scope="session")
def credit_deposit_result(tmp_path_factory: pytest.TempPathFactory):
    return build_credit_deposit_coupling_experiment(
        PACK_DIR,
        output_root=tmp_path_factory.mktemp("rwtam_credit_deposit"),
    )


def test_credit_deposit_default_off_export_path_reproduces_default_waterfall_byte_exact(
    tmp_path: Path,
) -> None:
    exported_off = export_credit_deposit_off_pack(PACK_DIR, tmp_path / "coupling_off")
    expected = build_v1(PACK_DIR, include_impulse_beta_comparator=False).rows(
        "out_phase6_waterfall_scaffold"
    )
    actual = build_v1(exported_off, include_impulse_beta_comparator=False).rows(
        "out_phase6_waterfall_scaffold"
    )
    assert actual == expected


def test_credit_deposit_on_moves_bank_deposit_stocks_by_loan_delta(tmp_path: Path) -> None:
    deposit_delta = {"low": Decimal("-10"), "base": Decimal("-20"), "high": Decimal("-30")}
    exported = export_credit_deposit_pack(
        PACK_DIR,
        tmp_path / "coupling_on",
        deposit_delta,
        DEPOSIT_FAMILIES,
    )
    before = _deposit_total(_read_csv_rows(PACK_DIR / "opening_stocks.csv"), "base")
    after = _deposit_total(_read_csv_rows(exported / "opening_stocks.csv"), "base")
    assert abs((after - before) - deposit_delta["base"]) < Decimal("0.000000000001")


def test_credit_deposit_leakage_share_mutation_is_engine_probe(tmp_path: Path) -> None:
    off_rows = build_v1(PACK_DIR, include_impulse_beta_comparator=False).rows(
        "out_phase6_waterfall_scaffold"
    )
    loan_delta = _base_loan_delta()
    low_pack = export_credit_deposit_pack(
        PACK_DIR,
        tmp_path / "low_leakage",
        {"low": Decimal("0"), "base": loan_delta * (Decimal("1") - Decimal("0.10")), "high": Decimal("0")},
        DEPOSIT_FAMILIES,
    )
    high_pack = export_credit_deposit_pack(
        PACK_DIR,
        tmp_path / "high_leakage",
        {"low": Decimal("0"), "base": loan_delta * (Decimal("1") - Decimal("0.45")), "high": Decimal("0")},
        DEPOSIT_FAMILIES,
    )
    off = _base_persistent_rw(build_v1(PACK_DIR, include_impulse_beta_comparator=False))
    low = _base_persistent_rw(build_v1(low_pack, include_impulse_beta_comparator=False))
    high = _base_persistent_rw(build_v1(high_pack, include_impulse_beta_comparator=False))

    assert low - off < high - off < 0
    assert build_v1(PACK_DIR, include_impulse_beta_comparator=False).rows(
        "out_phase6_waterfall_scaffold"
    ) == off_rows
    assert LEAKAGE_SHARE_BANDS["base"] == Decimal("0.25")


def test_credit_deposit_output_has_expected_rows_direction_and_labels(credit_deposit_result) -> None:
    rows = credit_deposit_result.rows("out_credit_deposit_coupling")
    assert len(rows) == 9
    assert {row["dose_mode"] for row in rows} == {"transient_12m", "persistent_level"}
    assert {row["horizon_id"] for row in rows} == {"year1_2026", "persistent_120m"}
    assert {row["band_structure"] for row in rows} == {"joint_band"}
    assert all(row["credit_supply_demand_leg"] == "off_diagnostic_only" for row in rows)
    base = next(
        row
        for row in rows
        if row["band"] == "base"
        and row["dose_mode"] == "persistent_level"
        and row["horizon_id"] == "year1_2026"
    )
    assert Decimal(base["deposit_stock_delta_bil"]) < 0
    assert Decimal(base["coupling_delta_RW"]) < 0


def test_credit_deposit_ablation_residual_reconciles_three_independent_runs(
    credit_deposit_result,
) -> None:
    rows = credit_deposit_result.rows("out_credit_deposit_coupling")
    assert all(row["ablation_additivity_assumed"] == "false" for row in rows)
    base = next(
        row
        for row in rows
        if row["band"] == "base"
        and row["dose_mode"] == "persistent_level"
        and row["horizon_id"] == "year1_2026"
    )
    full = Decimal(base["coupling_delta_RW"])
    checkable = Decimal(base["checkable_families_only_delta_RW"])
    savings_cd = Decimal(base["savings_cd_families_only_delta_RW"])
    residual = Decimal(base["family_subset_residual_delta_RW"])
    assert residual == full - checkable - savings_cd
    assert residual > 0
    assert residual == Decimal("0.00008513606598569686363360265")


def test_credit_deposit_band_cross_emits_leakage_elasticity_grid(
    credit_deposit_result,
) -> None:
    rows = credit_deposit_result.rows("out_credit_deposit_band_cross")
    assert len(rows) == 27
    assert {row["band_structure"] for row in rows} == {"leakage_elasticity_cross"}
    base_elasticity = [
        row
        for row in rows
        if row["horizon_id"] == "year1_2026"
        and row["dose_mode"] == "persistent_level"
        and row["elasticity_band"] == "base"
    ]
    by_leakage = {row["leakage_band"]: Decimal(row["coupling_delta_RW"]) for row in base_elasticity}
    assert by_leakage["low"] < by_leakage["base"] < by_leakage["high"] < 0


def test_credit_deposit_invariant_table_passes(credit_deposit_result) -> None:
    checks = credit_deposit_result.rows("out_credit_deposit_invariant_check")
    assert {row["check_id"] for row in checks} >= {
        "default_off_byte_exact",
        "direction_check_base_year1_persistent",
    }
    assert all(row["status"] == "pass" for row in checks)


def _deposit_total(rows: list[dict[str, str]], band: str) -> Decimal:
    return sum(
        _d(row[band])
        for row in rows
        if row["instrument_family"] in DEPOSIT_FAMILIES and "issuer=banks" in row["cell_or_sector"]
    )


def _base_loan_delta() -> Decimal:
    pack = _load_pack(PACK_DIR)
    phase6 = _load_pack(PACK_DIR / "phase6")
    loan_stock = sum(
        _d(row["base"])
        for row in pack["opening_stocks"]
        if row["instrument_family"]
        in {"c_and_i_depository_loans", "cre_mortgages_floating", "cre_mortgages_fixed"}
        and "holder=banks" in row["cell_or_sector"]
    )
    tightening = next(
        _d(row["base"])
        for row in phase6["conversion_parameters"]
        if row["parameter_id"] == "credit_supply_sloos_net_tightening_grid"
    )
    response = next(
        _d(row["base"])
        for row in phase6["conversion_parameters"]
        if row["parameter_id"]
        == "credit_supply_owner_diagnostic_new_lending_quantity_response_per_10pp_sloos"
    )
    return -loan_stock * tightening / Decimal("10") * response


def _base_persistent_rw(result) -> Decimal:
    row = next(
        item
        for item in result.rows("out_phase6_waterfall_scaffold")
        if item["period_type"] == "annual"
        and item["period"] == "2026"
        and item["band"] == "base"
        and item["ricardian_offset"] == "0"
        and item["headline_status"] == "final_rw_full"
    )
    return Decimal(row["cumulative_RW"])
