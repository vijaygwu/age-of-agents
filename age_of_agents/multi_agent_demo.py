"""Workflow versus multi-agent architecture comparison for Book 5."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class ArchitectureOption:
    name: str
    latency_steps: int
    trace_edges: int
    failure_modes: tuple[str, ...]
    recommendation: str


@dataclass(frozen=True)
class ArchitectureComparison:
    scenario: str
    selected: str
    options: tuple[ArchitectureOption, ...]


def compare_architectures(scenario: str = "stale_fixture") -> ArchitectureComparison:
    """Compare control structures for the narrow CI-diagnosis task."""

    options = (
        ArchitectureOption(
            name="single_workflow",
            latency_steps=4,
            trace_edges=3,
            failure_modes=("limited specialization",),
            recommendation="best default for narrow CI diagnosis",
        ),
        ArchitectureOption(
            name="supervisor_with_specialists",
            latency_steps=7,
            trace_edges=9,
            failure_modes=("handoff loss", "duplicate tool calls"),
            recommendation="use only if repo, infra, and test specialists are truly separable",
        ),
        ArchitectureOption(
            name="peer_to_peer_agents",
            latency_steps=10,
            trace_edges=18,
            failure_modes=("coordination loops", "unclear decision owner", "harder audit trail"),
            recommendation="reject for this task shape",
        ),
    )
    selected = "supervisor_with_specialists" if scenario == "cross_team_incident" else "single_workflow"
    return ArchitectureComparison(scenario=scenario, selected=selected, options=options)


def comparison_to_json(comparison: ArchitectureComparison) -> str:
    return json.dumps(asdict(comparison), indent=2, sort_keys=True)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare Book 5 agent architecture options.")
    parser.add_argument("--scenario", default="stale_fixture")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(comparison_to_json(compare_architectures(args.scenario)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
