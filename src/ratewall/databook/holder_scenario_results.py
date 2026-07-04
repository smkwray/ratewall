"""Holder-mix scenario result surface and PNG diagnostics."""

from __future__ import annotations

import csv
import gzip
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from ratewall.databook.model_artifact_store import (
    ArtifactManifestView,
    artifact_manifest_exists,
)

HOLDER_SCENARIO_IDS = (
    "tdcsim_holder_source_current_mix_v1",
    "tdcsim_holder_source_reserve_user_absorption_v1",
    "tdcsim_holder_source_domestic_nonbank_absorption_v1",
)

HOLDER_SCENARIO_RESULT_FIELDS = [
    "holder_scenario_result_row_id",
    "fiscal_year",
    "scenario_id",
    "scenario_label",
    "baseline_scenario_id",
    "ratewall_ratio",
    "delta_ratewall_ratio_vs_baseline",
    "total_current_demand_support_bil",
    "delta_total_current_demand_support_bil",
    "tdc_current_demand_support_bil",
    "delta_tdc_current_demand_support_bil",
    "direct_treasury_current_demand_support_bil",
    "delta_direct_treasury_current_demand_support_bil",
    "bank_treasury_current_demand_support_bil",
    "delta_bank_treasury_current_demand_support_bil",
    "frozen_denominator_bil",
    "denominator_change_allowed",
    "new_issuance_preference_banks_share",
    "new_issuance_preference_foreign_share",
    "new_issuance_preference_private_share",
    "new_issuance_preference_banks_plus_foreign_share",
    "final_stock_date",
    "final_total_stock_banks_share",
    "final_total_stock_foreign_share",
    "final_total_stock_private_share",
    "final_total_stock_cb_share",
    "final_total_stock_banks_plus_foreign_share",
    "mmf_deposit_pass_through",
    "source_status",
    "allowed_use",
    "blocked_use",
    "canonical_ratio_entry",
]


class HolderScenarioResultError(ValueError):
    """Raised when holder scenario outputs cannot be built consistently."""


@dataclass(frozen=True)
class _SuiteFiles:
    root: Path
    artifact: ArtifactManifestView | None


def holder_scenario_result_rows_from_directory(
    suite_dir: str | Path,
) -> list[dict[str, str]]:
    """Return holder-mix scenario rows from a verified TDCSim/RateWall suite."""

    files = _suite_files(suite_dir)
    effect_rows = _read_csv(files, "ratewall_tdcsim_cbo_scenario_effect.csv")
    ratio_rows = _read_csv(files, "ratewall_tdcsim_cbo_fiscal_year_ratio_input.csv")
    effect_by_key = {
        (row["scenario_id"], row["fiscal_year"]): row for row in effect_rows
    }
    ratio_by_key = {
        (row["scenario_id"], row["fiscal_year"]): row for row in ratio_rows
    }
    scenario_payloads = _holder_scenario_payloads(files)
    final_stock_shares = _final_holder_stock_shares(files)

    out: list[dict[str, str]] = []
    for fiscal_year in sorted({row["fiscal_year"] for row in effect_rows}):
        baseline = effect_by_key.get(("cbo_baseline_noop_v1", fiscal_year))
        if baseline is None:
            raise HolderScenarioResultError(
                f"missing baseline effect row for FY{fiscal_year}"
            )
        for scenario_id in HOLDER_SCENARIO_IDS:
            effect = effect_by_key.get((scenario_id, fiscal_year))
            ratio = ratio_by_key.get((scenario_id, fiscal_year))
            payload = scenario_payloads.get(scenario_id)
            stock = final_stock_shares.get(scenario_id)
            if effect is None or ratio is None or payload is None or stock is None:
                raise HolderScenarioResultError(
                    f"missing holder scenario inputs for {scenario_id} FY{fiscal_year}"
                )
            pref = _average_holder_preference_shares(payload)
            out.append(
                {
                    "holder_scenario_result_row_id": (
                        f"holder_scenario_result::{fiscal_year}::{scenario_id}"
                    ),
                    "fiscal_year": fiscal_year,
                    "scenario_id": scenario_id,
                    "scenario_label": _holder_label(scenario_id, payload),
                    "baseline_scenario_id": baseline["scenario_id"],
                    "ratewall_ratio": effect["level_ratewall_ratio"],
                    "delta_ratewall_ratio_vs_baseline": effect[
                        "delta_ratewall_ratio_vs_baseline"
                    ],
                    "total_current_demand_support_bil": effect[
                        "total_current_demand_support_bil"
                    ],
                    "delta_total_current_demand_support_bil": effect[
                        "delta_total_current_demand_support_bil"
                    ],
                    "tdc_current_demand_support_bil": effect[
                        "tdc_current_demand_support_bil"
                    ],
                    "delta_tdc_current_demand_support_bil": effect[
                        "delta_tdc_current_demand_support_bil"
                    ],
                    "direct_treasury_current_demand_support_bil": effect[
                        "direct_treasury_current_demand_support_bil"
                    ],
                    "delta_direct_treasury_current_demand_support_bil": effect[
                        "delta_direct_treasury_current_demand_support_bil"
                    ],
                    "bank_treasury_current_demand_support_bil": effect[
                        "bank_treasury_current_demand_support_bil"
                    ],
                    "delta_bank_treasury_current_demand_support_bil": effect[
                        "delta_bank_treasury_current_demand_support_bil"
                    ],
                    "frozen_denominator_bil": effect["frozen_denominator_bil"],
                    "denominator_change_allowed": "false_no_rate_change",
                    "new_issuance_preference_banks_share": _fmt(pref["Banks"]),
                    "new_issuance_preference_foreign_share": _fmt(pref["Foreign"]),
                    "new_issuance_preference_private_share": _fmt(pref["Private"]),
                    "new_issuance_preference_banks_plus_foreign_share": _fmt(
                        pref["Banks"] + pref["Foreign"]
                    ),
                    "final_stock_date": stock["date"],
                    "final_total_stock_banks_share": stock["Banks"],
                    "final_total_stock_foreign_share": stock["Foreign"],
                    "final_total_stock_private_share": stock["Private"],
                    "final_total_stock_cb_share": stock["CB"],
                    "final_total_stock_banks_plus_foreign_share": _fmt(
                        _decimal(stock["Banks"]) + _decimal(stock["Foreign"])
                    ),
                    "mmf_deposit_pass_through": ratio["mmf_deposit_pass_through"],
                    "source_status": ratio["source_status"],
                    "allowed_use": "assumption_mode_holder_scenario_readout",
                    "blocked_use": (
                        "canonical_headline_promotion;denominator_recalibration;"
                        "rate_change_claim;holder_specific_denominator_claim;"
                        "evidence_mode_claim;release_headline_claim"
                    ),
                    "canonical_ratio_entry": "false",
                }
            )
    return sorted(
        out,
        key=lambda row: (
            int(row["fiscal_year"]),
            HOLDER_SCENARIO_IDS.index(row["scenario_id"]),
        ),
    )


def write_holder_scenario_outputs(
    output_dir: str | Path,
    *,
    rows: Sequence[Mapping[str, str]],
) -> dict[str, Path]:
    """Write holder scenario CSV, PNG charts, and plain readout."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": out / "ratewall_holder_scenario_results.csv",
        "readout_md": out / "holder_scenario_readout.md",
        "png_delta_rw": out / "holder_01_delta_ratewall.png",
        "png_tdc_components": out / "holder_02_tdc_mechanism.png",
        "png_holder_shares": out / "holder_03_holder_share_shift.png",
    }
    _write_csv(paths["csv"], rows)
    paths["readout_md"].write_text(holder_scenario_readout_markdown(rows), encoding="utf-8")
    _write_holder_pngs(paths, rows)
    return paths


def holder_scenario_readout_markdown(rows: Sequence[Mapping[str, str]]) -> str:
    """Return a short plain-English readout for holder scenarios."""

    reserve = _row_by_id(rows, "tdcsim_holder_source_reserve_user_absorption_v1")
    private = _row_by_id(rows, "tdcsim_holder_source_domestic_nonbank_absorption_v1")
    current = _row_by_id(rows, "tdcsim_holder_source_current_mix_v1")
    lines = [
        "# Holder-Mix Scenario Readout",
        "",
        "These scenarios keep the CBO debt path and interest-rate path fixed. Because rates do not change, the denominator is held fixed. The RateWall movement comes through TDCSim's TDC cashflow channel.",
        "",
        f"- Current source-grounded holder mix: RW `{current['ratewall_ratio']}`, delta RW `{current['delta_ratewall_ratio_vs_baseline']}`.",
        f"- Banks+Foreign absorb more from Private: RW `{reserve['ratewall_ratio']}`, delta RW `{reserve['delta_ratewall_ratio_vs_baseline']}`.",
        f"- Domestic nonbank/private absorption comparator: RW `{private['ratewall_ratio']}`, delta RW `{private['delta_ratewall_ratio_vs_baseline']}`.",
        "",
        "Mechanism:",
        "",
        f"- In the Banks+Foreign absorption scenario, new-issuance Banks+Foreign preference is `{reserve['new_issuance_preference_banks_plus_foreign_share']}` and Private preference is `{reserve['new_issuance_preference_private_share']}`.",
        f"- The same row adds `{reserve['delta_tdc_current_demand_support_bil']}` billion dollars of TDC current-demand support versus baseline.",
        f"- The total current-demand support change is `{reserve['delta_total_current_demand_support_bil']}` billion dollars after direct Treasury-interest and bank Treasury-interest offsets.",
        f"- MMF deposit pass-through in the source rows is `{reserve['mmf_deposit_pass_through']}`.",
        "",
        "Boundary:",
        "",
        "- These are scenario-mode rows, not canonical headline entries.",
        "- They do not move the denominator because they do not change the rate path.",
    ]
    return "\n".join(lines) + "\n"


def _suite_files(suite_dir: str | Path) -> _SuiteFiles:
    root = Path(suite_dir)
    artifact = ArtifactManifestView.from_root(root) if artifact_manifest_exists(root) else None
    return _SuiteFiles(root=root, artifact=artifact)


def _read_csv(files: _SuiteFiles, logical_path: str) -> list[dict[str, str]]:
    if files.artifact is not None:
        if not files.artifact.has_file(logical_path):
            raise HolderScenarioResultError(f"missing required suite CSV: {logical_path}")
        with files.artifact.open_text(logical_path) as handle:
            return list(csv.DictReader(handle))
    path = files.root / logical_path
    if not path.exists():
        raise HolderScenarioResultError(f"missing required suite CSV: {path}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _holder_scenario_payloads(files: _SuiteFiles) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    if files.artifact is not None:
        paths = files.artifact.list_files(prefix="scenarios/", suffix=".json")
        for logical_path in paths:
            payload = json.loads(files.artifact.read_text(logical_path))
            scenario_id = str(payload.get("scenario_id", ""))
            if scenario_id in HOLDER_SCENARIO_IDS:
                out[scenario_id] = payload
        return out
    for path in sorted((files.root / "scenarios").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        scenario_id = str(payload.get("scenario_id", ""))
        if scenario_id in HOLDER_SCENARIO_IDS:
            out[scenario_id] = payload
    return out


def _average_holder_preference_shares(payload: Mapping[str, Any]) -> dict[str, Decimal]:
    rows = (
        payload.get("overrides", {})
        .get("holder_preferences", {})
        .get("rows", [])
    )
    if not rows:
        raise HolderScenarioResultError(
            f"scenario has no holder preference rows: {payload.get('scenario_id')}"
        )
    totals = {"Banks": Decimal("0"), "Foreign": Decimal("0"), "Private": Decimal("0")}
    for row in rows:
        shares = row["shares"]
        for holder in totals:
            totals[holder] += _decimal(shares[holder])
    count = Decimal(len(rows))
    return {holder: value / count for holder, value in totals.items()}


def _final_holder_stock_shares(files: _SuiteFiles) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    paths = _holder_stock_paths(files)
    for logical_path in paths:
        rows = _read_gzip_csv(files, logical_path)
        if not rows:
            continue
        scenario_id = rows[0]["scenario_id"]
        if scenario_id not in HOLDER_SCENARIO_IDS:
            continue
        final_date = max(row["date"] for row in rows)
        totals = {"Banks": Decimal("0"), "Foreign": Decimal("0"), "Private": Decimal("0"), "CB": Decimal("0")}
        total = Decimal("0")
        for row in rows:
            if row["date"] != final_date:
                continue
            amount = _decimal(row["debt_held_bil"])
            total += amount
            if row["holder_sector"] in totals:
                totals[row["holder_sector"]] += amount
        if total <= 0:
            raise HolderScenarioResultError(
                f"nonpositive final holder stock for {scenario_id}"
            )
        out[scenario_id] = {
            "date": final_date,
            **{holder: _fmt(value / total) for holder, value in totals.items()},
        }
    return out


def _holder_stock_paths(files: _SuiteFiles) -> tuple[str, ...]:
    if files.artifact is not None:
        return tuple(
            path
            for path in files.artifact.list_files(
                prefix="runs/",
                suffix="/outputs/tdcsim_holder_stocks.csv.gz",
            )
        )
    return tuple(
        path.relative_to(files.root).as_posix()
        for path in sorted(files.root.glob("runs/*/outputs/tdcsim_holder_stocks.csv.gz"))
    )


def _read_gzip_csv(files: _SuiteFiles, logical_path: str) -> list[dict[str, str]]:
    if files.artifact is not None:
        path = files.artifact.object_path(logical_path)
    else:
        path = files.root / logical_path
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _holder_label(scenario_id: str, payload: Mapping[str, Any]) -> str:
    title = str(payload.get("title", ""))
    if scenario_id == "tdcsim_holder_source_current_mix_v1":
        return "Current source-grounded holder mix"
    if scenario_id == "tdcsim_holder_source_reserve_user_absorption_v1":
        return "Banks+Foreign absorb more from Private"
    if scenario_id == "tdcsim_holder_source_domestic_nonbank_absorption_v1":
        return "Domestic nonbank/private absorption comparator"
    return title or scenario_id


def _write_csv(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HOLDER_SCENARIO_RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_holder_pngs(paths: Mapping[str, Path], rows: Sequence[Mapping[str, str]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = [_short_label(row) for row in rows]

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    values = [_float(row["delta_ratewall_ratio_vs_baseline"]) for row in rows]
    ax.barh(labels, values, color=["#64748b", "#2563eb", "#0f766e"])
    ax.axvline(0, color="#111827", linewidth=0.8)
    ax.set_title("Holder Scenarios: Delta RateWall vs CBO Baseline")
    ax.set_xlabel("RateWall ratio change")
    fig.tight_layout()
    fig.savefig(paths["png_delta_rw"], dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.2))
    x = range(len(rows))
    width = 0.24
    component_fields = [
        ("delta_tdc_current_demand_support_bil", "TDC", "#2563eb"),
        ("delta_direct_treasury_current_demand_support_bil", "Direct Treasury interest", "#7c3aed"),
        ("delta_bank_treasury_current_demand_support_bil", "Bank Treasury interest", "#0891b2"),
    ]
    for offset, (field, label, color) in zip((-width, 0, width), component_fields, strict=True):
        ax.bar(
            [index + offset for index in x],
            [_float(row[field]) for row in rows],
            width,
            label=label,
            color=color,
        )
    ax.axhline(0, color="#111827", linewidth=0.8)
    ax.set_xticks(list(x), labels, rotation=12, ha="right")
    ax.set_title("Holder Scenarios: Numerator Mechanism")
    ax.set_ylabel("Billion dollars vs baseline")
    ax.legend()
    fig.tight_layout()
    fig.savefig(paths["png_tdc_components"], dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5.4))
    share_fields = [
        ("new_issuance_preference_banks_share", "Banks", "#2563eb"),
        ("new_issuance_preference_foreign_share", "Foreign/ROW", "#16a34a"),
        ("new_issuance_preference_private_share", "Private", "#f97316"),
    ]
    bottom = [0.0] * len(rows)
    for field, label, color in share_fields:
        values = [_float(row[field]) for row in rows]
        ax.bar(labels, values, bottom=bottom, label=label, color=color)
        bottom = [prior + value for prior, value in zip(bottom, values, strict=True)]
    ax.set_ylim(0, 1)
    ax.set_title("Holder Scenarios: New-Issuance Preference Shares")
    ax.set_ylabel("Share")
    ax.legend(loc="upper right")
    ax.tick_params(axis="x", rotation=12)
    fig.tight_layout()
    fig.savefig(paths["png_holder_shares"], dpi=180)
    plt.close(fig)


def _row_by_id(
    rows: Sequence[Mapping[str, str]],
    scenario_id: str,
) -> Mapping[str, str]:
    for row in rows:
        if row["scenario_id"] == scenario_id:
            return row
    raise HolderScenarioResultError(f"missing holder row: {scenario_id}")


def _short_label(row: Mapping[str, str]) -> str:
    return row["scenario_label"].replace(" absorption comparator", "")


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise HolderScenarioResultError(f"invalid decimal value: {value}") from exc


def _float(value: object) -> float:
    return float(_decimal(value))


def _fmt(value: Decimal) -> str:
    if value == value.to_integral():
        return str(value.quantize(Decimal("1")))
    return format(value.normalize(), "f")
