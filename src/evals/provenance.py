"""Benchmark provenance helpers.

The fingerprint covers the files that define the frozen evaluation contract and
model-facing data/tool semantics. It is metadata only and does not alter runtime
behavior.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
from typing import Iterable


DEFAULT_CONTRACT_PATHS = (
    "evals/questions.json",
    "src/evals/scoring.py",
    "src/agents/single_agent.py",
    "src/tools/clickhouse_readonly.py",
    "scripts/generate_delivery_data.py",
    "sql/001_create_delivery_work_items.sql",
    "sql/002_ground_truth_team_metrics.sql",
)


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _resolve_commit_sha(root: Path) -> str | None:
    env_sha = os.getenv("GITHUB_SHA")
    if env_sha:
        return env_sha

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    return result.stdout.strip() or None


def build_benchmark_provenance(
    *,
    repository_root: str | Path = ".",
    contract_paths: Iterable[str] = DEFAULT_CONTRACT_PATHS,
    commit_sha: str | None = None,
) -> dict[str, object]:
    root = Path(repository_root)
    file_hashes: dict[str, str] = {}

    for relative in contract_paths:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"Benchmark contract file not found: {relative}")
        file_hashes[relative] = _sha256_bytes(path.read_bytes())

    aggregate = hashlib.sha256()
    for relative, digest in sorted(file_hashes.items()):
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")

    return {
        "git_commit_sha": commit_sha or _resolve_commit_sha(root),
        "benchmark_contract_sha256": aggregate.hexdigest(),
        "contract_files": file_hashes,
    }
