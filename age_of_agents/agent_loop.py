"""Typed agent-loop example for the Book 5 CI diagnosis case."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Iterable

from .ci_diagnosis import diagnose_ci_failure
from .tool_policy import (
    DEFAULT_MUTATION_ARTIFACTS,
    DEFAULT_TARGET_PATHS,
    TOOL_CONTRACTS,
    ApprovalGrant,
    ToolRequest,
    build_action_digest,
    build_approval_grant,
    evaluate_tool_request,
    load_consumed_grant_ids,
    load_approval_grant,
    store_consumed_grant_id,
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
    verifier_outcome: str = ""
    rollback_action: str = ""


@dataclass(frozen=True)
class AgentLoopRun:
    scenario: str
    approval_grant: ApprovalGrant | None
    states: tuple[AgentLoopState, ...]


def run_typed_agent_loop(
    scenario: str,
    approved: bool = False,
    requester: str = "ci-diagnosis-agent",
    approver: str = "platform-reviewer",
    approval_grant: ApprovalGrant | None = None,
    consumed_grant_ids: tuple[str, ...] = (),
) -> AgentLoopRun:
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

    if not diagnosis.approval_required:
        states.append(
            AgentLoopState(
                phase="execute_read_only",
                scenario=scenario,
                objective=objective,
                observations=observations,
                proposed_action=diagnosis.next_action,
                policy_decision="no protected approval required",
                final_status="completed_without_protected_side_effect",
            )
        )
        return AgentLoopRun(scenario=scenario, approval_grant=None, states=tuple(states))

    protected_tool_by_scenario = {
        "missing_dependency": "update_dependency",
        "stale_fixture": "prepare_patch",
    }
    protected_tool = protected_tool_by_scenario[scenario]
    request_args = {
        "scenario": scenario,
        "target_path": DEFAULT_TARGET_PATHS[protected_tool],
        "mutation_artifact": DEFAULT_MUTATION_ARTIFACTS[protected_tool],
    }
    action_digest = build_action_digest(TOOL_CONTRACTS[protected_tool], request_args)
    approval_grant = approval_grant or (
        build_approval_grant(
            TOOL_CONTRACTS[protected_tool],
            request_args,
            requested_by=requester,
            approved_by=approver,
            action_digest=action_digest,
        )
        if approved
        else None
    )
    decision = evaluate_tool_request(
        ToolRequest(
            tool_name=protected_tool,
            args=request_args,
            approval_grant=approval_grant,
            requested_by=requester,
            action_digest=action_digest,
            consumed_grant_ids=consumed_grant_ids,
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
    if decision.allowed:
        states.append(
            AgentLoopState(
                phase="execute_protected_demo",
                scenario=scenario,
                objective=objective,
                observations=observations,
                proposed_action=f"apply demo mutation artifact to {request_args['target_path']}",
                policy_decision=f"simulated scoped approval grant consumed: {approval_grant.grant_id}",
                final_status="approved_pending_real_execution",
                verifier_outcome="not_run",
                rollback_action=f"restore {request_args['target_path']} from pre-action snapshot if verifier fails",
            )
        )
        states.append(
            AgentLoopState(
                phase="prepare_post_action_verifier",
                scenario=scenario,
                objective=objective,
                observations=observations,
                proposed_action=decision.postcondition,
                policy_decision="demo stops before live side effect; independent post-action verifier not run",
                final_status="approved_pending_real_verifier",
                verifier_outcome="not_run",
                rollback_action=f"rollback plan prepared for {request_args['target_path']}",
            )
        )
    return AgentLoopRun(scenario=scenario, approval_grant=approval_grant, states=tuple(states))


def loop_to_json(run: AgentLoopRun) -> str:
    return json.dumps(asdict(run), indent=2, sort_keys=True)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Book 5 typed agent-loop demo.")
    parser.add_argument("--scenario", default="stale_fixture")
    parser.add_argument("--requester", default="ci-diagnosis-agent")
    parser.add_argument("--approver", default="platform-reviewer")
    parser.add_argument("--approve", action="store_true", help="Attach a scoped demo approval grant.")
    parser.add_argument("--approval-grant-file", help="Read a scoped grant issued by an external approval service.")
    parser.add_argument("--consumed-grants-file", help="JSON registry of consumed external approval grant ids.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.approve and args.approval_grant_file:
        parser.error("--approve and --approval-grant-file are mutually exclusive")
    if args.approval_grant_file and not args.consumed_grants_file:
        parser.error("--approval-grant-file requires --consumed-grants-file for single-use replay protection")
    external_grant = load_approval_grant(args.approval_grant_file) if args.approval_grant_file else None
    run = run_typed_agent_loop(
        args.scenario,
        args.approve or external_grant is not None,
        args.requester,
        args.approver,
        external_grant,
        (
            load_consumed_grant_ids(args.consumed_grants_file)
            if args.consumed_grants_file
            else ()
        )
    )
    if external_grant is not None and args.consumed_grants_file and run.states[-1].final_status == "approved_pending_real_verifier":
        store_consumed_grant_id(args.consumed_grants_file, external_grant.grant_id)
    print(loop_to_json(run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
