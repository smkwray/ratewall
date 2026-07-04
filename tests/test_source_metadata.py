from datetime import datetime, timezone

import pytest

from ratewall.sources.base import RetrievalMetadata, SourceSnapshot, utc_now_iso
from ratewall.sources import fred as fred_source
from ratewall.data.build import DEFAULT_SERIES
from ratewall.sources.fred import FredAdapter
from ratewall.sources.registry import SourceRegistry
from ratewall.sources.treasury_hqm import TreasuryHqmAdapter


def test_source_registry_contains_first_tranche_sources() -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")

    assert set(registry.sources) >= {
        "fred",
        "treasury_fiscaldata",
        "treasury_hqm",
        "cbo",
        "fed_h41",
        "ny_fed",
    }
    assert registry.validate() == []


def test_every_registered_series_has_required_metadata() -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")

    for series in registry.series.values():
        assert series.endpoint.startswith("https://")
        assert series.units
        assert series.frequency
        assert series.transform
        assert series.update_cadence
        assert series.source in registry.sources


def test_baa_source_is_registered_for_default_live_snapshot() -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    baa = registry.series_definition("BAA")

    assert "BAA" in DEFAULT_SERIES
    assert baa.source == "fred"
    assert baa.endpoint == "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAA"
    assert baa.units == "percent"
    assert baa.frequency == "monthly"
    assert baa.transform == "level"


def test_timestamp_policy_requires_utc_retrieval_metadata() -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    policy = registry.timestamp_policy

    assert policy.retrieval_timezone == "UTC"
    assert policy.retrieval_timestamp_field == "retrieved_at"
    assert policy.retrieval_timestamp_format == "iso8601_utc_z"
    assert {
        "source_id",
        "series_id",
        "source_url",
        "units",
        "frequency",
        "transform",
        "retrieved_at",
    } <= set(policy.required_snapshot_fields)


def test_utc_now_iso_uses_z_suffix() -> None:
    fixed = datetime(2026, 5, 9, 18, 30, tzinfo=timezone.utc)

    assert utc_now_iso(lambda: fixed) == "2026-05-09T18:30:00Z"


def test_fred_adapter_builds_timestamped_snapshot_from_csv() -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    fixed = datetime(2026, 5, 9, 18, 30, tzinfo=timezone.utc)

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"observation_date,WRESBAL\n2026-05-06,3032588\n"

    def opener(url: str) -> Response:
        assert url == registry.series_definition("WRESBAL").endpoint
        return Response()

    snapshot = FredAdapter(registry, opener=opener, clock=lambda: fixed).pull_series(
        "WRESBAL"
    )

    assert snapshot.metadata.source_id == "fred"
    assert snapshot.metadata.series_id == "WRESBAL"
    assert snapshot.metadata.retrieved_at == "2026-05-09T18:30:00Z"
    assert snapshot.records == [{"date": "2026-05-06", "value": "3032588"}]


def test_fred_curl_uses_bounded_env_timeouts(monkeypatch) -> None:
    calls = []

    class Result:
        stdout = "observation_date,WRESBAL\n2026-05-06,3032588\n"

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return Result()

    monkeypatch.setenv("RATEWALL_FRED_CONNECT_TIMEOUT_SECONDS", "3")
    monkeypatch.setenv("RATEWALL_FRED_MAX_TIME_SECONDS", "7")
    monkeypatch.setattr(fred_source.subprocess, "run", fake_run)

    assert "3032588" in fred_source._curl_text("https://example.test/fred.csv")

    args, kwargs = calls[0]
    assert args[args.index("--connect-timeout") + 1] == "3"
    assert args[args.index("--max-time") + 1] == "7"
    assert kwargs["check"] is True
    assert kwargs["capture_output"] is True


def test_fred_api_empty_observations_fail_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        fred_source,
        "_curl_text",
        lambda _url: '{"count":0,"observations":[]}',
    )

    with pytest.raises(ValueError, match="FRED API returned no observations"):
        fred_source._api_records("RRPONTSYD", "runtime-key")


def test_fred_api_missing_date_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        fred_source,
        "_curl_text",
        lambda _url: '{"observations":[{"value":"1"}]}',
    )

    with pytest.raises(ValueError, match="missing date"):
        fred_source._api_records("RRPONTSYD", "runtime-key")


def test_fred_api_html_body_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        fred_source,
        "_curl_text",
        lambda _url: "<html><body>error</body></html>",
    )

    with pytest.raises(ValueError, match="JSON object"):
        fred_source._api_records("RRPONTSYD", "runtime-key")


def test_fred_csv_empty_observations_fail_closed() -> None:
    with pytest.raises(ValueError, match="no observations"):
        fred_source._csv_records("observation_date,WRESBAL\n")


def test_fred_csv_blank_observation_date_fails_closed() -> None:
    with pytest.raises(ValueError, match="blank observation_date"):
        fred_source._csv_records("observation_date,WRESBAL\n,3032588\n")


def test_fred_source_release_at_uses_latest_date_for_unsorted_records() -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    fixed = datetime(2026, 5, 9, 18, 30, tzinfo=timezone.utc)

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return (
                b"observation_date,WRESBAL\n"
                b"2026-05-06,3032588\n"
                b"2026-04-30,3000000\n"
            )

    snapshot = FredAdapter(
        registry,
        opener=lambda _url: Response(),
        clock=lambda: fixed,
    ).pull_series("WRESBAL")

    assert snapshot.metadata.source_release_at == "2026-05-06"


def test_fred_csv_missing_observation_date_fails_closed() -> None:
    with pytest.raises(ValueError, match="observation_date"):
        fred_source._csv_records("date,WRESBAL\n2026-05-06,3032588\n")


def test_fred_csv_html_error_body_fails_closed() -> None:
    with pytest.raises(ValueError, match="observation_date"):
        fred_source._csv_records("<html><body>error</body></html>")


def test_snapshot_metadata_is_serializable() -> None:
    snapshot = SourceSnapshot(
        metadata=RetrievalMetadata(
            source_id="fred",
            series_id="WRESBAL",
            source_url="https://example.test",
            units="millions_of_dollars",
            frequency="weekly",
            transform="level",
            retrieved_at="2026-05-09T18:30:00Z",
        ),
        records=[{"date": "2026-05-06", "value": "3032588"}],
    )

    assert snapshot.to_dict()["metadata"]["retrieved_at"].endswith("Z")


def test_treasury_hqm_adapter_reads_local_official_workbook() -> None:
    registry = SourceRegistry.from_path("configs/sources.yml")
    fixed = datetime(2026, 6, 2, 12, 0, tzinfo=timezone.utc)

    snapshot = TreasuryHqmAdapter(
        registry,
        clock=lambda: fixed,
    ).pull_series("TREASURY_HQM_EOM_10Y_PAR")

    assert snapshot.metadata.source_id == "treasury_hqm"
    assert snapshot.metadata.series_id == "TREASURY_HQM_EOM_10Y_PAR"
    assert snapshot.metadata.snapshot_kind == "live_official_workbook"
    assert snapshot.metadata.retrieved_at == "2026-06-02T12:00:00Z"
    assert snapshot.metadata.source_release_at == "2026-04-30"
    assert len(snapshot.records) == 508
    assert snapshot.records[0]["date"] == "1984-01-31"
    assert snapshot.records[0]["value"] == "12.39"
    assert snapshot.records[-1]["date"] == "2026-04-30"
    assert snapshot.records[-1]["value"] == "5.11"
    assert len(snapshot.records[-1]["source_xls_sha256"]) == 64
