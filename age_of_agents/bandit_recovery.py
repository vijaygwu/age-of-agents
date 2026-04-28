"""Constrained bandit-style recovery selection for Book 5."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class RecoveryArm:
    name: str
    scenario: str
    sandbox_successes: int
    sandbox_trials: int
    protected_live_action: bool

    @property
    def empirical_success_rate(self) -> float:
        return self.sandbox_successes / self.sandbox_trials


@dataclass(frozen=True)
class BanditDecision:
    scenario: str
    selected_arm: str
    selected_score: float
    blocked_arms: tuple[str, ...]
    policy_note: str


RECOVERY_ARMS = (
    RecoveryArm("refresh_fixture", "stale_fixture", 8, 10, protected_live_action=False),
    RecoveryArm("rerun_schema_migration_replay", "stale_fixture", 5, 12, protected_live_action=False),
    RecoveryArm("propose_dependency_update", "missing_dependency", 7, 10, protected_live_action=False),
    RecoveryArm("inspect_dependency_cache", "missing_dependency", 4, 9, protected_live_action=False),
    RecoveryArm("retry_network_job", "flaky_network", 4, 10, protected_live_action=False),
    RecoveryArm("collect_network_trace", "flaky_network", 6, 12, protected_live_action=False),
    RecoveryArm("push_direct_fix", "stale_fixture", 10, 10, protected_live_action=True),
)


def ucb_score(arm: RecoveryArm, total_trials: int) -> float:
    """Upper confidence bound over sandbox-only trial outcomes."""

    exploration = (math.log(total_trials) / arm.sandbox_trials) ** 0.5
    return arm.empirical_success_rate + exploration


def choose_recovery_strategy(scenario: str) -> BanditDecision:
    """Choose a sandbox-verified recovery arm without granting broad autonomy."""

    candidates = [arm for arm in RECOVERY_ARMS if arm.scenario == scenario]
    if not candidates:
        raise ValueError(f"no recovery arms registered for scenario: {scenario}")

    blocked = tuple(arm.name for arm in candidates if arm.protected_live_action)
    eligible = [arm for arm in candidates if not arm.protected_live_action]
    if not eligible:
        raise ValueError(f"no sandbox recovery arms registered for scenario: {scenario}")
    total_trials = sum(arm.sandbox_trials for arm in eligible)
    selected = max(eligible, key=lambda arm: ucb_score(arm, total_trials))
    return BanditDecision(
        scenario=scenario,
        selected_arm=selected.name,
        selected_score=round(ucb_score(selected, total_trials), 2),
        blocked_arms=blocked,
        policy_note="UCB-style bandit choice is limited to sandbox recovery proposals, not autonomous live writes",
    )


def decision_to_json(decision: BanditDecision) -> str:
    return json.dumps(asdict(decision), indent=2, sort_keys=True)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Book 5 constrained recovery selection demo.")
    parser.add_argument("--scenario", default="stale_fixture")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(decision_to_json(choose_recovery_strategy(args.scenario)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
