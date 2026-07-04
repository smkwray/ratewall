#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${RATEWALL_PYTHON:-}" ]]; then
  PY="$RATEWALL_PYTHON"
elif [[ -x "$HOME/venvs/ratewall/bin/python" ]]; then
  PY="$HOME/venvs/ratewall/bin/python"
else
  PY="$(command -v python3)"
fi

cd "$ROOT"

export PYTHONDONTWRITEBYTECODE=1
export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:+$PYTEST_ADDOPTS }-p no:cacheprovider"
PYTEST_PARALLEL_ARGS=(-n auto --dist worksteal)
if [[ "${RATEWALL_PYTEST_SERIAL:-0}" == "1" ]]; then
  PYTEST_PARALLEL_ARGS=()
fi

"$PY" -m pytest -q --co
"$PY" tools/check_full_surface_collects.py
"$PY" -m pytest -q "${PYTEST_PARALLEL_ARGS[@]}" \
  tests/econ/test_assumption_pack_live_bands.py \
  tests/econ/test_calibrated_assumption_mode.py
"$PY" tools/check_restricted_lanes.py
"$PY" tools/check_stop_rule.py
RUFF_CACHE_DIR=/tmp/ratewall-ruff-cache "$PY" -m ruff check src tests
git diff --check
