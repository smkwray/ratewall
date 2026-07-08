from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.three_gaps import (
    build_three_gaps,
    write_three_gaps_outputs,
    write_three_gaps_report,
)


def main() -> None:
    result = build_three_gaps(Path("configs/rwtam/packs"))
    paths = write_three_gaps_outputs(result, Path("var/rwtam/scenarios/three_gaps"))
    report = write_three_gaps_report(result, Path("do/rwtam_three_gaps_report_20260704.md"))
    print(report)
    for table_name in [
        "out_easing_asymmetry",
        "out_rstar_illusion_exhibit",
        "out_rwpi_fx_off",
        "out_three_gaps_invariant_check",
    ]:
        _print_table(paths[table_name], max_rows=12)


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
