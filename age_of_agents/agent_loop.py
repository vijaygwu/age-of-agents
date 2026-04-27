"""Typed agent-loop example for the Book 5 CI diagnosis case."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Iterable

from .ci_diagnosis import diagnose_ci_failure
from .tool_policy import (
    DEFAULT_TARGET_PATHS,
    TOOL_CONTRACTS,
    ApprovalGrant,
    ToolRequest,
    build_approval_grant,
    evaluate_tool_request,
)


@dataclass(frozen=True)
class AgentLoopState:
    phase: str
    scenario: str
    objective: str
    observations: tuple[str, ...]
    proposed_action: str
    policy_decision: str
    final_status: str


@dataclass(frozen=True)
class AgentLoopRun:
    scenario: str
    approval_grant: ApprovalGrant | None
    states: tuple[AgentLoopState, ...]


def run_typed_agent_loop(scenario: str, approved: bool = False) -> AgentLoopRun:
    """Run a deterministic gather-decide-policy-gate loop."""

    objective = "diagnose CI failure without unapproved protected side effects"
    diagnosis = diagnose_ci_failure(scenario)
    observations = tuple(trace.evidence for trace in diagnosis.traces)
    states: list[AgentLoopState] = [
        AgentLoopState(
            phase="initialize",
            scenario=scenario,
            objective=objective,
            observations=(),
            proposed_action="gather read-only evidence",
            policy_decision="not_evaluated",
            final_status="running",
        ),
        AgentLoopState(
            phase="diagnose",
            scenario=scenario,
            objective=objective,
            observations=observations,
            proposed_action=diagnosis.next_action,
            policy_decision="read-only evidence captured",
            final_status="running",
        ),
    ]

    if diagnosis.escalation_required:
        states.append(
            AgentLoopState(
                phase="escalate",
                scenario=scenario,
                objective=objective,
                observations=observations,
                proposed_action=diagnosis.next_action,
                policy_decision="no protected action proposed",
                final_status="escalated_to_human",
            )
        )
        return AgentLoopRun(scenario=scenario, approval_grant=None, states=tuple(states))

    protected_tool = "update_dependency" if scenario == "missing_dependency" else "prepare_patch"
    request_args = {"scenario": scenario, "target_path": DEFAULT_TARGET_PATHS[protected_tool]}
    approval_grant = (
        build_approval_grant(TOOL_CONTRACTS[protected_tool], request_args)
        if approved
        else None
    )
    decision = evaluate_tool_request(
        ToolRequest(
            tool_name=protected_tool,
            args=request_args,
            approval_grant=approval_grant,
        )
    )
    states.append(
        AgentLoopState(
            phase="policy_gate",
            scenario=scenario,
            objective=objective,
            observations=observations,
            proposed_action=protected_tool,
            policy_decision=decision.reason,
            final_status="ready_to_execute" if decision.allowed else "waiting_for_approval",
        )
    )
    return AgentLoopRun(scenario=scenario, approval_grant=approval_grant, states=tuple(states))


def loop_to_json(run: AgentLoopRun) -> str:
    return json.dumps(asdict(run), indent=2, sort_keys=True)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Book 5 typed agent-loop demo.")
    parser.add_argument("--scenario", default="stale_fixture")
    parser.add_argument("--approve", action="store_true", help="Attach a scoped demo approval grant.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(loop_to_json(run_typed_agent_loop(args.scenario, args.approve)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
