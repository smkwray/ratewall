#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

suite="${1:-ratewall-safe-overnight}"
prefix="${2:-overnight}"

exec scripts/async_validate.py start-suite "$suite" --job-prefix "$prefix"
