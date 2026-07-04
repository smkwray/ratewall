from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import yaml

from ratewall.databook.build_legacy import _recipient_mpc_scenario_rows


ROOT = Path(__file__).resolve().parents[2]
PARAMETER_PACKS = ROOT / "configs" / "ratewall_parameter_packs.yml"

BLEND_ID = "BLEND_RECIPIENT_CURRENT_SPEND_V1"
EXPECTED_WEIGHTS = {
    "domestic_households_nonprofits": Decimal("0.55"),
    "domestic_nonfinancial_businesses": Decimal("0.10"),
    "banks": Decimal("0.15"),
    "mmf_ultimate_shareholders": Decimal("0.20"),
    "foreign_holders": Decimal("0.00"),
    "fed_soma_remittance_context": Decimal("0.00"),
}


def _parameter_pack(parameter: str) -> dict[str, object]:
    payload = yaml.safe_load(PARAMETER_PACKS.read_text(encoding="utf-8"))
    return next(
        row for row in payload["parameter_packs"] if row["parameter"] == parameter
    )


def test_exp2_recipient_blend_is_transparency_only_and_round_trips_to_flat_scalar() -> None:
    rows = _recipient_mpc_scenario_rows()

    assert {row["blend_id"] for row in rows} == {BLEND_ID}
    assert {
        row["recipient_group"]: Decimal(row["blend_component_weight"])
        for row in rows
    } == EXPECTED_WEIGHTS
    assert sum(Decimal(row["blend_component_weight"]) for row in rows) == Decimal("1.00")

    naive_base = sum(
        Decimal(row["blend_component_weight"]) * Decimal(row["mpc_base_assumption"])
        for row in rows
    )
    assert naive_base == Decimal("0.1475")
    assert {Decimal(row["blend_naive_base_share"]) for row in rows} == {naive_base}
    assert {Decimal(row["headline_flat_scalar"]) for row in rows} == {Decimal("0.12")}
    assert {Decimal(row["blend_reconciliation_factor"]) for row in rows} == {
        Decimal("0.12") / Decimal("0.1475")
    }

    normalized_total = sum(
        Decimal(row["normalized_blend_base_contribution"]) for row in rows
    )
    assert abs(normalized_total - Decimal("0.12")) < Decimal("1e-27")
    assert {Decimal(row["normalized_blend_base_share"]) for row in rows} == {
        Decimal("0.12")
    }

    assert {row["blend_use_status"] for row in rows} == {
        "transparency_only_reconciled_to_flat_scalar_not_headline_input"
    }
    disabled_fields = {
        "enters_main_ratio",
        "canonical_ratio_entry",
        "evidence_mode_enabled",
        "pricing_output_enabled",
        "tax_assumptions_enabled",
        "tax_output_enabled",
        "mpc_assumptions_enabled",
        "mpc_output_enabled",
        "holder_allocation_enabled",
        "tdc_chi_reuse_allowed",
        "incidence_claim_enabled",
        "welfare_claim_enabled",
    }
    for row in rows:
        assert {field: row[field] for field in disabled_fields} == {
            field: "false" for field in disabled_fields
        }


def test_exp2_recipient_blend_does_not_change_headline_treasury_share_band() -> None:
    pack = _parameter_pack("treasury_interest_demand_share")

    assert {
        "low": Decimal(str(pack["low"])),
        "base": Decimal(str(pack["base"])),
        "high": Decimal(str(pack["high"])),
    } == {
        "low": Decimal("0.05"),
        "base": Decimal("0.12"),
        "high": Decimal("0.25"),
    }
    assert pack["source_status"] == (
        "evidence1_literature_calibrated_assumption_mode_not_evidence_promotion"
    )
