from __future__ import annotations

import csv
import zipfile
from pathlib import Path

from ratewall.databook.deposit_payer_flow_source_materializer import (
    materialize_ffiec_deposit_interest_panel,
    materialize_ncua_share_interest_panel,
)


def test_materialize_ffiec_deposit_interest_panel(tmp_path: Path) -> None:
    archive = tmp_path / "FFIEC-CDR-Call-Bulk-All-Schedules-03312026.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "FFIEC CDR Call Bulk POR 03312026.txt",
            "\n".join(
                [
                    '"IDRSSD"\tFinancial Institution Name',
                    "1001\tFixture Bank",
                    "1002\tSecond Bank",
                ]
            ),
        )
        zf.writestr(
            "FFIEC CDR Call Schedule RI 03312026.txt",
            "\n".join(
                [
                    '"IDRSSD"\tRIAD4508\tRIAD0093\tRIADHK03\tRIADHK04\tRIAD4172',
                    "\tinterest on transaction accounts\tinterest on savings",
                    "1001\t1\t2\t3\t4\t99",
                    "1002\t\t5\t\t6\t100",
                ]
            ),
        )

    output = tmp_path / "panel.csv"
    materialize_ffiec_deposit_interest_panel(
        archive,
        output,
        source_url="https://cdr.ffiec.gov/public/pws/downloadbulkdata.aspx",
    )

    rows = list(csv.DictReader(output.open()))
    assert rows[0]["report_date"] == "2026-03-31"
    assert rows[0]["rssd_id"] == "1001"
    assert rows[0]["institution_name"] == "Fixture Bank"
    assert rows[0]["RIADHK04"] == "4"
    assert rows[1]["RIAD4508"] == "0"
    assert rows[1]["RIADHK03"] == "0"


def test_materialize_ncua_share_interest_panel_merges_fs220a(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "call-report-data-2026-03.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "FOICU.txt",
            "\n".join(
                [
                    '"CU_NUMBER","CU_NAME"',
                    '2001,"Fixture CU"',
                    '2002,"Second CU"',
                ]
            ),
        )
        zf.writestr(
            "FS220.txt",
            "\n".join(
                [
                    '"CU_NUMBER","CYCLE_DATE","ACCT_340","ACCT_380"',
                    '2001,"3/31/2026 0:00:00",30,80',
                    '2002,"3/31/2026 0:00:00",31,',
                ]
            ),
        )
        zf.writestr(
            "FS220A.txt",
            "\n".join(
                [
                    '"CU_NUMBER","CYCLE_DATE","ACCT_350","ACCT_381"',
                    '2001,"3/31/2026 0:00:00",40,90',
                    '2002,"3/31/2026 0:00:00",41,91',
                ]
            ),
        )

    output = tmp_path / "panel.csv"
    materialize_ncua_share_interest_panel(
        archive,
        output,
        source_url="https://www.ncua.gov/files/publications/analysis/"
        "call-report-data-2026-03.zip",
    )

    rows = list(csv.DictReader(output.open()))
    assert rows[0]["report_date"] == "2026-03-31"
    assert rows[0]["credit_union_name"] == "Fixture CU"
    assert rows[0]["380"] == "80"
    assert rows[0]["381"] == "90"
    assert rows[0]["340"] == "30"
    assert rows[0]["350"] == "40"
    assert rows[1]["380"] == "0"
