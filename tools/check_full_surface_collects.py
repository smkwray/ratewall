from __future__ import annotations

import os
import subprocess
import sys


def main() -> int:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTEST_ADDOPTS"] = (
        f"{env.get('PYTEST_ADDOPTS', '')} -p no:cacheprovider"
    ).strip()
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-m",
            "full_surface",
            "--co",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        return result.returncode
    collected = 0
    for line in result.stdout.splitlines():
        if "::" in line and not line.startswith("::"):
            collected += 1
            continue
        if ".py:" in line:
            try:
                collected += int(line.rsplit(":", maxsplit=1)[1].strip())
            except ValueError:
                pass
    if collected == 0:
        print("full_surface collection check failed: collected zero tests")
        print(result.stdout, end="")
        return 1
    print(f"full_surface collection check passed: {collected} tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
