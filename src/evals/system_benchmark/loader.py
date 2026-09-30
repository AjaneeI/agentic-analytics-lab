"""Fixture loading for System Benchmark v1."""

from __future__ import annotations

import json
from pathlib import Path

from src.evals.system_benchmark.contracts import (
    SystemBenchmarkTask,
    parse_task_contract,
)


def load_tasks(path: str | Path) -> list[SystemBenchmarkTask]:
    """Load and validate a non-empty System Benchmark task fixture."""

    fixture_path = Path(path)
    raw = json.loads(fixture_path.read_text())

    if not isinstance(raw, list):
        raise ValueError("System Benchmark fixture must contain a list")
    if not raw:
        raise ValueError("System Benchmark fixture must contain a non-empty list")

    tasks: list[SystemBenchmarkTask] = []
    seen_ids: set[str] = set()

    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each System Benchmark fixture entry must be an object")
        task = parse_task_contract(item)
        if task.case_id in seen_ids:
            raise ValueError(f"Duplicate System Benchmark case id: {task.case_id}")
        seen_ids.add(task.case_id)
        tasks.append(task)

    return tasks


def fixture_fingerprint_inputs(path: str | Path) -> tuple[Path, ...]:
    """Return deterministic file inputs that define this fixture at PR A."""

    return (Path(path),)
