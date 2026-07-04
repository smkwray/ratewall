from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

from ratewall.databook.tdcsim_contracts import (
    EXPECTED_TDCSIM_CONTRACT_VERSION,
    TDCSIM_REQUIRED_COMPONENT_FIELDS,
    TDCSIM_REQUIRED_SUMMARY_FIELDS,
    TDCSIM_SUMMARY_LABEL_FIELDS,
    tdc_forward_projection_surface_rows,
    tdcsim_projection_contract_bridge_rows,
)


def _write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _contract_dir(
    tmp_path: Path,
    *,
    contract_version: str = EXPECTED_TDCSIM_CONTRACT_VERSION,
    summary_overrides: dict[str, str] | None = None,
    component_overrides: dict[str, str] | None = None,
    drop_summary_fields: set[str] | None = None,
) -> Path:
    contract_dir = tmp_path / "tdcsim_contract"
    contract_dir.mkdir(parents=True)
    (contract_dir / "tdcsim_ratewall_manifest.json").write_text(
        json.dumps(
            {
                "contract_version": contract_version,
                "config_hash": "test_hash",
                "validation": {
                    "validation_status": "pass",
                    "failure_reasons": "",
                },
            }
        ),
        encoding="utf-8",
    )
    summary = {field: "0" for field in TDCSIM_REQUIRED_SUMMARY_FIELDS}
    summary.update(
        {
            "schema_version": contract_version,
            "simulation_version": "tdcsim_ratewall_contract_test",
            "scenario_id": "current_mix_baseline",
            "quarter": "2026Q2",
            "tdc_change_bil": "100",
            "tdc_fiscal_flow_bil": "5",
            "tdc_debt_service_principal_to_du_bil": "20",
            "tdc_debt_service_interest_to_du_bil": "10",
            "tdc_auction_absorption_du_bil": "-2",
            "tdc_secondary_trades_bil": "0",
            "tdc_other_bil": "0",
            "overlap_cashflow_bil": "10",
            "tdc_change_ex_overlap_bil": "90",
            "gross_issuance_cash_proceeds_bil": "200",
            "gross_issuance_proceeds_absorbed_by_du_bil": "2",
            "principal_redeemed_total_bil": "20",
            "bill_discount_interest_to_du_bil": "3",
            "coupon_interest_to_du_bil": "7",
            "frn_interest_to_du_bil": "11",
            "tips_coupon_interest_to_du_bil": "13",
            "tips_inflation_compensation_to_du_bil": "17",
            "mmf_deposit_pass_through": "0.97",
            "mmf_deposit_pass_through_status": "source_backed_measurement",
            "component_sum_bil": "100",
            "component_sum_error_bil": "0",
            "primary_flow_status": "aggregate_cash_proxy",
            "secondary_trade_status": "explicit_zero",
            "other_status": "explicit_zero",
            "claim_boundary": "test_contract",
        }
    )
    summary.update(summary_overrides or {})
    summary_fields = [
        "schema_version",
        "simulation_version",
        *sorted(TDCSIM_REQUIRED_SUMMARY_FIELDS),
        "primary_flow_status",
        "secondary_trade_status",
        "other_status",
        "claim_boundary",
    ]
    summary_fields = [
        field for field in summary_fields if field not in (drop_summary_fields or set())
    ]
    _write_csv(
        contract_dir / "tdcsim_ratewall_quarterly_summary.csv",
        summary_fields,
        [{field: summary.get(field, "") for field in summary_fields}],
    )
    component = {field: "" for field in TDCSIM_REQUIRED_COMPONENT_FIELDS}
    component.update(
        {
            "scenario_id": "current_mix_baseline",
            "quarter": "2026Q2",
            "component_key": "coupon_interest_to_du",
            "holder_bucket": "Private",
            "ratewall_perimeter": "DU",
            "security_type": "Fixed",
            "cash_component_key": "coupon_interest",
            "amount_bil": "7",
            "enters_direct_interest_support": "true",
            "enters_tdc_deposit_support_default": "false",
        }
    )
    component.update(component_overrides or {})
    _write_csv(
        contract_dir / "tdcsim_ratewall_quarterly_components.csv",
        sorted(TDCSIM_REQUIRED_COMPONENT_FIELDS),
        [component],
    )
    _write_csv(
        contract_dir / "tdcsim_ratewall_source_registry.csv",
        ["source_family", "source_key"],
        [],
    )
    return contract_dir


def test_tdcsim_contract_ingest_requires_current_contract_version(tmp_path: Path) -> None:
    contract_dir = _contract_dir(tmp_path, contract_version="0.2.0")

    rows = tdcsim_projection_contract_bridge_rows(contract_dir)
    surface_rows = tdc_forward_projection_surface_rows(contract_dir)

    assert rows == [
        {
            "scenario_id": "",
            "quarter": "",
            "tdcsim_contract_version": "0.2.0",
            "tdcsim_manifest_hash": "test_hash",
            "tdc_change_bil": "0",
            "tdc_fiscal_flow_bil": "0",
            "tdc_debt_service_principal_to_du_bil": "0",
            "tdc_debt_service_interest_to_du_bil": "0",
            "tdc_auction_absorption_du_bil": "0",
            "tdc_secondary_trades_bil": "0",
            "tdc_other_bil": "0",
            "overlap_cashflow_bil": "0",
            "tdc_change_ex_overlap_bil": "0",
            "gross_issuance_cash_proceeds_bil": "0",
            "gross_issuance_proceeds_absorbed_by_du_bil": "0",
            **{field: "0" for field in TDCSIM_SUMMARY_LABEL_FIELDS},
            "component_sum_bil": "0",
            "component_sum_error_bil": "0",
            "primary_flow_status": "",
            "secondary_trade_status": "",
            "other_status": "",
            "contract_ingest_status": "fail_closed_stale_contract_version",
            "assumption_mode": "true",
            "enters_main_ratio": "false",
            "evidence_mode_enabled": "false",
            "canonical_ratio_entry": "false",
            "claim_boundary": (
                "ratewall_tdcsim_contract_ingest_assumption_mode_not_evidence"
            ),
            "empirical_claim_enabled": "false",
            "policy_failure_claim_enabled": "false",
            "pricing_output_enabled": "false",
            "incidence_claim_enabled": "false",
            "welfare_claim_enabled": "false",
            "tax_output_enabled": "false",
            "mpc_output_enabled": "false",
            "holder_allocation_enabled": "false",
            "reset_calendar_construction_enabled": "false",
            "raw_rate_shock_enabled": "false",
            "causal_financialization_claim_enabled": "false",
        }
    ]
    assert {row["contract_ingest_status"] for row in surface_rows} == {
        "fail_closed_stale_contract_version"
    }


def test_tdcsim_contract_bridge_carries_exported_treasury_labels(
    tmp_path: Path,
) -> None:
    contract_dir = _contract_dir(tmp_path)

    rows = tdcsim_projection_contract_bridge_rows(contract_dir)
    surface_rows = tdc_forward_projection_surface_rows(contract_dir)

    assert len(rows) == 1
    row = rows[0]
    assert row["contract_ingest_status"] == "pass"
    assert row["tdcsim_contract_version"] == EXPECTED_TDCSIM_CONTRACT_VERSION
    assert row["gross_issuance_cash_proceeds_bil"] == "200"
    assert row["principal_redeemed_total_bil"] == "20"
    assert row["bill_discount_interest_to_du_bil"] == "3"
    assert row["coupon_interest_to_du_bil"] == "7"
    assert row["frn_interest_to_du_bil"] == "11"
    assert row["tips_coupon_interest_to_du_bil"] == "13"
    assert row["tips_inflation_compensation_to_du_bil"] == "17"
    assert row["mmf_deposit_pass_through"] == "0.97"
    assert {
        Decimal(row["tdc_deposit_support_base_ex_direct_interest_bil"])
        for row in surface_rows
    } == {Decimal("90")}


def test_tdcsim_contract_ingest_fails_closed_on_bad_labels(tmp_path: Path) -> None:
    stale_schema_dir = _contract_dir(
        tmp_path / "missing_field",
        drop_summary_fields={"bill_discount_interest_to_du_bil"},
    )
    bad_overlap_dir = _contract_dir(
        tmp_path / "bad_overlap",
        summary_overrides={"tdc_change_ex_overlap_bil": "89"},
    )
    dual_component_dir = _contract_dir(
        tmp_path / "dual_component",
        component_overrides={
            "enters_direct_interest_support": "true",
            "enters_tdc_deposit_support_default": "true",
        },
    )

    assert tdcsim_projection_contract_bridge_rows(stale_schema_dir)[0][
        "contract_ingest_status"
    ] == "fail_closed_missing_contract_fields"
    assert tdcsim_projection_contract_bridge_rows(bad_overlap_dir)[0][
        "contract_ingest_status"
    ] == "fail_closed_contract_identity_failed"
    assert tdcsim_projection_contract_bridge_rows(dual_component_dir)[0][
        "contract_ingest_status"
    ] == "fail_closed_contract_identity_failed"
