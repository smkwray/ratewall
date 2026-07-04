from __future__ import annotations

from argparse import Namespace
from dataclasses import fields
from pathlib import Path

import pytest

import ratewall.cli as cli
from ratewall.release import ReleaseArtifacts


def _dummy_release_artifacts(tmp_path: Path) -> ReleaseArtifacts:
    artifact_dir = tmp_path / "release-artifacts"
    return ReleaseArtifacts(
        **{field.name: artifact_dir / field.name for field in fields(ReleaseArtifacts)}
    )


def _release_args(tmp_path: Path, *, rebuild_databook: str = "none") -> Namespace:
    return Namespace(
        snapshot=tmp_path / "data" / "raw" / "ratewall_snapshot.json",
        output_dir=tmp_path / "outputs",
        rebuild_databook=rebuild_databook,
    )


def test_release_build_packages_existing_outputs_without_databook_rebuild(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_databook_rebuild(**_: object) -> None:
        raise AssertionError("release build must not rebuild databook by default")

    policy_calls: list[tuple[Path, dict[str, object]]] = []
    monkeypatch.setattr(cli, "build_databook", fail_databook_rebuild)
    monkeypatch.setattr(
        cli,
        "build_release_package",
        lambda **_: _dummy_release_artifacts(tmp_path),
    )
    monkeypatch.setattr(
        cli,
        "apply_default_table_output_policy",
        lambda output_dir, **kwargs: policy_calls.append((output_dir, kwargs)),
    )

    assert cli._cmd_release_build(_release_args(tmp_path)) == 0

    assert policy_calls == [
        (
            tmp_path / "outputs",
            {"extra_allowed_names": cli.RELEASE_VALIDATION_TABLE_NAMES},
        )
    ]
    assert '"source_archive"' in capsys.readouterr().out


@pytest.mark.parametrize(
    ("rebuild_databook", "expected_full"),
    [("default", False), ("full", True)],
)
def test_release_build_rebuilds_databook_only_when_requested(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    rebuild_databook: str,
    expected_full: bool,
) -> None:
    databook_calls: list[dict[str, object]] = []
    policy_calls: list[dict[str, object]] = []

    def record_databook_build(**kwargs: object) -> None:
        databook_calls.append(kwargs)

    monkeypatch.setattr(cli, "build_databook", record_databook_build)
    monkeypatch.setattr(
        cli,
        "build_release_package",
        lambda **_: _dummy_release_artifacts(tmp_path),
    )
    monkeypatch.setattr(
        cli,
        "apply_default_table_output_policy",
        lambda _output_dir, **kwargs: policy_calls.append(kwargs),
    )

    assert (
        cli._cmd_release_build(
            _release_args(tmp_path, rebuild_databook=rebuild_databook)
        )
        == 0
    )

    assert databook_calls == [
        {
            "snapshot_bundle": tmp_path / "data" / "raw" / "ratewall_snapshot.json",
            "output_dir": tmp_path / "outputs",
            "full": expected_full,
        }
    ]
    if rebuild_databook == "default":
        assert policy_calls == [
            {},
            {"extra_allowed_names": cli.RELEASE_VALIDATION_TABLE_NAMES},
        ]
    else:
        assert policy_calls == [
            {"extra_allowed_names": cli.RELEASE_VALIDATION_TABLE_NAMES}
        ]
