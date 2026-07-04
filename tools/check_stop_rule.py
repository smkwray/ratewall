#!/usr/bin/env python3
"""Fail diffs that add the RateWall source-gate treadmill pattern."""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


DEFAULT_CONFIG = Path("configs/ratewall_stop_rule.yml")


@dataclass(frozen=True)
class ChangedPath:
    status: str
    path: str


@dataclass(frozen=True)
class StopRuleResult:
    violation: bool
    categories: dict[str, list[str]]
    meaningful_paths: list[str]
    waiver_paths: list[str]
    message: str


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema") != "ratewall.stop_rule.v1":
        raise ValueError(f"{path} must use schema ratewall.stop_rule.v1")
    return payload


def git_changed_paths(
    *,
    base: str | None = None,
    head: str | None = None,
    staged: bool = False,
    include_untracked: bool = True,
) -> list[ChangedPath]:
    if base and head:
        args = ["git", "diff", "--name-status", f"{base}..{head}"]
    elif staged:
        args = ["git", "diff", "--cached", "--name-status"]
    else:
        args = ["git", "diff", "--name-status"]
    proc = subprocess.run(args, check=True, capture_output=True, text=True)
    paths = _parse_name_status(proc.stdout)
    if include_untracked and not (base and head):
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            check=True,
            capture_output=True,
            text=True,
        )
        paths.extend(
            ChangedPath(status="A", path=line)
            for line in untracked.stdout.splitlines()
            if line
        )
    return paths


def _parse_name_status(output: str) -> list[ChangedPath]:
    paths: list[ChangedPath] = []
    for line in output.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        paths.append(ChangedPath(status=status, path=path))
    return paths


def evaluate(paths: Iterable[ChangedPath], config: dict, root: Path) -> StopRuleResult:
    changed = list(paths)
    added = [item.path for item in changed if item.status.startswith("A")]
    meaningful = _matching_paths(
        [item.path for item in changed],
        config.get("meaningful_change_paths", []),
    )
    waivers = _matching_paths(
        [item.path for item in changed],
        config.get("waiver_paths", []),
    )

    categories: dict[str, list[str]] = {}
    for name, spec in config.get("categories", {}).items():
        matches = _matching_paths(added, spec.get("path_globs", []))
        content_regexes = spec.get("content_regexes") or []
        if content_regexes:
            matches.extend(_content_matches(added, content_regexes, root))
        deduped = sorted(set(matches))
        if deduped:
            categories[name] = deduped

    threshold = int(config.get("minimum_treadmill_categories", 3))
    violation = len(categories) >= threshold and not meaningful and not waivers
    return StopRuleResult(
        violation=violation,
        categories=categories,
        meaningful_paths=meaningful,
        waiver_paths=waivers,
        message=str(config.get("message", "Stop-rule violation.")),
    )


def _matching_paths(paths: Iterable[str], globs: Iterable[str]) -> list[str]:
    patterns = list(globs)
    return sorted(
        {
            path
            for path in paths
            if any(fnmatch.fnmatch(path, pattern) for pattern in patterns)
        }
    )


def _content_matches(
    paths: Iterable[str],
    regexes: Iterable[str],
    root: Path,
) -> list[str]:
    compiled = [re.compile(pattern, re.IGNORECASE) for pattern in regexes]
    matches: list[str] = []
    for path in paths:
        if not path.startswith("tests/") or not path.endswith(".py"):
            continue
        full_path = root / path
        if not full_path.exists() or full_path.stat().st_size > 200_000:
            continue
        text = full_path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in compiled):
            matches.append(path)
    return matches


def _print_result(result: StopRuleResult) -> None:
    if not result.categories:
        print("stop-rule: pass (no treadmill additions detected)")
        return
    if not result.violation:
        reason = "meaningful change present" if result.meaningful_paths else "waiver present"
        if not result.meaningful_paths and not result.waiver_paths:
            reason = "below category threshold"
        print(f"stop-rule: pass ({reason})")
        return
    print(result.message, file=sys.stderr)
    print("", file=sys.stderr)
    for name, paths in sorted(result.categories.items()):
        print(f"{name}:", file=sys.stderr)
        for path in paths:
            print(f"  {path}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--no-untracked", action="store_true")
    args = parser.parse_args(argv)

    root = Path.cwd()
    config = load_config(args.config)
    paths = git_changed_paths(
        base=args.base,
        head=args.head,
        staged=args.staged,
        include_untracked=not args.no_untracked,
    )
    result = evaluate(paths, config, root)
    _print_result(result)
    return 1 if result.violation else 0


if __name__ == "__main__":
    raise SystemExit(main())
