from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.scenarios import (
    build_financialization_grid,
    write_financialization_grid_outputs,
    write_financialization_report,
)


def main() -> None:
    results = build_financialization_grid(Path("configs/rwtam/packs"))
    paths = write_financialization_grid_outputs(
        results,
        Path("var/rwtam/scenarios/financialization"),
    )
    report = write_financialization_report(
        results,
        Path("do/rwtam_financialization_report_20260702.md"),
    )
    print(paths["out_financialization_grid"])
    _print_table(Path(paths["out_financialization_grid"]))
    print(report)


def _print_table(path: Path) -> None:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fields = reader.fieldnames or []
    print(",".join(fields))
    for row in rows:
        print(",".join(row[field] for field in fields))


if __name__ == "__main__":
    main()
