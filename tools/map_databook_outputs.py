#!/usr/bin/env python3
"""Map RateWall databook CSV outputs to writer functions from legacy build AST."""

from __future__ import annotations

import argparse
import ast
import csv
from dataclasses import dataclass
from pathlib import Path


DEFAULT_BUILD = Path("src/ratewall/databook/build_legacy.py")


@dataclass(frozen=True)
class WriterDef:
    name: str
    line_start: int
    line_end: int
    source_module: str


@dataclass(frozen=True)
class OutputMapping:
    output_csv: str
    writer_function: str
    row_function: str
    source_module: str
    line_start: str
    line_end: str


def _literal_path_filename(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value if node.value.endswith(".csv") else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _literal_path_filename(node.right)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Path":
        if node.args:
            return _literal_path_filename(node.args[0])
    return None


def _name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _call_name(node: ast.Call) -> str | None:
    return _name(node.func)


def _path_assignments(build_func: ast.FunctionDef) -> dict[str, str]:
    assignments: dict[str, str] = {}
    for node in ast.walk(build_func):
        targets: list[ast.expr] = []
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            targets = [target for target in node.targets if isinstance(target, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            targets = [node.target]
            value = node.value
        if value is None:
            continue
        filename = _literal_path_filename(value)
        if not filename:
            continue
        for target in targets:
            assert isinstance(target, ast.Name)
            assignments[target.id] = filename
    return assignments


def _writer_defs(module: ast.Module, build_path: Path) -> dict[str, WriterDef]:
    defs: dict[str, WriterDef] = {}
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("_write"):
            defs[node.name] = WriterDef(
                name=node.name,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno),
                source_module=str(build_path),
            )
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                local_name = alias.asname or alias.name
                if local_name.startswith("_write"):
                    imported = _imported_writer_def(
                        build_path=build_path,
                        module_name=node.module or "",
                        imported_name=alias.name,
                        local_name=local_name,
                    )
                    if imported:
                        defs[local_name] = imported
    return defs


def _imported_writer_def(
    *,
    build_path: Path,
    module_name: str,
    imported_name: str,
    local_name: str,
) -> WriterDef | None:
    if not module_name.startswith("ratewall.databook."):
        return None
    root = build_path.parents[3]
    module_path = root / "src" / Path(*module_name.split(".")).with_suffix(".py")
    if not module_path.exists():
        return None
    module = ast.parse(module_path.read_text(encoding="utf-8"))
    node = next(
        (
            item
            for item in module.body
            if isinstance(item, ast.FunctionDef) and item.name == imported_name
        ),
        None,
    )
    if node is None:
        return None
    return WriterDef(
        name=local_name,
        line_start=node.lineno,
        line_end=getattr(node, "end_lineno", node.lineno),
        source_module=str(module_path),
    )


def _row_hint(call: ast.Call) -> str:
    hints: list[str] = []
    for arg in call.args[1:]:
        if isinstance(arg, ast.Name) and (
            arg.id.endswith("_rows") or arg.id.endswith("_rows_")
        ):
            hints.append(arg.id)
        elif isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            if arg.value.startswith("$") and "row" in arg.value:
                hints.append(arg.value[1:])
    return ";".join(hints)


def build_mapping(build_path: Path = DEFAULT_BUILD) -> list[OutputMapping]:
    text = build_path.read_text(encoding="utf-8")
    module = ast.parse(text)
    build_func = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "build_databook"
    )
    paths = _path_assignments(build_func)
    writers = _writer_defs(module, build_path)
    mappings: dict[tuple[str, str], OutputMapping] = {}

    for node in ast.walk(build_func):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node)
        writer_name: str | None = None
        first_arg: ast.AST | None = None
        if call_name == "DatabookTableWriteSpec" and node.args:
            writer_name = _name(node.args[0])
            if len(node.args) > 1 and isinstance(node.args[1], ast.Tuple) and node.args[1].elts:
                first_arg = node.args[1].elts[0]
        elif call_name and call_name.startswith("_write") and node.args:
            writer_name = call_name
            first_arg = node.args[0]
        if not writer_name or first_arg is None:
            continue
        output_csv = _resolve_output(first_arg, paths)
        if not output_csv:
            continue
        writer_def = writers.get(writer_name)
        mappings[(output_csv, writer_name)] = OutputMapping(
            output_csv=output_csv,
            writer_function=writer_name,
            row_function=_row_hint(node),
            source_module=writer_def.source_module if writer_def else str(build_path),
            line_start=str(writer_def.line_start) if writer_def else "",
            line_end=str(writer_def.line_end) if writer_def else "",
        )

    return sorted(mappings.values(), key=lambda row: (row.output_csv, row.writer_function))


def _resolve_output(node: ast.AST, paths: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return paths.get(node.id)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if node.value.startswith("$"):
            return None
        return node.value if node.value.endswith(".csv") else None
    return _literal_path_filename(node)


def write_mapping(rows: list[OutputMapping], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "output_csv",
                "writer_function",
                "row_function",
                "source_module",
                "line_start",
                "line_end",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", type=Path, default=DEFAULT_BUILD)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    rows = build_mapping(args.build)
    if args.output:
        write_mapping(rows, args.output)
        print(f"wrote {args.output} ({len(rows)} rows)")
    else:
        writer = csv.DictWriter(
            __import__("sys").stdout,
            fieldnames=[
                "output_csv",
                "writer_function",
                "row_function",
                "source_module",
                "line_start",
                "line_end",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
