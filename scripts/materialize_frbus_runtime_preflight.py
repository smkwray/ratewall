#!/usr/bin/env python3
"""Probe whether the official FRB/US package can run in this environment.

The probe uses only project-local raw source artifacts and a /tmp workspace. It
records command evidence and blockers, but never computes or promotes a
RateWall denominator value.
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
OUTPUT_JSON = RAW_DIR / "frbus_runtime_runner_preflight.json"
WORKSPACE = Path("/tmp/ratewall-frbus-runtime-preflight")
PYFRBUS_ZIP = RAW_DIR / "pyfrbus.zip"
DATA_ZIP = RAW_DIR / "data_only_package.zip"
LANDING_PAGE = RAW_DIR / "frbus_python_landing_page.html"
TIMEOUT_SECONDS = 60


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tail(text: str, limit: int = 4000) -> str:
    text = text.replace(str(ROOT), "$RATEWALL_ROOT")
    text = text.replace(str(WORKSPACE), "$FRBUS_PREFLIGHT_WORKSPACE")
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


def _run_step(
    *,
    step_id: str,
    description: str,
    code: str,
    paths: dict[str, str],
) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = paths["package_root"]
    cmd = [sys.executable, "-B", "-c", code]
    try:
        completed = subprocess.run(
            cmd,
            cwd=WORKSPACE,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
        returncode = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        returncode = -1
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        timed_out = True

    if timed_out:
        status = "blocked_runtime_step_timeout"
    elif returncode == 0:
        status = "pass_runtime_step_completed_review_only"
    elif step_id == "installed_package_metadata_check":
        status = "blocked_frbus_dependency_install_metadata_missing"
    elif step_id == "dependency_import_check":
        status = "blocked_missing_python_dependency"
    elif step_id == "pyfrbus_import_check":
        status = "blocked_pyfrbus_import_failed"
    elif step_id == "frbus_model_load_check":
        status = "blocked_frbus_model_load_failed"
    else:
        status = "blocked_frbus_demo_execution_failed"

    return {
        "step_id": step_id,
        "description": description,
        "command": " ".join(cmd),
        "cwd": WORKSPACE.as_posix(),
        "python_executable": sys.executable,
        "returncode": str(returncode),
        "timed_out": str(timed_out).lower(),
        "status": status,
        "stdout_tail": _tail(stdout),
        "stderr_tail": _tail(stderr),
    }


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    paths = _extract_inputs()
    steps = [
        _run_step(
            step_id="installed_package_metadata_check",
            description=(
                "Record installed PyFRB/US runtime package metadata in the "
                "external environment."
            ),
            paths=paths,
            code=(
                "from importlib import metadata; "
                "pkgs=['pyfrbus','pandas','scipy','sympy','lxml','symengine']; "
                "missing=[]; versions=[]; "
                "\nfor p in pkgs:\n"
                "    try:\n"
                "        versions.append(p + '==' + metadata.version(p))\n"
                "    except metadata.PackageNotFoundError:\n"
                "        missing.append(p)\n"
                "print('installed=' + ';'.join(versions)); "
                "print('missing=' + ','.join(missing)); "
                "raise SystemExit(1 if missing else 0)"
            ),
        ),
        _run_step(
            step_id="dependency_import_check",
            description="Import PyFRB/US runtime dependencies in the external environment.",
            paths=paths,
            code=(
                "import importlib; "
                "mods=['pandas','numpy','scipy','sympy','lxml','symengine']; "
                "missing=[m for m in mods if importlib.util.find_spec(m) is None]; "
                "print('missing=' + ','.join(missing)); "
                "raise SystemExit(1 if missing else 0)"
            ),
        ),
        _run_step(
            step_id="pyfrbus_import_check",
            description="Import the official PyFRB/US package from the extracted ZIP.",
            paths=paths,
            code="from pyfrbus.frbus import Frbus; print('pyfrbus_import=pass')",
        ),
        _run_step(
            step_id="frbus_model_load_check",
            description="Load LONGBASE and instantiate the FRB/US model XML.",
            paths=paths,
            code=(
                "from pyfrbus.frbus import Frbus; "
                "from pyfrbus.load_data import load_data; "
                f"data=load_data({paths['data_path']!r}); "
                f"model=Frbus({paths['model_path']!r}); "
                "print('rows=%s cols=%s endo=%s' % (len(data), len(data.columns), len(model.endo_names)))"
            ),
        ),
        _run_step(
            step_id="official_100bp_demo_execution_check",
            description="Execute the inventoried 100bp rffintay add-factor demo in review-only mode.",
            paths=paths,
            code=(
                "import pandas; "
                "from pyfrbus.frbus import Frbus; "
                "from pyfrbus.load_data import load_data; "
                f"data=load_data({paths['data_path']!r}); "
                f"frbus=Frbus({paths['model_path']!r}); "
                "start=pandas.Period('2040Q1'); end=start+23; "
                "data.loc[start:end,'dfpdbt']=0; data.loc[start:end,'dfpsrp']=1; "
                "with_adds=frbus.init_trac(start,end,data); "
                "with_adds.loc[start,'rffintay_aerr'] += 1; "
                "sim=frbus.solve(start,end,with_adds); "
                "print('demo_rows=%s demo_cols=%s xgdp_h4=%s ec_h4=%s ebfi_h4=%s' % "
                "(len(sim), len(sim.columns), sim.loc[start+4,'xgdp'], sim.loc[start+4,'ec'], sim.loc[start+4,'ebfi']))"
            ),
        ),
    ]
    payload = {
        "parser_name": Path(__file__).name,
        "parser_version": "2026-05-23.1",
        "workspace_policy": "external_tmp_workspace_no_repo_local_cache",
        "workspace_path": paths["workspace"],
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "dependency_install_command": (
            "PIP_CACHE_DIR=/tmp/ratewall-pip-cache "
            "<external-ratewall-python> -m pip install -e "
            "/tmp/ratewall-frbus-install/pyfrbus"
        ),
        "landing_page_path": LANDING_PAGE.relative_to(ROOT).as_posix(),
        "landing_page_sha256": _sha256(LANDING_PAGE) if LANDING_PAGE.exists() else "",
        "pyfrbus_package_path": PYFRBUS_ZIP.relative_to(ROOT).as_posix(),
        "pyfrbus_package_sha256": _sha256(PYFRBUS_ZIP) if PYFRBUS_ZIP.exists() else "",
        "data_package_path": DATA_ZIP.relative_to(ROOT).as_posix(),
        "data_package_sha256": _sha256(DATA_ZIP) if DATA_ZIP.exists() else "",
        "commands": steps,
        "admission_status": "blocked_runtime_preflight_not_denominator_calibration",
        "claim_boundary": "frbus_runtime_runner_preflight_not_denominator_calibration",
    }
    OUTPUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
