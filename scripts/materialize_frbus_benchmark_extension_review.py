#!/usr/bin/env python3
"""Discover FRB/US benchmark output slots for FSPDP coverage gaps.

This materializer uses only official FRB/US package/data ZIPs already acquired
under data/raw and writes a review-only JSON payload. It records model variable
presence and benchmark scenario outputs, but it never computes a RateWall
denominator value.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data/raw/conventional_drag_parameterization_sources"
OUTPUT_JSON = RAW_DIR / "frbus_benchmark_output_slot_extension_review.json"
WORKSPACE = Path("/tmp/ratewall-frbus-benchmark-extension")
PYFRBUS_ZIP = RAW_DIR / "pyfrbus.zip"
DATA_ZIP = RAW_DIR / "data_only_package.zip"
LANDING_PAGE = RAW_DIR / "frbus_python_landing_page.html"
TIMEOUT_SECONDS = 90


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tail(text: str, limit: int = 4000) -> str:
    text = text.replace(str(ROOT), "$RATEWALL_ROOT")
    text = text.replace(str(WORKSPACE), "$FRBUS_EXTENSION_WORKSPACE")
    return text[-limit:]


def _extract_inputs() -> dict[str, str]:
    if WORKSPACE.exists():
        shutil.rmtree(WORKSPACE)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PYFRBUS_ZIP) as archive:
        archive.extractall(WORKSPACE)
    with zipfile.ZipFile(DATA_ZIP) as archive:
        archive.extract("data_only_package/LONGBASE.TXT", WORKSPACE)
    data_dir = WORKSPACE / "pyfrbus/data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        WORKSPACE / "data_only_package/LONGBASE.TXT",
        data_dir / "LONGBASE.TXT",
    )
    return {
        "workspace": WORKSPACE.as_posix(),
        "package_root": (WORKSPACE / "pyfrbus").as_posix(),
        "data_path": (data_dir / "LONGBASE.TXT").as_posix(),
        "model_path": (WORKSPACE / "pyfrbus/models/model.xml").as_posix(),
    }


def _run_discovery(paths: dict[str, str]) -> dict[str, object]:
    code = r"""
import json
import pandas
import xml.etree.ElementTree as ET
from pathlib import Path
from pyfrbus.frbus import Frbus
from pyfrbus.load_data import load_data

model_path = Path(__FRBUS_MODEL_PATH__)
data_path = Path(__FRBUS_DATA_PATH__)
data = load_data(str(data_path))
frbus = Frbus(str(model_path))
start = pandas.Period("2040Q1")
end = start + 23
data.loc[start:end, "dfpdbt"] = 0
data.loc[start:end, "dfpsrp"] = 1
with_adds = frbus.init_trac(start, end, data)
with_adds.loc[start, "rffintay_aerr"] += 1
sim = frbus.solve(start, end, with_adds)

root = ET.parse(model_path).getroot()
metadata = {}
for variable in root.findall("variable"):
    name = (variable.findtext("name") or "").strip().lower()
    if not name:
        continue
    metadata[name] = {
        "sector": (variable.findtext("sector") or "").strip(),
        "definition": (variable.findtext("definition") or "").strip(),
        "description": (variable.findtext("description") or "").strip(),
        "equation_type": (variable.findtext("equation_type") or "").strip(),
    }

candidate_variables = [
    "ec",
    "ecnia",
    "ecd",
    "eco",
    "ech",
    "ebfi",
    "ebfin",
    "eh",
    "ehn",
    "xgdp",
]
rows = []
for variable in candidate_variables:
    lower = variable.lower()
    for horizon_q in [4, 8, 12]:
        period = start + horizon_q
        rows.append({
            "candidate_model_variable": variable.upper(),
            "candidate_model_variable_lower": lower,
            "horizon_q": str(horizon_q),
            "model_variable_found": str(lower in frbus.endo_names or lower in data.columns).lower(),
            "model_variable_in_endo": str(lower in frbus.endo_names).lower(),
            "model_variable_in_data": str(lower in data.columns).lower(),
            "model_variable_in_sim": str(lower in sim.columns).lower(),
            "model_output_value_review_only": (
                str(sim.loc[period, lower]) if lower in sim.columns else ""
            ),
            "model_variable_sector": metadata.get(lower, {}).get("sector", ""),
            "model_variable_definition": metadata.get(lower, {}).get("definition", ""),
            "model_variable_description": metadata.get(lower, {}).get("description", ""),
            "model_variable_equation_type": metadata.get(lower, {}).get("equation_type", ""),
        })
payload = {
    "workspace": str(Path(__FRBUS_WORKSPACE__)),
    "model_path": str(model_path),
    "data_path": str(data_path),
    "scenario_handle": "official_100bp_rffintay_add_factor_demo_extension_review",
    "scenario_start": str(start),
    "scenario_end": str(end),
    "shock_definition": "source_demo_one_period_100bp_rffintay_add_factor_not_admitted_100bp_year",
    "policy_shock_add_factor": "rffintay_aerr_plus_1_at_2040Q1",
    "output_rows": rows,
    "demo_rows": str(len(sim)),
    "demo_cols": str(len(sim.columns)),
}
print(json.dumps(payload, sort_keys=True))
"""
    code = (
        code.replace("__FRBUS_MODEL_PATH__", repr(paths["model_path"]))
        .replace("__FRBUS_DATA_PATH__", repr(paths["data_path"]))
        .replace("__FRBUS_WORKSPACE__", repr(paths["workspace"]))
    )
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = paths["package_root"]
    completed = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=WORKSPACE,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode == 0:
        discovery = json.loads(completed.stdout)
        status = "pass_frbus_benchmark_extension_discovery_executed_review_only"
    else:
        discovery = {}
        status = "blocked_frbus_benchmark_extension_discovery_failed"
    return {
        "command": " ".join([sys.executable, "-B", "-c", "<frbus_extension_discovery_code>"]),
        "cwd": WORKSPACE.as_posix(),
        "python_executable": sys.executable,
        "returncode": str(completed.returncode),
        "runtime_step_status": status,
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
        "discovery": discovery,
    }


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    paths = _extract_inputs()
    run = _run_discovery(paths)
    payload = {
        "parser_name": Path(__file__).name,
        "parser_version": "2026-05-24.1",
        "workspace_policy": "external_tmp_workspace_no_repo_local_cache",
        "workspace_path": paths["workspace"],
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "landing_page_path": LANDING_PAGE.relative_to(ROOT).as_posix(),
        "landing_page_sha256": _sha256(LANDING_PAGE) if LANDING_PAGE.exists() else "",
        "pyfrbus_package_path": PYFRBUS_ZIP.relative_to(ROOT).as_posix(),
        "pyfrbus_package_sha256": _sha256(PYFRBUS_ZIP) if PYFRBUS_ZIP.exists() else "",
        "data_package_path": DATA_ZIP.relative_to(ROOT).as_posix(),
        "data_package_sha256": _sha256(DATA_ZIP) if DATA_ZIP.exists() else "",
        "runtime": run,
        "admission_status": "blocked_frbus_benchmark_extension_not_denominator_calibration",
        "claim_boundary": "frbus_benchmark_output_slot_extension_review_not_denominator_calibration",
    }
    OUTPUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
