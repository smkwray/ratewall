from __future__ import annotations

from ratewall.rwtam.assembly import build_assembly_outputs


def main() -> None:
    paths = build_assembly_outputs()
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
