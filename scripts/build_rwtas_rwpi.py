from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtas.rwpi import (
    build_rwpi,
    write_rwpi_outputs,
    write_rwpi_report,
    write_rwpi_validation_report,
)


def main() -> None:
    result = build_rwpi(Path("configs/rwtas/packs"))
    paths = write_rwpi_outputs(result, Path("var/rwtas/scenarios/rwpi"))
    report_path = write_rwpi_report(result, Path("do/rwtas_rwpi_build_report_20260703.md"))
    validation_report_path = write_rwpi_validation_report(
        result,
        Path("do/rwtas_rwpi_plug_validation_report_20260704.md"),
    )
    print(report_path)
    print(validation_report_path)
    for table_name in [
        "out_rwpi_invariant_check",
        "out_rwpi_window_path",
        "out_rwpi_plug_validation",
        "out_rwpi_probe_results",
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
