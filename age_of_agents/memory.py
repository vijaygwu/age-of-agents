"""Memory provenance and source-of-truth conflict examples for Book 5."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    kind: str
    claim: str
    source: str
    confidence: float
    permission_scope: str
    observed_at: str
    status: str = "candidate"


@dataclass(frozen=True)
class SourceOfTruth:
    name: str
    claim: str
    checked_at: str


@dataclass(frozen=True)
class MemoryResolution:
    action: str
    trusted_claim: str
    memory_status: str
    reason: str
    corrected_record: MemoryRecord | None


def resolve_memory_against_source(
    memory: MemoryRecord,
    source_of_truth: SourceOfTruth,
) -> MemoryResolution:
    """Trust the system of record over stale or conflicting agent memory."""

    if memory.claim == source_of_truth.claim:
        return MemoryResolution(
            action="promote",
            trusted_claim=memory.claim,
            memory_status="trusted",
            reason="memory agrees with the system of record",
            corrected_record=MemoryRecord(
                **{**asdict(memory), "status": "trusted"},
            ),
        )

    corrected = MemoryRecord(
        memory_id=f"{memory.memory_id}.correction",
        kind=memory.kind,
        claim=source_of_truth.claim,
        source=source_of_truth.name,
        confidence=1.0,
        permission_scope=memory.permission_scope,
        observed_at=source_of_truth.checked_at,
        status="trusted",
    )
    return MemoryResolution(
        action="quarantine_and_correct",
        trusted_claim=source_of_truth.claim,
        memory_status="quarantined",
        reason="memory conflicted with the current system of record",
        corrected_record=corrected,
    )


def demo_memory_conflict() -> MemoryResolution:
    stale_memory = MemoryRecord(
        memory_id="incident-041.fixture-schema",
        kind="episodic",
        claim="parser fixture uses schema v1",
        source="prior incident summary",
        confidence=0.72,
        permission_scope="ci-diagnosis-only",
        observed_at="2026-04-20T12:00:00Z",
    )
    repo_truth = SourceOfTruth(
        name="repository schema manifest",
        claim="parser fixture must use schema v2",
        checked_at="2026-04-26T00:00:00Z",
    )
    return resolve_memory_against_source(stale_memory, repo_truth)


def resolution_to_json(resolution: MemoryResolution) -> str:
    return json.dumps(asdict(resolution), indent=2, sort_keys=True)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Book 5 memory conflict demo.")
    parser.parse_args(list(argv) if argv is not None else None)
    print(resolution_to_json(demo_memory_conflict()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
