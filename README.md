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
python3 -m age_of_agents.agent_loop --scenario stale_fixture --approval-grant-file examples/approval_grant_prepare_patch.json --consumed-grants-file /tmp/book5-consumed-grants-agent-loop.json
python3 -m age_of_agents.tool_policy --tool prepare_patch
python3 -m age_of_agents.tool_policy --tool prepare_patch --invalid-args
python3 -m age_of_agents.tool_policy --tool prepare_patch --approve
python3 -m age_of_agents.tool_policy --tool prepare_patch --approval-grant-file examples/approval_grant_prepare_patch.json --consumed-grants-file /tmp/book5-consumed-grants-tool-policy.json
python3 -m age_of_agents.tool_policy --tool prepare_patch --attempt 2 --approve
python3 -m age_of_agents.tool_policy --tool prepare_patch --attempt 2 --approve --retry-nonce retry-2
python3 -m age_of_agents.planning --scenario flaky_network
python3 -m age_of_agents.memory
python3 -m age_of_agents.evidence_packets --scenario stale_fixture
python3 -m age_of_agents.evidence_packets --scenario stale_fixture --approved
python3 -m age_of_agents.multi_agent_demo --scenario stale_fixture
python3 -m age_of_agents.bandit_recovery --scenario stale_fixture
python3 -m age_of_agents.evaluation --report --output /tmp/book5-demo-report.json  # synthetic 300-case demo
python3 -m age_of_agents.evaluation --cases examples/replay_cases.json --output /tmp/book5-sample-report.json
python3 -m age_of_agents.autonomy_gate --cases examples/replay_cases.json
python3 -m age_of_agents.autonomy_gate --cases examples/replay_cases.json --online-evidence-file examples/online_evidence.json
python3 -m age_of_agents.evaluation --cases examples/replay_cases.json | python3 -m age_of_agents.autonomy_gate --report-file -
python3 -m unittest discover -s tests
```

`examples/replay_cases.json` is a smoke fixture. It exercises the report shape, explicit evaluation lanes, supplied candidate outputs, evidence-packet ingestion, baseline fields, scoped approval-request/grant fields, explicit objective/action/postcondition outcomes, protected-action execution, verifier execution and pass outcomes, authoritative shadow diagnoses when available, scoped shadow approval proposals, shadow safety/proposal fields, protected-action success, action-bearing non-protected coverage, assisted/canary ambiguity coverage, applicable-case denominators, paired candidate-only and baseline-only counts, coverage strata, evaluated-scope metadata, confidence-adjustment metadata, and staged gate output, but it is intentionally too small to clear a launch gate. File-based action cases fail closed when required outcome or safety fields are omitted, and repeated case templates are rejected rather than counted as independent launch evidence. `examples/online_evidence.json` documents the bounded-autonomy aggregate-count payload accepted by `autonomy_gate.py`, including raw metric numerators and denominators, a required case-level record manifest with trace-id digest, separate verifier coverage and verifier pass counts, Protected Approval Recall match counts, protected-action success counts, and a structured scope contract with traffic percentage, task classes, allowed tools, protected tools, data domains, rollback trigger, approver, and approval timestamp. The gate consumes raw case files directly or recomputes report-file metrics, evaluated scope, independent evidence fingerprints, and full diagnostics from embedded source cases, rejects report summary-only or tampered report files, and does not let online evidence override a failing pre-live report or expand beyond the evaluated scope. The launch-gate path requires an operational floor of at least 900 independent lane-tagged evidence fingerprints plus enough offline, shadow, assisted/canary, protected-action, action-bearing non-protected, and assisted/canary ambiguity examples for the adjusted confidence bounds to clear each threshold.

The `--approve` examples are simulations of an external approval authority and protected action. The `--approval-grant-file` examples show the integration shape for a grant minted outside the current process and require a consumed-grant registry so a grant id cannot be replayed through the CLI. The checked-in grant file is a demo template whose `DEMO_NOW` placeholders materialize as a 15-minute window at load time; production grants should be issued by an independent approval service. These commands demonstrate scoped grants, policy validation, state transitions, rollback planning, and evidence packet shape; they do not perform a real mutation and must not be reused as launch evidence without replacing the fixture grant and simulated verifier with an independent approval service plus a real post-action read-back.

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
- explicit approval-gate simulations and renewed approval for mutable retries
- postcondition metadata captured in traces for later verifier/replay checks
- escalation when evidence is ambiguous
- versioned trace records with tool contract ids, arguments, approval outcomes, postconditions, timing, run id, actor lineage, agent version, and evaluation lane
- a tiny lane-tagged replay/shadow/assisted/canary smoke report that accepts JSON case files with candidate outputs, evidence-packet fields, baseline outcomes and paired disagreement counts, explicit objective/action/postcondition outcomes, verifier execution and pass outcomes, authoritative shadow diagnoses when available, scoped approval requests and grants, protected-action success, action-bearing non-protected cases, and assisted/canary ambiguity cases, then demonstrates how a staged go/no-go gate is computed
- typed agent-loop state transitions for the running CI case
- tool approval policy, including contract failures, external approval-grant file ingestion, simulated scoped approval grants bound to the requester, distinct approver, canonical action digest over the tool contract plus canonical request payload, canonical workspace path checks, and renewed single-use approval for mutable retries
- plan-act-verify-replan behavior under a step budget
- memory conflict resolution against a system of record
- trace-backed evidence packets that keep pre-change evidence checks separate from post-action verifier outcomes; the approved protected-action packet is explicitly simulation-only until backed by a real verifier
- autonomy gate decisions from replay, shadow, Protected Approval Recall, Protected Action Success Rate, False Approval Request Rate, Unsafe-Action Rate, rollback, verifier coverage, verifier pass outcomes, and optional bounded online evidence
- workflow versus multi-agent architecture comparison
- constrained UCB-style recovery selection limited to sandbox evidence
