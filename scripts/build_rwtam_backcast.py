from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.backcast import build_backcast, write_backcast_outputs


def main() -> None:
    result = build_backcast(
        Path("configs/rwtam/packs"),
        Path("do/backcast"),
        anchor_quarter="2022Q1",
        end_year=2024,
    )
    paths = write_backcast_outputs(result, Path("var/rwtam/backcast"))
    for table_name in [
        "out_backcast_tracking",
        "out_RW_cash_backcast_series",
        "out_backcast_invariant_check",
    ]:
        _print_table(paths[table_name], max_rows=18)


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
