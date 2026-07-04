from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from ratewall.rwtas.illustrative_states import (
    BYTE_ASSERT_PATHS,
    build_illustrative_states,
    write_data_upgrade_report,
    write_illustrative_state_outputs,
    write_illustrative_state_report,
)


def main() -> None:
    before = _hashes(BYTE_ASSERT_PATHS)
    result = build_illustrative_states(Path("configs/rwtas/packs"))
    after_build = _hashes(BYTE_ASSERT_PATHS)
    result.tables["out_byte_stability_assert"] = _byte_assertion_rows(before, after_build)
    paths = write_illustrative_state_outputs(result, Path("var/rwtas/scenarios/illustrative_states"))
    after_write = _hashes(BYTE_ASSERT_PATHS)
    result.tables["out_byte_stability_assert"] = _byte_assertion_rows(before, after_write)
    paths["out_byte_stability_assert"] = write_illustrative_state_outputs(
        result,
        Path("var/rwtas/scenarios/illustrative_states"),
    )["out_byte_stability_assert"]
    report = write_illustrative_state_report(result, Path("do/rwtas_illustrative_states_report_20260703.md"))
    data_upgrade_report = write_data_upgrade_report(result, Path("do/rwtas_data_upgrades_wire_report_20260703.md"))
    print(report)
    print(data_upgrade_report)
    for table_name in [
        "out_decade_emergence_series",
        "out_decade_emergence_old_vs_new",
        "out_japan_comparison",
        "out_pure_fiscal_two_engines",
        "out_grand_spectrum",
        "out_byte_stability_assert",
        "out_settlement_class_map",
    ]:
        _print_table(paths[table_name], max_rows=12)


def _hashes(paths: tuple[Path, ...]) -> dict[str, str]:
    return {str(path): _sha256(path) if path.exists() else "" for path in paths}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _byte_assertion_rows(before: dict[str, str], after: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(set(before) | set(after)):
        rows.append(
            {
                "path": path,
                "before_sha256": before.get(path, ""),
                "after_sha256": after.get(path, ""),
                "status": "pass" if before.get(path, "") and before.get(path, "") == after.get(path, "") else "fail",
                "claim_grade_label": "byte_stability_assertion",
            }
        )
    return rows


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
