#!/usr/bin/env python3
"""Profile a RateWall databook build without writing profile artifacts to repo outputs."""

from __future__ import annotations

import argparse
import cProfile
import pstats
from pathlib import Path

from ratewall.databook.build import build_databook


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default="data/raw/ratewall_snapshot.json")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--profile-path", required=True)
    parser.add_argument("--stats-path", required=True)
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    profile_path = Path(args.profile_path)
    stats_path = Path(args.stats_path)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.parent.mkdir(parents=True, exist_ok=True)

    profiler = cProfile.Profile()
    profiler.enable()
    build_databook(snapshot_bundle=Path(args.snapshot), output_dir=output_dir)
    profiler.disable()
    profiler.dump_stats(profile_path)

    with stats_path.open("w", encoding="utf-8") as handle:
        stats = pstats.Stats(profiler, stream=handle).strip_dirs().sort_stats("cumtime")
        stats.print_stats(args.limit)
    print(f"profile_path: {profile_path}")
    print(f"stats_path: {stats_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
