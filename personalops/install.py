"""Idempotent installer for the isolated Personal Ops Hermes profile."""

from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

from personalops.contracts import validate_contracts
from personalops.validate import render_config, validate_profile


_CONTRACT_FILES = ("VERSION", "policy.json", "workflow.json")


def _require_absolute_directory(path: Path, label: str) -> Path:
    value = Path(path)
    if not value.is_absolute():
        raise ValueError(f"{label} must be absolute")
    value = value.resolve()
    if not value.is_dir():
        raise ValueError(f"{label} must be an existing directory")
    return value


def install_profile(
    *,
    package_root: Path,
    profile_root: Path,
    repo_root: Path,
    hermes_root: Path,
) -> dict[str, Any]:
    package = _require_absolute_directory(Path(package_root), "package root")
    repository = _require_absolute_directory(Path(repo_root), "repository root")
    hermes = _require_absolute_directory(Path(hermes_root), "Hermes root")
    profile_arg = Path(profile_root)
    if not profile_arg.is_absolute():
        raise ValueError("profile root must be absolute")
    profile = profile_arg.resolve()
    if not (repository / ".git").exists():
        raise ValueError("repository root must be a Git checkout")
    contract_errors = validate_contracts(package)
    if contract_errors:
        raise ValueError("invalid Personal Ops contracts: " + "; ".join(contract_errors))

    profile.mkdir(parents=True, exist_ok=True)
    contracts = profile / "personalops"
    contracts.mkdir(parents=True, exist_ok=True)
    for name in _CONTRACT_FILES:
        shutil.copy2(package / name, contracts / name)
    shutil.copy2(package / "profile" / "runtime-contract.json", contracts / "runtime-contract.json")

    source_plugin = package / "profile" / "plugins" / "personalops-repository"
    target_plugin = profile / "plugins" / "personalops-repository"
    if target_plugin.exists():
        shutil.rmtree(target_plugin)
    target_plugin.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_plugin, target_plugin)

    config = render_config(package, profile, repository, hermes)
    (profile / "config.yaml").write_text(config, encoding="utf-8")
    (profile / "cache").mkdir(parents=True, exist_ok=True)
    return validate_profile(
        package_root=package,
        profile_root=profile,
        repo_root=repository,
        hermes_root=hermes,
    )

