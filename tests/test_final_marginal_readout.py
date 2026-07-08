from __future__ import annotations

import csv
from pathlib import Path

from ratewall.databook.final_marginal_model import (
    SELECTED_RW_M_CLAIM_BOUNDARY,
    SELECTED_RW_M_RWTAM_BLOCKED_USE,
)
from ratewall.databook.final_marginal_readout import (
    FINAL_MARGINAL_READOUT_FIELDS,
    final_marginal_readout_rows,
    write_final_marginal_readout_outputs,
)


def test_final_marginal_readout_uses_only_marginal_outputs(tmp_path: Path) -> None:
    paths = _write_fixtures(tmp_path)

    rows = final_marginal_readout_rows(
        final_ratio_path=paths["final"],
        selected_numerator_path=paths["n"],
        denominator_path=paths["d"],
        safe_yield_path=paths["safe"],
        admitted_residual_path=paths["residual"],
        tdc_support_path=paths["tdc"],
        pi_debt_audit_path=paths["debt"],
        readiness_path=paths["readiness"],
        channel_parity_path=paths["parity"],
    )
    outputs = write_final_marginal_readout_outputs(tmp_path / "out", readout_rows=rows)

    assert {field for row in rows for field in row} == set(FINAL_MARGINAL_READOUT_FIELDS)
    by_metric = {row["metric_id"]: row for row in rows}
    assert by_metric["final_rw_m_selected_rows"]["metric_value"] == "1"
    assert (
        SELECTED_RW_M_RWTAM_BLOCKED_USE
        in by_metric["final_rw_m_selected_rows"]["blocked_use"]
    )
    assert (
        by_metric["final_rw_m_selected_rows"]["claim_boundary"]
        == SELECTED_RW_M_CLAIM_BOUNDARY
    )
    assert by_metric["tdc_selected_support_rows"]["metric_status"] == "pass"
    assert by_metric["channel_parity_rows"]["metric_status"] == "pass"
    assert outputs["final_marginal_readout_csv"].read_text(encoding="utf-8").startswith(
        "final_marginal_readout_row_id,"
    )


def _write_fixtures(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "final": tmp_path / "final.csv",
        "n": tmp_path / "n.csv",
        "d": tmp_path / "d.csv",
        "safe": tmp_path / "safe.csv",
        "residual": tmp_path / "residual.csv",
        "tdc": tmp_path / "tdc.csv",
        "debt": tmp_path / "debt.csv",
        "readiness": tmp_path / "readiness.csv",
        "parity": tmp_path / "parity.csv",
    }
    _write_csv(paths["final"], [{"final_rw_m_selected": "true"}])
    _write_csv(paths["n"], [{"selected_marginal_n_allowed": "true"}])
    _write_csv(paths["d"], [{"selected_marginal_D": "true"}])
    _write_csv(
        paths["safe"],
        [{"selected_safe_yield_delta_allowed": "false"}],
    )
    _write_csv(
        paths["residual"],
        [{"selected_admitted_disjoint_delta_allowed": "false"}],
    )
    _write_csv(
        paths["tdc"],
        [
            {
                "selected_tdc_formula_pass": "false",
                "enters_selected_rw_m": "false",
                "marginal_tdc_support_bil": "0",
                "support_formula": (
                    "retired_chi_support_zero;"
                    "income_addendum_parked_direct_treasury_mmf_interest_collision"
                ),
                "blocked_use": "selected_rw_m;income_addendum;chi_support",
            }
            for _ in range(11)
        ],
    )
    _write_csv(paths["debt"], [{"replacement_recommended": "false"}])
    _write_csv(paths["readiness"], [{"check_status": "pass"}])
    _write_csv(paths["parity"], [{"channel_id": str(i)} for i in range(30)])
    return paths


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = list(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
