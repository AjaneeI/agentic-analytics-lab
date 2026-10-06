"""Deterministic validation for an installed Personal Ops Hermes profile."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from personalops.contracts import validate_contracts


_OWNED_CONTRACT_FILES = ("VERSION", "policy.json", "workflow.json")
_PLACEHOLDERS = {
    "__PERSONALOPS_REPOSITORY_ROOT__": "repository_root",
    "__PERSONALOPS_CONTRACT_ROOT__": "contract_root",
    "__PERSONALOPS_EVIDENCE_LOG__": "evidence_log",
    "__PERSONALOPS_HERMES_ROOT__": "hermes_root",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_config(
    package_root: Path,
    profile_root: Path,
    repo_root: Path,
    hermes_root: Path,
) -> str:
    """Render only absolute, caller-approved paths into the profile template."""
    values = {
        "repository_root": str(Path(repo_root).resolve()),
        "contract_root": str((Path(profile_root).resolve() / "personalops")),
        "evidence_log": str((Path(profile_root).resolve() / "cache" / "events.jsonl")),
        "hermes_root": str(Path(hermes_root).resolve()),
    }
    text = (Path(package_root) / "profile" / "config.yaml").read_text(encoding="utf-8")
    for token, key in _PLACEHOLDERS.items():
        text = text.replace(token, json.dumps(values[key]))
    return text


def validate_runtime_guard(contract_path: Path, hermes_root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    try:
        contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return False, [f"runtime guard contract load failed: {exc}"]
    files = contract.get("files") if isinstance(contract, dict) else None
    if not isinstance(files, list) or not files:
        return False, ["runtime guard contract must name at least one file"]
    root = Path(hermes_root).resolve()
    for row in files:
        relative = row.get("path") if isinstance(row, dict) else None
        expected = row.get("sha256") if isinstance(row, dict) else None
        if not isinstance(relative, str) or not isinstance(expected, str):
            errors.append("runtime guard contract contains an invalid file entry")
            continue
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append(f"runtime guard path escapes Hermes root: {relative}")
            continue
        if not candidate.is_file():
            errors.append(f"runtime guard file missing: {relative}")
        elif _sha256(candidate) != expected:
            errors.append(f"runtime guard hash mismatch: {relative}")
    return not errors, errors


def validate_profile(
    *,
    package_root: Path,
    profile_root: Path,
    repo_root: Path,
    hermes_root: Path,
) -> dict[str, Any]:
    package = Path(package_root).resolve()
    profile = Path(profile_root).resolve()
    repository = Path(repo_root).resolve()
    hermes = Path(hermes_root).resolve()
    checks: dict[str, bool] = {}
    errors: list[str] = []

    contract_errors = validate_contracts(package)
    checks["package_contracts"] = not contract_errors
    errors.extend(contract_errors)

    checks["repository"] = repository.is_dir() and (repository / ".git").exists()
    if not checks["repository"]:
        errors.append("repository root must be an existing Git checkout")
    checks["hermes_root"] = hermes.is_dir()
    if not checks["hermes_root"]:
        errors.append("Hermes root must be an existing directory")

    owned_match = True
    for name in _OWNED_CONTRACT_FILES:
        source = package / name
        target = profile / "personalops" / name
        if not source.is_file() or not target.is_file() or source.read_bytes() != target.read_bytes():
            owned_match = False
            errors.append(f"installed contract mismatch: {name}")
    source_guard = package / "profile" / "runtime-contract.json"
    target_guard = profile / "personalops" / "runtime-contract.json"
    if not source_guard.is_file() or not target_guard.is_file() or source_guard.read_bytes() != target_guard.read_bytes():
        owned_match = False
        errors.append("installed contract mismatch: runtime-contract.json")
    checks["owned_contracts"] = owned_match

    source_plugin = package / "profile" / "plugins" / "personalops-repository"
    target_plugin = profile / "plugins" / "personalops-repository"
    plugin_files = ("__init__.py", "plugin.yaml")
    plugin_match = all(
        (source_plugin / name).is_file()
        and (target_plugin / name).is_file()
        and (source_plugin / name).read_bytes() == (target_plugin / name).read_bytes()
        for name in plugin_files
    )
    checks["plugin"] = plugin_match
    if not plugin_match:
        errors.append("installed Personal Ops plugin does not match the package")

    try:
        expected_config = render_config(package, profile, repository, hermes)
        config_match = (profile / "config.yaml").read_text(encoding="utf-8") == expected_config
    except (OSError, UnicodeError):
        config_match = False
    checks["config"] = config_match
    if not config_match:
        errors.append("installed config does not match the local-only profile template")

    guard_ok, guard_errors = validate_runtime_guard(target_guard, hermes)
    checks["runtime_guard"] = guard_ok
    errors.extend(guard_errors)
    return {
        "accepted": not errors,
        "profile_root": str(profile),
        "checks": checks,
        "errors": errors,
    }

