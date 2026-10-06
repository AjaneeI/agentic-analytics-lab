"""Deterministic validators for the versioned Personal Ops package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LEVELS = {"green", "yellow", "red"}
MODEL = {
    "name": "hermes-local:qwen3.5-9b",
    "provider": "custom",
    "base_url": "http://127.0.0.1:11434/v1",
    "context_length": 65536,
}
TOOLS = ["clarify", "delegate_task", "personalops_repository"]
WORKER_FIELDS = [
    "Objective",
    "Inputs",
    "Allowed changes",
    "Acceptance",
    "Evidence",
    "Stop",
]
CONSULTATION_FIELDS = [
    "Decision needed",
    "Why it matters",
    "Options/tradeoffs",
    "Hermes recommendation",
]
FINAL_STATUS_FIELDS = [
    "current_state",
    "recommended_action",
    "action_taken",
    "verification",
    "decision_needed",
]
ALLOWED_CHECKS = {
    "context": ["python3", "scripts/check_project_context.py"],
    "diff": ["git", "diff", "--check"],
    "full": [
        "python3",
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-v",
    ],
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def load_policy(root: Path) -> dict[str, Any]:
    return _load_json(Path(root) / "policy.json")


def load_workflow(root: Path) -> dict[str, Any]:
    return _load_json(Path(root) / "workflow.json")


def validate_contracts(root: Path) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    try:
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        policy = load_policy(root)
        workflow = load_workflow(root)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [f"contract load failed: {exc}"]

    levels = policy.get("levels")
    if not isinstance(levels, dict) or set(levels) != LEVELS:
        errors.append("policy.levels must contain exactly green, yellow, red")
    elif any(not isinstance(levels[name], list) or not levels[name] for name in LEVELS):
        errors.append("each policy level must be a non-empty list")

    if policy.get("package_version") != version:
        errors.append("policy.package_version must match VERSION")
    if workflow.get("package_version") != version:
        errors.append("workflow.package_version must match VERSION")

    consultation = policy.get("consultation")
    if not isinstance(consultation, dict) or consultation.get("required_sections") != CONSULTATION_FIELDS:
        errors.append("policy consultation fields must match the structured clarify contract")

    model = workflow.get("model")
    if not isinstance(model, dict):
        errors.append("workflow.model must be an object")
    else:
        for key, value in MODEL.items():
            if model.get(key) != value:
                if key == "base_url":
                    errors.append("workflow.model.base_url must be loopback Ollama")
                else:
                    errors.append(f"workflow.model.{key} must equal {value!r}")
        if model.get("fallbacks") != []:
            errors.append("workflow.model.fallbacks must be empty")

    if workflow.get("tools") != TOOLS:
        errors.append("workflow.tools must expose only clarify, delegate_task, and personalops_repository")

    worker = workflow.get("worker")
    if not isinstance(worker, dict):
        errors.append("workflow.worker must be an object")
    else:
        if worker.get("max_workers") != 1 or worker.get("max_concurrency") != 1:
            errors.append("workflow.worker must allow exactly one non-concurrent worker")
        if worker.get("required_fields") != WORKER_FIELDS:
            errors.append("workflow.worker.required_fields must match the six-field contract")

    checks = workflow.get("checks")
    if not isinstance(checks, dict) or set(checks) != set(ALLOWED_CHECKS):
        errors.append("workflow.checks must contain exactly the approved named checks")
    else:
        for name, expected in ALLOWED_CHECKS.items():
            row = checks.get(name)
            command = row.get("command") if isinstance(row, dict) else None
            if not isinstance(command, list) or not command or not all(
                isinstance(item, str) and item for item in command
            ):
                errors.append(f"workflow.checks.{name}.command must be a non-empty string list")
            elif command != expected:
                errors.append(f"workflow.checks.{name}.command is not approved")
            timeout = row.get("timeout_seconds") if isinstance(row, dict) else None
            if timeout is not None and (
                not isinstance(timeout, int)
                or isinstance(timeout, bool)
                or not 1 <= timeout <= 600
            ):
                errors.append(f"workflow.checks.{name}.timeout_seconds must be between 1 and 600")

    if workflow.get("final_status_fields") != FINAL_STATUS_FIELDS:
        errors.append("workflow.final_status_fields must match the product response contract")
    return errors
