from __future__ import annotations

import csv
from pathlib import Path

from ratewall.rwtam import load_config, run_rwtam
from ratewall.rwtam.reports import write_outputs


def main() -> None:
    config = load_config(Path("configs/rwtam"))
    result = run_rwtam(config)
    output_paths = write_outputs(result, Path("var/rwtam"))
    _print_table(output_paths["out_ratewall_monthly"])
    _print_table(output_paths["out_invariant_check"])


def _print_table(path: Path) -> None:
    print(path)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    if not rows:
        print("(no rows)")
        return
    fields = reader.fieldnames or []
    print(",".join(fields))
    for row in rows:
        print(",".join(row[field] for field in fields))


if __name__ == "__main__":
    main()
