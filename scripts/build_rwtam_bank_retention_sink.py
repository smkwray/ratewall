#!/usr/bin/env python
"""Build the RWTAM bank-retention deposit-sink scenario outputs."""

from pathlib import Path

from ratewall.rwtam.bank_retention_sink import (
    build_bank_retention_sink_experiment,
    write_bank_retention_outputs,
    write_bank_retention_report,
)


def main() -> None:
    result = build_bank_retention_sink_experiment(Path("configs/rwtam/packs"))
    write_bank_retention_outputs(result)
    write_bank_retention_report(result)


if __name__ == "__main__":
    main()
