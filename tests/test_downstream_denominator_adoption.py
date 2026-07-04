from __future__ import annotations

import pytest
from pathlib import Path




pytestmark = pytest.mark.full_surface

PUBLIC_README = Path("outputs/reports/ratewall_public_readme.md")
PAPER_SUPPORT = Path("outputs/reports/ratewall_paper_support_packet.md")
BACKEND_COMPLETION = Path("outputs/reports/ratewall_backend_completion_readiness_report.md")
PAPER_SUPPORT_APPENDIX = Path("outputs/reports/ratewall_paper_support_backend_appendix.md")
TABLE_PLATE = Path("outputs/reports/ratewall_table_plate.md")
RELEASE_INDEX = Path("outputs/reports/ratewall_release_artifact_index.md")
REVIEWER_PACKET = Path(
    "outputs/reports/ratewall_runtime_annual_flow_support_offset_reviewer_packet.md"
)
LIMITATIONS = Path(
    "outputs/reports/ratewall_runtime_annual_flow_support_offset_limitations.md"
)


def _assert_compact_layer_precedes_raw_traceback(text: str) -> None:
    compact_a = text.index("ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv")
    compact_b = text.index("ratewall_runtime_annual_flow_support_offset_frontier_summary.csv")
    raw = text.index("ratewall_runtime_annual_flow_support_offset_scenarios.csv")
    assert compact_a < raw
    assert compact_b < raw


def test_public_readme_states_live_denominator_policy() -> None:
    text = PUBLIC_README.read_text(encoding="utf-8")
    assert "## Live Denominator Policy" in text
    assert "literature-backed h4 endpoint proxy" in text
    assert "Legacy `0.6/0.7 pp GDP` anchors remain sensitivity-only" in text
    assert "Bounded h8 remains review-only/non-runtime cumulative evidence." in text
    assert "FRB/US remains benchmark-only context" in text
    assert (
        "`outputs/tables/ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv`"
        in text
    )
    assert (
        "`outputs/tables/ratewall_runtime_annual_flow_support_offset_frontier_summary.csv`"
        in text
    )
    assert "`outputs/tables/ratewall_runtime_annual_flow_support_offset_scenarios.csv`" in text
    assert "`outputs/tables/ratewall_annual_support_numerator_contract.csv`" in text
    assert (
        "`outputs/tables/ratewall_runtime_annual_flow_support_offset_readiness_registry.csv`"
        in text
    )
    assert "`outputs/tables/ratewall_annual_support_numerator_source_gate.csv`" in text
    assert "`outputs/tables/ratewall_annual_support_numerator_uncertainty_envelope.csv`" in text
    assert (
        "`outputs/tables/ratewall_runtime_annual_flow_support_offset_closeout_decision.csv`"
        in text
    )
    assert (
        "`outputs/tables/ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv`"
        in text
    )
    assert (
        "`outputs/reports/ratewall_runtime_annual_flow_support_offset_reviewer_packet.md`"
        in text
    )
    assert (
        "`outputs/reports/ratewall_runtime_annual_flow_support_offset_limitations.md`"
        in text
    )
    _assert_compact_layer_precedes_raw_traceback(text)


def test_paper_support_packet_uses_runtime_denominator_language() -> None:
    text = PAPER_SUPPORT.read_text(encoding="utf-8")
    assert "## Live Denominator Policy" in text
    assert "legacy `0.6/0.7` placeholders" in text
    assert "Treat bounded h8 as cumulative overlay/stress context" in text
    assert "not as the runtime denominator" in text
    assert "`ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_frontier_summary.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_scenarios.csv`" in text
    assert "`ratewall_annual_support_numerator_contract.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_readiness_registry.csv`" in text
    assert "`ratewall_annual_support_numerator_source_gate.csv`" in text
    assert "`ratewall_annual_support_numerator_uncertainty_envelope.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_closeout_decision.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_reviewer_packet.md`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_limitations.md`" in text
    _assert_compact_layer_precedes_raw_traceback(text)


def test_backend_completion_report_distinguishes_assumption_mode_from_live_runtime_policy() -> None:
    text = BACKEND_COMPLETION.read_text(encoding="utf-8")
    assert "## Live Runtime Denominator Policy" in text
    assert "still summarizes Assumption Mode v1 completion" in text
    assert "not the default runtime policy" in text
    assert (
        "with scalar conventional-drag assumptions still confined to Assumption Mode "
        "diagnostics rather than the live runtime denominator policy."
    ) in text
    assert "The live runtime annual-flow denominator policy now uses the literature-backed h4 endpoint proxy family" in text
    assert "`ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_frontier_summary.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_scenarios.csv`" in text
    assert "`ratewall_annual_support_numerator_contract.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_readiness_registry.csv`" in text
    assert "`ratewall_annual_support_numerator_source_gate.csv`" in text
    assert "`ratewall_annual_support_numerator_uncertainty_envelope.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_closeout_decision.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_reviewer_packet.md`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_limitations.md`" in text
    assert "with scalar conventional drag as the main denominator." not in text
    _assert_compact_layer_precedes_raw_traceback(text)


def test_paper_support_backend_appendix_keeps_paper_use_denominator_policy_explicit() -> None:
    text = PAPER_SUPPORT_APPENDIX.read_text(encoding="utf-8")
    assert "## Denominator Policy For Paper Use" in text
    assert "Use the literature-backed annual-flow runtime family as the live default denominator" in text
    assert "Keep legacy `0.6/0.7 pp GDP` rows in paper support only as sensitivity-only" in text
    assert "Keep bounded h8 review-only and non-runtime" in text
    assert "Keep FRB/US benchmark-only" in text
    assert "`ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_frontier_summary.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_scenarios.csv`" in text
    assert "`ratewall_annual_support_numerator_contract.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_readiness_registry.csv`" in text
    assert "`ratewall_annual_support_numerator_source_gate.csv`" in text
    assert "`ratewall_annual_support_numerator_uncertainty_envelope.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_closeout_decision.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_reviewer_packet.md`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_limitations.md`" in text
    _assert_compact_layer_precedes_raw_traceback(text)


def test_release_report_surfaces_list_compact_runtime_support_offset_outputs() -> None:
    table_plate = TABLE_PLATE.read_text(encoding="utf-8")
    release_index = RELEASE_INDEX.read_text(encoding="utf-8")
    for text in (table_plate, release_index):
        assert "ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv" in text
        assert "ratewall_runtime_annual_flow_support_offset_frontier_summary.csv" in text
        assert "ratewall_runtime_annual_flow_support_offset_closeout_decision.csv" in text
        assert "ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv" in text


def test_reviewer_packet_and_limitations_reports_are_listed_and_generated() -> None:
    release_index = RELEASE_INDEX.read_text(encoding="utf-8")
    assert "ratewall_runtime_annual_flow_support_offset_reviewer_packet.md" in release_index
    assert "ratewall_runtime_annual_flow_support_offset_limitations.md" in release_index
    assert REVIEWER_PACKET.exists()
    assert LIMITATIONS.exists()
