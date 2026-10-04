"""Development freeze-gate audit for System Benchmark v1."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from src.evals.system_benchmark.contracts import BenchmarkFamily, BenchmarkSplit, SystemBenchmarkTask
from src.evals.system_benchmark.references import ReferenceExpectation, validate_task_reference


@dataclass(frozen=True)
class FreezeAudit:
    ready: bool
    task_count: int
    expected_task_count: int
    family_counts: dict[str, int]
    missing_reference_ids: tuple[str, ...]
    invalid_reference_ids: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "task_count": self.task_count,
            "expected_task_count": self.expected_task_count,
            "family_counts": self.family_counts,
            "missing_reference_ids": list(self.missing_reference_ids),
            "invalid_reference_ids": list(self.invalid_reference_ids),
            "reasons": list(self.reasons),
        }


def audit_development_freeze(
    tasks: Iterable[SystemBenchmarkTask],
    references: Iterable[ReferenceExpectation],
    *,
    expected_per_family: int = 3,
) -> FreezeAudit:
    """Check the predeclared PR F exit conditions that are mechanically auditable."""

    task_list = list(tasks)
    reference_by_id = {
        reference.reference_solution_id: reference
        for reference in references
    }
    family_counts = Counter(task.family.value for task in task_list)
    reasons: list[str] = []

    if any(task.split is not BenchmarkSplit.DEVELOPMENT for task in task_list):
        reasons.append("non_development_task_present")

    expected_task_count = len(BenchmarkFamily) * expected_per_family
    if len(task_list) != expected_task_count:
        reasons.append("development_task_count_incomplete")

    for family in BenchmarkFamily:
        if family_counts.get(family.value, 0) != expected_per_family:
            reasons.append(f"family_{family.value}_coverage_incomplete")

    missing: list[str] = []
    invalid: list[str] = []
    for task in task_list:
        reference = reference_by_id.get(task.reference_solution_id)
        if reference is None:
            missing.append(task.reference_solution_id)
            continue
        try:
            validate_task_reference(task, reference)
        except ValueError:
            invalid.append(task.reference_solution_id)

    if missing:
        reasons.append("missing_references")
    if invalid:
        reasons.append("invalid_task_reference_contracts")

    stable_reasons = tuple(dict.fromkeys(reasons))
    return FreezeAudit(
        ready=not stable_reasons,
        task_count=len(task_list),
        expected_task_count=expected_task_count,
        family_counts={
            family.value: family_counts.get(family.value, 0)
            for family in BenchmarkFamily
        },
        missing_reference_ids=tuple(sorted(set(missing))),
        invalid_reference_ids=tuple(sorted(set(invalid))),
        reasons=stable_reasons,
    )
