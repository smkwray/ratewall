#!/usr/bin/env python3
"""Start and inspect background validation jobs for RateWall.

The runner keeps slow checks out of the interactive edit loop. It writes job
metadata under ``var/async-validation``; ``var/`` is gitignored by this repo.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JOB_DIR = ROOT / "var" / "async-validation"


def _venv_python(env_var: str, project_name: str) -> Path:
    """Resolve the interpreter for a sibling project venv.

    Honors ``$<env_var>`` if set; otherwise falls back to
    ``~/venvs/<project_name>/bin/python``. The home-relative fallback keeps
    this file portable across machines — no absolute user path is baked in.
    """
    override = os.environ.get(env_var)
    if override:
        return Path(override).expanduser()
    return Path.home() / "venvs" / project_name / "bin" / "python"


RATEWALL_PYTHON = _venv_python("RATEWALL_PYTHON", "ratewall")
TDCSIM_PYTHON = _venv_python("TDCSIM_PYTHON", "tdcsim")
TDCSIM_ROOT = ROOT.parent / "tdcsim"


PROFILES: dict[str, dict[str, str]] = {
    "ratewall-full-pytest": {
        "cwd": str(ROOT),
        "command": (
            "PYTHONDONTWRITEBYTECODE=1 "
            'PYTEST_ADDOPTS="${PYTEST_ADDOPTS:+$PYTEST_ADDOPTS }'
            '-p no:cacheprovider -n 16" '
            f"{shlex.quote(str(RATEWALL_PYTHON))} -m pytest -q"
        ),
        "description": "Full RateWall pytest suite.",
    },
    "ratewall-focused-tdc": {
        "cwd": str(ROOT),
        "command": (
            "PYTHONDONTWRITEBYTECODE=1 "
            "PYTEST_ADDOPTS='-p no:cacheprovider' "
            f"{shlex.quote(str(RATEWALL_PYTHON))} -m pytest "
            "tests/test_research_prototype.py -q "
            "-k 'tdcsim or tdc_forward or canonical_tdc or "
            "tdc_new_tables_keep_forbidden_switches_false'"
        ),
        "description": "Focused RateWall TDC/TDCSim ingestion tests.",
    },
    "ratewall-databook-build": {
        "cwd": str(ROOT),
        "command": (
            "PYTHONDONTWRITEBYTECODE=1 "
            f"{shlex.quote(str(RATEWALL_PYTHON))} -m ratewall.cli "
            "databook build --output-dir __JOB_PATH__/outputs"
        ),
        "description": "RateWall databook rebuild in a job-specific output dir.",
    },
    "ratewall-release-build": {
        "cwd": str(ROOT),
        "command": (
            "PYTHONDONTWRITEBYTECODE=1 "
            f"{shlex.quote(str(RATEWALL_PYTHON))} -m ratewall.cli "
            "databook build --output-dir __JOB_PATH__/outputs && "
            "PYTHONDONTWRITEBYTECODE=1 "
            f"{shlex.quote(str(RATEWALL_PYTHON))} -m ratewall.cli "
            "release build --output-dir __JOB_PATH__/outputs"
        ),
        "description": "RateWall databook plus release build in a job-specific output dir.",
    },
    "ratewall-full-surface-release-pytest": {
        "cwd": str(ROOT),
        "command": (
            "PYTHONDONTWRITEBYTECODE=1 "
            f"{shlex.quote(str(RATEWALL_PYTHON))} -m ratewall.cli "
            "databook build --output-dir outputs --full && "
            "PYTHONDONTWRITEBYTECODE=1 "
            f"{shlex.quote(str(RATEWALL_PYTHON))} -m ratewall.cli "
            "release build --output-dir outputs && "
            "PYTHONDONTWRITEBYTECODE=1 "
            f"{shlex.quote(str(RATEWALL_PYTHON))} -m ratewall.cli "
            "databook build --output-dir outputs --full && "
            "PYTHONDONTWRITEBYTECODE=1 "
            'PYTEST_ADDOPTS="${PYTEST_ADDOPTS:+$PYTEST_ADDOPTS }'
            '-p no:cacheprovider" '
            f"{shlex.quote(str(RATEWALL_PYTHON))} -m pytest -q -m full_surface"
        ),
        "description": (
            "Build the repo full/release output surface, then run full_surface tests."
        ),
    },
    "ratewall-profile-databook": {
        "cwd": str(ROOT),
        "command": (
            "PYTHONDONTWRITEBYTECODE=1 "
            f"{shlex.quote(str(RATEWALL_PYTHON))} scripts/profile_databook.py "
            "--output-dir __JOB_PATH__/outputs "
            "--profile-path __JOB_PATH__/databook.cprofile "
            "--stats-path __JOB_PATH__/databook.pstats.txt"
        ),
        "description": "Profile RateWall databook build in a job-specific output dir.",
    },
    "ratewall-ruff": {
        "cwd": str(ROOT),
        "command": (
            "RUFF_CACHE_DIR=/tmp/ratewall-ruff-cache "
            f"{shlex.quote(str(RATEWALL_PYTHON))} -m ruff check src tests"
        ),
        "description": "RateWall Ruff with cache outside repo.",
    },
    "tdcsim-focused": {
        "cwd": str(TDCSIM_ROOT),
        "command": (
            "PYTHONDONTWRITEBYTECODE=1 "
            "PYTEST_ADDOPTS='-p no:cacheprovider' "
            f"{shlex.quote(str(TDCSIM_PYTHON))} -m pytest "
            "tests/test_ratewall_contract.py -q"
        ),
        "description": "Focused TDCSim RateWall contract tests.",
    },
    "tdcsim-source-refresh": {
        "cwd": str(TDCSIM_ROOT),
        "command": (
            "PYTHONDONTWRITEBYTECODE=1 "
            f"{shlex.quote(str(TDCSIM_PYTHON))} "
            "src/ratewall_input_builder.py "
            "--output-dir data/ratewall_inputs "
            "--config-path tdc_config_ratewall_source_backed.yaml "
            "--ratewall-root ../ratewall && "
            "PYTHONDONTWRITEBYTECODE=1 TDCSIM_SCENARIO_WORKERS=${TDCSIM_SCENARIO_WORKERS:-7} "
            f"{shlex.quote(str(TDCSIM_PYTHON))} run.py "
            "tdc_config_ratewall_source_backed.yaml"
        ),
        "description": "Regenerate source-backed TDCSim inputs and contract.",
    },
}

SUITES: dict[str, tuple[str, ...]] = {
    "ratewall-safe-overnight": (
        "ratewall-full-pytest",
        "ratewall-release-build",
        "ratewall-full-surface-release-pytest",
        "ratewall-ruff",
        "tdcsim-focused",
    ),
    "ratewall-profile-overnight": (
        "ratewall-profile-databook",
        "ratewall-full-pytest",
        "ratewall-ruff",
        "tdcsim-focused",
    ),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _job_dir(base: Path, job_id: str) -> Path:
    return base / job_id


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _load_job(base: Path, job_id: str) -> tuple[Path, dict]:
    path = _job_dir(base, job_id) / "job.json"
    if not path.exists():
        raise SystemExit(f"Unknown job id: {job_id}")
    return path.parent, _read_json(path)


def _status_for(job_path: Path, job: dict) -> dict:
    status_path = job_path / "status.json"
    status = _read_json(status_path) if status_path.exists() else {}
    pid = int(job["pid"])
    running = not status_path.exists() and _is_running(pid)
    if status_path.exists():
        state = "passed" if int(status.get("exit_code", 1)) == 0 else "failed"
    elif running:
        state = "running"
    else:
        state = "unknown_exit_missing_status"
    return {
        **job,
        "state": state,
        "running": running,
        "exit_code": status.get("exit_code"),
        "ended_at": status.get("ended_at"),
    }


def _render_status(status: dict) -> str:
    lines = [
        f"job_id: {status['job_id']}",
        f"profile: {status['profile']}",
        f"state: {status['state']}",
        f"pid: {status['pid']}",
        f"started_at: {status['started_at']}",
        f"ended_at: {status.get('ended_at') or ''}",
        f"exit_code: {status.get('exit_code') if status.get('exit_code') is not None else ''}",
        f"log_path: {status['log_path']}",
        f"command: {status['command']}",
    ]
    return "\n".join(lines)


def list_profiles(_args: argparse.Namespace) -> int:
    for name, spec in sorted(PROFILES.items()):
        print(f"{name}\t{spec['description']}")
    return 0


def list_suites(_args: argparse.Namespace) -> int:
    for name, profiles in sorted(SUITES.items()):
        print(f"{name}\t{', '.join(profiles)}")
    return 0


def _start_job(
    *,
    base: Path,
    profile: str,
    job_id: str | None = None,
    command_override: str | None = None,
    cwd_override: str | None = None,
    dry_run: bool = False,
) -> tuple[int, dict | None]:
    if profile not in PROFILES:
        raise SystemExit(f"Unknown profile {profile!r}. Use list-profiles.")
    spec = PROFILES[profile]
    resolved_job_id = job_id or f"{profile}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    job_path = _job_dir(base, resolved_job_id)
    log_path = job_path / "run.log"
    status_path = job_path / "status.json"
    cwd = str(Path(cwd_override or spec["cwd"]).resolve())
    command_template = command_override or spec["command"]
    command = command_template.replace("__JOB_PATH__", shlex.quote(str(job_path)))
    prune_command = (
        f"{shlex.quote(str(Path(sys.executable).resolve()))} "
        f"{shlex.quote(str(Path(__file__).resolve()))} "
        f"--job-dir {shlex.quote(str(base.resolve()))} prune --apply"
    )
    wrapped = (
        f"cd {shlex.quote(cwd)} && "
        f"{{ {command}; }} > {shlex.quote(str(log_path))} 2>&1; "
        "status=$?; "
        f"printf '{{\"exit_code\":%s,\"ended_at\":\"%s\"}}\\n' "
        f"\"$status\" \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\" > {shlex.quote(str(status_path))}; "
        'if [ "${RATEWALL_ASYNC_VALIDATE_AUTO_PRUNE:-1}" != "0" ]; then '
        f"{prune_command} > {shlex.quote(str(job_path / 'prune.log'))} 2>&1 || true; "
        "fi; "
        "exit $status"
    )
    if dry_run:
        print(wrapped)
        return 0, None
    base.mkdir(parents=True, exist_ok=True)
    if job_path.exists():
        raise SystemExit(f"Job already exists: {resolved_job_id}")
    job_path.mkdir(parents=True)
    process = subprocess.Popen(["/bin/bash", "-lc", wrapped], start_new_session=True)
    job = {
        "job_id": resolved_job_id,
        "profile": profile,
        "description": spec["description"],
        "pid": process.pid,
        "cwd": cwd,
        "command": command,
        "log_path": str(log_path),
        "status_path": str(status_path),
        "started_at": _utc_now(),
    }
    _write_json(job_path / "job.json", job)
    return 0, _status_for(job_path, job)


def start(args: argparse.Namespace) -> int:
    exit_code, status_payload = _start_job(
        base=Path(args.job_dir),
        profile=args.profile,
        job_id=args.job_id,
        command_override=args.command,
        cwd_override=args.cwd,
        dry_run=bool(args.dry_run),
    )
    if status_payload is None:
        return exit_code
    print(_render_status(status_payload))
    return exit_code


def start_suite(args: argparse.Namespace) -> int:
    if args.suite not in SUITES:
        raise SystemExit(f"Unknown suite {args.suite!r}. Use list-suites.")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    started: list[dict] = []
    for profile in SUITES[args.suite]:
        job_id = f"{args.job_prefix or args.suite}-{profile}-{stamp}"
        _, status_payload = _start_job(
            base=Path(args.job_dir),
            profile=profile,
            job_id=job_id,
            dry_run=bool(args.dry_run),
        )
        if status_payload is not None:
            started.append(status_payload)
    for payload in started:
        print(_render_status(payload))
        print()
    if started:
        print("collect_commands:")
        for payload in started:
            print(f"  scripts/async_validate.py collect {payload['job_id']}")
    return 0


def status(args: argparse.Namespace) -> int:
    job_path, job = _load_job(Path(args.job_dir), args.job_id)
    print(_render_status(_status_for(job_path, job)))
    return 0


def list_jobs(args: argparse.Namespace) -> int:
    base = Path(args.job_dir)
    if not base.exists():
        return 0
    for job_json in sorted(base.glob("*/job.json")):
        job_path = job_json.parent
        print(_render_status(_status_for(job_path, _read_json(job_json))))
        print()
    return 0


def tail(args: argparse.Namespace) -> int:
    job_path, job = _load_job(Path(args.job_dir), args.job_id)
    log_path = Path(job["log_path"])
    if not log_path.exists():
        raise SystemExit(f"Log does not exist yet: {log_path}")
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-args.lines :]:
        print(line)
    return 0


def collect(args: argparse.Namespace) -> int:
    job_path, job = _load_job(Path(args.job_dir), args.job_id)
    current = _status_for(job_path, job)
    summary_path = job_path / "summary.txt"
    tail_lines = []
    log_path = Path(job["log_path"])
    if log_path.exists():
        tail_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
    summary = _render_status(current) + "\n\nlast_log_lines:\n" + "\n".join(tail_lines) + "\n"
    summary_path.write_text(summary, encoding="utf-8")
    print(summary)
    print(f"summary_path: {summary_path}")
    return 0 if current["state"] in {"passed", "running"} else 1


def _path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GiB"


def _started_at_key(job: dict) -> str:
    return str(job.get("started_at") or "")


def _is_pinned_job(job_path: Path) -> bool:
    return any((job_path / marker).exists() for marker in ("PINNED", ".pinned"))


def _validation_size_summary(job_dir: Path) -> list[tuple[str, Path, int]]:
    downloads = Path.home() / "Downloads"
    return [
        ("job_dir", job_dir, _path_size(job_dir)),
        ("var", ROOT / "var", _path_size(ROOT / "var")),
        ("outputs", ROOT / "outputs", _path_size(ROOT / "outputs")),
        ("data", ROOT / "data", _path_size(ROOT / "data")),
        (
            "release_archives",
            ROOT / "outputs" / "release",
            sum(path.stat().st_size for path in (ROOT / "outputs" / "release").glob("*.zip")),
        ),
        (
            "downloads_ratewall_zips",
            downloads,
            sum(path.stat().st_size for path in downloads.glob("*ratewall*.zip")),
        ),
    ]


def prune(args: argparse.Namespace) -> int:
    """Report or prune stale async validation job directories."""
    if args.apply and args.dry_run:
        raise SystemExit("Use either --dry-run or --apply, not both.")
    job_dir = Path(args.job_dir)
    jobs: list[tuple[Path, dict, dict, int]] = []
    if job_dir.exists():
        for job_json in sorted(job_dir.glob("*/job.json")):
            job_path = job_json.parent
            job = _read_json(job_json)
            jobs.append((job_path, job, _status_for(job_path, job), _path_size(job_path)))

    latest_by_profile_state: dict[tuple[str, str], tuple[Path, str]] = {}
    for job_path, job, status_payload, _size in jobs:
        state = status_payload["state"]
        if state not in {"passed", "failed"}:
            continue
        key = (str(job["profile"]), state)
        current = latest_by_profile_state.get(key)
        if current is None or _started_at_key(job) > current[1]:
            latest_by_profile_state[key] = (job_path, _started_at_key(job))

    keep_paths = {path for path, _started in latest_by_profile_state.values()}
    decisions: list[tuple[str, Path, str, int]] = []
    for job_path, job, status_payload, size in jobs:
        state = status_payload["state"]
        if _is_pinned_job(job_path):
            decisions.append(("keep", job_path, "pinned", size))
        elif state in {"running", "unknown_exit_missing_status"}:
            decisions.append(("keep", job_path, f"state={state}", size))
        elif job_path in keep_paths:
            decisions.append(("keep", job_path, f"latest_{state}_per_profile", size))
        elif state == "passed":
            decisions.append(("prune", job_path, "older_passed_job", size))
        else:
            decisions.append(("keep", job_path, f"state={state}", size))

    print("size_summary:")
    for label, path, size in _validation_size_summary(job_dir):
        print(f"  {label}: {_format_bytes(size)}\t{path}")
    print()
    print("retention_policy:")
    print("  keep current pending/running or unknown-status jobs")
    print("  keep latest passing job per profile")
    print("  keep latest failing job per profile")
    print("  keep jobs marked with PINNED or .pinned")
    print("  prune older passing job directories only")
    print()

    prune_bytes = sum(size for action, _path, _reason, size in decisions if action == "prune")
    print(
        f"jobs: total={len(decisions)} prune_candidates="
        f"{sum(1 for action, _path, _reason, _size in decisions if action == 'prune')} "
        f"candidate_bytes={_format_bytes(prune_bytes)}"
    )
    for action, job_path, reason, size in decisions:
        if action == "prune" or args.verbose:
            print(f"{action}\t{_format_bytes(size)}\t{reason}\t{job_path}")

    if not args.apply:
        print("\ndry_run: no files deleted; pass --apply to remove prune candidates")
        return 0

    for action, job_path, _reason, _size in decisions:
        if action == "prune":
            shutil.rmtree(job_path)
    print(f"\napplied: removed {_format_bytes(prune_bytes)} of older passed job output")
    return 0


def selftest(args: argparse.Namespace) -> int:
    exit_code, status_payload = _start_job(
        base=Path(args.job_dir),
        profile="ratewall-ruff",
        job_id=args.job_id or f"selftest-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        command_override=(
            f"{shlex.quote(str(RATEWALL_PYTHON))} -c "
            + shlex.quote("print('async validation selftest ok')")
        ),
        cwd_override=str(ROOT),
        dry_run=bool(args.dry_run),
    )
    if status_payload is not None:
        print(_render_status(status_payload))
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job-dir", default=str(DEFAULT_JOB_DIR))
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list-profiles").set_defaults(func=list_profiles)
    sub.add_parser("list-suites").set_defaults(func=list_suites)
    start_p = sub.add_parser("start")
    start_p.add_argument("profile")
    start_p.add_argument("--job-id")
    start_p.add_argument("--command")
    start_p.add_argument("--cwd")
    start_p.add_argument("--dry-run", action="store_true")
    start_p.set_defaults(func=start)
    suite_p = sub.add_parser("start-suite")
    suite_p.add_argument("suite")
    suite_p.add_argument("--job-prefix")
    suite_p.add_argument("--dry-run", action="store_true")
    suite_p.set_defaults(func=start_suite)
    status_p = sub.add_parser("status")
    status_p.add_argument("job_id")
    status_p.set_defaults(func=status)
    sub.add_parser("list-jobs").set_defaults(func=list_jobs)
    tail_p = sub.add_parser("tail")
    tail_p.add_argument("job_id")
    tail_p.add_argument("--lines", type=int, default=40)
    tail_p.set_defaults(func=tail)
    collect_p = sub.add_parser("collect")
    collect_p.add_argument("job_id")
    collect_p.set_defaults(func=collect)
    prune_p = sub.add_parser("prune")
    prune_p.add_argument("--dry-run", action="store_true")
    prune_p.add_argument("--apply", action="store_true")
    prune_p.add_argument("--verbose", action="store_true")
    prune_p.set_defaults(func=prune)
    selftest_p = sub.add_parser("selftest")
    selftest_p.add_argument("--job-id")
    selftest_p.add_argument("--command")
    selftest_p.add_argument("--cwd")
    selftest_p.add_argument("--dry-run", action="store_true")
    selftest_p.set_defaults(func=selftest)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
