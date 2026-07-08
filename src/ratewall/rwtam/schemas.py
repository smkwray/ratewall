"""CSV-backed schemas and validation for the RWTAM V0 engine."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from ratewall.rwtam.contract import BANNED_COLLAPSED_LABELS, SECTOR_IDS


class RwtamConfigError(ValueError):
    """Raised when RWTAM inputs violate the V0 contract."""


def _decimal(value: str, *, field: str) -> Decimal:
    try:
        return Decimal(value)
    except Exception as exc:  # pragma: no cover - Decimal gives varied messages.
        raise RwtamConfigError(f"invalid decimal for {field}: {value!r}") from exc


def _bool(value: str, *, field: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise RwtamConfigError(f"invalid boolean for {field}: {value!r}")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise RwtamConfigError(f"missing RWTAM config table: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RwtamConfigError(f"missing header in RWTAM config table: {path}")
        return list(reader.fieldnames), list(reader)


def _reject_banned_label(value: str, *, table: str, field: str) -> None:
    if value in BANNED_COLLAPSED_LABELS:
        raise RwtamConfigError(
            f"banned collapsed label {value!r} in {table}.{field}"
        )


@dataclass(frozen=True)
class Sector:
    sector_id: str
    sector_code: str
    display_name: str
    role: str
    is_base_sector: bool


@dataclass(frozen=True)
class CalendarMonth:
    month: str
    tau_month: Decimal


@dataclass(frozen=True)
class ScenarioPair:
    run_pair_id: str
    state_id: str
    baseline_scenario_id: str
    shock_scenario_id: str
    shock_id: str
    start_month: str
    end_month: str
    same_state_pair_flag: bool


@dataclass(frozen=True)
class Shock:
    shock_id: str
    shock_bps_year: Decimal
    shock_rate_delta_ann: Decimal
    application_rule: str


@dataclass(frozen=True)
class ReferenceRate:
    reference_rate_id: str
    rate_family: str
    driver_id: str
    description: str


@dataclass(frozen=True)
class ReferenceRatePath:
    scenario_id: str
    month: str
    reference_rate_id: str
    annual_rate: Decimal
    shock_pass_through_multiplier: Decimal
    shock_eligible_flag: bool


@dataclass(frozen=True)
class Instrument:
    instrument: str
    instrument_class: str
    reference_rate_id: str
    description: str


@dataclass(frozen=True)
class ClaimOpening:
    state_id: str
    opening_month: str
    claim_id: str
    holder_sector: str
    holder_cell: str
    issuer_sector: str
    issuer_cell: str
    instrument: str
    incidence_mode: str
    principal_begin_bil: Decimal
    book_value_begin_bil: Decimal
    market_value_begin_bil: Decimal
    currency: str
    valuation_basis: str
    report_group_id: str


@dataclass(frozen=True)
class ClaimTerm:
    claim_id: str
    rate_type: str
    reference_rate_id: str
    spread: Decimal
    contract_adjustment: Decimal
    contract_fixed_rate: Decimal
    administered_rate: Decimal
    zero_rate_flag: bool
    reset_frequency_months: int
    next_reset_month: str
    reset_lag: int
    maturity_month: str
    maturity_bucket_id: str
    repricing_share: Decimal
    interest_payment_frequency: str
    amortization_type: str
    cashflow_schedule_id: str
    default_rule_id: str
    fee_reward_subsidy_rule_id: str


@dataclass(frozen=True)
class ExposureState:
    state_id: str
    month: str
    claim_id: str
    performing_principal_bil: Decimal
    distressed_paying_principal_bil: Decimal
    defaulted_nonperforming_principal_bil: Decimal
    cumulative_writeoff_bil: Decimal

    @property
    def total_principal_bil(self) -> Decimal:
        return (
            self.performing_principal_bil
            + self.distressed_paying_principal_bil
            + self.defaulted_nonperforming_principal_bil
        )

    @property
    def paying_principal_bil(self) -> Decimal:
        return self.performing_principal_bil + self.distressed_paying_principal_bil


@dataclass(frozen=True)
class DefaultTransitionRule:
    default_rule_id: str
    transition_timing: str
    scheduled_payment_on_defaulted_flag: bool
    interest_accrual_on_defaulted_flag: bool


@dataclass(frozen=True)
class FlowTermRule:
    term_rule_id: str
    claim_id: str
    flow_kind: str
    payer_sector: str
    payer_cell: str
    receiver_sector: str
    receiver_cell: str
    baseline_amount_bil: Decimal
    shock_amount_bil: Decimal
    cash_flag: str
    stock_effect: str
    report_group_id: str
    real_conversion_eligible: bool


@dataclass(frozen=True)
class ConversionRule:
    conversion_rule_id: str
    cell_id: str
    sector_id: str
    effect_family: str
    activity_component: str
    conversion_coeff: Decimal
    domestic_eligibility_weight: Decimal
    input_basis_label: str
    valid_from: str
    valid_to: str
    generated_from: str = ""


@dataclass(frozen=True)
class AssumptionParameter:
    parameter_id: str
    parameter_value: Decimal
    input_basis_label: str
    description: str


@dataclass(frozen=True)
class RicardianCounterfactualRule:
    payer_cell: str
    payer_sector: str
    reference_cell: str
    parameter_id: str
    generated_coeff_basis: str


@dataclass(frozen=True)
class ReportGroupRule:
    report_view_id: str
    report_group_id: str
    channel_id: str
    additive_flag: bool
    exclusive_assignment_flag: bool
    classification_basis: str


@dataclass(frozen=True)
class RwtamConfig:
    base_path: Path
    sectors: tuple[Sector, ...]
    calendar_months: tuple[CalendarMonth, ...]
    scenario_pairs: tuple[ScenarioPair, ...]
    shocks: tuple[Shock, ...]
    reference_rates: tuple[ReferenceRate, ...]
    reference_rate_paths: tuple[ReferenceRatePath, ...]
    instruments: tuple[Instrument, ...]
    claim_opening_stock: tuple[ClaimOpening, ...]
    claim_terms: tuple[ClaimTerm, ...]
    exposure_states: tuple[ExposureState, ...]
    default_transition_rules: tuple[DefaultTransitionRule, ...]
    flow_term_rules: tuple[FlowTermRule, ...]
    base_conversion_rules: tuple[ConversionRule, ...]
    assumption_parameters: tuple[AssumptionParameter, ...]
    ricardian_counterfactual_rules: tuple[RicardianCounterfactualRule, ...]
    report_group_rules: tuple[ReportGroupRule, ...]

    @property
    def scenario_pair(self) -> ScenarioPair:
        if len(self.scenario_pairs) != 1:
            raise RwtamConfigError("RWTAM V0 expects exactly one scenario pair")
        return self.scenario_pairs[0]

    @property
    def ricardian_offset(self) -> Decimal:
        params = {
            parameter.parameter_id: parameter.parameter_value
            for parameter in self.assumption_parameters
        }
        if "ricardian_offset" not in params:
            raise RwtamConfigError("missing named parameter: ricardian_offset")
        return params["ricardian_offset"]

    @property
    def conversion_rules(self) -> tuple[ConversionRule, ...]:
        base_by_cell = _one_conversion_rule_per_cell(self.base_conversion_rules)
        generated: list[ConversionRule] = []
        parameter_by_id = {
            parameter.parameter_id: parameter.parameter_value
            for parameter in self.assumption_parameters
        }
        for rule in self.ricardian_counterfactual_rules:
            if rule.payer_cell in base_by_cell:
                raise RwtamConfigError(
                    "ricardian payer cells must not be bare conversion rows: "
                    f"{rule.payer_cell}"
                )
            if rule.reference_cell not in base_by_cell:
                raise RwtamConfigError(
                    f"ricardian reference cell missing conversion rule: "
                    f"{rule.reference_cell}"
                )
            if rule.parameter_id not in parameter_by_id:
                raise RwtamConfigError(
                    f"ricardian parameter missing: {rule.parameter_id}"
                )
            reference = base_by_cell[rule.reference_cell]
            offset = parameter_by_id[rule.parameter_id]
            generated.append(
                ConversionRule(
                    conversion_rule_id=f"generated::{rule.parameter_id}::{rule.payer_cell}",
                    cell_id=rule.payer_cell,
                    sector_id=rule.payer_sector,
                    effect_family=reference.effect_family,
                    activity_component=reference.activity_component,
                    conversion_coeff=offset * reference.conversion_coeff,
                    domestic_eligibility_weight=reference.domestic_eligibility_weight,
                    input_basis_label=f"generated_from_named_{rule.parameter_id}",
                    valid_from=reference.valid_from,
                    valid_to=reference.valid_to,
                    generated_from=rule.generated_coeff_basis,
                )
            )
        return self.base_conversion_rules + tuple(generated)


def load_config(base_path: Path) -> RwtamConfig:
    """Load and validate a RWTAM V0 config directory."""

    base_path = Path(base_path)
    config = RwtamConfig(
        base_path=base_path,
        sectors=_load_sectors(base_path / "cfg_sector.csv"),
        calendar_months=_load_calendar(base_path / "cfg_calendar_month.csv"),
        scenario_pairs=_load_scenario_pairs(base_path / "cfg_scenario_pair.csv"),
        shocks=_load_shocks(base_path / "cfg_shock.csv"),
        reference_rates=_load_reference_rates(base_path / "cfg_reference_rate.csv"),
        reference_rate_paths=_load_reference_paths(
            base_path / "in_reference_rate_path.csv"
        ),
        instruments=_load_instruments(base_path / "cfg_instrument.csv"),
        claim_opening_stock=_load_claims(base_path / "in_claim_opening_stock.csv"),
        claim_terms=_load_terms(base_path / "in_claim_terms.csv"),
        exposure_states=_load_exposures(base_path / "in_exposure_state_opening.csv"),
        default_transition_rules=_load_default_rules(
            base_path / "cfg_default_transition_rule.csv"
        ),
        flow_term_rules=_load_flow_terms(base_path / "cfg_flow_term_rule.csv"),
        base_conversion_rules=_load_conversion_rules(
            base_path / "cfg_real_conversion_rule.csv"
        ),
        assumption_parameters=_load_parameters(
            base_path / "cfg_assumption_parameter.csv"
        ),
        ricardian_counterfactual_rules=_load_ricardian_rules(
            base_path / "cfg_ricardian_counterfactual.csv"
        ),
        report_group_rules=_load_report_rules(base_path / "cfg_report_group_rule.csv"),
    )
    _validate_config(config)
    return config


def _load_sectors(path: Path) -> tuple[Sector, ...]:
    _, rows = _read_csv(path)
    return tuple(
        Sector(
            sector_id=row["sector_id"],
            sector_code=row["sector_code"],
            display_name=row["display_name"],
            role=row["role"],
            is_base_sector=_bool(row["is_base_sector"], field="is_base_sector"),
        )
        for row in rows
    )


def _load_calendar(path: Path) -> tuple[CalendarMonth, ...]:
    _, rows = _read_csv(path)
    return tuple(
        CalendarMonth(
            month=row["month"],
            tau_month=_decimal(row["tau_month"], field="tau_month"),
        )
        for row in rows
    )


def _load_scenario_pairs(path: Path) -> tuple[ScenarioPair, ...]:
    _, rows = _read_csv(path)
    return tuple(
        ScenarioPair(
            run_pair_id=row["run_pair_id"],
            state_id=row["state_id"],
            baseline_scenario_id=row["baseline_scenario_id"],
            shock_scenario_id=row["shock_scenario_id"],
            shock_id=row["shock_id"],
            start_month=row["start_month"],
            end_month=row["end_month"],
            same_state_pair_flag=_bool(
                row["same_state_pair_flag"], field="same_state_pair_flag"
            ),
        )
        for row in rows
    )


def _load_shocks(path: Path) -> tuple[Shock, ...]:
    _, rows = _read_csv(path)
    return tuple(
        Shock(
            shock_id=row["shock_id"],
            shock_bps_year=_decimal(row["shock_bps_year"], field="shock_bps_year"),
            shock_rate_delta_ann=_decimal(
                row["shock_rate_delta_ann"], field="shock_rate_delta_ann"
            ),
            application_rule=row["application_rule"],
        )
        for row in rows
    )


def _load_reference_rates(path: Path) -> tuple[ReferenceRate, ...]:
    _, rows = _read_csv(path)
    return tuple(
        ReferenceRate(
            reference_rate_id=row["reference_rate_id"],
            rate_family=row["rate_family"],
            driver_id=row["driver_id"],
            description=row["description"],
        )
        for row in rows
    )


def _load_reference_paths(path: Path) -> tuple[ReferenceRatePath, ...]:
    _, rows = _read_csv(path)
    return tuple(
        ReferenceRatePath(
            scenario_id=row["scenario_id"],
            month=row["month"],
            reference_rate_id=row["reference_rate_id"],
            annual_rate=_decimal(row["annual_rate"], field="annual_rate"),
            shock_pass_through_multiplier=_decimal(
                row["shock_pass_through_multiplier"],
                field="shock_pass_through_multiplier",
            ),
            shock_eligible_flag=_bool(
                row["shock_eligible_flag"], field="shock_eligible_flag"
            ),
        )
        for row in rows
    )


def _load_instruments(path: Path) -> tuple[Instrument, ...]:
    _, rows = _read_csv(path)
    return tuple(
        Instrument(
            instrument=row["instrument"],
            instrument_class=row["instrument_class"],
            reference_rate_id=row["reference_rate_id"],
            description=row["description"],
        )
        for row in rows
    )


def _load_claims(path: Path) -> tuple[ClaimOpening, ...]:
    _, rows = _read_csv(path)
    return tuple(
        ClaimOpening(
            state_id=row["state_id"],
            opening_month=row["opening_month"],
            claim_id=row["claim_id"],
            holder_sector=row["holder_sector"],
            holder_cell=row["holder_cell"],
            issuer_sector=row["issuer_sector"],
            issuer_cell=row["issuer_cell"],
            instrument=row["instrument"],
            incidence_mode=row["incidence_mode"],
            principal_begin_bil=_decimal(
                row["principal_begin_bil"], field="principal_begin_bil"
            ),
            book_value_begin_bil=_decimal(
                row["book_value_begin_bil"], field="book_value_begin_bil"
            ),
            market_value_begin_bil=_decimal(
                row["market_value_begin_bil"], field="market_value_begin_bil"
            ),
            currency=row["currency"],
            valuation_basis=row["valuation_basis"],
            report_group_id=row["report_group_id"],
        )
        for row in rows
    )


def _load_terms(path: Path) -> tuple[ClaimTerm, ...]:
    _, rows = _read_csv(path)
    return tuple(
        ClaimTerm(
            claim_id=row["claim_id"],
            rate_type=row["rate_type"],
            reference_rate_id=row["reference_rate_id"],
            spread=_decimal(row["spread"], field="spread"),
            contract_adjustment=_decimal(
                row["contract_adjustment"], field="contract_adjustment"
            ),
            contract_fixed_rate=_decimal(
                row["contract_fixed_rate"], field="contract_fixed_rate"
            ),
            administered_rate=_decimal(
                row["administered_rate"], field="administered_rate"
            ),
            zero_rate_flag=_bool(row["zero_rate_flag"], field="zero_rate_flag"),
            reset_frequency_months=int(row["reset_frequency_months"]),
            next_reset_month=row["next_reset_month"],
            reset_lag=int(row["reset_lag"]),
            maturity_month=row["maturity_month"],
            maturity_bucket_id=row["maturity_bucket_id"],
            repricing_share=_decimal(row["repricing_share"], field="repricing_share"),
            interest_payment_frequency=row["interest_payment_frequency"],
            amortization_type=row["amortization_type"],
            cashflow_schedule_id=row["cashflow_schedule_id"],
            default_rule_id=row["default_rule_id"],
            fee_reward_subsidy_rule_id=row["fee_reward_subsidy_rule_id"],
        )
        for row in rows
    )


def _load_exposures(path: Path) -> tuple[ExposureState, ...]:
    _, rows = _read_csv(path)
    return tuple(
        ExposureState(
            state_id=row["state_id"],
            month=row["month"],
            claim_id=row["claim_id"],
            performing_principal_bil=_decimal(
                row["performing_principal_bil"], field="performing_principal_bil"
            ),
            distressed_paying_principal_bil=_decimal(
                row["distressed_paying_principal_bil"],
                field="distressed_paying_principal_bil",
            ),
            defaulted_nonperforming_principal_bil=_decimal(
                row["defaulted_nonperforming_principal_bil"],
                field="defaulted_nonperforming_principal_bil",
            ),
            cumulative_writeoff_bil=_decimal(
                row["cumulative_writeoff_bil"], field="cumulative_writeoff_bil"
            ),
        )
        for row in rows
    )


def _load_default_rules(path: Path) -> tuple[DefaultTransitionRule, ...]:
    _, rows = _read_csv(path)
    return tuple(
        DefaultTransitionRule(
            default_rule_id=row["default_rule_id"],
            transition_timing=row["transition_timing"],
            scheduled_payment_on_defaulted_flag=_bool(
                row["scheduled_payment_on_defaulted_flag"],
                field="scheduled_payment_on_defaulted_flag",
            ),
            interest_accrual_on_defaulted_flag=_bool(
                row["interest_accrual_on_defaulted_flag"],
                field="interest_accrual_on_defaulted_flag",
            ),
        )
        for row in rows
    )


def _load_flow_terms(path: Path) -> tuple[FlowTermRule, ...]:
    _, rows = _read_csv(path)
    terms: list[FlowTermRule] = []
    for row in rows:
        if not any(row.values()):
            continue
        terms.append(
            FlowTermRule(
                term_rule_id=row["term_rule_id"],
                claim_id=row["claim_id"],
                flow_kind=row["flow_kind"],
                payer_sector=row["payer_sector"],
                payer_cell=row["payer_cell"],
                receiver_sector=row["receiver_sector"],
                receiver_cell=row["receiver_cell"],
                baseline_amount_bil=_decimal(
                    row["baseline_amount_bil"], field="baseline_amount_bil"
                ),
                shock_amount_bil=_decimal(
                    row["shock_amount_bil"], field="shock_amount_bil"
                ),
                cash_flag=row["cash_flag"],
                stock_effect=row["stock_effect"],
                report_group_id=row["report_group_id"],
                real_conversion_eligible=_bool(
                    row["real_conversion_eligible"], field="real_conversion_eligible"
                ),
            )
        )
    return tuple(terms)


def _load_conversion_rules(path: Path) -> tuple[ConversionRule, ...]:
    fieldnames, rows = _read_csv(path)
    forbidden_fields = {"leg_role", "flow_type", "instrument_class"}
    present_forbidden = forbidden_fields.intersection(fieldnames)
    if present_forbidden:
        raise RwtamConfigError(
            "cfg_real_conversion_rule must be keyed by cell only; "
            f"forbidden fields present: {', '.join(sorted(present_forbidden))}"
        )
    rules = tuple(
        ConversionRule(
            conversion_rule_id=row["conversion_rule_id"],
            cell_id=row["cell_id"],
            sector_id=row["sector_id"],
            effect_family=row["effect_family"],
            activity_component=row["activity_component"],
            conversion_coeff=_decimal(
                row["conversion_coeff"], field="conversion_coeff"
            ),
            domestic_eligibility_weight=_decimal(
                row["domestic_eligibility_weight"],
                field="domestic_eligibility_weight",
            ),
            input_basis_label=row["input_basis_label"],
            valid_from=row["valid_from"],
            valid_to=row["valid_to"],
        )
        for row in rows
    )
    _one_conversion_rule_per_cell(rules)
    return rules


def _load_parameters(path: Path) -> tuple[AssumptionParameter, ...]:
    _, rows = _read_csv(path)
    return tuple(
        AssumptionParameter(
            parameter_id=row["parameter_id"],
            parameter_value=_decimal(row["parameter_value"], field="parameter_value"),
            input_basis_label=row["input_basis_label"],
            description=row["description"],
        )
        for row in rows
    )


def _load_ricardian_rules(path: Path) -> tuple[RicardianCounterfactualRule, ...]:
    _, rows = _read_csv(path)
    return tuple(
        RicardianCounterfactualRule(
            payer_cell=row["payer_cell"],
            payer_sector=row["payer_sector"],
            reference_cell=row["reference_cell"],
            parameter_id=row["parameter_id"],
            generated_coeff_basis=row["generated_coeff_basis"],
        )
        for row in rows
    )


def _load_report_rules(path: Path) -> tuple[ReportGroupRule, ...]:
    _, rows = _read_csv(path)
    return tuple(
        ReportGroupRule(
            report_view_id=row["report_view_id"],
            report_group_id=row["report_group_id"],
            channel_id=row["channel_id"],
            additive_flag=_bool(row["additive_flag"], field="additive_flag"),
            exclusive_assignment_flag=_bool(
                row["exclusive_assignment_flag"], field="exclusive_assignment_flag"
            ),
            classification_basis=row["classification_basis"],
        )
        for row in rows
    )


def _one_conversion_rule_per_cell(
    rules: tuple[ConversionRule, ...],
) -> dict[str, ConversionRule]:
    by_cell: dict[str, ConversionRule] = {}
    for rule in rules:
        if rule.cell_id in by_cell:
            raise RwtamConfigError(
                "cfg_real_conversion_rule must contain exactly one magnitude per "
                f"cell; duplicate cell: {rule.cell_id}"
            )
        by_cell[rule.cell_id] = rule
    return by_cell


def _validate_config(config: RwtamConfig) -> None:
    sector_ids = tuple(sector.sector_id for sector in config.sectors)
    if sector_ids != SECTOR_IDS:
        raise RwtamConfigError(
            "cfg_sector must list exactly the eight RWTAM base sectors in order"
        )
    if not all(sector.is_base_sector for sector in config.sectors):
        raise RwtamConfigError("all cfg_sector rows must be base sectors in V0")

    sector_id_set = set(sector_ids)
    for sector in config.sectors:
        _reject_banned_label(sector.sector_id, table="cfg_sector", field="sector_id")

    claims_by_id = {claim.claim_id: claim for claim in config.claim_opening_stock}
    if len(claims_by_id) != len(config.claim_opening_stock):
        raise RwtamConfigError("duplicate claim_id in in_claim_opening_stock")
    terms_by_claim = {term.claim_id: term for term in config.claim_terms}
    if set(terms_by_claim) != set(claims_by_id):
        raise RwtamConfigError("claim terms must match opening claim ids exactly")

    instrument_ids = {instrument.instrument for instrument in config.instruments}
    reference_rate_ids = {
        reference_rate.reference_rate_id for reference_rate in config.reference_rates
    }
    default_rule_ids = {
        rule.default_rule_id for rule in config.default_transition_rules
    }
    conversion_cells = {rule.cell_id for rule in config.conversion_rules}

    for claim in config.claim_opening_stock:
        for field, value in [
            ("holder_sector", claim.holder_sector),
            ("issuer_sector", claim.issuer_sector),
            ("holder_cell", claim.holder_cell),
            ("issuer_cell", claim.issuer_cell),
            ("report_group_id", claim.report_group_id),
        ]:
            _reject_banned_label(
                value, table="in_claim_opening_stock", field=field
            )
        if claim.holder_sector not in sector_id_set:
            raise RwtamConfigError(f"unknown holder sector: {claim.holder_sector}")
        if claim.issuer_sector not in sector_id_set:
            raise RwtamConfigError(f"unknown issuer sector: {claim.issuer_sector}")
        if claim.instrument not in instrument_ids:
            raise RwtamConfigError(f"unknown instrument: {claim.instrument}")
        if claim.principal_begin_bil < 0:
            raise RwtamConfigError(f"negative claim principal: {claim.claim_id}")
        if claim.holder_cell not in conversion_cells:
            raise RwtamConfigError(f"missing holder-cell conversion: {claim.holder_cell}")
        if claim.issuer_cell not in conversion_cells:
            raise RwtamConfigError(f"missing issuer-cell conversion: {claim.issuer_cell}")

    for term in config.claim_terms:
        if term.reference_rate_id not in reference_rate_ids:
            raise RwtamConfigError(f"unknown reference rate: {term.reference_rate_id}")
        if term.default_rule_id not in default_rule_ids:
            raise RwtamConfigError(f"unknown default rule: {term.default_rule_id}")
        if term.repricing_share < 0 or term.repricing_share > 1:
            raise RwtamConfigError(f"repricing_share out of range: {term.claim_id}")

    exposure_keys = {
        (exposure.state_id, exposure.month, exposure.claim_id)
        for exposure in config.exposure_states
    }
    expected_exposure_keys = {
        (claim.state_id, claim.opening_month, claim.claim_id)
        for claim in config.claim_opening_stock
    }
    if exposure_keys != expected_exposure_keys:
        raise RwtamConfigError("exposure-state rows must match opening claim rows")
    for exposure in config.exposure_states:
        if (
            exposure.performing_principal_bil < 0
            or exposure.distressed_paying_principal_bil < 0
            or exposure.defaulted_nonperforming_principal_bil < 0
        ):
            raise RwtamConfigError(f"negative exposure partition: {exposure.claim_id}")
        claim = claims_by_id[exposure.claim_id]
        if exposure.total_principal_bil != claim.principal_begin_bil:
            raise RwtamConfigError(
                f"P/X/N partition does not sum to principal: {exposure.claim_id}"
            )

    for rule in config.default_transition_rules:
        if rule.scheduled_payment_on_defaulted_flag:
            raise RwtamConfigError(
                "V0 default rule must not schedule payments on defaulted exposure"
            )
        if rule.interest_accrual_on_defaulted_flag:
            raise RwtamConfigError(
                "V0 default rule must not accrue interest on defaulted exposure"
            )

    for rule in config.flow_term_rules:
        if rule.claim_id not in claims_by_id:
            raise RwtamConfigError(f"flow term references unknown claim: {rule.claim_id}")
        if rule.payer_sector not in sector_id_set:
            raise RwtamConfigError(f"unknown flow-term payer sector: {rule.payer_sector}")
        if rule.receiver_sector not in sector_id_set:
            raise RwtamConfigError(
                f"unknown flow-term receiver sector: {rule.receiver_sector}"
            )
        if rule.payer_cell not in conversion_cells:
            raise RwtamConfigError(f"unknown flow-term payer cell: {rule.payer_cell}")
        if rule.receiver_cell not in conversion_cells:
            raise RwtamConfigError(
                f"unknown flow-term receiver cell: {rule.receiver_cell}"
            )
        if rule.baseline_amount_bil < 0 or rule.shock_amount_bil < 0:
            raise RwtamConfigError(
                f"flow-term scenario amounts must be nonnegative: {rule.term_rule_id}"
            )

    pair = config.scenario_pair
    if not pair.same_state_pair_flag:
        raise RwtamConfigError("scenario pair must be same-state in V0")
    scenarios = {pair.baseline_scenario_id, pair.shock_scenario_id}
    path_keys = {
        (path.scenario_id, path.month, path.reference_rate_id)
        for path in config.reference_rate_paths
    }
    for month in config.calendar_months:
        for scenario_id in scenarios:
            for reference_rate_id in reference_rate_ids:
                key = (scenario_id, month.month, reference_rate_id)
                if key not in path_keys:
                    raise RwtamConfigError(f"missing reference path row: {key}")

    parameter_ids = {parameter.parameter_id for parameter in config.assumption_parameters}
    if "ricardian_offset" not in parameter_ids:
        raise RwtamConfigError("cfg_assumption_parameter must name ricardian_offset")

    report_rules = config.report_group_rules
    if not any(rule.additive_flag and rule.exclusive_assignment_flag for rule in report_rules):
        raise RwtamConfigError("cfg_report_group_rule must define an official view")
