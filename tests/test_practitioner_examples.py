from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from age_of_agents.agent_loop import run_typed_agent_loop
from age_of_agents.autonomy_gate import evaluate_autonomy_gate
from age_of_agents.bandit_recovery import choose_recovery_strategy
from age_of_agents.evidence_packets import build_evidence_packet
from age_of_agents.memory import demo_memory_conflict
from age_of_agents.multi_agent_demo import compare_architectures
from age_of_agents.planning import run_plan_act_verify_replan
from age_of_agents.tool_policy import (
    DEFAULT_TARGET_PATHS,
    TOOL_CONTRACTS,
    ToolRequest,
    build_approval_grant,
    evaluate_tool_request,
)


class PractitionerExampleTests(unittest.TestCase):
    def test_protected_tool_requires_approval(self) -> None:
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                {"scenario": "stale_fixture", "target_path": DEFAULT_TARGET_PATHS["prepare_patch"]},
            )
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.approval_required)
        self.assertTrue(decision.contract_valid)
        self.assertIn("requires scoped approval", decision.reason)

    def test_tool_contract_rejects_invalid_arguments(self) -> None:
        decision = evaluate_tool_request(
            ToolRequest("prepare_patch", {"scenario": "stale_fixture", "target_path": "/etc/passwd"})
        )
        self.assertFalse(decision.allowed)
        self.assertFalse(decision.contract_valid)
        self.assertIn("contract validation failed", decision.reason)

    def test_dependency_tool_path_scope_uses_exact_paths_or_directories(self) -> None:
        accepted_args = {"scenario": "missing_dependency", "target_path": "requirements.lock"}
        accepted = evaluate_tool_request(
            ToolRequest(
                "update_dependency",
                accepted_args,
                approval_grant=build_approval_grant(TOOL_CONTRACTS["update_dependency"], accepted_args),
            )
        )
        self.assertTrue(accepted.allowed)

        rejected = evaluate_tool_request(
            ToolRequest(
                "update_dependency",
                {"scenario": "missing_dependency", "target_path": "requirements_backup.txt"},
            )
        )
        self.assertFalse(rejected.allowed)
        self.assertFalse(rejected.contract_valid)

        rejected_suffix = evaluate_tool_request(
            ToolRequest(
                "update_dependency",
                {"scenario": "missing_dependency", "target_path": "pyproject.toml.bak"},
            )
        )
        self.assertFalse(rejected_suffix.allowed)
        self.assertFalse(rejected_suffix.contract_valid)

    def test_mutable_retry_requires_renewed_approval(self) -> None:
        request_args = {"scenario": "stale_fixture", "target_path": DEFAULT_TARGET_PATHS["prepare_patch"]}
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                request_args,
                attempt=2,
                approval_grant=build_approval_grant(TOOL_CONTRACTS["prepare_patch"], request_args),
            )
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.renewed_approval_required)

        renewed = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                request_args,
                attempt=2,
                approval_grant=build_approval_grant(
                    TOOL_CONTRACTS["prepare_patch"],
                    request_args,
                    retry_nonce="retry-2",
                ),
            )
        )
        self.assertTrue(renewed.allowed)
        self.assertFalse(renewed.renewed_approval_required)

    def test_typed_agent_loop_waits_for_approval(self) -> None:
        run = run_typed_agent_loop("stale_fixture")
        self.assertEqual(run.states[-1].phase, "policy_gate")
        self.assertEqual(run.states[-1].final_status, "waiting_for_approval")

    def test_typed_agent_loop_allows_approved_protected_action(self) -> None:
        run = run_typed_agent_loop("stale_fixture", approved=True)
        self.assertEqual(run.states[-1].final_status, "ready_to_execute")

    def test_planner_replans_to_escalation_when_replay_is_ambiguous(self) -> None:
        run = run_plan_act_verify_replan("flaky_network")
        self.assertEqual(run.replan_count, 1)
        self.assertEqual(run.final_decision, "escalate_with_evidence_packet")
        self.assertEqual(run.steps[-1].status, "escalated")

    def test_memory_conflict_prefers_source_of_truth(self) -> None:
        resolution = demo_memory_conflict()
        self.assertEqual(resolution.action, "quarantine_and_correct")
        self.assertEqual(resolution.trusted_claim, "parser fixture must use schema v2")
        self.assertIsNotNone(resolution.corrected_record)

    def test_evidence_packet_contains_trace_and_approval_events(self) -> None:
        packet = build_evidence_packet("stale_fixture")
        self.assertEqual(packet.objective_status, "blocked_until_approved")
        self.assertEqual(len(packet.trace_spans), 3)
        self.assertEqual(packet.approval_events[0]["status"], "pending_human_review")

    def test_autonomy_gate_blocks_bounded_autonomy_for_demo_metrics(self) -> None:
        decision = evaluate_autonomy_gate()
        self.assertEqual(decision.final_decision, "no_go_rescope_before_live_side_effects")
        self.assertFalse(all(stage.passed for stage in decision.stages))

    def test_multi_agent_demo_rejects_peer_to_peer_for_narrow_task(self) -> None:
        comparison = compare_architectures("stale_fixture")
        self.assertEqual(comparison.selected, "single_workflow")
        peer = [option for option in comparison.options if option.name == "peer_to_peer_agents"][0]
        self.assertIn("reject", peer.recommendation)

    def test_constrained_bandit_blocks_live_write_arm(self) -> None:
        decision = choose_recovery_strategy("stale_fixture")
        self.assertEqual(decision.selected_arm, "refresh_fixture")
        self.assertIn("push_direct_fix", decision.blocked_arms)


if __name__ == "__main__":
    unittest.main()
