"""A small CI-diagnosis agent case study.

The example is deliberately deterministic. It models the control structure from
Book 5: gather evidence, keep task state explicit, avoid protected side effects,
and escalate when the evidence is not strong enough.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Iterable

from .tool_policy import TOOL_CONTRACTS, ToolContract


@dataclass(frozen=True)
class StepTrace:
    run_id: str
    agent_version: str
    evaluation_lane: str
    step: str
    tool_contract_id: str
    tool_args: dict[str, str]
    evidence: str
    approval_outcome: str
    verifier: str
    postcondition_result: str
    decision: str
    started_at: str
    completed_at: str
    side_effect_summary: str


@dataclass(frozen=True)
class DiagnosisResult:
    scenario: str
    root_cause: str
    next_action: str
    approval_required: bool
    escalation_required: bool
    traces: tuple[StepTrace, ...]


READ_ONLY_TOOLS: dict[str, ToolContract] = {
    name: TOOL_CONTRACTS[name]
    for name in ("inspect_ci_log", "inspect_repo", "run_replay")
}


SCENARIOS = {
    "stale_fixture": {
        "log": "parser shard fails only in CI after schema migration",
        "repo": "fixture loader still points at v1 schema snapshot",
        "replay": "targeted replay reproduces failure and passes with refreshed fixture",
    },
    "missing_dependency": {
        "log": "import error for optional parser package",
        "repo": "lockfile omits parser-extra dependency in CI image",
        "replay": "sandbox replay passes after dependency is installed",
    },
    "flaky_network": {
        "log": "download timeout appears across unrelated shards",
        "repo": "no code-path change explains the failure",
        "replay": "retry succeeds once but failure evidence is ambiguous",
    },
}


def _trace(
    step: str,
    evidence: str,
    verifier: str,
    decision: str,
    scenario: str,
    sequence: int,
) -> StepTrace:
    contract = READ_ONLY_TOOLS[step]
    return StepTrace(
        run_id=f"ci-demo-{scenario}",
        agent_version="book5-demo-v1",
        evaluation_lane="offline_replay",
        step=step,
        tool_contract_id=contract.tool_contract_id,
        tool_args={"scenario": scenario},
        evidence=evidence,
        approval_outcome="not_required",
        verifier=verifier,
        postcondition_result="passed",
        decision=decision,
        started_at=f"2026-04-26T00:00:{sequence:02d}Z",
        completed_at=f"2026-04-26T00:00:{sequence + 1:02d}Z",
        side_effect_summary=contract.side_effects,
    )


def _require_known_scenario(scenario: str) -> dict[str, str]:
    try:
        return SCENARIOS[scenario]
    except KeyError as exc:
        known = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"unknown scenario {scenario!r}; expected one of: {known}") from exc


def diagnose_ci_failure(scenario: str) -> DiagnosisResult:
    """Diagnose a bounded CI failure without taking protected side effects."""

    facts = _require_known_scenario(scenario)
    traces: list[StepTrace] = []

    traces.append(
        _trace(
            "inspect_ci_log",
            facts["log"],
            READ_ONLY_TOOLS["inspect_ci_log"].postcondition,
            "continue: failure signature is narrow enough for repo inspection",
            scenario,
            0,
        )
    )
    traces.append(
        _trace(
            "inspect_repo",
            facts["repo"],
            READ_ONLY_TOOLS["inspect_repo"].postcondition,
            "continue: hypothesis is testable in sandbox replay",
            scenario,
            2,
        )
    )
    traces.append(
        _trace(
            "run_replay",
            facts["replay"],
            READ_ONLY_TOOLS["run_replay"].postcondition,
            "evaluate replay evidence before proposing a protected change",
            scenario,
            4,
        )
    )

    if scenario == "stale_fixture":
        return DiagnosisResult(
            scenario=scenario,
            root_cause="stale parser fixture after schema migration",
            next_action="prepare a patch proposal that refreshes the fixture and request review",
            approval_required=True,
            escalation_required=False,
            traces=tuple(traces),
        )

    if scenario == "missing_dependency":
        return DiagnosisResult(
            scenario=scenario,
            root_cause="missing parser-extra dependency in CI image",
            next_action="prepare a dependency update proposal and request review",
            approval_required=True,
            escalation_required=False,
            traces=tuple(traces),
        )

    return DiagnosisResult(
        scenario=scenario,
        root_cause="ambiguous infrastructure flake",
        next_action="escalate with logs, replay result, and uncertainty instead of retrying indefinitely",
        approval_required=False,
        escalation_required=True,
        traces=tuple(traces),
    )


def result_to_json(result: DiagnosisResult) -> str:
    payload = asdict(result)
    return json.dumps(payload, indent=2, sort_keys=True)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Book 5 CI diagnosis case study.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="stale_fixture")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(result_to_json(diagnose_ci_failure(args.scenario)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
