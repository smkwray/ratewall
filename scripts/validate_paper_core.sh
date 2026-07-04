#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${RATEWALL_PYTHON:-$HOME/venvs/ratewall/bin/python}"

cd "$ROOT"

export PYTHONDONTWRITEBYTECODE=1
export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:+$PYTEST_ADDOPTS }-p no:cacheprovider"

"$PY" -m pytest \
  tests/test_paper_core_results_index.py \
  tests/test_active_output_reconciliation.py \
  tests/test_joint_wall_probability_surface.py \
  tests/test_forecast_path_ratio_pass_through_scenarios.py \
  -q

RUFF_CACHE_DIR=/tmp/ratewall-ruff-cache "$PY" -m ruff check \
  src/ratewall/databook/path_ratio_program.py \
  src/ratewall/databook/build.py \
  src/ratewall/release.py \
  tests/test_paper_core_results_index.py

if [[ -n "${RATEWALL_CURATED_ZIP:-}" ]]; then
  zip_has_artifact() {
    local artifact="$1"
    local candidates=(
      "$artifact"
      "ratewall/$artifact"
      "project/$artifact"
    )
    local candidate
    for candidate in "${candidates[@]}"; do
      if unzip -l "$RATEWALL_CURATED_ZIP" "$candidate" >/dev/null 2>&1; then
        return 0
      fi
    done
    return 1
  }

  required_artifacts=(
    "outputs/tables/ratewall_paper_core_results_index.csv"
    "outputs/tables/ratewall_ratio_object_registry.csv"
    "outputs/tables/ratewall_active_output_index.csv"
    "outputs/tables/ratewall_reference_scenario_object_crosswalk.csv"
    "outputs/tables/ratewall_joint_wall_probability_summary.csv"
    "outputs/tables/ratewall_forecast_path_ratio_pass_through_scenario_registry.csv"
    "outputs/tables/ratewall_critical_beta_frontier.csv"
    "outputs/tables/ratewall_historical_closest_approach_clean.csv"
    "outputs/tables/ratewall_release_manifest.json"
  )
  missing=()
  for artifact in "${required_artifacts[@]}"; do
    if ! zip_has_artifact "$artifact"; then
      missing+=("$artifact")
    fi
  done
  if ((${#missing[@]})); then
    printf 'Curated zip missing paper-core artifacts:\n' >&2
    printf '  %s\n' "${missing[@]}" >&2
    exit 1
  fi
fi

git diff --check
