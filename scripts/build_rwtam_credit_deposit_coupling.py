from pathlib import Path

from ratewall.rwtam.credit_deposit_coupling import (
    build_credit_deposit_coupling_experiment,
    write_credit_deposit_fix_report,
    write_credit_deposit_outputs,
    write_credit_deposit_report,
)


def main() -> None:
    result = build_credit_deposit_coupling_experiment(Path("configs/rwtam/packs"))
    paths = write_credit_deposit_outputs(
        result,
        Path("var/rwtam/scenarios/credit_deposit_coupling"),
    )
    report = write_credit_deposit_report(
        result,
        Path("do/rwtam_credit_deposit_report_20260704.md"),
    )
    fix_report = write_credit_deposit_fix_report(
        result,
        Path("do/rwtam_credit_deposit_fix_report_20260704.md"),
    )
    print(paths["out_credit_deposit_coupling"])
    print(paths["out_credit_deposit_band_cross"])
    print(report)
    print(fix_report)


if __name__ == "__main__":
    main()
