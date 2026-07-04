#!/usr/bin/env python3
"""Build an AST call graph for RateWall legacy databook builder closures."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from map_databook_outputs import build_mapping


DEFAULT_BUILD = Path("src/ratewall/databook/build_legacy.py")
DEFAULT_KEEP_MANIFEST = Path("configs/ratewall_keep_tables_20260607.yml")


@dataclass(frozen=True)
class FunctionInfo:
    name: str
    line_start: int
    line_end: int
    calls: list[str]


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def build_callgraph(build_path: Path = DEFAULT_BUILD) -> dict[str, FunctionInfo]:
    module = ast.parse(build_path.read_text(encoding="utf-8"))
    function_names = {
        node.name for node in module.body if isinstance(node, ast.FunctionDef)
    }
    graph: dict[str, FunctionInfo] = {}
    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        calls = sorted(
            {
                name
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
                for name in [_name(call.func)]
                if name in function_names
            }
        )
        graph[node.name] = FunctionInfo(
            name=node.name,
            line_start=node.lineno,
            line_end=getattr(node, "end_lineno", node.lineno),
            calls=calls,
        )
    return graph


def closure(graph: dict[str, FunctionInfo], roots: list[str]) -> set[str]:
    seen: set[str] = set()
    stack = [root for root in roots if root in graph]
    while stack:
        name = stack.pop()
        if name in seen:
            continue
        seen.add(name)
        stack.extend(graph[name].calls)
    return seen


def keeper_outputs(manifest_path: Path = DEFAULT_KEEP_MANIFEST) -> set[str]:
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    tiers = payload.get("tiers", {})
    outputs: set[str] = set()
    for entries in tiers.values():
        for entry in entries:
            outputs.add(str(entry["output_name"]))
    return outputs


def keeper_writer_roots(
    *,
    build_path: Path = DEFAULT_BUILD,
    manifest_path: Path = DEFAULT_KEEP_MANIFEST,
) -> list[str]:
    keepers = keeper_outputs(manifest_path)
    roots = {
        row.writer_function
        for row in build_mapping(build_path)
        if row.output_csv in keepers
    }
    return sorted(roots)


def _matching(names: set[str], pattern: str) -> list[str]:
    compiled = re.compile(pattern)
    return sorted(name for name in names if compiled.search(name))


def graph_payload(
    *,
    build_path: Path,
    manifest_path: Path,
    include_build_databook: bool,
) -> dict:
    graph = build_callgraph(build_path)
    roots = keeper_writer_roots(build_path=build_path, manifest_path=manifest_path)
    if include_build_databook:
        roots = sorted({"build_databook", *roots})
    external_roots = sorted(root for root in roots if root not in graph)
    keep_closure = closure(graph, roots)
    return {
        "schema": "ratewall.databook_callgraph.v1",
        "build_path": str(build_path),
        "keep_manifest": str(manifest_path),
        "roots": roots,
        "external_roots": external_roots,
        "closure": sorted(keep_closure),
        "functions": {
            name: {
                "line_start": info.line_start,
                "line_end": info.line_end,
                "calls": info.calls,
            }
            for name, info in sorted(graph.items())
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--keep-manifest", type=Path, default=DEFAULT_KEEP_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--include-build-databook", action="store_true")
    parser.add_argument("--cut-pattern", default="")
    parser.add_argument("--assert-no-cut-inbound", action="store_true")
    args = parser.parse_args(argv)

    payload = graph_payload(
        build_path=args.build,
        manifest_path=args.keep_manifest,
        include_build_databook=args.include_build_databook,
    )
    if args.assert_no_cut_inbound and args.cut_pattern:
        matches = _matching(set(payload["closure"]), args.cut_pattern)
        if matches:
            raise SystemExit(
                "cut-pattern functions are in keeper closure: " + ", ".join(matches)
            )
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"wrote {args.output} ({len(payload['closure'])} closure functions)")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
