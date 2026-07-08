from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.rwtam.bank_retention_sink import (
    DEPOSIT_FAMILIES,
    PAYOUT_RECYCLE_SHARE_BANDS,
    build_bank_retention_sink_experiment,
    export_bank_retention_off_pack,
    export_bank_retention_pack,
)
from ratewall.rwtam.v1 import _d, _read_csv_rows, build_v1


PACK_DIR = Path("configs/rwtam/packs")


@pytest.fixture(scope="session")
def bank_retention_result(tmp_path_factory: pytest.TempPathFactory):
    return build_bank_retention_sink_experiment(
        PACK_DIR,
        output_root=tmp_path_factory.mktemp("rwtam_bank_retention"),
    )


def test_bank_retention_default_off_export_path_reproduces_default_waterfall_byte_exact(
    tmp_path: Path,
) -> None:
    exported_off = export_bank_retention_off_pack(PACK_DIR, tmp_path / "sink_off")
    expected = build_v1(PACK_DIR, include_impulse_beta_comparator=False).rows(
        "out_phase6_waterfall_scaffold"
    )
    actual = build_v1(exported_off, include_impulse_beta_comparator=False).rows(
        "out_phase6_waterfall_scaffold"
    )
    assert actual == expected


def test_bank_retention_on_moves_bank_deposit_stocks_by_sink_delta(tmp_path: Path) -> None:
    deposit_delta = {"low": Decimal("-4"), "base": Decimal("-5"), "high": Decimal("-6")}
    exported = export_bank_retention_pack(
        PACK_DIR,
        tmp_path / "sink_on",
        deposit_delta,
        DEPOSIT_FAMILIES,
    )
    before = _deposit_total(_read_csv_rows(PACK_DIR / "opening_stocks.csv"), "base")
    after = _deposit_total(_read_csv_rows(exported / "opening_stocks.csv"), "base")
    assert abs((after - before) - deposit_delta["base"]) < Decimal("0.000000000001")


def test_bank_retention_output_has_expected_rows_direction_and_caveat(
    bank_retention_result,
) -> None:
    rows = bank_retention_result.rows("out_bank_retention_sink")
    assert len(rows) == 18
    assert {row["row_type"] for row in rows} == {
        "bank_retention_sink",
        "combined_credit_deposit_plus_bank_retention",
    }
    base = _base_bank_row(rows)
    assert Decimal(base["deposit_stock_delta_bil"]) < 0
    assert Decimal(base["delta_RW"]) < 0
    assert base["ablation_additivity_assumed"] == "false"
    caveats = bank_retention_result.rows("out_bank_retention_caveats")
    assert any(row["caveat_id"] == "m2_perimeter_note" for row in caveats)


def test_bank_retention_recycle_share_probe_moves_rw_monotonically(
    bank_retention_result,
) -> None:
    rows = [
        row
        for row in bank_retention_result.rows("out_bank_retention_sink")
        if row["row_type"] == "bank_retention_sink"
        and row["dose_mode"] == "persistent_level"
        and row["horizon_id"] == "year1_2026"
    ]
    by_band = {row["band"]: Decimal(row["delta_RW"]) for row in rows}
    assert PAYOUT_RECYCLE_SHARE_BANDS["low"] < PAYOUT_RECYCLE_SHARE_BANDS["base"]
    assert by_band["low"] < by_band["base"] < by_band["high"] < 0


def test_bank_retention_ablation_residual_reconciles_independent_runs(
    bank_retention_result,
) -> None:
    base = _base_bank_row(bank_retention_result.rows("out_bank_retention_sink"))
    full = Decimal(base["delta_RW"])
    checkable = Decimal(base["checkable_families_only_delta_RW"])
    savings_cd = Decimal(base["savings_cd_families_only_delta_RW"])
    residual = Decimal(base["family_subset_residual_delta_RW"])
    assert residual == full - checkable - savings_cd
    assert residual == Decimal("0.00000422654141283558249608518")


def test_bank_retention_combined_sinks_interaction_is_from_independent_runs(
    bank_retention_result,
) -> None:
    rows = bank_retention_result.rows("out_bank_retention_sink")
    combined = next(
        row
        for row in rows
        if row["row_type"] == "combined_credit_deposit_plus_bank_retention"
        and row["band"] == "base"
        and row["dose_mode"] == "persistent_level"
        and row["horizon_id"] == "year1_2026"
    )
    bank = _base_bank_row(rows)
    interaction = Decimal(combined["pairwise_interaction_delta_RW"])
    expected = (
        Decimal(combined["combined_sinks_delta_RW"])
        - Decimal(combined["credit_deposit_only_delta_RW"])
        - Decimal(bank["delta_RW"])
    )
    assert interaction == expected
    assert interaction != 0


def test_bank_retention_invariant_table_passes(bank_retention_result) -> None:
    checks = bank_retention_result.rows("out_bank_retention_invariant_check")
    assert {row["status"] for row in checks} == {"pass"}


def _base_bank_row(rows: list[dict[str, str]]) -> dict[str, str]:
    return next(
        row
        for row in rows
        if row["row_type"] == "bank_retention_sink"
        and row["band"] == "base"
        and row["dose_mode"] == "persistent_level"
        and row["horizon_id"] == "year1_2026"
    )


def _deposit_total(rows: list[dict[str, str]], band: str) -> Decimal:
    return sum(
        _d(row[band])
        for row in rows
        if row["instrument_family"] in DEPOSIT_FAMILIES and "issuer=banks" in row["cell_or_sector"]
    )
