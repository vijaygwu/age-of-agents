from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from age_of_agents.ci_diagnosis import READ_ONLY_TOOLS, diagnose_ci_failure
from age_of_agents.evaluation import ReplayCase, demo_report, evaluate_cases


class CiDiagnosisTests(unittest.TestCase):
    def test_stale_fixture_requires_review_before_protected_change(self) -> None:
        result = diagnose_ci_failure("stale_fixture")
        self.assertEqual(result.root_cause, "stale parser fixture after schema migration")
        self.assertTrue(result.approval_required)
        self.assertFalse(result.escalation_required)
        self.assertIn("request review", result.next_action)

    def test_ambiguous_flake_escalates_instead_of_looping(self) -> None:
        result = diagnose_ci_failure("flaky_network")
        self.assertTrue(result.escalation_required)
        self.assertFalse(result.approval_required)
        self.assertIn("uncertainty", result.next_action)

    def test_tools_have_postconditions_and_no_unapproved_side_effects(self) -> None:
        for contract in READ_ONLY_TOOLS.values():
            self.assertTrue(contract.postcondition)
            if contract.mode == "read-only":
                self.assertEqual(contract.side_effects, "none")
                self.assertFalse(contract.requires_approval)

    def test_traces_have_replay_and_audit_provenance(self) -> None:
        result = diagnose_ci_failure("stale_fixture")
        first_trace = result.traces[0]
        self.assertEqual(first_trace.run_id, "ci-demo-stale_fixture")
        self.assertEqual(first_trace.agent_version, "book5-demo-v1")
        self.assertEqual(first_trace.evaluation_lane, "offline_replay")
        self.assertEqual(first_trace.tool_contract_id, "tool.inspect_ci_log.v1")
        self.assertEqual(first_trace.tool_args["scenario"], "stale_fixture")
        self.assertEqual(first_trace.approval_outcome, "not_required")
        self.assertEqual(first_trace.postcondition_result, "passed")
        self.assertEqual(first_trace.side_effect_summary, "none")

    def test_demo_evaluation_report_matches_chapter_gate(self) -> None:
        report = demo_report()
        self.assertEqual(report.total_cases, 100)
        self.assertEqual(report.minimum_launch_gate_cases, 200)
        self.assertEqual(report.baseline_observed_cases, 100)
        self.assertEqual(report.protected_approval_cases, 51)
        self.assertEqual(report.rollback_test_cases, 100)
        self.assertEqual(report.verifier_check_cases, 100)
        self.assertFalse(report.launch_gate_sample_size_met)
        self.assertTrue(report.baseline_comparison_met)
        self.assertFalse(report.confidence_gate_met)
        self.assertEqual(report.baseline_success_rate, 0.55)
        self.assertAlmostEqual(report.candidate_baseline_lift, 0.07)
        self.assertEqual(report.offline_replay_success_rate, 0.62)
        self.assertEqual(report.shadow_human_agreement_rate, 0.71)
        self.assertEqual(report.silent_failure_rate, 0.09)
        self.assertEqual(report.planned_approval_rate, 1.0)
        self.assertEqual(report.approval_false_positive_rate, 0.0)
        self.assertEqual(report.unsafe_action_rate, 0.0)
        self.assertEqual(report.human_rescue_rate, 0.14)
        self.assertEqual(report.rollback_test_pass_rate, 0.70)
        self.assertEqual(report.verifier_coverage_rate, 0.76)
        self.assertEqual(report.average_cost_usd, 2.10)
        self.assertEqual(report.decision, "no_go_rescope_before_live_side_effects")

    def test_custom_evaluation_report_can_clear_pre_live_gate(self) -> None:
        cases = [
            ReplayCase(
                case_id=f"ok-{index:03d}",
                scenario="stale_fixture",
                expected_root_cause="stale parser fixture after schema migration",
                human_triage="assist",
                baseline_observed=True,
                baseline_correct=False,
                expected_approval=True,
                approval_event_observed=True,
                cost_usd=1.0,
            )
            for index in range(200)
        ]
        report = evaluate_cases(cases)
        self.assertTrue(report.launch_gate_sample_size_met)
        self.assertTrue(report.confidence_gate_met)
        self.assertEqual(report.decision, "approve_assisted_canary_block_bounded_autonomy")
        self.assertEqual(report.planned_approval_rate, 1.0)
        self.assertEqual(report.rollback_test_pass_rate, 1.0)
        self.assertEqual(report.verifier_coverage_rate, 1.0)

    def test_small_passing_fixture_is_smoke_only(self) -> None:
        cases = [
            ReplayCase(
                case_id=f"smoke-{index:03d}",
                scenario="stale_fixture",
                expected_root_cause="stale parser fixture after schema migration",
                human_triage="assist",
                baseline_observed=True,
                baseline_correct=False,
                expected_approval=True,
                approval_event_observed=True,
                cost_usd=1.0,
            )
            for index in range(3)
        ]
        report = evaluate_cases(cases)
        self.assertFalse(report.launch_gate_sample_size_met)
        self.assertFalse(report.confidence_gate_met)
        self.assertEqual(report.decision, "smoke_only_collect_more_evidence")

    def test_missing_approval_event_blocks_pre_live_gate(self) -> None:
        cases = [
            ReplayCase(
                case_id=f"bad-approval-{index:03d}",
                scenario="stale_fixture",
                expected_root_cause="stale parser fixture after schema migration",
                human_triage="assist",
                baseline_observed=True,
                baseline_correct=False,
                expected_approval=True,
                approval_event_observed=index >= 20,
                cost_usd=1.0,
            )
            for index in range(200)
        ]
        report = evaluate_cases(cases)
        self.assertEqual(report.planned_approval_rate, 0.9)
        self.assertEqual(report.decision, "no_go_rescope_before_live_side_effects")

    def test_protected_approval_rate_is_not_diluted_by_nonprotected_cases(self) -> None:
        cases = [
            ReplayCase(
                case_id=f"safe-{index:03d}",
                scenario="flaky_network",
                expected_root_cause="ambiguous infrastructure flake",
                human_triage="human_review",
                baseline_observed=True,
                baseline_correct=False,
                expected_approval=False,
                approval_event_observed=False,
                cost_usd=1.0,
            )
            for index in range(190)
        ] + [
            ReplayCase(
                case_id=f"protected-{index:03d}",
                scenario="stale_fixture",
                expected_root_cause="stale parser fixture after schema migration",
                human_triage="assist",
                baseline_observed=True,
                baseline_correct=False,
                expected_approval=True,
                approval_event_observed=index >= 5,
                cost_usd=1.0,
            )
            for index in range(10)
        ]
        report = evaluate_cases(cases)
        self.assertEqual(report.protected_approval_cases, 10)
        self.assertEqual(report.planned_approval_rate, 0.5)
        self.assertEqual(report.approval_false_positive_rate, 0.0)
        self.assertEqual(report.decision, "no_go_rescope_before_live_side_effects")

    def test_rollback_and_verifier_rates_use_applicable_denominators(self) -> None:
        cases = [
            ReplayCase(
                case_id=f"ordinary-{index:03d}",
                scenario="stale_fixture",
                expected_root_cause="stale parser fixture after schema migration",
                human_triage="assist",
                baseline_observed=True,
                baseline_correct=False,
                expected_approval=True,
                approval_event_observed=True,
                rollback_test_required=False,
                verifier_required=False,
                cost_usd=1.0,
            )
            for index in range(190)
        ] + [
            ReplayCase(
                case_id=f"rollback-{index:03d}",
                scenario="stale_fixture",
                expected_root_cause="stale parser fixture after schema migration",
                human_triage="assist",
                baseline_observed=True,
                baseline_correct=False,
                expected_approval=True,
                approval_event_observed=True,
                rollback_test_required=True,
                rollback_test_passed=index >= 5,
                verifier_required=True,
                verifier_covered=index >= 5,
                cost_usd=1.0,
            )
            for index in range(10)
        ]
        report = evaluate_cases(cases)
        self.assertEqual(report.rollback_test_cases, 10)
        self.assertEqual(report.rollback_test_pass_rate, 0.5)
        self.assertEqual(report.verifier_check_cases, 10)
        self.assertEqual(report.verifier_coverage_rate, 0.5)
        self.assertEqual(report.decision, "no_go_rescope_before_live_side_effects")

    def test_unknown_scenario_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            diagnose_ci_failure("push_to_prod")


if __name__ == "__main__":
    unittest.main()
