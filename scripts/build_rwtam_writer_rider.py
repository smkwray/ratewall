from __future__ import annotations

from ratewall.rwtam.writer_rider import build_writer_rider_outputs


def main() -> None:
    paths = build_writer_rider_outputs()
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
