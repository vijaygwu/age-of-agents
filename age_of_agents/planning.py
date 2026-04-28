"""Plan-act-verify-replan example for Book 5."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Iterable

from .ci_diagnosis import diagnose_ci_failure


@dataclass(frozen=True)
class PlanStep:
    name: str
    tool: str
    expected_postcondition: str
    evidence: str
    status: str


@dataclass(frozen=True)
class PlanningRun:
    scenario: str
    initial_budget: int
    budget_remaining: int
    replan_count: int
    final_decision: str
    steps: tuple[PlanStep, ...]


def run_plan_act_verify_replan(scenario: str, step_budget: int = 5) -> PlanningRun:
    """Execute a bounded plan and stop when verification is ambiguous."""

    if step_budget < 3:
        raise ValueError("the demo plan needs at least three steps of budget")

    diagnosis = diagnose_ci_failure(scenario)
    steps = [
        PlanStep(
            name="read failure signature",
            tool="inspect_ci_log",
            expected_postcondition="dominant failure signature extracted",
            evidence=diagnosis.traces[0].evidence,
            status="verified",
        ),
        PlanStep(
            name="inspect likely code path",
            tool="inspect_repo",
            expected_postcondition="relevant code path and fixture path checked",
            evidence=diagnosis.traces[1].evidence,
            status="verified",
        ),
        PlanStep(
            name="run targeted replay",
            tool="run_replay",
            expected_postcondition="targeted shard completed and signature changed or persisted",
            evidence=diagnosis.traces[2].evidence,
            status="ambiguous" if diagnosis.escalation_required else "verified",
        ),
    ]
    budget_remaining = step_budget - len(steps)
    replan_count = 0

    if diagnosis.escalation_required:
        if budget_remaining > 0:
            steps.append(
                PlanStep(
                    name="replan to human escalation",
                    tool="none",
                    expected_postcondition="uncertainty is explicit and bounded",
                    evidence=diagnosis.next_action,
                    status="escalated",
                )
            )
            budget_remaining -= 1
            replan_count = 1
        final_decision = "escalate_with_evidence_packet"
    elif not diagnosis.approval_required:
        if budget_remaining > 0:
            steps.append(
                PlanStep(
                    name="complete read-only recovery",
                    tool="run_replay",
                    expected_postcondition="replay completed without protected mutation",
                    evidence=diagnosis.next_action,
                    status="verified",
                )
            )
            budget_remaining -= 1
        final_decision = "complete_without_protected_change"
    else:
        protected_tool_by_scenario = {
            "missing_dependency": ("prepare dependency update request", "update_dependency"),
            "stale_fixture": ("prepare fixture patch request", "prepare_patch"),
        }
        request_name, protected_tool = protected_tool_by_scenario[scenario]
        if budget_remaining > 0:
            steps.append(
                PlanStep(
                    name=request_name,
                    tool=protected_tool,
                    expected_postcondition="human review request includes trace evidence",
                    evidence=diagnosis.next_action,
                    status="approval_required",
                )
            )
            budget_remaining -= 1
        final_decision = "request_approval_before_protected_change"

    return PlanningRun(
        scenario=scenario,
        initial_budget=step_budget,
        budget_remaining=budget_remaining,
        replan_count=replan_count,
        final_decision=final_decision,
        steps=tuple(steps),
    )


def planning_to_json(run: PlanningRun) -> str:
    return json.dumps(asdict(run), indent=2, sort_keys=True)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Book 5 plan-act-verify-replan demo.")
    parser.add_argument("--scenario", default="flaky_network")
    parser.add_argument("--step-budget", type=int, default=5)
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(planning_to_json(run_plan_act_verify_replan(args.scenario, args.step_budget)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
