from __future__ import annotations

from pathlib import Path

from ratewall.rwtam.scenarios import (
    build_financialization_grid,
    build_holder_composition_scenarios,
    build_issuance_mix_scenarios,
    build_rstar_wedge_rows,
    write_holder_composition_outputs,
    write_issuance_mix_outputs,
    write_rstar_wedge,
    write_s1s2_wedge_report,
)


def main() -> None:
    pack_dir = Path("configs/rwtam/packs")
    issuance = build_issuance_mix_scenarios(pack_dir)
    holders = build_holder_composition_scenarios(pack_dir)
    financialization = build_financialization_grid(pack_dir)
    wedge_rows = build_rstar_wedge_rows(
        base_result=issuance["base"],
        financialization_results=financialization,
        issuance_results=issuance,
        holder_results=holders,
    )
    write_issuance_mix_outputs(issuance, Path("var/rwtam/scenarios/issuance_mix"))
    write_holder_composition_outputs(holders, Path("var/rwtam/scenarios/holder_composition"))
    wedge_path = write_rstar_wedge(wedge_rows, Path("var/rwtam/scenarios"))
    report_path = write_s1s2_wedge_report(
        issuance_results=issuance,
        holder_results=holders,
        wedge_rows=wedge_rows,
        output_path=Path("do/rwtam_s1s2_wedge_report_20260702.md"),
    )
    print(wedge_path)
    print(report_path)


if __name__ == "__main__":
    main()
