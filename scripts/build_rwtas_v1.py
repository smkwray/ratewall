from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtas.v1 import build_v1, write_v1_outputs


def main() -> None:
    result = build_v1(Path("configs/rwtas/packs"))
    paths = write_v1_outputs(result, Path("var/rwtas/v1"))
    for table_name in [
        "out_ratewall_rollup",
        "out_government_interest_channel",
        "out_invariant_check",
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
