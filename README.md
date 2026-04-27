# Age of Agents Companion Code

Runnable companion material for Book 5, `The Age of AI Agents`.

This repository starts with the CI-diagnosis case study used across the book. It is intentionally small: the goal is to show the control boundaries a production agent needs before it earns more autonomy.

Requires Python 3.10 or newer.

## Run

From this directory:

```bash
python3 -m age_of_agents.ci_diagnosis --scenario stale_fixture
python3 -m age_of_agents.ci_diagnosis --scenario missing_dependency
python3 -m age_of_agents.ci_diagnosis --scenario flaky_network
python3 -m age_of_agents.agent_loop --scenario stale_fixture
python3 -m age_of_agents.agent_loop --scenario stale_fixture --approve
python3 -m age_of_agents.tool_policy --tool prepare_patch
python3 -m age_of_agents.tool_policy --tool prepare_patch --invalid-args
python3 -m age_of_agents.tool_policy --tool prepare_patch --approve
python3 -m age_of_agents.tool_policy --tool prepare_patch --attempt 2 --approve
python3 -m age_of_agents.tool_policy --tool prepare_patch --attempt 2 --approve --retry-nonce retry-2
python3 -m age_of_agents.planning --scenario flaky_network
python3 -m age_of_agents.memory
python3 -m age_of_agents.evidence_packets --scenario stale_fixture
python3 -m age_of_agents.multi_agent_demo --scenario stale_fixture
python3 -m age_of_agents.bandit_recovery --scenario stale_fixture
python3 -m age_of_agents.evaluation --report --output /tmp/book5-demo-report.json
python3 -m age_of_agents.evaluation --cases examples/replay_cases.json --output /tmp/book5-sample-report.json
python3 -m age_of_agents.autonomy_gate --report-file /tmp/book5-sample-report.json
python3 -m unittest discover -s tests
```

`examples/replay_cases.json` is a smoke fixture. It exercises the report shape, baseline fields, approval-event fields, applicable-case denominators, and staged gate output, but it is intentionally too small to clear a launch gate. The launch-gate path requires at least 200 replay cases, paired baseline comparison, protected-case approval recall, rollback/verifier checks over the applicable cases, and confidence bounds that clear the thresholds.

From the enclosing `publish/` directory, either `cd code/Age-of-Agents` first or install the package in editable mode:

```bash
python3 -m pip install -e code/Age-of-Agents
python3 -m age_of_agents.ci_diagnosis --scenario stale_fixture
python3 -m age_of_agents.evaluation --cases code/Age-of-Agents/examples/replay_cases.json --output /tmp/book5-sample-report.json
python3 -m age_of_agents.autonomy_gate --report-file /tmp/book5-sample-report.json
```

## What This Demonstrates

- typed task state rather than free-form memory
- read-only diagnosis before protected side effects
- explicit tool contracts with deterministic argument validation
- explicit approval gates and renewed approval for mutable retries
- postcondition metadata captured in traces for later verifier/replay checks
- escalation when evidence is ambiguous
- versioned trace records with tool contract ids, arguments, approval outcomes, postconditions, timing, run id, agent version, and evaluation lane
- a tiny replay/shadow smoke report that accepts JSON case files with baseline outcomes and expected approval events, then demonstrates how a staged go/no-go gate is computed
- typed agent-loop state transitions for the running CI case
- tool approval policy, including contract failures, scoped approval grants, canonical workspace path checks, and renewed approval for mutable retries
- plan-act-verify-replan behavior under a step budget
- memory conflict resolution against a system of record
- trace-backed evidence packets for human or grader review
- autonomy gate decisions from replay, shadow, planned approval, safety, rollback, verifier, and optional online evidence
- workflow versus multi-agent architecture comparison
- constrained bandit-style recovery selection limited to sandbox evidence
