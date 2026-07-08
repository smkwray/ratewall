from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam.ai_boom_twin import (
    build_ai_boom_twin,
    write_ai_boom_outputs,
    write_ai_boom_report,
)


def main() -> None:
    result = build_ai_boom_twin(Path("configs/rwtam/packs"))
    paths = write_ai_boom_outputs(result, Path("var/rwtam/scenarios/ai_boom_twin"))
    report = write_ai_boom_report(result, Path("do/rwtam_ai_boom_report_20260704.md"))
    print(report)
    for table_name in [
        "out_ai_boom_invariant_check",
        "out_ai_boom_twin",
        "out_ai_boom_state_path",
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
