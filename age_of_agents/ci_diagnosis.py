"""A small CI-diagnosis agent case study.

The example is deliberately deterministic. It models the control structure from
Book 5: gather evidence, keep task state explicit, avoid protected side effects,
and escalate when the evidence is not strong enough.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
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
    requested_by: str
    approved_by: str


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
    "cache_warmup": {
        "log": "first parser shard is slow after image refresh but recovers on replay",
        "repo": "cache initialization path is read-only and needs no fixture or dependency change",
        "replay": "sandbox replay warms the cache and passes without a protected write",
    },
}


def _trace(
    step: str,
    evidence: str,
    verifier: str,
    decision: str,
    scenario: str,
    sequence: int,
    run_id: str,
    base_time: datetime,
    postcondition_result: str = "passed",
    evaluation_lane: str = "offline_replay",
    requested_by: str = "ci-diagnosis-agent",
    approved_by: str = "",
) -> StepTrace:
    contract = READ_ONLY_TOOLS[step]
    started_at = base_time + timedelta(seconds=sequence)
    completed_at = base_time + timedelta(seconds=sequence + 1)
    return StepTrace(
        run_id=run_id,
        agent_version="book5-demo-v1",
        evaluation_lane=evaluation_lane,
        step=step,
        tool_contract_id=contract.tool_contract_id,
        tool_args={"scenario": scenario},
        evidence=evidence,
        approval_outcome="not_required",
        verifier=verifier,
        postcondition_result=postcondition_result,
        decision=decision,
        started_at=started_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        completed_at=completed_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
        side_effect_summary=contract.side_effects,
        requested_by=requested_by,
        approved_by=approved_by,
    )


def _require_known_scenario(scenario: str) -> dict[str, str]:
    try:
        return SCENARIOS[scenario]
    except KeyError as exc:
        known = ", ".join(sorted(SCENARIOS))
        raise ValueError(f"unknown scenario {scenario!r}; expected one of: {known}") from exc


def diagnose_ci_failure(scenario: str, evaluation_lane: str = "offline_replay") -> DiagnosisResult:
    """Diagnose a bounded CI failure without taking protected side effects."""

    facts = _require_known_scenario(scenario)
    traces: list[StepTrace] = []
    run_suffix = hashlib.sha256(f"{scenario}:{evaluation_lane}".encode("utf-8")).hexdigest()[:8]
    run_id = f"ci-demo-{scenario}-{run_suffix}"
    base_time = datetime(2026, 4, 27, 0, 0, tzinfo=timezone.utc)

    traces.append(
        _trace(
            "inspect_ci_log",
            facts["log"],
            READ_ONLY_TOOLS["inspect_ci_log"].postcondition,
            "continue: failure signature is narrow enough for repo inspection",
            scenario,
            0,
            run_id,
            base_time,
            evaluation_lane=evaluation_lane,
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
            run_id,
            base_time,
            evaluation_lane=evaluation_lane,
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
            run_id,
            base_time,
            postcondition_result="ambiguous" if scenario == "flaky_network" else "passed",
            evaluation_lane=evaluation_lane,
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

    if scenario == "cache_warmup":
        return DiagnosisResult(
            scenario=scenario,
            root_cause="cold parser cache after image refresh",
            next_action="run the read-only cache warmup replay and keep monitoring",
            approval_required=False,
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
