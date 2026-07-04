from __future__ import annotations

from pathlib import Path


REVIEWER_PACKET = Path(
    "outputs/reports/ratewall_runtime_annual_flow_support_offset_reviewer_packet.md"
)
LIMITATIONS = Path(
    "outputs/reports/ratewall_runtime_annual_flow_support_offset_limitations.md"
)


def test_reviewer_packet_points_to_compact_layer_overlay_and_closeout_sources() -> None:
    text = REVIEWER_PACKET.read_text(encoding="utf-8")
    assert "# Runtime Annual-Flow Support-Offset Reviewer Packet" in text
    assert "`ratewall_runtime_annual_flow_support_offset_adoption_matrix.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_frontier_summary.csv`" in text
    assert (
        "`ratewall_runtime_annual_flow_support_offset_readiness_registry.csv`" in text
    )
    assert "`ratewall_runtime_annual_flow_support_offset_closeout_decision.csv`" in text
    assert "`ratewall_runtime_annual_flow_support_offset_benchmark_overlay.csv`" in text
    assert "`ratewall_conventional_drag_denominator_status_compact.csv`" in text
    assert (
        "`ratewall_conventional_drag_denominator_promotion_rule_evaluation.csv`"
        in text
    )
    assert "`ratewall_frbus_100bp_year_fspdp_proxy_benchmark.csv`" in text
    assert "`ratewall_conventional_drag_current_demand_ratio_gate.csv`" in text
    assert "`ratewall_denominator_scale_conflict_followup_decision.csv`" in text
    assert "weak-IV-safe interval" in text
    assert "FRB/US benchmarks: h4" in text
    assert "warn_bounded_h8_above_literature_runtime_and_frbus_review_cluster" in text
    assert "review_weak_frbus_100bp_year_component_benchmark_support" in text


def test_reviewer_limitations_surface_keeps_blocked_claim_modes_explicit() -> None:
    text = LIMITATIONS.read_text(encoding="utf-8")
    assert "# Runtime Annual-Flow Support-Offset Limitations" in text
    assert "`ratewall_runtime_annual_flow_support_offset_closeout_decision.csv`" in text
    assert "pass_same_design_h4_validation_materialized_runtime_policy_maintained" in text
    assert "Legacy `0.6/0.7 pp GDP` rows are sensitivity-only" in text
    assert "Bounded h8 remains review-only overlay evidence" in text
    assert "FRB/US remains benchmark-only" in text
    assert "canonical `RW_Y`" in text
