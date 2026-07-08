from __future__ import annotations

import hashlib
from decimal import Decimal
from pathlib import Path

import pytest

from ratewall.rwtam.peg_defense import (
    build_peg_defense_exhibit,
    write_peg_defense_outputs,
)


PACK_DIR = Path("configs/rwtam/packs")
DEFAULT_GOLDEN_ROLLUP = Path("tests/fixtures/rwtam/golden_wave8/out_ratewall_rollup.csv")


@pytest.fixture(scope="module")
def peg_result(tmp_path_factory: pytest.TempPathFactory):
    return build_peg_defense_exhibit(
        PACK_DIR,
        output_root=tmp_path_factory.mktemp("rwtam_peg_defense"),
    )


def test_peg_defense_grid_fx_off_and_effectiveness_recomputes(peg_result, tmp_path: Path) -> None:
    golden_before = _sha256(DEFAULT_GOLDEN_ROLLUP)
    rows = peg_result.rows("out_peg_defense_exhibit")
    checks = {
        row["check_id"]: row["status"]
        for row in peg_result.rows("out_peg_defense_invariant_check")
    }

    assert len(rows) == 23
    assert {row["state_id"] for row in rows} == {
        "P1_modern_financialized",
        "P2_italy_1992_configuration",
        "P3_textbook_small_open_economy",
        "P4_uk_1992_variable_rate_defender",
        "P5_hk_currency_board_1997",
        "P5_hk_currency_board_now_deposits_400pct",
        "P5_argentina_motivated_dollarization_60pct",
        "P5_argentina_motivated_dollarization_80pct",
        "P6_postwar_us_pegged_engine_off",
        "P6_postwar_us_freed_beta_counterfactual",
    }
    assert {row["dose_mode"] for row in rows} == {"transient_12m"}
    spikes_by_state = {}
    for row in rows:
        spikes_by_state.setdefault(row["state_id"], set()).add(row["defense_spike_bp"])
    assert spikes_by_state["P1_modern_financialized"] == {"200", "500", "1000"}
    assert spikes_by_state["P2_italy_1992_configuration"] == {"200", "500", "1000"}
    assert spikes_by_state["P3_textbook_small_open_economy"] == {"200", "500", "1000"}
    assert spikes_by_state["P4_uk_1992_variable_rate_defender"] == {"200", "500"}
    assert spikes_by_state["P5_hk_currency_board_1997"] == {"300", "1500"}
    assert spikes_by_state["P5_hk_currency_board_now_deposits_400pct"] == {"300", "1500"}
    assert spikes_by_state["P5_argentina_motivated_dollarization_60pct"] == {"300", "1500"}
    assert spikes_by_state["P5_argentina_motivated_dollarization_80pct"] == {"300", "1500"}
    assert spikes_by_state["P6_postwar_us_pegged_engine_off"] == {"200", "500"}
    assert spikes_by_state["P6_postwar_us_freed_beta_counterfactual"] == {"200", "500"}
    assert all(row["claim_grade_label"] == "hypothetical_illustration;scenario_only" for row in rows)
    assert all(row["fx_channel_status"] == "off" for row in rows)
    assert all(Decimal(row["fx_net_export_drag_year1_base"]) == 0 for row in rows)
    assert all(row["fx_import_price_relief_status"] == "excluded_parallel_real_income_object" for row in rows)

    for row in rows:
        clean_expected = abs(Decimal(row["N_bil"]) - Decimal(row["D_bil"])) / (
            Decimal(row["defense_spike_bp"]) / Decimal("100")
        )
        deadweight_expected = Decimal(row["deadweight_bil"]) / (
            Decimal(row["clean_compression_bil"]) + Decimal(row["deadweight_bil"])
        )
        assert Decimal(row["clean_compression_per_100bp"]) == clean_expected
        assert Decimal(row["deadweight_share_of_compression"]) == deadweight_expected
        assert row["held_stance_comparison"].startswith("persistent_level:RW_ratio=")
        assert row["distress_activated"] in {"true", "false"}
        assert row["deadweight_activated"] in {"true", "false"}
        assert row["distress_deadweight_source_path"]
        assert row["exhibit_claim"]
        assert row["slot_summary"]
        assert row["compression_channel_memo"]

    assert set(checks.values()) == {"pass"}
    paths = write_peg_defense_outputs(peg_result, tmp_path)
    assert paths["out_peg_defense_exhibit"].exists()
    assert paths["out_peg_defense_p2_bridge"].exists()
    assert paths["out_peg_defense_notes"].exists()
    assert paths["out_peg_defense_slot_inputs"].exists()
    assert _sha256(DEFAULT_GOLDEN_ROLLUP) == golden_before


def test_peg_defense_notes_and_shape_checks(peg_result) -> None:
    rows = peg_result.rows("out_peg_defense_exhibit")
    notes = peg_result.rows("out_peg_defense_notes")
    slot_inputs = peg_result.rows("out_peg_defense_slot_inputs")
    p2 = [row for row in rows if row["state_id"] == "P2_italy_1992_configuration"]
    by_cell = {(row["state_id"], row["defense_spike_bp"]): row for row in rows}

    assert {row["note_id"] for row in notes}.issuperset(
        {
            "policy_moral",
            "no_reserve_drain_bop_dynamics",
            "no_sovereign_risk_premium",
            "no_rstar_wedge",
            "p2_not_calibrated_italy",
            "p4_uk_1992_claim",
            "p5_hk_currency_board_claim",
            "p6_postwar_us_claim",
            "dollarization_switch_claim",
            "obstfeld_rogoff_uk_mortgage_verify_before_quote",
        }
    )
    assert {row["state_id"] for row in slot_inputs}.issuperset(
        {
            "P4_uk_1992_variable_rate_defender",
            "P5_hk_currency_board_1997",
            "P6_postwar_us_pegged_engine_off",
        }
    )
    assert p2
    assert all(row["state_note"].startswith("stylized-not-calibrated-to-Italy") for row in p2)
    assert {row["defense_spike_bp"] for row in p2} == {"200", "500", "1000"}
    assert Decimal(by_cell[("P4_uk_1992_variable_rate_defender", "200")]["RW_ratio_at_spike"]) < Decimal("0.05")
    assert Decimal(by_cell[("P5_hk_currency_board_1997", "300")]["RW_ratio_at_spike"]) > Decimal(
        by_cell[("P4_uk_1992_variable_rate_defender", "200")]["RW_ratio_at_spike"]
    )
    assert Decimal(by_cell[("P5_hk_currency_board_now_deposits_400pct", "300")]["RW_ratio_at_spike"]) > Decimal(
        by_cell[("P5_hk_currency_board_1997", "300")]["RW_ratio_at_spike"]
    )
    assert by_cell[("P6_postwar_us_pegged_engine_off", "200")]["N_bil"] == "0"
    assert Decimal(by_cell[("P6_postwar_us_freed_beta_counterfactual", "200")]["RW_ratio_at_spike"]) > Decimal("0")
    assert Decimal(by_cell[("P5_argentina_motivated_dollarization_60pct", "300")]["N_bil"]) > Decimal(
        by_cell[("P5_argentina_motivated_dollarization_80pct", "300")]["N_bil"]
    )


def test_peg_defense_cell_values_and_p2_fx_bridge_are_pinned(peg_result) -> None:
    rows = {
        (row["state_id"], row["defense_spike_bp"]): row
        for row in peg_result.rows("out_peg_defense_exhibit")
    }
    pinned = {
        ("P1_modern_financialized", "200"): {
            "N_bil": "20.53113529546456750007620769",
            "D_bil": "311.3759074242390662605890038",
            "deadweight_bil": "5.848305746364472684027108274",
        },
        ("P2_italy_1992_configuration", "500"): {
            "N_bil": "98.72564960738854469312436331",
            "D_bil": "789.9946916809479356281809504",
            "deadweight_bil": "15.87661554820963982610380306",
        },
        ("P3_textbook_small_open_economy", "1000"): {
            "N_bil": "7.827562607601289935218255656",
            "D_bil": "1612.811332611704080567935341",
            "deadweight_bil": "55.51399657368554211058788862",
        },
        ("P4_uk_1992_variable_rate_defender", "200"): {
            "RW_ratio_at_spike": "0.03861899331194242147922341665",
            "N_bil": "13.37918220657061171850421039",
            "D_bil": "346.4404703276735492841223041",
        },
        ("P5_hk_currency_board_1997", "300"): {
            "RW_ratio_at_spike": "0.1700800781817555010557706934",
            "N_bil": "81.11829841294683930434582905",
            "deadweight_bil": "11.10963127892032054592855183",
        },
        ("P5_hk_currency_board_now_deposits_400pct", "300"): {
            "RW_ratio_at_spike": "0.7524075615077239692971508062",
            "N_bil": "347.6782633455738940442529763",
            "deposit_side_N_bil": "467.6934581149405561431902948",
        },
        ("P5_argentina_motivated_dollarization_80pct", "300"): {
            "RW_ratio_at_spike": "0.002146496617847890644110014014",
            "N_bil": "1.02375395784386571302220721",
            "deposit_N_rerouted_out_of_domestic_flow_bil": "80.09454445510297359132362184",
        },
        ("P6_postwar_us_pegged_engine_off", "200"): {
            "RW_ratio_at_spike": "0",
            "N_bil": "0",
            "D_bil": "308.0388001726284971228129364",
        },
        ("P6_postwar_us_freed_beta_counterfactual", "200"): {
            "RW_ratio_at_spike": "0.07268818749374688995966089668",
            "N_bil": "22.38391185344997439685542627",
            "D_bil": "307.9442840059202726858182105",
        },
    }
    for key, expected_values in pinned.items():
        row = rows[key]
        for column, expected in expected_values.items():
            assert row[column] == expected

    bridge = {
        row["dose_mode"]: row
        for row in peg_result.rows("out_peg_defense_p2_bridge")
    }
    assert set(bridge) == {"transient_12m", "persistent_level"}
    assert bridge["persistent_level"]["fx_on_RW_ratio"] == "0.09561997971969756412292018616"
    assert bridge["persistent_level"]["fx_off_RW_ratio"] == "0.1293816532985249532883381643"
    for row in bridge.values():
        assert row["diagnosis"] == "gap_closes_to_removed_fx_drag_in_D"
        assert row["D_gap_fx_on_minus_off_bil"] == "55.765"
        assert row["expected_removed_fx_drag_bil"] == "55.765"
        assert row["bridge_residual_bil"] == "0"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
