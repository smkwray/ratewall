from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.peg_defense import (
    build_peg_defense_exhibit,
    write_peg_defense_outputs,
    write_peg_defense_report,
)


def main() -> None:
    result = build_peg_defense_exhibit(Path("configs/rwtam/packs"))
    paths = write_peg_defense_outputs(result, Path("var/rwtam/scenarios/peg_defense"))
    report = write_peg_defense_report(result, Path("do/rwtam_peg_exhibits_report_20260707.md"))
    print(report)
    for table_name in [
        "out_peg_defense_invariant_check",
        "out_peg_defense_exhibit",
        "out_peg_defense_p2_bridge",
        "out_peg_defense_notes",
        "out_peg_defense_slot_inputs",
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
