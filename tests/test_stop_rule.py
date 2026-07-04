from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "check_stop_rule.py"
SPEC = importlib.util.spec_from_file_location("check_stop_rule", MODULE_PATH)
assert SPEC is not None
check_stop_rule = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = check_stop_rule
SPEC.loader.exec_module(check_stop_rule)


def _config() -> dict:
    return check_stop_rule.load_config(Path("configs/ratewall_stop_rule.yml"))


def test_stop_rule_fails_treadmill_pattern_without_meaningful_change(tmp_path: Path) -> None:
    paths = [
        check_stop_rule.ChangedPath("A", "outputs/tables/new_source_context.csv"),
        check_stop_rule.ChangedPath("A", "outputs/tables/new_claim_gate.csv"),
        check_stop_rule.ChangedPath("A", "outputs/tables/new_guardrail_audit.csv"),
        check_stop_rule.ChangedPath("A", "do/new_blocker_workplan.md"),
    ]

    result = check_stop_rule.evaluate(paths, _config(), tmp_path)

    assert result.violation is True
    assert set(result.categories) >= {"context_table", "gate_table", "audit_table"}


def test_stop_rule_allows_treadmill_pattern_with_calibration_change(tmp_path: Path) -> None:
    paths = [
        check_stop_rule.ChangedPath("A", "outputs/tables/new_source_context.csv"),
        check_stop_rule.ChangedPath("A", "outputs/tables/new_claim_gate.csv"),
        check_stop_rule.ChangedPath("A", "outputs/tables/new_guardrail_audit.csv"),
        check_stop_rule.ChangedPath("M", "configs/ratewall_assumption_sets.yml"),
    ]

    result = check_stop_rule.evaluate(paths, _config(), tmp_path)

    assert result.violation is False
    assert result.meaningful_paths == ["configs/ratewall_assumption_sets.yml"]


def test_stop_rule_allows_below_threshold_additions(tmp_path: Path) -> None:
    paths = [
        check_stop_rule.ChangedPath("A", "outputs/tables/new_source_context.csv"),
        check_stop_rule.ChangedPath("A", "outputs/tables/new_claim_gate.csv"),
    ]

    result = check_stop_rule.evaluate(paths, _config(), tmp_path)

    assert result.violation is False
    assert set(result.categories) == {"context_table", "gate_table"}
