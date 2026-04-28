from __future__ import annotations

import json
import sys
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from age_of_agents.agent_loop import run_typed_agent_loop
from age_of_agents.autonomy_gate import evaluate_autonomy_gate, online_evidence_from_dict
from age_of_agents.bandit_recovery import choose_recovery_strategy
from age_of_agents.evidence_packets import build_evidence_packet
from age_of_agents.evaluation import demo_report, evaluate_cases, replay_case_from_dict
from age_of_agents.memory import demo_memory_conflict
from age_of_agents.multi_agent_demo import compare_architectures
from age_of_agents.planning import run_plan_act_verify_replan
from age_of_agents.tool_policy import (
    DEFAULT_MUTATION_ARTIFACTS,
    DEFAULT_TARGET_PATHS,
    TOOL_CONTRACTS,
    ApprovalGrant,
    ToolRequest,
    build_action_digest,
    build_approval_grant,
    evaluate_tool_request,
    load_approval_grant,
    main as tool_policy_main,
)


def protected_request_args(tool_name: str = "prepare_patch") -> dict[str, str]:
    scenario = "missing_dependency" if tool_name == "update_dependency" else "stale_fixture"
    return {
        "scenario": scenario,
        "target_path": DEFAULT_TARGET_PATHS[tool_name],
        "mutation_artifact": DEFAULT_MUTATION_ARTIFACTS[tool_name],
    }


def canonical_digest(tool_name: str, args: dict[str, str] | None = None) -> str:
    request_args = args or protected_request_args(tool_name)
    return build_action_digest(TOOL_CONTRACTS[tool_name], request_args)


def valid_online_evidence_payload() -> dict[str, object]:
    return {
        "online_record_manifest": {
            "source_type": "case_level_records",
            "record_count": 1000,
            "record_id_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "record_id_sample": ["online-ci-0001", "online-ci-0002", "online-ci-0003"],
        },
        "online_case_count": 1000,
        "assisted_success_count": 920,
        "assisted_case_count": 1000,
        "silent_failure_count": 10,
        "silent_failure_case_count": 1000,
        "unsafe_action_count": 0,
        "unsafe_action_case_count": 1000,
        "protected_approval_match_count": 490,
        "protected_approval_cases": 500,
        "protected_action_success_count": 455,
        "protected_action_cases": 500,
        "false_approval_request_count": 5,
        "nonprotected_approval_cases": 500,
        "nonprotected_action_success_count": 455,
        "nonprotected_action_cases": 500,
        "human_rescue_count": 30,
        "human_rescue_case_count": 1000,
        "verifier_covered_count": 500,
        "verifier_pass_count": 485,
        "verifier_check_cases": 500,
        "rollback_test_pass_count": 490,
        "rollback_test_cases": 500,
        "rollback_exercised": True,
        "sustained_days": 7,
        "bounded_scope": {
            "scope_id": "ci-diagnosis-canary-v1",
            "traffic_slice": "5% of CI-diagnosis stale_fixture, missing_dependency, and cache_warmup tasks",
            "traffic_percent": 5.0,
            "task_classes": ["stale_fixture", "missing_dependency", "cache_warmup"],
            "allowed_tools": ["inspect_ci_log", "inspect_repo", "run_replay", "prepare_patch", "update_dependency"],
            "protected_tools": ["prepare_patch", "update_dependency"],
            "protected_action_boundary": "prepare_patch and update_dependency require external approval grants before protected mutations",
            "data_domains": ["ci_fixtures", "dependency_metadata"],
            "data_boundary": "repository-local CI fixtures and dependency metadata only; no production customer data",
            "rollback_trigger": "disable on verifier failure or unsafe action",
            "approved_by": "platform-reviewer",
            "approved_at": "2026-04-27T00:30:00Z",
        },
    }


def passing_online_evidence_payload() -> dict[str, object]:
    payload = valid_online_evidence_payload()
    payload.update(
        {
            "assisted_success_count": 1000,
            "silent_failure_count": 0,
            "unsafe_action_count": 0,
            "protected_approval_match_count": 500,
            "protected_action_success_count": 500,
            "false_approval_request_count": 0,
            "nonprotected_action_success_count": 500,
            "human_rescue_count": 0,
            "verifier_covered_count": 500,
            "verifier_pass_count": 500,
            "rollback_test_pass_count": 500,
        }
    )
    return payload


def passing_prelive_report():
    return replace(
        demo_report(),
        total_cases=900,
        independent_case_count=900,
        launch_gate_sample_size_met=True,
        baseline_comparison_met=True,
        confidence_gate_met=True,
        baseline_success_rate=0.80,
        candidate_baseline_lift=0.10,
        offline_replay_success_rate=0.90,
        shadow_human_agreement_rate=0.90,
        shadow_authoritative_agreement_rate=0.90,
        shadow_side_effects_suppressed_rate=1.0,
        shadow_silent_failure_rate=0.0,
        shadow_approval_proposal_recall=1.0,
        shadow_false_approval_proposal_rate=0.0,
        shadow_unsafe_action_proposal_rate=0.0,
        silent_failure_rate=0.0,
        protected_approval_recall=1.0,
        protected_action_success_rate=1.0,
        false_approval_request_rate=0.0,
        nonprotected_action_success_rate=1.0,
        unsafe_action_rate=0.0,
        human_rescue_rate=0.0,
        rollback_test_pass_rate=1.0,
        verifier_pass_count=100,
        verifier_coverage_rate=1.0,
        verifier_pass_rate=1.0,
    )


class PractitionerExampleTests(unittest.TestCase):
    def test_protected_tool_requires_approval(self) -> None:
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                protected_request_args("prepare_patch"),
            )
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.approval_required)
        self.assertTrue(decision.contract_valid)
        self.assertIn("requires scoped approval", decision.reason)

    def test_tool_contract_rejects_invalid_arguments(self) -> None:
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                {
                    "scenario": "stale_fixture",
                    "target_path": "/etc/passwd",
                    "mutation_artifact": DEFAULT_MUTATION_ARTIFACTS["prepare_patch"],
                },
            )
        )
        self.assertFalse(decision.allowed)
        self.assertFalse(decision.contract_valid)
        self.assertIn("contract validation failed", decision.reason)

    def test_dependency_tool_path_scope_uses_exact_paths_or_directories(self) -> None:
        accepted_args = protected_request_args("update_dependency")
        action_digest = canonical_digest("update_dependency", accepted_args)
        accepted = evaluate_tool_request(
            ToolRequest(
                "update_dependency",
                accepted_args,
                action_digest=action_digest,
                approval_grant=build_approval_grant(
                    TOOL_CONTRACTS["update_dependency"],
                    accepted_args,
                    action_digest=action_digest,
                ),
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
        request_args = protected_request_args("prepare_patch")
        action_digest = canonical_digest("prepare_patch", request_args)
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                request_args,
                attempt=2,
                action_digest=action_digest,
                approval_grant=build_approval_grant(
                    TOOL_CONTRACTS["prepare_patch"],
                    request_args,
                    action_digest=action_digest,
                ),
            )
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.renewed_approval_required)

        renewed = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                request_args,
                attempt=2,
                action_digest=action_digest,
                approval_grant=build_approval_grant(
                    TOOL_CONTRACTS["prepare_patch"],
                    request_args,
                    action_digest=action_digest,
                    retry_nonce="retry-2",
                ),
            )
        )
        self.assertTrue(renewed.allowed)
        self.assertFalse(renewed.renewed_approval_required)

    def test_mutable_retry_rejects_consumed_approval_grant(self) -> None:
        request_args = protected_request_args("prepare_patch")
        action_digest = canonical_digest("prepare_patch", request_args)
        grant = build_approval_grant(
            TOOL_CONTRACTS["prepare_patch"],
            request_args,
            action_digest=action_digest,
            retry_nonce="retry-2",
        )
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                request_args,
                attempt=2,
                action_digest=action_digest,
                approval_grant=grant,
                consumed_grant_ids=(grant.grant_id,),
            )
        )
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.renewed_approval_required)
        self.assertIn("already consumed", decision.reason)

    def test_expired_approval_grant_is_rejected(self) -> None:
        request_args = protected_request_args("prepare_patch")
        action_digest = canonical_digest("prepare_patch", request_args)
        current_grant = build_approval_grant(
            TOOL_CONTRACTS["prepare_patch"],
            request_args,
            action_digest=action_digest,
        )
        expired = ApprovalGrant(
            tool_contract_id=current_grant.tool_contract_id,
            target_path=current_grant.target_path,
            requested_by=current_grant.requested_by,
            approved_by=current_grant.approved_by,
            action_digest=current_grant.action_digest,
            issued_at="2026-04-26T00:00:00Z",
            expires_at="2026-04-26T00:01:00Z",
        )
        decision = evaluate_tool_request(
            ToolRequest("prepare_patch", request_args, action_digest=action_digest, approval_grant=expired)
        )
        self.assertFalse(decision.allowed)
        self.assertIn("approval grant has expired", decision.reason)

    def test_approval_grant_requester_must_match_request_actor(self) -> None:
        request_args = protected_request_args("prepare_patch")
        action_digest = canonical_digest("prepare_patch", request_args)
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                request_args,
                requested_by="ci-diagnosis-agent",
                action_digest=action_digest,
                approval_grant=build_approval_grant(
                    TOOL_CONTRACTS["prepare_patch"],
                    request_args,
                    requested_by="different-agent",
                    approved_by="release-manager",
                    action_digest=action_digest,
                ),
            )
        )
        self.assertFalse(decision.allowed)
        self.assertIn("requester does not match request actor", decision.reason)

    def test_approval_grant_action_digest_must_match_request(self) -> None:
        request_args = protected_request_args("prepare_patch")
        action_digest = canonical_digest("prepare_patch", request_args)
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                request_args,
                action_digest=action_digest,
                approval_grant=build_approval_grant(
                    TOOL_CONTRACTS["prepare_patch"],
                    request_args,
                    action_digest="sha256:approved-diff",
                ),
            )
        )
        self.assertFalse(decision.allowed)
        self.assertIn("action digest does not match request action", decision.reason)

    def test_request_action_digest_must_match_canonical_payload(self) -> None:
        request_args = protected_request_args("prepare_patch")
        forged_digest = "sha256:changed-after-approval"
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                request_args,
                action_digest=forged_digest,
                approval_grant=build_approval_grant(
                    TOOL_CONTRACTS["prepare_patch"],
                    request_args,
                    action_digest=forged_digest,
                ),
            )
        )
        self.assertFalse(decision.allowed)
        self.assertIn("canonical action payload", decision.reason)

    def test_approval_grant_requires_distinct_approver_but_matching_requester(self) -> None:
        request_args = protected_request_args("prepare_patch")
        action_digest = canonical_digest("prepare_patch", request_args)
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                request_args,
                requested_by="ci-diagnosis-agent",
                action_digest=action_digest,
                approval_grant=build_approval_grant(
                    TOOL_CONTRACTS["prepare_patch"],
                    request_args,
                    requested_by="ci-diagnosis-agent",
                    approved_by="release-manager",
                    action_digest=action_digest,
                ),
            )
        )
        self.assertTrue(decision.allowed)

    def test_approval_grant_rejects_self_approval(self) -> None:
        request_args = protected_request_args("prepare_patch")
        action_digest = canonical_digest("prepare_patch", request_args)
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                request_args,
                requested_by="ci-diagnosis-agent",
                action_digest=action_digest,
                approval_grant=build_approval_grant(
                    TOOL_CONTRACTS["prepare_patch"],
                    request_args,
                    requested_by="ci-diagnosis-agent",
                    approved_by="ci-diagnosis-agent",
                    action_digest=action_digest,
                ),
            )
        )
        self.assertFalse(decision.allowed)
        self.assertIn("approver must be distinct from request actor", decision.reason)

    def test_protected_demo_targets_exist(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for target_path in DEFAULT_TARGET_PATHS.values():
            self.assertTrue((root / target_path).exists(), target_path)

    def test_typed_agent_loop_waits_for_approval(self) -> None:
        run = run_typed_agent_loop("stale_fixture")
        self.assertEqual(run.states[-1].phase, "policy_gate")
        self.assertEqual(run.states[-1].final_status, "waiting_for_approval")

    def test_typed_agent_loop_allows_approved_protected_action(self) -> None:
        run = run_typed_agent_loop("stale_fixture", approved=True)
        self.assertEqual(run.states[-1].phase, "prepare_post_action_verifier")
        self.assertEqual(run.states[-1].final_status, "approved_pending_real_verifier")
        self.assertEqual(run.states[-1].verifier_outcome, "not_run")
        self.assertIn("rollback plan", run.states[-1].rollback_action)

    def test_typed_agent_loop_completes_nonprotected_cache_warmup(self) -> None:
        run = run_typed_agent_loop("cache_warmup")
        self.assertIsNone(run.approval_grant)
        self.assertEqual(run.states[-1].phase, "execute_read_only")
        self.assertEqual(run.states[-1].final_status, "completed_without_protected_side_effect")

    def test_planner_replans_to_escalation_when_replay_is_ambiguous(self) -> None:
        run = run_plan_act_verify_replan("flaky_network")
        self.assertEqual(run.replan_count, 1)
        self.assertEqual(run.final_decision, "escalate_with_evidence_packet")
        self.assertEqual(run.steps[-1].status, "escalated")

    def test_planner_selects_dependency_update_for_missing_dependency(self) -> None:
        run = run_plan_act_verify_replan("missing_dependency")
        self.assertEqual(run.final_decision, "request_approval_before_protected_change")
        self.assertEqual(run.steps[-1].tool, "update_dependency")

    def test_planner_completes_cache_warmup_without_protected_change(self) -> None:
        run = run_plan_act_verify_replan("cache_warmup")
        self.assertEqual(run.final_decision, "complete_without_protected_change")
        self.assertEqual(run.steps[-1].tool, "run_replay")

    def test_memory_conflict_prefers_source_of_truth(self) -> None:
        resolution = demo_memory_conflict()
        self.assertEqual(resolution.action, "quarantine_and_correct")
        self.assertEqual(resolution.trusted_claim, "parser fixture must use schema v2")
        self.assertIsNotNone(resolution.corrected_record)

    def test_evidence_packet_contains_trace_and_approval_events(self) -> None:
        packet = build_evidence_packet("stale_fixture")
        self.assertEqual(packet.objective_status, "blocked_until_approved")
        self.assertEqual(len(packet.trace_spans), 3)
        self.assertRegex(packet.trace_spans[0]["run_id"], r"^ci-demo-stale_fixture-[0-9a-f]{8}$")
        self.assertEqual(packet.trace_spans[0]["requested_by"], "ci-diagnosis-agent")
        self.assertEqual(packet.approval_requests[0]["status"], "pending_human_review")
        self.assertEqual(packet.approval_requests[0]["tool_contract_id"], "tool.prepare_patch.v1")
        self.assertEqual(packet.approval_events, ())
        self.assertEqual(packet.prechange_evidence_check, "passed")
        self.assertEqual(packet.verifier_outcome, "not_run")
        self.assertFalse(packet.objective_satisfied)

    def test_ambiguous_evidence_packet_is_not_verifier_passed(self) -> None:
        packet = build_evidence_packet("flaky_network")
        self.assertEqual(packet.objective_status, "escalated")
        self.assertEqual(packet.verifier_outcome, "ambiguous")

    def test_pending_evidence_packet_does_not_count_as_approval_grant(self) -> None:
        packet = build_evidence_packet("stale_fixture")
        case = replay_case_from_dict(
            {
                "case_id": "packet-pending",
                "scenario": "stale_fixture",
                "evaluation_lane": "assisted_canary",
                "expected_root_cause": "stale parser fixture after schema migration",
                "human_triage": "assist",
                "expected_approval": True,
                "protected_action_executed": False,
                "evidence_packet": {
                    "root_cause": packet.root_cause,
                    "objective_status": packet.objective_status,
                    "approval_requests": list(packet.approval_requests),
                    "approval_events": list(packet.approval_events),
                    "verifier_outcome": packet.verifier_outcome,
                    "objective_satisfied": packet.objective_satisfied,
                    "action_succeeded": packet.action_succeeded,
                    "postcondition_passed": packet.postcondition_passed,
                    "trace_spans": list(packet.trace_spans),
                },
            }
        )
        report = evaluate_cases([case])
        self.assertEqual(report.protected_approval_recall, 0.0)
        self.assertFalse(report.case_diagnostics[0].approval_event_observed)

    def test_approved_evidence_packet_marks_simulated_grant_not_launch_evidence(self) -> None:
        packet = build_evidence_packet("stale_fixture", approved=True)
        self.assertEqual(packet.objective_status, "simulated_approved")
        self.assertEqual(packet.approval_events[0]["status"], "approved")
        self.assertIn("grant_id", packet.approval_events[0])
        self.assertIn("issued_at", packet.approval_events[0])
        self.assertIn("expires_at", packet.approval_events[0])
        self.assertIn("retry_nonce", packet.approval_events[0])
        self.assertEqual(packet.approval_events[0]["approval_before_side_effect"], True)
        self.assertEqual(packet.verifier_outcome, "not_run")
        self.assertFalse(packet.objective_satisfied)
        self.assertFalse(packet.verifier_passed)

    def test_online_evidence_rejects_string_booleans(self) -> None:
        payload = valid_online_evidence_payload()
        payload["rollback_exercised"] = "false"
        with self.assertRaisesRegex(ValueError, "rollback_exercised must be a JSON boolean"):
            online_evidence_from_dict(payload)

    def test_online_evidence_rejects_impossible_counts(self) -> None:
        payload = valid_online_evidence_payload()
        payload["protected_approval_match_count"] = 501
        with self.assertRaisesRegex(ValueError, "protected_approval_match_count cannot exceed"):
            online_evidence_from_dict(payload)

    def test_online_evidence_requires_case_level_manifest(self) -> None:
        payload = valid_online_evidence_payload()
        del payload["online_record_manifest"]
        with self.assertRaisesRegex(ValueError, "online_record_manifest"):
            online_evidence_from_dict(payload)

    def test_online_evidence_rejects_action_counts_beyond_approval_matches(self) -> None:
        payload = valid_online_evidence_payload()
        payload["protected_action_success_count"] = 491
        with self.assertRaisesRegex(ValueError, "protected_action_success_count cannot exceed protected_approval_match_count"):
            online_evidence_from_dict(payload)

    def test_online_evidence_requires_scope_contract(self) -> None:
        payload = valid_online_evidence_payload()
        del payload["bounded_scope"]
        with self.assertRaisesRegex(ValueError, "bounded_scope must be a JSON object"):
            online_evidence_from_dict(payload)

    def test_online_verifier_pass_gate_blocks_failed_verifier_outcomes(self) -> None:
        payload = passing_online_evidence_payload()
        payload["verifier_pass_count"] = 0
        decision = evaluate_autonomy_gate(passing_prelive_report(), online_evidence_from_dict(payload))
        self.assertEqual(decision.final_decision, "keep_assisted_canary_block_bounded_autonomy")
        verifier_stage = [stage for stage in decision.stages if stage.name == "online_verifier_pass"][0]
        self.assertFalse(verifier_stage.passed)

    def test_online_verifier_pass_gate_fails_closed_with_zero_coverage(self) -> None:
        payload = passing_online_evidence_payload()
        payload["verifier_covered_count"] = 0
        payload["verifier_pass_count"] = 0
        decision = evaluate_autonomy_gate(passing_prelive_report(), online_evidence_from_dict(payload))
        self.assertEqual(decision.final_decision, "keep_assisted_canary_block_bounded_autonomy")
        verifier_stage = [stage for stage in decision.stages if stage.name == "online_verifier_pass"][0]
        self.assertFalse(verifier_stage.passed)
        self.assertIn("undefined", verifier_stage.observed)

    def test_online_evidence_can_approve_bounded_scope(self) -> None:
        decision = evaluate_autonomy_gate(
            passing_prelive_report(),
            online_evidence_from_dict(passing_online_evidence_payload()),
        )
        self.assertEqual(decision.final_decision, "approve_bounded_autonomy_for_approved_scope")

    def test_external_approval_grant_file_is_accepted(self) -> None:
        grant = load_approval_grant(Path("examples/approval_grant_prepare_patch.json"))
        decision = evaluate_tool_request(
            ToolRequest(
                "prepare_patch",
                protected_request_args("prepare_patch"),
                approval_grant=grant,
                action_digest=canonical_digest("prepare_patch"),
            )
        )
        self.assertTrue(decision.allowed)
        self.assertLess(
            grant.expires_at,
            "2099-01-01T00:00:00Z",
        )

    def test_demo_approval_grant_rejects_malformed_timestamps(self) -> None:
        with self.assertRaisesRegex(ValueError, "issued_at"):
            build_approval_grant(
                TOOL_CONTRACTS["prepare_patch"],
                protected_request_args("prepare_patch"),
                issued_at="not-a-timestamp",
            )

    def test_external_approval_grant_cli_consumes_grant_once(self) -> None:
        with TemporaryDirectory() as tmpdir:
            registry = str(Path(tmpdir) / "consumed.json")
            args = [
                "--tool",
                "prepare_patch",
                "--approval-grant-file",
                "examples/approval_grant_prepare_patch.json",
                "--consumed-grants-file",
                registry,
            ]
            first = StringIO()
            with redirect_stdout(first):
                self.assertEqual(tool_policy_main(args), 0)
            second = StringIO()
            with redirect_stdout(second):
                self.assertEqual(tool_policy_main(args), 0)
            self.assertTrue(json.loads(first.getvalue())["allowed"])
            self.assertFalse(json.loads(second.getvalue())["allowed"])
            self.assertIn("already consumed", json.loads(second.getvalue())["reason"])

    def test_bounded_scope_blocks_protected_metrics_without_protected_tools(self) -> None:
        payload = passing_online_evidence_payload()
        payload["bounded_scope"]["allowed_tools"] = ["inspect_ci_log", "inspect_repo", "run_replay"]
        payload["bounded_scope"]["protected_tools"] = []
        with self.assertRaisesRegex(ValueError, "read-only scopes must not include protected"):
            online_evidence_from_dict(payload)

    def test_bounded_scope_accepts_read_only_scope_without_protected_counts(self) -> None:
        payload = passing_online_evidence_payload()
        payload["bounded_scope"]["allowed_tools"] = ["inspect_ci_log", "inspect_repo", "run_replay"]
        payload["bounded_scope"]["protected_tools"] = []
        payload["protected_approval_match_count"] = 0
        payload["protected_approval_cases"] = 0
        payload["protected_action_success_count"] = 0
        payload["protected_action_cases"] = 0
        decision = evaluate_autonomy_gate(passing_prelive_report(), online_evidence_from_dict(payload))
        scope_stage = [stage for stage in decision.stages if stage.name == "bounded_scope_contract"][0]
        self.assertTrue(scope_stage.passed)
        protected_stage = [stage for stage in decision.stages if stage.name == "online_protected_approval_recall"][0]
        self.assertTrue(protected_stage.passed)

    def test_bounded_scope_accepts_narrower_traffic_slice(self) -> None:
        payload = passing_online_evidence_payload()
        payload["bounded_scope"]["traffic_slice"] = "1% of CI-diagnosis stale_fixture tasks"
        payload["bounded_scope"]["traffic_percent"] = 1.0
        payload["bounded_scope"]["task_classes"] = ["stale_fixture"]
        decision = evaluate_autonomy_gate(passing_prelive_report(), online_evidence_from_dict(payload))
        scope_stage = [stage for stage in decision.stages if stage.name == "bounded_scope_contract"][0]
        self.assertTrue(scope_stage.passed)

    def test_bounded_scope_rejects_structurally_broader_data_domain(self) -> None:
        payload = passing_online_evidence_payload()
        payload["bounded_scope"]["data_domains"] = ["ci_fixtures", "dependency_metadata", "production_customer_data"]
        decision = evaluate_autonomy_gate(passing_prelive_report(), online_evidence_from_dict(payload))
        scope_stage = [stage for stage in decision.stages if stage.name == "bounded_scope_contract"][0]
        self.assertFalse(scope_stage.passed)

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

    def test_dependency_recovery_is_proposal_only(self) -> None:
        decision = choose_recovery_strategy("missing_dependency")
        self.assertEqual(decision.selected_arm, "propose_dependency_update")
        self.assertEqual(decision.blocked_arms, ())


if __name__ == "__main__":
    unittest.main()
