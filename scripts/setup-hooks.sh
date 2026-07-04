#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/pre-commit tools/check_stop_rule.py

echo "core.hooksPath=$(git config --get core.hooksPath)"
