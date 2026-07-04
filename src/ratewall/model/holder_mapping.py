"""Disabled holder-mapping contract for public-liability cash-flow context."""

from __future__ import annotations

from dataclasses import dataclass


SCHEMA_VERSION = "holder_mapping_design_v0_non_final"
DISABLED_ALLOCATION_SCHEMA_VERSION = "holder_final_owner_allocation_v0_disabled"
DISABLED_DESIGN_LEDGER_SCHEMA_VERSION = "holder_allocation_design_ledger_v0_disabled"


@dataclass(frozen=True)
class HolderMappingSwitches:
    holder_bridge_enabled: bool = False
    tax_assumptions_enabled: bool = False
    mpc_assumptions_enabled: bool = False
    welfare_incidence_enabled: bool = False

    @property
    def incidence_claim_enabled(self) -> bool:
        return (
            self.holder_bridge_enabled
            and self.tax_assumptions_enabled
            and self.mpc_assumptions_enabled
            and self.welfare_incidence_enabled
        )


def disabled_mapping_design(
    *,
    gate_component: str,
    source_inputs: str,
    switches: HolderMappingSwitches | None = None,
) -> dict[str, str]:
    switches = switches or HolderMappingSwitches()
    stages = {
        "foreign_stock_context": "sector_stock_context",
        "money_fund_direct_treasury_context": "intermediary_portfolio_context",
        "money_fund_repo_collateral_context": "collateral_channel_context",
        "sec_nmfp_mspd_cusip_overlap": "cusip_coverage_gate",
        "valuation_input_gate": "valuation_input_gate",
        "final_owner_mapping_readiness": "final_owner_design_gate",
    }
    match_keys = {
        "foreign_stock_context": "sector_date",
        "money_fund_direct_treasury_context": "sector_channel_date",
        "money_fund_repo_collateral_context": "collateral_channel_date",
        "sec_nmfp_mspd_cusip_overlap": "cusip",
        "valuation_input_gate": "cusip",
        "final_owner_mapping_readiness": "not_enabled",
    }
    return {
        "mapping_schema_version": SCHEMA_VERSION,
        "mapping_stage": stages.get(gate_component, "not_enabled"),
        "source_holder_layer": source_inputs,
        "security_match_key": match_keys.get(gate_component, "not_enabled"),
        "holder_bridge_enabled": _bool_string(switches.holder_bridge_enabled),
        "tax_assumptions_enabled": _bool_string(switches.tax_assumptions_enabled),
        "mpc_assumptions_enabled": _bool_string(switches.mpc_assumptions_enabled),
        "final_owner_bridge_required": "true",
        "allocation_weight_status": "not_enabled_requires_policy_switches",
        "incidence_claim_enabled": _bool_string(switches.incidence_claim_enabled),
    }


def disabled_scenario_context() -> dict[str, str]:
    switches = HolderMappingSwitches()
    return {
        "final_owner_mapping_ready": "false",
        "final_owner_allocation_output_status": "disabled_no_weights_no_incidence",
        "final_owner_allocation_schema_version": DISABLED_ALLOCATION_SCHEMA_VERSION,
        "allocation_design_ledger_status": "disabled_design_layers_no_weights",
        "allocation_design_ledger_schema_version": DISABLED_DESIGN_LEDGER_SCHEMA_VERSION,
        "welfare_incidence_enabled": _bool_string(switches.welfare_incidence_enabled),
        "holder_mapping_schema_version": SCHEMA_VERSION,
        "holder_mapping_stage": "readiness_schema_not_enabled",
        "holder_bridge_enabled": _bool_string(switches.holder_bridge_enabled),
        "tax_assumptions_enabled": _bool_string(switches.tax_assumptions_enabled),
        "mpc_assumptions_enabled": _bool_string(switches.mpc_assumptions_enabled),
        "incidence_claim_enabled": _bool_string(switches.incidence_claim_enabled),
    }


def disabled_final_owner_allocation_rows(
    *,
    gate_rows: list[dict[str, str]],
    switches: HolderMappingSwitches | None = None,
) -> list[dict[str, str]]:
    """Build a disabled allocation output from gate rows.

    The rows expose schema and blocker state only. They intentionally do not
    emit holder weights, cash-flow allocations, tax effects, MPCs, or welfare
    incidence.
    """

    switches = switches or HolderMappingSwitches()
    rows = []
    for row in gate_rows:
        design = disabled_mapping_design(
            gate_component=row["gate_component"],
            source_inputs=row["source_inputs"],
            switches=switches,
        )
        rows.append(
            {
                "allocation_schema_version": DISABLED_ALLOCATION_SCHEMA_VERSION,
                "source_gate_component": row["gate_component"],
                "source_gate_status": row["status"],
                "mapping_schema_version": design["mapping_schema_version"],
                "mapping_stage": design["mapping_stage"],
                "source_holder_layer": design["source_holder_layer"],
                "security_match_key": design["security_match_key"],
                "candidate_final_owner_group": "not_allocated",
                "allocation_weight": "",
                "allocation_weight_status": design["allocation_weight_status"],
                "allocated_cashflow_bil": "",
                "tax_assumption": "",
                "mpc_assumption": "",
                "welfare_incidence_metric": "",
                "holder_bridge_enabled": design["holder_bridge_enabled"],
                "tax_assumptions_enabled": design["tax_assumptions_enabled"],
                "mpc_assumptions_enabled": design["mpc_assumptions_enabled"],
                "welfare_incidence_enabled": _bool_string(
                    switches.welfare_incidence_enabled
                ),
                "incidence_claim_enabled": design["incidence_claim_enabled"],
                "output_status": "disabled_no_weights_no_incidence",
                "blocker_note": (
                    "Final-owner allocation remains disabled until holder bridge, "
                    "tax, MPC, and welfare switches are explicitly enabled and "
                    "validated."
                ),
                "claim_boundary": "disabled_schema_not_final_owner_incidence",
            }
        )
    return rows


def disabled_allocation_design_ledger_rows(
    *,
    gate_rows: list[dict[str, str]],
    switches: HolderMappingSwitches | None = None,
) -> list[dict[str, str]]:
    """Build a layer-by-layer disabled allocation design ledger."""

    switches = switches or HolderMappingSwitches()
    rows = []
    for row in gate_rows:
        design = disabled_mapping_design(
            gate_component=row["gate_component"],
            source_inputs=row["source_inputs"],
            switches=switches,
        )
        for layer in _disabled_design_layers():
            rows.append(
                {
                    "design_ledger_schema_version": DISABLED_DESIGN_LEDGER_SCHEMA_VERSION,
                    "source_gate_component": row["gate_component"],
                    "source_gate_status": row["status"],
                    "mapping_schema_version": design["mapping_schema_version"],
                    "mapping_stage": design["mapping_stage"],
                    "design_layer": layer["design_layer"],
                    "layer_order": layer["layer_order"],
                    "required_bridge": layer["required_bridge"],
                    "source_layer_input": layer["source_layer_input"],
                    "output_field_family": layer["output_field_family"],
                    "switch_required": layer["switch_required"],
                    "switch_enabled": layer["switch_enabled"],
                    "weight_output_enabled": "false",
                    "cashflow_output_enabled": "false",
                    "tax_output_enabled": "false",
                    "mpc_output_enabled": "false",
                    "welfare_output_enabled": "false",
                    "incidence_claim_enabled": design["incidence_claim_enabled"],
                    "design_status": "disabled_layer_contract_only",
                    "blocker_note": layer["blocker_note"],
                    "claim_boundary": "disabled_design_ledger_not_incidence",
                }
            )
    return rows


def _disabled_design_layers() -> tuple[dict[str, str], ...]:
    return (
        {
            "design_layer": "legal_holder",
            "layer_order": "1",
            "required_bridge": "security_or_sector_to_legal_holder",
            "source_layer_input": "TIC/Z.1/OFR/SEC/MSPD holder or security context",
            "output_field_family": "legal_holder_weight",
            "switch_required": "holder_bridge_enabled",
            "switch_enabled": "false",
            "blocker_note": "Legal-holder bridge is disabled; no legal-holder weights are emitted.",
        },
        {
            "design_layer": "intermediary",
            "layer_order": "2",
            "required_bridge": "legal_holder_to_intermediary_channel",
            "source_layer_input": "SEC N-MFP/OFR money-fund and repo channel context",
            "output_field_family": "intermediary_channel_weight",
            "switch_required": "holder_bridge_enabled",
            "switch_enabled": "false",
            "blocker_note": "Intermediary bridge is disabled; no intermediary allocation is emitted.",
        },
        {
            "design_layer": "beneficial_owner",
            "layer_order": "3",
            "required_bridge": "intermediary_to_beneficial_owner",
            "source_layer_input": "future SCF/DFA/fund-owner bridge inputs",
            "output_field_family": "beneficial_owner_weight",
            "switch_required": "holder_bridge_enabled",
            "switch_enabled": "false",
            "blocker_note": "Beneficial-owner bridge is disabled; no final-owner incidence is emitted.",
        },
        {
            "design_layer": "taxable_owner",
            "layer_order": "4",
            "required_bridge": "beneficial_owner_to_tax_treatment",
            "source_layer_input": "future taxable account and tax-rate assumptions",
            "output_field_family": "after_tax_cashflow",
            "switch_required": "tax_assumptions_enabled",
            "switch_enabled": "false",
            "blocker_note": "Tax assumptions are disabled; no after-tax allocation is emitted.",
        },
        {
            "design_layer": "mpc",
            "layer_order": "5",
            "required_bridge": "taxable_owner_to_mpc_assumption",
            "source_layer_input": "future MPC by holder/income/wealth group",
            "output_field_family": "consumption_impulse",
            "switch_required": "mpc_assumptions_enabled",
            "switch_enabled": "false",
            "blocker_note": "MPC assumptions are disabled; no consumption impulse is emitted.",
        },
        {
            "design_layer": "welfare",
            "layer_order": "6",
            "required_bridge": "mpc_layer_to_welfare_loss_function",
            "source_layer_input": "future normative welfare weights",
            "output_field_family": "welfare_incidence_metric",
            "switch_required": "welfare_incidence_enabled",
            "switch_enabled": "false",
            "blocker_note": "Welfare switch is disabled; no welfare incidence metric is emitted.",
        },
    )


def _bool_string(value: bool) -> str:
    return "true" if value else "false"
