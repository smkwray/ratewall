from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtas.mechanisms import (
    build_mechanism_wave,
    write_mechanism_wave_outputs,
    write_mechanism_wave_report,
)


def main() -> None:
    result = build_mechanism_wave(Path("configs/rwtas/packs"))
    paths = write_mechanism_wave_outputs(result, Path("var/rwtas/scenarios/mechanism_wave"))
    report_path = write_mechanism_wave_report(result, Path("do/rwtas_mechanism_wave_report_20260702.md"))
    print(report_path)
    for table_name in [
        "out_mechanism_invariant_check",
        "out_holder_stress_ledger",
        "out_dsr_dispersion_crossing_profile",
        "out_inflation_overlay_diagnostic",
    ]:
        _print_table(paths[table_name], max_rows=8)


def _print_table(path: Path, max_rows: int) -> None:
    print(path)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    print(",".join(fields))
    for row in rows[:max_rows]:
        print(",".join(row[field] for field in fields))
    if len(rows) > max_rows:
        print(f"... {len(rows) - max_rows} more rows")


if __name__ == "__main__":
    main()
