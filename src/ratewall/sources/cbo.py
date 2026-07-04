"""CBO source adapter."""

from __future__ import annotations

import csv
import hashlib
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from ratewall.sources.base import (
    RetrievalMetadata,
    SourceSnapshot,
    open_with_timeout,
    utc_now_iso,
)
from ratewall.sources.cbo_workbook import parse_cbo_budget_projection_rows
from ratewall.sources.registry import SourceRegistry


class CboAdapter:
    """Fetch and lightly parse registered CBO resources."""

    def __init__(
        self,
        registry: SourceRegistry,
        *,
        opener: Callable = urlopen,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.registry = registry
        self.opener = opener
        self.clock = clock

    def pull_resource(self, series_id: str) -> SourceSnapshot:
        spec = self.registry.series_definition(series_id)
        if spec.source != "cbo":
            raise ValueError(f"{series_id} is registered to {spec.source}, not cbo")
        local_snapshot = _local_official_download_snapshot(
            spec=spec,
            series_id=series_id,
            clock=self.clock,
        )
        if local_snapshot is not None:
            return local_snapshot
        try:
            with open_with_timeout(self.opener, _request(spec.endpoint)) as response:
                body = response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            if exc.code == 403:
                attempted = _attempted_official_downloads(self.opener)
                raise RuntimeError(
                    "CBO official publication endpoint returned HTTP 403 with "
                    "DataDome protection for direct non-browser fetches; "
                    "attempted official URLs: "
                    + "; ".join(
                        f"{result['url']} ({result['status']})"
                        for result in attempted
                    )
                ) from exc
            raise
        metadata = RetrievalMetadata(
            source_id="cbo",
            series_id=series_id,
            source_url=spec.endpoint,
            units=spec.units,
            frequency=spec.frequency,
            transform=spec.transform,
            retrieved_at=utc_now_iso(self.clock),
            source_release_at=_publication_date(body),
        )
        return SourceSnapshot(
            metadata=metadata,
            records=[
                {
                    "content_type": "html_or_download_page",
                    "title": _title(body),
                    "publication_date": _publication_date(body),
                    "text_excerpt": _clean_text(body)[:4000],
                }
            ],
        )


def _local_official_download_snapshot(
    *,
    spec,
    series_id: str,
    clock: Callable[[], datetime] | None,
) -> SourceSnapshot | None:
    cbo_dir = Path("data/raw/cbo")
    files = [
        (
            "10_year_budget_projections_xlsx",
            cbo_dir / "51118-2026-02-Budget-Projections.xlsx",
            "https://www.cbo.gov/system/files/2026-02/51118-2026-02-Budget-Projections.xlsx",
        ),
        (
            "economic_projections_xlsx",
            cbo_dir / "51135-2026-02-Economic-Projections.xlsx",
            "https://www.cbo.gov/system/files/2026-02/51135-2026-02-Economic-Projections.xlsx",
        ),
        (
            "historical_economic_data_zip",
            cbo_dir / "55022-2026-02-Historical-Economic-Data.zip",
            "https://www.cbo.gov/system/files/2026-02/55022-2026-02-Historical-Economic-Data.zip",
        ),
        (
            "eval_projections_baselines_csv",
            cbo_dir / "cbo_eval_projections_baselines.csv",
            "https://github.com/US-CBO/eval-projections/blob/main/input_data/baselines.csv",
        ),
    ]
    existing = [
        _local_file_record(label=label, path=path, url=url)
        for label, path, url in files
        if path.exists()
    ]
    if not existing:
        return None
    records = []
    for record in existing:
        if record["file_name"].endswith(".xlsx"):
            xlsx_path = cbo_dir / record["file_name"]
            record.update(_xlsx_summary(xlsx_path))
            if record["file_name"] == "51118-2026-02-Budget-Projections.xlsx":
                projection_rows = parse_cbo_budget_projection_rows(xlsx_path)
                record["normalized_projection_rows"] = str(len(projection_rows))
                records.extend(projection_rows)
        if record["file_name"].endswith(".zip"):
            record.update(_zip_summary(cbo_dir / record["file_name"]))
        if record["file_name"].endswith(".csv"):
            record.update(_baseline_csv_summary(cbo_dir / record["file_name"]))
        records.append(record)
    metadata = RetrievalMetadata(
        source_id="cbo",
        series_id=series_id,
        source_url=spec.endpoint,
        units=spec.units,
        frequency=spec.frequency,
        transform=spec.transform,
        retrieved_at=utc_now_iso(clock),
        source_release_at="2026-02",
        snapshot_kind="live_browser_download",
        note=(
            "Official CBO budget XLSX was downloaded through the browser from "
            "the CBO data page; official CBO economic projection XLSX and "
            "historical economic ZIP are retained when available; official "
            "US-CBO GitHub baselines CSV is also available as an alternate CBO "
            "data surface."
        ),
    )
    return SourceSnapshot(metadata=metadata, records=records)


def _local_file_record(*, label: str, path: Path, url: str) -> dict[str, str | int]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "dataset": label,
        "file_name": path.name,
        "local_path": str(path),
        "source_url": url,
        "bytes": path.stat().st_size,
        "sha256": digest,
    }


def _xlsx_summary(path: Path) -> dict[str, str]:
    with ZipFile(path) as archive:
        workbook = archive.read("xl/workbook.xml").decode("utf-8", errors="replace")
    sheets = re.findall(r'<sheet[^>]+name="([^"]+)"', workbook)
    return {
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "sheet_names": ";".join(sheets),
    }


def _zip_summary(path: Path) -> dict[str, str]:
    with ZipFile(path) as archive:
        names = archive.namelist()
    return {
        "content_type": "application/zip",
        "zip_members": ";".join(names),
    }


def _baseline_csv_summary(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    dates = sorted({row["baseline_date"] for row in rows if row.get("baseline_date")})
    latest = dates[-1] if dates else ""
    latest_rows = [row for row in rows if row.get("baseline_date") == latest]
    return {
        "content_type": "text/csv",
        "rows": str(len(rows)),
        "latest_baseline_date": latest,
        "latest_projected_years": ";".join(
            sorted({row["projected_fiscal_year"] for row in latest_rows})
        ),
    }


def _title(body: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.I | re.S)
    if not match:
        return None
    return _clean_text(match.group(1))


def _publication_date(body: str) -> str | None:
    patterns = [
        r'"datePublished"\s*:\s*"([0-9]{4}-[0-9]{2}-[0-9]{2})',
        r'([A-Z][a-z]+ [0-9]{1,2}, [0-9]{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, body)
        if match:
            return match.group(1)
    return None


def _clean_text(value: str) -> str:
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()


def _request(url: str) -> Request:
    return Request(url, headers={"User-Agent": "Mozilla/5.0 ratewall-research"})


def _attempted_official_downloads(opener: Callable) -> list[dict[str, str]]:
    urls = [
        "https://www.cbo.gov/publication/62105",
        (
            "https://www.cbo.gov/system/files/2026-02/"
            "51118-2026-02-Budget-Projections.xlsx"
        ),
        (
            "https://www.cbo.gov/system/files/2026-02/"
            "51135-2026-02-Economic-Projections.xlsx"
        ),
    ]
    return [{"url": url, "status": _status_for_url(opener, url)} for url in urls]


def _status_for_url(opener: Callable, url: str) -> str:
    try:
        with open_with_timeout(opener, _request(url)) as response:
            content_type = response.headers.get("content-type", "unknown")
            response.read(1)
        return f"accessible content_type={content_type}"
    except HTTPError as exc:
        return f"HTTP {exc.code}"
    except OSError as exc:
        return f"{type(exc).__name__}: {exc}"
