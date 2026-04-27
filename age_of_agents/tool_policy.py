"""Tool contracts, argument validation, and approval policy examples for Book 5."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


KNOWN_SCENARIOS = ("flaky_network", "missing_dependency", "stale_fixture")
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ToolContract:
    tool_name: str
    tool_contract_id: str
    mode: str
    side_effects: str
    requires_approval: bool
    idempotent: bool
    postcondition: str
    required_args: tuple[str, ...]
    optional_args: tuple[str, ...] = ()
    allowed_scenarios: tuple[str, ...] = KNOWN_SCENARIOS
    allowed_exact_paths: tuple[str, ...] = ()
    allowed_path_prefixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApprovalGrant:
    tool_contract_id: str
    target_path: str
    actor: str
    issued_at: str
    expires_at: str
    retry_nonce: str = ""


@dataclass(frozen=True)
class ToolRequest:
    tool_name: str
    args: dict[str, str]
    attempt: int = 1
    approval_grant: ApprovalGrant | None = None


@dataclass(frozen=True)
class ContractValidation:
    valid: bool
    errors: tuple[str, ...]


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    approval_required: bool
    renewed_approval_required: bool
    reason: str
    postcondition: str
    side_effect_summary: str
    tool_contract_id: str
    contract_valid: bool
    validation_errors: tuple[str, ...]


TOOL_CONTRACTS = {
    "inspect_ci_log": ToolContract(
        tool_name="inspect_ci_log",
        tool_contract_id="tool.inspect_ci_log.v1",
        mode="read-only",
        side_effects="none",
        requires_approval=False,
        idempotent=True,
        postcondition="dominant failure signature extracted",
        required_args=("scenario",),
        optional_args=("log_source",),
    ),
    "inspect_repo": ToolContract(
        tool_name="inspect_repo",
        tool_contract_id="tool.inspect_repo.v1",
        mode="read-only",
        side_effects="none",
        requires_approval=False,
        idempotent=True,
        postcondition="relevant code path and fixture path checked",
        required_args=("scenario",),
        optional_args=("path",),
        allowed_path_prefixes=("age_of_agents/", "tests/", "fixtures/"),
    ),
    "run_replay": ToolContract(
        tool_name="run_replay",
        tool_contract_id="tool.run_replay.v1",
        mode="sandboxed",
        side_effects="temporary replay artifacts",
        requires_approval=False,
        idempotent=True,
        postcondition="targeted shard completed and signature changed or persisted",
        required_args=("scenario",),
        optional_args=("shard",),
    ),
    "prepare_patch": ToolContract(
        tool_name="prepare_patch",
        tool_contract_id="tool.prepare_patch.v1",
        mode="protected",
        side_effects="writes a proposed patch to the working tree",
        requires_approval=True,
        idempotent=False,
        postcondition="patch diff exists and verifier can inspect it",
        required_args=("scenario", "target_path"),
        allowed_scenarios=("stale_fixture",),
        allowed_path_prefixes=("fixtures/", "tests/fixtures/"),
    ),
    "update_dependency": ToolContract(
        tool_name="update_dependency",
        tool_contract_id="tool.update_dependency.v1",
        mode="protected",
        side_effects="updates dependency manifest and lockfile",
        requires_approval=True,
        idempotent=False,
        postcondition="dependency diff exists and tests can be rerun",
        required_args=("scenario", "target_path"),
        allowed_scenarios=("missing_dependency",),
        allowed_exact_paths=("pyproject.toml", "requirements.txt", "requirements.lock", "uv.lock"),
        allowed_path_prefixes=("requirements/",),
    ),
}


DEFAULT_TARGET_PATHS = {
    "prepare_patch": "tests/fixtures/parser_schema_v2.json",
    "update_dependency": "requirements.lock",
}


def _safe_relative_path(value: str) -> bool:
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts and value.strip() == value and bool(value)


def _normalize_workspace_path(value: str, workspace_root: Path = WORKSPACE_ROOT) -> tuple[str | None, str | None]:
    if not _safe_relative_path(value):
        return None, "must be a safe relative path"

    root = workspace_root.resolve()
    target = (root / value).resolve(strict=False)
    try:
        relative = target.relative_to(root)
    except ValueError:
        return None, "must resolve inside the approved workspace"
    return relative.as_posix(), None


def _path_allowed(contract: ToolContract, value: str) -> bool:
    exact_allowed = value in contract.allowed_exact_paths
    prefix_allowed = any(value.startswith(prefix) for prefix in contract.allowed_path_prefixes)
    return exact_allowed or prefix_allowed


def _approval_target(args: dict[str, str]) -> str:
    return args.get("target_path") or args.get("path") or ""


def build_approval_grant(
    contract: ToolContract,
    args: dict[str, str],
    *,
    actor: str = "platform-reviewer",
    issued_at: str = "2026-04-26T00:00:00Z",
    expires_at: str = "2026-12-31T23:59:59Z",
    retry_nonce: str = "",
) -> ApprovalGrant:
    target_path = _approval_target(args)
    if target_path:
        normalized, error = _normalize_workspace_path(target_path)
        if error:
            normalized = target_path
        target_path = normalized or target_path
    return ApprovalGrant(
        tool_contract_id=contract.tool_contract_id,
        target_path=target_path,
        actor=actor,
        issued_at=issued_at,
        expires_at=expires_at,
        retry_nonce=retry_nonce,
    )


def validate_approval_grant(
    contract: ToolContract,
    args: dict[str, str],
    grant: ApprovalGrant | None,
    *,
    required_retry_nonce: str = "",
) -> tuple[bool, tuple[str, ...]]:
    if grant is None:
        return False, ("missing scoped approval grant",)

    errors: list[str] = []
    target_path = _approval_target(args)
    if target_path:
        normalized, error = _normalize_workspace_path(target_path)
        if error:
            errors.append(f"approval target {error}")
            normalized = target_path
        target_path = normalized or target_path

    if grant.tool_contract_id != contract.tool_contract_id:
        errors.append("approval grant is bound to a different tool contract")
    if grant.target_path != target_path:
        errors.append("approval grant target path does not match request target")
    if not grant.actor:
        errors.append("approval grant must include an actor")
    if not grant.issued_at or not grant.expires_at or grant.expires_at <= grant.issued_at:
        errors.append("approval grant must include a valid issued/expires window")
    if required_retry_nonce and grant.retry_nonce != required_retry_nonce:
        errors.append("mutable retry requires a fresh retry nonce")
    return not errors, tuple(errors)


def validate_tool_args(contract: ToolContract, args: dict[str, str]) -> ContractValidation:
    """Validate required fields, unknown fields, scenario scope, and path scope."""

    errors: list[str] = []
    allowed_args = set(contract.required_args) | set(contract.optional_args)

    for field in contract.required_args:
        if not args.get(field):
            errors.append(f"missing required argument: {field}")

    for field in sorted(set(args) - allowed_args):
        errors.append(f"unknown argument for {contract.tool_name}: {field}")

    scenario = args.get("scenario")
    if scenario and scenario not in contract.allowed_scenarios:
        allowed = ", ".join(contract.allowed_scenarios)
        errors.append(f"scenario {scenario!r} is outside contract scope; expected one of: {allowed}")

    for path_field in ("path", "target_path"):
        value = args.get(path_field)
        if not value:
            continue
        normalized, error = _normalize_workspace_path(value)
        if error:
            errors.append(f"{path_field} {error}")
            continue
        if (contract.allowed_exact_paths or contract.allowed_path_prefixes) and not _path_allowed(contract, normalized or value):
            allowed = ", ".join(contract.allowed_exact_paths + contract.allowed_path_prefixes)
            errors.append(f"{path_field} must match an allowed path or directory prefix: {allowed}")

    return ContractValidation(valid=not errors, errors=tuple(errors))


def _decision(
    *,
    allowed: bool,
    approval_required: bool,
    renewed_approval_required: bool,
    reason: str,
    contract: ToolContract | None,
    validation: ContractValidation | None = None,
) -> PolicyDecision:
    validation = validation or ContractValidation(valid=True, errors=())
    return PolicyDecision(
        allowed=allowed,
        approval_required=approval_required,
        renewed_approval_required=renewed_approval_required,
        reason=reason,
        postcondition=contract.postcondition if contract else "",
        side_effect_summary=contract.side_effects if contract else "none",
        tool_contract_id=contract.tool_contract_id if contract else "",
        contract_valid=validation.valid,
        validation_errors=validation.errors,
    )


def evaluate_tool_request(request: ToolRequest) -> PolicyDecision:
    """Apply contract validation, approval, and retry policy for a requested tool call."""

    contract = TOOL_CONTRACTS.get(request.tool_name)
    if contract is None:
        return _decision(
            allowed=False,
            approval_required=False,
            renewed_approval_required=False,
            reason=f"unknown tool: {request.tool_name}",
            contract=None,
            validation=ContractValidation(valid=False, errors=(f"unknown tool: {request.tool_name}",)),
        )

    validation = validate_tool_args(contract, request.args)
    if not validation.valid:
        return _decision(
            allowed=False,
            approval_required=contract.requires_approval,
            renewed_approval_required=False,
            reason="contract validation failed",
            contract=contract,
            validation=validation,
        )

    if request.attempt < 1:
        return _decision(
            allowed=False,
            approval_required=False,
            renewed_approval_required=False,
            reason="attempt count must be positive",
            contract=contract,
            validation=validation,
        )

    required_retry_nonce = f"retry-{request.attempt}" if request.attempt > 1 and not contract.idempotent else ""
    approval_valid, approval_errors = validate_approval_grant(
        contract,
        request.args,
        request.approval_grant,
        required_retry_nonce=required_retry_nonce,
    )

    if request.attempt > 1 and not contract.idempotent and not approval_valid:
        return _decision(
            allowed=False,
            approval_required=True,
            renewed_approval_required=True,
            reason="mutable retry requires renewed scoped approval: " + "; ".join(approval_errors),
            contract=contract,
            validation=validation,
        )

    if contract.requires_approval and not approval_valid:
        return _decision(
            allowed=False,
            approval_required=True,
            renewed_approval_required=False,
            reason="protected tool requires scoped approval: " + "; ".join(approval_errors),
            contract=contract,
            validation=validation,
        )

    return _decision(
        allowed=True,
        approval_required=contract.requires_approval,
        renewed_approval_required=False,
        reason="policy permits tool call",
        contract=contract,
        validation=validation,
    )


def build_cli_args(tool_name: str, scenario: str, target_path: str, invalid_args: bool) -> dict[str, str]:
    if invalid_args:
        return {"scenario": scenario, "target_path": "/etc/passwd"}

    args = {"scenario": scenario}
    if tool_name in DEFAULT_TARGET_PATHS:
        args["target_path"] = target_path or DEFAULT_TARGET_PATHS[tool_name]
    return args


def decision_to_json(decision: PolicyDecision) -> str:
    return json.dumps(asdict(decision), indent=2, sort_keys=True)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a Book 5 tool-policy request.")
    parser.add_argument("--tool", choices=sorted(TOOL_CONTRACTS), default="prepare_patch")
    parser.add_argument("--scenario", choices=KNOWN_SCENARIOS, default="stale_fixture")
    parser.add_argument("--target-path", default="")
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--approve", action="store_true", help="Attach a scoped demo approval grant.")
    parser.add_argument("--approval-actor", default="platform-reviewer")
    parser.add_argument("--approval-expires-at", default="2026-12-31T23:59:59Z")
    parser.add_argument("--retry-nonce", default="")
    parser.add_argument("--invalid-args", action="store_true", help="Send an intentionally invalid path.")
    args = parser.parse_args(list(argv) if argv is not None else None)
    request_args = build_cli_args(args.tool, args.scenario, args.target_path, args.invalid_args)
    contract = TOOL_CONTRACTS[args.tool]
    approval_grant = (
        build_approval_grant(
            contract,
            request_args,
            actor=args.approval_actor,
            expires_at=args.approval_expires_at,
            retry_nonce=args.retry_nonce,
        )
        if args.approve
        else None
    )
    request = ToolRequest(
        tool_name=args.tool,
        args=request_args,
        attempt=args.attempt,
        approval_grant=approval_grant,
    )
    print(decision_to_json(evaluate_tool_request(request)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
